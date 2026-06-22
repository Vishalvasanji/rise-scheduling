"""Dependency table — typed, lagged precedence edges between tasks."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DependencyTypeEnum


class Dependency(Base):
    __tablename__ = "dependencies"
    __table_args__ = (
        UniqueConstraint(
            "predecessor_id", "successor_id", name="uq_dependency_pred_succ"
        ),
        CheckConstraint("predecessor_id != successor_id", name="ck_dependency_no_self"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    predecessor_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    successor_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[DependencyTypeEnum] = mapped_column(
        String, nullable=False, default=DependencyTypeEnum.FS
    )
    lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Computed: edge lies on the critical path.
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
