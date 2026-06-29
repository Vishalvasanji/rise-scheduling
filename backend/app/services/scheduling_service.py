"""The single write/recalc path. Every mutation — from chat (MCP) or web (API) —
flows through here: mutate -> recalculate the whole project schedule -> validate
(cycle / date conflict) -> persist computed fields -> audit, all in one
transaction. If the engine rejects the result, the transaction rolls back and
nothing is persisted.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.engine import compute_schedule
from app.engine.types import (
    DependencyType,
    ScheduleDependency,
    ScheduleResult,
    ScheduleTask,
)
from app.models import Dependency, Task
from app.repositories import (
    audit_repo,
    dependency_repo,
    project_repo,
    task_repo,
)

# Fields a client is allowed to write on a task (everything else is computed).
WRITABLE_TASK_FIELDS = {
    "name",
    "wbs",
    "trade",
    "duration_days",
    "percent_complete",
    "status",
    "is_milestone",
    "actual_start",
    "actual_finish",
    "start_no_earlier_than",
    "external_ref",
    "procore_id",
}


# ---- ORM <-> engine mapping --------------------------------------------------

def _to_engine_tasks(tasks: list[Task]) -> list[ScheduleTask]:
    return [
        ScheduleTask(
            id=t.id,
            duration_days=0 if t.is_milestone else int(t.duration_days or 0),
            is_milestone=bool(t.is_milestone),
            actual_start=t.actual_start,
            actual_finish=t.actual_finish,
            start_no_earlier_than=t.start_no_earlier_than,
            wbs=t.wbs,
        )
        for t in tasks
    ]


def _to_engine_deps(deps: list[Dependency]) -> list[ScheduleDependency]:
    return [
        ScheduleDependency(
            predecessor_id=d.predecessor_id,
            successor_id=d.successor_id,
            type=DependencyType(d.type if isinstance(d.type, str) else d.type.value),
            lag_days=int(d.lag_days or 0),
        )
        for d in deps
    ]


def _recalc_and_persist(session: Session, project_id: int) -> ScheduleResult:
    """Run the engine for one project and write computed fields back. Raises
    CircularDependencyError / DateConflictError (caller rolls back)."""
    project = project_repo.get(session, project_id)
    if project is None:
        raise ValueError(f"Unknown project {project_id}")
    tasks = task_repo.list_for_project(session, project_id)
    deps = dependency_repo.list_for_project(session, project_id)

    result = compute_schedule(
        _to_engine_tasks(tasks), _to_engine_deps(deps), project.anchor_date
    )

    task_repo.bulk_update_computed(session, tasks, result.tasks)
    dependency_repo.set_critical_flags(session, deps, result.critical_dependencies)
    project_repo.update_dates(
        session, project_id, result.project_start, result.project_finish
    )
    return result


def recalculate(session: Session, project_id: int, actor: str = "system") -> ScheduleResult:
    """Recompute and persist a project's schedule without other mutations."""
    try:
        result = _recalc_and_persist(session, project_id)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


# ---- mutations (each recalculates + audits in one transaction) ---------------

def create_task(
    session: Session, project_id: int, fields: dict, actor: str = "system"
) -> tuple[Task, ScheduleResult]:
    clean = {k: v for k, v in fields.items() if k in WRITABLE_TASK_FIELDS}
    try:
        task = task_repo.create(session, project_id=project_id, **clean)
        result = _recalc_and_persist(session, project_id)
        audit_repo.record(
            session, actor=actor, action="create", entity_type="task",
            entity_id=task.id, project_id=project_id,
            summary=f"Created task '{task.name}'", after=clean,
        )
        session.commit()
        return task, result
    except Exception:
        session.rollback()
        raise


def update_task(
    session: Session, task_id: int, fields: dict, actor: str = "system"
) -> tuple[Task, ScheduleResult]:
    existing = task_repo.get(session, task_id)
    if existing is None:
        raise ValueError(f"Unknown task {task_id}")
    project_id = existing.project_id
    before = {k: getattr(existing, k) for k in fields if k in WRITABLE_TASK_FIELDS}
    clean = {k: v for k, v in fields.items() if k in WRITABLE_TASK_FIELDS}
    try:
        task = task_repo.update(session, task_id, clean)
        result = _recalc_and_persist(session, project_id)
        audit_repo.record(
            session, actor=actor, action="update", entity_type="task",
            entity_id=task_id, project_id=project_id,
            summary=f"Updated task '{task.name}'", before=before, after=clean,
        )
        session.commit()
        return task, result
    except Exception:
        session.rollback()
        raise


def delete_task(session: Session, task_id: int, actor: str = "system") -> ScheduleResult:
    existing = task_repo.get(session, task_id)
    if existing is None:
        raise ValueError(f"Unknown task {task_id}")
    project_id = existing.project_id
    name = existing.name
    try:
        task_repo.delete(session, task_id)
        result = _recalc_and_persist(session, project_id)
        audit_repo.record(
            session, actor=actor, action="delete", entity_type="task",
            entity_id=task_id, project_id=project_id, summary=f"Deleted task '{name}'",
        )
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def create_dependency(
    session: Session,
    predecessor_id: int,
    successor_id: int,
    dep_type: str = "FS",
    lag_days: int = 0,
    actor: str = "system",
) -> tuple[Dependency, ScheduleResult]:
    pred = task_repo.get(session, predecessor_id)
    succ = task_repo.get(session, successor_id)
    if pred is None or succ is None:
        raise ValueError("Both predecessor and successor tasks must exist")
    project_id = succ.project_id
    try:
        dependency = dependency_repo.create(
            session,
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            type=DependencyType(dep_type).value,
            lag_days=lag_days,
        )
        result = _recalc_and_persist(session, project_id)  # rejects cycles
        audit_repo.record(
            session, actor=actor, action="create", entity_type="dependency",
            entity_id=dependency.id, project_id=project_id,
            summary=f"Linked {predecessor_id} -> {successor_id} ({dep_type}{_fmt_lag(lag_days)})",
        )
        session.commit()
        return dependency, result
    except Exception:
        session.rollback()
        raise


def delete_dependency(
    session: Session, dependency_id: int, actor: str = "system"
) -> ScheduleResult:
    dependency = dependency_repo.get(session, dependency_id)
    if dependency is None:
        raise ValueError(f"Unknown dependency {dependency_id}")
    succ = task_repo.get(session, dependency.successor_id)
    project_id = succ.project_id if succ else None
    try:
        dependency_repo.delete(session, dependency_id)
        result = _recalc_and_persist(session, project_id)
        audit_repo.record(
            session, actor=actor, action="delete", entity_type="dependency",
            entity_id=dependency_id, project_id=project_id,
            summary=f"Removed dependency {dependency_id}",
        )
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def _fmt_lag(lag: int) -> str:
    if lag == 0:
        return ""
    return f"{lag:+d}"


# Re-export for callers that want the date type without importing datetime.
__all__ = [
    "create_task", "update_task", "delete_task",
    "create_dependency", "delete_dependency", "recalculate",
    "WRITABLE_TASK_FIELDS", "date",
]
