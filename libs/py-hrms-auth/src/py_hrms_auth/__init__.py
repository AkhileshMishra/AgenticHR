"""AgenticHR Authentication and Authorization Library."""

from .jwt_dep import (
    AuthContext,
    TokenPayload,
    get_auth_context,
    require_roles,
    require_scopes,
    require_tenant_access,
    verify_bearer_token,
    RequireHRAdmin,
    RequireHRManager,
    RequireEmployeeAdmin,
    RequireEmployeeManager,
    RequireEmployeeSelf,
    RequireAgentLeaveRequester,
    RequireAgentTimesheetApprover,
    RequireAgentPayrollProcessor,
)

from .rbac import (
    Permission, Role, AccessContext, 
    require_permission, require_any_permission, 
    require_resource_access, require_role,
    audit_log, create_access_context
)

from .middleware import (
    RateLimitMiddleware, SecurityHeadersMiddleware,
    RequestValidationMiddleware, IPFilterMiddleware,
    RequestLoggingMiddleware, CORSSecurityMiddleware
)

__all__ = [
    "AuthContext",
    "TokenPayload",
    "get_auth_context",
    "require_roles",
    "require_scopes",
    "require_tenant_access",
    "verify_bearer_token",
    "RequireHRAdmin",
    "RequireHRManager",
    "RequireEmployeeAdmin",
    "RequireEmployeeManager",
    "RequireEmployeeSelf",
    "RequireAgentLeaveRequester",
    "RequireAgentTimesheetApprover",
    "RequireAgentPayrollProcessor",
    "Permission", "Role", "AccessContext",
    "require_permission", "require_any_permission", 
    "require_resource_access", "require_role",
    "audit_log", "create_access_context",
    "RateLimitMiddleware", "SecurityHeadersMiddleware",
    "RequestValidationMiddleware", "IPFilterMiddleware",
    "RequestLoggingMiddleware", "CORSSecurityMiddleware"
]

__version__ = "0.1.0"
