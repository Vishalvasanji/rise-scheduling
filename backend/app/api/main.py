"""FastAPI application factory. Registers routers, CORS, and global handlers
that translate engine errors into HTTP responses (cycle -> 409, date conflict
-> 422), so the same engine errors surface consistently across every route."""

from __future__ import annotations

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
from app.services.errors import ConflictError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="RISE Schedule Hub API", version="0.1.0")

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
