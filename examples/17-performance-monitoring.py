"""
[*] Zenith Performance Monitoring - Complete Observability Stack

This example demonstrates comprehensive performance monitoring, health checks,
metrics collection, and profiling capabilities for production applications.

Key Monitoring Features Demonstrated:
- Health Check endpoints (/health, /health/detailed)
- Prometheus-compatible metrics (/metrics)
- Performance decorators (@cached, @measure_time)
- Request/response time tracking
- Memory and system resource monitoring
- Custom business metrics
- Performance profiling and bottleneck detection

Run with: python examples/12-performance-monitoring.py
Visit: http://localhost:8002

Monitoring Endpoints:
- GET /health                 - Basic health check
- GET /health/detailed        - Comprehensive system health
- GET /metrics                - Prometheus metrics
- GET /performance            - Performance profiling data
- GET /cache/stats            - Cache performance statistics
- POST /api/expensive         - Simulate expensive operation (cached)
- GET /api/slow               - Simulate slow operation (monitored)
"""

import asyncio
import os

# Optional system monitoring (pip install psutil for full functionality)
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
import random
import time
from datetime import datetime

from pydantic import BaseModel

from zenith import Zenith
from zenith.monitoring.health import HealthCheck, HealthManager, HealthStatus
from zenith.monitoring.metrics import MetricsCollector, record_request_metrics
from zenith.monitoring.performance import (
    PerformanceProfiler,
    cache_stats,
    cached,
    clear_cache,
)

# ============================================================================
# MODELS
# ============================================================================


class ExpensiveRequest(BaseModel):
    """Data for expensive operation."""

    complexity: int = 1
    processing_time: float | None = None


class PerformanceStats(BaseModel):
    """Performance statistics."""

    cache_stats: dict
    health_status: str
    system_resources: dict
    active_connections: int
    request_metrics: dict


# ============================================================================
# GLOBAL MONITORING SETUP
# ============================================================================

# Performance profiler instance
profiler = PerformanceProfiler()

# Metrics collector instance
metrics = MetricsCollector()

# Application with monitoring configuration
app = Zenith()


# ============================================================================
# CUSTOM HEALTH CHECKS
# ============================================================================


async def database_health_check() -> bool:
    """Simulate database connectivity check."""
    # In a real app, this would check actual database connection
    await asyncio.sleep(0.1)  # Simulate connection check
    return random.choice([True, True, True, False])  # 75% success rate


async def redis_health_check() -> bool:
    """Simulate Redis connectivity check."""
    await asyncio.sleep(0.05)  # Simulate Redis ping
    return True


async def external_api_health_check() -> bool:
    """Simulate external API dependency check."""
    await asyncio.sleep(0.2)  # Simulate API call
    return random.choice([True, True, False])  # 66% success rate


async def memory_health_check() -> bool:
    """Check system memory usage."""
    if not HAS_PSUTIL:
        return True  # Assume healthy if psutil not available
    try:
        memory = psutil.virtual_memory()
        return memory.percent < 90  # Unhealthy if > 90% memory usage
    except Exception:
        return False


# Health manager with custom checks
health_manager = HealthManager(version="1.0.0")

# Add individual health checks
health_manager.add_check(
    HealthCheck("database", database_health_check, timeout_secs=2.0, critical=True)
)
health_manager.add_check(
    HealthCheck("redis", redis_health_check, timeout_secs=1.0, critical=False)
)
health_manager.add_check(
    HealthCheck(
        "external_api", external_api_health_check, timeout_secs=3.0, critical=False
    )
)
health_manager.add_check(
    HealthCheck("memory", memory_health_check, timeout_secs=1.0, critical=True)
)


# ============================================================================
# PERFORMANCE MONITORING UTILITIES
# ============================================================================


def get_system_resources() -> dict:
    """Get current system resource usage."""
    if not HAS_PSUTIL:
        return {
            "cpu_percent": "N/A (install psutil)",
            "memory_percent": "N/A (install psutil)",
            "disk_percent": "N/A (install psutil)",
            "process_count": "N/A (install psutil)",
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
            "note": "Install psutil for full system monitoring: pip install psutil",
        }
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "process_count": len(psutil.pids()),
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
        }
    except Exception as e:
        return {"error": f"Could not get system resources: {e}"}


def track_request_metrics(
    endpoint: str, method: str, duration: float, status_code: int
):
    """Track request metrics."""
    # Record built-in HTTP metrics
    record_request_metrics(method, endpoint, status_code, duration, metrics)

    # Custom business metrics
    metrics.counter("requests_total", labels={"endpoint": endpoint, "method": method})
    metrics.histogram(
        "request_duration_seconds", duration, labels={"endpoint": endpoint}
    )

    if status_code >= 400:
        metrics.counter(
            "errors_total", labels={"endpoint": endpoint, "status": str(status_code)}
        )


# ============================================================================
# CACHED EXPENSIVE OPERATIONS
# ============================================================================


