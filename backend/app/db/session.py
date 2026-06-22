"""Session helpers: a context manager for scripts/services and a FastAPI
dependency. Both yield a Session from the single session factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.engine import get_session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional Session scope for scripts and the service layer."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped Session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
