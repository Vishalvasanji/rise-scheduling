"""Dependency request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import DependencyTypeEnum


class DependencyCreate(BaseModel):
    predecessor_id: int
    successor_id: int
    type: DependencyTypeEnum = DependencyTypeEnum.FS
    lag_days: int = 0


class DependencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    predecessor_id: int
    successor_id: int
    type: DependencyTypeEnum
    lag_days: int
    is_critical: bool
