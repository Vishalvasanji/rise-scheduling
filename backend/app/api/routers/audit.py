"""Change-activity (audit) read endpoints. Every write already records an audit
entry via the service layer; this exposes them for the Activity view, enriched with
the actor's name and a descriptive field-level change built from the before/after
snapshots."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from app.api.authz import assert_project_access
from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.models import AuditLog
from app.repositories import audit_repo, user_repo
from app.schemas.audit import AuditOut
from app.services.audit_view import describe_change

router = APIRouter(tags=["activity"])


def _name_map(session) -> dict[str, str]:
    """actor email -> full name, for resolving the Who column to a person's name."""
    return {u.email: u.full_name for u in user_repo.list_all(session) if u.full_name}


def _loads(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _out(entry: AuditLog, name_map: dict[str, str]) -> AuditOut:
    return AuditOut(
        id=entry.id,
        actor=entry.actor,
        actor_name=name_map.get(entry.actor),
        source=entry.source,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        project_id=entry.project_id,
        summary=entry.summary,
        detail=describe_change(
            entry.action, entry.entity_type, entry.summary,
            _loads(entry.before), _loads(entry.after),
        ),
        created_at=entry.created_at,
    )


@router.get("/projects/{project_id}/audit", response_model=list[AuditOut])
def project_activity(
    project_id: int, session: SessionDep, user: CurrentUserDep, limit: int = 100
):
    """Recent changes to a project (who did what), newest first. Access-gated."""
    assert_project_access(session, user, project_id)
    name_map = _name_map(session)
    entries = audit_repo.list_for_project(session, project_id, limit=limit)
    return [_out(e, name_map) for e in entries]


@router.get("/audit", response_model=list[AuditOut])
def all_activity(session: SessionDep, _admin: AdminDep, limit: int = 200):
    """Recent changes across every project (admin only)."""
    name_map = _name_map(session)
    return [_out(e, name_map) for e in audit_repo.list_recent(session, limit=limit)]
