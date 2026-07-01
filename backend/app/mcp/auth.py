"""Bearer-token auth for the hosted MCP (Streamable HTTP) connector.

Each user pastes a long-lived connector token (minted by ``POST /auth/connector-token``,
a JWT carrying ``scope: "mcp"``) into the Claude.ai custom connector. This verifier runs
on every MCP request: it decodes the token with the shared ``auth_secret``, confirms the
user still exists, and hands the request the user's email as the subject — which the
tools use to attribute and scope every change. Reuses the same JWT backend as the web
API; the MCP service shares the API's database, so users/assignments are visible here.
"""

from __future__ import annotations

from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.auth import AuthError, get_auth_backend
from app.db.session import session_scope
from app.repositories import user_repo

_SCOPE = "mcp"


def decode_mcp_token(token: str) -> AccessToken | None:
    """Verify a connector JWT (scope "mcp") and resolve it to the owning user, or
    None. Shared by the bearer verifier (stdio/local) and the OAuth provider's
    ``load_access_token`` (the hosted Claude.ai connector)."""
    try:
        claims = get_auth_backend().verify_token(token)
    except AuthError:
        return None
    if claims.get("scope") != _SCOPE:
        return None
    email = claims.get("sub")
    if not email:
        return None
    with session_scope() as session:
        user = user_repo.get_by_email(session, email)
    if user is None:
        return None
    return AccessToken(
        token=token,
        client_id=email,
        scopes=[_SCOPE],
        subject=email,
        expires_at=claims.get("exp"),
        claims={"role": user.role},
    )


class JWTTokenVerifier(TokenVerifier):
    """Verify a connector JWT and resolve it to the owning user (or reject)."""

    async def verify_token(self, token: str) -> AccessToken | None:
        # None → FastMCP's RequireAuthMiddleware returns a 401.
        return decode_mcp_token(token)
