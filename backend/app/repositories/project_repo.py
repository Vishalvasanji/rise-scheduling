"""Project data access."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project


def list_all(session: Session) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.id)))


def get(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)


def create(session: Session, **fields) -> Project:
    project = Project(**fields)
    session.add(project)
    session.flush()
    return project


def update_dates(
    session: Session, project_id: int, start: date | None, finish: date | None
) -> None:
    project = session.get(Project, project_id)
    if project is not None:
        project.planned_start = start
        project.planned_finish = finish
