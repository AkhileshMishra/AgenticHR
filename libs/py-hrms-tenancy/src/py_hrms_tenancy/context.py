"""
Tenant context management for AgenticHR

This module provides tenant context management including:
- Tenant identification and validation
- Context propagation across requests
- Tenant-aware database connections
- Multi-tenant middleware
"""
import os
from typing import Optional, Dict, Any
from contextvars import ContextVar
from dataclasses import dataclass
from fastapi import Request, HTTPException, Depends
from fastapi.middleware.base import BaseHTTPMiddleware
import structlog

# Context variables for tenant tracking
current_tenant_var: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)
tenant_data_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar('tenant_data', default=None)

logger = structlog.get_logger(__name__)

@dataclass
class TenantInfo:
    """Tenant information"""
    id: str
    name: str
    schema_name: str
    status: str = "active"
    settings: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TenantContext:
    """Tenant context manager"""
    
    def __init__(self):
        self._tenants: Dict[str, TenantInfo] = {}
        self._load_tenants()
    
    def _load_tenants(self):
        """Load tenant configuration"""
        # In production, this would load from database
        # For now, we'll use environment variables or defaults
        default_tenants = [
            TenantInfo(
                id="default",
                name="Default Organization",
                schema_name="public",
                status="active"
            ),
            TenantInfo(
                id="acme-corp",
                name="ACME Corporation",
                schema_name="tenant_acme_corp",
                status="active"
            ),
            TenantInfo(
                id="tech-startup",
                name="Tech Startup Inc",
                schema_name="tenant_tech_startup",
                status="active"
            )
        ]
        
        for tenant in default_tenants:
            self._tenants[tenant.id] = tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantInfo]:
        """Get tenant information by ID"""
        return self._tenants.get(tenant_id)
    
    def get_all_tenants(self) -> Dict[str, TenantInfo]:
        """Get all tenants"""
        return self._tenants.copy()
    
    def add_tenant(self, tenant: TenantInfo):
        """Add a new tenant"""
        self._tenants[tenant.id] = tenant
    
    def remove_tenant(self, tenant_id: str):
        """Remove a tenant"""
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
    
    def is_valid_tenant(self, tenant_id: str) -> bool:
        """Check if tenant ID is valid and active"""
        tenant = self.get_tenant(tenant_id)
        return tenant is not None and tenant.status == "active"

# Global tenant context instance
tenant_context = TenantContext()

def get_current_tenant() -> Optional[str]:
    """Get current tenant ID from context"""
    return current_tenant_var.get()

def get_tenant_data() -> Optional[Dict[str, Any]]:
    """Get current tenant data from context"""
    return tenant_data_var.get()

def set_tenant_context(tenant_id: str, tenant_data: Optional[Dict[str, Any]] = None):
    """Set tenant context"""
    current_tenant_var.set(tenant_id)
    if tenant_data:
        tenant_data_var.set(tenant_data)

def clear_tenant_context():
    """Clear tenant context"""
    current_tenant_var.set(None)
    tenant_data_var.set(None)

def get_tenant_schema(tenant_id: Optional[str] = None) -> str:
    """Get schema name for tenant"""
    if tenant_id is None:
        tenant_id = get_current_tenant()
    
    if tenant_id is None:
        return "public"  # Default schema
    
    tenant = tenant_context.get_tenant(tenant_id)
    if tenant:
        return tenant.schema_name
    
    return "public"

class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and set tenant context"""
    
    def __init__(self, app, default_tenant: str = "default"):
        super().__init__(app)
        self.default_tenant = default_tenant
    
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from various sources
        tenant_id = self._extract_tenant_id(request)
        
        # Validate tenant
        if not tenant_context.is_valid_tenant(tenant_id):
            logger.warning(
                "Invalid tenant ID",
                tenant_id=tenant_id,
                path=request.url.path,
                method=request.method
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tenant: {tenant_id}"
            )
        
        # Set tenant context
        tenant_info = tenant_context.get_tenant(tenant_id)
        set_tenant_context(
            tenant_id,
            {
                "name": tenant_info.name,
                "schema": tenant_info.schema_name,
                "settings": tenant_info.settings or {}
            }
        )
        
        logger.info(
            "Tenant context set",
            tenant_id=tenant_id,
            schema=tenant_info.schema_name,
            path=request.url.path
        )
        
        try:
            response = await call_next(request)
            
            # Add tenant info to response headers
            response.headers["X-Tenant-ID"] = tenant_id
            response.headers["X-Tenant-Schema"] = tenant_info.schema_name
            
            return response
        
        finally:
            # Clear context after request
            clear_tenant_context()
    
    def _extract_tenant_id(self, request: Request) -> str:
        """Extract tenant ID from request"""
        # Priority order:
        # 1. Header: X-Tenant-ID
        # 2. Query parameter: tenant_id
        # 3. Subdomain (if configured)
        # 4. JWT token (if available)
        # 5. Default tenant
        
        # Check header
        tenant_id = request.headers.get("x-tenant-id")
        if tenant_id:
            return tenant_id
        
        # Check query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        # Check subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain != "www" and subdomain != "api":
                # Check if subdomain maps to a tenant
                if tenant_context.is_valid_tenant(subdomain):
                    return subdomain
        
        # Check JWT token (simplified - in production you'd decode the token)
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # In production, decode JWT and extract tenant_id claim
            pass
        
        # Return default tenant
        return self.default_tenant

def require_tenant() -> str:
    """Dependency to require tenant context"""
    tenant_id = get_current_tenant()
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant context not set"
        )
    return tenant_id

def get_tenant_dependency() -> Optional[str]:
    """Dependency to get optional tenant context"""
    return get_current_tenant()

def require_tenant_info() -> TenantInfo:
    """Dependency to require tenant info"""
    tenant_id = require_tenant()
    tenant_info = tenant_context.get_tenant(tenant_id)
    if not tenant_info:
        raise HTTPException(
            status_code=400,
            detail=f"Tenant not found: {tenant_id}"
        )
    return tenant_info

class TenantValidator:
    """Validator for tenant-specific operations"""
    
    @staticmethod
    def validate_tenant_access(
        user_tenant_id: str,
        resource_tenant_id: str,
        allow_cross_tenant: bool = False
    ):
        """Validate that user can access resource from specific tenant"""
        if user_tenant_id != resource_tenant_id and not allow_cross_tenant:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cross-tenant access not allowed"
            )
    
    @staticmethod
    def validate_tenant_operation(
        tenant_id: str,
        operation: str,
        resource_type: str
    ):
        """Validate that operation is allowed for tenant"""
        tenant_info = tenant_context.get_tenant(tenant_id)
        if not tenant_info:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tenant: {tenant_id}"
            )
        
        if tenant_info.status != "active":
            raise HTTPException(
                status_code=403,
                detail=f"Tenant is not active: {tenant_id}"
            )
        
        # Check tenant-specific permissions (if configured)
        settings = tenant_info.settings or {}
        permissions = settings.get("permissions", {})
        
        if resource_type in permissions:
            allowed_operations = permissions[resource_type]
            if operation not in allowed_operations:
                raise HTTPException(
                    status_code=403,
                    detail=f"Operation '{operation}' not allowed for tenant '{tenant_id}' on '{resource_type}'"
                )

def tenant_aware_dependency(
    tenant_id: str = Depends(require_tenant),
    tenant_info: TenantInfo = Depends(require_tenant_info)
):
    """Combined dependency for tenant-aware endpoints"""
    return {
        "tenant_id": tenant_id,
        "tenant_info": tenant_info,
        "schema": tenant_info.schema_name
    }
