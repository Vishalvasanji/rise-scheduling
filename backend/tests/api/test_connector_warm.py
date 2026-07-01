"""Tests for the warm-on-connect endpoint (/auth/connector-warm) and the MCP
health route it pings — both wake the sleepy free-tier connector dyno."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


@pytest.fixture()
def auth_token() -> str:
    from app.db.session import session_scope
    from app.services import auth_service

    with session_scope() as s:
        if auth_service.get_by_email(s, "warm-admin@example.com") is None:
            auth_service.create_user(
                s, email="warm-admin@example.com", password="pw",
                full_name="Warm Admin", role="admin",
            )
    return client.post(
        "/auth/login", json={"email": "warm-admin@example.com", "password": "pw"}
    ).json()["access_token"]


class _FakeResp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def _fake_client(*, status_code: int | None = None, raises: Exception | None = None):
    class _Client:
        def __init__(self, *a, **k) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a) -> bool:
            return False

        async def get(self, url):  # noqa: ANN001
            if raises is not None:
                raise raises
            return _FakeResp(status_code)

    return _Client


def test_connector_warm_requires_auth():
    assert client.get("/auth/connector-warm").status_code == 401


def test_connector_warm_ready_when_health_ok(auth_token, monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.auth.httpx.AsyncClient", _fake_client(status_code=200)
    )
    resp = client.get(
        "/auth/connector-warm", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"ready": True}


def test_connector_warm_not_ready_on_error(auth_token, monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.auth.httpx.AsyncClient",
        _fake_client(raises=httpx.ConnectTimeout("cold start")),
    )
    resp = client.get(
        "/auth/connector-warm", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"ready": False}


def test_connector_warm_not_ready_on_non_200(auth_token, monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.auth.httpx.AsyncClient", _fake_client(status_code=503)
    )
    resp = client.get(
        "/auth/connector-warm", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.json() == {"ready": False}


def test_mcp_health_route():
    """The MCP server exposes a cheap no-DB /health route for waking the dyno."""
    import asyncio
    import json

    from app.mcp.server import health

    resp = asyncio.run(health(None))  # the handler ignores the request
    assert resp.status_code == 200
    assert json.loads(resp.body) == {"status": "ok"}
