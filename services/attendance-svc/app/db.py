import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "hr")
DB_USER = os.getenv("POSTGRES_USER", "hr")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "hr")

DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create async engine
engine = create_async_engine(DB_URL, future=True, echo=False)

# Create async session factory
SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
