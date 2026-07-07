"""Alembic environment. Reads DATABASE_URL from app settings (the single swap
point) and targets ``Base.metadata`` so autogenerate sees all models."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F401,F403  (register all tables on Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,  # SQLite-friendly ALTERs
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Reuse the application's engine builder so libSQL/Turso auth (and the
    # SQLite-only tweaks) are applied identically to migrations and the app.
    from app.db.engine import get_engine, wait_for_db

    connectable = get_engine()
    # A cold deploy may hit a transient gateway error on the very first connect
    # (e.g. Turso/libSQL Hrana 502); retry with backoff before migrating so the
    # boot chain doesn't abort on a blip.
    wait_for_db(connectable)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
