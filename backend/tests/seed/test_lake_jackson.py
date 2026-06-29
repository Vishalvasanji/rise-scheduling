"""The Lake Jackson demo import builds a valid, gated schedule and is idempotent."""

from __future__ import annotations

from datetime import date

from app.repositories import project_repo, task_repo
from app.seed.lake_jackson import ANCHOR, PHASES, PROJECT_NAME, ensure_lake_jackson


def _expected_task_count() -> int:
    return sum(len(tasks) for _p, blds in PHASES for _b, tasks in blds)


def test_ensure_lake_jackson(session):
    project_id = ensure_lake_jackson(session)
    assert project_id is not None
    # Second run is a no-op (won't clobber edits made through the app).
    assert ensure_lake_jackson(session) is None

    project = next(p for p in project_repo.list_all(session) if p.name == PROJECT_NAME)
    try:
        assert project.anchor_date == ANCHOR
        tasks = task_repo.list_for_project(session, project.id)
        assert len(tasks) == _expected_task_count()
        # No cycles: every task got computed dates from the recalc.
        assert all(t.planned_start and t.planned_finish for t in tasks)
        # WBS encodes phase.building.task for the roll-ups.
        assert all(len(t.wbs.split(".")) == 3 for t in tasks)
        # Phase gate: phase 2 starts only after phase 1 has finished.
        p1_finish = max(t.planned_finish for t in tasks if t.wbs.startswith("1."))
        p2_start = min(t.planned_start for t in tasks if t.wbs.startswith("2."))
        assert p2_start >= p1_finish
        # Zero-duration source rows became milestones.
        assert any(t.is_milestone for t in tasks)
    finally:
        # Keep the shared session DB clean for other tests (cascade deletes tasks/deps).
        session.delete(project)
        session.commit()


def test_anchor_is_last_week_sunday():
    assert ANCHOR == date(2026, 6, 21)
