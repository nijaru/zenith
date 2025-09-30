"""
Rate limiting middleware for Zenith applications.

Provides configurable request rate limiting with support for:
- Per-IP rate limiting
- Per-user rate limiting
- Custom rate limits per endpoint
- Multiple time windows (per minute, per hour, per day)
- Redis-backed storage for distributed systems
- In-memory storage for single-instance deployments
"""

import asyncio
import logging
import time
from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("zenith.middleware.rate_limit")


@dataclass(slots=True)
class RateLimit:
    """Rate limit configuration."""

    requests: int  # Number of requests allowed
    window: int  # Time window in seconds
    per: str = "ip"  # Rate limit per: 'ip', 'user', 'endpoint'


class RateLimitStorage:
    """Base class for rate limit storage backends."""

    async def get_count(self, key: str) -> int:
        """Get current request count for key."""
        raise NotImplementedError

    async def increment(self, key: str, window: int) -> int:
        """Increment request count and return new count."""
        raise NotImplementedError

    async def reset(self, key: str) -> None:
        """Reset request count for key."""
        raise NotImplementedError


class MemoryRateLimitStorage(RateLimitStorage):
    """In-memory rate limit storage with automatic cleanup."""

    __slots__ = (
        "_cleanup_interval",
        "_cleanup_task",
        "_lock",
        "_max_entries",
        "_storage",
    )

    def __init__(self, cleanup_interval: int = 300, max_entries: int = 10000):
        self._storage: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval  # 5 minutes
        self._max_entries = max_entries
        self._cleanup_task: asyncio.Task | None = None
        self._start_cleanup()

    async def get_count(self, key: str) -> int:
        """Get current request count for key."""
        async with self._lock:
            if key not in self._storage:
                return 0

            count, expires_at = self._storage[key]
            if time.time() > expires_at:
                del self._storage[key]
                return 0

            return count

    async def increment(self, key: str, window: int) -> int:
        """Increment request count and return new count."""
        async with self._lock:
            current_time = time.time()
            expires_at = current_time + window

            if key not in self._storage:
                # Perform size-based cleanup if needed (before adding new entry)
                if len(self._storage) >= self._max_entries:
                    await self._cleanup_expired()
                    # If still at max capacity after removing expired, remove oldest
                    if len(self._storage) >= self._max_entries:
                        # Remove oldest entry (by expiration time)
                        oldest_key = min(
                            self._storage.keys(), key=lambda k: self._storage[k][1]
                        )
                        self._storage.pop(oldest_key, None)

                self._storage[key] = (1, expires_at)
                return 1

            count, old_expires_at = self._storage[key]

            # Reset if window expired
            if current_time > old_expires_at:
                self._storage[key] = (1, expires_at)
                return 1

            # Increment within window
            new_count = count + 1
            self._storage[key] = (new_count, old_expires_at)
            return new_count

    async def reset(self, key: str) -> None:
        """Reset request count for key."""
        async with self._lock:
            self._storage.pop(key, None)

    def _start_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired entries."""
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                async with self._lock:
                    await self._cleanup_expired()
        except asyncio.CancelledError:
            logger.debug("Rate limit cleanup task cancelled")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from storage."""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, expires_at) in self._storage.items()
            if current_time > expires_at
        ]
        for key in expired_keys:
            self._storage.pop(key, None)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")

    def stop_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

    def get_storage_stats(self) -> dict:
        """Get storage statistics for monitoring."""
        return {
            "total_entries": len(self._storage),
            "max_entries": self._max_entries,
            "cleanup_interval": self._cleanup_interval,
            "cleanup_task_running": self._cleanup_task is not None
            and not self._cleanup_task.done(),
        }


