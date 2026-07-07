"""The startup readiness gate: /health stays open while the DB initializes, but
DB-backed routes return 503 until the background migrate/seed finishes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import main as main_mod
from app.api.main import app

client = TestClient(app)


def test_health_open_even_when_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(main_mod._ready, "db", False)
    assert client.get("/health").status_code == 200


def test_db_route_returns_503_when_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(main_mod._ready, "db", False)
    r = client.get("/projects")
    assert r.status_code == 503
    assert r.json()["error"] == "starting_up"
    assert r.headers.get("Retry-After") == "5"


def test_db_route_not_gated_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(main_mod._ready, "db", True)
    # Passes the gate through to the real handler (200/401/…), never a 503.
    assert client.get("/projects").status_code != 503
