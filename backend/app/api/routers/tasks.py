"""Task CRUD endpoints. All writes go through the scheduling service (single
recalc + validation + audit path)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.authz import assert_project_access, assert_task_access
from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import scheduling_service

router = APIRouter(tags=["tasks"])


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
)
def create_task(project_id: int, payload: TaskCreate, session: SessionDep, user: CurrentUserDep):
    assert_project_access(session, user, project_id)
    task, _ = scheduling_service.create_task(
        session, project_id, payload.model_dump(exclude_unset=True), actor=user.email
    )
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, session: SessionDep, user: CurrentUserDep):
    assert_task_access(session, user, task_id)
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("expected_version", None)
    force = data.pop("force", False)
    task, _ = scheduling_service.update_task(
        session, task_id, data, actor=user.email,
        expected_version=expected_version, force=force,
    )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: SessionDep, user: CurrentUserDep):
    assert_task_access(session, user, task_id)
    scheduling_service.delete_task(session, task_id, actor=user.email)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, session: SessionDep, user: CurrentUserDep):
    return assert_task_access(session, user, task_id)
