"""Auth endpoints (pilot)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.auth import AuthError
from app.schemas.auth import LoginRequest, TokenResponse
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
