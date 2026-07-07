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
    # A cold deploy may 502 on the first connect while a sleeping Turso/libSQL
    # instance wakes, which can outlast a short retry. This step runs before
    # uvicorn binds a port, so wait a generous window (~2.5 min: 1,2,4,8,16, then
    # 20s each) to ride out the cold start rather than aborting the boot chain.
    wait_for_db(connectable, attempts=12, base_delay=1.0, max_delay=20.0)
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
