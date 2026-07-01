"""The Activity feed renders a descriptive, field-level change from the before/after
snapshots recorded on every update."""

from __future__ import annotations

from app.services.audit_view import describe_change


def test_update_describes_changed_fields():
    detail = describe_change(
        "update", "task", "Updated task 'First Paint'",
        {"start_no_earlier_than": "2026-06-29", "duration_days": 5},
        {"start_no_earlier_than": "2026-06-30", "duration_days": 8},
    )
    assert detail == (
        "Updated task 'First Paint': "
        "Earliest start 6/29/26 → 6/30/26; Duration 5d → 8d"
    )


def test_status_and_percent_are_humanised():
    detail = describe_change(
        "update", "task", "Updated task 'Slab'",
        {"status": "not_started", "percent_complete": 0},
        {"status": "in_progress", "percent_complete": 40},
    )
    assert "Status Not started → In progress" in detail
    assert "% complete 0% → 40%" in detail


def test_unchanged_field_is_skipped_and_empty_diff_is_none():
    # duration didn't change → only the start is reported.
    detail = describe_change(
        "update", "task", "Updated task 'X'",
        {"duration_days": 5, "actual_start": None},
        {"duration_days": 5, "actual_start": "2026-07-01"},
    )
    assert detail == "Updated task 'X': Actual start — → 7/1/26"

    # Nothing actually changed → None so the caller falls back to the summary.
    assert describe_change(
        "update", "task", "Updated task 'X'",
        {"duration_days": 5}, {"duration_days": 5},
    ) is None


def test_create_and_delete_have_no_diff():
    assert describe_change("create", "task", "Created task 'X'", None, {"name": "X"}) is None
    assert describe_change("delete", "task", "Deleted task 'X'", None, None) is None
