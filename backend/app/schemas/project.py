"""Project + schedule response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.dependency import DependencyOut
from app.schemas.task import TaskOut


class ProjectCreate(BaseModel):
    name: str
    anchor_date: date
    deal_type: str | None = None
    units: int | None = None
    stage: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    deal_type: str | None
    units: int | None
    stage: str | None
    anchor_date: date
    wbs_labels: dict[str, str] | None
    planned_start: date | None
    planned_finish: date | None
    external_ref: str | None
    procore_id: str | None


class ScheduleOut(BaseModel):
    """Full project schedule consumed by the Gantt and task grid."""

    project: ProjectOut
    tasks: list[TaskOut]
    dependencies: list[DependencyOut]
