"""Seed 5 synthetic LIHTC development schedules (dummydata.md).

Fictional names/addresses; authentic schedule shapes. Each project is inserted
through the data layer and then recalculated through the **scheduling service**,
so seeded schedules are CPM-computed exactly like real writes and exercise the
engine. Idempotent: existing projects with the same names are wiped and reseeded.

Edge-case coverage (dummydata.md §"Edge cases"):
  1. Parallel converging workstreams + float  -> P1 design/entitlement -> permit
  2. Long-lead milestone roll-up               -> P1/P2 application->award (60d)
  3. FF-30 negative-lag finish                 -> P1 marketing -> CO
  4. Staggered SS rehab batches                -> P3 unit-turn batches (SS+15)
  5. Sitework-heavy critical-path shift        -> P5 earthwork + flood fill
  6. One deliberately slipped task             -> P2 financial closing (actual > planned)
  (7. Circular dependency is a TEST fixture only, never seeded.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Dependency, Project, Task
from app.models.enums import TaskStatus
from app.repositories import dependency_repo, project_repo, task_repo
from app.services import scheduling_service

ANCHOR = date(2026, 6, 22)  # pilot anchor (a Monday)


def _shift_months(d: date, months: int) -> date:
    # Approximate month shift (90 days) — pilot calendar has no holidays anyway.
    return d + timedelta(days=90 * months)


@dataclass
class T:
    """Task spec keyed for dependency wiring."""

    key: str
    name: str
    wbs: str
    dur: int
    ms: bool = False
    pct: float = 0.0
    status: TaskStatus = TaskStatus.NOT_STARTED
    astart: date | None = None
    afinish: date | None = None


@dataclass
class D:
    """Dependency spec referencing task keys."""

    pred: str
    succ: str
    type: str = "FS"
    lag: int = 0


@dataclass
class ProjectSpec:
    name: str
    deal_type: str
    units: int
    stage: str
    anchor: date
    tasks: list[T]
    deps: list[D] = field(default_factory=list)


def _build(session: Session, spec: ProjectSpec) -> int:
    project = project_repo.create(
        session,
        name=spec.name,
        deal_type=spec.deal_type,
        units=spec.units,
        stage=spec.stage,
        anchor_date=spec.anchor,
    )
    session.flush()
    key_to_id: dict[str, int] = {}
    for ts in spec.tasks:
        task = task_repo.create(
            session,
            project_id=project.id,
            name=ts.name,
            wbs=ts.wbs,
            duration_days=0 if ts.ms else ts.dur,
            is_milestone=ts.ms,
            percent_complete=ts.pct,
            status=ts.status,
            actual_start=ts.astart,
            actual_finish=ts.afinish,
        )
        key_to_id[ts.key] = task.id
    for ds in spec.deps:
        dependency_repo.create(
            session,
            predecessor_id=key_to_id[ds.pred],
            successor_id=key_to_id[ds.succ],
            type=ds.type,
            lag_days=ds.lag,
        )
    session.commit()
    scheduling_service.recalculate(session, project.id, actor="seed")
    return project.id


# --------------------------------------------------------------------------- #
# P1 — Cedar Pointe BTR: full A–E reference project, ~35 tasks.
# Critical path through Financing -> Construction; FF-30 marketing; parallel
# design/entitlement converging on permit.
# --------------------------------------------------------------------------- #
def _p1() -> ProjectSpec:
    DONE = TaskStatus.COMPLETE
    GO = TaskStatus.IN_PROGRESS
    tasks = [
        # Phase A — Predevelopment (complete)
        T("A1", "Site identification & LOI", "A.1", 10, pct=100, status=DONE),
        T("A2", "Purchase & Sale Agreement", "A.2", 15, pct=100, status=DONE),
        T("A3", "Due diligence (ESA, survey, geotech)", "A.3", 30, pct=100, status=DONE),
        T("A4", "Site feasibility / QCT-DDA / flood screen", "A.4", 10, pct=100, status=DONE),
        T("A5", "Preliminary site plan", "A.5", 20, pct=100, status=DONE),
        # Phase B — Financing (in progress)
        T("B1", "LIHTC/bond application prep", "B.1", 25, pct=100, status=DONE),
        T("B2", "Application submission -> award", "B.2", 60, pct=60, status=GO),
        T("B3", "Lender term sheet", "B.3", 20, pct=20, status=GO),
        T("B4", "Syndicator/equity LOI", "B.4", 20, pct=10, status=GO),
        T("B5", "Gap financing (CDBG-DR / soft sources)", "B.5", 40),
        T("B6", "Financial closing", "B.6", 30),
        T("BM", "Financial closing complete", "B.7", 0, ms=True),
        # Phase C — Design & Entitlement
        T("C1", "Schematic design", "C.1", 25, pct=80, status=GO),
        T("C2", "Design development", "C.2", 30, pct=20, status=GO),
        T("C3", "Construction documents", "C.3", 45),
        T("C4", "Zoning/entitlement approval", "C.4", 60, pct=30, status=GO),
        T("C5", "Building permit", "C.5", 30),
        # Phase D — Construction
        T("D1", "Mobilization", "D.1", 10),
        T("D2", "Site work / earthwork", "D.2", 40),
        T("D3", "Foundations", "D.3", 30),
        T("D4", "Vertical construction", "D.4", 180),
        T("D5", "MEP rough-in", "D.5", 60),
        T("D6", "Interior finishes", "D.6", 90),
        T("D7", "Site amenities / landscaping", "D.7", 40),
        T("DM", "Substantial completion", "D.8", 0, ms=True),
        T("CO", "Certificate of Occupancy", "D.9", 15, ms=True),
        # Phase E — Lease-up & Stabilization
        T("E1", "Marketing launch", "E.1", 30),
        T("E2", "Lease-up to stabilization", "E.2", 120),
        T("E3", "Placed-in-service / 8609", "E.3", 0, ms=True),
        T("E4", "Permanent loan conversion", "E.4", 30),
    ]
    deps = [
        D("A1", "A2"), D("A2", "A3"), D("A3", "A4", "SS"), D("A3", "A5"),
        # Financing
        D("A2", "B1"), D("B1", "B2"), D("B2", "B3"), D("B2", "B4"), D("B2", "B5"),
        D("B3", "B6"), D("B4", "B6"), D("B5", "B6"), D("B6", "BM"),
        # Design + entitlement (parallel, converge on permit)
        D("A5", "C1"), D("C1", "C2"), D("C2", "C3"), D("A5", "C4"),
        D("C3", "C5"), D("C4", "C5"),
        # Cross-phase gate: closing AND permit before mobilization
        D("BM", "D1"), D("C5", "D1"),
        D("D1", "D2"), D("D2", "D3"), D("D3", "D4"),
        D("D4", "D5", "SS", 30), D("D4", "D6", "SS", 60), D("D4", "D7"),
        D("D4", "DM"), D("D6", "DM"), D("DM", "CO"),
        # FF-30: marketing finishes 30 working days before CO finishes
        D("CO", "E1", "FF", -30),
        D("CO", "E2"), D("E2", "E3"), D("E2", "E4"),
    ]
    return ProjectSpec(
        "Cedar Pointe BTR", "New construction, 4% bond", 80, "Pre-construction",
        ANCHOR, tasks, deps,
    )


# --------------------------------------------------------------------------- #
# P2 — Monterrey Townhomes: A–D, ~25 tasks. Financing-heavy critical path with
# a deliberately slipped financial-closing task.
# --------------------------------------------------------------------------- #
def _p2() -> ProjectSpec:
    DONE = TaskStatus.COMPLETE
    GO = TaskStatus.IN_PROGRESS
    anchor = _shift_months(ANCHOR, -3)
    # Slipped task: closing was planned ~ within its 30d, but actuals run long.
    closing_start = _shift_months(anchor, 4)
    closing_finish_late = closing_start + timedelta(days=70)  # well past 30 working days
    tasks = [
        T("A1", "Site identification & LOI", "A.1", 10, pct=100, status=DONE),
        T("A2", "Purchase & Sale Agreement", "A.2", 15, pct=100, status=DONE),
        T("A3", "Due diligence", "A.3", 30, pct=100, status=DONE),
        T("A4", "Preliminary site plan", "A.4", 20, pct=100, status=DONE),
        T("B1", "LIHTC/bond application prep", "B.1", 25, pct=100, status=DONE),
        T("B2", "Application submission -> award", "B.2", 60, pct=100, status=DONE),
        T("B3", "Lender term sheet", "B.3", 20, pct=100, status=DONE),
        T("B4", "Syndicator/equity LOI", "B.4", 20, pct=100, status=DONE),
        T("B5", "Gap financing", "B.5", 40, pct=80, status=GO),
        T("B6", "Financial closing", "B.6", 30, pct=60, status=GO,
          astart=closing_start, afinish=closing_finish_late),  # SLIPPED
        T("BM", "Financial closing complete", "B.7", 0, ms=True),
        T("C1", "Schematic design", "C.1", 25, pct=100, status=DONE),
        T("C2", "Design development", "C.2", 30, pct=100, status=DONE),
        T("C3", "Construction documents", "C.3", 45, pct=70, status=GO),
        T("C4", "Building permit", "C.4", 30, pct=20, status=GO),
        T("D1", "Mobilization", "D.1", 10),
        T("D2", "Site work / earthwork", "D.2", 40),
        T("D3", "Foundations", "D.3", 30),
        T("D4", "Vertical construction", "D.4", 150),
        T("D5", "MEP rough-in", "D.5", 50),
        T("D6", "Interior finishes", "D.6", 80),
        T("DM", "Substantial completion", "D.7", 0, ms=True),
        T("CO", "Certificate of Occupancy", "D.8", 15, ms=True),
    ]
    deps = [
        D("A1", "A2"), D("A2", "A3"), D("A3", "A4"),
        D("A2", "B1"), D("B1", "B2"), D("B2", "B3"), D("B2", "B4"), D("B2", "B5"),
        D("B3", "B6"), D("B4", "B6"), D("B5", "B6"), D("B6", "BM"),
        D("A4", "C1"), D("C1", "C2"), D("C2", "C3"), D("C3", "C4"),
        D("BM", "D1"), D("C4", "D1"),
        D("D1", "D2"), D("D2", "D3"), D("D3", "D4"),
        D("D4", "D5", "SS", 30), D("D4", "D6", "SS", 60),
        D("D4", "DM"), D("D6", "DM"), D("DM", "CO"),
    ]
    return ProjectSpec(
        "Monterrey Townhomes", "New construction, 4% bond", 52, "Closing/financing",
        anchor, tasks, deps,
    )


# --------------------------------------------------------------------------- #
# P3 — Forest Glen Rehab: B–E with occupied-unit-turn batches, ~30 tasks.
# Staggered SS+15 rehab batches.
# --------------------------------------------------------------------------- #
def _p3() -> ProjectSpec:
    DONE = TaskStatus.COMPLETE
    GO = TaskStatus.IN_PROGRESS
    anchor = _shift_months(ANCHOR, -5)
    tasks = [
        T("B1", "Acquisition financing prep", "B.1", 25, pct=100, status=DONE),
        T("B2", "Application -> award", "B.2", 60, pct=100, status=DONE),
        T("B3", "Lender term sheet", "B.3", 20, pct=100, status=DONE),
        T("B6", "Financial closing", "B.6", 30, pct=100, status=DONE),
        T("BM", "Financial closing complete", "B.7", 0, ms=True),
        T("C1", "Rehab scope / scattered-site survey", "C.1", 25, pct=100, status=DONE),
        T("C2", "Construction documents", "C.2", 35, pct=100, status=DONE),
        T("C3", "Building permit", "C.3", 30, pct=100, status=DONE),
        T("D1", "Mobilization", "D.1", 10, pct=100, status=DONE),
        T("D2", "Common area / exterior rehab", "D.2", 60, pct=70, status=GO),
        # Occupied unit-turn batches: 4 phases of 30 units, each SS+15 off prior.
        T("U1", "Unit turns — batch 1 (30 units)", "D.3.1", 45, pct=70, status=GO),
        T("U2", "Unit turns — batch 2 (30 units)", "D.3.2", 45, pct=55, status=GO),
        T("U3", "Unit turns — batch 3 (30 units)", "D.3.3", 45, pct=40, status=GO),
        T("U4", "Unit turns — batch 4 (30 units)", "D.3.4", 45, pct=10, status=GO),
        T("DM", "Substantial completion", "D.4", 0, ms=True),
        T("CO", "Certificate of Occupancy", "D.5", 15, ms=True),
        T("E1", "Marketing / re-lease", "E.1", 30, pct=30, status=GO),
        T("E2", "Lease-up to stabilization", "E.2", 90),
        T("E3", "Placed-in-service / 8609", "E.3", 0, ms=True),
        T("E4", "Permanent loan conversion", "E.4", 30),
    ]
    deps = [
        D("B1", "B2"), D("B2", "B3"), D("B3", "B6"), D("B6", "BM"),
        D("BM", "C1"), D("C1", "C2"), D("C2", "C3"),
        D("C3", "D1"), D("D1", "D2"),
        D("D1", "U1"),
        D("U1", "U2", "SS", 15), D("U2", "U3", "SS", 15), D("U3", "U4", "SS", 15),
        D("D2", "DM"), D("U4", "DM"), D("DM", "CO"),
        D("CO", "E1", "FF", -30), D("CO", "E2"), D("E2", "E3"), D("E2", "E4"),
    ]
    return ProjectSpec(
        "Forest Glen Rehab", "Acquisition-rehab", 120, "Construction",
        anchor, tasks, deps,
    )


# --------------------------------------------------------------------------- #
# P4 — Tullis Family: A–C only (earliest stage), ~18 tasks. Entitlement-driven
# critical path. Mostly 0% complete.
# --------------------------------------------------------------------------- #
def _p4() -> ProjectSpec:
    GO = TaskStatus.IN_PROGRESS
    anchor = _shift_months(ANCHOR, 3)
    tasks = [
        T("A1", "Site identification & LOI", "A.1", 10, pct=100, status=TaskStatus.COMPLETE),
        T("A2", "Purchase & Sale Agreement", "A.2", 15, pct=40, status=GO),
        T("A3", "Due diligence (ESA, survey, geotech)", "A.3", 30, pct=10, status=GO),
        T("A4", "Site feasibility / QCT-DDA / flood screen", "A.4", 10),
        T("A5", "Preliminary site plan", "A.5", 20),
        T("B1", "9% LIHTC application prep", "B.1", 25),
        T("B2", "Application submission -> award", "B.2", 60),
        T("B3", "Lender term sheet", "B.3", 20),
        T("B4", "Syndicator/equity LOI", "B.4", 20),
        T("C1", "Schematic design", "C.1", 25),
        T("C2", "Design development", "C.2", 30),
        T("C3", "Construction documents", "C.3", 45),
        T("C4", "Zoning/entitlement approval", "C.4", 60),
        T("C5", "Building permit", "C.5", 30),
    ]
    deps = [
        D("A1", "A2"), D("A2", "A3"), D("A3", "A4", "SS"), D("A3", "A5"),
        D("A2", "B1"), D("B1", "B2"), D("B2", "B3"), D("B2", "B4"),
        D("A5", "C1"), D("C1", "C2"), D("C2", "C3"),
        D("A5", "C4"),  # entitlement parallel to design
        D("C3", "C5"), D("C4", "C5"),  # entitlement on critical path into permit
    ]
    return ProjectSpec(
        "Tullis Family", "New construction, 9% LIHTC", 100, "Predevelopment",
        anchor, tasks, deps,
    )


# --------------------------------------------------------------------------- #
# P5 — Algiers Manor: A–D with heavy site work, ~28 tasks. Earthwork + flood
# elevation fill as a long predecessor to foundations -> critical path on site.
# --------------------------------------------------------------------------- #
def _p5() -> ProjectSpec:
    DONE = TaskStatus.COMPLETE
    GO = TaskStatus.IN_PROGRESS
    anchor = _shift_months(ANCHOR, -2)
    tasks = [
        T("A1", "Site identification & LOI", "A.1", 10, pct=100, status=DONE),
        T("A2", "Purchase & Sale Agreement", "A.2", 15, pct=100, status=DONE),
        T("A3", "Due diligence", "A.3", 30, pct=100, status=DONE),
        T("A4", "Flood / elevation study", "A.4", 20, pct=100, status=DONE),
        T("B1", "Bond application prep", "B.1", 25, pct=100, status=DONE),
        T("B2", "Application -> award", "B.2", 60, pct=100, status=DONE),
        T("B6", "Financial closing", "B.6", 30, pct=100, status=DONE),
        T("BM", "Financial closing complete", "B.7", 0, ms=True),
        T("C1", "Schematic design", "C.1", 25, pct=100, status=DONE),
        T("C2", "Construction documents", "C.2", 45, pct=100, status=DONE),
        T("C3", "Building permit", "C.3", 30, pct=100, status=DONE),
        T("D1", "Mobilization", "D.1", 10, pct=100, status=DONE),
        # Heavy, long site work — the critical driver.
        T("D2", "Clearing & demolition", "D.2", 30, pct=100, status=DONE),
        T("D3", "Mass earthwork / cut & fill", "D.3", 60, pct=60, status=GO),
        T("D4", "Flood-elevation fill & compaction", "D.4", 50, pct=30, status=GO),
        T("D5", "Stormwater / underground utilities", "D.5", 40, pct=10, status=GO),
        T("D6", "Foundations", "D.6", 30),
        T("D7", "Vertical construction", "D.7", 180),
        T("D8", "MEP rough-in", "D.8", 60),
        T("D9", "Interior finishes", "D.9", 90),
        T("DM", "Substantial completion", "D.10", 0, ms=True),
        T("CO", "Certificate of Occupancy", "D.11", 15, ms=True),
    ]
    deps = [
        D("A1", "A2"), D("A2", "A3"), D("A3", "A4"),
        D("A2", "B1"), D("B1", "B2"), D("B2", "B6"), D("B6", "BM"),
        D("A4", "C1"), D("C1", "C2"), D("C2", "C3"),
        D("BM", "D1"), D("C3", "D1"),
        D("D1", "D2"), D("D2", "D3"),
        D("D3", "D4"),  # flood fill after mass earthwork
        D("D4", "D5"), D("D5", "D6"),  # long site chain precedes foundations
        D("D6", "D7"),
        D("D7", "D8", "SS", 30), D("D7", "D9", "SS", 60),
        D("D7", "DM"), D("D9", "DM"), D("DM", "CO"),
    ]
    return ProjectSpec(
        "Algiers Manor", "New construction, hybrid elevation", 124, "Site work",
        anchor, tasks, deps,
    )


def _wipe_existing(session: Session, names: list[str]) -> None:
    existing = [p for p in project_repo.list_all(session) if p.name in names]
    for project in existing:
        task_ids = [t.id for t in task_repo.list_for_project(session, project.id)]
        if task_ids:
            session.execute(
                delete(Dependency).where(
                    Dependency.successor_id.in_(task_ids)
                    | Dependency.predecessor_id.in_(task_ids)
                )
            )
            session.execute(delete(Task).where(Task.id.in_(task_ids)))
        session.execute(delete(Project).where(Project.id == project.id))
    session.commit()


def seed_all(session: Session) -> list[int]:
    """Seed all 5 projects (idempotent). Returns the created project ids."""
    specs = [_p1(), _p2(), _p3(), _p4(), _p5()]
    _wipe_existing(session, [s.name for s in specs])
    return [_build(session, spec) for spec in specs]
