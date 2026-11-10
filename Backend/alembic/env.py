import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401
from app.config import settings
from app.db import Base

target_metadata = Base.metadata
LOCK_ID = 727001


def do_run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.execute(f"SELECT pg_advisory_xact_lock({LOCK_ID})")
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run)
            await connection.commit()
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline mode is not supported, run migrations against a database")

asyncio.run(run_online())
