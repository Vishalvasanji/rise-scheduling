"""Auth endpoints (pilot)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, SessionDep
from app.auth import AuthError
from app.config import get_settings
from app.repositories import oauth_repo, user_repo
from app.schemas.auth import (
    ConnectorTokenResponse,
    LoginRequest,
    MeResponse,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep):
    try:
        token = auth_service.authenticate(session, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    return TokenResponse(access_token=token)


@router.get("/claude-status")
def claude_status(user: CurrentUserDep, session: SessionDep):
    """Whether this user's Claude connector is live — i.e. they hold a non-expired
    OAuth refresh token. Drives the header's Claude status pill."""
    return {"connected": oauth_repo.has_active_refresh_token(session, user.email)}


@router.get("/connector-url")
def connector_url(_user: CurrentUserDep):
    """The MCP URL to paste into Claude.ai's custom connector. Claude runs the OAuth
    flow against it and the user signs in with their scheduling-hub account — no token
    to copy."""
    return {"connector_url": get_settings().mcp_public_url}


@router.get("/connector-warm")
async def connector_warm(_user: CurrentUserDep):
    """Wake the MCP connector dyno before the user connects from Claude. The MCP
    service is a Render free web service that sleeps when idle, so the first
    connection cold-starts and can time out. Hitting its cheap /health route from
    the web app warms it; the browser calls our own API to avoid CORS. Returns
    ``{"ready": true}`` once the MCP server answers (the request may block for the
    duration of a cold start)."""
    url = get_settings().mcp_issuer_url.rstrip("/") + "/health"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
    except httpx.HTTPError:
        return {"ready": False}
    return {"ready": resp.status_code == 200}


@router.post("/connector-token", response_model=ConnectorTokenResponse)
def connector_token(user: CurrentUserDep):
    """Mint this user's long-lived connector token (Bearer) — for local/stdio MCP use
    (e.g. Claude Desktop). The hosted Claude.ai connector uses OAuth instead."""
    return ConnectorTokenResponse(
        token=auth_service.issue_connector_token(user),
        connector_url=get_settings().mcp_public_url,
    )


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUserDep, session: SessionDep):
    return MeResponse(
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_admin=user.role == "admin",
        project_ids=user_repo.assigned_project_ids(session, user.id),
    )
