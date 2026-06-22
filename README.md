# RISE Schedule Hub

A centralized scheduling system for RISE Residential's active LIHTC development
projects. The pilot is a **standalone** system (no Procore dependency) with two
user-facing surfaces backed by **one** scheduling engine and validation path:

- **Claude chat** via an MCP server (`/backend/app/mcp`)
- **React web app** with full CRUD + an interactive Gantt (`/frontend`)

See [`SCOPE.md`](./docs/SCOPE.md) for the full pilot scope and
[`dummydata.md`](./docs/dummydata.md) for the synthetic seed data spec.

## Repository layout

```
/backend     FastAPI JSON API + MCP server + pure CPM scheduling engine
/frontend    React + Vite web app with gantt-task-react
/docs        Scope and dummy-data specifications
```

## Architecture

```
 Field ─┐
 PM ─────┼─► Claude (chat) ──► MCP server ─┐
 Leadership ─► Web app (CRUD) ─────────────┤
                                           ▼
                                  Scheduling service  ──► CPM engine
                                  (single write path)     (critical path,
                                           │                roll-up, slack)
                                           ▼
                                  SQLAlchemy data-access
                                           │
                                  SQLite (pilot) ─► Turso / Postgres (later)
```

Both the web app and chat write through the **same** `scheduling_service`, which
mutates, recalculates the critical path, validates (rejecting circular
dependencies and date conflicts), and writes the audit log inside one transaction.

## Quick start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head          # create the schema
python -m app.seed.run_seed   # seed 5 dummy LIHTC projects
uvicorn app.api.main:app --reload
```

Run the MCP server:

```bash
python -m app.mcp.server
```

Run the tests:

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Design-for-Procore

The pilot holds the Procore-ready seams from the first migration: stable internal
IDs, WBS/hierarchy codes, dependency type + lag, % complete, working-day
calendar, start/finish, and nullable `external_ref` / `procore_id` fields. A
future Procore bridge attaches through a single adapter without a schema
migration. Sync itself is a later phase (SCOPE §7).
