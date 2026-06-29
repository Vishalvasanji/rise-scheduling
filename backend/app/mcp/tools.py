"""MCP tool implementations. Each opens a session, calls the shared service
layer, and returns plain JSON-serialisable dicts. Engine errors (cycles, date
conflicts) are converted to structured error payloads the chat agent surfaces.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.db.session import session_scope
from app.engine.errors import CircularDependencyError, DateConflictError
from app.schemas.project import ProposalOut, TaskChange
from app.services import (
    project_service,
    proposal_service,
    report_service,
    scheduling_service,
)

ACTOR = "chat"


def _wbs_label_path(wbs: str | None, labels: dict[str, Any] | None) -> str | None:
    """Resolve a task's WBS to its labeled group path so chat can refer to a task
    by its phase/building names, not the raw code. e.g. WBS ``"2.2.5"`` with the
    project's ``wbs_labels`` -> ``"Phase 2 / Building 13"``. Each proper prefix
    (``"2"``, ``"2.2"``) is a group level; a prefix with no label falls back to the
    raw code. Returns None for an empty/ungrouped WBS."""
    if not wbs:
        return None
    segs = wbs.split(".")
    parts = [
        (labels or {}).get(".".join(segs[:i]), ".".join(segs[:i]))
        for i in range(1, len(segs))
    ]
    return " / ".join(parts) if parts else None


def _task_dict(task, labels: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "name": task.name,
        "wbs": task.wbs,
        # Human-readable group path (phase / building) from the project's labels.
        "group": _wbs_label_path(task.wbs, labels),
        "building": task.building,
        "duration_days": task.duration_days,
        "percent_complete": task.percent_complete,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "is_milestone": task.is_milestone,
        "actual_start": _iso(task.actual_start),
        "actual_finish": _iso(task.actual_finish),
        "start_no_earlier_than": _iso(task.start_no_earlier_than),
        "planned_start": _iso(task.planned_start),
        "planned_finish": _iso(task.planned_finish),
        "total_float": task.total_float,
        "is_critical": task.is_critical,
    }


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _project_labels(session, project_id: int) -> dict[str, Any] | None:
    """The project's WBS-prefix -> name map, or None."""
    project = project_service.get_project(session, project_id)
    return project.wbs_labels if project else None


def _error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, CircularDependencyError):
        return {
            "ok": False, "error": "circular_dependency",
            "cycle": exc.cycle, "message": str(exc),
        }
    if isinstance(exc, DateConflictError):
        return {"ok": False, "error": "date_conflict", "task_id": exc.task_id, "message": str(exc)}
    return {"ok": False, "error": "bad_request", "message": str(exc)}


def list_projects() -> dict[str, Any]:
    with session_scope() as s:
        projects = project_service.list_projects(s)
        return {
            "ok": True,
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "deal_type": p.deal_type,
                    "units": p.units,
                    "stage": p.stage,
                    "planned_start": _iso(p.planned_start),
                    "planned_finish": _iso(p.planned_finish),
                    "wbs_labels": p.wbs_labels,
                }
                for p in projects
            ],
        }


def get_schedule(project_id: int) -> dict[str, Any]:
    with session_scope() as s:
        result = project_service.get_schedule(s, project_id)
        if result is None:
            return {"ok": False, "error": "not_found", "message": f"No project {project_id}"}
        project, tasks, deps = result
        labels = project.wbs_labels
        return {
            "ok": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "planned_start": _iso(project.planned_start),
                "planned_finish": _iso(project.planned_finish),
                # WBS-prefix -> name map (e.g. "2.2" -> "Building 13"). Use these
                # names (or each task's `group`) when referring to phases/buildings.
                "wbs_labels": labels,
            },
            "tasks": [_task_dict(t, labels) for t in tasks],
            "dependencies": [
                {
                    "id": d.id,
                    "predecessor_id": d.predecessor_id,
                    "successor_id": d.successor_id,
                    "type": d.type.value if hasattr(d.type, "value") else d.type,
                    "lag_days": d.lag_days,
                    "is_critical": d.is_critical,
                }
                for d in deps
            ],
        }


