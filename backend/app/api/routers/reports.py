"""Reporting endpoints (leadership digest, slippage, what-changed)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/leadership-digest")
def leadership_digest(session: SessionDep):
    return report_service.leadership_digest(session)


@router.get("/slippage")
def slippage(session: SessionDep, project_id: int | None = None):
    return report_service.slippage_report(session, project_id)


@router.get("/what-changed/{project_id}")
def what_changed(project_id: int, session: SessionDep, limit: int = 25):
    return report_service.what_changed(session, project_id, limit=limit)
