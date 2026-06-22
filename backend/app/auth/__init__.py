"""Pilot auth, behind one swappable module (SCOPE §8). In-house and basic —
acceptable only because the pilot uses dummy data. Swaps to Entra ID in
production by replacing the backend selected in ``get_auth_backend``."""

from app.auth.base import AuthBackend, AuthError
from app.auth.jwt_backend import JWTAuthBackend
from app.config import get_settings

_backend: AuthBackend | None = None


def get_auth_backend() -> AuthBackend:
    """Return the configured auth backend (the single swap point)."""
    global _backend
    if _backend is None:
        settings = get_settings()
        # Only one backend in the pilot; selection lives here for the future swap.
        _backend = JWTAuthBackend(
            secret=settings.auth_secret, ttl_minutes=settings.auth_token_ttl_minutes
        )
    return _backend


__all__ = ["AuthBackend", "AuthError", "JWTAuthBackend", "get_auth_backend"]
