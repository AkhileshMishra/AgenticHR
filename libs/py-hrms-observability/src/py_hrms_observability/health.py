"""
Health checks for AgenticHR services

This module provides comprehensive health checking including:
- Service health endpoints
- Dependency health checks
- Readiness and liveness probes
- Health status aggregation
"""
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import FastAPI, Response, status
import httpx
import psutil

class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: float
    details: Optional[Dict[str, Any]] = None

@dataclass
class HealthReport:
    """Overall health report"""
    status: HealthStatus
    service: str
    version: str
    timestamp: float
    uptime_seconds: float
    checks: List[HealthCheck]
    system_info: Optional[Dict[str, Any]] = None

class HealthChecker:
    """Health checker for services"""
    
    def __init__(self, service_name: str, service_version: str = "0.1.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.start_time = time.time()
        self.checks: Dict[str, Callable[[], Awaitable[HealthCheck]]] = {}
    
    def add_check(self, name: str, check_func: Callable[[], Awaitable[HealthCheck]]):
        """Add a health check"""
        self.checks[name] = check_func
    
    async def run_check(self, name: str, check_func: Callable) -> HealthCheck:
        """Run a single health check"""
        start_time = time.time()
        
        try:
            result = await check_func()
            duration = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheck):
                result.duration_ms = duration
                result.timestamp = time.time()
                return result
            else:
                # If check function returns boolean or other simple type
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                return HealthCheck(
                    name=name,
                    status=status,
                    message="OK" if result else "Check failed",
                    duration_ms=duration,
                    timestamp=time.time()
                )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=duration,
                timestamp=time.time(),
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def get_health_report(self, include_system_info: bool = True) -> HealthReport:
        """Get comprehensive health report"""
        check_results = []
        
        # Run all health checks
        for name, check_func in self.checks.items():
            result = await self.run_check(name, check_func)
            check_results.append(result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(check_results)
        
        # Get system info if requested
        system_info = None
        if include_system_info:
            system_info = self._get_system_info()
        
        return HealthReport(
            status=overall_status,
            service=self.service_name,
            version=self.service_version,
            timestamp=time.time(),
            uptime_seconds=time.time() - self.start_time,
            checks=check_results,
            system_info=system_info
        )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall health status from individual checks"""
        if not checks:
            return HealthStatus.HEALTHY
        
        statuses = [check.status for check in checks]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "process_count": len(psutil.pids()),
            }
        except Exception:
            return {"error": "Could not retrieve system info"}

# Common health check functions

async def database_health_check(
    database_url: str,
    timeout: float = 5.0
) -> HealthCheck:
    """Check database connectivity"""
    try:
        # This is a simplified check - in production you'd use actual DB connection
        import asyncpg
        
        start_time = time.time()
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=timeout
        )
        
        # Simple query to test connection
        await conn.fetchval("SELECT 1")
        await conn.close()
        
        duration = (time.time() - start_time) * 1000
        
        return HealthCheck(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection successful",
            duration_ms=duration,
            timestamp=time.time()
        )
    
    except asyncio.TimeoutError:
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connection timeout after {timeout}s",
            duration_ms=timeout * 1000,
            timestamp=time.time()
        )
    
    except Exception as e:
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connection failed: {str(e)}",
            duration_ms=0,
            timestamp=time.time(),
            details={"error": str(e)}
        )

async def redis_health_check(
    redis_url: str,
    timeout: float = 5.0
) -> HealthCheck:
    """Check Redis connectivity"""
    try:
        import redis.asyncio as redis
        
        start_time = time.time()
        client = redis.from_url(redis_url)
        
        # Simple ping to test connection
        await asyncio.wait_for(client.ping(), timeout=timeout)
        await client.close()
        
        duration = (time.time() - start_time) * 1000
        
        return HealthCheck(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful",
            duration_ms=duration,
            timestamp=time.time()
        )
    
    except asyncio.TimeoutError:
        return HealthCheck(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection timeout after {timeout}s",
            duration_ms=timeout * 1000,
            timestamp=time.time()
        )
    
    except Exception as e:
        return HealthCheck(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
            duration_ms=0,
            timestamp=time.time(),
            details={"error": str(e)}
        )

async def http_service_health_check(
    service_name: str,
    url: str,
    timeout: float = 5.0,
    expected_status: int = 200
) -> HealthCheck:
    """Check HTTP service health"""
    try:
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
        
        duration = (time.time() - start_time) * 1000
        
        if response.status_code == expected_status:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.HEALTHY,
                message=f"Service responded with status {response.status_code}",
                duration_ms=duration,
                timestamp=time.time(),
                details={"status_code": response.status_code}
            )
        else:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.DEGRADED,
                message=f"Service responded with unexpected status {response.status_code}",
                duration_ms=duration,
                timestamp=time.time(),
                details={"status_code": response.status_code, "expected": expected_status}
            )
    
    except asyncio.TimeoutError:
        return HealthCheck(
            name=service_name,
            status=HealthStatus.UNHEALTHY,
            message=f"Service timeout after {timeout}s",
            duration_ms=timeout * 1000,
            timestamp=time.time()
        )
    
    except Exception as e:
        return HealthCheck(
            name=service_name,
            status=HealthStatus.UNHEALTHY,
            message=f"Service check failed: {str(e)}",
            duration_ms=0,
            timestamp=time.time(),
            details={"error": str(e)}
        )

async def celery_health_check(
    broker_url: str,
    timeout: float = 5.0
) -> HealthCheck:
    """Check Celery broker health"""
    try:
        # This is a simplified check - in production you'd use actual Celery inspection
        if "redis://" in broker_url:
            return await redis_health_check(broker_url, timeout)
        elif "amqp://" in broker_url or "pyamqp://" in broker_url:
            # For RabbitMQ, we'd check AMQP connection
            return HealthCheck(
                name="celery_broker",
                status=HealthStatus.HEALTHY,
                message="Celery broker check not implemented",
                duration_ms=0,
                timestamp=time.time()
            )
        else:
            return HealthCheck(
                name="celery_broker",
                status=HealthStatus.UNKNOWN,
                message="Unknown broker type",
                duration_ms=0,
                timestamp=time.time()
            )
    
    except Exception as e:
        return HealthCheck(
            name="celery_broker",
            status=HealthStatus.UNHEALTHY,
            message=f"Celery broker check failed: {str(e)}",
            duration_ms=0,
            timestamp=time.time(),
            details={"error": str(e)}
        )

def add_health_endpoints(app: FastAPI, health_checker: HealthChecker):
    """Add health check endpoints to FastAPI app"""
    
    @app.get("/health")
    async def health():
        """Basic health check"""
        return {
            "status": "healthy",
            "service": health_checker.service_name,
            "version": health_checker.service_version,
            "timestamp": time.time()
        }
    
    @app.get("/health/detailed")
    async def detailed_health():
        """Detailed health check with all dependencies"""
        report = await health_checker.get_health_report()
        
        # Set HTTP status based on health
        status_code = status.HTTP_200_OK
        if report.status == HealthStatus.UNHEALTHY:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif report.status == HealthStatus.DEGRADED:
            status_code = status.HTTP_200_OK  # Still serving traffic
        
        return Response(
            content=str(asdict(report)),
            status_code=status_code,
            media_type="application/json"
        )
    
    @app.get("/health/ready")
    async def readiness():
        """Readiness probe - is service ready to serve traffic?"""
        report = await health_checker.get_health_report(include_system_info=False)
        
        if report.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            return {"status": "ready", "timestamp": time.time()}
        else:
            return Response(
                content='{"status": "not_ready"}',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json"
            )
    
    @app.get("/health/live")
    async def liveness():
        """Liveness probe - is service alive?"""
        # Simple liveness check - if we can respond, we're alive
        return {
            "status": "alive",
            "service": health_checker.service_name,
            "uptime_seconds": time.time() - health_checker.start_time,
            "timestamp": time.time()
        }