class RedisRateLimitStorage(RateLimitStorage):
    """Redis-backed rate limit storage."""

    def __init__(self, redis_client, key_prefix: str = "rate_limit:"):
        self.redis = redis_client
        self.key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    async def get_count(self, key: str) -> int:
        """Get current request count for key."""
        redis_key = self._make_key(key)
        count = await self.redis.get(redis_key)
        return int(count) if count else 0

    async def increment(self, key: str, window: int) -> int:
        """Increment request count and return new count."""
        redis_key = self._make_key(key)

        # Use Redis pipeline for atomic operations
        async with self.redis.pipeline() as pipe:
            await pipe.incr(redis_key)
            await pipe.expire(redis_key, window)
            results = await pipe.execute()

            return int(results[0])

    async def reset(self, key: str) -> None:
        """Reset request count for key."""
        redis_key = self._make_key(key)
        await self.redis.delete(redis_key)


class RateLimitConfig:
    """Configuration for rate limiting middleware."""

    def __init__(
        self,
        default_limits: list[RateLimit] | None = None,
        storage: RateLimitStorage | None = None,
        exempt_paths: list[str] | None = None,
        exempt_ips: list[str] | None = None,
        error_message: str = "Rate limit exceeded",
        include_headers: bool = True,
    ):
        self.default_limits = default_limits or [
            RateLimit(requests=1000, window=3600, per="ip"),  # 1000/hour
            RateLimit(requests=100, window=60, per="ip"),  # 100/minute
        ]
        self.storage = storage or MemoryRateLimitStorage()
        self.exempt_paths = exempt_paths if exempt_paths is not None else []
        self.exempt_ips = exempt_ips if exempt_ips is not None else []
        self.error_message = error_message
        self.include_headers = include_headers


