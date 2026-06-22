"""Milestone table.

A milestone in the schedule is a zero-duration ``Task`` (the engine handles it
with no special case). This table provides an optional named view / grouping of
significant milestone tasks for reporting and the milestone roll-up view, linking
to the underlying task. Kept separate so reporting can label milestones
(e.g. "Financial Closing", "Placed-in-service / 8609") without overloading tasks.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)
