"""
High-level decorators for common web patterns.

Provides convenient decorators for caching, rate limiting, validation,
and other common patterns to reduce boilerplate.

NOTE: These decorators are currently simplified implementations for demonstration.
For production use, consider:
- Redis-backed caching with @cache decorator
- Redis-backed rate limiting with @rate_limit
- Proper distributed locking for cache invalidation
"""

import functools
import hashlib
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable, TypeVar

from zenith.exceptions import RateLimitException, ValidationException

T = TypeVar("T")

# Thread-safe cache with LRU eviction
_cache_lock = Lock()
_cache_store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
_MAX_CACHE_SIZE = 1000

# Thread-safe rate limiting
_rate_limit_lock = Lock()
_rate_limit_store: dict[str, list[float]] = {}


def cache(ttl: int = 60):
    """
    Cache endpoint responses for the specified time.

    Args:
        ttl: Time to live in seconds

    Example:
        @app.get("/expensive")
        @cache(ttl=300)  # Cache for 5 minutes
        async def expensive_operation():
            return compute_something()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key using SHA256 (more secure than MD5)
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_hash = hashlib.sha256(cache_key.encode()).hexdigest()

            # Thread-safe cache check
            with _cache_lock:
                if cache_hash in _cache_store:
                    cached_value, cached_time = _cache_store[cache_hash]
                    if time.time() - cached_time < ttl:
                        # Move to end for LRU
                        _cache_store.move_to_end(cache_hash)
                        return cached_value
                    else:
                        # Remove expired entry
                        del _cache_store[cache_hash]

            # Compute result outside of lock
            result = await func(*args, **kwargs)

            # Thread-safe cache update with LRU eviction
            with _cache_lock:
                _cache_store[cache_hash] = (result, time.time())
                _cache_store.move_to_end(cache_hash)

                # LRU eviction if cache is too large
                while len(_cache_store) > _MAX_CACHE_SIZE:
                    _cache_store.popitem(last=False)

            return result
        return wrapper
    return decorator


def rate_limit(limit: str):
    """
    Rate limit endpoint access.

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")

    Example:
        @app.post("/api/generate")
        @rate_limit("5/minute")
        async def generate():
            return {"result": "..."}
    """
    def decorator(func: Callable) -> Callable:
        # Parse rate limit
        count, period = limit.split("/")
        count = int(count)

        period_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }.get(period, 60)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get client identifier from request context if available
            # In production, this would use IP address or authenticated user ID
            from zenith.core.scoped import get_current_request
            request = get_current_request()

            if request and hasattr(request, 'client'):
                client_id = f"{func.__name__}:{request.client.host}"
            elif request and hasattr(request, 'user'):
                client_id = f"{func.__name__}:{request.user.id}"
            else:
                # Fallback for testing/development
                client_id = f"{func.__name__}:default"

            current_time = time.time()

            # Thread-safe rate limit check
            with _rate_limit_lock:
                if client_id in _rate_limit_store:
                    # Clean up old requests
                    requests = [
                        req_time for req_time in _rate_limit_store[client_id]
                        if current_time - req_time < period_seconds
                    ]

                    if len(requests) >= count:
                        # Calculate retry-after time
                        oldest_request = min(requests)
                        retry_after = int(period_seconds - (current_time - oldest_request))
                        raise RateLimitException(
                            f"Rate limit exceeded: {limit}. Try again in {retry_after} seconds."
                        )

                    requests.append(current_time)
                    _rate_limit_store[client_id] = requests
                else:
                    _rate_limit_store[client_id] = [current_time]

                # Clean up old clients periodically
                if len(_rate_limit_store) > 10000:
                    for key in list(_rate_limit_store.keys()):
                        requests = _rate_limit_store[key]
                        if all(current_time - req > period_seconds for req in requests):
                            del _rate_limit_store[key]

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate(request_model: type = None, response_model: type = None):
    """
    Validate request and response data.

    Args:
        request_model: Pydantic model for request validation
        response_model: Pydantic model for response validation

    Example:
        @app.post("/users")
        @validate(request_model=UserCreate, response_model=User)
        async def create_user(data: dict):
            return {"id": 1, **data}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Validate request if model provided
            if request_model:
                # In real implementation, would extract request data
                # This is simplified
                pass

            # Execute function
            result = await func(*args, **kwargs)

            # Validate response if model provided
            if response_model:
                # In real implementation, would validate response
                # This is simplified
                pass

            return result
        return wrapper
    return decorator


