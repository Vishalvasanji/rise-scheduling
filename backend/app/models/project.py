"""Project table."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    deal_type: Mapped[str | None] = mapped_column(String, nullable=True)
    units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)

    # Schedule anchor for this project's CPM index space.
    anchor_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Optional WBS-prefix -> display label map for roll-up rows (e.g. "1.1" ->
    # "Clubhouse"). Null/absent prefixes fall back to the raw WBS code.
    wbs_labels: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # One in-flight "what-if" proposal (from chat or the API): the proposed
    # mutations + metadata. Null when there's nothing pending. The proposed
    # schedule is computed on read; "apply" replays the mutations for real.
    pending_proposal: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Computed roll-up (task -> project), refreshed on every recalc.
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_finish: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Design-for-Procore: reserved external identity (nullable, no migration later).
    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    procore_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    tasks: Mapped[list[Task]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
