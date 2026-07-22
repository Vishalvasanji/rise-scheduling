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


def change_password(
    session: Session, user: User, current_password: str, new_password: str
) -> None:
    """Self-service rotation: verify the current password, write the new hash, and
    clear the forced-change flag. Raises AuthError on a wrong current password."""
    backend = get_auth_backend()
    if not backend.verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect")
    user.password_hash = backend.hash_password(new_password)
    user.must_change_password = False
    session.commit()


def issue_mcp_access_token(email: str, ttl_minutes: int | None = None) -> str:
    """A short-lived OAuth access token for the Claude.ai connector: the same
    ``scope: "mcp"`` JWT the MCP server verifies, so per-user scoping/attribution are
    unchanged. Minted by the OAuth token exchange; refreshed via the refresh token."""
    backend = get_auth_backend()
    ttl = ttl_minutes if ttl_minutes is not None else get_settings().mcp_access_token_ttl_minutes
    return backend.issue_token(
        subject=email, claims={"scope": "mcp"}, ttl_minutes=ttl
    )


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
