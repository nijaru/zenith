---
title: Middleware
description: Request processing and response handling in Zenith
---

import { Code, Aside } from '@astrojs/starlight/components';

## What is Middleware?

Middleware are functions that process requests before they reach your route handlers and responses before they're sent to clients. Zenith provides a comprehensive set of production-ready middleware.

## Built-in Middleware

### Security Headers

Protect your application with industry-standard security headers:

```python
from zenith import Zenith
from zenith.middleware import SecurityHeadersMiddleware

app = Zenith(
    middleware=[
        SecurityHeadersMiddleware({
            "force_https": True,
            "hsts_max_age": 31536000,  # 1 year
            "content_type_nosniff": True,
            "frame_deny": True,
            "xss_protection": True,
            "csp": "default-src 'self'"
        })
    ]
)
```

### CORS (Cross-Origin Resource Sharing)

```python
from zenith.middleware import CORSMiddleware

app.add_middleware(CORSMiddleware, {
    "allow_origins": ["https://example.com", "http://localhost:3000"],
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["*"],
    "allow_credentials": True,
    "max_age": 86400  # 24 hours
})
```

### Rate Limiting

Prevent abuse with configurable rate limits:

```python
from zenith.middleware import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, {
    "default_limits": ["100/minute", "1000/hour"],
    "key_func": lambda request: request.client.host,
    "storage": "redis://localhost:6379",  # Or "memory" for in-memory
    "headers_enabled": True  # Add X-RateLimit-* headers
})

# Per-endpoint limits
@app.get("/api/expensive", rate_limit="10/minute")
async def expensive_operation():
    return {"result": "processed"}
```

### Authentication

```python
from zenith.middleware import AuthMiddleware
from zenith.auth import JWTConfig

app.add_middleware(AuthMiddleware, {
    "jwt_config": JWTConfig(
        secret_key="your-secret-key",
        algorithm="HS256",
        expire_minutes=30
    ),
    "exclude_paths": ["/auth/login", "/auth/register", "/health"]
})
```

### Request Logging

```python
from zenith.middleware import LoggingMiddleware
import logging

logging.basicConfig(level=logging.INFO)

app.add_middleware(LoggingMiddleware, {
    "log_request_body": False,  # Privacy consideration
    "log_response_body": False,
    "log_headers": ["User-Agent", "X-Request-ID"],
    "exclude_paths": ["/health", "/metrics"]
})
```

### Compression

```python
from zenith.middleware import CompressionMiddleware

app.add_middleware(CompressionMiddleware, {
    "minimum_size": 1024,  # Only compress responses > 1KB
    "gzip_level": 6,
    "br_quality": 4,  # Brotli quality (0-11)
    "exclude_types": ["image/jpeg", "image/png"]  # Already compressed
})
```

### Request ID

```python
from zenith.middleware import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware, {
    "header_name": "X-Request-ID",
    "generate": lambda: str(uuid.uuid4()),
    "trust_header": False  # Don't trust client-provided IDs
})
```

### CSRF Protection

```python
from zenith.middleware import CSRFMiddleware

app.add_middleware(CSRFMiddleware, {
    "cookie_name": "_csrf_token",
    "header_name": "X-CSRF-Token",
    "safe_methods": ["GET", "HEAD", "OPTIONS"],
    "cookie_secure": True,  # HTTPS only
    "cookie_samesite": "strict"
})
```

## Custom Middleware

### Basic Middleware

```python
from zenith import Request, Response
from typing import Callable, Awaitable

class TimingMiddleware:
    """Add response time header."""
    
    def __init__(self, app: Callable[[Request], Awaitable[Response]]):
        self.app = app
    
    async def __call__(self, request: Request) -> Response:
        import time
        start = time.time()
        
        # Process request
        response = await self.app(request)
        
        # Add timing header
        duration = time.time() - start
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response

app.add_middleware(TimingMiddleware)
```

### Middleware with Configuration

```python
class APIKeyMiddleware:
    """Validate API key."""
    
    def __init__(self, app, config: dict):
        self.app = app
        self.api_keys = config.get("api_keys", [])
        self.header_name = config.get("header_name", "X-API-Key")
    
    async def __call__(self, request: Request) -> Response:
        # Skip for excluded paths
        if request.url.path in ["/health", "/docs"]:
            return await self.app(request)
        
        # Check API key
        api_key = request.headers.get(self.header_name)
        if not api_key or api_key not in self.api_keys:
            return JSONResponse(
                {"error": "Invalid API key"},
                status_code=401
            )
        
        return await self.app(request)

app.add_middleware(APIKeyMiddleware, {
    "api_keys": ["key1", "key2"],
    "header_name": "X-API-Key"
})
```

