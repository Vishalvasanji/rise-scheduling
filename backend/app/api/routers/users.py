"""Admin-only user management: list/create/update users, reset passwords, and
assign the projects each user can access."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, SessionDep
from app.repositories import user_repo
from app.schemas.user import ProjectAssignment, UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


def _out(user, project_ids: list[int]) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        project_ids=project_ids,
    )


@router.get("", response_model=list[UserOut])
def list_users(session: SessionDep, _admin: AdminDep):
    return [_out(u, pids) for u, pids in user_service.list_users(session)]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: SessionDep, _admin: AdminDep):
    user = user_service.create_user(
        session,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
        project_ids=payload.project_ids,
    )
    return _out(user, user_repo.assigned_project_ids(session, user.id))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, session: SessionDep, _admin: AdminDep):
    user = user_service.update_user(
        session,
        user_id,
        full_name=payload.full_name,
        role=payload.role,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return _out(user, user_repo.assigned_project_ids(session, user.id))


@router.put("/{user_id}/projects", response_model=UserOut)
def set_user_projects(
    user_id: int, payload: ProjectAssignment, session: SessionDep, _admin: AdminDep
):
    user = user_repo.get(session, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    user_service.set_user_projects(session, user_id, payload.project_ids)
    return _out(user, user_repo.assigned_project_ids(session, user_id))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, session: SessionDep, admin: AdminDep):
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="You can't delete yourself")
    if not user_service.delete_user(session, user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
