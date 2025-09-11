"""
Response caching middleware for Zenith applications.

Provides in-memory and Redis-based response caching for GET requests
to improve API performance and reduce database load.
"""

import hashlib
import json
import time
from typing import Any

from zenith.core.json_encoder import _json_dumps, _json_loads

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CacheConfig:
    """Configuration for response caching middleware."""
    
    def __init__(
        self,
        # Cache settings
        default_ttl: int = 300,  # 5 minutes default
        max_cache_items: int = 1000,  # Max items in memory cache
        # Cache control
        cache_methods: list[str] | None = None,
        cache_status_codes: list[int] | None = None,
        # Path configuration
        cache_paths: list[str] | None = None,
        ignore_paths: list[str] | None = None,
        # Query parameters
        ignore_query_params: list[str] | None = None,
        vary_headers: list[str] | None = None,
        # Redis settings (optional)
        use_redis: bool = False,
        redis_client: Any = None,
        redis_prefix: str = "zenith:cache:",
    ):
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_items
        
        self.cache_methods = cache_methods or ["GET", "HEAD"]
        self.cache_status_codes = cache_status_codes or [200, 201, 203, 300, 301, 302, 304, 307, 308]
        
        self.cache_paths = set(cache_paths or [])
        self.ignore_paths = set(ignore_paths or [])
        
        self.ignore_query_params = set(ignore_query_params or [])
        self.vary_headers = vary_headers or ["Authorization", "Accept-Language"]
        
        self.use_redis = use_redis
        self.redis_client = redis_client
        self.redis_prefix = redis_prefix


class MemoryCache:
    """Simple in-memory LRU cache."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: dict[str, dict] = {}
        self.access_times: dict[str, float] = {}
    
    def get(self, key: str) -> dict | None:
        """Get cached item."""
        if key not in self.cache:
            return None
            
        item = self.cache[key]
        
        # Check if expired
        if time.time() > item["expires_at"]:
            self.delete(key)
            return None
            
        # Update access time for LRU
        self.access_times[key] = time.time()
        return item
    
    def set(self, key: str, data: dict, ttl: int) -> None:
        """Set cached item with TTL."""
        # Evict oldest items if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
            
        self.cache[key] = {
            "content": data["content"],
            "media_type": data["media_type"],
            "headers": data["headers"],
            "status_code": data["status_code"],
            "expires_at": time.time() + ttl,
            "cached_at": time.time(),
        }
        self.access_times[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Delete cached item."""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.access_times.clear()
    
    def _evict_oldest(self) -> None:
        """Evict oldest accessed item."""
        if not self.access_times:
            return
            
        oldest_key = min(self.access_times, key=self.access_times.get)
        self.delete(oldest_key)


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching HTTP responses."""
    
    def __init__(self, app, config: CacheConfig = None):
        super().__init__(app)
        self.config = config or CacheConfig()
        
        # Initialize cache backend
        if self.config.use_redis and self.config.redis_client:
            self.cache = RedisCache(self.config.redis_client, self.config.redis_prefix)
        else:
            self.cache = MemoryCache(self.config.max_cache_size)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Cache responses for GET requests."""
        
        # Only cache specific methods
        if request.method not in self.config.cache_methods:
            return await call_next(request)
        
        # Check if path should be cached
        if not self._should_cache_path(request.url.path):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get cached response
        cached = self.cache.get(cache_key)
        if cached:
            return Response(
                content=cached["content"],
                status_code=cached["status_code"],
                headers=dict(cached["headers"], **{"X-Cache": "HIT"}),
                media_type=cached["media_type"],
            )
        
        # Get fresh response
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code in self.config.cache_status_codes:
            await self._cache_response(cache_key, response)
            response.headers["X-Cache"] = "MISS"
        
        return response
    
    def _should_cache_path(self, path: str) -> bool:
        """Check if path should be cached."""
        # If specific cache paths are configured, only cache those
        if self.config.cache_paths:
            return any(path.startswith(cache_path) for cache_path in self.config.cache_paths)
        
        # Check ignore paths
        if self.config.ignore_paths:
            return not any(path.startswith(ignore_path) for ignore_path in self.config.ignore_paths)
        
        return True
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        # Start with method and path
        key_parts = [request.method, request.url.path]
        
        # Add relevant query parameters
        query_params = dict(request.query_params)
        for ignore_param in self.config.ignore_query_params:
            query_params.pop(ignore_param, None)
        
        if query_params:
            key_parts.append(_json_dumps(query_params))
        
        # Add vary headers
        for header in self.config.vary_headers:
            if header.lower() in request.headers:
                key_parts.append(f"{header}:{request.headers[header.lower()]}")
        
        # Create hash
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _cache_response(self, cache_key: str, response: Response) -> None:
        """Cache response data."""
        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Store in cache
        cache_data = {
            "content": body,
            "media_type": response.media_type,
            "headers": dict(response.headers),
            "status_code": response.status_code,
        }
        
        self.cache.set(cache_key, cache_data, self.config.default_ttl)
        
        # Recreate response with cached body
        response.body_iterator = iter([body])


