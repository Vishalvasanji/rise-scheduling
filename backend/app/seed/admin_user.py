"""Ensure the platform admin account exists.

Idempotent and meant to run on every boot (the API container's start command),
so the admin login is present even on an already-seeded prod DB — where
``run_seed --if-empty`` short-circuits before its own user-creation step.

The admin's role grants access to every project, so they need no user_projects
rows. The temp password should be changed from the admin panel after first login.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import get_auth_backend
from app.config import get_settings
from app.db.session import session_scope
from app.repositories import user_repo
from app.services import user_service

ADMIN_EMAIL = "vvasanji@sonomaadvisors.com"
ADMIN_FULL_NAME = "Vishal Vasanji"

# The pilot's original demo user was seeded with a reserved `.local` domain, which
# EmailStr rejects — it broke the admin Users list. Rewrite it to a valid address.
_LEGACY_DEMO_EMAIL = "demo@rise.local"
_DEMO_EMAIL = "demo@example.com"


def ensure_admin(session: Session) -> bool:
    """Create the admin user if absent (with must_change_password, via
    user_service.create_user). Returns True if it was created."""
    if user_repo.get_by_email(session, ADMIN_EMAIL) is not None:
        return False
    user_service.create_user(
        session,
        email=ADMIN_EMAIL,
        password=get_settings().admin_seed_password,
        full_name=ADMIN_FULL_NAME,
        role="admin",
    )
    return True


def flag_seeded_passwords(session: Session) -> int:
    """Any existing user still on a seeded temp password gets
    ``must_change_password`` set, so first login forces a rotation — this is how
    an already-seeded prod DB picks up the forced-change behavior. Returns the
    number of users flagged."""
    settings = get_settings()
    backend = get_auth_backend()
    flagged = 0
    for email, seed_pw in (
        (ADMIN_EMAIL, settings.admin_seed_password),
        (_DEMO_EMAIL, settings.demo_seed_password),
    ):
        user = user_repo.get_by_email(session, email)
        if (
            user is not None
            and not user.must_change_password
            and backend.verify_password(seed_pw, user.password_hash)
        ):
            user.must_change_password = True
            flagged += 1
    if flagged:
        session.commit()
    return flagged


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
        flagged = flag_seeded_passwords(session)
    if created:
        print(f"Created admin {ADMIN_EMAIL} (temp password — first login forces a change).")
    else:
        print(f"Admin {ADMIN_EMAIL} already exists; skipping.")
    if repaired:
        print(f"Repaired legacy demo user {_LEGACY_DEMO_EMAIL} -> {_DEMO_EMAIL}.")
    if flagged:
        print(f"Flagged {flagged} user(s) still on seeded passwords for forced rotation.")


if __name__ == "__main__":
    main()
