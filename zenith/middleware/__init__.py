"""
Middleware system for Zenith applications.

Provides essential middleware for production applications:
- Response caching (in-memory and Redis)
- CORS (Cross-Origin Resource Sharing)
- CSRF (Cross-Site Request Forgery) protection
- Rate limiting
- Authentication
- Security headers
- Request/response logging with structured output
- Request ID tracking for distributed tracing
- Response compression (gzip/deflate)
- Error handling
"""

from .auth import AuthenticationMiddleware
from .cache import (
    CacheConfig,
    MemoryCache,
    RedisCache,
    ResponseCacheMiddleware,
    cache_control_headers,
    create_cache_middleware,
)
from .compression import CompressionConfig, CompressionMiddleware, create_compression_middleware
from .cors import CORSConfig, CORSMiddleware
from .csrf import CSRFConfig, CSRFError, CSRFMiddleware, create_csrf_middleware, get_csrf_token
from .exceptions import ExceptionHandlerMiddleware
from .logging import (
    JsonFormatter,
    RequestLoggingConfig,
    RequestLoggingMiddleware,
    StructuredFormatter,
    create_request_logging_middleware,
    setup_structured_logging,
)
from .rate_limit import (
    RateLimit,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitStorage,
    MemoryRateLimitStorage,
    RedisRateLimitStorage,
    create_rate_limiter,
    create_redis_rate_limiter,
)
from .request_id import (
    RequestIDConfig,
    RequestIDMiddleware,
    create_request_id_middleware,
    get_request_id,
)
from .security import (
    SecurityConfig,
    SecurityHeadersMiddleware,
    TrustedProxyMiddleware,
    constant_time_compare,
    generate_secure_token,
    get_development_security_config,
    get_strict_security_config,
    sanitize_html_input,
    validate_url,
)

__all__ = [
    "AuthenticationMiddleware",
    "CacheConfig",
    "CompressionConfig",
    "CompressionMiddleware", 
    "create_compression_middleware",
    "MemoryCache",
    "RedisCache", 
    "ResponseCacheMiddleware",
    "cache_control_headers",
    "create_cache_middleware",
    "CORSConfig",
    "CORSMiddleware",
    "CSRFConfig",
    "CSRFError",
    "CSRFMiddleware",
    "create_csrf_middleware",
    "get_csrf_token",
    "ExceptionHandlerMiddleware",
    "JsonFormatter",
    "RequestLoggingConfig",
    "RequestLoggingMiddleware",
    "StructuredFormatter",
    "create_request_logging_middleware",
    "setup_structured_logging",
    "RateLimit",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "RateLimitStorage",
    "MemoryRateLimitStorage",
    "RedisRateLimitStorage",
    "create_rate_limiter",
    "create_redis_rate_limiter",
    "RequestIDConfig",
    "RequestIDMiddleware",
    "create_request_id_middleware", 
    "get_request_id",
    "SecurityConfig",
    "SecurityHeadersMiddleware",
    "TrustedProxyMiddleware",
    "constant_time_compare",
    "generate_secure_token",
    "get_development_security_config",
    "get_strict_security_config",
    "sanitize_html_input",
    "validate_url",
]
