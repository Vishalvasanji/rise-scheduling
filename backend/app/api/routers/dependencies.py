"""Dependency endpoints. Creating a dependency that would form a cycle is
rejected by the engine (HTTP 409) before anything is persisted."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.authz import assert_task_access
from app.api.deps import CurrentUserDep, SessionDep
from app.repositories import dependency_repo
from app.schemas.dependency import DependencyCreate, DependencyOut
from app.services import scheduling_service

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


@router.post("", response_model=DependencyOut, status_code=status.HTTP_201_CREATED)
def create_dependency(payload: DependencyCreate, session: SessionDep, user: CurrentUserDep):
    # Both endpoints share a project; check access via the successor's project.
    assert_task_access(session, user, payload.successor_id)
    dependency, _ = scheduling_service.create_dependency(
        session,
        predecessor_id=payload.predecessor_id,
        successor_id=payload.successor_id,
        dep_type=payload.type.value,
        lag_days=payload.lag_days,
        actor=user.email,
    )
    return dependency


@router.delete("/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(dependency_id: int, session: SessionDep, user: CurrentUserDep):
    dependency = dependency_repo.get(session, dependency_id)
    if dependency is None:
        raise HTTPException(status_code=404, detail="Dependency not found")
    assert_task_access(session, user, dependency.successor_id)
    scheduling_service.delete_dependency(session, dependency_id, actor=user.email)
