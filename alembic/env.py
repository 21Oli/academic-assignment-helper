"""
Alembic environment — async-compatible with SQLAlchemy 2.x.

Run migrations:
    alembic upgrade head

Create a new migration:
    alembic revision --autogenerate -m "describe change"
"""
import os
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make sure all models are imported so Alembic can detect them
from backend.models import Base  # noqa: F401 — registers all ORM models

# ---------------------------------------------------------------------------
# Alembic Config object (provides access to values in alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "")
# Alembic needs a sync URL for its own connection handling; swap asyncpg → psycopg2
sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode (generates SQL script without a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (connects to the live DB)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
