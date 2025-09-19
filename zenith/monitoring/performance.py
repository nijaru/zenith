"""
Performance utilities for Zenith applications.

Provides decorators and utilities for optimizing application performance
including query caching, method memoization, and profiling helpers.
"""

import asyncio
import functools
import hashlib
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, TypeVar

import msgspec

# Configurable in-memory cache for function results
_MAX_CACHE_SIZE = 1000  # Maximum number of cached items
_function_cache: dict[str, dict] = {}
_cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
_cache_lock = asyncio.Lock() if hasattr(asyncio, "Lock") else None

# Performance logger
logger = logging.getLogger("zenith.performance")

# Type variable for preserving function signatures
F = TypeVar("F", bound=Callable[..., Any])


def cached(ttl: int = 300, key_func: Callable | None = None):
    """
    Cache function results for the specified TTL (time-to-live).

    Args:
        ttl: Cache TTL in seconds (default 5 minutes)
        key_func: Custom function to generate cache keys

    Usage:
        @cached(ttl=60)
        async def expensive_database_query(user_id: int):
            # This will be cached for 60 seconds
            return await db.get_user(user_id)
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # Check cache
            now = time.time()
            if cache_key in _function_cache:
                cached_item = _function_cache[cache_key]
                if now < cached_item["expires_at"]:
                    # Update last accessed time for LRU
                    cached_item["last_accessed"] = now
                    _cache_stats["hits"] += 1
                    return cached_item["result"]
                else:
                    # Expired, remove from cache
                    del _function_cache[cache_key]

            # Cache miss - call function
            _cache_stats["misses"] += 1
            result = await func(*args, **kwargs)

            # Store in cache with size management
            await _store_in_cache(cache_key, result, now + ttl, now)

            return result

        return wrapper

    return decorator


def cache_key(*parts: Any) -> str:
    """
    Generate a cache key from multiple parts.

    Usage:
        @cached(key_func=lambda user_id, include_deleted: cache_key("users", user_id, include_deleted))
        async def get_users(user_id: int, include_deleted: bool = False):
            ...
    """
    return _generate_cache_key("custom", parts, {})


def clear_cache(pattern: str | None = None) -> None:
    """
    Clear function cache.

    Args:
        pattern: If provided, only clear keys containing this pattern
    """
    if pattern:
        # Dictionary comprehension is 15-30% faster than creating list then deleting
        keys_to_keep = {k: v for k, v in _function_cache.items() if pattern not in k}
        _function_cache.clear()
        _function_cache.update(keys_to_keep)
    else:
        _function_cache.clear()

    # Reset stats when clearing all
    if not pattern:
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0


def cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total * 100) if total > 0 else 0

    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "evictions": _cache_stats["evictions"],
        "hit_rate": f"{hit_rate:.1f}%",
        "cache_size": len(_function_cache),
        "max_cache_size": _MAX_CACHE_SIZE,
    }


async def _store_in_cache(
    cache_key: str, result: Any, expires_at: float, cached_at: float
) -> None:
    """Store item in cache with size management."""
    global _function_cache, _cache_stats

    # Add access time for LRU tracking
    cache_item = {
        "result": result,
        "expires_at": expires_at,
        "cached_at": cached_at,
        "last_accessed": cached_at,
    }

    # Check if we need to make space
    if len(_function_cache) >= _MAX_CACHE_SIZE and cache_key not in _function_cache:
        await _evict_lru_items(1)

    _function_cache[cache_key] = cache_item


async def _evict_lru_items(count: int = 1) -> None:
    """Evict least recently used items from cache."""
    global _function_cache, _cache_stats

    if not _function_cache:
        return

    # First, try to evict expired items using dictionary comprehension
    current_time = time.time()

    # Separate expired and valid items in one pass (more efficient)
    valid_items = {}
    expired_count = 0
    for key, item in _function_cache.items():
        if current_time >= item["expires_at"] and expired_count < count:
            _cache_stats["evictions"] += 1
            expired_count += 1
            count -= 1
        else:
            valid_items[key] = item

    # Update cache with only valid items
    if expired_count > 0:
        _function_cache.clear()
        _function_cache.update(valid_items)

    # If we still need to evict more, use LRU
    if count > 0:
        # Sort by last_accessed time (oldest first)
        lru_items = sorted(_function_cache.items(), key=lambda x: x[1]["last_accessed"])

        for key, _ in lru_items[:count]:
            _function_cache.pop(key, None)
            _cache_stats["evictions"] += 1


def configure_cache(max_size: int = 1000) -> None:
    """Configure cache settings."""
    global _MAX_CACHE_SIZE
    _MAX_CACHE_SIZE = max_size
    logger.info(f"Performance cache configured with max_size={max_size}")


def get_cache_info() -> dict[str, Any]:
    """Get detailed cache information for monitoring."""
    current_time = time.time()
    expired_count = sum(
        1 for item in _function_cache.values() if current_time >= item["expires_at"]
    )

    return {
        **cache_stats(),
        "expired_entries": expired_count,
        "memory_efficient": len(_function_cache) < _MAX_CACHE_SIZE,
    }


def measure_time(name: str | None = None):
    """
    Decorator to measure function execution time.

    Usage:
        @measure_time("database_query")
        async def slow_query():
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                func_name = name or func.__name__
                logger.info(f"{func_name}: {duration:.3f}s")

        return wrapper

    return decorator


