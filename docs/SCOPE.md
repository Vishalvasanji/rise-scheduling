# Project Scope — RISE Schedule Hub

**Deliverable for:** Claude Code
**Owner:** Vishal Vasanji, RISE Residential
**Status:** v1 scope, pilot phase
**Last updated:** June 22, 2026

---

## 1. One-line summary

A centralized scheduling system for 4–5 active development projects. All users — field, PM, leadership — update and query schedules by chatting with Claude, and a web app provides full create/edit/delete/view. Procore sync is a later, separate phase; the pilot is designed so it bolts on without rework.

---

## 2. Objective

- Stand up a standalone, working schedule system in the pilot — no Procore dependency.
- Make one schedule the source of truth across all active projects.
- All users interact via Claude chat **and** a web app.
- Let Claude do the heavy lifting: build, update, recalculate, and report.
- Design the data model and seams so a two-way Procore bridge attaches later cleanly.

---

## 3. Locked decisions

| Decision | Choice |
|---|---|
| Pilot scope | Standalone schedule system (DB + engine + chat + web). **No Procore in pilot.** |
| Procore sync | **Separate later phase.** Designed-for in pilot, not built. |
| Database | **Turso (libSQL/SQLite)** to start |
| Field/PM/leadership interaction | **All users** chat with Claude to create, update, query |
| UI surfaces | (1) Claude chat (all users), (2) **React** web app with full CRUD + **interactive Gantt** (drag tasks, edit dependencies, live critical-path) |
| Front-end hosting | Vercel (React front end). Render hosts the FastAPI JSON API + MCP + cron. |
| Claude ↔ data connection | MCP server (same pattern as the rise-markets pipeline) |
| Who can write to master | Both web app and chat |
| Auth (pilot) | In-house, basic — standard libraries (bcrypt/argon2 + session cookies), behind one swappable module. Per-user logins; RBAC deferred to production. |
| Hosting (pilot) | Render hosts FastAPI API + MCP + cron; Vercel hosts React front end. Bursty usage (free tier survivable; ~$7/mo before demos). |
| Master location | Personal stack for pilot → production migration later |

---

## 4. Architecture overview (pilot)

```
   Field ─┐
   PM ─────┼─► Claude (chat) ──► MCP server ─┐
   Leadership ─► Web app (CRUD) ─────────────┤
                                             ▼
                                    Scheduling engine
                                     (critical path,
                                      date roll-up, slack)
                                             │
                                             ▼
                                     Turso (libSQL) master
                                             │
                                  ┌──────────┘
                                  ▼
                      [ future seam: Procore bridge adapter ]
                          (not built in pilot — see §7)
```

**Single source of truth = Turso master.** Chat and web both write through the same engine + validation + audit log (one path, not two).

---

## 5. Components to build (pilot)

### 5.1 Data layer — Turso (libSQL)
- libSQL = SQLite dialect. Local dev = a SQLite file; shared/pilot = Turso Cloud. Cheap, fast, low-ops — good fit for 4–5 projects and a few users.
- **Wrap all DB access behind a data-access/ORM layer** (see §8 stack note) so the engine target can later be swapped to Postgres if production governance requires it. Do not scatter raw libSQL calls through the app.
- Core tables: `projects`, `tasks`, `dependencies`, `milestones`, `resources`, `users`, `audit_log`.
- Concurrency note: libSQL is single-writer. Fine at this scale; writes are serialized through the engine anyway.

### 5.2 Scheduling engine
- Critical path (CPM): early/late start/finish, total float/slack.
- Dependency types (FS, SS, FF, SF) + lag.
- Date roll-up: task → milestone → project.
- Constraint validation: circular-dependency detection, date conflicts.
- Recalc on every write (chat or web).

### 5.3 MCP server (chat interface — all users)
- Same pattern as the existing rise-markets MCP work.
- Initial tools:
  - `get_schedule(project_id)`
  - `update_task(task_id, fields)` — progress %, dates, status
  - `create_task(project_id, fields)`
  - `delete_task(task_id)`
  - `list_projects()`
  - `get_critical_path(project_id)`
  - `generate_report(scope, type)` — leadership digest, slippage, what-changed
- All writes route through the same engine + audit log as the web app.

### 5.4 Web app (React CRUD UI + interactive Gantt)
- Full create / edit / delete / view: projects, tasks, milestones, dependencies.
- **Interactive Gantt** is a centerpiece: drag to reschedule, edit dependencies visually, critical path updates live. Consumes the FastAPI JSON API.
- Views: task grid, interactive Gantt, milestone roll-up, cross-project leadership dashboard (read).
- **Use a Gantt library — do not hand-build.** Drag + dependency editing + critical-path rendering from scratch is a deep rabbit hole. Evaluate at scaffolding:
  - Open-source (free, more wiring): e.g., `frappe-gantt`, `react-gantt-task` / `gantt-task-react`.
  - Commercial (richer drag/dependency UX, license cost): e.g., Bryntum, DHTMLX, Syncfusion.
  - This is the one spot where free-only may trade money for build time — decide consciously.
- All users access; granular per-role write rules deferred (§9).

### 5.5 Reporting
- Leadership digest, slippage report, what-changed-since report — generated on demand via chat or web.

---

## 6. Designed-for-Procore principles (apply in pilot, build later)

The pilot must not paint into a corner. While building, hold to:
- **Task schema maps cleanly to Procore / `.xer`:** stable task IDs, WBS/hierarchy, dependency types + lag, % complete, calendars, start/finish. These are the fields a future `.xer` export or API push will need.
- **Keep a clean export seam:** the master schedule should be readable by a single adapter module later (no logic that assumes Procore will never exist).
- **Internal IDs stable and external-ID-ready:** reserve a nullable `procore_id` / `external_ref` on tasks and projects now, so later sync can reconcile without a schema migration.

