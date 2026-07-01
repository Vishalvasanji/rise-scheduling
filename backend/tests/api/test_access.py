"""Sign-in is required, and project access is hidden + blocked: members only see
and edit assigned projects; admin sees/edits all; user management is admin-only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import session_scope
from app.services import auth_service

client = TestClient(app)
ANCHOR = "2026-06-22"


def _token(email: str, password: str) -> str:
    return client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_token() -> str:
    with session_scope() as s:
        if auth_service.get_by_email(s, "admin2@example.com") is None:
            auth_service.create_user(
                s, email="admin2@example.com", password="pw",
                full_name="Admin Two", role="admin",
            )
    return _token("admin2@example.com", "pw")


def test_auth_required(admin_token):
    # No token → 401 on a gated route.
    assert client.get("/projects").status_code == 401
    assert client.get("/projects", headers=_hdr(admin_token)).status_code == 200


def test_me(admin_token):
    me = client.get("/auth/me", headers=_hdr(admin_token)).json()
    assert me["email"] == "admin2@example.com"
    assert me["is_admin"] is True


def test_member_sees_only_assigned_and_is_blocked(admin_token):
    h = _hdr(admin_token)
    # Admin makes two projects.
    mk = lambda name: client.post(  # noqa: E731
        "/projects", json={"name": name, "anchor_date": ANCHOR}, headers=h
    ).json()["id"]
    p1, p2 = mk("P1"), mk("P2")

    # Admin creates a member assigned to P1 only.
    member = client.post(
        "/users",
        json={
            "email": "member@example.com", "password": "pw",
            "full_name": "Member", "role": "member", "project_ids": [p1],
        },
        headers=h,
    )
    assert member.status_code == 201
    mtok = _token("member@example.com", "pw")
    mh = _hdr(mtok)

    # The member's project list contains P1 but not P2.
    ids = {p["id"] for p in client.get("/projects", headers=mh).json()}
    assert p1 in ids and p2 not in ids

    # Member can read + edit P1...
    assert client.get(f"/projects/{p1}/schedule", headers=mh).status_code == 200
    t = client.post(f"/projects/{p1}/tasks", json={"name": "A", "duration_days": 2}, headers=mh)
    assert t.status_code == 201
    # ...but is blocked from P2 (hidden AND blocked → 403).
    assert client.get(f"/projects/{p2}/schedule", headers=mh).status_code == 403
    assert client.post(
        f"/projects/{p2}/tasks", json={"name": "X", "duration_days": 2}, headers=mh
    ).status_code == 403

    # User management is admin-only.
    assert client.get("/users", headers=mh).status_code == 403
    assert client.get("/users", headers=h).status_code == 200


def test_users_list_tolerates_legacy_invalid_email(admin_token):
    """A stored user with a now-invalid domain (e.g. the pilot's `.local` demo) must
    not 500 the whole Users list — UserOut serializes email as a plain str."""
    with session_scope() as s:
        if auth_service.get_by_email(s, "legacy@rise.local") is None:
            # Bypasses input EmailStr validation the same way the old seed did.
            auth_service.create_user(
                s, email="legacy@rise.local", password="pw", role="member"
            )
    r = client.get("/users", headers=_hdr(admin_token))
    assert r.status_code == 200
    assert any(u["email"] == "legacy@rise.local" for u in r.json())


def test_repair_demo_email_heals_legacy_row():
    from app.seed import admin_user

    with session_scope() as s:
        if auth_service.get_by_email(s, "demo@rise.local") is None:
            auth_service.create_user(
                s, email="demo@rise.local", password="pw", role="leadership"
            )
        assert admin_user.repair_demo_email(s) is True
        assert auth_service.get_by_email(s, "demo@rise.local") is None
        fixed = auth_service.get_by_email(s, "demo@example.com")
        assert fixed is not None and fixed.role == "member"
        # No legacy row left → no-op.
        assert admin_user.repair_demo_email(s) is False


def test_admin_can_reassign_projects(admin_token):
    h = _hdr(admin_token)
    p = client.post(
        "/projects", json={"name": "P3", "anchor_date": ANCHOR}, headers=h
    ).json()["id"]
    u = client.post(
        "/users",
        json={
            "email": "member2@example.com", "password": "pw",
            "role": "member", "project_ids": [],
        },
        headers=h,
    ).json()
    assert u["project_ids"] == []
    updated = client.put(
        f"/users/{u['id']}/projects", json={"project_ids": [p]}, headers=h
    ).json()
    assert updated["project_ids"] == [p]
