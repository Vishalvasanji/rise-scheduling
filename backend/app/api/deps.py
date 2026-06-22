"""FastAPI dependencies: DB session, current user, and engine-error translation."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth import AuthError, get_auth_backend
from app.db.session import get_db

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
