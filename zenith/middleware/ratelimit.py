"""
Rate limiting middleware for Zenith applications.

Provides configurable rate limiting to protect APIs from abuse and
ensure fair usage across clients.
"""

import time
from typing import Callable, Dict, List, Optional, Tuple, Union
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class RateLimitStore:
    """Base class for rate limit storage backends."""
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> Tuple[bool, Dict[str, Union[int, float]]]:
        """
        Check if a request is allowed and return rate limit info.
        
        Returns:
            (is_allowed, info) where info contains:
            - limit: The rate limit
            - remaining: Requests remaining in window
            - reset: Unix timestamp when window resets
        """
        raise NotImplementedError


class MemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit store using sliding window."""
    
    def __init__(self):
        # Store request timestamps for each key
        self._requests: Dict[str, deque] = defaultdict(deque)
        # Store window info for each key  
        self._windows: Dict[str, Tuple[int, float]] = {}
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> Tuple[bool, Dict[str, Union[int, float]]]:
        """Check if request is allowed using sliding window algorithm."""
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Get or create request queue for this key
        requests = self._requests[key]
        
        # Remove old requests outside the window
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Check if we're within the limit
        current_count = len(requests)
        is_allowed = current_count < limit
        
        if is_allowed:
            # Add this request to the queue
            requests.append(current_time)
        
        # Calculate reset time (start of next window)
        reset_time = current_time + window_seconds
        
        return is_allowed, {
            "limit": limit,
            "remaining": max(0, limit - current_count - (1 if is_allowed else 0)),
            "reset": reset_time,
            "retry_after": window_seconds if not is_allowed else None
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with flexible configuration.
    
    Features:
    - Configurable rate limits per endpoint or globally
    - Multiple identification strategies (IP, user, API key)
    - Sliding window algorithm for accurate rate limiting
    - Proper HTTP headers (X-RateLimit-*, Retry-After)
    - Customizable error responses
    - Multiple storage backends (memory, Redis)
    
    Example:
        from zenith.middleware import RateLimitMiddleware
        
        app = Zenith(middleware=[
            RateLimitMiddleware(
                default_limit=100,
                window_seconds=3600,  # 100 requests per hour
                per_endpoint_limits={
                    "/api/auth/login": (5, 300),  # 5 per 5 minutes
                    "/api/upload": (10, 3600),    # 10 per hour
                }
            )
        ])
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 1000,
        window_seconds: int = 3600,
        per_endpoint_limits: Optional[Dict[str, Tuple[int, int]]] = None,
        identifier: Union[str, Callable[[Request], str]] = "ip",
        store: Optional[RateLimitStore] = None,
        skip_paths: Optional[List[str]] = None,
        skip_successful_requests: bool = False,
    ):
        super().__init__(app)
        
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.per_endpoint_limits = per_endpoint_limits or {}
        self.skip_paths = skip_paths or ["/health", "/metrics"]
        self.skip_successful_requests = skip_successful_requests
        
        # Set up identifier function
        if isinstance(identifier, str):
            self.identifier_func = self._get_identifier_func(identifier)
        else:
            self.identifier_func = identifier
        
        # Set up storage backend
        self.store = store or MemoryRateLimitStore()
    
    def _get_identifier_func(self, identifier_type: str) -> Callable[[Request], str]:
        """Get identifier function based on type."""
        
        if identifier_type == "ip":
            return lambda req: self._get_client_ip(req)
        elif identifier_type == "user":
            return lambda req: str(getattr(req.state, "user_id", "anonymous"))
        elif identifier_type == "api_key":
            return lambda req: req.headers.get("x-api-key", "unknown")
        else:
            raise ValueError(f"Unknown identifier type: {identifier_type}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxies."""
        
        # Check for forwarded headers (from reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (client IP)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_for_path(self, path: str) -> Tuple[int, int]:
        """Get rate limit configuration for a specific path."""
        
        # Check for exact path match
        if path in self.per_endpoint_limits:
            return self.per_endpoint_limits[path]
        
        # Check for pattern matches (simple prefix matching)
        for pattern, (limit, window) in self.per_endpoint_limits.items():
            if path.startswith(pattern):
                return limit, window
        
        # Return default
        return self.default_limit, self.window_seconds
    
    def _should_skip_path(self, path: str) -> bool:
        """Check if path should be skipped from rate limiting."""
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting to the request."""
        
        # Skip rate limiting for certain paths
        if self._should_skip_path(request.url.path):
            return await call_next(request)
        
        # Get client identifier
        client_id = self.identifier_func(request)
        
        # Get rate limit configuration for this path
        limit, window_seconds = self._get_rate_limit_for_path(request.url.path)
        
        # Create rate limit key
        rate_limit_key = f"{client_id}:{request.url.path}:{request.method}"
        
        # Check if request is allowed
        is_allowed, rate_info = await self.store.is_allowed(
            rate_limit_key, limit, window_seconds
        )
        
        # If rate limited, return 429 response
        if not is_allowed:
            return self._create_rate_limit_response(rate_info)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        self._add_rate_limit_headers(response, rate_info)
        
        return response
    
    def _create_rate_limit_response(self, rate_info: Dict) -> Response:
        """Create a 429 Too Many Requests response."""
        
        error_response = {
            "error": "RateLimitExceeded",
            "message": "Rate limit exceeded",
            "status_code": 429,
            "details": {
                "limit": rate_info["limit"],
                "window": "per hour",  # Could be made dynamic
                "retry_after": rate_info.get("retry_after")
            }
        }
        
        response = JSONResponse(
            content=error_response,
            status_code=429
        )
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, rate_info)
        
        # Add Retry-After header
        if rate_info.get("retry_after"):
            response.headers["retry-after"] = str(int(rate_info["retry_after"]))
        
        return response
    
    def _add_rate_limit_headers(self, response: Response, rate_info: Dict) -> None:
        """Add rate limit headers to response."""
        
        response.headers["x-ratelimit-limit"] = str(rate_info["limit"])
        response.headers["x-ratelimit-remaining"] = str(rate_info["remaining"])
        response.headers["x-ratelimit-reset"] = str(int(rate_info["reset"]))


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit store (requires redis package)."""
    
    def __init__(self, redis_client=None, key_prefix: str = "zenith:ratelimit"):
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis rate limiting requires 'redis' package. "
                "Install with: pip install redis"
            )
        
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.key_prefix = key_prefix
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> Tuple[bool, Dict[str, Union[int, float]]]:
        """Redis-based sliding window rate limiting."""
        
        redis_key = f"{self.key_prefix}:{key}"
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current requests
        pipe.zcard(redis_key)
        
        # Execute pipeline
        results = pipe.execute()
        current_count = results[1]
        
        # Check if allowed
        is_allowed = current_count < limit
        
        if is_allowed:
            # Add current request
            pipe = self.redis.pipeline()
            pipe.zadd(redis_key, {str(current_time): current_time})
            pipe.expire(redis_key, window_seconds)
            pipe.execute()
        
        reset_time = current_time + window_seconds
        
        return is_allowed, {
            "limit": limit,
            "remaining": max(0, limit - current_count - (1 if is_allowed else 0)),
            "reset": reset_time,
            "retry_after": window_seconds if not is_allowed else None
        }


def rate_limit_middleware(
    default_limit: int = 1000,
    window_seconds: int = 3600,
    per_endpoint_limits: Optional[Dict[str, Tuple[int, int]]] = None,
    identifier: Union[str, Callable[[Request], str]] = "ip",
    store: Optional[RateLimitStore] = None,
    skip_paths: Optional[List[str]] = None,
):
    """
    Helper function to create rate limiting middleware.
    
    Example:
        from zenith.middleware.ratelimit import rate_limit_middleware
        
        app = Zenith(middleware=[
            rate_limit_middleware(
                default_limit=1000,
                window_seconds=3600,
                per_endpoint_limits={
                    "/api/auth/login": (5, 300),  # 5 requests per 5 minutes
                }
            )
        ])
    """
    
    def create_middleware(app: ASGIApp):
        return RateLimitMiddleware(
            app=app,
            default_limit=default_limit,
            window_seconds=window_seconds,
            per_endpoint_limits=per_endpoint_limits,
            identifier=identifier,
            store=store,
            skip_paths=skip_paths,
        )
    
    return create_middleware