def create_task(project_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    with session_scope() as s:
        try:
            task, _ = scheduling_service.create_task(s, project_id, fields, actor=ACTOR)
            return {"ok": True, "task": _task_dict(task, _project_labels(s, project_id))}
        except Exception as exc:  # noqa: BLE001 — converted to structured error
            return _error(exc)


def update_task(task_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    with session_scope() as s:
        try:
            task, _ = scheduling_service.update_task(s, task_id, fields, actor=ACTOR)
            return {"ok": True, "task": _task_dict(task, _project_labels(s, task.project_id))}
        except Exception as exc:  # noqa: BLE001
            return _error(exc)


def delete_task(task_id: int) -> dict[str, Any]:
    with session_scope() as s:
        try:
            scheduling_service.delete_task(s, task_id, actor=ACTOR)
            return {"ok": True, "deleted": task_id}
        except Exception as exc:  # noqa: BLE001
            return _error(exc)


def create_dependency(
    predecessor_id: int, successor_id: int, dep_type: str = "FS", lag_days: int = 0
) -> dict[str, Any]:
    with session_scope() as s:
        try:
            dep, _ = scheduling_service.create_dependency(
                s, predecessor_id, successor_id, dep_type, lag_days, actor=ACTOR
            )
            return {"ok": True, "dependency_id": dep.id}
        except Exception as exc:  # noqa: BLE001
            return _error(exc)


def get_critical_path(project_id: int) -> dict[str, Any]:
    with session_scope() as s:
        labels = _project_labels(s, project_id)
        tasks = project_service.get_critical_path(s, project_id)
        return {"ok": True, "critical_path": [_task_dict(t, labels) for t in tasks]}


# ---- proposals (dry-run "what-if" changes the user reviews before applying) --

def _change_line(c: TaskChange) -> str:
    if c.change_type == "new":
        p = c.proposed
        span = f" ({_iso(p.planned_start)}→{_iso(p.planned_finish)})" if p else ""
        return f"+ NEW '{c.name}'{span}"
    if c.change_type == "removed":
        return f"- REMOVED '{c.name}'"
    cur, prop = c.current, c.proposed
    if c.change_type == "moved" and cur and prop:
        return (
            f"~ MOVED '{c.name}': {_iso(cur.planned_finish)} → "
            f"{_iso(prop.planned_finish)}"
        )
    return f"~ MODIFIED '{c.name}'"


def _proposal_payload(proposal: ProposalOut) -> dict[str, Any]:
    proj = proposal.schedule.project
    return {
        "summary": proposal.summary,
        "actor": proposal.actor,
        "created_at": proposal.created_at,
        "project_finish": _iso(proj.planned_finish),
        "change_count": len(proposal.changes),
        "step_count": len(proposal.steps),
        "steps": [
            {"summary": s.summary, "change_count": s.change_count}
            for s in proposal.steps
        ],
        "changes": [
            {
                "task_id": c.task_id,
                "name": c.name,
                "change_type": c.change_type,
                "current": c.current.model_dump(mode="json") if c.current else None,
                "proposed": c.proposed.model_dump(mode="json") if c.proposed else None,
            }
            for c in proposal.changes
        ],
        "diff_text": [_change_line(c) for c in proposal.changes],
    }


def propose_changes(
    project_id: int,
    mutations: list[dict[str, Any]],
    summary: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Stage a what-if proposal and return its cumulative diff (nothing applied
    yet). Appends to any pending proposal by default so the user can keep stacking
    changes; pass ``replace=True`` to start over."""
    with session_scope() as s:
        try:
            proposal = proposal_service.set_pending(
                s, project_id, mutations, summary=summary, actor=ACTOR, replace=replace
            )
            return {"ok": True, "proposal": _proposal_payload(proposal)}
        except Exception as exc:  # noqa: BLE001 — converted to structured error
            return _error(exc)


def undo_last_change(project_id: int) -> dict[str, Any]:
    """Remove the most recently staged step from the pending proposal."""
    with session_scope() as s:
        try:
            proposal = proposal_service.undo_last(s, project_id, actor=ACTOR)
            if proposal is None:
                return {"ok": True, "pending": False}
            return {"ok": True, "pending": True, "proposal": _proposal_payload(proposal)}
        except Exception as exc:  # noqa: BLE001
            return _error(exc)


def get_proposal(project_id: int) -> dict[str, Any]:
    """Return the project's pending proposal diff, or ``pending: False``."""
    with session_scope() as s:
        proposal = proposal_service.get_pending(s, project_id)
        if proposal is None:
            return {"ok": True, "pending": False}
        return {"ok": True, "pending": True, "proposal": _proposal_payload(proposal)}


def apply_proposal(project_id: int) -> dict[str, Any]:
    """Apply the pending proposal for real and clear it."""
    with session_scope() as s:
        try:
            schedule = proposal_service.apply_pending(s, project_id, actor=ACTOR)
            if schedule is None:
                return {"ok": False, "error": "not_found", "message": "No pending proposal"}
            return {
                "ok": True,
                "applied": True,
                "project_finish": _iso(schedule.project.planned_finish),
            }
        except Exception as exc:  # noqa: BLE001
            return _error(exc)


def discard_proposal(project_id: int) -> dict[str, Any]:
    """Discard the pending proposal without applying it."""
    with session_scope() as s:
        discarded = proposal_service.discard_pending(s, project_id)
        return {"ok": True, "discarded": discarded}


def generate_report(scope: str, report_type: str) -> dict[str, Any]:
    """scope: 'all' or a project id (as string). report_type: leadership_digest |
    slippage | what_changed."""
    with session_scope() as s:
        project_id = int(scope) if scope.isdigit() else None
        if report_type == "leadership_digest":
            return {"ok": True, "report": report_service.leadership_digest(s)}
        if report_type == "slippage":
            return {"ok": True, "report": report_service.slippage_report(s, project_id)}
        if report_type == "what_changed":
            if project_id is None:
                return {
                    "ok": False, "error": "bad_request",
                    "message": "what_changed needs a project id",
                }
            return {"ok": True, "report": report_service.what_changed(s, project_id)}
        return {
            "ok": False, "error": "bad_request",
            "message": f"Unknown report type {report_type}",
        }
