"""The Claude.ai connector authenticates via a self-hosted OAuth flow backed by the
scheduling-hub accounts: register → authorize → sign in → code → token, with the issued
access token being the same scope:"mcp" JWT the tools already verify."""

from __future__ import annotations

import asyncio
import time

from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from app.mcp import oauth
from app.mcp.auth import decode_mcp_token
from app.mcp.oauth import SchedulingHubOAuthProvider, verify_login_request
from app.mcp.oauth_login import oauth_login
from app.repositories import oauth_repo
from app.services import auth_service

REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def _run(coro):
    return asyncio.run(coro)


def _client(client_id: str = "client-abc") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(client_id=client_id, redirect_uris=[REDIRECT])


def _params() -> AuthorizationParams:
    return AuthorizationParams(
        state="xyz",
        scopes=["mcp"],
        code_challenge="challenge123",
        redirect_uri=REDIRECT,
        redirect_uri_provided_explicitly=True,
        resource="https://rise-schedule-hub-mcp.onrender.com/mcp",
    )


def test_register_and_get_client(session):
    p = SchedulingHubOAuthProvider()
    _run(p.register_client(_client("client-reg")))
    loaded = _run(p.get_client("client-reg"))
    assert loaded is not None and str(loaded.redirect_uris[0]) == REDIRECT
    assert _run(p.get_client("nope")) is None


def test_authorize_redirects_to_signin_with_signed_request(session):
    p = SchedulingHubOAuthProvider()
    url = _run(p.authorize(_client(), _params()))
    assert url.startswith(oauth.login_url() + "?req=")
    blob = url.split("req=", 1)[1]
    claims = verify_login_request(blob)
    assert claims is not None
    assert claims["redirect_uri"] == REDIRECT
    assert claims["code_challenge"] == "challenge123"
    assert claims["state"] == "xyz"


def test_full_code_exchange_and_refresh(session):
    auth_service.create_user(session, email="oauth@example.com", password="pw", role="member")
    p = SchedulingHubOAuthProvider()
    _run(p.register_client(_client()))

    # authorize -> sign in (simulate the login page completing) -> code
    blob = _run(p.authorize(_client(), _params())).split("req=", 1)[1]
    claims = verify_login_request(blob)
    claims["subject"] = "oauth@example.com"
    code_str = oauth.issue_code_after_login(claims)

    authcode = _run(p.load_authorization_code(_client(), code_str))
    assert authcode is not None
    assert authcode.subject == "oauth@example.com"
    assert authcode.code_challenge == "challenge123"

    token = _run(p.exchange_authorization_code(_client(), authcode))
    access = decode_mcp_token(token.access_token)
    assert access is not None and access.subject == "oauth@example.com"
    assert access.scopes == ["mcp"]
    assert token.refresh_token

    # The code is single-use.
    assert _run(p.load_authorization_code(_client(), code_str)) is None

    # load_access_token accepts the issued JWT, rejects junk.
    assert _run(p.load_access_token(token.access_token)) is not None
    assert _run(p.load_access_token("not-a-jwt")) is None

    # Refresh mints a fresh working access token.
    rt = _run(p.load_refresh_token(_client(), token.refresh_token))
    assert rt is not None and rt.subject == "oauth@example.com"
    refreshed = _run(p.exchange_refresh_token(_client(), rt, ["mcp"]))
    assert decode_mcp_token(refreshed.access_token).subject == "oauth@example.com"
    # The rotated refresh token is single-use.
    assert _run(p.load_refresh_token(_client(), token.refresh_token)) is None


# ---- the sign-in page ----

def _login_client() -> TestClient:
    app = Starlette(routes=[Route("/oauth/login", oauth_login, methods=["GET", "POST"])])
    return TestClient(app)


def test_signin_page_renders_and_rejects_bad_link(session):
    p = SchedulingHubOAuthProvider()
    blob = _run(p.authorize(_client(), _params())).split("req=", 1)[1]
    c = _login_client()
    assert c.get(f"/oauth/login?req={blob}").status_code == 200
    assert "Connect Claude to RISE" in c.get(f"/oauth/login?req={blob}").text
    assert c.get("/oauth/login?req=garbage").status_code == 400


def test_signin_completes_grant_and_rejects_bad_password(session):
    auth_service.create_user(session, email="signin@example.com", password="pw", role="member")
    p = SchedulingHubOAuthProvider()
    blob = _run(p.authorize(_client(), _params())).split("req=", 1)[1]
    c = _login_client()

    bad = c.post(
        "/oauth/login",
        data={"req": blob, "email": "signin@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401

    ok = c.post(
        "/oauth/login",
        data={"req": blob, "email": "signin@example.com", "password": "pw"},
        follow_redirects=False,
    )
    assert ok.status_code == 302
    assert ok.headers["location"].startswith(REDIRECT)
    assert "code=" in ok.headers["location"] and "state=xyz" in ok.headers["location"]


# ---- connection-status pill signal ----

def test_has_active_refresh_token(session):
    email = "pill@example.com"
    assert oauth_repo.has_active_refresh_token(session, email) is False
    oauth_repo.add_refresh_token(
        session, token="rt-live", client_id="c", subject=email,
        scopes=["mcp"], expires_at=int(time.time()) + 3600,
    )
    assert oauth_repo.has_active_refresh_token(session, email) is True


def test_has_active_refresh_token_ignores_expired(session):
    email = "expired@example.com"
    oauth_repo.add_refresh_token(
        session, token="rt-old", client_id="c", subject=email,
        scopes=["mcp"], expires_at=int(time.time()) - 10,
    )
    assert oauth_repo.has_active_refresh_token(session, email) is False
