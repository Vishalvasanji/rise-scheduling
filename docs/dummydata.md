# Dummy Data Spec — RISE Schedule Hub Pilot

**Purpose:** Synthetic but realistic LIHTC development schedules to build and test the scheduling engine, chat, and Gantt against real-world structures. **No real deal data** (per SCOPE §11) — names/addresses are fictional, shapes are authentic.

**Use:** seed Turso with these on first migration. Cover the edge cases the engine must handle: long lead-time financing tasks, parallel workstreams, FS/SS/FF dependencies with lag, milestones, and a critical path that runs through financing + construction.

---

## Seed: 5 projects (mix of deal types + stages)

| ID | Project | Type | Units | Stage at seed | Why included (test coverage) |
|----|---------|------|-------|---------------|------------------------------|
| P1 | Cedar Pointe BTR | New construction, 4% bond | 80 | Pre-construction | Full lifecycle, long financing lead time |
| P2 | Monterrey Townhomes | New construction, 4% bond | 52 | Closing/financing | Financing-heavy critical path |
| P3 | Forest Glen Rehab | Acquisition-rehab | 120 | Construction | Rehab phasing, occupied-unit turns |
| P4 | Tullis Family | New construction, 9% LIHTC | 100 | Predevelopment | Earliest stage, entitlement-driven |
| P5 | Algiers Manor | New construction, hybrid elevation | 124 | Site work | Sitework/earthwork + flood-elevation tasks |

---

## Task taxonomy (phases every project draws from)

Use these standard LIHTC phases; not every project uses every task. Durations in working days.

### Phase A — Predevelopment / Site Control
- Site identification & LOI — 10d
- Purchase & Sale Agreement — 15d
- Due diligence (Phase I ESA, survey, geotech) — 30d
- Site feasibility / QCT-DDA / flood screen — 10d
- Preliminary site plan — 20d

### Phase B — Financing
- LIHTC/bond application prep — 25d
- Application submission → award — 60d *(long lead; milestone)*
- Lender term sheet — 20d
- Syndicator/equity LOI — 20d
- Gap financing (CDBG-DR / soft sources) — 40d
- Financial closing — 30d *(major milestone)*

### Phase C — Design & Entitlement
- Schematic design — 25d
- Design development — 30d
- Construction documents — 45d
- Zoning/entitlement approval — 60d *(can run parallel to design)*
- Building permit — 30d

### Phase D — Construction
- Mobilization — 10d
- Site work / earthwork — 40d
- Foundations — 30d
- Vertical construction — 180d
- MEP rough-in — 60d (SS+30 off vertical)
- Interior finishes — 90d (SS+60 off vertical)
- Site amenities / landscaping — 40d
- Substantial completion — milestone
- Certificate of Occupancy — 15d *(milestone)*

### Phase E — Lease-up & Stabilization
- Marketing launch — starts FF-30 before CO
- Lease-up to stabilization — 120d
- Placed-in-service / 8609 — milestone
- Permanent loan conversion — 30d

---

## Dependency patterns to encode (engine must handle all four)

- **FS (finish-to-start):** Foundations → Vertical construction.
- **SS+lag (start-to-start with lag):** Vertical → MEP rough-in (SS+30); Vertical → Interior finishes (SS+60).
- **FF-lag (finish-to-finish):** Marketing launch → CO (FF-30, marketing finishes 30d before CO).
- **Cross-phase gate:** Financial closing (B) is a hard predecessor to Mobilization (D) — no construction before close. This should sit on the critical path.

---

## Edge cases to seed (so the engine is tested, not just populated)

1. **Parallel workstreams converging:** Design (C) and Entitlement run parallel, both must finish before Permit. Tests float calculation on the non-critical branch.
2. **Long-lead milestone:** Application→award (60d) with downstream tasks waiting. Tests milestone roll-up.
3. **Negative-lag finish:** Marketing FF-30 before CO. Tests FF with lag.
4. **Occupied rehab phasing (P3):** unit-turn tasks in batches (e.g., 4 phases of 30 units, each SS+15 off the prior). Tests staggered SS chains.
5. **Sitework-heavy start (P5):** earthwork + flood-elevation fill as a predecessor to foundations, longer than normal. Tests critical-path shifting onto site work.
6. **One deliberately slipped task:** set one P2 financing task behind schedule (actual > planned) so slippage reports and what-changed have something to show.
7. **A circular dependency (in a test fixture only, not seed):** to verify the engine *rejects* it.

---

## Per-project seed targets

- **P1 Cedar Pointe:** full A–E, ~35 tasks, critical path through Financing → Construction. The "complete reference" project.
- **P2 Monterrey:** A–D, ~25 tasks, critical path through Financing (closing slips). Carries the slipped-task edge case.
- **P3 Forest Glen:** B–E with rehab unit-turn batches, ~30 tasks. Carries staggered-SS edge case.
- **P4 Tullis:** A–C only (early stage), ~18 tasks, entitlement on critical path.
- **P5 Algiers Manor:** A–D with heavy site work, ~28 tasks. Carries sitework-critical-path edge case.

---

## Field shape per task (matches SCOPE §6 design-for-Procore)

```
task:
  id (internal, stable)
  project_id
  name
  wbs / hierarchy code
  planned_start, planned_finish
  actual_start, actual_finish (nullable)
  duration_days
  percent_complete
  status (not_started | in_progress | complete | blocked)
  is_milestone (bool)
  external_ref / procore_id (nullable — reserved for Phase 3)
dependency:
  predecessor_id, successor_id
  type (FS | SS | FF | SF)
  lag_days (can be negative)
```

---

## Notes

- Working-day calendar (Mon–Fri), no holidays for pilot — keep the calendar simple; production adds holiday calendars.
- Dates: anchor P1 start at a fixed pilot date (e.g., today) so the Gantt renders a sensible window; stagger the others ±3 months around it.
- Keep percent_complete realistic to each project's stage (P4 mostly 0%, P3 construction tasks 40–70%, etc.) so dashboards look real in demos.
