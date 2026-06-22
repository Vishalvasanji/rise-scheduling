"""Project-level reads and creation. Computed schedule fields are persisted by
the scheduling service, so reads here are plain queries."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Dependency, Project, Task
from app.repositories import dependency_repo, project_repo, task_repo


def list_projects(session: Session) -> list[Project]:
    return project_repo.list_all(session)


def get_project(session: Session, project_id: int) -> Project | None:
    return project_repo.get(session, project_id)


def create_project(
    session: Session,
    name: str,
    anchor_date: date,
    deal_type: str | None = None,
    units: int | None = None,
    stage: str | None = None,
) -> Project:
    project = project_repo.create(
        session,
        name=name,
        anchor_date=anchor_date,
        deal_type=deal_type,
        units=units,
        stage=stage,
    )
    session.commit()
    return project


def get_schedule(
    session: Session, project_id: int
) -> tuple[Project, list[Task], list[Dependency]] | None:
    """Return the full schedule (project + tasks + dependencies) for a project."""
    project = project_repo.get(session, project_id)
    if project is None:
        return None
    tasks = task_repo.list_for_project(session, project_id)
    deps = dependency_repo.list_for_project(session, project_id)
    return project, tasks, deps


def get_critical_path(session: Session, project_id: int) -> list[Task]:
    """Critical tasks for a project, ordered by planned start."""
    tasks = task_repo.list_for_project(session, project_id)
    critical = [t for t in tasks if t.is_critical]
    critical.sort(key=lambda t: (t.planned_start or date.max, t.id))
    return critical
