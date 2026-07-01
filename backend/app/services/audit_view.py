"""Human-readable rendering of an audit entry's field-level change, built at read
time from the before/after snapshots the service layer already records. Keeps the
Activity feed descriptive ("Earliest start 6/29 → 6/30; Duration 8d") without
storing anything extra."""

from __future__ import annotations

import re
from typing import Any

# Field name -> label shown in the Activity feed. Covers the writable task fields.
FIELD_LABELS: dict[str, str] = {
    "name": "Name",
    "wbs": "WBS",
    "trade": "Trade",
    "building": "Building",
    "duration_days": "Duration",
    "percent_complete": "% complete",
    "status": "Status",
    "is_milestone": "Milestone",
    "actual_start": "Actual start",
    "actual_finish": "Actual finish",
    "start_no_earlier_than": "Earliest start",
    "external_ref": "External ref",
    "procore_id": "Procore ID",
}

_DATE_FIELDS = {"actual_start", "actual_finish", "start_no_earlier_than"}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fmt_value(field: str, value: Any) -> str:
    """Render one stored value for display. Stored values are already JSON-clean
    (dates as 'YYYY-MM-DD', status as 'in_progress', numbers, bools)."""
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if field == "duration_days":
        return f"{value}d"
    if field == "percent_complete":
        return f"{value}%"
    if field == "status":
        return str(value).replace("_", " ").capitalize()
    if isinstance(value, str) and _ISO_DATE.match(value):
        y, m, d = value.split("-")
        return f"{int(m)}/{int(d)}/{y[2:]}"
    return str(value)


def describe_change(
    action: str,
    entity_type: str,
    summary: str | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> str | None:
    """A descriptive change line, or None when there's nothing to diff (in which case
    the caller falls back to the plain summary). For a task update, appends the changed
    fields to the summary: "Updated task 'X': Earliest start 6/29/26 → 6/30/26"."""
    if action != "update" or not after:
        return None
    parts: list[str] = []
    for field, new in after.items():
        old = (before or {}).get(field)
        if old == new:
            continue
        label = FIELD_LABELS.get(field, field.replace("_", " ").capitalize())
        parts.append(f"{label} {_fmt_value(field, old)} → {_fmt_value(field, new)}")
    if not parts:
        return None
    diff = "; ".join(parts)
    return f"{summary}: {diff}" if summary else diff
