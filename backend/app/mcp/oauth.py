"""Self-hosted OAuth 2.1 authorization server for the Claude.ai connector, backed by
the scheduling-hub user accounts.

The MCP SDK mounts the OAuth endpoints (/authorize, /token, /register, /revoke,
discovery) and verifies PKCE; this provider owns the state and identity: it registers
connector clients (DCR), sends the user to our sign-in page, mints single-use
authorization codes after they log in with their scheduling-hub email/password, and
exchanges those for a ``scope:"mcp"`` access-token JWT (+ refresh token). Because the
access token is the same JWT the MCP tools already verify, per-user project scoping and
"via Claude" attribution work unchanged.
"""

from __future__ import annotations

import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from app.auth import AuthError, get_auth_backend
from app.config import get_settings
from app.db.session import session_scope
from app.mcp.auth import decode_mcp_token
from app.repositories import oauth_repo
from app.services import auth_service

_SCOPE = "mcp"
_CODE_TTL_SECONDS = 300          # authorization code lifetime
_REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
_LOGIN_REQUEST_TTL_MINUTES = 15  # the signed blob carrying the /authorize params


def login_url() -> str:
    return f"{get_settings().mcp_issuer_url.rstrip('/')}/oauth/login"


def sign_login_request(client_id: str, params: AuthorizationParams) -> str:
    """Pack the in-flight /authorize params into a short-lived signed blob so the
    sign-in page can complete the grant without a server-side pending-auth table."""
    return get_auth_backend().issue_token(
        subject=client_id,
        claims={
            "typ": "oauth_login",
            "redirect_uri": str(params.redirect_uri),
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
            "code_challenge": params.code_challenge,
            "scopes": params.scopes or [_SCOPE],
            "state": params.state,
            "resource": params.resource,
        },
        ttl_minutes=_LOGIN_REQUEST_TTL_MINUTES,
    )


def verify_login_request(blob: str) -> dict | None:
    try:
        claims = get_auth_backend().verify_token(blob)
    except AuthError:
        return None
    if claims.get("typ") != "oauth_login":
        return None
    return claims


def issue_code_after_login(claims: dict) -> str:
    """Called by the sign-in page once the user is authenticated: mint a single-use
    authorization code bound to their email and return the code string."""
    code = secrets.token_urlsafe(32)
    with session_scope() as session:
        oauth_repo.add_code(
            session,
            code=code,
            client_id=claims["sub"],
            subject=claims["subject"],
            redirect_uri=claims["redirect_uri"],
            redirect_uri_provided_explicitly=bool(
                claims["redirect_uri_provided_explicitly"]
            ),
            code_challenge=claims["code_challenge"],
            scopes=claims.get("scopes") or [_SCOPE],
            resource=claims.get("resource"),
            expires_at=time.time() + _CODE_TTL_SECONDS,
        )
    return code


def redirect_after_login(claims: dict, code: str) -> str:
    return construct_redirect_uri(
        claims["redirect_uri"], code=code, state=claims.get("state")
    )


class SchedulingHubOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    # ---- clients (dynamic registration) ----

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with session_scope() as session:
            row = oauth_repo.get_client(session, client_id)
        if row is None:
            return None
        return OAuthClientInformationFull.model_validate(row.client_info)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        with session_scope() as session:
            oauth_repo.upsert_client(
                session,
                client_id=client_info.client_id,
                client_secret=client_info.client_secret,
                client_info=client_info.model_dump(mode="json"),
            )

    # ---- authorize: hand the user to our sign-in page ----

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        blob = sign_login_request(client.client_id, params)
        return f"{login_url()}?req={blob}"

    # ---- authorization code grant ----

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        with session_scope() as session:
            row = oauth_repo.get_code(session, authorization_code)
        if row is None or row.client_id != client.client_id:
            return None
        if row.expires_at < time.time():
            return None
        return AuthorizationCode(
            code=row.code,
            scopes=list(row.scopes or []),
            expires_at=row.expires_at,
            client_id=row.client_id,
            code_challenge=row.code_challenge,
            redirect_uri=row.redirect_uri,
            redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
            resource=row.resource,
            subject=row.subject,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        with session_scope() as session:
            oauth_repo.consume_code(session, authorization_code.code)  # single-use
        return self._issue_tokens(
            authorization_code.subject, client.client_id, authorization_code.scopes
        )

    # ---- refresh token grant ----

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        with session_scope() as session:
            row = oauth_repo.get_refresh_token(session, refresh_token)
        if row is None or row.client_id != client.client_id:
            return None
        if row.expires_at is not None and row.expires_at < int(time.time()):
            return None
        return RefreshToken(
            token=row.token,
            client_id=row.client_id,
            scopes=list(row.scopes or []),
            expires_at=row.expires_at,
            subject=row.subject,
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Rotate: drop the used refresh token and issue a fresh pair.
        with session_scope() as session:
            oauth_repo.delete_refresh_token(session, refresh_token.token)
        return self._issue_tokens(
            refresh_token.subject, client.client_id, scopes or refresh_token.scopes
        )

    # ---- access token verification (every MCP request) ----

    async def load_access_token(self, token: str) -> AccessToken | None:
        return decode_mcp_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        # Access tokens are stateless JWTs; only stored refresh tokens are revocable.
        if isinstance(token, RefreshToken):
            with session_scope() as session:
                oauth_repo.delete_refresh_token(session, token.token)

    # ---- helpers ----

    def _issue_tokens(
        self, subject: str, client_id: str, scopes: list[str]
    ) -> OAuthToken:
        ttl = get_settings().mcp_access_token_ttl_minutes
        access = auth_service.issue_mcp_access_token(subject, ttl_minutes=ttl)
        refresh = secrets.token_urlsafe(32)
        with session_scope() as session:
            oauth_repo.add_refresh_token(
                session,
                token=refresh,
                client_id=client_id,
                subject=subject,
                scopes=scopes or [_SCOPE],
                expires_at=int(time.time()) + _REFRESH_TTL_SECONDS,
            )
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=ttl * 60,
            scope=" ".join(scopes or [_SCOPE]),
            refresh_token=refresh,
        )
