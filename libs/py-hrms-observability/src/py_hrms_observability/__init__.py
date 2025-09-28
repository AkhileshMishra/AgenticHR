"""AgenticHR Observability Library."""

from .metrics import (
    MetricsMiddleware,
    track_db_operation,
    track_business_operation,
    track_task_execution,
    record_auth_attempt,
    set_active_tokens,
    set_db_connections,
    set_service_info,
    update_uptime,
    update_memory_usage,
    get_metrics,
    get_metrics_content_type,
)

from .logging import (
    configure_logging,
    LoggingMiddleware,
    PerformanceLogger,
    log_performance,
    log_business_event,
    log_security_event,
    log_audit_event,
    log_error,
    get_logger,
    set_correlation_id,
    set_user_context,
    get_correlation_id,
    generate_correlation_id,
    debug, info, warning, error, critical,
)

from .tracing import (
    configure_tracing,
    get_tracer,
    create_span,
    trace_function,
    trace_database_operation,
    trace_business_operation,
    trace_external_call,
    add_span_attribute,
    add_span_event,
    record_exception,
    get_trace_id,
    get_span_id,
    TracingContext,
    create_tracing_context,
)

from .health import (
    HealthStatus,
    HealthCheck,
    HealthReport,
    HealthChecker,
    database_health_check,
    redis_health_check,
    http_service_health_check,
    celery_health_check,
    add_health_endpoints,
)

__all__ = [
    # Metrics
    "MetricsMiddleware",
    "track_db_operation",
    "track_business_operation", 
    "track_task_execution",
    "record_auth_attempt",
    "set_active_tokens",
    "set_db_connections",
    "set_service_info",
    "update_uptime",
    "update_memory_usage",
    "get_metrics",
    "get_metrics_content_type",
    
    # Logging
    "configure_logging",
    "LoggingMiddleware",
    "PerformanceLogger",
    "log_performance",
    "log_business_event",
    "log_security_event",
    "log_audit_event",
    "log_error",
    "get_logger",
    "set_correlation_id",
    "set_user_context",
    "get_correlation_id",
    "generate_correlation_id",
    "debug", "info", "warning", "error", "critical",
    
    # Tracing
    "configure_tracing",
    "get_tracer",
    "create_span",
    "trace_function",
    "trace_database_operation",
    "trace_business_operation",
    "trace_external_call",
    "add_span_attribute",
    "add_span_event",
    "record_exception",
    "get_trace_id",
    "get_span_id",
    "TracingContext",
    "create_tracing_context",
    
    # Health
    "HealthStatus",
    "HealthCheck",
    "HealthReport",
    "HealthChecker",
    "database_health_check",
    "redis_health_check",
    "http_service_health_check",
    "celery_health_check",
    "add_health_endpoints",
]

__version__ = "0.1.0"
