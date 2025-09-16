"""
Enhanced dependency injection patterns for better developer experience.

Provides convenient shortcuts for common dependencies like database sessions,
authentication, caching, and other services.
"""

from __future__ import annotations

from typing import Annotated, Any, AsyncGenerator, Callable, TypeVar
from collections.abc import Awaitable

try:
    from fastapi import Depends
except ImportError:
    # FastAPI not available, create a dummy Depends for type compatibility
    class Depends:
        def __init__(self, dependency: Callable[..., Any]):
            self.dependency = dependency
from sqlalchemy.ext.asyncio import AsyncSession

from .container import get_db_session, set_current_db_session

__all__ = ["DB", "Auth", "Cache", "Inject", "Service", "Request"]

T = TypeVar("T")


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency for FastAPI routes.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = DB):
            users = await User.all()
            return users
    """
    session = await get_db_session()
    set_current_db_session(session)
    try:
        yield session
    finally:
        set_current_db_session(None)


async def get_auth_user() -> Any:
    """
    Get authenticated user dependency.

    This is a placeholder that will be properly implemented
    when the auth system is integrated.
    """
    # TODO: Implement actual authentication
    # For now, return a mock user to avoid breaking the interface
    return {"id": 1, "name": "Mock User", "email": "mock@example.com"}


async def get_cache_client() -> Any:
    """
    Get cache client dependency.

    This will be properly implemented when caching is added.
    """
    # TODO: Implement actual cache client
    return {}


async def get_current_request() -> Any:
    """
    Get current HTTP request object.

    This will be properly implemented with request context.
    """
    # TODO: Implement request context
    return {}


# Convenient dependency shortcuts (Rails-like simplicity)
# These can be used directly in route parameters

# Database session shortcut
DB = Depends(get_database_session)

# Authentication shortcuts
Auth = Depends(get_auth_user)

# Cache client shortcut
Cache = Depends(get_cache_client)

# Request object shortcut
Request = Depends(get_current_request)


def Inject(service_type: type[T] | None = None) -> Any:
    """
    Enhanced dependency injection for services.

    Works similar to FastAPI's Depends but with automatic service resolution.

    Usage:
        @app.get("/posts")
        async def get_posts(
            posts_service: PostService = Inject(),
            user: User = Auth,
            db: AsyncSession = DB
        ):
            return await posts_service.get_recent_posts()

    For explicit service types:
        @app.get("/posts")
        async def get_posts(posts: PostService = Inject(PostService)):
            return await posts.get_recent_posts()
    """
    if service_type is None:
        # Auto-resolve from type annotation
        def auto_resolve_service():
            # This will be resolved by FastAPI based on the parameter type annotation
            # The actual service resolution will be handled by the DI container
            pass

        return Depends(auto_resolve_service)
    else:
        # Explicit service type
        def resolve_service() -> service_type:
            # TODO: Integrate with DI container to resolve services
            # For now, return a basic implementation
            return service_type()

        return Depends(resolve_service)


def Service(
    singleton: bool = True,
    lifecycle: str = "application"
) -> Callable:
    """
    Decorator to mark a class as a service for dependency injection.

    Usage:
        @Service()
        class UserService:
            def __init__(self, db: AsyncSession = DB):
                self.db = db

            async def get_users(self):
                return await User.all()

        # Then inject into routes:
        @app.get("/users")
        async def get_users(service: UserService = Inject()):
            return await service.get_users()

    Args:
        singleton: Whether to create a single instance (default: True)
        lifecycle: Service lifecycle - "application", "request", or "transient"
    """
    def decorator(cls: type[T]) -> type[T]:
        # Add service metadata
        cls._zenith_service = True
        cls._zenith_singleton = singleton
        cls._zenith_lifecycle = lifecycle

        # TODO: Register with DI container
        # This will be implemented when we integrate with the container system

        return cls

    return decorator


# Type aliases for better documentation
DatabaseSession = Annotated[AsyncSession, DB]
AuthenticatedUser = Annotated[Any, Auth]
CacheClient = Annotated[Any, Cache]
HttpRequest = Annotated[Any, Request]


# Convenience functions for manual dependency resolution
async def resolve_db() -> AsyncSession:
    """Manually resolve database session outside of FastAPI context."""
    return await get_db_session()


async def resolve_auth() -> Any:
    """Manually resolve authenticated user outside of FastAPI context."""
    return await get_auth_user()


def resolve_cache() -> Any:
    """Manually resolve cache client outside of FastAPI context."""
    # Cache is typically synchronous
    return {}


# Context managers for manual session management
class DatabaseContext:
    """Context manager for database operations outside web requests."""

    def __init__(self):
        self.session = None

    async def __aenter__(self) -> AsyncSession:
        self.session = await resolve_db()
        set_current_db_session(self.session)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        set_current_db_session(None)
        if self.session:
            await self.session.close()


class ServiceContext:
    """Context manager for service operations outside web requests."""

    def __init__(self, *services: type):
        self.services = services
        self.instances = {}

    async def __aenter__(self):
        # Initialize services
        for service_type in self.services:
            # TODO: Proper service resolution
            self.instances[service_type] = service_type()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup services if needed
        pass

    def get(self, service_type: type[T]) -> T:
        """Get a service instance."""
        return self.instances.get(service_type)