"""Pending "what-if" proposal endpoints.

One in-flight proposal per project, shared by chat (MCP) and the web app. GET
returns the proposed (computed) schedule plus a per-task diff, or ``null`` when
nothing is pending; apply replays it for real; discard clears it. Engine errors
(cycle/date conflict) surface through the global handlers in ``api/main.py``."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import ActorDep, SessionDep
from app.schemas.project import ProposalCreate, ProposalOut, ScheduleOut
from app.services import project_service, proposal_service

router = APIRouter(prefix="/projects/{project_id}/proposal", tags=["proposals"])


def _require_project(session: SessionDep, project_id: int) -> None:
    if project_service.get_project(session, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("", response_model=ProposalOut | None)
def get_proposal(project_id: int, session: SessionDep):
    """The pending proposal with its computed schedule + diff, or null."""
    _require_project(session, project_id)
    return proposal_service.get_pending(session, project_id)


@router.post("", response_model=ProposalOut)
def set_proposal(
    project_id: int, payload: ProposalCreate, session: SessionDep, actor: ActorDep
):
    """Stage a what-if proposal (validated via a dry-run; invalid → 4xx)."""
    _require_project(session, project_id)
    return proposal_service.set_pending(
        session, project_id, payload.mutations, summary=payload.summary, actor=actor
    )


@router.post("/apply", response_model=ScheduleOut)
def apply_proposal(project_id: int, session: SessionDep, actor: ActorDep):
    """Apply the pending proposal for real and return the new schedule."""
    _require_project(session, project_id)
    schedule = proposal_service.apply_pending(session, project_id, actor=actor)
    if schedule is None:
        raise HTTPException(status_code=404, detail="No pending proposal")
    return schedule


@router.post("/discard", status_code=204)
def discard_proposal(project_id: int, session: SessionDep):
    """Discard the pending proposal (no-op if none)."""
    _require_project(session, project_id)
    proposal_service.discard_pending(session, project_id)
