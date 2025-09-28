"""
Structured logging for AgenticHR services

This module provides standardized structured logging with:
- JSON formatting
- Correlation IDs
- Service context
- Performance logging
- Error tracking
"""
import os
import sys
import time
import uuid
import logging
import structlog
from typing import Dict, Any, Optional
from contextvars import ContextVar
from fastapi import Request
from fastapi.middleware.base import BaseHTTPMiddleware

# Context variables for request tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)

def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    json_logs: bool = True,
    include_stdlib: bool = True
):
    """Configure structured logging for the service"""
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context(service_name),
        add_correlation_id,
        add_user_context,
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging if requested
    if include_stdlib:
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )
        
        # Reduce noise from some libraries
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

def add_service_context(service_name: str):
    """Add service context to all log entries"""
    def processor(logger, method_name, event_dict):
        event_dict["service"] = service_name
        event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
        return event_dict
    return processor

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries"""
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict

def add_user_context(logger, method_name, event_dict):
    """Add user context to log entries"""
    user_id = user_id_var.get()
    tenant_id = tenant_id_var.get()
    
    if user_id:
        event_dict["user_id"] = user_id
    if tenant_id:
        event_dict["tenant_id"] = tenant_id
    
    return event_dict

def set_correlation_id(correlation_id: str):
    """Set correlation ID for current context"""
    correlation_id_var.set(correlation_id)

def set_user_context(user_id: Optional[str] = None, tenant_id: Optional[str] = None):
    """Set user context for current context"""
    if user_id:
        user_id_var.set(user_id)
    if tenant_id:
        tenant_id_var.set(tenant_id)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_var.get()

def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request logging and correlation IDs"""
    
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
        self.logger = structlog.get_logger()
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract correlation ID
        correlation_id = (
            request.headers.get("x-correlation-id") or
            request.headers.get("x-request-id") or
            generate_correlation_id()
        )
        
        set_correlation_id(correlation_id)
        
        # Extract user context from auth if available
        auth_header = request.headers.get("authorization")
        if auth_header:
            # In a real implementation, you'd decode the JWT here
            # For now, we'll just log that auth is present
            pass
        
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=dict(request.headers),
            client_ip=request.client.host if request.client else None,
        )
        
        try:
            # Add correlation ID to response headers
            response = await call_next(request)
            response.headers["x-correlation-id"] = correlation_id
            
            # Log successful request
            duration = time.time() - start_time
            self.logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                response_size=response.headers.get("content-length"),
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            self.logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise

class PerformanceLogger:
    """Context manager for performance logging"""
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.logger = structlog.get_logger()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(
            "operation_started",
            operation=self.operation,
            **self.context
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(
                "operation_completed",
                operation=self.operation,
                duration_ms=round(duration * 1000, 2),
                **self.context
            )
        else:
            self.logger.error(
                "operation_failed",
                operation=self.operation,
                duration_ms=round(duration * 1000, 2),
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )

def log_performance(operation: str, **context):
    """Decorator for performance logging"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with PerformanceLogger(operation, **context):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with PerformanceLogger(operation, **context):
                return func(*args, **kwargs)
        
        if hasattr(func, '__code__') and 'async' in func.__code__.co_flags:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def log_business_event(event: str, **data):
    """Log business events for analytics"""
    logger = structlog.get_logger()
    logger.info(
        "business_event",
        event=event,
        **data
    )

def log_security_event(event: str, severity: str = "info", **data):
    """Log security events"""
    logger = structlog.get_logger()
    
    log_method = getattr(logger, severity.lower(), logger.info)
    log_method(
        "security_event",
        event=event,
        severity=severity,
        **data
    )

def log_audit_event(action: str, resource: str, **data):
    """Log audit events"""
    logger = structlog.get_logger()
    logger.info(
        "audit_event",
        action=action,
        resource=resource,
        timestamp=time.time(),
        **data
    )

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log errors with context"""
    logger = structlog.get_logger()
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        exc_info=True
    )

def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)

# Convenience functions for common log levels
def debug(message: str, **kwargs):
    """Log debug message"""
    logger = structlog.get_logger()
    logger.debug(message, **kwargs)

def info(message: str, **kwargs):
    """Log info message"""
    logger = structlog.get_logger()
    logger.info(message, **kwargs)

def warning(message: str, **kwargs):
    """Log warning message"""
    logger = structlog.get_logger()
    logger.warning(message, **kwargs)

def error(message: str, **kwargs):
    """Log error message"""
    logger = structlog.get_logger()
    logger.error(message, **kwargs)

def critical(message: str, **kwargs):
    """Log critical message"""
    logger = structlog.get_logger()
    logger.critical(message, **kwargs)
