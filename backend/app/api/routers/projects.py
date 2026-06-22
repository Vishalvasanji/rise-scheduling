"""Project + full-schedule endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.schemas.project import ProjectCreate, ProjectOut, ScheduleOut
from app.schemas.task import TaskOut
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(session: SessionDep):
    return project_service.list_projects(session)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: SessionDep):
    return project_service.create_project(
        session,
        name=payload.name,
        anchor_date=payload.anchor_date,
        deal_type=payload.deal_type,
        units=payload.units,
        stage=payload.stage,
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, session: SessionDep):
    project = project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/schedule", response_model=ScheduleOut)
def get_schedule(project_id: int, session: SessionDep):
    result = project_service.get_schedule(session, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project, tasks, deps = result
    return ScheduleOut(project=project, tasks=tasks, dependencies=deps)


@router.get("/{project_id}/critical-path", response_model=list[TaskOut])
def get_critical_path(project_id: int, session: SessionDep):
    if project_service.get_project(session, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_service.get_critical_path(session, project_id)
