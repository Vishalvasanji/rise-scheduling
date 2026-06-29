"""Plain dataclasses the engine operates on. No DB or framework types here.

CPM arithmetic is done in **integer working-day indices** (anchor = the project's
schedule anchor date). Dates are derived only at the end via ``calendar.py``.
This keeps FS/SS/FF/SF + lag (including negative lag) pure integer math and
sidesteps date-rounding bugs.

Duration convention: ``early_finish = early_start + duration_days`` where ES/EF
are *instants* on the working-day axis. A milestone has duration 0, so EF == ES
falls out with no special case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class DependencyType(str, Enum):
    FS = "FS"  # finish-to-start
    SS = "SS"  # start-to-start
    FF = "FF"  # finish-to-finish
    SF = "SF"  # start-to-finish


@dataclass
class ScheduleTask:
    """Input + computed CPM fields for a single task (working-day index space)."""

    id: int
    duration_days: int  # working days; a milestone is 0
    is_milestone: bool = False
    wbs: str | None = None  # hierarchy code (e.g. "D.4") for summary roll-up
    # Actuals pin the bar when present (forward pass uses them as a hard start).
    actual_start: date | None = None
    actual_finish: date | None = None
    # "Start no earlier than" planning constraint: a floor on early start (the task
    # can't start before this date, but predecessors are still respected). Applied
    # only when there is no actual_start. Lets the field reschedule a future start
    # without logging a fake actual.
    start_no_earlier_than: date | None = None

    # Computed by the CPM passes (working-day indices relative to the anchor).
    early_start: int = 0
    early_finish: int = 0
    late_start: int = 0
    late_finish: int = 0
    total_float: int = 0
    free_float: int = 0
    is_critical: bool = False


@dataclass
class ScheduleDependency:
    """A typed, lagged precedence edge. ``lag_days`` is in working days and may
    be negative (e.g. an FF-30 marketing-before-CO relationship)."""

    predecessor_id: int
    successor_id: int
    type: DependencyType = DependencyType.FS
    lag_days: int = 0
    is_critical: bool = False  # computed: on the critical path (binding + both endpoints critical)


@dataclass
class TaskScheduleResult:
    """Per-task CPM output with dates mapped back from index space."""

    id: int
    early_start_date: date
    early_finish_date: date
    late_start_date: date
    late_finish_date: date
    total_float: int
    free_float: int
    is_critical: bool


@dataclass
class ScheduleResult:
    """The full output of ``compute_schedule``."""

    tasks: dict[int, TaskScheduleResult]
    critical_path: list[int]  # ordered task ids along one critical chain
    critical_dependencies: set[tuple[int, int]]  # (predecessor_id, successor_id) pairs
    project_start: date | None
    project_finish: date | None
    # WBS-summary roll-up: wbs code -> (start, finish)
    summary_rows: dict[str, tuple[date, date]] = field(default_factory=dict)
