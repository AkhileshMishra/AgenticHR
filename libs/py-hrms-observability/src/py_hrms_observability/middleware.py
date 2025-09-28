import time
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from sqlalchemy.ext.asyncio import AsyncSession

from .audit_log import AuditLogORM
from .db import AsyncSessionLocal
from py_hrms_auth import AuthContext, get_auth_context

class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        user_id = None
        tenant_id = None
        try:
            # Attempt to get AuthContext from request state if available
            auth_context: AuthContext = request.state.auth_context
            if auth_context:
                user_id = auth_context.user_id
                tenant_id = auth_context.tenant_id
        except AttributeError:
            pass # AuthContext not available, e.g., for unauthenticated endpoints

        audit_data = {
            "timestamp": time.time(),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": f"{request.method} {request.url.path}",
            "resource_type": "api_endpoint",
            "resource_id": None, # Can be populated by endpoint decorators if needed
            "success": response.status_code < 400,
            "details": {
                "request_method": request.method,
                "request_url": str(request.url),
                "response_status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
            },
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
        }

        async with AsyncSessionLocal() as session:
            audit_log_entry = AuditLogORM(
                timestamp=datetime.fromtimestamp(audit_data["timestamp"]),
                user_id=audit_data["user_id"],
                tenant_id=audit_data["tenant_id"],
                action=audit_data["action"],
                resource_type=audit_data["resource_type"],
                resource_id=audit_data["resource_id"],
                success=audit_data["success"],
                details=audit_data["details"],
                ip_address=audit_data["ip_address"],
                user_agent=audit_data["user_agent"],
                method=audit_data["method"],
                url=audit_data["url"],
                status_code=audit_data["status_code"],
            )
            session.add(audit_log_entry)
            await session.commit()

        return response

