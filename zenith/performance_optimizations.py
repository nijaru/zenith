"""
Performance optimizations for Zenith framework.

Provides optimized middleware configurations and performance-first defaults
for high-throughput applications like AI/ML APIs and fintech systems.
"""

from typing import Any
from zenith.middleware.security import SecurityConfig
from zenith.middleware.rate_limit import RateLimit, RateLimitConfig
from zenith.middleware.logging import RequestLoggingConfig
from zenith.middleware.compression import CompressionConfig


def get_minimal_security_config() -> SecurityConfig:
    """
    Minimal security configuration for high-performance APIs.
    
    Provides essential security headers with minimal processing overhead.
    Only includes the most critical security headers.
    """
    return SecurityConfig(
        # Essential security headers only
        content_type_nosniff=True,
        frame_options="DENY",
        xss_protection="1; mode=block",
        
        # Disable expensive features
        csp_policy=None,  # No CSP - reduces header processing
        hsts_max_age=0,   # No HSTS for APIs
        permissions_policy=None,  # No permissions policy
        referrer_policy=None,     # No referrer policy
        
        # Disable CSRF for API-only apps
        csrf_protection=False,
        force_https=False,  # Handle at load balancer level
    )


def get_performance_rate_limits() -> list[RateLimit]:
    """
    Performance-optimized rate limits for high-throughput APIs.
    
    Uses fewer, simpler rate limits to reduce processing overhead.
    """
    return [
        # Single rate limit - simpler processing
        RateLimit(requests=10000, window=3600, per="ip"),  # 10K/hour per IP
    ]


def get_minimal_logging_config() -> RequestLoggingConfig:
    """
    Minimal logging configuration for maximum performance.
    
    Logs only essential information with minimal processing.
    """
    return RequestLoggingConfig(
        level=30,  # WARNING level - only errors
        include_headers=False,
        include_body=False,
        exclude_health_checks=True,
        exclude_paths={"/health", "/metrics", "/ping", "/favicon.ico"},
        max_body_size=0,  # No body logging
    )


def get_optimized_compression_config() -> CompressionConfig:
    """
    Optimized compression for API responses.
    
    Compresses only large responses to balance speed vs bandwidth.
    """
    return CompressionConfig(
        minimum_size=2048,  # Only compress larger responses
        compressible_types={
            "application/json",  # Most common API response type
            "text/plain",
        },
        exclude_paths={
            "/health", "/metrics", "/ping", "/favicon.ico",
            "/api/v1/ping",  # Common API health check patterns
        }
    )


class PerformanceMiddlewareConfig:
    """
    Pre-configured middleware settings optimized for performance.
    
    Provides sensible defaults for different performance scenarios.
    """
    
    @staticmethod
    def api_optimized():
        """Configuration optimized for API-only applications."""
        return {
            'security': get_minimal_security_config(),
            'rate_limits': get_performance_rate_limits(),
            'logging': get_minimal_logging_config(),
            'compression': get_optimized_compression_config(),
        }
    
    # Note: Removed fintech_optimized() and ai_ml_optimized() to reduce API surface.
    # Users can customize the api_optimized() config for specific needs:
    #
    # For high-security applications:
    # config = PerformanceMiddlewareConfig.api_optimized()  
    # config['security'] = SecurityConfig(hsts_max_age=31536000, force_https=True)
    # config['rate_limits'] = [RateLimit(requests=1000, window=3600, per="ip")]
    #
    # For high-throughput ML applications:
    # config = PerformanceMiddlewareConfig.api_optimized()
    # config['rate_limits'] = [RateLimit(requests=50000, window=3600, per="ip")]
    # config['logging'] = RequestLoggingConfig(level=40)  # ERROR only


