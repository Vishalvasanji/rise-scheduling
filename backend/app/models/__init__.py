"""SQLAlchemy ORM models. Importing this package registers all tables on
``Base.metadata`` (used by Alembic autogenerate and ``create_all`` in tests)."""

from app.models.audit_log import AuditLog
from app.models.dependency import Dependency
from app.models.enums import DependencyTypeEnum, TaskStatus
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.resource import Resource
from app.models.task import Task
from app.models.user import User

__all__ = [
    "AuditLog",
    "Dependency",
    "DependencyTypeEnum",
    "TaskStatus",
    "Milestone",
    "Project",
    "Resource",
    "Task",
    "User",
]
