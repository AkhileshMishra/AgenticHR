import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DB_URL = "postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}".format(
    user=os.getenv("POSTGRES_USER","hr"),
    pwd=os.getenv("POSTGRES_PASSWORD","hr"),
    host=os.getenv("POSTGRES_HOST","postgres"),
    port=os.getenv("POSTGRES_PORT","5432"),
    db=os.getenv("POSTGRES_DB","hr"),
)

engine = create_async_engine(DB_URL, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
