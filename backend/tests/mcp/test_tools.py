"""The MCP (chat) layer surfaces human WBS labels — a task's phase/building names
and the project's prefix→name map — so chat refers to "Building 13", not "2.2"."""

from __future__ import annotations

from datetime import date

from app.mcp import tools
from app.services import project_service, scheduling_service

ANCHOR = date(2026, 6, 22)


def test_wbs_label_path_resolves_and_falls_back():
    labels = {"2": "Phase 2", "2.2": "Building 13"}
    assert tools._wbs_label_path("2.2.5", labels) == "Phase 2 / Building 13"
    # Missing label for a level falls back to the raw prefix.
    assert tools._wbs_label_path("2.2.5", {"2": "Phase 2"}) == "Phase 2 / 2.2"
    # Ungrouped / empty WBS has no group path.
    assert tools._wbs_label_path("5", labels) is None
    assert tools._wbs_label_path(None, labels) is None


def test_get_schedule_exposes_labels_to_chat(session):
    project = project_service.create_project(session, name="Labeled", anchor_date=ANCHOR)
    project.wbs_labels = {"2": "Phase 2", "2.2": "Building 13"}
    session.commit()
    scheduling_service.create_task(
        session, project.id, {"name": "Roof", "wbs": "2.2.5", "duration_days": 3}
    )

    out = tools.get_schedule(project.id)
    assert out["ok"]
    # The project carries the full label map...
    assert out["project"]["wbs_labels"] == {"2": "Phase 2", "2.2": "Building 13"}
    # ...and the task carries its resolved group path.
    task = next(t for t in out["tasks"] if t["wbs"] == "2.2.5")
    assert task["group"] == "Phase 2 / Building 13"
