"""
Prometheus metrics for AgenticHR services

This module provides standardized metrics collection for all services including:
- HTTP request metrics
- Database operation metrics
- Business logic metrics
- System health metrics
"""
import time
from typing import Dict, Any, Optional
from functools import wraps
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

# Create custom registry for service metrics
service_registry = CollectorRegistry()

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'service'],
    registry=service_registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service'],
    registry=service_registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['service'],
    registry=service_registry
)

# Database Metrics
db_operations_total = Counter(
    'db_operations_total',
    'Total database operations',
    ['operation', 'table', 'service'],
    registry=service_registry
)

db_operation_duration_seconds = Histogram(
    'db_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'table', 'service'],
    registry=service_registry
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections',
    ['service'],
    registry=service_registry
)

# Business Logic Metrics
business_operations_total = Counter(
    'business_operations_total',
    'Total business operations',
    ['operation', 'service'],
    registry=service_registry
)

business_operation_duration_seconds = Histogram(
    'business_operation_duration_seconds',
    'Business operation duration in seconds',
    ['operation', 'service'],
    registry=service_registry
)

# Authentication Metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result', 'service'],  # result: success, failure, invalid_token
    registry=service_registry
)

auth_tokens_active = Gauge(
    'auth_tokens_active',
    'Currently active authentication tokens',
    ['service'],
    registry=service_registry
)

# Celery/Task Metrics
tasks_total = Counter(
    'tasks_total',
    'Total tasks processed',
    ['task_name', 'status', 'service'],  # status: success, failure, retry
    registry=service_registry
)

task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task execution duration in seconds',
    ['task_name', 'service'],
    registry=service_registry
)

tasks_in_progress = Gauge(
    'tasks_in_progress',
    'Tasks currently being processed',
    ['task_name', 'service'],
    registry=service_registry
)

# System Health Metrics
service_info = Info(
    'service_info',
    'Service information',
    registry=service_registry
)

service_uptime_seconds = Gauge(
    'service_uptime_seconds',
    'Service uptime in seconds',
    ['service'],
    registry=service_registry
)

memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['service'],
    registry=service_registry
)

# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'service'],
    registry=service_registry
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""
    
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Track request in progress
        http_requests_in_progress.labels(service=self.service_name).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=request.method,
                endpoint=self._get_endpoint_pattern(request),
                status_code=response.status_code,
                service=self.service_name
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=self._get_endpoint_pattern(request),
                service=self.service_name
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error
            errors_total.labels(
                error_type=type(e).__name__,
                service=self.service_name
            ).inc()
            
            # Still record the request
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=self._get_endpoint_pattern(request),
                service=self.service_name
            ).observe(duration)
            
            raise
        
        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(service=self.service_name).dec()
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern from request"""
        # This is a simplified version - in production you'd want to
        # extract the actual route pattern from FastAPI
        path = request.url.path
        
        # Replace IDs with placeholders
        import re
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path

def track_db_operation(operation: str, table: str, service_name: str):
    """Decorator to track database operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record successful operation
                duration = time.time() - start_time
                db_operations_total.labels(
                    operation=operation,
                    table=table,
                    service=service_name
                ).inc()
                
                db_operation_duration_seconds.labels(
                    operation=operation,
                    table=table,
                    service=service_name
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # Record error
                errors_total.labels(
                    error_type=f"db_{type(e).__name__}",
                    service=service_name
                ).inc()
                raise
        
        return wrapper
    return decorator

def track_business_operation(operation: str, service_name: str):
    """Decorator to track business operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record successful operation
                duration = time.time() - start_time
                business_operations_total.labels(
                    operation=operation,
                    service=service_name
                ).inc()
                
                business_operation_duration_seconds.labels(
                    operation=operation,
                    service=service_name
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # Record error
                errors_total.labels(
                    error_type=f"business_{type(e).__name__}",
                    service=service_name
                ).inc()
                raise
        
        return wrapper
    return decorator

def track_task_execution(task_name: str, service_name: str):
    """Decorator to track Celery task execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Track task in progress
            tasks_in_progress.labels(
                task_name=task_name,
                service=service_name
            ).inc()
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record successful task
                duration = time.time() - start_time
                tasks_total.labels(
                    task_name=task_name,
                    status="success",
                    service=service_name
                ).inc()
                
                task_duration_seconds.labels(
                    task_name=task_name,
                    service=service_name
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # Record failed task
                tasks_total.labels(
                    task_name=task_name,
                    status="failure",
                    service=service_name
                ).inc()
                
                errors_total.labels(
                    error_type=f"task_{type(e).__name__}",
                    service=service_name
                ).inc()
                
                raise
            
            finally:
                # Decrement in-progress counter
                tasks_in_progress.labels(
                    task_name=task_name,
                    service=service_name
                ).dec()
        
        return wrapper
    return decorator

def record_auth_attempt(result: str, service_name: str):
    """Record authentication attempt"""
    auth_attempts_total.labels(
        result=result,
        service=service_name
    ).inc()

def set_active_tokens(count: int, service_name: str):
    """Set number of active tokens"""
    auth_tokens_active.labels(service=service_name).set(count)

def set_db_connections(count: int, service_name: str):
    """Set number of active database connections"""
    db_connections_active.labels(service=service_name).set(count)

def set_service_info(service_name: str, version: str, **kwargs):
    """Set service information"""
    info_dict = {
        'service': service_name,
        'version': version,
        **kwargs
    }
    service_info.info(info_dict)

def update_uptime(uptime_seconds: float, service_name: str):
    """Update service uptime"""
    service_uptime_seconds.labels(service=service_name).set(uptime_seconds)

def update_memory_usage(memory_bytes: int, service_name: str):
    """Update memory usage"""
    memory_usage_bytes.labels(service=service_name).set(memory_bytes)

def get_metrics() -> str:
    """Get metrics in Prometheus format"""
    return generate_latest(service_registry).decode('utf-8')

def get_metrics_content_type() -> str:
    """Get metrics content type"""
    return CONTENT_TYPE_LATEST