---

## 7. Procore bridge — SEPARATE LATER PHASE (not pilot)

Documented here for design alignment only. Build after the pilot proves out.
- **Two-way (push + pull)** is the eventual target.
- **Pull:** read Procore schedule via API GET endpoints (confirmed available).
- **Push (path TBD):** Path A — Procore API write (if a schedule write/integration endpoint exists); Path B — `.xer` export via MPXJ → Procore Scheduling tool import (manual / Procore Drive / overnight Cowork job). Native `.mpp`/Asta/Phoenix are not writable by open tooling; `.xer` is the viable file path.
- **Phase-entry spikes (resolve before building this phase):**
  1. Does Procore's schedule API support write/integration POST? (Y/N → Path A vs. B)
  2. Does import update existing tasks or only create? (dupe risk)
  3. Old Schedule tool vs. new Scheduling tool in use?
  4. Does MPXJ `.xer` import cleanly (version compatibility)?

---

## 8. Tech stack

- **DB:** Turso (libSQL) — SQLite file locally, Turso Cloud shared.
- **Language:** Python (locked) — matches the existing skill toolkit and rise-markets MCP pattern.
- **Backend:** FastAPI, containerized (Docker). Runs identically local → production host.
- **Data-access abstraction:** SQLAlchemy (Core or ORM) targeting **both libSQL and Postgres**, so a later libSQL→Postgres swap is a dialect/URL change, not a rewrite. All DB access goes through this layer — no raw libSQL calls scattered in the app. libSQL connects via the SQLAlchemy SQLite dialect over the libSQL driver (`sqlalchemy-libsql` / libSQL SQLAlchemy dialect).
- **MCP server:** Python MCP SDK, sharing the same engine + data-access layer as the API.
- **Web app:** React (Vite or Next.js) on Vercel, consuming the FastAPI JSON API. Interactive Gantt via a dedicated Gantt library (§5.4) — not hand-built.
- **Auth:** in-house, basic (pilot). Standard libraries only — `passlib` with bcrypt/argon2 for password hashing, httpOnly secure session cookies or short-lived JWT (`python-jose`/`authlib`). No custom crypto, no plaintext. Behind one auth module → swaps to Entra ID in production.
- **Hosting:** Render runs the FastAPI JSON API + MCP server + Render Cron Jobs; Vercel hosts the React front end. Docker-native backend, so the same container lifts to Azure later. Free tier for dev (bursty usage tolerates cold starts); move always-on services to ~$7/mo tier before leadership demos.
- **Secrets/config:** env vars only.

---

## 9. Out of scope for pilot

- Procore sync (separate phase — §7).
- Granular role-based permissions (field vs. leadership write rules) — production.
- Native `.mpp`, Asta, Phoenix generation — not feasible with open tooling.
- High-concurrency real-time multi-user editing — light edit discipline assumed.
- Native mobile app — chat + responsive web only.
- Production security hardening — gated to migration.

---

## 10. Phasing

| Phase | Goal | Exit criteria |
|---|---|---|
| **1 — Core pilot** | DB + engine + MCP chat (all users) + web CRUD, **dummy data**, Turso | Create/update/delete tasks via chat AND web; engine recalculates critical path + roll-ups |
| **2 — Reporting + automation** | Dashboards, leadership digests, what-changed | One-command leadership report from chat or web |
| **3 — Procore bridge** | Separate phase: spikes → pull → push (§7) | Procore data pulls in; master pushes to Procore read view |
| **4 — Production** | Migrate compute to Azure; data-residency decision; RBAC; Entra ID | Security sign-off; real-data go-live with role-based access |

---

## 11. Hard constraints

- **No real company data on personal/pilot infrastructure.** Pilot = synthetic/dummy projects only. Real deal data goes live only after the production migration + security review.
- **In-house auth is pilot-only.** Acceptable solely because of dummy data + a handful of internal users. Before real data: swap to Entra ID **and** complete a security review. Hand-rolled auth must never carry real pipeline data.
- **Portability by construction:** DB access behind one ORM/abstraction; auth behind one module; config in env. SQLite/libSQL now must not block a Postgres/Azure target later.
- **Single validation path:** chat and web writes share one engine, validation, and audit log.
- **Design-for-Procore (§6) held throughout the pilot**, even though sync isn't built until Phase 3.

---

## 12. Open decisions / risks

| # | Question | Impact | When |
|---|---|---|---|
| 1 | **Gantt library:** open-source (free, more wiring) vs. commercial (richer, license cost)? | UI quality vs. build time + cost | At scaffolding |
| 2 | Production **data residency**: keep data in Turso Cloud, or move to company Azure tenant? | Decides if a libSQL→Postgres migration is ever needed | Phase 4 |
| 3 | Company sanction for **Azure subscription + deploy rights**? | Gates Phase 4 | Before Phase 3 |
| 4 | Procore phase-entry spikes (§7) | Decides Procore push path | Start of Phase 3 |

---

## 13. Immediate next step for Claude Code

1. **Pick the Gantt library (§12 #1)** — open-source vs. commercial.
2. Scaffold the repo: Turso schema + migrations via SQLAlchemy, FastAPI backend, MCP server stub, Docker; React front end on Vercel.
3. Build the scheduling engine (CPM + roll-ups) against dummy data.
4. Stand up chat (MCP) + React web CRUD against the same engine + data-access layer.
5. Wire the interactive Gantt to the JSON API.
6. Hold the design-for-Procore principles (§6) — including the nullable `external_ref` fields — from the first migration.
