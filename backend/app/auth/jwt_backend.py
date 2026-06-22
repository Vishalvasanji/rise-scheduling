"""JWT + passlib(bcrypt) auth backend. Standard libraries only, no custom
crypto. Pilot-only — replaced by Entra ID before real data (SCOPE §11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.auth.base import AuthError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"


class JWTAuthBackend:
    def __init__(self, secret: str, ttl_minutes: int) -> None:
        self._secret = secret
        self._ttl = timedelta(minutes=ttl_minutes)

    def hash_password(self, password: str) -> str:
        return _pwd_context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return _pwd_context.verify(password, password_hash)

    def issue_token(self, *, subject: str, claims: dict | None = None) -> str:
        now = datetime.now(UTC)
        payload = {"sub": subject, "iat": now, "exp": now + self._ttl}
        if claims:
            payload.update(claims)
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def verify_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:  # expired, bad signature, malformed
            raise AuthError("Invalid or expired token") from exc
