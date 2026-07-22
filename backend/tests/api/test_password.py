"""Self-service change-password, forced rotation of temp passwords, and the
login brute-force throttle."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import session_scope
from app.services import auth_service

client = TestClient(app)


def _token(email: str, password: str) -> str:
    return client.post("/auth/login", json={"email": email, "password": password}).json()[
        "access_token"
    ]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mk_admin(email: str) -> str:
    with session_scope() as s:
        if auth_service.get_by_email(s, email) is None:
            auth_service.create_user(s, email=email, password="pw", role="admin")
    return _token(email, "pw")


def test_admin_created_user_must_change_then_clears():
    admin = _mk_admin("pwadmin@example.com")
    r = client.post(
        "/users",
        headers=_hdr(admin),
        json={"email": "field1@example.com", "password": "temp-pass-1", "role": "member"},
    )
    assert r.status_code == 201

    tok = _token("field1@example.com", "temp-pass-1")
    me = client.get("/auth/me", headers=_hdr(tok)).json()
    assert me["must_change_password"] is True

    # Wrong current password → 403, flag stays.
    r = client.post(
        "/auth/change-password",
        headers=_hdr(tok),
        json={"current_password": "nope", "new_password": "my-own-pass-9"},
    )
    assert r.status_code == 403

    # Correct current password → 204, flag clears, old password stops working.
    r = client.post(
        "/auth/change-password",
        headers=_hdr(tok),
        json={"current_password": "temp-pass-1", "new_password": "my-own-pass-9"},
    )
    assert r.status_code == 204
    tok2 = _token("field1@example.com", "my-own-pass-9")
    assert client.get("/auth/me", headers=_hdr(tok2)).json()["must_change_password"] is False
    assert (
        client.post(
            "/auth/login", json={"email": "field1@example.com", "password": "temp-pass-1"}
        ).status_code
        == 401
    )


def test_admin_reset_sets_flag_again():
    admin = _mk_admin("pwadmin2@example.com")
    r = client.post(
        "/users",
        headers=_hdr(admin),
        json={"email": "field2@example.com", "password": "temp-a", "role": "member"},
    )
    uid = r.json()["id"]
    tok = _token("field2@example.com", "temp-a")
    client.post(
        "/auth/change-password",
        headers=_hdr(tok),
        json={"current_password": "temp-a", "new_password": "settled-pass-1"},
    )
    # Admin resets the password → forced-change comes back.
    r = client.patch(f"/users/{uid}", headers=_hdr(admin), json={"password": "temp-b"})
    assert r.status_code == 200
    tok2 = _token("field2@example.com", "temp-b")
    assert client.get("/auth/me", headers=_hdr(tok2)).json()["must_change_password"] is True


def test_short_new_password_rejected():
    with session_scope() as s:
        if auth_service.get_by_email(s, "shorty@example.com") is None:
            auth_service.create_user(s, email="shorty@example.com", password="pw-eight1")
    tok = _token("shorty@example.com", "pw-eight1")
    r = client.post(
        "/auth/change-password",
        headers=_hdr(tok),
        json={"current_password": "pw-eight1", "new_password": "short"},
    )
    assert r.status_code == 422  # pydantic min_length


def test_login_throttle_locks_after_five_failures():
    email = "throttle@example.com"
    with session_scope() as s:
        if auth_service.get_by_email(s, email) is None:
            auth_service.create_user(s, email=email, password="right-pass-1")
    for _ in range(5):
        assert (
            client.post("/auth/login", json={"email": email, "password": "wrong"}).status_code
            == 401
        )
    # Sixth attempt (even with the RIGHT password) is throttled.
    r = client.post("/auth/login", json={"email": email, "password": "right-pass-1"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers
