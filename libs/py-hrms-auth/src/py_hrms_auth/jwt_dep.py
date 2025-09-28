"""JWT authentication dependency for FastAPI services."""

import os
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Optional

import httpx
import structlog
from fastapi import Depends, HTTPException, Header, status
from jose import jwt, JWTError
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# Configuration from environment
ISSUER = os.getenv("OIDC_ISSUER", "")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "")
JWKS_URL = os.getenv("JWKS_URL", "")


class TokenPayload(BaseModel):
    """JWT token payload model."""
    
    sub: str
    iss: str
    aud: str
    exp: int
    iat: int
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    roles: List[str] = []
    tenant_id: Optional[str] = None
    scope: Optional[str] = None


class AuthContext(BaseModel):
    """Authentication context for the current request."""
    
    user_id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = []
    tenant_id: Optional[str] = None
    scopes: List[str] = []
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_scope(self, scope: str) -> bool:
        """Check if user has a specific scope."""
        return scope in self.scopes


@lru_cache(maxsize=1)
def _get_jwks() -> Dict[str, Any]:
    """Fetch and cache JWKS from the identity provider."""
    if not JWKS_URL:
        raise ValueError("JWKS_URL environment variable is required")
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(JWKS_URL)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error("Failed to fetch JWKS", error=str(e), jwks_url=JWKS_URL)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify tokens - authentication service unavailable"
        )


def _get_signing_key(kid: str) -> Dict[str, Any]:
    """Get the signing key for the given key ID."""
    jwks = _get_jwks()
    keys = jwks.get("keys", [])
    
    for key in keys:
        if key.get("kid") == kid:
            return key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token - unknown key ID"
    )


def verify_bearer_token(
    authorization: Annotated[Optional[str], Header()] = None
) -> TokenPayload:
    """Verify and decode JWT bearer token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ", 1)[1]
    
    try:
        # Get the unverified header to extract the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token - missing key ID"
            )
        
        # Get the signing key
        signing_key = _get_signing_key(kid)
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[signing_key.get("alg", "RS256")],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"verify_signature": True, "verify_exp": True}
        )
        
        return TokenPayload(**payload)
        
    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Unexpected error during token verification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )


from py_hrms_tenancy import set_tenant_context

def get_auth_context(token: TokenPayload = Depends(verify_bearer_token)) -> AuthContext:
    """Extract authentication context from verified token."""
    scopes = []
    if token.scope:
        scopes = token.scope.split()
    
    auth_context = AuthContext(
        user_id=token.sub,
        username=token.preferred_username or token.email or token.sub,
        email=token.email,
        roles=token.roles,
        tenant_id=token.tenant_id,
        scopes=scopes
    )

    if auth_context.tenant_id:
        set_tenant_context(auth_context.tenant_id)

    return auth_context


def require_roles(required_roles: List[str]):
    """Dependency factory to require specific roles."""
    def _check_roles(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not auth.has_any_role(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return auth
    
    return _check_roles


def require_scopes(required_scopes: List[str]):
    """Dependency factory to require specific scopes."""
    def _check_scopes(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not any(auth.has_scope(scope) for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {required_scopes}"
            )
        return auth
    
    return _check_scopes


def require_tenant_access(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Require that the user has tenant access."""
    if not auth.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required"
        )
    return auth


# Common role-based dependencies
RequireHRAdmin = Depends(require_roles(["hr.admin"]))
RequireHRManager = Depends(require_roles(["hr.manager", "hr.admin"]))
RequireEmployeeAdmin = Depends(require_roles(["employee.admin", "hr.admin"]))
RequireEmployeeManager = Depends(require_roles(["employee.manager", "employee.admin", "hr.admin"]))
RequireEmployeeSelf = Depends(require_roles(["employee.self", "employee.manager", "employee.admin", "hr.admin"]))

# Agent role dependencies
RequireAgentLeaveRequester = Depends(require_roles(["agent.leave.requester"]))
RequireAgentTimesheetApprover = Depends(require_roles(["agent.timesheet.approver"]))
RequireAgentPayrollProcessor = Depends(require_roles(["agent.payroll.processor"]))