def paginate(default_limit: int = 20, max_limit: int = 100):
    """
    Add pagination to list endpoints.

    Args:
        default_limit: Default page size
        max_limit: Maximum allowed page size

    Example:
        @app.get("/users")
        @paginate()
        async def list_users(page: int = 1, limit: int = 20):
            return await User.paginate(page, limit)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, page: int = 1, limit: int = default_limit, **kwargs):
            # Enforce limits
            limit = min(limit, max_limit)
            limit = max(1, limit)
            page = max(1, page)

            # Calculate offset
            offset = (page - 1) * limit

            # Inject pagination params
            kwargs["_page"] = page
            kwargs["_limit"] = limit
            kwargs["_offset"] = offset

            result = await func(*args, page=page, limit=limit, **kwargs)

            # Wrap result with pagination metadata
            if isinstance(result, list):
                return {
                    "items": result,
                    "page": page,
                    "limit": limit,
                    "total": len(result),  # In real implementation, would get actual total
                }

            return result
        return wrapper
    return decorator


def returns(model: type):
    """
    Automatically handle response serialization and 404s.

    Args:
        model: Expected return type

    Example:
        @app.get("/users/{id}")
        @returns(User)
        async def get_user(id: int):
            return await User.get(id)  # Auto-404 if None
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Auto-404 if None
            if result is None:
                from zenith.exceptions import NotFoundException
                raise NotFoundException(f"{model.__name__} not found")

            # Auto-serialize if model instance
            if hasattr(result, "model_dump"):
                return result.model_dump()
            elif hasattr(result, "dict"):
                return result.dict()

            return result
        return wrapper
    return decorator


def auth_required(role: str = None, scopes: list[str] = None):
    """
    Require authentication with optional role/scope checking.

    Args:
        role: Required user role
        scopes: Required permission scopes

    Example:
        @app.post("/admin/users")
        @auth_required(role="admin")
        async def create_admin_user(user=CurrentUser):
            return {"admin": user}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # In real implementation, would check auth from request context
            # This is simplified

            # Check authentication
            user = kwargs.get("user") or kwargs.get("current_user")
            if not user:
                from zenith.exceptions import UnauthorizedException
                raise UnauthorizedException("Authentication required")

            # Check role if specified
            if role and getattr(user, "role", None) != role:
                from zenith.exceptions import ForbiddenException
                raise ForbiddenException(f"Role {role} required")

            # Check scopes if specified
            if scopes:
                user_scopes = getattr(user, "scopes", [])
                if not all(scope in user_scopes for scope in scopes):
                    from zenith.exceptions import ForbiddenException
                    raise ForbiddenException(f"Scopes {scopes} required")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def transaction(rollback_on: tuple[type[Exception]] = (Exception,)):
    """
    Wrap endpoint in a database transaction.

    Args:
        rollback_on: Exception types that trigger rollback

    Example:
        @app.post("/transfer")
        @transaction()
        async def transfer_funds(data: TransferRequest):
            await debit_account(data.from_account, data.amount)
            await credit_account(data.to_account, data.amount)
            return {"success": True}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # In real implementation, would get DB session from context
            # and wrap in transaction
            try:
                result = await func(*args, **kwargs)
                # Commit transaction
                return result
            except rollback_on as e:
                # Rollback transaction
                raise
        return wrapper
    return decorator


# Export convenience shortcuts
__all__ = [
    "cache",
    "rate_limit",
    "validate",
    "paginate",
    "returns",
    "auth_required",
    "transaction",
]