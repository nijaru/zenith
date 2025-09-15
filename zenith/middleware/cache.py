"""
Response caching middleware for Zenith applications.

Provides in-memory and Redis-based response caching for GET requests
to improve API performance and reduce database load.
"""

import contextlib
import hashlib
import time
from collections import OrderedDict
from typing import Any

import msgspec
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send


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
        self.cache_status_codes = cache_status_codes or [
            200,
            201,
            203,
            300,
            301,
            302,
            304,
            307,
            308,
        ]

        self.cache_paths = set(cache_paths or [])
        self.ignore_paths = set(ignore_paths or [])

        self.ignore_query_params = set(ignore_query_params or [])
        self.vary_headers = vary_headers or ["Authorization", "Accept-Language"]

        self.use_redis = use_redis
        self.redis_client = redis_client
        self.redis_prefix = redis_prefix


class MemoryCache:
    """Optimized in-memory LRU cache using OrderedDict."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, dict] = OrderedDict()

    def get(self, key: str) -> dict | None:
        """Get cached item with LRU update."""
        if key not in self.cache:
            return None

        item = self.cache[key]

        # Check if expired
        if time.time() > item["expires_at"]:
            del self.cache[key]
            return None

        # Move to end for LRU (O(1) operation in OrderedDict)
        self.cache.move_to_end(key)
        return item

    def set(self, key: str, data: dict, ttl: int) -> None:
        """Set cached item with TTL and LRU eviction."""
        # Update existing item
        if key in self.cache:
            del self.cache[key]

        # Evict oldest items if cache is full
        elif len(self.cache) >= self.max_size:
            # Remove oldest (first) item
            self.cache.popitem(last=False)

        self.cache[key] = {
            "content": data["content"],
            "media_type": data["media_type"],
            "headers": data["headers"],
            "status_code": data["status_code"],
            "expires_at": time.time() + ttl,
            "cached_at": time.time(),
        }

    def delete(self, key: str) -> None:
        """Delete cached item."""
        self.cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()


class ResponseCacheMiddleware:
    """Pure ASGI middleware for caching HTTP responses."""

    def __init__(self, app: ASGIApp, config: CacheConfig = None):
        self.app = app
        self.config = config or CacheConfig()

        # Initialize cache backend
        if self.config.use_redis and self.config.redis_client:
            self.cache = RedisCache(self.config.redis_client, self.config.redis_prefix)
        else:
            self.cache = MemoryCache(self.config.max_cache_size)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with response caching."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Only cache specific methods
        method = scope["method"]
        if method not in self.config.cache_methods:
            await self.app(scope, receive, send)
            return

        # Check if path should be cached
        path = scope["path"]
        if not self._should_cache_path(path):
            await self.app(scope, receive, send)
            return

        # Create request object for cache key generation
        request = Request(scope, receive)
        cache_key = self._generate_cache_key(request)

        # Try to get cached response
        cached = self.cache.get(cache_key)
        if cached:
            await self._send_cached_response(cached, send)
            return

        # Intercept response for caching
        response_started = False
        response_data = {
            "status_code": 200,
            "headers": [],
            "body": b"",
        }

        async def send_wrapper(message):
            nonlocal response_started, response_data

            if message["type"] == "http.response.start":
                response_started = True
                response_data["status_code"] = message["status"]
                response_data["headers"] = list(message.get("headers", []))

                # Add cache miss header
                response_data["headers"].append((b"x-cache", b"MISS"))
                message["headers"] = response_data["headers"]

            elif message["type"] == "http.response.body" and response_started:
                body_chunk = message.get("body", b"")
                response_data["body"] += body_chunk

                # If this is the last chunk, cache the response
                if not message.get("more_body", False):
                    if response_data["status_code"] in self.config.cache_status_codes:
                        await self._cache_response_asgi(cache_key, response_data)

            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _send_cached_response(self, cached: dict, send: Send) -> None:
        """Send a cached response via ASGI."""
        # Send response start
        headers = [(b"x-cache", b"HIT")]

        # Add cached headers but filter out any existing x-cache headers
        cached_headers = cached.get("headers", [])
        for header_name, header_value in cached_headers:
            if header_name.lower() != b"x-cache":
                headers.append((header_name, header_value))

        await send(
            {
                "type": "http.response.start",
                "status": cached["status_code"],
                "headers": headers,
            }
        )

        # Send response body
        await send(
            {
                "type": "http.response.body",
                "body": cached["content"],
                "more_body": False,
            }
        )

    async def _cache_response_asgi(self, cache_key: str, response_data: dict) -> None:
        """Cache response data from ASGI intercepted response."""
        cache_data = {
            "content": response_data["body"],
            "media_type": "application/json",  # Default, could be enhanced
            "headers": response_data["headers"],
            "status_code": response_data["status_code"],
        }

        self.cache.set(cache_key, cache_data, self.config.default_ttl)

    def _should_cache_path(self, path: str) -> bool:
        """Check if path should be cached."""
        # If specific cache paths are configured, only cache those
        if self.config.cache_paths:
            return any(
                path.startswith(cache_path) for cache_path in self.config.cache_paths
            )

        # Check ignore paths
        if self.config.ignore_paths:
            return not any(
                path.startswith(ignore_path) for ignore_path in self.config.ignore_paths
            )

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
            key_parts.append(msgspec.json.encode(query_params).decode())

        # Add vary headers
        for header in self.config.vary_headers:
            if header.lower() in request.headers:
                key_parts.append(f"{header}:{request.headers[header.lower()]}")

        # Create hash
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()


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
                return msgspec.json.decode(
                    data.encode() if isinstance(data, str) else data
                )
            return None
        except Exception:
            return None

    def set(self, key: str, data: dict, ttl: int) -> None:
        """Set cached item in Redis with TTL."""
        try:
            serialized = msgspec.json.encode(data).decode()
            self.redis.setex(f"{self.prefix}{key}", ttl, serialized)
        except Exception:
            pass  # Fail silently for cache errors

    def delete(self, key: str) -> None:
        """Delete cached item from Redis."""
        with contextlib.suppress(Exception):
            self.redis.delete(f"{self.prefix}{key}")

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
    **kwargs,
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
        **kwargs,
    )

    return ResponseCacheMiddleware(app=None, config=config)


def cache_control_headers(
    max_age_secs: int = 300, is_public: bool = True
) -> dict[str, str]:
    """Generate cache control headers for manual caching."""
    headers = {}

    if is_public:
        headers["Cache-Control"] = f"public, max-age={max_age_secs}"
    else:
        headers["Cache-Control"] = f"private, max-age={max_age_secs}"

    headers["ETag"] = f'"{int(time.time())}"'

    return headers
