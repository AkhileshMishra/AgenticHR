"""
Role-Based Access Control (RBAC) for AgenticHR

This module provides comprehensive RBAC functionality including:
- Role definitions and permissions
- Permission checking decorators
- Resource-based access control
- Audit logging
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from functools import wraps
from fastapi import HTTPException, Request
import logging

# Configure audit logger
audit_logger = logging.getLogger("agentichr.audit")
audit_logger.setLevel(logging.INFO)

class Permission(Enum):
    """System permissions"""
    # Employee permissions
    EMPLOYEE_READ = "employee:read"
    EMPLOYEE_WRITE = "employee:write"
    EMPLOYEE_DELETE = "employee:delete"
    EMPLOYEE_READ_ALL = "employee:read:all"
    
    # Attendance permissions
    ATTENDANCE_READ = "attendance:read"
    ATTENDANCE_WRITE = "attendance:write"
    ATTENDANCE_READ_ALL = "attendance:read:all"
    ATTENDANCE_MANAGE = "attendance:manage"
    
    # Leave permissions
    LEAVE_READ = "leave:read"
    LEAVE_WRITE = "leave:write"
    LEAVE_APPROVE = "leave:approve"
    LEAVE_READ_ALL = "leave:read:all"
    LEAVE_MANAGE = "leave:manage"
    
    # User management permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_MANAGE = "user:manage"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    AUDIT_READ = "audit:read"
    REPORTS_READ = "reports:read"
    REPORTS_GENERATE = "reports:generate"
    
    # Workflow permissions
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_MANAGE = "workflow:manage"

class Role(Enum):
    """System roles with their permissions"""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR_ADMIN = "hr_admin"
    SYSTEM_ADMIN = "system_admin"
    AUDITOR = "auditor"

# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.EMPLOYEE: {
        Permission.EMPLOYEE_READ,
        Permission.ATTENDANCE_READ,
        Permission.ATTENDANCE_WRITE,
        Permission.LEAVE_READ,
        Permission.LEAVE_WRITE,
    },
    Role.MANAGER: {
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_READ_ALL,
        Permission.ATTENDANCE_READ,
        Permission.ATTENDANCE_READ_ALL,
        Permission.LEAVE_READ,
        Permission.LEAVE_READ_ALL,
        Permission.LEAVE_APPROVE,
        Permission.REPORTS_READ,
    },
    Role.HR_ADMIN: {
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_WRITE,
        Permission.EMPLOYEE_READ_ALL,
        Permission.ATTENDANCE_READ,
        Permission.ATTENDANCE_READ_ALL,
        Permission.ATTENDANCE_MANAGE,
        Permission.LEAVE_READ,
        Permission.LEAVE_READ_ALL,
        Permission.LEAVE_APPROVE,
        Permission.LEAVE_MANAGE,
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.REPORTS_READ,
        Permission.REPORTS_GENERATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_MANAGE,
    },
    Role.SYSTEM_ADMIN: {
        # System admins have all permissions
        *Permission
    },
    Role.AUDITOR: {
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_READ_ALL,
        Permission.ATTENDANCE_READ,
        Permission.ATTENDANCE_READ_ALL,
        Permission.LEAVE_READ,
        Permission.LEAVE_READ_ALL,
        Permission.AUDIT_READ,
        Permission.REPORTS_READ,
        Permission.WORKFLOW_READ,
    }
}

class AccessContext:
    """Context for access control decisions"""
    def __init__(
        self,
        user_id: int,
        roles: List[str],
        permissions: Set[Permission],
        tenant_id: Optional[str] = None,
        department: Optional[str] = None,
        manager_id: Optional[int] = None
    ):
        self.user_id = user_id
        self.roles = roles
        self.permissions = permissions
        self.tenant_id = tenant_id
        self.department = department
        self.manager_id = manager_id

def get_permissions_for_roles(roles: List[str]) -> Set[Permission]:
    """Get all permissions for given roles"""
    permissions = set()
    for role_str in roles:
        try:
            role = Role(role_str)
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        except ValueError:
            # Unknown role, skip
            continue
    return permissions

def create_access_context(auth_data: Dict[str, Any]) -> AccessContext:
    """Create access context from auth data"""
    user_id = auth_data.get("user_id", 0)
    roles = auth_data.get("roles", [])
    tenant_id = auth_data.get("tenant_id")
    department = auth_data.get("department")
    manager_id = auth_data.get("manager_id")
    
    permissions = get_permissions_for_roles(roles)
    
    return AccessContext(
        user_id=user_id,
        roles=roles,
        permissions=permissions,
        tenant_id=tenant_id,
        department=department,
        manager_id=manager_id
    )

def has_permission(context: AccessContext, permission: Permission) -> bool:
    """Check if context has specific permission"""
    return permission in context.permissions

def has_any_permission(context: AccessContext, permissions: List[Permission]) -> bool:
    """Check if context has any of the specified permissions"""
    return any(perm in context.permissions for perm in permissions)

def has_all_permissions(context: AccessContext, permissions: List[Permission]) -> bool:
    """Check if context has all specified permissions"""
    return all(perm in context.permissions for perm in permissions)

def can_access_resource(
    context: AccessContext,
    resource_type: str,
    resource_id: Optional[int] = None,
    resource_owner_id: Optional[int] = None,
    resource_department: Optional[str] = None
) -> bool:
    """Check if context can access specific resource"""
    
    # System admins can access everything
    if Permission.SYSTEM_ADMIN in context.permissions:
        return True
    
    # Resource-specific logic
    if resource_type == "employee":
        # Can read own employee record
        if resource_owner_id == context.user_id and Permission.EMPLOYEE_READ in context.permissions:
            return True
        
        # Can read all employees if has permission
        if Permission.EMPLOYEE_READ_ALL in context.permissions:
            return True
        
        # Managers can read employees in their department
        if (Permission.EMPLOYEE_READ in context.permissions and 
            resource_department == context.department and
            Role.MANAGER.value in context.roles):
            return True
    
    elif resource_type == "attendance":
        # Can read own attendance
        if resource_owner_id == context.user_id and Permission.ATTENDANCE_READ in context.permissions:
            return True
        
        # Can read all attendance if has permission
        if Permission.ATTENDANCE_READ_ALL in context.permissions:
            return True
    
    elif resource_type == "leave":
        # Can read own leave requests
        if resource_owner_id == context.user_id and Permission.LEAVE_READ in context.permissions:
            return True
        
        # Can read all leave requests if has permission
        if Permission.LEAVE_READ_ALL in context.permissions:
            return True
    
    return False

def audit_log(
    action: str,
    resource_type: str,
    resource_id: Optional[int],
    user_id: int,
    success: bool,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """Log audit event"""
    audit_data = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "success": success,
        "details": details or {},
    }
    
    if request:
        audit_data.update({
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "url": str(request.url),
        })
    
    audit_logger.info("AUDIT", extra=audit_data)

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract auth context from kwargs
            auth = kwargs.get("auth")
            if not auth:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            context = create_access_context(auth)
            
            if not has_permission(context, permission):
                audit_log(
                    action=f"access_denied_{func.__name__}",
                    resource_type="endpoint",
                    resource_id=None,
                    user_id=context.user_id,
                    success=False,
                    details={"required_permission": permission.value}
                )
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission required: {permission.value}"
                )
            
            # Add context to kwargs for use in endpoint
            kwargs["access_context"] = context
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[Permission]):
    """Decorator to require any of the specified permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth = kwargs.get("auth")
            if not auth:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            context = create_access_context(auth)
            
            if not has_any_permission(context, permissions):
                audit_log(
                    action=f"access_denied_{func.__name__}",
                    resource_type="endpoint",
                    resource_id=None,
                    user_id=context.user_id,
                    success=False,
                    details={"required_permissions": [p.value for p in permissions]}
                )
                raise HTTPException(
                    status_code=403, 
                    detail=f"One of these permissions required: {[p.value for p in permissions]}"
                )
            
            kwargs["access_context"] = context
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_resource_access(resource_type: str, resource_id_param: str = "id"):
    """Decorator to require access to specific resource"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth = kwargs.get("auth")
            if not auth:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            context = create_access_context(auth)
            resource_id = kwargs.get(resource_id_param)
            
            # For now, we'll do basic permission check
            # In a real implementation, you'd fetch resource details from DB
            if not can_access_resource(context, resource_type, resource_id):
                audit_log(
                    action=f"resource_access_denied_{func.__name__}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=context.user_id,
                    success=False
                )
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied to {resource_type} resource"
                )
            
            kwargs["access_context"] = context
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: Role):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth = kwargs.get("auth")
            if not auth:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            context = create_access_context(auth)
            
            if role.value not in context.roles:
                audit_log(
                    action=f"role_access_denied_{func.__name__}",
                    resource_type="endpoint",
                    resource_id=None,
                    user_id=context.user_id,
                    success=False,
                    details={"required_role": role.value}
                )
                raise HTTPException(
                    status_code=403, 
                    detail=f"Role required: {role.value}"
                )
            
            kwargs["access_context"] = context
            return await func(*args, **kwargs)
        return wrapper
    return decorator