@cached(ttl=300)  # Cache for 5 minutes
async def expensive_database_query(user_id: int, complexity: int = 1) -> dict:
    """Simulate expensive database operation with caching."""
    # Simulate database processing time based on complexity
    processing_time = complexity * 0.5
    await asyncio.sleep(processing_time)

    # Track the operation
    with profiler.time_function("expensive_database_query"):
        # Simulate complex computation
        result = {
            "user_id": user_id,
            "data": [f"record_{i}" for i in range(complexity * 100)],
            "computed_score": sum(range(complexity * 1000)),
            "processing_time": processing_time,
            "cached_at": datetime.utcnow().isoformat(),
        }

    # Update metrics
    metrics.counter("database_queries_total", labels={"type": "expensive"})
    metrics.histogram("query_processing_time", processing_time)

    return result


@cached(
    ttl=60,
    key_func=lambda *args, **kwargs: f"user_profile_{kwargs.get('user_id', 'unknown')}",
)
async def get_user_profile(user_id: int) -> dict:
    """Get user profile with smart caching."""
    await asyncio.sleep(0.2)  # Simulate database lookup

    return {
        "user_id": user_id,
        "profile": f"User {user_id} profile data",
        "last_updated": datetime.utcnow().isoformat(),
    }


# ============================================================================
# MONITORED SLOW OPERATIONS
# ============================================================================


async def slow_operation_with_monitoring(duration: float = 1.0) -> dict:
    """Slow operation with comprehensive monitoring."""
    start_time = time.time()

    # Start profiling
    with profiler.time_function("slow_operation"):
        # Update metrics
        metrics.counter("slow_operations_started")
        metrics.gauge("active_operations", profiler.active_operations)

        # Simulate work with progress updates
        steps = int(duration * 10)  # 10 steps per second
        for i in range(steps):
            await asyncio.sleep(0.1)
            # Update progress metric
            progress = (i + 1) / steps * 100
            metrics.gauge("operation_progress_percent", progress)

        # Final results
        actual_duration = time.time() - start_time
        metrics.histogram("operation_duration_seconds", actual_duration)
        metrics.counter("slow_operations_completed")

        return {
            "duration": actual_duration,
            "steps_completed": steps,
            "performance_impact": "monitored",
        }


# ============================================================================
# MONITORING ENDPOINTS
# ============================================================================


