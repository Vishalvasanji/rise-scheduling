"""Task table — the central scheduling entity.

Carries both the editable planning fields and the columns computed by the CPM
engine on every write (early/late start/finish, float, critical flag). Computed
fields are persisted (not derived on read) so the Gantt GET is a plain read and
chat + web stay consistent.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaskStatus


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "wbs", name="uq_task_project_wbs"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    wbs: Mapped[str | None] = mapped_column(String, nullable=True)
    # Responsible trade (free text, e.g. "Electrical"). Nullable; client-editable.
    trade: Mapped[str | None] = mapped_column(String, nullable=True)
    # Building this task belongs to (e.g. "Building 13", "Clubhouse"). Nullable;
    # populated structurally (e.g. by the Lake Jackson import from the WBS prefix).
    building: Mapped[str | None] = mapped_column(String, nullable=True)

    # Planning inputs.
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    percent_complete: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[TaskStatus] = mapped_column(
        String, nullable=False, default=TaskStatus.NOT_STARTED
    )
    is_milestone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Actuals (nullable). When present, they pin the bar during CPM.
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Computed by the engine on every recalc.
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    late_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    late_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_float: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_float: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Design-for-Procore: reserved external identity (nullable).
    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    procore_id: Mapped[str | None] = mapped_column(String, nullable=True)

    project: Mapped[Project] = relationship(back_populates="tasks")  # noqa: F821
