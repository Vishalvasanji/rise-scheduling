"""FastAPI application factory. Registers routers, CORS, and global handlers
that translate engine errors into HTTP responses (cycle -> 409, date conflict
-> 422), so the same engine errors surface consistently across every route."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import (
    audit,
    auth,
    dependencies,
    projects,
    proposals,
    reports,
    tasks,
    users,
)
from app.config import get_settings
from app.engine.errors import CircularDependencyError, DateConflictError, SchedulingError
from app.services.errors import BulkConflictError, ConflictError

logger = logging.getLogger(__name__)

# Backend root (…/backend), which contains the migrations/ directory.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Readiness gate. Defaults True so tests and manual-migration setups aren't gated;
# real startup flips it False (when migrate_on_startup is on) until the background
# DB init finishes. A dict so the middleware always sees the live value.
_ready = {"db": True}

# Paths served even while the DB is still initializing (they touch no DB).
_READINESS_EXEMPT = ("/health", "/openapi.json", "/docs", "/redoc")


def _migrate_and_seed() -> None:
    """Apply migrations then run the idempotent seeds. Runs in a worker thread off
    the event loop; raises on any failure so the caller can retry."""
    from alembic import command
    from alembic.config import Config

    # Build the Alembic config in code (no ini file) so its fileConfig() call can't
    # reconfigure the app's logging. env.py reads DATABASE_URL from settings and
    # waits for the DB itself.
    cfg = Config()
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    command.upgrade(cfg, "head")

    from app.seed import admin_user, lake_jackson, run_seed

    run_seed.main(if_empty=True)  # 5 dummy projects + demo user, only if DB is empty
    lake_jackson.main()  # Lake Jackson demo project (idempotent)
    admin_user.main()  # admin account (idempotent)


async def _prepare_database() -> None:
    """Background task: migrate + seed, retrying forever with backoff so a cold or
    briefly-unreachable Turso never blocks the server from binding its port. Flips
    the readiness flag once done; DB routes 503 until then."""
    loop = asyncio.get_running_loop()
    delay = 5.0
    while True:
        try:
            await loop.run_in_executor(None, _migrate_and_seed)
            _ready["db"] = True
            logger.info("Database ready: migrations applied and seed complete.")
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Database init failed; retrying in %.0fs.", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Decouple boot from the DB: bind the port and serve /health immediately, and
    # migrate + seed in the background. A cross-region cold start (Render↔Turso) or
    # a transient 502 then can't fail the deploy — the app self-heals when the DB
    # answers. Turn off with MIGRATE_ON_STARTUP=0 to manage migrations yourself.
    task: asyncio.Task[None] | None = None
    if get_settings().migrate_on_startup:
        _ready["db"] = False
        task = asyncio.create_task(_prepare_database())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="RISE Schedule Hub API", version="0.1.0", lifespan=lifespan)

    # While the background DB init runs, DB-backed routes return a clean 503 (with
    # Retry-After) instead of 500s. Registered before CORS so the CORS layer stays
    # outermost and still adds its headers to these 503 responses.
    @app.middleware("http")
    async def _db_readiness_gate(request: Request, call_next):  # noqa: ANN001,ANN202
        if (
            not _ready["db"]
            and request.method != "OPTIONS"
            and not request.url.path.startswith(_READINESS_EXEMPT)
        ):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "starting_up",
                    "detail": "Database is initializing; retry shortly.",
                },
                headers={"Retry-After": "5"},
            )
        return await call_next(request)

    # FRONTEND_ORIGIN may be a comma-separated list (e.g. the Vercel prod URL plus
    # localhost for dev), so the same backend serves local and hosted front ends.
    allowed_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(CircularDependencyError)
    async def _cycle_handler(_request: Request, exc: CircularDependencyError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "circular_dependency", "cycle": exc.cycle, "detail": str(exc)},
        )

    @app.exception_handler(DateConflictError)
    async def _date_handler(_request: Request, exc: DateConflictError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "date_conflict", "task_id": exc.task_id, "reason": exc.reason},
        )

    @app.exception_handler(ConflictError)
    async def _conflict_handler(_request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "version_conflict",
                "task_id": exc.task_id,
                "current_version": exc.current_version,
                "updated_by": exc.updated_by,
                "updated_at": exc.updated_at.isoformat() if exc.updated_at else None,
                "detail": str(exc),
            },
        )

    @app.exception_handler(BulkConflictError)
    async def _bulk_conflict_handler(_request: Request, exc: BulkConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "bulk_version_conflict",
                "conflicts": exc.conflicts,
                "detail": str(exc),
            },
        )

    @app.exception_handler(SchedulingError)
    async def _sched_handler(_request: Request, exc: SchedulingError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "scheduling_error", "detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def _value_handler(_request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "bad_request", "detail": str(exc)},
        )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(projects.router)
    app.include_router(proposals.router)
    app.include_router(tasks.router)
    app.include_router(dependencies.router)
    app.include_router(reports.router)
    app.include_router(audit.router)
    return app


app = create_app()
