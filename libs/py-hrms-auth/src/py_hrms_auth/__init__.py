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
]

__version__ = "0.1.0"