class RateLimitMiddleware:
    """
    Rate limiting middleware with configurable limits and storage backends.

    Features:
    - Multiple rate limits per application
    - Per-IP, per-user, or per-endpoint limiting
    - Configurable time windows
    - Custom error responses
    - Exempt paths and IP addresses
    - Redis or memory storage
    """

    def __init__(
        self,
        app: ASGIApp,
        config: RateLimitConfig | None = None,
        # Individual parameters (for backward compatibility)
        *,
        default_limits: list[RateLimit] | None = None,
        storage: RateLimitStorage | None = None,
        exempt_paths: list[str] | None = None,
        exempt_ips: list[str] | None = None,
        error_message: str = "Rate limit exceeded",
        include_headers: bool = True,
    ):
        self.app = app

        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.default_limits = config.default_limits
            self.storage = config.storage
            self.exempt_paths = set(config.exempt_paths)
            self.exempt_ips = set(config.exempt_ips)
            self.error_message = config.error_message
            self.include_headers = config.include_headers
        else:
            # Use individual parameters with defaults
            self.default_limits = default_limits or [
                RateLimit(requests=1000, window=3600, per="ip"),  # 1000/hour
                RateLimit(requests=100, window=60, per="ip"),  # 100/minute
            ]
            self.storage = storage or MemoryRateLimitStorage()
            self.exempt_paths = set(exempt_paths) if exempt_paths is not None else set()
            self.exempt_ips = set(exempt_ips) if exempt_ips is not None else set()
            self.error_message = error_message
            self.include_headers = include_headers

        # Per-endpoint limits
        self.endpoint_limits: dict[str, list[RateLimit]] = {}

        logger.info(
            f"Rate limiting enabled with {len(self.default_limits)} default limits"
        )

    def add_endpoint_limit(self, path: str, limits: list[RateLimit]) -> None:
        """Add custom rate limits for specific endpoint."""
        self.endpoint_limits[path] = limits
        logger.info(f"Added custom rate limits for {path}: {limits}")

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header first (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to client host
        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> str | None:
        """Extract user ID from request (if authenticated)."""
        # Try to get user from request state (set by auth middleware)
        user = None
        if hasattr(request.state, "user"):
            user = request.state.user
        elif hasattr(request.state, "current_user"):
            user = request.state.current_user

        if user:
            return str(user.get("id") or user.get("user_id", ""))

        # Try to extract from JWT token in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from zenith.auth import extract_user_from_token

                token = auth_header.split(" ", 1)[1]
                user = extract_user_from_token(token)
                if user:
                    return str(user["id"])
            except Exception:
                pass

        return None

    def _get_rate_limit_key(
        self,
        request: Request,
        rate_limit: RateLimit,
        is_endpoint_specific: bool = False,
    ) -> str:
        """Generate rate limit key based on limit type."""
        path = request.url.path

        if rate_limit.per == "ip":
            client_ip = self._get_client_ip(request)
            # Include path in key for endpoint-specific limits
            if is_endpoint_specific:
                return f"ip:{client_ip}:{path}:{rate_limit.window}"
            return f"ip:{client_ip}:{rate_limit.window}"

        elif rate_limit.per == "user":
            user_id = self._get_user_id(request)
            if not user_id:
                # Fall back to IP if no user
                client_ip = self._get_client_ip(request)
                if is_endpoint_specific:
                    return f"ip:{client_ip}:{path}:{rate_limit.window}"
                return f"ip:{client_ip}:{rate_limit.window}"
            # Include path in key for endpoint-specific limits
            if is_endpoint_specific:
                return f"user:{user_id}:{path}:{rate_limit.window}"
            return f"user:{user_id}:{rate_limit.window}"

        elif rate_limit.per == "endpoint":
            client_ip = self._get_client_ip(request)
            return f"endpoint:{path}:{client_ip}:{rate_limit.window}"

        else:
            raise ValueError(f"Unknown rate limit type: {rate_limit.per}")

    def _should_exempt(self, request: Request) -> bool:
        """Check if request should be exempted from rate limiting."""
        # Check exempt paths
        path = request.url.path
        if path in self.exempt_paths:
            return True

        # Check exempt IPs
        client_ip = self._get_client_ip(request)
        return client_ip in self.exempt_ips

    def _get_applicable_limits(self, request: Request) -> list[RateLimit]:
        """Get rate limits applicable to this request."""
        path = request.url.path

        # Check for endpoint-specific limits
        for endpoint_path, limits in self.endpoint_limits.items():
            if path.startswith(endpoint_path):
                return limits

        # Use default limits
        return self.default_limits

    async def _check_rate_limits(
        self, request: Request, limits: list[RateLimit]
    ) -> tuple[bool, RateLimit | None, int, int]:
        """
        Check all applicable rate limits.

        Returns:
            (allowed, violated_limit, current_count, limit_count)
        """
        # Check if this is an endpoint-specific limit
        path = request.url.path
        is_endpoint_specific = any(
            path.startswith(endpoint_path) for endpoint_path in self.endpoint_limits
        )

        for rate_limit in limits:
            key = self._get_rate_limit_key(request, rate_limit, is_endpoint_specific)
            current_count = await self.storage.increment(key, rate_limit.window)

            if current_count > rate_limit.requests:
                return False, rate_limit, current_count, rate_limit.requests

        return True, None, 0, 0

    def _create_error_response(
        self,
        rate_limit: RateLimit,
        current_count: int,
        limit_count: int,
        request: Request,
    ) -> Response:
        """Create rate limit exceeded response."""
        headers = {}

        if self.include_headers:
            headers.update(
                {
                    "X-RateLimit-Limit": str(rate_limit.requests),
                    "X-RateLimit-Window": str(rate_limit.window),
                    "X-RateLimit-Remaining": str(
                        max(0, rate_limit.requests - current_count)
                    ),
                    "Retry-After": str(rate_limit.window),
                }
            )

        return JSONResponse(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": self.error_message,
                "limit": rate_limit.requests,
                "window": rate_limit.window,
                "current": current_count,
            },
            headers=headers,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip rate limiting for exempt requests
        if self._should_exempt_asgi(scope):
            await self.app(scope, receive, send)
            return

        # Get applicable rate limits
        limits = self._get_applicable_limits_asgi(scope)

        # Check rate limits
        (
            allowed,
            violated_limit,
            current_count,
            limit_count,
        ) = await self._check_rate_limits_asgi(scope, limits)

        if not allowed:
            client_ip = self._get_client_ip_asgi(scope)
            path = scope.get("path", "")
            logger.warning(
                f"Rate limit exceeded for {client_ip} "
                f"on {path}: {current_count}/{limit_count}"
            )
            error_response = self._create_error_response_asgi(
                violated_limit, current_count, limit_count, scope
            )
            await error_response(scope, receive, send)
            return

        # Wrap send to add rate limit headers to successful responses
        async def send_wrapper(message):
            if (
                message["type"] == "http.response.start"
                and self.include_headers
                and limits
            ):
                # Check if this is an endpoint-specific limit
                path = scope.get("path", "")
                is_endpoint_specific = any(
                    path.startswith(endpoint_path)
                    for endpoint_path in self.endpoint_limits
                )
                # Use the most restrictive limit for headers
                most_restrictive = min(
                    limits, key=lambda limit: limit.requests / limit.window
                )
                key = self._get_rate_limit_key_asgi(
                    scope, most_restrictive, is_endpoint_specific
                )
                current = await self.storage.get_count(key)

                response_headers = list(message.get("headers", []))
                response_headers.extend(
                    [
                        (
                            b"x-ratelimit-limit",
                            str(most_restrictive.requests).encode("latin-1"),
                        ),
                        (
                            b"x-ratelimit-window",
                            str(most_restrictive.window).encode("latin-1"),
                        ),
                        (
                            b"x-ratelimit-remaining",
                            str(max(0, most_restrictive.requests - current)).encode(
                                "latin-1"
                            ),
                        ),
                    ]
                )
                message["headers"] = response_headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

    # ASGI-specific helper methods
    def _get_client_ip_asgi(self, scope: Scope) -> str:
        """Extract client IP address from ASGI scope."""
        headers = dict(scope.get("headers", []))

        # Check X-Forwarded-For header first (for proxies)
        forwarded_for_bytes = headers.get(b"x-forwarded-for")
        if forwarded_for_bytes:
            forwarded_for = forwarded_for_bytes.decode("latin-1")
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip_bytes = headers.get(b"x-real-ip")
        if real_ip_bytes:
            return real_ip_bytes.decode("latin-1").strip()

        # Fall back to client host from scope
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _get_user_id_asgi(self, scope: Scope) -> str | None:
        """Extract user ID from ASGI scope (if authenticated)."""
        # Try to get user from scope state (set by auth middleware)
        state = scope.get("state")
        if not state:
            return None

        user = None

        # Handle both dictionary and object-based state
        if isinstance(state, dict):
            # State is a dictionary (common case)
            user = state.get("current_user") or state.get("user")
        else:
            # State is an object with attributes
            user = getattr(state, "current_user", None) or getattr(state, "user", None)

        if user:
            return str(user.get("id") or user.get("user_id", ""))

        # Try to extract from JWT token in Authorization header
        headers = dict(scope.get("headers", []))
        auth_header_bytes = headers.get(b"authorization")
        if auth_header_bytes:
            auth_header = auth_header_bytes.decode("latin-1")
            if auth_header.startswith("Bearer "):
                try:
                    from zenith.auth import extract_user_from_token

                    token = auth_header.split(" ", 1)[1]
                    user = extract_user_from_token(token)
                    if user:
                        return str(user["id"])
                except Exception:
                    pass

        return None

    def _get_rate_limit_key_asgi(
        self, scope: Scope, rate_limit: RateLimit, is_endpoint_specific: bool = False
    ) -> str:
        """Generate rate limit key based on limit type for ASGI requests."""
        path = scope.get("path", "")

        if rate_limit.per == "ip":
            client_ip = self._get_client_ip_asgi(scope)
            # Include path in key for endpoint-specific limits
            if is_endpoint_specific:
                return f"ip:{client_ip}:{path}:{rate_limit.window}"
            return f"ip:{client_ip}:{rate_limit.window}"

        elif rate_limit.per == "user":
            user_id = self._get_user_id_asgi(scope)
            if not user_id:
                # Fall back to IP if no user
                client_ip = self._get_client_ip_asgi(scope)
                if is_endpoint_specific:
                    return f"ip:{client_ip}:{path}:{rate_limit.window}"
                return f"ip:{client_ip}:{rate_limit.window}"
            # Include path in key for endpoint-specific limits
            if is_endpoint_specific:
                return f"user:{user_id}:{path}:{rate_limit.window}"
            return f"user:{user_id}:{rate_limit.window}"

        elif rate_limit.per == "endpoint":
            client_ip = self._get_client_ip_asgi(scope)
            return f"endpoint:{path}:{client_ip}:{rate_limit.window}"

        else:
            raise ValueError(f"Unknown rate limit type: {rate_limit.per}")

    def _should_exempt_asgi(self, scope: Scope) -> bool:
        """Check if ASGI request should be exempted from rate limiting."""
        # Check exempt paths
        path = scope.get("path", "")
        if path in self.exempt_paths:
            return True

        # Check exempt IPs
        client_ip = self._get_client_ip_asgi(scope)
        return client_ip in self.exempt_ips

    def _get_applicable_limits_asgi(self, scope: Scope) -> list[RateLimit]:
        """Get rate limits applicable to this ASGI request."""
        path = scope.get("path", "")

        # Check for endpoint-specific limits
        for endpoint_path, limits in self.endpoint_limits.items():
            if path.startswith(endpoint_path):
                return limits

        # Use default limits
        return self.default_limits

    async def _check_rate_limits_asgi(
        self, scope: Scope, limits: list[RateLimit]
    ) -> tuple[bool, RateLimit | None, int, int]:
        """
        Check all applicable rate limits for ASGI requests.

        Returns:
            (allowed, violated_limit, current_count, limit_count)
        """
        # Check if this is an endpoint-specific limit
        path = scope.get("path", "")
        is_endpoint_specific = any(
            path.startswith(endpoint_path) for endpoint_path in self.endpoint_limits
        )

        for rate_limit in limits:
            key = self._get_rate_limit_key_asgi(scope, rate_limit, is_endpoint_specific)
            current_count = await self.storage.increment(key, rate_limit.window)

            if current_count > rate_limit.requests:
                return False, rate_limit, current_count, rate_limit.requests

        return True, None, 0, 0

    def _create_error_response_asgi(
        self, rate_limit: RateLimit, current_count: int, limit_count: int, scope: Scope
    ) -> Response:
        """Create rate limit exceeded response for ASGI requests."""
        headers = {}

        if self.include_headers:
            headers.update(
                {
                    "X-RateLimit-Limit": str(rate_limit.requests),
                    "X-RateLimit-Window": str(rate_limit.window),
                    "X-RateLimit-Remaining": str(
                        max(0, rate_limit.requests - current_count)
                    ),
                    "Retry-After": str(rate_limit.window),
                }
            )

        return JSONResponse(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": self.error_message,
                "limit": rate_limit.requests,
                "window": rate_limit.window,
                "current": current_count,
            },
            headers=headers,
        )


