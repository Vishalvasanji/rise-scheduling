"""Proposals are pure dry-runs: previewing/staging computes the proposed schedule
without touching the DB; applying replays the mutations for real; an invalid
proposal is rejected and never stored."""

from __future__ import annotations

from datetime import date

import pytest

from app.engine.errors import CircularDependencyError
from app.repositories import dependency_repo, project_repo, task_repo
from app.services import project_service, proposal_service, scheduling_service

ANCHOR = date(2026, 6, 22)


def _chain(session, name="Prop Test"):
    """A → B → C finish-to-start chain (durations 5/3/4)."""
    project = project_service.create_project(session, name=name, anchor_date=ANCHOR)
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 3})
    c, _ = scheduling_service.create_task(session, project.id, {"name": "C", "duration_days": 4})
    scheduling_service.create_dependency(session, a.id, b.id, "FS")
    scheduling_service.create_dependency(session, b.id, c.id, "FS")
    return project, a, b, c


def test_set_pending_does_not_touch_db(session):
    project, a, b, c = _chain(session, "dryrun")
    finish_before = {t.id: task_repo.get(session, t.id).planned_finish for t in (a, b, c)}

    proposal = proposal_service.set_pending(
        session,
        project.id,
        [{"op": "update_task", "task_id": a.id, "fields": {"duration_days": 10}}],
        summary="Stretch A to 10 days",
    )

    # The proposal reports A modified + downstream B/C moved, and a later finish.
    by_id = {c_.task_id: c_ for c_ in proposal.changes}
    assert by_id[a.id].change_type in ("moved", "modified")
    assert by_id[b.id].change_type == "moved"
    assert by_id[c.id].change_type == "moved"

    proposed_a = next(t for t in proposal.schedule.tasks if t.id == a.id)
    assert proposed_a.planned_finish > finish_before[a.id]

    # DB is untouched: the live tasks still hold their old computed dates.
    session.expire_all()
    for t in (a, b, c):
        assert task_repo.get(session, t.id).planned_finish == finish_before[t.id]
    # ...but the proposal blob is stored on the project.
    assert project_repo.get(session, project.id).pending_proposal is not None


def test_apply_pending_persists_and_clears(session):
    project, a, b, c = _chain(session, "apply")
    c_finish_before = task_repo.get(session, c.id).planned_finish

    proposal_service.set_pending(
        session,
        project.id,
        [{"op": "update_task", "task_id": a.id, "fields": {"duration_days": 10}}],
    )
    proposed_c = next(
        t for t in proposal_service.get_pending(session, project.id).schedule.tasks
        if t.id == c.id
    )

    schedule = proposal_service.apply_pending(session, project.id)
    assert schedule is not None

    session.expire_all()
    # The proposed downstream shift is now the live schedule.
    assert task_repo.get(session, c.id).planned_finish == proposed_c.planned_finish
    assert task_repo.get(session, c.id).planned_finish > c_finish_before
    assert task_repo.get(session, a.id).duration_days == 10
    # ...and the proposal is cleared.
    assert project_repo.get(session, project.id).pending_proposal is None
    assert proposal_service.get_pending(session, project.id) is None


def test_create_task_and_dependency_proposal(session):
    project, a, b, c = _chain(session, "create")
    deps_before = len(dependency_repo.list_for_project(session, project.id))

    proposal = proposal_service.set_pending(
        session,
        project.id,
        [
            {"op": "create_task", "ref": "new", "fields": {"name": "D", "duration_days": 2}},
            {"op": "create_dependency", "predecessor": c.id, "successor": "new", "type": "FS"},
        ],
        summary="Add D after C",
    )
    new_change = next(ch for ch in proposal.changes if ch.change_type == "new")
    assert new_change.name == "D"
    # Nothing persisted yet.
    session.expire_all()
    assert len(dependency_repo.list_for_project(session, project.id)) == deps_before

    proposal_service.apply_pending(session, project.id)
    session.expire_all()
    tasks = task_repo.list_for_project(session, project.id)
    d = next(t for t in tasks if t.name == "D")
    assert d.planned_start is not None
    assert len(dependency_repo.list_for_project(session, project.id)) == deps_before + 1


def test_cycle_proposal_rejected_not_stored(session):
    project, a, b, c = _chain(session, "cycle")

    # Closing the loop C → A would create a cycle: rejected, nothing stored.
    with pytest.raises(CircularDependencyError):
        proposal_service.set_pending(
            session,
            project.id,
            [{"op": "create_dependency", "predecessor": c.id, "successor": a.id}],
        )

    session.expire_all()
    assert project_repo.get(session, project.id).pending_proposal is None


def test_discard_clears_without_applying(session):
    project, a, b, c = _chain(session, "discard")
    finish_before = task_repo.get(session, c.id).planned_finish

    proposal_service.set_pending(
        session,
        project.id,
        [{"op": "update_task", "task_id": a.id, "fields": {"duration_days": 99}}],
    )
    assert proposal_service.discard_pending(session, project.id) is True

    session.expire_all()
    assert project_repo.get(session, project.id).pending_proposal is None
    assert task_repo.get(session, c.id).planned_finish == finish_before
    # Discarding again is a no-op.
    assert proposal_service.discard_pending(session, project.id) is False
