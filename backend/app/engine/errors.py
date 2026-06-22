"""Engine error types. Raised during ``compute_schedule`` and surfaced by the
service layer as HTTP 4xx (API) or structured tool errors (MCP)."""

from __future__ import annotations


class SchedulingError(Exception):
    """Base class for all scheduling-engine errors."""


class CircularDependencyError(SchedulingError):
    """A dependency cycle was detected; the schedule cannot be computed.

    ``cycle`` is the ordered list of task ids forming the cycle, e.g.
    ``[A, B, C, A]``, so callers can show exactly which edges to remove.
    """

    def __init__(self, cycle: list[int]) -> None:
        self.cycle = cycle
        path = " -> ".join(str(t) for t in cycle)
        super().__init__(f"Circular dependency detected: {path}")


class DateConflictError(SchedulingError):
    """A task's actual/planned dates are internally inconsistent.

    ``task_id`` identifies the offending task; ``reason`` is human-readable.
    """

    def __init__(self, task_id: int, reason: str) -> None:
        self.task_id = task_id
        self.reason = reason
        super().__init__(f"Date conflict on task {task_id}: {reason}")
