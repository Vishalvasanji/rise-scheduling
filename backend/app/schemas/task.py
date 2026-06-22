"""Task request/response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskStatus


class TaskCreate(BaseModel):
    name: str
    wbs: str | None = None
    duration_days: int = Field(default=0, ge=0)
    percent_complete: float = Field(default=0.0, ge=0, le=100)
    status: TaskStatus = TaskStatus.NOT_STARTED
    is_milestone: bool = False
    actual_start: date | None = None
    actual_finish: date | None = None
    external_ref: str | None = None
    procore_id: str | None = None


class TaskUpdate(BaseModel):
    """All fields optional; only provided fields are written."""

    name: str | None = None
    wbs: str | None = None
    duration_days: int | None = Field(default=None, ge=0)
    percent_complete: float | None = Field(default=None, ge=0, le=100)
    status: TaskStatus | None = None
    is_milestone: bool | None = None
    actual_start: date | None = None
    actual_finish: date | None = None
    external_ref: str | None = None
    procore_id: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    wbs: str | None
    duration_days: int
    percent_complete: float
    status: TaskStatus
    is_milestone: bool
    actual_start: date | None
    actual_finish: date | None
    # Computed by the engine.
    planned_start: date | None
    planned_finish: date | None
    late_start: date | None
    late_finish: date | None
    total_float: int | None
    free_float: int | None
    is_critical: bool
    external_ref: str | None
    procore_id: str | None
