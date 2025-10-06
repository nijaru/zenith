"""
Request-scoped dependency injection for async resources.

Provides proper async context isolation for database sessions and other
resources that need to be created per-request.
"""

import asyncio
import inspect
from collections.abc import AsyncGenerator, Callable
from contextvars import ContextVar
from typing import Any, TypeVar

from starlette.requests import Request

T = TypeVar("T")

# Context variable to track current request
_current_request: ContextVar[Request | None] = ContextVar(
    "current_request", default=None
)


class RequestScoped:
    """
    Marks a dependency as request-scoped (similar to FastAPI's Depends).

    This ensures the dependency is created fresh for each request,
    avoiding async event loop binding issues common with database sessions.

    Example (FastAPI-style):
        @app.get("/users")
        async def get_users(db: AsyncSession = RequestScoped(get_db)):
            # db is created fresh for this request
            result = await db.execute(select(User))
            return result.scalars().all()

    This is equivalent to FastAPI's:
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """

    __slots__ = ("_cache_key", "dependency")

    def __init__(
        self,
        dependency: Callable[..., AsyncGenerator] | Callable[..., Any] | None = None,
    ):
        """
        Initialize a request-scoped dependency.

        Args:
            dependency: Async generator or callable that creates the dependency.
                       If None, will be inferred from type annotation.
        """
        self.dependency = dependency
        self._cache_key = f"_request_scoped_{id(dependency)}" if dependency else None

    async def get_or_create(self, request: Request) -> Any:
        """Get or create the dependency for this request."""
        if not self.dependency:
            raise ValueError("RequestScoped requires a dependency function")

        # Update cache key if needed
        if not self._cache_key:
            self._cache_key = f"_request_scoped_{id(self.dependency)}"

        # Check if already created for this request
        if hasattr(request.state, self._cache_key):
            return getattr(request.state, self._cache_key)

        # Create new instance for this request
        if asyncio.iscoroutinefunction(self.dependency):
            # Async factory
            instance = await self.dependency()
        elif inspect.isasyncgenfunction(self.dependency):
            # Async generator factory (FastAPI-style)
            gen = self.dependency()
            instance = await gen.__anext__()
            # Store generator for cleanup
            if not hasattr(request.state, "_async_generators"):
                request.state._async_generators = []
            request.state._async_generators.append(gen)
        else:
            # Sync factory
            instance = self.dependency()

        # Cache for this request
        setattr(request.state, self._cache_key, instance)
        return instance

    async def cleanup(self, request: Request) -> None:
        """Clean up resources after request."""
        import contextlib

        # Clean up async generators
        if hasattr(request.state, "_async_generators"):
            for gen in request.state._async_generators:
                with contextlib.suppress(Exception):
                    await gen.aclose()
            delattr(request.state, "_async_generators")

        # Remove cached instance
        if hasattr(request.state, self._cache_key):
            delattr(request.state, self._cache_key)


# DatabaseSession removed in favor of cleaner Session dependency
# Use: from zenith import Session
# Then: async def handler(session: AsyncSession = Session)


def get_current_request() -> Request | None:
    """Get the current request from context."""
    return _current_request.get()


def set_current_request(request: Request) -> None:
    """Set the current request in context."""
    _current_request.set(request)


def clear_current_request() -> None:
    """Clear the current request from context."""
    _current_request.set(None)


# Convenience function for creating request-scoped dependencies
def request_scoped(
    dependency: Callable[..., AsyncGenerator] | Callable[..., Any],
) -> RequestScoped:
    """
    Decorator to mark a dependency factory as request-scoped.

    Example:
        @request_scoped
        async def get_service():
            # This will be created fresh for each request
            return MyService()

        @app.get("/")
        async def handler(service: MyService = Inject(get_service)):
            return await service.do_something()
    """
    return RequestScoped(dependency)


# FastAPI-compatible alias
Depends = RequestScoped

__all__ = [
    "Depends",
    "RequestScoped",
    "clear_current_request",
    "get_current_request",
    "request_scoped",
    "set_current_request",
]