# Convenience functions for easy setup
def create_rate_limiter(
    requests_per_minute: int = 100,
    requests_per_hour: int = 1000,
    storage: RateLimitStorage | None = None,
    **kwargs,
) -> RateLimitMiddleware:
    """
    Create a rate limiter middleware with common defaults.

    Args:
        requests_per_minute: Maximum requests per minute per IP address
        requests_per_hour: Maximum requests per hour per IP address
        storage: Storage backend for rate limit data (defaults to memory)
        **kwargs: Additional arguments passed to RateLimitMiddleware

    Returns:
        Configured RateLimitMiddleware instance
    """
    limits = [
        RateLimit(requests=requests_per_minute, window=60, per="ip"),
        RateLimit(requests=requests_per_hour, window=3600, per="ip"),
    ]

    return RateLimitMiddleware(
        app=None,  # Will be set by Zenith
        default_limits=limits,
        storage=storage,
        **kwargs,
    )


def create_redis_rate_limiter(
    redis_client,
    requests_per_minute: int = 100,
    requests_per_hour: int = 1000,
    **kwargs,
) -> RateLimitMiddleware:
    """
    Create a Redis-backed rate limiter middleware.

    Args:
        redis_client: Redis client instance for persistent storage
        requests_per_minute: Maximum requests per minute per IP address
        requests_per_hour: Maximum requests per hour per IP address
        **kwargs: Additional arguments passed to RateLimitMiddleware

    Returns:
        Configured RateLimitMiddleware instance with Redis storage
    """
    storage = RedisRateLimitStorage(redis_client)
    return create_rate_limiter(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        storage=storage,
        **kwargs,
    )
