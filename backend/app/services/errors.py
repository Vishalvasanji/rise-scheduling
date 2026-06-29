"""Service-layer errors (distinct from the engine's scheduling errors)."""

from __future__ import annotations

from datetime import datetime


class ConflictError(Exception):
    """Raised on a stale write: the task's version no longer matches what the
    editor last saw. Carries who changed it (and when) so the UI can ask the user
    whether to overwrite."""

    def __init__(
        self,
        task_id: int,
        current_version: int,
        updated_by: str | None,
        updated_at: datetime | None,
    ) -> None:
        self.task_id = task_id
        self.current_version = current_version
        self.updated_by = updated_by
        self.updated_at = updated_at
        super().__init__(
            f"Task {task_id} was changed by {updated_by or 'someone'} "
            f"(now version {current_version})"
        )
