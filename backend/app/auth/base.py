"""Auth backend protocol — the seam production swaps for Entra ID."""

from __future__ import annotations

from typing import Protocol


class AuthError(Exception):
    """Raised on invalid credentials or an invalid/expired token."""


class AuthBackend(Protocol):
    """Password hashing + token issue/verify. Implementations must not use
    custom crypto (SCOPE §8)."""

    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password: str, password_hash: str) -> bool: ...

    def issue_token(
        self, *, subject: str, claims: dict | None = None,
        ttl_minutes: int | None = None,
    ) -> str: ...

    def verify_token(self, token: str) -> dict:
        """Return the token claims, or raise :class:`AuthError`."""
        ...
