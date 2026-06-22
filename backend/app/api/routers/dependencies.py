"""Dependency endpoints. Creating a dependency that would form a cycle is
rejected by the engine (HTTP 409) before anything is persisted."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import ActorDep, SessionDep
from app.schemas.dependency import DependencyCreate, DependencyOut
from app.services import scheduling_service

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


@router.post("", response_model=DependencyOut, status_code=status.HTTP_201_CREATED)
def create_dependency(payload: DependencyCreate, session: SessionDep, actor: ActorDep):
    dependency, _ = scheduling_service.create_dependency(
        session,
        predecessor_id=payload.predecessor_id,
        successor_id=payload.successor_id,
        dep_type=payload.type.value,
        lag_days=payload.lag_days,
        actor=actor,
    )
    return dependency


@router.delete("/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(dependency_id: int, session: SessionDep, actor: ActorDep):
    scheduling_service.delete_dependency(session, dependency_id, actor=actor)
