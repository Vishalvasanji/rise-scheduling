# Deploying the RISE Schedule Hub pilot

The pilot has **two tiers** that must both be hosted and pointed at each other:

| Tier | Host | What it is |
|------|------|------------|
| Frontend | **Vercel** | React/Vite SPA (`/frontend`) — no data of its own |
| Backend | **Render** | FastAPI JSON API (`/backend`), Docker |
| Database | **Turso (libSQL)** | Persistent shared DB (SCOPE §8) |

> The frontend only renders data it fetches from the backend, so deploying to
> Vercel alone shows an empty app. You must deploy the backend (Render) and a
> database (Turso) too.

---

## A. Turso database (one-time, from your machine)

You need the [Turso CLI](https://docs.turso.tech/cli/installation) and your account.

```bash
turso db create rise-schedule-hub
turso db show rise-schedule-hub --url          # -> libsql://<db-host>
turso db tokens create rise-schedule-hub       # -> <auth-token>
```

Build the SQLAlchemy URL (note the `sqlite+libsql://` dialect prefix and
`secure=true`):

```
sqlite+libsql://<db-host>/?authToken=<auth-token>&secure=true
```

Create the schema and seed the 5 dummy projects **into Turso** from `/backend`:

```bash
cd backend
source .venv/bin/activate            # the venv with sqlalchemy-libsql installed
export DATABASE_URL='sqlite+libsql://<db-host>/?authToken=<auth-token>&secure=true'
alembic upgrade head
python -m app.seed.run_seed
```

You should see `Seeded 5 projects: [1, 2, 3, 4, 5]`. (If Alembic misbehaves over
libSQL, fall back to `python -c "from app.db.base import Base; from app.db.engine
import get_engine; import app.models; Base.metadata.create_all(get_engine())"`
then re-run the seed — same end state for the pilot.)

---

## B. Backend on Render

1. **New → Blueprint** and select this repo (Render reads `backend/render.yaml`).
   Or **New → Web Service**, runtime **Docker**, root directory `backend`.
2. Service name `rise-schedule-hub-api` → URL
   `https://rise-schedule-hub-api.onrender.com`.
3. Set environment variables (Dashboard → Environment):
   - `DATABASE_URL` = the Turso URL from step A
   - `AUTH_SECRET` = any long random string
   - `FRONTEND_ORIGIN` = `https://rise-schedule-hub.vercel.app` (your planned
     Vercel URL; comma-separate more if needed)
   - `PILOT_ANCHOR_DATE` = `2026-06-22` (already defaulted in `render.yaml`)
4. Deploy, then verify:
   ```bash
   curl https://rise-schedule-hub-api.onrender.com/health      # {"status":"ok"}
   curl https://rise-schedule-hub-api.onrender.com/projects     # 5 projects
   ```

> Render's free tier sleeps after inactivity, so the first request after idle is
> slow (cold start). Move to the ~$7/mo tier before leadership demos.

---

## C. Frontend on Vercel

1. **Add New → Project**, import this repo.
2. **Root Directory = `frontend`** (Vercel auto-detects Vite; `frontend/vercel.json`
   sets the build + SPA rewrite).
3. Environment variable:
   - `VITE_API_BASE_URL` = `https://rise-schedule-hub-api.onrender.com`
4. Deploy and open the production URL.

---

## D. Close the CORS loop

If the real Vercel production URL differs from what you set in `FRONTEND_ORIGIN`
(step B3), update `FRONTEND_ORIGIN` on Render to the actual URL and redeploy the
backend. That is the only second deploy needed.

---

## Verify end-to-end

1. Open the Vercel URL — the sidebar lists 5 projects + the leadership dashboard.
2. Open **Cedar Pointe BTR** → the Gantt renders with **red critical-path bars**
   and milestone diamonds; the task grid shows computed dates and float.
3. **Drag a task bar** → its dependents shift; refresh and the change persists
   (proves the Turso write-through + recalculation path).
4. Browser **Network** tab: requests hit the Render origin with no CORS errors.

## Notes

- The pilot app allows anonymous read/write (the audit log records `anonymous`),
  so there is no login wall — convenient for a shared demo. Swap to real auth
  (Entra ID) before any real data (SCOPE §11).
- No secrets are committed. All credentials live in Render/Vercel env vars; the
  local `.env` is gitignored.
