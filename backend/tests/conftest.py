"""Shared fixtures: an isolated in-memory-ish SQLite DB per test session, with
the schema created from the ORM metadata and a single seeded project."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# Point the app at a throwaway SQLite file BEFORE importing app modules that
# read settings / build the engine.
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.name}"
# Tests build the schema from ORM metadata below; never let the app's startup
# migrate/seed run against the throwaway DB (it would double-create and pollute).
os.environ["MIGRATE_ON_STARTUP"] = "false"

from app.db.base import Base  # noqa: E402
from app.db.engine import get_engine  # noqa: E402
from app.db.session import session_scope  # noqa: E402
from app.models import *  # noqa: E402,F401,F403


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    engine = get_engine()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    try:
        os.unlink(_TMP.name)
    except OSError:
        pass


@pytest.fixture()
def session() -> Iterator:
    with session_scope() as s:
        yield s
