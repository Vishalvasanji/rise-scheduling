"""API smoke tests: CRUD, schedule read, and engine-error status codes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)
ANCHOR = "2026-06-22"


@pytest.fixture(autouse=True)
def _auth():
    """Authenticate the shared client as an admin (every route now requires
    sign-in; an admin can reach every project)."""
    from app.db.session import session_scope
    from app.services import auth_service

    with session_scope() as s:
        if auth_service.get_by_email(s, "api-admin@example.com") is None:
            auth_service.create_user(
                s, email="api-admin@example.com", password="pw",
                full_name="API Admin", role="admin",
            )
    token = client.post(
        "/auth/login", json={"email": "api-admin@example.com", "password": "pw"}
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield
    client.headers.pop("Authorization", None)


@pytest.fixture()
def project_id() -> int:
    resp = client.post("/projects", json={"name": "API Test", "anchor_date": ANCHOR})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_task_crud_and_schedule(project_id):
    a = client.post(f"/projects/{project_id}/tasks", json={"name": "A", "duration_days": 5}).json()
    b = client.post(f"/projects/{project_id}/tasks", json={"name": "B", "duration_days": 3}).json()
    dep = client.post(
        "/dependencies",
        json={"predecessor_id": a["id"], "successor_id": b["id"], "type": "FS"},
    )
    assert dep.status_code == 201

    schedule = client.get(f"/projects/{project_id}/schedule").json()
    assert len(schedule["tasks"]) == 2
    assert len(schedule["dependencies"]) == 1
    b_out = next(t for t in schedule["tasks"] if t["id"] == b["id"])
    assert b_out["planned_start"] is not None
    assert b_out["is_critical"] is True


def test_cycle_returns_409(project_id):
    a = client.post(f"/projects/{project_id}/tasks", json={"name": "A", "duration_days": 2}).json()
    b = client.post(f"/projects/{project_id}/tasks", json={"name": "B", "duration_days": 2}).json()
    client.post("/dependencies", json={"predecessor_id": a["id"], "successor_id": b["id"]})
    resp = client.post("/dependencies", json={"predecessor_id": b["id"], "successor_id": a["id"]})
    assert resp.status_code == 409
    assert resp.json()["error"] == "circular_dependency"
    assert resp.json()["cycle"][0] == resp.json()["cycle"][-1]


def test_date_conflict_returns_422(project_id):
    t = client.post(f"/projects/{project_id}/tasks", json={"name": "A", "duration_days": 5}).json()
    resp = client.patch(
        f"/tasks/{t['id']}",
        json={"actual_start": "2026-06-26", "actual_finish": "2026-06-22"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "date_conflict"


def test_delete_task(project_id):
    payload = {"name": "Temp", "duration_days": 1}
    t = client.post(f"/projects/{project_id}/tasks", json=payload).json()
    assert client.delete(f"/tasks/{t['id']}").status_code == 204
    assert client.get(f"/tasks/{t['id']}").status_code == 404


def test_stale_edit_returns_409(project_id):
    t = client.post(f"/projects/{project_id}/tasks", json={"name": "A", "duration_days": 5}).json()
    assert t["version"] == 1
    # First edit succeeds and bumps the version to 2.
    ok = client.patch(f"/tasks/{t['id']}", json={"duration_days": 6, "expected_version": 1})
    assert ok.status_code == 200 and ok.json()["version"] == 2
    # A second edit still claiming version 1 conflicts (409) and names the editor.
    stale = client.patch(f"/tasks/{t['id']}", json={"duration_days": 7, "expected_version": 1})
    assert stale.status_code == 409
    body = stale.json()
    assert body["error"] == "version_conflict"
    assert body["current_version"] == 2 and body["updated_by"] == "api-admin@example.com"
    # Forcing the overwrite lands it.
    forced = client.patch(
        f"/tasks/{t['id']}", json={"duration_days": 7, "expected_version": 1, "force": True}
    )
    assert forced.status_code == 200 and forced.json()["duration_days"] == 7
