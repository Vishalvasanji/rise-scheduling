"""CLI entrypoint: ``python -m app.seed.run_seed [--if-empty]``.

Seeds the 5 dummy LIHTC projects and a demo user. Run after ``alembic upgrade
head``. Idempotent. With ``--if-empty`` it does nothing when projects already
exist — used on hosted boot so a deploy never wipes edits made through the app.
"""

from __future__ import annotations

import sys

from app.db.session import session_scope
from app.repositories import project_repo
from app.seed.seed_data import seed_all
from app.services import auth_service


def main() -> None:
    if_empty = "--if-empty" in sys.argv
    with session_scope() as session:
        if if_empty and project_repo.list_all(session):
            print("Projects already exist; skipping seed (--if-empty).")
            return
        project_ids = seed_all(session)
        # A demo login for the pilot (dummy credentials only).
        if auth_service.get_by_email(session, "demo@rise.local") is None:
            auth_service.create_user(
                session,
                email="demo@rise.local",
                password="demo-pilot-password",
                full_name="Demo User",
                role="leadership",
            )
        print(f"Seeded {len(project_ids)} projects: {project_ids}")
        print("Demo login: demo@rise.local / demo-pilot-password")


if __name__ == "__main__":
    main()
