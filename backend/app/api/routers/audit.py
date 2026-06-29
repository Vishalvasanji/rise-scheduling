"""Change-activity (audit) read endpoints. Every write already records an audit
entry via the service layer; this exposes them for the Activity view."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.authz import assert_project_access
from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.repositories import audit_repo
from app.schemas.audit import AuditOut

router = APIRouter(tags=["activity"])


@router.get("/projects/{project_id}/audit", response_model=list[AuditOut])
def project_activity(
    project_id: int, session: SessionDep, user: CurrentUserDep, limit: int = 100
):
    """Recent changes to a project (who did what), newest first. Access-gated."""
    assert_project_access(session, user, project_id)
    return audit_repo.list_for_project(session, project_id, limit=limit)


@router.get("/audit", response_model=list[AuditOut])
def all_activity(session: SessionDep, _admin: AdminDep, limit: int = 200):
    """Recent changes across every project (admin only)."""
    return audit_repo.list_recent(session, limit=limit)
