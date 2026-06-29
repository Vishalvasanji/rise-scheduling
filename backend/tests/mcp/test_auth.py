"""The Claude.ai (MCP) connector is per-user: a long-lived connector token resolves
to the signed-in user, and every tool attributes changes to them and limits them to
their assigned projects — the same access rules the web app enforces."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import date

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from app.mcp import tools
from app.mcp.auth import JWTTokenVerifier
from app.repositories import user_repo
from app.services import auth_service, project_service

ANCHOR = date(2026, 6, 22)


@contextmanager
def as_user(email: str):
    """Simulate an authenticated MCP request for ``email`` (what the bearer middleware
    does in production) so the tools see a connected user."""
    token = AccessToken(
        token="t", client_id=email, scopes=["mcp"], subject=email,
    )
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        yield
    finally:
        auth_context_var.reset(reset)


# ---- connector token + verifier ----

def test_connector_token_round_trips_to_the_user(session):
    user = auth_service.create_user(
        session, email="conn@example.com", password="pw", role="member"
    )
    token = auth_service.issue_connector_token(user)

    access = asyncio.run(JWTTokenVerifier().verify_token(token))
    assert access is not None
    assert access.subject == "conn@example.com"
    assert access.scopes == ["mcp"]


def test_verifier_rejects_plain_login_and_garbage_tokens(session):
    auth_service.create_user(
        session, email="login@example.com", password="pw", role="member"
    )
    # A normal login token has no `scope: mcp` claim → rejected for the connector.
    login_token = auth_service.authenticate(session, "login@example.com", "pw")
    verifier = JWTTokenVerifier()
    assert asyncio.run(verifier.verify_token(login_token)) is None
    assert asyncio.run(verifier.verify_token("not-a-jwt")) is None


# ---- per-user project scoping in the tools ----

def _get_or_create(session, email: str, role: str):
    user = auth_service.get_by_email(session, email)
    if user is None:
        user = auth_service.create_user(session, email=email, password="pw", role=role)
    return user


def _setup(session):
    """Idempotent: tests share one SQLite file (no per-test rollback)."""
    admin = _get_or_create(session, "mcpadmin@example.com", "admin")
    member = _get_or_create(session, "mcpmember@example.com", "member")
    p1 = project_service.create_project(session, name="MCP P1", anchor_date=ANCHOR)
    p2 = project_service.create_project(session, name="MCP P2", anchor_date=ANCHOR)
    user_repo.set_projects(session, member.id, [p1.id])
    session.commit()
    return admin, member, p1, p2


def test_member_lists_and_edits_only_assigned_projects(session):
    _admin, _member, p1, p2 = _setup(session)

    with as_user("mcpmember@example.com"):
        # list_projects is filtered to the assignment.
        names = {p["id"] for p in tools.list_projects()["projects"]}
        assert p1.id in names and p2.id not in names

        # Reading/creating on an assigned project works and is attributed to the user.
        assert tools.get_schedule(p1.id)["ok"]
        created = tools.create_task(p1.id, {"name": "Wall", "duration_days": 2})
        assert created["ok"]

        # An unassigned project is blocked for read AND write.
        assert tools.get_schedule(p2.id)["error"] == "forbidden"
        assert tools.create_task(p2.id, {"name": "X", "duration_days": 1})["error"] == "forbidden"

    # The chat change was attributed to the real user, not "chat".
    audited = project_service.get_schedule(session, p1.id)
    task = next(t for t in audited[1] if t.name == "Wall")
    assert task.updated_by == "mcpmember@example.com"


def test_admin_reaches_every_project(session):
    _admin, _member, _p1, p2 = _setup(session)
    with as_user("mcpadmin@example.com"):
        ids = {p["id"] for p in tools.list_projects()["projects"]}
        assert p2.id in ids
        assert tools.get_schedule(p2.id)["ok"]
