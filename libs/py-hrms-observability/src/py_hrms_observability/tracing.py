"""
Distributed tracing for AgenticHR services

This module provides OpenTelemetry-based distributed tracing with:
- Automatic instrumentation for FastAPI, SQLAlchemy, and HTTP clients
- Custom span creation and annotation
- Trace correlation across services
- Performance monitoring
"""
import os
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

def configure_tracing(
    service_name: str,
    service_version: str = "0.1.0",
    jaeger_endpoint: Optional[str] = None,
    sample_rate: float = 1.0
):
    """Configure OpenTelemetry tracing for the service"""
    
    # Create resource with service information
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: service_version,
        ResourceAttributes.SERVICE_NAMESPACE: "agentichr",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Configure Jaeger exporter if endpoint provided
    if jaeger_endpoint or os.getenv("JAEGER_ENDPOINT"):
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_endpoint or os.getenv("JAEGER_ENDPOINT", "localhost"),
            agent_port=int(os.getenv("JAEGER_PORT", "6831")),
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)
    
    # Set the global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Auto-instrument common libraries
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()

def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name)

def create_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
) -> trace.Span:
    """Create a new span"""
    tracer = trace.get_tracer(__name__)
    span = tracer.start_span(name, kind=kind)
    
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    
    return span

def trace_function(
    name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator to trace function execution"""
    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name, kind=kind) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            description=str(e)
                        )
                    )
                    span.record_exception(e)
                    raise
        
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name, kind=kind) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            description=str(e)
                        )
                    )
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def trace_database_operation(
    operation: str,
    table: str,
    query: Optional[str] = None
):
    """Decorator to trace database operations"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                f"db.{operation}",
                kind=trace.SpanKind.CLIENT
            ) as span:
                # Add database attributes
                span.set_attribute("db.operation", operation)
                span.set_attribute("db.table", table)
                span.set_attribute("db.system", "postgresql")
                
                if query:
                    span.set_attribute("db.statement", query)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    
                    # Add result info if available
                    if hasattr(result, 'rowcount'):
                        span.set_attribute("db.rows_affected", result.rowcount)
                    
                    return result
                except Exception as e:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            description=str(e)
                        )
                    )
                    span.record_exception(e)
                    raise
        
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                f"db.{operation}",
                kind=trace.SpanKind.CLIENT
            ) as span:
                # Add database attributes
                span.set_attribute("db.operation", operation)
                span.set_attribute("db.table", table)
                span.set_attribute("db.system", "postgresql")
                
                if query:
                    span.set_attribute("db.statement", query)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    
                    # Add result info if available
                    if hasattr(result, 'rowcount'):
                        span.set_attribute("db.rows_affected", result.rowcount)
                    
                    return result
                except Exception as e:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            description=str(e)
                        )
                    )
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def trace_business_operation(operation: str, **attributes):
    """Decorator to trace business operations"""
    def decorator(func):
        return trace_function(
            name=f"business.{operation}",
            kind=trace.SpanKind.INTERNAL,
            attributes=attributes
        )(func)
    
    return decorator

def trace_external_call(service: str, operation: str):
    """Decorator to trace external service calls"""
    def decorator(func):
        return trace_function(
            name=f"external.{service}.{operation}",
            kind=trace.SpanKind.CLIENT,
            attributes={
                "external.service": service,
                "external.operation": operation
            }
        )(func)
    
    return decorator

def add_span_attribute(key: str, value: Any):
    """Add attribute to current span"""
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute(key, value)

def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Add event to current span"""
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name, attributes or {})

def record_exception(exception: Exception):
    """Record exception in current span"""
    current_span = trace.get_current_span()
    if current_span:
        current_span.record_exception(exception)
        current_span.set_status(
            trace.Status(
                trace.StatusCode.ERROR,
                description=str(exception)
            )
        )

def get_trace_id() -> Optional[str]:
    """Get current trace ID"""
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        return format(current_span.get_span_context().trace_id, '032x')
    return None

def get_span_id() -> Optional[str]:
    """Get current span ID"""
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        return format(current_span.get_span_context().span_id, '016x')
    return None

class TracingContext:
    """Context manager for creating spans"""
    
    def __init__(
        self,
        name: str,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.kind = kind
        self.attributes = attributes or {}
        self.span = None
        self.tracer = trace.get_tracer(__name__)
    
    def __enter__(self):
        self.span = self.tracer.start_span(self.name, kind=self.kind)
        
        # Add attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        
        # Make span current
        self.token = trace.set_span_in_context(self.span)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(
                trace.Status(
                    trace.StatusCode.ERROR,
                    description=str(exc_val)
                )
            )
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(trace.Status(trace.StatusCode.OK))
        
        self.span.end()

def create_tracing_context(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    **attributes
) -> TracingContext:
    """Create a tracing context manager"""
    return TracingContext(name, kind, attributes)
