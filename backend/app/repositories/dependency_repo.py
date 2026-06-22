"""Dependency data access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dependency, Task


def list_for_project(session: Session, project_id: int) -> list[Dependency]:
    """All dependencies whose successor belongs to the project (predecessor and
    successor always share a project in the pilot model)."""
    task_ids = select(Task.id).where(Task.project_id == project_id)
    return list(
        session.scalars(
            select(Dependency).where(Dependency.successor_id.in_(task_ids))
        )
    )


def get(session: Session, dependency_id: int) -> Dependency | None:
    return session.get(Dependency, dependency_id)


def create(session: Session, **fields) -> Dependency:
    dependency = Dependency(**fields)
    session.add(dependency)
    session.flush()
    return dependency


def delete(session: Session, dependency_id: int) -> bool:
    dependency = session.get(Dependency, dependency_id)
    if dependency is None:
        return False
    session.delete(dependency)
    session.flush()
    return True


def set_critical_flags(
    session: Session,
    dependencies: list[Dependency],
    critical_edges: set[tuple[int, int]],
) -> None:
    for dep in dependencies:
        dep.is_critical = (dep.predecessor_id, dep.successor_id) in critical_edges
