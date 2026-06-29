"""Ensure the platform admin account exists.

Idempotent and meant to run on every boot (the API container's start command),
so the admin login is present even on an already-seeded prod DB — where
``run_seed --if-empty`` short-circuits before its own user-creation step.

The admin's role grants access to every project, so they need no user_projects
rows. The temp password should be changed from the admin panel after first login.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import session_scope
from app.repositories import user_repo
from app.services import user_service

ADMIN_EMAIL = "vvasanji@sonomaadvisors.com"
ADMIN_FULL_NAME = "Vishal Vasanji"
ADMIN_TEMP_PASSWORD = "RiseAdmin#2026"  # noqa: S105 — pilot temp password, change after first login


def ensure_admin(session: Session) -> bool:
    """Create the admin user if absent. Returns True if it was created."""
    if user_repo.get_by_email(session, ADMIN_EMAIL) is not None:
        return False
    user_service.create_user(
        session,
        email=ADMIN_EMAIL,
        password=ADMIN_TEMP_PASSWORD,
        full_name=ADMIN_FULL_NAME,
        role="admin",
    )
    return True


def main() -> None:
    with session_scope() as session:
        created = ensure_admin(session)
    if created:
        print(f"Created admin {ADMIN_EMAIL} (temp password — change after first login).")
    else:
        print(f"Admin {ADMIN_EMAIL} already exists; skipping.")


if __name__ == "__main__":
    main()
