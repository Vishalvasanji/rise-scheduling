"""Critical Path Method over typed, lagged dependencies in working-day space.

All arithmetic is done on integer working-day indices (anchor = the project's
schedule anchor date); dates are mapped back only at the end. Supports FS/SS/FF/SF
with positive or negative lag and zero-duration milestones.
"""

from __future__ import annotations

from datetime import date

from app.engine import calendar
from app.engine.errors import DateConflictError
from app.engine.graph import Graph, build_graph, topological_order
from app.engine.rollup import compute_project_bounds, compute_summary_rows
from app.engine.types import (
    DependencyType,
    ScheduleDependency,
    ScheduleResult,
    ScheduleTask,
    TaskScheduleResult,
)


def _forward_candidate_es(
    dep: ScheduleDependency, pred: ScheduleTask, succ_duration: int
) -> int:
    """Earliest-start index the predecessor imposes on the successor."""
    if dep.type == DependencyType.FS:
        return pred.early_finish + dep.lag_days
    if dep.type == DependencyType.SS:
        return pred.early_start + dep.lag_days
    if dep.type == DependencyType.FF:
        # S.EF = P.EF + lag  =>  S.ES = (P.EF + lag) - S.duration
        return (pred.early_finish + dep.lag_days) - succ_duration
    # SF: S.EF = P.ES + lag  =>  S.ES = (P.ES + lag) - S.duration
    return (pred.early_start + dep.lag_days) - succ_duration


def _backward_candidate_lf(
    dep: ScheduleDependency, succ: ScheduleTask, pred_duration: int
) -> int:
    """Latest-finish index the successor imposes on the predecessor.

    Each relation is the forward equation solved for the predecessor's late
    value; SS/SF yield an LS constraint converted to LF via the predecessor's
    duration.
    """
    if dep.type == DependencyType.FS:
        return succ.late_start - dep.lag_days
    if dep.type == DependencyType.FF:
        return succ.late_finish - dep.lag_days
    if dep.type == DependencyType.SS:
        # P.LS = S.LS - lag  =>  P.LF = (S.LS - lag) + P.duration
        return (succ.late_start - dep.lag_days) + pred_duration
    # SF: P.LS = S.LF - lag  =>  P.LF = (S.LF - lag) + P.duration
    return (succ.late_finish - dep.lag_days) + pred_duration


def _validate_actuals(tasks: list[ScheduleTask]) -> None:
    for t in tasks:
        if t.actual_start and t.actual_finish and t.actual_finish < t.actual_start:
            raise DateConflictError(
                t.id, f"actual_finish ({t.actual_finish}) precedes actual_start ({t.actual_start})"
            )


def _forward_pass(graph: Graph, order: list[int], anchor: date) -> int:
    """Compute early start/finish for every task; return the project end index."""
    project_end = 0
    for node_id in order:
        t = graph.nodes[node_id]
        if t.actual_start is not None:
            es = calendar.date_to_index(t.actual_start, anchor)
        else:
            candidates = [
                _forward_candidate_es(dep, graph.nodes[dep.predecessor_id], t.duration_days)
                for dep in graph.predecessors[node_id]
            ]
            es = max(candidates) if candidates else 0
            # "Start no earlier than" is a floor: predecessors still win when they
            # push the task later; the constraint only delays an otherwise-earlier
            # start. Ignored once the task has actually started (actual_start above).
            if t.start_no_earlier_than is not None:
                es = max(es, calendar.date_to_index(t.start_no_earlier_than, anchor))
        t.early_start = es
        t.early_finish = es + t.duration_days
        project_end = max(project_end, t.early_finish)
    return project_end


def _backward_pass(graph: Graph, order: list[int], project_end: int) -> None:
    """Compute late start/finish for every task (reverse topological order)."""
    for node_id in reversed(order):
        t = graph.nodes[node_id]
        outgoing = graph.successors[node_id]
        if not outgoing:
            lf = project_end
        else:
            lf = min(
                _backward_candidate_lf(dep, graph.nodes[dep.successor_id], t.duration_days)
                for dep in outgoing
            )
        t.late_finish = lf
        t.late_start = lf - t.duration_days


def _compute_float_and_critical(graph: Graph, project_end: int) -> None:
    """Total float, free float, and the per-task critical flag."""
    for node_id, t in graph.nodes.items():
        t.total_float = t.late_start - t.early_start
        t.is_critical = t.total_float == 0

        outgoing = graph.successors[node_id]
        if not outgoing:
            t.free_float = project_end - t.early_finish
        else:
            slacks = []
            for dep in outgoing:
                succ = graph.nodes[dep.successor_id]
                required = _forward_candidate_es(dep, t, succ.duration_days)
                slacks.append(succ.early_start - required)
            t.free_float = min(slacks)


