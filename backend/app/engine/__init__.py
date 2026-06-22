"""Pure scheduling engine — CPM, working-day calendar, roll-up, validation.

This package imports NOTHING from SQLAlchemy, FastAPI, or the rest of the app.
It operates on plain dataclasses (`types.py`) so it can be unit-tested in
isolation and reused identically by the API and the MCP server through the
service layer.
"""

from app.engine.cpm import compute_schedule
from app.engine.errors import (
    CircularDependencyError,
    DateConflictError,
    SchedulingError,
)
from app.engine.types import (
    DependencyType,
    ScheduleDependency,
    ScheduleResult,
    ScheduleTask,
)

__all__ = [
    "compute_schedule",
    "CircularDependencyError",
    "DateConflictError",
    "SchedulingError",
    "DependencyType",
    "ScheduleDependency",
    "ScheduleResult",
    "ScheduleTask",
]
