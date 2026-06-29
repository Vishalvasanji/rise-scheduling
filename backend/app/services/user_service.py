"""User management (admin): create/update users, reset passwords, and set the
projects each user can access. Password hashing routes through the auth backend."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import get_auth_backend
from app.models import User
from app.repositories import user_repo

VALID_ROLES = {"admin", "member"}


def list_users(session: Session) -> list[tuple[User, list[int]]]:
    """All users paired with their assigned project ids (admins: empty — they see all)."""
    by_user = user_repo.projects_by_user(session)
    return [(u, by_user.get(u.id, [])) for u in user_repo.list_all(session)]


def create_user(
    session: Session,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    role: str = "member",
    project_ids: list[int] | None = None,
) -> User:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'")
    if user_repo.get_by_email(session, email) is not None:
        raise ValueError(f"A user with email {email} already exists")
    user = user_repo.create(
        session,
        email=email,
        full_name=full_name,
        password_hash=get_auth_backend().hash_password(password),
        role=role,
    )
    user_repo.set_projects(session, user.id, project_ids or [])
    session.commit()
    return user


def update_user(
    session: Session,
    user_id: int,
    *,
    full_name: str | None = None,
    role: str | None = None,
    password: str | None = None,
) -> User | None:
    fields: dict = {}
    if full_name is not None:
        fields["full_name"] = full_name
    if role is not None:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'")
        fields["role"] = role
    if password:
        fields["password_hash"] = get_auth_backend().hash_password(password)
    user = user_repo.update(session, user_id, fields)
    session.commit()
    return user


def set_user_projects(session: Session, user_id: int, project_ids: list[int]) -> None:
    user_repo.set_projects(session, user_id, project_ids)
    session.commit()


def delete_user(session: Session, user_id: int) -> bool:
    ok = user_repo.delete(session, user_id)
    session.commit()
    return ok
