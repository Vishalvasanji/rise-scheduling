"""Task CRUD endpoints. All writes go through the scheduling service (single
recalc + validation + audit path)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import ActorDep, SessionDep
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import scheduling_service

router = APIRouter(tags=["tasks"])


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
)
def create_task(project_id: int, payload: TaskCreate, session: SessionDep, actor: ActorDep):
    task, _ = scheduling_service.create_task(
        session, project_id, payload.model_dump(exclude_unset=True), actor=actor
    )
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, session: SessionDep, actor: ActorDep):
    task, _ = scheduling_service.update_task(
        session, task_id, payload.model_dump(exclude_unset=True), actor=actor
    )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: SessionDep, actor: ActorDep):
    scheduling_service.delete_task(session, task_id, actor=actor)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, session: SessionDep):
    from app.repositories import task_repo

    task = task_repo.get(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
