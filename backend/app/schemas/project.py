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


class ChangeSide(BaseModel):
    planned_start: date | None = None
    planned_finish: date | None = None
    duration_days: int | None = None


class TaskChange(BaseModel):
    """One task's before/after under a proposed change."""

    task_id: int
    name: str
    change_type: str  # new | removed | moved | modified
    current: ChangeSide | None = None
    proposed: ChangeSide | None = None


class ProposalStep(BaseModel):
    """One staged step of a proposal (one ``propose_changes`` call). The proposal
    accumulates steps; the diff/schedule are the cumulative result of all of them."""

    summary: str | None = None
    change_count: int | None = None  # number of mutation ops in this step
    created_at: str | None = None


class ProposalOut(BaseModel):
    """A pending what-if proposal: its metadata, the staged steps, the proposed
    (computed) schedule, and the per-task diff vs the live schedule."""

    summary: str | None = None  # the most recent step's summary
    actor: str | None = None
    created_at: str | None = None
    schedule: ScheduleOut
    changes: list[TaskChange]
    steps: list[ProposalStep] = []


class ProposalCreate(BaseModel):
    """A what-if proposal: an ordered list of mutation ops + an optional summary.

    Each mutation is ``{op, ...}``: ``update_task{task_id, fields}``,
    ``create_task{ref, fields}``, ``delete_task{task_id}``,
    ``create_dependency{predecessor, successor, type?, lag?}`` (endpoints may be a
    real task id or a ``create_task`` ref), ``delete_dependency{dependency_id}``.

    By default this **appends** to any pending proposal (the user keeps stacking
    changes); set ``replace=true`` to discard what's staged and start over."""

    mutations: list[dict]
    summary: str | None = None
    replace: bool = False
