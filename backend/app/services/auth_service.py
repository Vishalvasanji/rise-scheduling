"""Auth service: user creation and login, routed through the swappable auth
backend. Pilot only."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthError, get_auth_backend
from app.config import get_settings
from app.models import User


def create_user(
    session: Session, email: str, password: str, full_name: str | None = None,
    role: str = "member",
) -> User:
    backend = get_auth_backend()
    user = User(
        email=email,
        full_name=full_name,
        password_hash=backend.hash_password(password),
        role=role,
    )
    session.add(user)
    session.commit()
    return user


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def authenticate(session: Session, email: str, password: str) -> str:
    """Verify credentials and return a signed token. Raises AuthError on failure."""
    backend = get_auth_backend()
    user = get_by_email(session, email)
    if user is None or not backend.verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    return backend.issue_token(subject=user.email, claims={"role": user.role})


def issue_connector_token(user: User) -> str:
    """Mint a long-lived token for a user's Claude.ai custom connector. It carries
    a ``scope: "mcp"`` claim so the MCP server can require it, and reuses the login
    JWT (no separate token store) — regenerating simply issues a new one."""
    backend = get_auth_backend()
    return backend.issue_token(
        subject=user.email,
        claims={"role": user.role, "scope": "mcp"},
        ttl_minutes=get_settings().connector_token_ttl_minutes,
    )
