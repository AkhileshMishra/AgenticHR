from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
import os

from app.db import Base  # metadata
from app.models import EmployeeORM  # Import all models

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

def get_url():
    u = os.getenv("POSTGRES_USER","hr")
    p = os.getenv("POSTGRES_PASSWORD","hr")
    h = os.getenv("POSTGRES_HOST","postgres")
    d = os.getenv("POSTGRES_DB","hr")
    return f"postgresql+asyncpg://{u}:{p}@{h}:5432/{d}"

target_metadata = Base.metadata

async def run_migrations_online():
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio; asyncio.run(run_migrations_online())
