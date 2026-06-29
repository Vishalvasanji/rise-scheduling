"""Change-activity (audit) response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    source: str  # web | chat (chat = made via the Claude.ai connector)
    action: str  # create | update | delete
    entity_type: str  # task | dependency
    entity_id: int | None
    project_id: int | None
    summary: str | None
    created_at: datetime