### Async Middleware

```python
class DatabaseMiddleware:
    """Provide database connection."""
    
    def __init__(self, app, config: dict):
        self.app = app
        self.db_url = config["database_url"]
        self.pool = None
    
    async def startup(self):
        """Initialize connection pool."""
        self.pool = await create_pool(self.db_url)
    
    async def shutdown(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def __call__(self, request: Request) -> Response:
        async with self.pool.acquire() as conn:
            request.state.db = conn
            return await self.app(request)

app.add_middleware(DatabaseMiddleware, {
    "database_url": "postgresql://localhost/mydb"
})
```

## Middleware Order

Middleware are executed in the order they're added (for requests) and reverse order (for responses):

```python
app = Zenith(
    middleware=[
        SecurityHeadersMiddleware({}),  # 1st request, last response
        CORSMiddleware({}),             # 2nd request, 2nd-last response
        RateLimitMiddleware({}),        # 3rd request, 3rd-last response
        AuthMiddleware({}),             # 4th request, 4th-last response
        LoggingMiddleware({})           # Last request, 1st response
    ]
)
```

<Aside type="caution">
  **Important**: Middleware order matters! Authentication should come before rate limiting, and security headers should be applied last (first in the list).
</Aside>

## Conditional Middleware

```python
from zenith import Zenith
import os

app = Zenith()

# Only add in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(SecurityHeadersMiddleware, {
        "force_https": True
    })
    app.add_middleware(RateLimitMiddleware, {
        "default_limits": ["100/minute"]
    })

# Always add CORS
app.add_middleware(CORSMiddleware, {
    "allow_origins": os.getenv("CORS_ORIGINS", "*").split(",")
})
```

## Middleware Groups

Organize middleware into logical groups:

```python
def setup_security_middleware(app: Zenith):
    """Security-related middleware."""
    app.add_middleware(SecurityHeadersMiddleware, {
        "force_https": True
    })
    app.add_middleware(CSRFMiddleware, {
        "cookie_secure": True
    })
    app.add_middleware(RateLimitMiddleware, {
        "default_limits": ["100/minute"]
    })

def setup_monitoring_middleware(app: Zenith):
    """Monitoring and observability."""
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware, {
        "exclude_paths": ["/health"]
    })
    app.add_middleware(MetricsMiddleware)

# Apply groups
app = Zenith()
setup_security_middleware(app)
setup_monitoring_middleware(app)
```

## Performance Considerations

### Lightweight Middleware

```python
class FastMiddleware:
    """Minimal overhead middleware."""
    
    __slots__ = ['app', 'config']  # Memory optimization
    
    def __init__(self, app, config: dict):
        self.app = app
        self.config = config
    
    async def __call__(self, request: Request) -> Response:
        # Quick check, minimal processing
        if self.should_skip(request):
            return await self.app(request)
        
        # Fast operation
        request.state.processed = True
        return await self.app(request)
    
    def should_skip(self, request: Request) -> bool:
        # O(1) lookup
        return request.url.path in self.config.get('skip_paths', set())
```

### Caching Middleware

```python
from zenith.middleware import CacheMiddleware

app.add_middleware(CacheMiddleware, {
    "backend": "redis://localhost:6379",
    "default_ttl": 300,  # 5 minutes
    "key_prefix": "zenith:cache:",
    "methods": ["GET", "HEAD"],
    "status_codes": [200, 301, 308]
})

# Per-endpoint caching
@app.get("/api/data", cache_ttl=3600)  # 1 hour
async def get_data():
    return expensive_computation()
```

## Testing Middleware

```python
from zenith.testing import TestClient
import pytest

@pytest.mark.asyncio
async def test_rate_limit():
    app = Zenith()
    app.add_middleware(RateLimitMiddleware, {
        "default_limits": ["5/minute"]
    })
    
    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}
    
    async with TestClient(app) as client:
        # Should succeed for first 5 requests
        for _ in range(5):
            response = await client.get("/test")
            assert response.status_code == 200
        
        # Should fail on 6th request
        response = await client.get("/test")
        assert response.status_code == 429
        assert "X-RateLimit-Remaining" in response.headers
```

## Next Steps

- Implement [Authentication](/concepts/authentication) with middleware
- Learn about [Database](/concepts/database) middleware
- Explore [Performance](/features/performance) optimization