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

# The pilot's original demo user was seeded with a reserved `.local` domain, which
# EmailStr rejects — it broke the admin Users list. Rewrite it to a valid address.
_LEGACY_DEMO_EMAIL = "demo@rise.local"
_DEMO_EMAIL = "demo@example.com"


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


def repair_demo_email(session: Session) -> bool:
    """Heal the legacy `demo@rise.local` row (invalid domain, legacy role) to a valid
    address + role so reads don't 500. No-op if it's absent. Runs on every boot, so it
    also cleans the already-seeded prod DB. Returns True if a row was repaired."""
    legacy = user_repo.get_by_email(session, _LEGACY_DEMO_EMAIL)
    if legacy is None:
        return False
    # Only rename if the target address isn't already taken (avoid a unique clash).
    if user_repo.get_by_email(session, _DEMO_EMAIL) is None:
        user_repo.update(session, legacy.id, {"email": _DEMO_EMAIL, "role": "member"})
        session.commit()
    return True


def main() -> None:
    with session_scope() as session:
        created = ensure_admin(session)
        repaired = repair_demo_email(session)
    if created:
        print(f"Created admin {ADMIN_EMAIL} (temp password — change after first login).")
    else:
        print(f"Admin {ADMIN_EMAIL} already exists; skipping.")
    if repaired:
        print(f"Repaired legacy demo user {_LEGACY_DEMO_EMAIL} -> {_DEMO_EMAIL}.")


if __name__ == "__main__":
    main()
