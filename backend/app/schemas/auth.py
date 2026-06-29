"""Auth schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """The signed-in user's identity + access, for the frontend gate."""

    email: EmailStr
    full_name: str | None = None
    role: str
    is_admin: bool
    project_ids: list[int] = []