def create_performance_app_factory():
    """
    Factory function that creates optimized Zenith apps.
    
    Returns a function that creates Zenith apps with performance-first defaults.
    """
    def create_optimized_app(profile: str = "api", **kwargs):
        """
        Create a Zenith app with performance optimizations.
        
        Args:
            profile: Performance profile ("api", "fintech", "ai_ml")
            **kwargs: Additional arguments for docs configuration
        
        Returns:
            Zenith app configured for high performance
        """
        from zenith import Zenith
        from zenith.middleware import (
            SecurityHeadersMiddleware,
            RateLimitMiddleware, 
            RequestLoggingMiddleware,
            CompressionMiddleware
        )
        
        # Use API optimized config (only profile we support)
        config = PerformanceMiddlewareConfig.api_optimized()
        
        # Extract docs-related kwargs
        docs_kwargs = {}
        for key in ['title', 'version', 'description', 'docs_url', 'redoc_url', 'openapi_url']:
            if key in kwargs:
                docs_kwargs[key] = kwargs.pop(key)
        
        # Create app with no default middleware
        app = Zenith(debug=False, middleware=[], **kwargs)
        
        # Add only essential middleware in performance-optimized order
        # (fastest middleware first, most expensive last)
        
        # 1. Security headers (fast header additions)
        app.add_middleware(SecurityHeadersMiddleware, config=config['security'])
        
        # 2. Rate limiting (fast memory/Redis operations) 
        app.add_middleware(RateLimitMiddleware, 
                          default_limits=config['rate_limits'])
        
        # 3. Minimal logging (only if needed)
        if config['logging'].level <= 30:  # Only add if INFO or higher
            app.add_middleware(RequestLoggingMiddleware, config=config['logging'])
        
        # 4. Compression last (most expensive)
        app.add_middleware(CompressionMiddleware, config=config['compression'])
        
        # Configure docs if any docs kwargs were provided
        if docs_kwargs:
            app.add_docs(**docs_kwargs)
        
        return app
    
    return create_optimized_app


# Primary factory for all API applications
create_api_app = lambda **kwargs: create_performance_app_factory()("api", **kwargs)

# Advanced users can customize rate limits and logging as needed:
#
# from zenith.performance_optimizations import PerformanceMiddlewareConfig
# 
# # For ML APIs that need higher rate limits:
# config = PerformanceMiddlewareConfig.api_optimized()
# config['rate_limits'] = [RateLimit(requests=50000, window=3600, per="ip")]
# config['logging'] = RequestLoggingConfig(level=40)  # ERROR only
# 
# app = Zenith(debug=False, middleware=[])
# # Apply config manually...


def benchmark_middleware_impact():
    """
    Utility function to benchmark middleware performance impact.
    
    Helps developers understand the cost of each middleware layer.
    """
    import asyncio
    import time
    from zenith.testing import TestClient
    
    async def _benchmark():
        results = {}
        
        # Test bare app
        bare_app = create_performance_app_factory()("api")
        # Remove all middleware
        bare_app.user_middleware = []
        bare_app.middleware_stack = []
        
        @bare_app.get("/")
        async def hello():
            return {"msg": "hello"}
        
        async with TestClient(bare_app) as client:
            start = time.perf_counter()
            for _ in range(500):
                await client.get("/")
            bare_time = time.perf_counter() - start
            results['bare'] = 500 / bare_time
        
        # Test optimized app
        opt_app = create_api_app()
        @opt_app.get("/")
        async def hello():
            return {"msg": "hello"}
            
        async with TestClient(opt_app) as client:
            start = time.perf_counter()
            for _ in range(500):
                await client.get("/")
            opt_time = time.perf_counter() - start
            results['optimized'] = 500 / opt_time
        
        # Test default app
        from zenith import Zenith
        default_app = Zenith(debug=False)
        @default_app.get("/")
        async def hello():
            return {"msg": "hello"}
            
        async with TestClient(default_app) as client:
            start = time.perf_counter()
            for _ in range(500):
                await client.get("/")
            default_time = time.perf_counter() - start
            results['default'] = 500 / default_time
        
        return results
    
    return asyncio.run(_benchmark())


if __name__ == "__main__":
    # Quick benchmark
    results = benchmark_middleware_impact()
    print("Middleware Performance Comparison:")
    print(f"Bare app:      {results['bare']:.0f} req/s")
    print(f"Optimized:     {results['optimized']:.0f} req/s ({results['optimized']/results['bare']*100:.1f}% retention)")
    print(f"Default:       {results['default']:.0f} req/s ({results['default']/results['bare']*100:.1f}% retention)")