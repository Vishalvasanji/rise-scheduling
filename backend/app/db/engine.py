"""The single place the database engine is constructed from ``DATABASE_URL``.

This is the swap point for SCOPE's portability constraint: moving from SQLite to
Turso (libSQL) or Postgres is a change to ``DATABASE_URL`` only. SQLite needs
``PRAGMA foreign_keys=ON`` per-connection to enforce foreign keys.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _prepare_libsql(url: str) -> tuple[str, dict]:
    """Split a Turso libSQL URL into a clean URL + connect_args.

    The libSQL dialect expects the Turso auth token via ``connect_args``
    (``auth_token``), NOT the URL query string, so we lift ``authToken`` /
    ``auth_token`` out of the query and keep the rest (e.g. ``secure=true``).
    A lone ``/`` path is dropped so only the host identifies the remote DB.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    token = query.pop("authToken", None) or query.pop("auth_token", None)
    path = "" if parts.path in ("", "/") else parts.path
    clean = urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), ""))
    connect_args = {"auth_token": token} if token else {}
    return clean, connect_args


def _build_engine(url: str) -> Engine:
    is_sqlite_family = url.startswith("sqlite")
    is_libsql = "+libsql" in url  # Turso (libSQL) — NOT pysqlite

    connect_args: dict = {}
    if is_libsql:
        # Pass the auth token via connect_args; check_same_thread is pysqlite-only.
        url, connect_args = _prepare_libsql(url)
    elif is_sqlite_family:
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, future=True)

    # PRAGMA foreign_keys is a local-pysqlite concern; on Turso auth/url config
    # travels in the connection string and this listener does not apply.
    if is_sqlite_family and not is_libsql:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine(get_settings().database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionLocal
