from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
import os

# Your models
from app.models import Base  # ensure Base.metadata aggregates all tables

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

def run_migrations_offline():
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run)

def do_run(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio; asyncio.run(run_migrations_online())