@app.get("/health")
async def basic_health_check():
    """Basic health check endpoint."""
    start_time = time.time()

    # Simple health check
    status = "healthy"
    checks = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": status,
        "uptime": time.time() - app.startup_time if hasattr(app, "startup_time") else 0,
    }

    # Track metrics
    duration = time.time() - start_time
    track_request_metrics("/health", "GET", duration, 200)

    return checks


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with all dependencies."""
    start_time = time.time()

    # Run all health checks
    health_result = await health_manager.run_checks()

    # Add system information
    system_info = {
        "system_resources": get_system_resources(),
        "cache_statistics": cache_stats(),
        "performance_profile": profiler.get_stats(),
        "active_metrics": len(metrics._counters) + len(metrics._gauges),
    }

    response_data = {
        **health_result.to_dict(),
        "system_info": system_info,
    }

    # Track metrics
    duration = time.time() - start_time
    status_code = 200 if health_result.status == HealthStatus.HEALTHY else 503
    track_request_metrics("/health/detailed", "GET", duration, status_code)

    return response_data


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    # Generate Prometheus format
    prometheus_data = metrics.export_prometheus()

    # Add custom application metrics
    additional_metrics = []

    # System metrics
    try:
        resources = get_system_resources()
        for metric, value in resources.items():
            if isinstance(value, (int, float)):
                additional_metrics.append(f"system_{metric} {value}")
    except Exception:
        pass

    # Cache metrics
    cache_metrics = cache_stats()
    for metric, value in cache_metrics.items():
        if isinstance(value, (int, float)):
            additional_metrics.append(f"cache_{metric} {value}")

    # Performance metrics
    perf_stats = profiler.get_stats()
    for func_name, stats in perf_stats.items():
        if isinstance(stats, dict) and "avg_time" in stats:
            additional_metrics.append(
                f'function_avg_duration_seconds{{function="{func_name}"}} {stats["avg_time"]}'
            )
            additional_metrics.append(
                f'function_call_count{{function="{func_name}"}} {stats["call_count"]}'
            )

    # Combine all metrics
    full_metrics = prometheus_data + "\n" + "\n".join(additional_metrics)

    return full_metrics


@app.get("/performance")
async def performance_stats():
    """Detailed performance statistics."""
    return PerformanceStats(
        cache_stats=cache_stats(),
        health_status="healthy",  # Simplified for example
        system_resources=get_system_resources(),
        active_connections=1,  # Simplified for example
        request_metrics={
            "total_requests": metrics._counters.get("requests_total", 0),
            "error_rate": "< 1%",  # Simplified calculation
            "avg_response_time": "< 100ms",  # Simplified calculation
        },
    ).model_dump()


@app.get("/cache/stats")
async def cache_statistics():
    """Detailed cache performance statistics."""
    stats = cache_stats()

    # Add cache content information
    cache_info = {
        **stats,
        "cache_entries": [
            {
                "function": "expensive_database_query",
                "description": "Database query results cached for 5 minutes",
            },
            {
                "function": "get_user_profile",
                "description": "User profile data cached for 1 minute",
            },
        ],
        "cache_tips": [
            "Monitor hit rate - aim for >80% for frequently accessed data",
            "Adjust TTL based on data freshness requirements",
            "Use custom key functions for complex cache keys",
            "Clear cache when underlying data changes",
        ],
    }

    return cache_info


# ============================================================================
# API ENDPOINTS WITH MONITORING
# ============================================================================


@app.post("/api/expensive")
async def expensive_operation(request: ExpensiveRequest):
    """Expensive operation demonstrating caching and monitoring."""
    start_time = time.time()

    # This will use caching
    result = await expensive_database_query(
        user_id=random.randint(1, 100), complexity=request.complexity
    )

    # Track custom metrics
    duration = time.time() - start_time
    track_request_metrics("/api/expensive", "POST", duration, 200)
    metrics.gauge("last_expensive_operation_duration", duration)

    return {
        "message": "Expensive operation completed",
        "result": result,
        "performance_notes": {
            "cached": "Result cached for 5 minutes",
            "monitoring": "Duration and resource usage tracked",
            "profiling": "Function performance profiled",
        },
    }


@app.get("/api/slow")
async def slow_endpoint(duration: float = 2.0):
    """Slow endpoint demonstrating monitoring."""
    start_time = time.time()

    # Run monitored slow operation
    result = await slow_operation_with_monitoring(duration)

    # Track metrics
    actual_duration = time.time() - start_time
    track_request_metrics("/api/slow", "GET", actual_duration, 200)

    return {
        "message": "🐌 Slow operation completed",
        "operation_result": result,
        "monitoring_data": {
            "profiled": True,
            "metrics_recorded": True,
            "performance_tracked": True,
        },
    }


@app.get("/api/user/{user_id}")
async def get_user(user_id: int):
    """User endpoint with caching and monitoring."""
    start_time = time.time()

    # Get user profile (cached)
    profile = await get_user_profile(user_id)

    # Track metrics
    duration = time.time() - start_time
    track_request_metrics(f"/api/user/{user_id}", "GET", duration, 200)

    return {"user": profile, "cache_info": "Profile cached for 1 minute per user"}


# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================


@app.delete("/cache")
async def clear_application_cache():
    """Clear application cache."""
    start_time = time.time()

    old_stats = cache_stats()
    clear_cache()

    duration = time.time() - start_time
    track_request_metrics("/cache", "DELETE", duration, 200)

    return {
        "message": "🗑️ Cache cleared successfully",
        "previous_stats": old_stats,
        "new_stats": cache_stats(),
    }


# ============================================================================
# APPLICATION LIFECYCLE & MONITORING SETUP
# ============================================================================


@app.on_startup
async def setup_monitoring():
    """Initialize monitoring and profiling."""
    app.startup_time = time.time()

    # Start profiler
    profiler.enabled = True

    # Initialize baseline metrics
    metrics.gauge("application_startup_timestamp", app.startup_time)
    metrics.counter("application_starts")

    print("[*] Performance monitoring initialized")
    print(f"🏥 Health checks: {len(health_manager.checks)} configured")
    print("[*] Metrics collection active")
    print("[*] Performance profiling enabled")


@app.on_shutdown
async def cleanup_monitoring():
    """Clean up monitoring resources."""
    print("[*] Performance monitoring shutdown")

    # Final metrics
    uptime = time.time() - app.startup_time
    metrics.gauge("application_uptime_seconds", uptime)

    # Cleanup
    profiler.enabled = False


# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================

MONITORING_CONFIG = """
[*] MONITORING CONFIGURATION GUIDE

🏥 Health Checks:
   - GET /health - Basic liveness probe
   - GET /health/detailed - Full dependency checks
   - Configure timeouts and criticality levels
   - Use for K8s liveness/readiness probes

[*] Metrics Collection:
   - GET /metrics - Prometheus-compatible export
   - Automatic request metrics (count, duration, errors)
   - Custom business metrics with labels
   - System resource monitoring

[*] Performance Optimization:
   - @cached decorator for expensive operations
   - Smart cache key generation
   - TTL-based cache expiration
   - Cache hit rate monitoring

[*] Profiling & Debugging:
   - Function-level performance profiling
   - Request correlation and tracking
   - Resource usage monitoring
   - Bottleneck identification

🚨 Production Recommendations:
   - Set up alerts on health check failures
   - Monitor cache hit rates (aim for >80%)
   - Track P95/P99 response times
   - Set memory and CPU thresholds
   - Use structured logging with correlation IDs
"""

print(MONITORING_CONFIG)


if __name__ == "__main__":
    print("[*] Starting Zenith Performance Monitoring Demo")
    print("Visit: http://localhost:8002")
    print("Try /health, /metrics, and /performance endpoints!")
    print("\n" + MONITORING_CONFIG)

    app.run(host="127.0.0.1", port=8002, reload=True)
