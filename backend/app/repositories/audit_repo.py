"""Audit-log data access."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    session: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
    project_id: int | None,
    summary: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        summary=summary,
        before=json.dumps(before, default=str) if before is not None else None,
        after=json.dumps(after, default=str) if after is not None else None,
    )
    session.add(entry)
    session.flush()
    return entry


def list_for_project(session: Session, project_id: int, limit: int = 100) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.project_id == project_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
    )


def list_recent(session: Session, limit: int = 200) -> list[AuditLog]:
    """Most recent activity across all projects (admin)."""
    return list(
        session.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
    )
