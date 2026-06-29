"""The single write path: writes recalc the schedule, and an invalid write
(cycle) rolls back atomically — persisting nothing."""

from __future__ import annotations

from datetime import date

import pytest

from app.engine.errors import CircularDependencyError
from app.repositories import dependency_repo, task_repo
from app.services import project_service, scheduling_service
from app.services.errors import ConflictError

ANCHOR = date(2026, 6, 22)


def _new_project(session, name="Svc Test"):
    return project_service.create_project(session, name=name, anchor_date=ANCHOR)


def test_create_task_recalculates(session):
    project = _new_project(session, "recalc")
    t1, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    t2, result = scheduling_service.create_task(
        session, project.id, {"name": "B", "duration_days": 3}
    )
    scheduling_service.create_dependency(session, t1.id, t2.id, "FS")

    refreshed = task_repo.get(session, t2.id)
    assert refreshed.planned_start is not None
    assert refreshed.planned_finish is not None
    assert refreshed.planned_start <= refreshed.planned_finish
    # B should start after A starts (FS chain pushes the successor downstream)
    a = task_repo.get(session, t1.id)
    assert refreshed.planned_start > a.planned_start


def test_cycle_write_rolls_back(session):
    project = _new_project(session, "cycle")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 2})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 2})
    c, _ = scheduling_service.create_task(session, project.id, {"name": "C", "duration_days": 2})
    scheduling_service.create_dependency(session, a.id, b.id, "FS")
    scheduling_service.create_dependency(session, b.id, c.id, "FS")

    deps_before = len(dependency_repo.list_for_project(session, project.id))
    # Closing the loop C -> A must be rejected and persist nothing.
    with pytest.raises(CircularDependencyError):
        scheduling_service.create_dependency(session, c.id, a.id, "FS")

    session.expire_all()
    deps_after = len(dependency_repo.list_for_project(session, project.id))
    assert deps_after == deps_before  # the cycle-creating edge was NOT persisted


def test_update_task_marks_critical(session):
    project = _new_project(session, "critical")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 5})
    scheduling_service.create_dependency(session, a.id, b.id, "FS")
    # A single FS chain is entirely critical.
    assert task_repo.get(session, a.id).is_critical
    assert task_repo.get(session, b.id).is_critical


def test_start_no_earlier_than_reschedules_without_an_actual(session):
    project = _new_project(session, "snet")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    start_before = task_repo.get(session, a.id).planned_start

    # Push the start out to a later date via the planning constraint.
    target = date(2026, 7, 6)  # a Monday, after the default start
    scheduling_service.update_task(session, a.id, {"start_no_earlier_than": target})

    refreshed = task_repo.get(session, a.id)
    assert refreshed.planned_start == target          # the computed start moved
    assert refreshed.start_no_earlier_than == target  # constraint stored
    assert refreshed.actual_start is None             # ...and NOT logged as an actual
    assert refreshed.planned_start > start_before


def test_version_bumps_only_on_user_edit(session):
    project = _new_project(session, "version")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 3})
    scheduling_service.create_dependency(session, a.id, b.id, "FS")
    b_version = task_repo.get(session, b.id).version

    # Editing A recalculates B's dates, but must NOT bump B's version.
    scheduling_service.update_task(session, a.id, {"duration_days": 8}, actor="alice")
    assert task_repo.get(session, b.id).version == b_version
    edited_a = task_repo.get(session, a.id)
    assert edited_a.version == 2  # 1 on create, +1 on this edit
    assert edited_a.updated_by == "alice"


def test_stale_update_conflicts_unless_forced(session):
    project = _new_project(session, "conflict")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    # Alice edits first → version goes 1 → 2, attributed to her.
    scheduling_service.update_task(
        session, a.id, {"duration_days": 6}, actor="alice", expected_version=1
    )

    # Bob still thinks it's version 1 → conflict naming alice.
    with pytest.raises(ConflictError) as ei:
        scheduling_service.update_task(
            session, a.id, {"duration_days": 7}, actor="bob", expected_version=1
        )
    assert ei.value.updated_by == "alice"
    assert ei.value.current_version == 2
    assert task_repo.get(session, a.id).duration_days == 6  # bob's write didn't land

    # Bob forces the overwrite → it lands and bumps the version.
    scheduling_service.update_task(
        session, a.id, {"duration_days": 7}, actor="bob", expected_version=1, force=True
    )
    forced = task_repo.get(session, a.id)
    assert forced.duration_days == 7
    assert forced.updated_by == "bob"
    assert forced.version == 3

    # A correct expected_version also succeeds.
    scheduling_service.update_task(
        session, a.id, {"duration_days": 8}, actor="carol", expected_version=3
    )
    assert task_repo.get(session, a.id).duration_days == 8
