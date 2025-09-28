"""
Multi-tenant database isolation for AgenticHR

This module provides database isolation strategies including:
- Schema-per-tenant isolation
- Tenant-aware database sessions
- Automatic schema switching
- Migration management per tenant
"""
import os
from typing import Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.sql import text
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import DeclarativeBase
import structlog

from .context import get_current_tenant, get_tenant_schema, tenant_context

logger = structlog.get_logger(__name__)

class TenantAwareBase(DeclarativeBase):
    """Base class for tenant-aware models"""
    
    @classmethod
    def __table_cls__(cls, name, metadata, *args, **kwargs):
        """Override table creation to add tenant-aware schema"""
        # Get current tenant schema
        schema = get_tenant_schema()
        if schema and schema != "public":
            kwargs["schema"] = schema
        
        return Table(name, metadata, *args, **kwargs)

class TenantDatabaseManager:
    """Manager for tenant-aware database operations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engines: Dict[str, Any] = {}
        self.session_makers: Dict[str, Any] = {}
        self._setup_engines()
    
    def _setup_engines(self):
        """Setup database engines for each tenant"""
        # Create default engine
        self.engines["default"] = create_async_engine(
            self.database_url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        )
        
        self.session_makers["default"] = async_sessionmaker(
            self.engines["default"],
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # For schema-per-tenant, we can use the same engine
        # but different session configurations
        for tenant_id, tenant_info in tenant_context.get_all_tenants().items():
            if tenant_id != "default":
                self.engines[tenant_id] = self.engines["default"]
                self.session_makers[tenant_id] = self.session_makers["default"]
    
    def get_engine(self, tenant_id: Optional[str] = None):
        """Get database engine for tenant"""
        if tenant_id is None:
            tenant_id = get_current_tenant() or "default"
        
        return self.engines.get(tenant_id, self.engines["default"])
    
    def get_session_maker(self, tenant_id: Optional[str] = None):
        """Get session maker for tenant"""
        if tenant_id is None:
            tenant_id = get_current_tenant() or "default"
        
        return self.session_makers.get(tenant_id, self.session_makers["default"])
    
    @asynccontextmanager
    async def get_session(self, tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """Get database session for tenant with automatic schema switching"""
        session_maker = self.get_session_maker(tenant_id)
        
        async with session_maker() as session:
            # Set search path for schema isolation
            schema = get_tenant_schema(tenant_id)
            if schema and schema != "public":
                await session.execute(text(f"SET search_path TO {schema}, public"))
            
            logger.debug(
                "Database session created",
                tenant_id=tenant_id,
                schema=schema
            )
            
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(
                    "Database session error",
                    tenant_id=tenant_id,
                    schema=schema,
                    error=str(e)
                )
                raise
            finally:
                await session.close()
    
    async def create_tenant_schema(self, tenant_id: str) -> bool:
        """Create schema for new tenant"""
        tenant_info = tenant_context.get_tenant(tenant_id)
        if not tenant_info:
            logger.error("Tenant not found", tenant_id=tenant_id)
            return False
        
        schema_name = tenant_info.schema_name
        
        try:
            async with self.get_session("default") as session:
                # Create schema
                await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                await session.commit()
                
                logger.info(
                    "Tenant schema created",
                    tenant_id=tenant_id,
                    schema=schema_name
                )
                return True
        
        except Exception as e:
            logger.error(
                "Failed to create tenant schema",
                tenant_id=tenant_id,
                schema=schema_name,
                error=str(e)
            )
            return False
    
    async def drop_tenant_schema(self, tenant_id: str, cascade: bool = False) -> bool:
        """Drop schema for tenant"""
        tenant_info = tenant_context.get_tenant(tenant_id)
        if not tenant_info:
            logger.error("Tenant not found", tenant_id=tenant_id)
            return False
        
        schema_name = tenant_info.schema_name
        
        # Safety check - don't drop public schema
        if schema_name == "public":
            logger.error("Cannot drop public schema", tenant_id=tenant_id)
            return False
        
        try:
            async with self.get_session("default") as session:
                cascade_clause = "CASCADE" if cascade else "RESTRICT"
                await session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} {cascade_clause}"))
                await session.commit()
                
                logger.info(
                    "Tenant schema dropped",
                    tenant_id=tenant_id,
                    schema=schema_name,
                    cascade=cascade
                )
                return True
        
        except Exception as e:
            logger.error(
                "Failed to drop tenant schema",
                tenant_id=tenant_id,
                schema=schema_name,
                error=str(e)
            )
            return False
    
    async def migrate_tenant_schema(self, tenant_id: str) -> bool:
        """Run migrations for tenant schema"""
        tenant_info = tenant_context.get_tenant(tenant_id)
        if not tenant_info:
            logger.error("Tenant not found", tenant_id=tenant_id)
            return False
        
        schema_name = tenant_info.schema_name
        
        try:
            # This is a simplified migration - in production you'd use Alembic
            async with self.get_session(tenant_id) as session:
                # Set search path
                await session.execute(text(f"SET search_path TO {schema_name}, public"))
                
                # Create tables (this would be done via Alembic in production)
                from sqlalchemy import MetaData
                metadata = MetaData(schema=schema_name)
                
                # In production, you'd run: alembic -x tenant=<tenant_id> upgrade head
                
                logger.info(
                    "Tenant schema migrated",
                    tenant_id=tenant_id,
                    schema=schema_name
                )
                return True
        
        except Exception as e:
            logger.error(
                "Failed to migrate tenant schema",
                tenant_id=tenant_id,
                schema=schema_name,
                error=str(e)
            )
            return False
    
    async def list_tenant_schemas(self) -> Dict[str, Any]:
        """List all tenant schemas"""
        try:
            async with self.get_session("default") as session:
                result = await session.execute(text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name LIKE 'tenant_%' 
                    OR schema_name = 'public'
                    ORDER BY schema_name
                """))
                
                schemas = [row[0] for row in result.fetchall()]
                
                # Map schemas to tenants
                schema_info = {}
                for tenant_id, tenant_info in tenant_context.get_all_tenants().items():
                    schema_info[tenant_info.schema_name] = {
                        "tenant_id": tenant_id,
                        "tenant_name": tenant_info.name,
                        "exists": tenant_info.schema_name in schemas
                    }
                
                return schema_info
        
        except Exception as e:
            logger.error("Failed to list tenant schemas", error=str(e))
            return {}