class RedisCache:
    """Redis-based cache backend."""
    
    def __init__(self, redis_client, prefix: str = "zenith:cache:"):
        self.redis = redis_client
        self.prefix = prefix
    
    def get(self, key: str) -> dict | None:
        """Get cached item from Redis."""
        try:
            data = self.redis.get(f"{self.prefix}{key}")
            if data:
                return _json_loads(data)
            return None
        except Exception:
            return None
    
    def set(self, key: str, data: dict, ttl: int) -> None:
        """Set cached item in Redis with TTL."""
        try:
            serialized = _json_dumps(data)
            self.redis.setex(f"{self.prefix}{key}", ttl, serialized)
        except Exception:
            pass  # Fail silently for cache errors
    
    def delete(self, key: str) -> None:
        """Delete cached item from Redis."""
        try:
            self.redis.delete(f"{self.prefix}{key}")
        except Exception:
            pass
    
    def clear(self) -> None:
        """Clear all cached items with prefix."""
        try:
            keys = self.redis.keys(f"{self.prefix}*")
            if keys:
                self.redis.delete(*keys)
        except Exception:
            pass


# Convenience functions
def create_cache_middleware(
    default_ttl: int = 300,
    cache_paths: list[str] | None = None,
    ignore_paths: list[str] | None = None,
    use_redis: bool = False,
    redis_client: Any = None,
    **kwargs
) -> ResponseCacheMiddleware:
    """
    Create response cache middleware with common defaults.
    
    Args:
        default_ttl: Default cache time-to-live in seconds
        cache_paths: Specific paths to cache (None caches all eligible responses)
        ignore_paths: Paths to exclude from caching
        use_redis: Whether to use Redis for cache storage
        redis_client: Redis client instance (required if use_redis=True)
        **kwargs: Additional arguments passed to ResponseCacheMiddleware
        
    Returns:
        Configured ResponseCacheMiddleware instance
    """
    
    # Default ignore paths for APIs
    default_ignore = {
        "/health",
        "/metrics", 
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    if ignore_paths:
        default_ignore.update(ignore_paths)
    
    config = CacheConfig(
        default_ttl=default_ttl,
        cache_paths=cache_paths,
        ignore_paths=list(default_ignore),
        use_redis=use_redis,
        redis_client=redis_client,
        **kwargs
    )
    
    return ResponseCacheMiddleware(app=None, config=config)


def cache_control_headers(max_age_secs: int = 300, is_public: bool = True) -> dict[str, str]:
    """Generate cache control headers for manual caching."""
    headers = {}
    
    if is_public:
        headers["Cache-Control"] = f"public, max-age={max_age_secs}"
    else:
        headers["Cache-Control"] = f"private, max-age={max_age_secs}"
    
    headers["ETag"] = f'"{int(time.time())}"'
    
    return headers