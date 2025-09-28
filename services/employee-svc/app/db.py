"""Database configuration for employee service."""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DB_URL = "postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}".format(
    user=os.getenv("POSTGRES_USER","hr"),
    pwd=os.getenv("POSTGRES_PASSWORD","hr"),
    host=os.getenv("POSTGRES_HOST","postgres"),
    port=os.getenv("POSTGRES_PORT","5432"),
    db=os.getenv("POSTGRES_DB","hr"),
)

engine = create_async_engine(
    DB_URL, 
    future=True, 
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    """Get database session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models import EmployeeORM
        await conn.run_sync(Base.metadata.create_all)
