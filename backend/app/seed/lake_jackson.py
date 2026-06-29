"""Idempotent import of the Lake Jackson demo project from its master schedule.

The source sheet (a finish/completion "60-day" schedule) lists, per task, the
responsible subcontractor and a duration, grouped Phase -> Building. It carries no
explicit dependencies, so the schedule is synthesized for the demo:

  * finish-to-start chain within each building (in listed order),
  * buildings run in parallel within a phase; phases run sequentially (1 -> 2 -> 3),
  * WBS ``"{phase}.{building}.{task}"`` so the app rolls up Phase -> Building -> task.

Anchored to the beginning of last week (2026-06-21) so it reads as a current demo,
with ``percent_complete`` / ``status`` auto-filled as of today from the computed
dates. Runs on boot (Dockerfile) after the main seed and is a no-op once the project
exists, so it never clobbers edits made through the app.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db.session import session_scope
from app.engine.calendar import working_days_between
from app.models.enums import TaskStatus
from app.repositories import dependency_repo, project_repo, task_repo
from app.services import scheduling_service

PROJECT_NAME = "Lake Jackson"
ANCHOR = date(2026, 6, 21)  # beginning of last week (demo roll-forward)

# WBS-prefix -> display label for the roll-up rows (phases + buildings).
LABELS = {
    "1": "Phase 1",
    "2": "Phase 2",
    "3": "Phase 3",
    "1.1": "Clubhouse",
    "1.2": "Building 8",
    "1.3": "Building 9",
    "2.1": "Building 10",
    "2.2": "Building 13",
    "3.1": "Building 12",
    "3.2": "Building 11",
}

# (phase_no, [(building_name, [(task_name, subcontractor/trade, duration_days), ...])])
# Duration 0 -> milestone. Sourced from the Lake Jackson Master Schedule.
PHASES: list[tuple[int, list[tuple[str, list[tuple[str, str, int]]]]]] = [
    (1, [
        ("Clubhouse", [
            ("MEP Rough In", "PRG, Prosperity, HRDZ", 15),
            ("Framing Pre-Inspection", "MS Construction", 0),
            ("Insulation", "Williams (Labor)", 7),
            ("Drywall Hang", "Wall Werks", 6),
            ("Drywall Tape/ Float / Texture", "Wall Werks", 6),
            ("First Paint", "Bruno Chavez", 5),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Cabinets", "Allied Interior Solutions", 5),
            ("Countertops", "Sorto Interiors", 5),
            ("Tile", "Affordable family interiors", 4),
            ("Plumbing Trim Out", "HRDZ", 5),
            ("Energize Building", "Power Company", 0),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 4),
            ("HVAC Start up", "PRG", 4),
            ("Flooring", "AFI", 5),
            ("Finish Trim", "Panther", 3),
            ("Second Paint", "Bruno Chavez", 4),
            ("Appliances", "Lowes", 0),
            ("Leasing Punchlist", "RISE Leasing", 4),
            ("CO Inspection", "City Permit Office", 0),
            ("Final Clean", "Merry Maids", 3),
        ]),
        ("Building 8", [
            ("Wood Trim (Base, Stool, etc)", "Panther", 5),
            ("Paint Wood Trim", "Bruno Chavez", 5),
            ("Countertops", "Sorto Interiors", 4),
            ("Tile", "Sorto Interiors", 5),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 4),
            ("Finish Trim (Lockout)", "Panther", 4),
            ("Plumbing Trim Out", "HRDZ", 4),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Flooring", "AFI", 5),
            ("HVAC Start up", "PRG", 4),
            ("Electric Service Inspection", "City Permit Office", 0),
            ("Appliances", "Lowes", 3),
            ("Leasing Punchlist", "RISE Leasing", 5),
            ("Final Clean", "Merry Maids", 3),
            ("City Final Inspection", "City Permit Office", 0),
            ("Fire Marshall Inspection", "Fire Marshall Office", 0),
            ("Building Turnover", "RISE", 1),
            ("Elevator Rough In", "Kone", 0),
        ]),
        ("Building 9", [
            ("Paint Wall Out", "Bruno Chavez", 5),
            ("Wood Trim (Base, Stool, etc)", "Panther", 5),
            ("Paint Wood Trim", "Bruno Chavez", 5),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Elevator Rough In", "Kone", 0),
            ("Cabinets", "Allied Interior Solutions", 5),
            ("Countertops", "Sorto Interiors", 4),
            ("Tile", "Sorto Interiors", 5),
            ("Electric Service Inspection", "City Permit Office", 0),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 4),
            ("HVAC Start up", "PRG", 4),
            ("Flooring", "AFI", 5),
            ("Plumbing Trim Out", "HRDZ", 3),
            ("Finish Trim (Lockout)", "Panther", 4),
            ("Appliances", "Lowes", 0),
            ("Leasing Punchlist", "RISE Leasing", 5),
            ("CO Inspection", "City Permit Office", 0),
            ("Fire Marshall Inspection", "Fire Marshall Office", 0),
            ("Final Clean", "Merry Maids", 3),
            ("Building Turnover", "RISE", 1),
        ]),
    ]),
    (2, [
        ("Building 10", [
            ("MEP Rough In", "PRG, Prosperity, HRDZ", 18),
            ("MEP RI Inspection", "PRG, Prosperity, HRDZ", 0),
            ("Roof Jacks / Roof", "MS Construction", 1),
            ("Insulation", "Williams (Labor)", 3),
            ("Drywall Hang", "Wall Werks", 7),
            ("Drywall Tape/ Float / Texture", "Wall Werks", 7),
            ("Gypcrete", "Jadco", 5),
            ("Paint Wall Out", "Bruno Chavez", 5),
            ("Wood Trim (Base, Stool, etc)", "Panther", 5),
            ("Paint Wood Trim", "Bruno Chavez", 5),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Elevator Rough In", "Kone", 0),
            ("Cabinets", "Allied Interior Solutions", 5),
            ("Countertops", "Sorto Interiors", 4),
            ("Tile", "Sorto Interiors", 5),
            ("Electric Service Inspection", "City Permit Office", 3),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 4),
            ("HVAC Start up", "PRG", 4),
            ("Flooring", "AFI", 5),
            ("Plumbing Trim Out", "HRDZ", 3),
            ("Finish Trim (Lockout)", "Panther", 4),
            ("Appliances", "Lowes", 0),
            ("Leasing Punchlist", "RISE Leasing", 5),
            ("CO Inspection", "City Permit Office", 0),
            ("Fire Marshall Inspection", "Fire Marshall Office", 0),
            ("Final Clean", "Merry Maids", 3),
            ("Building Turnover", "RISE", 1),
        ]),
        ("Building 13", [
            ("MEP Rough In", "PRG, Prosperity, HRDZ", 15),
            ("Framing Pre-Inspection", "MS Construction", 0),
            ("Insulation", "Williams (Labor)", 7),
            ("Drywall Hang", "Wall Werks", 6),
            ("Drywall Tape/ Float / Texture", "Wall Werks", 6),
            ("Gypcrete", "Jadco", 5),
            ("Paint Wall Out", "Bruno Chavez", 6),
            ("Wood Trim (Base, Stool, etc)", "Panther", 5),
            ("Paint Wood Trim", "Bruno Chavez", 5),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Elevator Rough In", "Kone", 0),
            ("Cabinets", "Allied Interior Solutions", 5),
            ("Countertops", "Sorto Interiors", 5),
            ("Tile", "Sorto Interiors", 4),
            ("Electric Service Inspection", "City Permit Office", 3),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 5),
            ("HVAC Start up", "PRG", 4),
            ("Flooring", "AFI", 4),
            ("Plumbing Trim Out", "HRDZ", 5),
            ("Finish Trim (Lockout)", "Panther", 3),
            ("Appliances", "Lowes", 4),
            ("Leasing Punchlist", "RISE Leasing", 5),
            ("CO Inspection", "City Permit Office", 0),
            ("Fire Marshall Inspection", "Fire Marshall Office", 0),
            ("Final Clean", "Merry Maids", 0),
            ("Building Turnover", "RISE", 5),
        ]),
    ]),
    (3, [
        ("Building 12", [
            ("MEP Rough In", "PRG, Prosperity, HRDZ", 15),
            ("Framing Pre-Inspection", "MS Construction", 0),
            ("Insulation", "Williams (Labor)", 7),
            ("Drywall Hang", "Wall Werks", 6),
            ("Drywall Tape/ Float / Texture", "Wall Werks", 6),
            ("Gypcrete", "Jadco", 6),
            ("Paint Wall Out", "Bruno Chavez", 5),
            ("Wood Trim (Base, Stool, etc)", "Panther", 5),
            ("Paint Wood Trim", "Bruno Chavez", 5),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Elevator Rough In", "Kone", 0),
            ("Cabinets", "Allied Interior Solutions", 5),
            ("Countertops", "Sorto Interiors", 5),
            ("Tile", "Sorto Interiors", 5),
            ("Electric Service Inspection", "City Permit Office", 3),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 4),
            ("HVAC Start up", "PRG", 4),
            ("Flooring", "AFI", 5),
            ("Plumbing Trim Out", "HRDZ", 3),
            ("Finish Trim (Lockout)", "Panther", 4),
            ("Appliances", "Lowes", 0),
            ("Leasing Punchlist", "RISE Leasing", 5),
            ("CO Inspection", "City Permit Office", 3),
            ("Fire Marshall Inspection", "Fire Marshall Office", 0),
            ("Final Clean", "Merry Maids", 5),
            ("Building Turnover", "RISE", 0),
        ]),
        ("Building 11", [
            ("MEP Rough In", "PRG, Prosperity, HRDZ", 15),
            ("Framing Pre-Inspection", "MS Construction", 0),
            ("Insulation", "Williams (Labor)", 7),
            ("Drywall Hang", "Wall Werks", 6),
            ("Drywall Tape/ Float / Texture", "Wall Werks", 6),
            ("Gypcrete", "Jadco", 6),
            ("Paint Wall Out", "Bruno Chavez", 5),
            ("Wood Trim (Base, Stool, etc)", "Panther", 5),
            ("Paint Wood Trim", "Bruno Chavez", 5),
            ("Mech/ Elec Trim Out", "PRG, Prosperity", 5),
            ("Elevator Rough In", "Kone", 0),
            ("Cabinets", "Allied Interior Solutions", 15),
            ("Countertops", "Sorto Interiors", 5),
            ("Tile", "Sorto Interiors", 4),
            ("Electric Service Inspection", "City Permit Office", 3),
            ("Fire Alarm / Sprinkler Trim Out", "Texican", 0),
            ("HVAC Start up", "PRG", 4),
            ("Flooring", "AFI", 4),
            ("Plumbing Trim Out", "HRDZ", 5),
            ("Finish Trim (Lockout)", "Panther", 3),
            ("Appliances", "Lowes", 4),
            ("Leasing Punchlist", "RISE Leasing", 0),
            ("CO Inspection", "City Permit Office", 0),
            ("Fire Marshall Inspection", "Fire Marshall Office", 0),
            ("Final Clean", "Merry Maids", 5),
            ("Building Turnover", "RISE", 0),
        ]),
    ]),
]


def _already_imported(session: Session) -> bool:
    return any(p.name == PROJECT_NAME for p in project_repo.list_all(session))


def _fill_progress(session: Session, project_id: int) -> None:
    """Auto-fill percent_complete / status from the computed dates, as of today.

    Pure data (no effect on the CPM), so no recalc is needed afterwards.
    """
    today = date.today()
    for t in task_repo.list_for_project(session, project_id):
        if t.planned_start is None or t.planned_finish is None:
            continue
        if t.planned_finish < today:
            t.percent_complete = 100.0
            t.status = TaskStatus.COMPLETE
        elif t.is_milestone or t.duration_days == 0:
            t.percent_complete = 0.0
            t.status = TaskStatus.NOT_STARTED
        elif t.planned_start <= today:
            elapsed = working_days_between(t.planned_start, today)
            pct = round(100.0 * elapsed / t.duration_days)
            t.percent_complete = float(max(0, min(100, pct)))
            t.status = TaskStatus.IN_PROGRESS
        else:
            t.percent_complete = 0.0
            t.status = TaskStatus.NOT_STARTED
    session.commit()


def _apply_labels(session: Session, project) -> None:
    """Set the roll-up display labels (idempotent; refreshes on every boot)."""
    if project.wbs_labels != LABELS:
        project.wbs_labels = LABELS
        session.commit()


def _apply_buildings(session: Session, project_id: int) -> None:
    """Tag each task with its building name, derived from the WBS ``phase.building``
    prefix (e.g. ``"2.2.x"`` -> "Building 13"). Idempotent; refreshes on every boot
    so an already-live project picks it up on deploy."""
    changed = False
    for t in task_repo.list_for_project(session, project_id):
        if not t.wbs:
            continue
        segs = t.wbs.split(".")
        if len(segs) < 2:
            continue
        building = LABELS.get(".".join(segs[:2]))
        if building and t.building != building:
            t.building = building
            changed = True
    if changed:
        session.commit()


def ensure_lake_jackson(session: Session) -> int | None:
    """Create the Lake Jackson demo project if it doesn't already exist.

    Always (re)applies the roll-up labels so an already-live project picks them up on
    deploy. Returns the new project id, or None if it was already present.
    """
    existing = next(
        (p for p in project_repo.list_all(session) if p.name == PROJECT_NAME), None
    )
    if existing is not None:
        _apply_labels(session, existing)
        _apply_buildings(session, existing.id)
        return None

    project = project_repo.create(
        session,
        name=PROJECT_NAME,
        deal_type="New construction",
        units=None,
        stage="Construction",
        anchor_date=ANCHOR,
    )
    session.flush()

    phase_firsts: dict[int, list[int]] = {}  # phase -> first-task id per building
    phase_lasts: dict[int, list[int]] = {}  # phase -> last-task id per building
    for phase_no, buildings in PHASES:
        firsts: list[int] = []
        lasts: list[int] = []
        for b_idx, (_building, tasks) in enumerate(buildings, start=1):
            ids: list[int] = []
            for t_idx, (name, trade, dur) in enumerate(tasks, start=1):
                task = task_repo.create(
                    session,
                    project_id=project.id,
                    name=name,
                    wbs=f"{phase_no}.{b_idx}.{t_idx}",
                    trade=trade,
                    duration_days=dur,
                    is_milestone=dur == 0,
                )
                if ids:  # finish-to-start chain within the building
                    dependency_repo.create(
                        session,
                        predecessor_id=ids[-1],
                        successor_id=task.id,
                        type="FS",
                        lag_days=0,
                    )
                ids.append(task.id)
            firsts.append(ids[0])
            lasts.append(ids[-1])
        phase_firsts[phase_no] = firsts
        phase_lasts[phase_no] = lasts

    # Phase gate: each next-phase building starts only after every prior-phase
    # building has finished.
    phase_nos = [p for p, _ in PHASES]
    for prev, nxt in zip(phase_nos, phase_nos[1:], strict=False):
        for first_id in phase_firsts[nxt]:
            for last_id in phase_lasts[prev]:
                dependency_repo.create(
                    session,
                    predecessor_id=last_id,
                    successor_id=first_id,
                    type="FS",
                    lag_days=0,
                )

    session.commit()
    scheduling_service.recalculate(session, project.id, actor="import")
    _fill_progress(session, project.id)
    _apply_labels(session, project)
    _apply_buildings(session, project.id)
    return project.id


def main() -> None:
    with session_scope() as session:
        project_id = ensure_lake_jackson(session)
    if project_id is None:
        print(f"{PROJECT_NAME} already exists; skipping import.")
    else:
        print(f"Imported {PROJECT_NAME} as project {project_id}.")


if __name__ == "__main__":
    main()
