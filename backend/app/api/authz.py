"""Project-level access checks. Admins can access every project; members only the
projects assigned to them. Used by the routers to hide AND block unassigned work."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import task_repo, user_repo


def can_access_project(session: Session, user: User, project_id: int) -> bool:
    if user.role == "admin":
        return True
    return project_id in set(user_repo.assigned_project_ids(session, user.id))


def assert_project_access(session: Session, user: User, project_id: int) -> None:
    if not can_access_project(session, user, project_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )


def assert_task_access(session: Session, user: User, task_id: int):
    """Resolve a task to its project and check access. Returns the task (404 if
    missing) so callers can reuse it."""
    task = task_repo.get(session, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")
    assert_project_access(session, user, task.project_id)
    return task