def _mark_critical_dependencies(graph: Graph) -> set[tuple[int, int]]:
    """An edge is critical when both endpoints are critical and it is the binding
    constraint that determined the successor's early start."""
    critical: set[tuple[int, int]] = set()
    for node_id, t in graph.nodes.items():
        if not t.is_critical:
            continue
        for dep in graph.successors[node_id]:
            succ = graph.nodes[dep.successor_id]
            if not succ.is_critical:
                continue
            required = _forward_candidate_es(dep, t, succ.duration_days)
            if required == succ.early_start:
                dep.is_critical = True
                critical.add((dep.predecessor_id, dep.successor_id))
    return critical


def _extract_critical_path(graph: Graph, critical_edges: set[tuple[int, int]]) -> list[int]:
    """Walk one ordered critical chain from a start node to an end node."""
    if not critical_edges:
        # No multi-task chain; return any single critical node (e.g. lone milestone).
        lone = [tid for tid, t in graph.nodes.items() if t.is_critical]
        return [min(lone)] if lone else []

    successors_on_path: dict[int, int] = {}
    has_incoming: set[int] = set()
    for pred, succ in critical_edges:
        successors_on_path.setdefault(pred, succ)
        has_incoming.add(succ)

    starts = sorted(p for p, _ in critical_edges if p not in has_incoming)
    if not starts:
        return []
    path = [starts[0]]
    current = starts[0]
    while current in successors_on_path:
        current = successors_on_path[current]
        path.append(current)
    return path


def compute_schedule(
    tasks: list[ScheduleTask],
    dependencies: list[ScheduleDependency],
    anchor: date,
) -> ScheduleResult:
    """Run the full CPM computation and map results back to calendar dates.

    Raises :class:`CircularDependencyError` on a dependency cycle and
    :class:`DateConflictError` on inconsistent actuals — both before any output
    is produced, so callers can treat a failed computation as "nothing changed".
    """
    if not tasks:
        return ScheduleResult(
            tasks={}, critical_path=[], critical_dependencies=set(),
            project_start=None, project_finish=None, summary_rows={},
        )

    _validate_actuals(tasks)
    graph = build_graph(tasks, dependencies)
    order = topological_order(graph)  # raises on cycle

    project_end = _forward_pass(graph, order, anchor)
    _backward_pass(graph, order, project_end)
    _compute_float_and_critical(graph, project_end)
    critical_edges = _mark_critical_dependencies(graph)
    critical_path = _extract_critical_path(graph, critical_edges)

    # Map index space back to calendar dates.
    task_results: dict[int, TaskScheduleResult] = {}
    task_dates: dict[int, tuple[date, date]] = {}
    task_wbs: dict[int, str | None] = {}
    for tid, t in graph.nodes.items():
        es_date = calendar.index_to_date(t.early_start, anchor)
        ef_date = _finish_date(t.early_start, t.early_finish, t.duration_days, anchor)
        ls_date = calendar.index_to_date(t.late_start, anchor)
        lf_date = _finish_date(t.late_start, t.late_finish, t.duration_days, anchor)
        task_results[tid] = TaskScheduleResult(
            id=tid,
            early_start_date=es_date,
            early_finish_date=ef_date,
            late_start_date=ls_date,
            late_finish_date=lf_date,
            total_float=t.total_float,
            free_float=t.free_float,
            is_critical=t.is_critical,
        )
        task_dates[tid] = (es_date, ef_date)
        task_wbs[tid] = t.wbs

    project_start, project_finish = compute_project_bounds(task_dates)
    summary_rows = compute_summary_rows(task_dates, task_wbs)

    return ScheduleResult(
        tasks=task_results,
        critical_path=critical_path,
        critical_dependencies=critical_edges,
        project_start=project_start,
        project_finish=project_finish,
        summary_rows=summary_rows,
    )


def _finish_date(start_idx: int, finish_idx: int, duration: int, anchor: date) -> date:
    """Display finish = last working day occupied (inclusive).

    For a positive-duration task that is ``finish_idx - 1`` in index space; a
    milestone (duration 0) is a point, so its finish date equals its start date.
    """
    if duration <= 0:
        return calendar.index_to_date(start_idx, anchor)
    return calendar.index_to_date(finish_idx - 1, anchor)
