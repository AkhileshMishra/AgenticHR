import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .audit_log import Base

AUDIT_DATABASE_URL = os.getenv("AUDIT_DATABASE_URL", "postgresql+asyncpg://hr:hr@postgres:5432/hr")

engine = create_async_engine(AUDIT_DATABASE_URL, poolclass=NullPool)
AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def init_audit_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_audit_db():
    async with AsyncSessionLocal() as session:
        yield session

