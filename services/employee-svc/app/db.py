"""Database configuration for employee service."""

import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from py_hrms_tenancy import get_current_tenant, TenantDatabaseManager

DB_URL_TEMPLATE = "postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"

def get_base_db_url() -> str:
    return DB_URL_TEMPLATE.format(
        user=os.getenv("POSTGRES_USER","hr"),
        pwd=os.getenv("POSTGRES_PASSWORD","hr"),
        host=os.getenv("POSTGRES_HOST","postgres"),
        port=os.getenv("POSTGRES_PORT","5432"),
        db=os.getenv("POSTGRES_DB","hr"),
    )

class Base(DeclarativeBase):
    pass

tenant_db_manager = TenantDatabaseManager(base_db_url=get_base_db_url(), base_model=Base)

async def get_db() -> AsyncSession:
    """Get database session for the current tenant."""
    current_tenant_id = get_current_tenant()
    if not current_tenant_id:
        raise Exception("Tenant context not set for database access.")
    async for session in tenant_db_manager.get_session(current_tenant_id):
        yield session

async def init_db():
    """Initialize database tables for all tenants."""
    # Import all models to ensure they are registered
    from app.models import EmployeeORM
    await tenant_db_manager.initialize_all_tenants_dbs()

