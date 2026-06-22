"""The single write path: writes recalc the schedule, and an invalid write
(cycle) rolls back atomically — persisting nothing."""

from __future__ import annotations

from datetime import date

import pytest

from app.engine.errors import CircularDependencyError
from app.repositories import dependency_repo, task_repo
from app.services import project_service, scheduling_service

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
