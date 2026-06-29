"""User + user↔project assignment data access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserProject


def list_all(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.id)))


def get(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def create(session: Session, **fields) -> User:
    user = User(**fields)
    session.add(user)
    session.flush()
    return user


def update(session: Session, user_id: int, fields: dict) -> User | None:
    user = session.get(User, user_id)
    if user is None:
        return None
    for key, value in fields.items():
        setattr(user, key, value)
    session.flush()
    return user


def delete(session: Session, user_id: int) -> bool:
    user = session.get(User, user_id)
    if user is None:
        return False
    session.delete(user)
    session.flush()
    return True


def assigned_project_ids(session: Session, user_id: int) -> list[int]:
    return list(
        session.scalars(
            select(UserProject.project_id)
            .where(UserProject.user_id == user_id)
            .order_by(UserProject.project_id)
        )
    )


def projects_by_user(session: Session) -> dict[int, list[int]]:
    """user_id -> [assigned project ids], for the admin user list."""
    out: dict[int, list[int]] = {}
    for up in session.scalars(select(UserProject)):
        out.setdefault(up.user_id, []).append(up.project_id)
    return out


def set_projects(session: Session, user_id: int, project_ids: list[int]) -> None:
    """Replace a user's project assignments with exactly ``project_ids``."""
    existing = list(
        session.scalars(select(UserProject).where(UserProject.user_id == user_id))
    )
    want = set(project_ids)
    have = {up.project_id for up in existing}
    for up in existing:
        if up.project_id not in want:
            session.delete(up)
    for pid in want - have:
        session.add(UserProject(user_id=user_id, project_id=pid))
    session.flush()
