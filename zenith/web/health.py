"""
Health check utilities for Zenith framework.

Provides built-in health and readiness probes for monitoring
and deployment orchestration.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from starlette.responses import JSONResponse
from starlette.requests import Request


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class OverallHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: float
    checks: List[HealthCheckResult] = field(default_factory=list)
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "details": check.details
                }
                for check in self.checks
            ]
        }


class HealthCheck:
    """Individual health check implementation."""
    
    def __init__(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]],
        timeout: float = 5.0,
        critical: bool = True
    ):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.critical = critical  # If True, failure marks overall system unhealthy
    
    async def run(self) -> HealthCheckResult:
        """Run the health check with timeout."""
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(self.check_func(), timeout=self.timeout)
            duration_ms = (time.time() - start_time) * 1000
            
            if result:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="OK",
                    duration_ms=duration_ms
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Check failed",
                    duration_ms=duration_ms
                )
                
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Timeout after {self.timeout}s",
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Error: {str(e)}",
                duration_ms=duration_ms
            )


class HealthManager:
    """Manages multiple health checks."""
    
    def __init__(self, version: Optional[str] = None):
        self.checks: List[HealthCheck] = []
        self.version = version
        self._startup_time = time.time()
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check."""
        self.checks.append(check)
    
    def add_simple_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]],
        timeout: float = 5.0,
        critical: bool = True
    ) -> None:
        """Add a simple health check function."""
        check = HealthCheck(name, check_func, timeout, critical)
        self.add_check(check)
    
    async def run_checks(self, include_non_critical: bool = True) -> OverallHealth:
        """Run all health checks and return overall status."""
        checks_to_run = self.checks
        if not include_non_critical:
            checks_to_run = [c for c in self.checks if c.critical]
        
        # Run all checks concurrently
        results = await asyncio.gather(
            *[check.run() for check in checks_to_run],
            return_exceptions=True
        )
        
        # Process results
        check_results = []
        overall_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle unexpected exceptions
                check_result = HealthCheckResult(
                    name=checks_to_run[i].name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Unexpected error: {str(result)}"
                )
            else:
                check_result = result
            
            check_results.append(check_result)
            
            # Update overall status
            if check_result.status == HealthStatus.UNHEALTHY:
                if checks_to_run[i].critical:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            elif check_result.status == HealthStatus.DEGRADED:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        return OverallHealth(
            status=overall_status,
            timestamp=time.time(),
            checks=check_results,
            version=self.version
        )
    
    # Built-in health checks
    async def check_database(self) -> bool:
        """Check database connectivity."""
        try:
            # This should be implemented based on your database setup
            # For now, just return True as placeholder
            return True
        except Exception:
            return False
    
    async def check_redis(self) -> bool:
        """Check Redis connectivity."""
        try:
            # Placeholder - implement actual Redis check
            return True
        except Exception:
            return False
    
    def add_database_check(self, timeout: float = 5.0) -> None:
        """Add database connectivity check."""
        self.add_simple_check("database", self.check_database, timeout, critical=True)
    
    def add_redis_check(self, timeout: float = 3.0) -> None:
        """Add Redis connectivity check."""
        self.add_simple_check("redis", self.check_redis, timeout, critical=False)
    
    def add_uptime_check(self, min_uptime: float = 30.0) -> None:
        """Add uptime check (useful for readiness probes)."""
        async def check_uptime() -> bool:
            uptime = time.time() - self._startup_time
            return uptime >= min_uptime
        
        self.add_simple_check("uptime", check_uptime, timeout=1.0, critical=True)


# Global health manager instance
health_manager = HealthManager()


# Route handlers
async def health_endpoint(request: Request) -> JSONResponse:
    """Health check endpoint handler."""
    health = await health_manager.run_checks(include_non_critical=True)
    
    status_code = 200
    if health.status == HealthStatus.UNHEALTHY:
        status_code = 503  # Service Unavailable
    elif health.status == HealthStatus.DEGRADED:
        status_code = 200  # Still OK, just degraded
    
    return JSONResponse(health.to_dict(), status_code=status_code)


async def readiness_endpoint(request: Request) -> JSONResponse:
    """Readiness check endpoint handler (critical checks only)."""
    health = await health_manager.run_checks(include_non_critical=False)
    
    status_code = 200 if health.status == HealthStatus.HEALTHY else 503
    
    # Minimal response for readiness
    return JSONResponse(
        {
            "status": health.status.value,
            "timestamp": health.timestamp
        },
        status_code=status_code
    )


async def liveness_endpoint(request: Request) -> JSONResponse:
    """Liveness check endpoint handler (minimal check)."""
    return JSONResponse(
        {
            "status": "alive",
            "timestamp": time.time()
        },
        status_code=200
    )


# Convenience function to add health routes to an app
def add_health_routes(app, health_path: str = "/health", readiness_path: str = "/ready", liveness_path: str = "/live"):
    """Add health check routes to a Zenith application."""
    
    @app.get(health_path)
    async def health(request: Request):
        return await health_endpoint(request)
    
    @app.get(readiness_path)
    async def readiness(request: Request):
        return await readiness_endpoint(request)
    
    @app.get(liveness_path) 
    async def liveness(request: Request):
        return await liveness_endpoint(request)