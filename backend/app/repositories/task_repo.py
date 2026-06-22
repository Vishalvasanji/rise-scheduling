"""Task data access, including the bulk write of engine-computed fields."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.types import TaskScheduleResult
from app.models import Task


def list_for_project(session: Session, project_id: int) -> list[Task]:
    return list(
        session.scalars(
            select(Task).where(Task.project_id == project_id).order_by(Task.id)
        )
    )


def get(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def create(session: Session, **fields) -> Task:
    task = Task(**fields)
    session.add(task)
    session.flush()
    return task


def update(session: Session, task_id: int, fields: dict) -> Task | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    for key, value in fields.items():
        setattr(task, key, value)
    session.flush()
    return task


def delete(session: Session, task_id: int) -> bool:
    task = session.get(Task, task_id)
    if task is None:
        return False
    session.delete(task)
    session.flush()
    return True


def bulk_update_computed(
    session: Session, tasks: list[Task], results: dict[int, TaskScheduleResult]
) -> None:
    """Write the engine's computed CPM fields back onto the ORM tasks."""
    for task in tasks:
        r = results.get(task.id)
        if r is None:
            continue
        task.planned_start = r.early_start_date
        task.planned_finish = r.early_finish_date
        task.late_start = r.late_start_date
        task.late_finish = r.late_finish_date
        task.total_float = r.total_float
        task.free_float = r.free_float
        task.is_critical = r.is_critical
