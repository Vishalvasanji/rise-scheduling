"""Unhandled exceptions must come back as JSON 500s WITH CORS headers — a bare
Starlette 500 bypasses the CORS layer, and the browser then reports an opaque
"Failed to fetch" instead of showing the app's error banner."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


@app.get("/__test_boom")
def _boom():  # pragma: no cover - the raise IS the test fixture
    raise RuntimeError("kaboom")


def test_unhandled_error_is_json_500_with_cors():
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/__test_boom", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 500
    assert r.json()["error"] == "internal_error"
    # The part that used to break: the error response must clear CORS so the
    # frontend can actually read it.
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
