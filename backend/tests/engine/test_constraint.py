"""The "start no earlier than" constraint is a floor on early start: it delays a
task that would otherwise start earlier, still defers to predecessors, and is
ignored once the task has actually started."""

from datetime import date

from app.engine import compute_schedule
from app.engine.calendar import date_to_index, index_to_date
from app.engine.types import ScheduleDependency, ScheduleTask

ANCHOR = date(2026, 6, 22)  # Monday


def _es_index(res, tid):
    return date_to_index(res.tasks[tid].early_start_date, ANCHOR)


def test_constraint_floors_a_lone_task():
    snet = index_to_date(4, ANCHOR)  # working-day index 4
    res = compute_schedule(
        [ScheduleTask(id=1, duration_days=5, start_no_earlier_than=snet)], [], ANCHOR
    )
    assert _es_index(res, 1) == 4  # floored from 0


def test_constraint_pushes_successors():
    # A(5) -> B(3); without a constraint B starts at index 5.
    snet = index_to_date(8, ANCHOR)
    tasks = [
        ScheduleTask(id=1, duration_days=5),
        ScheduleTask(id=2, duration_days=3, start_no_earlier_than=snet),
    ]
    res = compute_schedule(tasks, [ScheduleDependency(predecessor_id=1, successor_id=2)], ANCHOR)
    assert _es_index(res, 2) == 8  # floored later than the FS-driven 5
    assert res.tasks[2].early_start_date == snet


def test_constraint_earlier_than_predecessor_has_no_effect():
    # Constraint before the FS-driven start (5) must NOT pull the task in.
    snet = index_to_date(2, ANCHOR)
    tasks = [
        ScheduleTask(id=1, duration_days=5),
        ScheduleTask(id=2, duration_days=3, start_no_earlier_than=snet),
    ]
    res = compute_schedule(tasks, [ScheduleDependency(predecessor_id=1, successor_id=2)], ANCHOR)
    assert _es_index(res, 2) == 5  # predecessor still wins


def test_actual_start_overrides_constraint():
    # A started task ignores its constraint (the actual pins it).
    res = compute_schedule(
        [ScheduleTask(
            id=1, duration_days=5,
            actual_start=index_to_date(3, ANCHOR),
            start_no_earlier_than=index_to_date(8, ANCHOR),
        )],
        [],
        ANCHOR,
    )
    assert _es_index(res, 1) == 3  # actual_start wins, not the constraint
