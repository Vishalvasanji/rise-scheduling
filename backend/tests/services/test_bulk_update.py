"""Batched ("Save all" from the spreadsheet) task edits: many rows applied in one
transaction with a single recalc, per-row audit, atomic rollback, and a version
conflict that aborts the whole batch without applying anything."""

from __future__ import annotations

from datetime import date

import pytest

from app.repositories import audit_repo, task_repo
from app.services import project_service, scheduling_service
from app.services.errors import BulkConflictError

ANCHOR = date(2026, 6, 22)


def _new_project(session, name="Bulk Test"):
    return project_service.create_project(session, name=name, anchor_date=ANCHOR)


def test_bulk_applies_all_with_one_audit_per_row(session):
    project = _new_project(session, "bulk-apply")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 3})
    scheduling_service.create_dependency(session, a.id, b.id, "FS")
    before_audit = len(audit_repo.list_for_project(session, project.id))

    scheduling_service.bulk_update_tasks(
        session,
        project.id,
        [
            {"task_id": a.id, "fields": {"name": "A2", "duration_days": 8}},
            {"task_id": b.id, "fields": {"trade": "Framing"}},
        ],
        actor="dana",
        source="web",
    )

    ra = task_repo.get(session, a.id)
    rb = task_repo.get(session, b.id)
    assert ra.name == "A2" and ra.duration_days == 8 and ra.updated_by == "dana"
    assert rb.trade == "Framing"
    # B's dates recomputed off A's new duration (single recalc ran).
    assert rb.planned_start >= ra.planned_finish
    # One audit entry per edited row.
    assert len(audit_repo.list_for_project(session, project.id)) == before_audit + 2


def test_bulk_rolls_back_atomically_on_engine_error(session):
    from app.engine.errors import DateConflictError

    project = _new_project(session, "bulk-rollback")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 2})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 2})

    # One row is a clean edit; the other pins actual_finish before actual_start,
    # which the engine rejects — the whole batch must roll back.
    with pytest.raises(DateConflictError):
        scheduling_service.bulk_update_tasks(
            session,
            project.id,
            [
                {"task_id": a.id, "fields": {"name": "A-edited"}},
                {
                    "task_id": b.id,
                    "fields": {
                        "actual_start": date(2026, 7, 1),
                        "actual_finish": date(2026, 6, 1),
                    },
                },
            ],
        )

    session.expire_all()
    # Neither edit persisted — the batch is all-or-nothing.
    assert task_repo.get(session, a.id).name == "A"
    assert task_repo.get(session, b.id).actual_finish is None


def test_bulk_version_conflict_aborts_without_applying(session):
    project = _new_project(session, "bulk-conflict")
    a, _ = scheduling_service.create_task(session, project.id, {"name": "A", "duration_days": 5})
    b, _ = scheduling_service.create_task(session, project.id, {"name": "B", "duration_days": 3})
    # Someone bumps A's version to 2 out from under the editor.
    scheduling_service.update_task(session, a.id, {"duration_days": 6}, actor="alice")

    # The editor still thinks A is version 1 → the whole batch aborts.
    with pytest.raises(BulkConflictError) as ei:
        scheduling_service.bulk_update_tasks(
            session,
            project.id,
            [
                {"task_id": a.id, "fields": {"name": "A-new"}, "expected_version": 1},
                {"task_id": b.id, "fields": {"name": "B-new"}, "expected_version": 1},
            ],
        )
    conflicts = ei.value.conflicts
    assert [c["task_id"] for c in conflicts] == [a.id]
    assert conflicts[0]["updated_by"] == "alice"
    session.expire_all()
    # Nothing applied — not even the non-conflicting row B.
    assert task_repo.get(session, a.id).name == "A"
    assert task_repo.get(session, b.id).name == "B"

    # Forcing overwrites the conflicting row and applies the rest.
    scheduling_service.bulk_update_tasks(
        session,
        project.id,
        [
            {"task_id": a.id, "fields": {"name": "A-new"}, "expected_version": 1},
            {"task_id": b.id, "fields": {"name": "B-new"}, "expected_version": 1},
        ],
        force=True,
    )
    assert task_repo.get(session, a.id).name == "A-new"
    assert task_repo.get(session, b.id).name == "B-new"


def test_bulk_rejects_task_outside_project(session):
    p1 = _new_project(session, "bulk-p1")
    p2 = _new_project(session, "bulk-p2")
    other, _ = scheduling_service.create_task(session, p2.id, {"name": "X", "duration_days": 1})
    with pytest.raises(ValueError):
        scheduling_service.bulk_update_tasks(
            session, p1.id, [{"task_id": other.id, "fields": {"name": "nope"}}]
        )
