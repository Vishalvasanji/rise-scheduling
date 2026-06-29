"""FastAPI dependencies: DB session, current user, and engine-error translation."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthError, get_auth_backend
from app.db.session import get_db
from app.models import User
from app.repositories import user_repo

SessionDep = Annotated[Session, Depends(get_db)]


def get_current_actor(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Resolve the acting user from a bearer token. Pilot auth is permissive:
    unauthenticated calls act as 'anonymous' so the dummy-data pilot is usable
    without a login wall, but a valid token is honoured for the audit trail."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return "anonymous"
    token = authorization.split(" ", 1)[1]
    try:
        claims = get_auth_backend().verify_token(token)
        return claims.get("sub", "anonymous")
    except AuthError:
        return "anonymous"


ActorDep = Annotated[str, Depends(get_current_actor)]


def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Strict identity: resolve the signed-in `User` from the bearer token, or
    401. Unlike `get_current_actor`, this never falls back to anonymous — it gates
    the web app's authenticated routes."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        claims = get_auth_backend().verify_token(token)
    except AuthError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    email = claims.get("sub")
    user = user_repo.get_by_email(session, email) if email else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUserDep) -> User:
    """403 unless the signed-in user is an admin."""
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


AdminDep = Annotated[User, Depends(require_admin)]
