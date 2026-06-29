"""Reporting endpoints (leadership digest, slippage, what-changed)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.authz import assert_project_access
from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/leadership-digest")
def leadership_digest(session: SessionDep, _admin: AdminDep):
    # Aggregates every project → admin only.
    return report_service.leadership_digest(session)


@router.get("/slippage")
def slippage(session: SessionDep, user: CurrentUserDep, project_id: int | None = None):
    if project_id is None:
        if user.role != "admin":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Specify a project you have access to"
            )
    else:
        assert_project_access(session, user, project_id)
    return report_service.slippage_report(session, project_id)


@router.get("/what-changed/{project_id}")
def what_changed(project_id: int, session: SessionDep, user: CurrentUserDep, limit: int = 25):
    assert_project_access(session, user, project_id)
    return report_service.what_changed(session, project_id, limit=limit)
