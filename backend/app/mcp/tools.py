"""MCP tool implementations. Each opens a session, calls the shared service
layer, and returns plain JSON-serialisable dicts. Engine errors (cycles, date
conflicts) are converted to structured error payloads the chat agent surfaces.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.db.session import session_scope
from app.engine.errors import CircularDependencyError, DateConflictError
from app.services import project_service, report_service, scheduling_service

ACTOR = "chat"


def _task_dict(task) -> dict[str, Any]:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "name": task.name,
        "wbs": task.wbs,
        "duration_days": task.duration_days,
        "percent_complete": task.percent_complete,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "is_milestone": task.is_milestone,
        "actual_start": _iso(task.actual_start),
        "actual_finish": _iso(task.actual_finish),
        "planned_start": _iso(task.planned_start),
        "planned_finish": _iso(task.planned_finish),
        "total_float": task.total_float,
        "is_critical": task.is_critical,
    }


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


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
        return {
            "ok": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "planned_start": _iso(project.planned_start),
                "planned_finish": _iso(project.planned_finish),
            },
            "tasks": [_task_dict(t) for t in tasks],
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
            return {"ok": True, "task": _task_dict(task)}
        except Exception as exc:  # noqa: BLE001 — converted to structured error
            return _error(exc)


def update_task(task_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    with session_scope() as s:
        try:
            task, _ = scheduling_service.update_task(s, task_id, fields, actor=ACTOR)
            return {"ok": True, "task": _task_dict(task)}
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
        tasks = project_service.get_critical_path(s, project_id)
        return {"ok": True, "critical_path": [_task_dict(t) for t in tasks]}


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
