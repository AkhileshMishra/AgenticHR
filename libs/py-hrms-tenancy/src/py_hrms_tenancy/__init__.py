"""AgenticHR Multi-Tenancy Library."""

from .context import (
    TenantInfo,
    TenantContext,
    TenantMiddleware,
    TenantValidator,
    tenant_context,
    get_current_tenant,
    get_tenant_data,
    set_tenant_context,
    clear_tenant_context,
    get_tenant_schema,
    require_tenant,
    get_tenant_dependency,
    require_tenant_info,
    tenant_aware_dependency,
)

from .database import (
    TenantAwareBase,
    TenantDatabaseManager,
    TenantQueryMixin,
    TenantMigrationManager,
    initialize_tenant_database,
    get_tenant_db_manager,
    get_tenant_session,
    tenant_aware_model,
)

__all__ = [
    # Context
    "TenantInfo",
    "TenantContext", 
    "TenantMiddleware",
    "TenantValidator",
    "tenant_context",
    "get_current_tenant",
    "get_tenant_data",
    "set_tenant_context",
    "clear_tenant_context",
    "get_tenant_schema",
    "require_tenant",
    "get_tenant_dependency",
    "require_tenant_info",
    "tenant_aware_dependency",
    
    # Database
    "TenantAwareBase",
    "TenantDatabaseManager",
    "TenantQueryMixin",
    "TenantMigrationManager",
    "initialize_tenant_database",
    "get_tenant_db_manager",
    "get_tenant_session",
    "tenant_aware_model",
]

__version__ = "0.1.0"
