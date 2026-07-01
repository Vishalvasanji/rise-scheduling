"""Auth schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    # Plain str: login is a lookup by address, and a legacy account with a now-invalid
    # domain (e.g. the pilot demo `@rise.local`) must still be able to sign in.
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConnectorTokenResponse(BaseModel):
    """A long-lived token + the MCP URL to paste into the Claude.ai connector."""

    token: str
    connector_url: str


class MeResponse(BaseModel):
    """The signed-in user's identity + access, for the frontend gate."""

    # Plain str: output of a stored identity (see UserOut) — never re-validate here.
    email: str
    full_name: str | None = None
    role: str
    is_admin: bool
    project_ids: list[int] = []
