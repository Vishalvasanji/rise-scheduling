"""User-management schemas (admin)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: str
    project_ids: list[int] = []


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "member"
    project_ids: list[int] = []


class UserUpdate(BaseModel):
    """All optional; only provided fields are written. `password` resets it."""

    full_name: str | None = None
    role: str | None = None
    password: str | None = None


class ProjectAssignment(BaseModel):
    project_ids: list[int]