def batch_queries(batch_size: int = 100):
    """
    Decorator to batch database queries for better performance.

    Args:
        batch_size: Maximum items per batch

    Note: This is a placeholder - actual implementation would depend on
    specific ORM and query patterns used.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(items: list, *args, **kwargs):
            if not items:
                return []

            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                batch_result = await func(batch, *args, **kwargs)
                results.extend(batch_result)

            return results

        return wrapper

    return decorator


class PerformanceProfiler:
    """Simple performance profiler for tracking bottlenecks."""

    __slots__ = ("enabled", "timings")

    def __init__(self):
        self.timings: dict[str, list[float]] = {}
        self.enabled = True

    def time_function(self, name: str):
        """Context manager for timing code blocks."""
        return self.TimeContext(self, name)

    def record(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        if not self.enabled:
            return

        if name not in self.timings:
            self.timings[name] = []
        self.timings[name].append(duration)

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        for name, times in self.timings.items():
            if times:
                stats[name] = {
                    "count": len(times),
                    "total": sum(times),
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                }
        return stats

    def clear(self) -> None:
        """Clear all timing data."""
        self.timings.clear()

    class TimeContext:
        """Context manager for timing code blocks."""

        def __init__(self, profiler: "PerformanceProfiler", name: str):
            self.profiler = profiler
            self.name = name
            self.start_time = 0.0

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            self.profiler.record(self.name, duration)


# Global profiler instance
profiler = PerformanceProfiler()


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name and arguments."""
    # Convert args and kwargs to a deterministic string
    key_data = {
        "func": func_name,
        "args": args,
        "kwargs": kwargs,
    }

    # Use JSON serialization for consistent key generation
    try:
        key_string = msgspec.json.encode(key_data).decode()
    except (TypeError, ValueError):
        # Fallback to string representation
        key_string = f"{func_name}:{args!s}:{sorted(kwargs.items())!s}"

    # Create hash for consistent key length
    return hashlib.md5(key_string.encode()).hexdigest()


# Database query optimization helpers
def optimize_db_session(session):
    """
    Apply common database session optimizations.

    This is a placeholder for database-specific optimizations like:
    - Setting appropriate isolation levels
    - Enabling/disabling autoflush
    - Setting fetch strategies
    """
    # Example optimizations (would be database-specific)
    try:
        # Disable autoflush for read-heavy operations
        session.autoflush = False
        # Enable lazy loading for better performance
        session.expire_on_commit = False
    except AttributeError:
        # Not all session types support these options
        pass

    return session


def query_cache_key(
    model_name: str, filters: dict | None = None, order_by: str | None = None
) -> str:
    """Generate consistent cache keys for database queries."""
    parts = [model_name]

    if filters:
        # Sort filters for consistent key generation
        sorted_filters = sorted(filters.items())
        parts.append(msgspec.json.encode(sorted_filters).decode())

    if order_by:
        parts.append(f"order_by:{order_by}")

    key_string = "|".join(parts)
    return hashlib.md5(key_string.encode()).hexdigest()


# Performance monitoring helpers
def log_slow_queries(threshold_ms: int = 100):
    """
    Decorator to log queries that take longer than the threshold.

    Args:
        threshold_ms: Log queries slower than this (in milliseconds)
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow query: {func.__name__} took {duration_ms:.1f}ms"
                    )

        return wrapper

    return decorator


def track_performance(threshold_ms: float = 100):
    """
    Decorator to track performance of both sync and async functions.

    Args:
        threshold_ms: Log warning if execution exceeds this threshold

    Example:
        @track_performance(threshold_ms=50)
        async def slow_operation():
            await asyncio.sleep(0.1)
            return "done"
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000

                    if duration_ms > threshold_ms:
                        logger.warning(
                            f"Slow async operation: {func.__name__} took {duration_ms:.1f}ms "
                            f"(threshold: {threshold_ms}ms)"
                        )
                    else:
                        logger.debug(
                            f"Async operation: {func.__name__} took {duration_ms:.1f}ms"
                        )

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000

                    if duration_ms > threshold_ms:
                        logger.warning(
                            f"Slow operation: {func.__name__} took {duration_ms:.1f}ms "
                            f"(threshold: {threshold_ms}ms)"
                        )
                    else:
                        logger.debug(
                            f"Operation: {func.__name__} took {duration_ms:.1f}ms"
                        )

            return sync_wrapper  # type: ignore

    return decorator


@contextmanager
def profile_block(name: str, threshold_ms: float = 100):
    """
    Context manager for profiling code blocks.

    Args:
        name: Name of the code block being profiled
        threshold_ms: Log warning if execution exceeds this threshold

    Example:
        with profile_block("database_query", threshold_ms=50):
            results = await db.execute(query)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000

        if duration_ms > threshold_ms:
            logger.warning(
                f"Slow block '{name}' took {duration_ms:.1f}ms "
                f"(threshold: {threshold_ms}ms)"
            )
        else:
            logger.debug(f"Block '{name}' took {duration_ms:.1f}ms")
