"""Enumerations shared by models and schemas."""

from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class DependencyTypeEnum(str, Enum):
    FS = "FS"  # finish-to-start
    SS = "SS"  # start-to-start
    FF = "FF"  # finish-to-finish
    SF = "SF"  # start-to-finish
