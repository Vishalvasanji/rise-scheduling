"""On-demand reports (SCOPE §5.5). Basic in Phase 1: leadership digest, slippage,
and what-changed. Reads persisted schedule + audit data; no recompute needed."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Task
from app.repositories import audit_repo, project_repo, task_repo


def leadership_digest(session: Session) -> dict:
    """Cross-project summary: counts, dates, and critical-task totals."""
    projects = project_repo.list_all(session)
    rows = []
    for p in projects:
        tasks = task_repo.list_for_project(session, p.id)
        rows.append(
            {
                "project_id": p.id,
                "name": p.name,
                "stage": p.stage,
                "units": p.units,
                "planned_start": p.planned_start,
                "planned_finish": p.planned_finish,
                "task_count": len(tasks),
                "critical_count": sum(1 for t in tasks if t.is_critical),
                "percent_complete": _avg_complete(tasks),
                "slipped_count": sum(1 for t in tasks if _is_slipped(t)),
            }
        )
    return {"type": "leadership_digest", "generated": date.today(), "projects": rows}


def slippage_report(session: Session, project_id: int | None = None) -> dict:
    """Tasks running behind: negative total float, or actuals past plan."""
    projects = (
        [project_repo.get(session, project_id)]
        if project_id is not None
        else project_repo.list_all(session)
    )
    items = []
    for p in projects:
        if p is None:
            continue
        for t in task_repo.list_for_project(session, p.id):
            if _is_slipped(t):
                items.append(
                    {
                        "project_id": p.id,
                        "project": p.name,
                        "task_id": t.id,
                        "task": t.name,
                        "planned_finish": t.planned_finish,
                        "actual_finish": t.actual_finish,
                        "total_float": t.total_float,
                    }
                )
    return {"type": "slippage", "generated": date.today(), "items": items}


def what_changed(session: Session, project_id: int, limit: int = 25) -> dict:
    """Recent audit entries for a project (the what-changed feed)."""
    entries = audit_repo.list_for_project(session, project_id, limit=limit)
    return {
        "type": "what_changed",
        "project_id": project_id,
        "generated": date.today(),
        "changes": [
            {
                "when": e.created_at,
                "actor": e.actor,
                "action": e.action,
                "entity": e.entity_type,
                "summary": e.summary,
            }
            for e in entries
        ],
    }


def _avg_complete(tasks: list[Task]) -> float:
    if not tasks:
        return 0.0
    return round(sum(t.percent_complete for t in tasks) / len(tasks), 1)


def _is_slipped(task: Task) -> bool:
    if task.total_float is not None and task.total_float < 0:
        return True
    if task.actual_finish and task.planned_finish and task.actual_finish > task.planned_finish:
        return True
    return False
