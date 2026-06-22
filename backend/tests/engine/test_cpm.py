"""CPM correctness across all four dependency types, lag, milestones, float,
negative lag, and cycle rejection."""

from datetime import date

import pytest

from app.engine import compute_schedule
from app.engine.calendar import index_to_date
from app.engine.errors import CircularDependencyError, DateConflictError
from app.engine.types import DependencyType as DT
from app.engine.types import ScheduleDependency, ScheduleTask

ANCHOR = date(2026, 6, 22)  # Monday


def task(tid, dur, milestone=False, actual_start=None, wbs=None):
    return ScheduleTask(
        id=tid, duration_days=dur, is_milestone=milestone,
        actual_start=actual_start, wbs=wbs,
    )


def dep(p, s, t=DT.FS, lag=0):
    return ScheduleDependency(predecessor_id=p, successor_id=s, type=t, lag_days=lag)


def idx(result, tid):
    """Recover the early-start working-day index from a task result."""
    from app.engine import calendar
    return calendar.date_to_index(result.tasks[tid].early_start_date, ANCHOR)


# ---- dependency types --------------------------------------------------------

def test_fs_chain():
    tasks = [task(1, 5), task(2, 3)]
    res = compute_schedule(tasks, [dep(1, 2, DT.FS)], ANCHOR)
    # task1: ES=0 EF=5; task2 FS: ES=5
    assert idx(res, 2) == 5


def test_fs_with_lag():
    res = compute_schedule([task(1, 5), task(2, 3)], [dep(1, 2, DT.FS, lag=2)], ANCHOR)
    assert idx(res, 2) == 7


def test_ss_with_lag():
    res = compute_schedule([task(1, 10), task(2, 3)], [dep(1, 2, DT.SS, lag=4)], ANCHOR)
    assert idx(res, 2) == 4  # successor starts 4 working days after predecessor start


def test_ff_with_lag():
    # FF+0: successor finishes when predecessor finishes. pred EF=10, succ dur=3 => succ ES=7
    res = compute_schedule([task(1, 10), task(2, 3)], [dep(1, 2, DT.FF, lag=0)], ANCHOR)
    assert idx(res, 2) == 7


def test_sf_relationship():
    # SF: S.EF = P.ES + lag. pred ES=0, lag=8, succ dur=3 => succ EF=8 => succ ES=5
    res = compute_schedule([task(1, 4), task(2, 3)], [dep(1, 2, DT.SF, lag=8)], ANCHOR)
    assert idx(res, 2) == 5


# ---- negative lag (FF-30 marketing-before-CO) --------------------------------

def test_ff_negative_lag_overlaps_predecessor():
    # CO is the predecessor here in FF sense: marketing FF-30 before CO means
    # marketing.EF = CO.EF - 30. Model CO(dur 1) -> marketing(dur 20) FF-30.
    co = task(1, 1)
    marketing = task(2, 20)
    res = compute_schedule([co, marketing], [dep(1, 2, DT.FF, lag=-30)], ANCHOR)
    # co EF=1; marketing EF = 1 - 30 = -29; marketing ES = -29 - 20 = -49
    assert idx(res, 2) == -49
    # marketing finishes (EF index -29) well before co finishes (EF index 1): overlap/negative
    assert res.tasks[2].early_finish_date < res.tasks[1].early_finish_date


# ---- milestones (zero duration) ----------------------------------------------

def test_milestone_zero_duration():
    t1 = task(1, 5)
    ms = task(2, 0, milestone=True)
    res = compute_schedule([t1, ms], [dep(1, 2, DT.FS)], ANCHOR)
    # milestone ES==EF index 5; start date == finish date
    assert res.tasks[2].early_start_date == res.tasks[2].early_finish_date
    assert idx(res, 2) == 5


# ---- float & parallel converging workstreams ---------------------------------

def test_parallel_branches_float_and_critical():
    # Two parallel chains feeding a join. Long chain is critical (float 0),
    # short chain has positive float.
    start = task(1, 0, milestone=True)
    long_a = task(2, 10)
    short_b = task(3, 3)
    join = task(4, 2)
    deps = [
        dep(1, 2, DT.FS), dep(1, 3, DT.FS),
        dep(2, 4, DT.FS), dep(3, 4, DT.FS),
    ]
    res = compute_schedule([start, long_a, short_b, join], deps, ANCHOR)
    assert res.tasks[2].is_critical          # long branch critical
    assert res.tasks[2].total_float == 0
    assert not res.tasks[3].is_critical      # short branch has slack
    assert res.tasks[3].total_float == 7     # 10 - 3
    assert res.tasks[3].free_float == 7
    assert res.critical_path[0] == 1 and res.critical_path[-1] == 4


# ---- slipped task surfaces negative float downstream -------------------------

def test_actual_start_pins_and_pushes_downstream():
    t1 = task(1, 5)
    t2 = task(2, 5, actual_start=ANCHOR)  # forced to start at anchor (index 0)
    # t2 depends on t1 FS but its actual start pins it earlier than planned
    res = compute_schedule([t1, t2], [dep(1, 2, DT.FS)], ANCHOR)
    assert idx(res, 2) == 0  # actual wins over the FS constraint


# ---- cycle rejection ---------------------------------------------------------

def test_circular_dependency_rejected():
    tasks = [task(1, 1), task(2, 1), task(3, 1)]
    deps = [dep(1, 2), dep(2, 3), dep(3, 1)]
    with pytest.raises(CircularDependencyError) as exc:
        compute_schedule(tasks, deps, ANCHOR)
    assert exc.value.cycle[0] == exc.value.cycle[-1]  # closed loop


def test_date_conflict_rejected():
    t = task(1, 5)
    t.actual_start = date(2026, 6, 26)
    t.actual_finish = date(2026, 6, 22)  # before start
    with pytest.raises(DateConflictError):
        compute_schedule([t], [], ANCHOR)


# ---- roll-up -----------------------------------------------------------------

def test_project_bounds_and_summary_rows():
    tasks = [task(1, 5, wbs="D.1"), task(2, 3, wbs="D.2")]
    res = compute_schedule(tasks, [dep(1, 2, DT.FS)], ANCHOR)
    assert res.project_start == index_to_date(0, ANCHOR)
    # last task EF index 8 -> last working day index 7
    assert res.project_finish == index_to_date(7, ANCHOR)
    assert "D" in res.summary_rows
    d_start, d_finish = res.summary_rows["D"]
    assert d_start == res.project_start
    assert d_finish == res.project_finish