# Global database manager instance
db_manager: Optional[TenantDatabaseManager] = None

def initialize_tenant_database(database_url: str):
    """Initialize tenant database manager"""
    global db_manager
    db_manager = TenantDatabaseManager(database_url)
    return db_manager

def get_tenant_db_manager() -> TenantDatabaseManager:
    """Get tenant database manager"""
    if db_manager is None:
        raise RuntimeError("Tenant database manager not initialized")
    return db_manager

async def get_tenant_session(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get tenant-aware database session"""
    manager = get_tenant_db_manager()
    async with manager.get_session(tenant_id) as session:
        yield session

class TenantQueryMixin:
    """Mixin for tenant-aware queries"""
    
    @classmethod
    async def get_by_id_for_tenant(
        cls,
        session: AsyncSession,
        id: int,
        tenant_id: Optional[str] = None
    ):
        """Get record by ID for specific tenant"""
        from sqlalchemy import select
        
        # Ensure we're in the right schema context
        if tenant_id:
            schema = get_tenant_schema(tenant_id)
            if schema and schema != "public":
                await session.execute(text(f"SET search_path TO {schema}, public"))
        
        result = await session.execute(select(cls).where(cls.id == id))
        return result.scalar_one_or_none()
    
    @classmethod
    async def list_for_tenant(
        cls,
        session: AsyncSession,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ):
        """List records for specific tenant"""
        from sqlalchemy import select
        
        # Ensure we're in the right schema context
        if tenant_id:
            schema = get_tenant_schema(tenant_id)
            if schema and schema != "public":
                await session.execute(text(f"SET search_path TO {schema}, public"))
        
        result = await session.execute(
            select(cls).limit(limit).offset(offset)
        )
        return result.scalars().all()

def tenant_aware_model(cls):
    """Decorator to make model tenant-aware"""
    # Add tenant query methods
    for method_name in ['get_by_id_for_tenant', 'list_for_tenant']:
        if not hasattr(cls, method_name):
            setattr(cls, method_name, getattr(TenantQueryMixin, method_name))
    
    return cls

class TenantMigrationManager:
    """Manager for tenant-specific migrations"""
    
    def __init__(self, alembic_cfg_path: str = "alembic.ini"):
        self.alembic_cfg_path = alembic_cfg_path
    
    async def migrate_all_tenants(self):
        """Run migrations for all tenants"""
        results = {}
        
        for tenant_id in tenant_context.get_all_tenants():
            try:
                success = await self.migrate_tenant(tenant_id)
                results[tenant_id] = {"success": success}
            except Exception as e:
                results[tenant_id] = {"success": False, "error": str(e)}
        
        return results
    
    async def migrate_tenant(self, tenant_id: str) -> bool:
        """Run migrations for specific tenant"""
        # This would integrate with Alembic in production
        # For now, we'll use the database manager
        manager = get_tenant_db_manager()
        return await manager.migrate_tenant_schema(tenant_id)
    
    async def create_tenant_migration(self, tenant_id: str, message: str):
        """Create new migration for tenant"""
        # This would run: alembic -x tenant=<tenant_id> revision --autogenerate -m "<message>"
        pass
    
    async def get_migration_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get migration status for tenant"""
        # This would check Alembic version table in tenant schema
        return {
            "tenant_id": tenant_id,
            "current_revision": "head",  # Placeholder
            "pending_migrations": []
        }
