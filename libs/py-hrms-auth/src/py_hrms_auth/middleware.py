"""
Security middleware for AgenticHR services

This module provides security middleware including:
- Rate limiting
- Request validation
- Security headers
- IP filtering
- Request logging
"""
import time
import json
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

# Configure security logger
security_logger = logging.getLogger("agentichr.security")
security_logger.setLevel(logging.INFO)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using in-memory storage"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, Dict[str, Any]] = {}
    
    def _get_client_key(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Use IP address as client key
        client_ip = request.client.host if request.client else "unknown"
        
        # If authenticated, use user ID
        auth_header = request.headers.get("authorization")
        if auth_header:
            # Simple hash of auth header for consistent key
            auth_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
            return f"user_{auth_hash}"
        
        return f"ip_{client_ip}"
    
    def _is_rate_limited(self, client_key: str) -> bool:
        """Check if client is rate limited"""
        now = time.time()
        
        if client_key not in self.clients:
            self.clients[client_key] = {
                "calls": 1,
                "window_start": now
            }
            return False
        
        client_data = self.clients[client_key]
        
        # Reset window if period has passed
        if now - client_data["window_start"] > self.period:
            client_data["calls"] = 1
            client_data["window_start"] = now
            return False
        
        # Check if limit exceeded
        if client_data["calls"] >= self.calls:
            return True
        
        # Increment call count
        client_data["calls"] += 1
        return False
    
    async def dispatch(self, request: Request, call_next):
        client_key = self._get_client_key(request)
        
        if self._is_rate_limited(client_key):
            security_logger.warning(
                f"Rate limit exceeded for client {client_key}",
                extra={
                    "client_key": client_key,
                    "ip": request.client.host if request.client else None,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": self.period}
            )
        
        response = await call_next(request)
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests"""
    
    def __init__(self, app, max_content_length: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_content_length = max_content_length
        self.blocked_user_agents = [
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "nessus",
        ]
    
    def _is_suspicious_request(self, request: Request) -> Optional[str]:
        """Check if request is suspicious"""
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return f"Content length too large: {content_length}"
        
        # Check user agent
        user_agent = request.headers.get("user-agent", "").lower()
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent in user_agent:
                return f"Blocked user agent: {user_agent}"
        
        # Check for common attack patterns in URL
        suspicious_patterns = [
            "../",
            "..\\",
            "<script",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
            "union select",
            "drop table",
            "insert into",
            "delete from",
        ]
        
        url_path = str(request.url).lower()
        for pattern in suspicious_patterns:
            if pattern in url_path:
                return f"Suspicious pattern in URL: {pattern}"
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        # Validate request
        suspicious_reason = self._is_suspicious_request(request)
        if suspicious_reason:
            security_logger.warning(
                f"Suspicious request blocked: {suspicious_reason}",
                extra={
                    "ip": request.client.host if request.client else None,
                    "path": request.url.path,
                    "method": request.method,
                    "user_agent": request.headers.get("user-agent"),
                    "reason": suspicious_reason
                }
            )
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid request"}
            )
        
        response = await call_next(request)
        return response

class IPFilterMiddleware(BaseHTTPMiddleware):
    """Filter requests by IP address"""
    
    def __init__(self, app, allowed_ips: Optional[List[str]] = None, blocked_ips: Optional[List[str]] = None):
        super().__init__(app)
        self.allowed_ips = set(allowed_ips or [])
        self.blocked_ips = set(blocked_ips or [])
    
    def _is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        # If no allowed IPs specified, allow all except blocked
        if not self.allowed_ips:
            return ip not in self.blocked_ips
        
        # If allowed IPs specified, only allow those
        return ip in self.allowed_ips and ip not in self.blocked_ips
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        if not self._is_ip_allowed(client_ip):
            security_logger.warning(
                f"IP blocked: {client_ip}",
                extra={
                    "ip": client_ip,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied"}
            )
        
        response = await call_next(request)
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for security monitoring"""
    
    def __init__(self, app, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }
        
        # Log request body if enabled (be careful with sensitive data)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Only log first 1000 characters to avoid huge logs
                    request_data["body_preview"] = body.decode()[:1000]
            except Exception:
                request_data["body_preview"] = "Could not decode body"
        
        security_logger.info("REQUEST", extra=request_data)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            response_data = {
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "method": request.method,
                "url": str(request.url),
                "ip": request.client.host if request.client else None,
            }
            
            security_logger.info("RESPONSE", extra=response_data)
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            error_data = {
                "error": str(e),
                "process_time": round(process_time, 4),
                "method": request.method,
                "url": str(request.url),
                "ip": request.client.host if request.client else None,
            }
            
            security_logger.error("REQUEST_ERROR", extra=error_data)
            raise

class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security considerations"""
    
    def __init__(
        self,
        app,
        allowed_origins: List[str],
        allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allowed_headers: List[str] = ["Authorization", "Content-Type"],
        max_age: int = 3600
    ):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.allowed_methods = allowed_methods
        self.allowed_headers = allowed_headers
        self.max_age = max_age
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if "*" in self.allowed_origins:
            return True
        return origin in self.allowed_origins
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            if origin and self._is_origin_allowed(origin):
                response = Response()
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
                response.headers["Access-Control-Max-Age"] = str(self.max_age)
                response.headers["Access-Control-Allow-Credentials"] = "true"
                return response
            else:
                return JSONResponse(status_code=403, content={"error": "Origin not allowed"})
        
        # Process actual request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
