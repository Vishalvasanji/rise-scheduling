"""Date roll-up: task -> WBS summary -> project.

Summary rows are *computed* from WBS codes, never stored as graph edges, so they
cannot introduce fake dependencies into the CPM graph. Project start/finish is
simply the min/max over all task dates (milestones included, since a milestone is
just a zero-duration task).
"""

from __future__ import annotations

from datetime import date


def compute_summary_rows(
    task_dates: dict[int, tuple[date, date]],
    task_wbs: dict[int, str | None],
) -> dict[str, tuple[date, date]]:
    """Roll leaf-task dates up to every WBS ancestor prefix.

    A task with WBS ``"D.4"`` contributes to summary row ``"D"``; a task with
    ``"1.2.3"`` contributes to ``"1"`` and ``"1.2"``. Each summary row spans the
    min start / max finish of its descendant tasks.
    """
    summary: dict[str, tuple[date, date]] = {}
    for task_id, (start, finish) in task_dates.items():
        wbs = task_wbs.get(task_id)
        if not wbs:
            continue
        parts = wbs.split(".")
        for i in range(1, len(parts)):
            prefix = ".".join(parts[:i])
            if prefix not in summary:
                summary[prefix] = (start, finish)
            else:
                cur_start, cur_finish = summary[prefix]
                summary[prefix] = (min(cur_start, start), max(cur_finish, finish))
    return summary


def compute_project_bounds(
    task_dates: dict[int, tuple[date, date]],
) -> tuple[date | None, date | None]:
    """Project start = earliest task start; finish = latest task finish."""
    if not task_dates:
        return None, None
    starts = [start for start, _ in task_dates.values()]
    finishes = [finish for _, finish in task_dates.values()]
    return min(starts), max(finishes)
