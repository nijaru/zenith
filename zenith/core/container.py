"""
Dependency injection container for service management.

Provides service registration, resolution, and lifecycle management.
"""

import asyncio
import inspect
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, TypeVar, Union, get_args, get_origin

T = TypeVar("T")

# Context variable to store the current database session
try:
    from sqlalchemy.ext.asyncio import AsyncSession

    _current_db_session: ContextVar[AsyncSession | None] = ContextVar(
        "current_db_session", default=None
    )
    _HAS_SQLALCHEMY = True
except ImportError:
    _current_db_session = None
    _HAS_SQLALCHEMY = False

# Global registry for the default database instance
_default_database = None


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """
    Unwrap optional types like `SomeType | None` or `Optional[SomeType]`.

    Returns:
        Tuple of (unwrapped_type, is_optional)
    """
    # Handle None type
    if annotation is type(None):
        return annotation, False

    # Check if it's a Union type (typing.Union or types.UnionType from X | Y)
    origin = get_origin(annotation)

    # Handle both typing.Union and types.UnionType (Python 3.10+)
    if origin is Union or (
        hasattr(annotation, "__args__") and type(annotation).__name__ == "UnionType"
    ):
        # Get args - works for both Union[X, Y] and X | Y
        args = get_args(annotation)
        if not args:  # Fallback for UnionType
            args = getattr(annotation, "__args__", ())

        # Filter out NoneType
        non_none_args = [arg for arg in args if arg is not type(None)]

        if len(non_none_args) == 1:
            # Optional[X] or X | None
            return non_none_args[0], True
        elif len(non_none_args) > 1:
            # Union of multiple non-None types - return as is
            return annotation, False

    # Not an optional type
    return annotation, False


class DIContainer:
    """Dependency injection container with async support."""

    __slots__ = (
        "_factories",
        "_services",
        "_shutdown_hooks",
        "_singletons",
        "_startup_hooks",
    )

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._startup_hooks: list[Callable] = []
        self._shutdown_hooks: list[Callable] = []
        # Register the container itself for injection
        container_key = f"{DIContainer.__module__}.{DIContainer.__name__}"
        self._services[container_key] = self
        self._singletons[container_key] = True

    def register(
        self,
        service_type: type[T] | str,
        implementation: T | Callable[..., T] | None = None,
        singleton: bool = True,
    ) -> None:
        """Register a service with the container."""
        key = self._get_key(service_type)

        if implementation is None:
            # Auto-register the type itself
            implementation = service_type

        if inspect.isclass(implementation):
            # Store class for lazy instantiation
            self._factories[key] = implementation
        else:
            # Store instance directly
            self._services[key] = implementation

        if singleton:
            self._singletons[key] = True

    def get(self, service_type: type[T] | str) -> T:
        """Get a service instance from the container."""
        key = self._get_key(service_type)

        # Return existing instance if singleton
        if key in self._singletons and key in self._services:
            return self._services[key]

        # Create new instance from factory
        if key in self._factories:
            factory = self._factories[key]
            instance = self._create_instance(factory)

            # Store if singleton
            if key in self._singletons:
                self._services[key] = instance

            return instance

        # Return existing service
        if key in self._services:
            return self._services[key]

        raise KeyError(f"Service not registered: {key}")

    def _create_instance(self, factory: Callable) -> Any:
        """
        Create instance with dependency injection.

        Automatically resolves dependencies from type hints.
        For Service classes, creates instances recursively.
        """
        sig = inspect.signature(factory)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == "self":
                continue

            # Skip if no type annotation
            if param.annotation == inspect.Parameter.empty:
                # Use default value if available
                if param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                continue

            # Unwrap optional types (e.g., UserService | None -> UserService)
            actual_type, is_optional = _unwrap_optional(param.annotation)

            # If it's optional and has a default, skip resolution
            if is_optional and param.default != inspect.Parameter.empty:
                kwargs[param_name] = param.default
                continue

            # Try to resolve from container first
            try:
                dependency = self.get(actual_type)
                kwargs[param_name] = dependency
            except KeyError:
                # If not in container, check if it's a Service class
                try:
                    # Import Service here to avoid circular import
                    from zenith.core.service import Service

                    # Check if the annotation is a Service subclass
                    if inspect.isclass(actual_type) and issubclass(
                        actual_type, Service
                    ):
                        # Recursively create the Service with its dependencies
                        dependency = self._create_instance(actual_type)
                        kwargs[param_name] = dependency
                    elif param.default != inspect.Parameter.empty:
                        # Use default value
                        kwargs[param_name] = param.default
                    else:
                        # Cannot resolve - raise error
                        raise KeyError(
                            f"Cannot resolve dependency: {actual_type} for parameter '{param_name}'"
                        ) from None
                except (TypeError, AttributeError):
                    # Not a class or not a Service, use default if available
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        raise KeyError(
                            f"Cannot resolve dependency: {actual_type} for parameter '{param_name}'"
                        ) from None

        return factory(**kwargs)

    def _get_key(self, service_type: type | str) -> str:
        """Get string key for service type."""
        if isinstance(service_type, str):
            return service_type
        return f"{service_type.__module__}.{service_type.__name__}"

    def register_startup(self, hook: Callable) -> None:
        """Register startup hook."""
        self._startup_hooks.append(hook)

    def register_shutdown(self, hook: Callable) -> None:
        """Register shutdown hook."""
        self._shutdown_hooks.append(hook)

    async def startup(self) -> None:
        """Execute startup hooks with parallel async execution."""
        if not self._startup_hooks:
            return

        # Separate sync and async hooks for optimal execution
        sync_hooks = [
            h for h in self._startup_hooks if not asyncio.iscoroutinefunction(h)
        ]
        async_hooks = [h for h in self._startup_hooks if asyncio.iscoroutinefunction(h)]

        # Run sync hooks first (they're usually faster)
        for hook in sync_hooks:
            hook()

        # Run async hooks in parallel using TaskGroup
        if async_hooks:
            async with asyncio.TaskGroup() as tg:
                for hook in async_hooks:
                    tg.create_task(hook())

    async def shutdown(self) -> None:
        """Execute shutdown hooks and cleanup with parallel async execution."""
        import logging

        logger = logging.getLogger("zenith.container")

        # Shutdown hooks should run in reverse order, but can parallelize async ones
        if self._shutdown_hooks:
            reversed_hooks = list(reversed(self._shutdown_hooks))
            sync_hooks = [
                h for h in reversed_hooks if not asyncio.iscoroutinefunction(h)
            ]
            async_hooks = [h for h in reversed_hooks if asyncio.iscoroutinefunction(h)]

            # Run sync hooks first (they're usually faster)
            for hook in sync_hooks:
                try:
                    hook()
                except Exception as e:
                    logger.warning(f"Error in sync shutdown hook {hook.__name__}: {e}")

            # Run async hooks in parallel
            if async_hooks:
                try:
                    async with asyncio.TaskGroup() as tg:
                        for hook in async_hooks:
                            tg.create_task(hook())
                except ExceptionGroup as eg:
                    for exc in eg.exceptions:
                        logger.warning(f"Error in async shutdown hook: {exc}")

        # Cleanup async services in parallel
        service_cleanup_tasks = []
        for service in self._services.values():
            try:
                if hasattr(service, "__aexit__"):
                    service_cleanup_tasks.append(service.__aexit__(None, None, None))
                elif hasattr(service, "close") and asyncio.iscoroutinefunction(
                    service.close
                ):
                    service_cleanup_tasks.append(service.close())
                elif hasattr(service, "close"):
                    service.close()
            except Exception as e:
                logger.warning(
                    f"Error closing service {service.__class__.__name__}: {e}"
                )

        # Cleanup async services in parallel
        if service_cleanup_tasks:
            try:
                async with asyncio.TaskGroup() as tg:
                    for cleanup_task in service_cleanup_tasks:
                        tg.create_task(cleanup_task)
            except ExceptionGroup as eg:
                for exc in eg.exceptions:
                    logger.warning(f"Error in service cleanup: {exc}")

    @asynccontextmanager
    async def lifespan(self):
        """Context manager for container lifecycle."""
        await self.startup()
        try:
            yield self
        finally:
            await self.shutdown()


# Database session management functions
def set_current_db_session(session) -> None:
    """Set the current database session in the context."""
    if _HAS_SQLALCHEMY and _current_db_session:
        _current_db_session.set(session)


def get_current_db_session():
    """Get the current database session from the context."""
    if _HAS_SQLALCHEMY and _current_db_session:
        return _current_db_session.get()
    return None


async def get_db_session() -> "AsyncSession":
    """
    Get the current database session for use with ZenithModel.

    This function is used by ZenithModel to access the database session.
    It first tries to get the session from the context (set during web requests),
    and falls back to creating a new session if needed.

    Returns:
        AsyncSession: The database session to use

    Raises:
        RuntimeError: If no session is available and no database is configured
    """
    if not _HAS_SQLALCHEMY:
        raise RuntimeError(
            "SQLAlchemy not installed. Install with: uv add sqlalchemy[asyncio]"
        )

    session = get_current_db_session()
    if session is not None:
        return session

    try:
        db = _get_default_database()
        async with db.session() as new_session:
            return new_session
    except Exception as e:
        raise RuntimeError(
            f"No database session available in context and cannot create new session: {e}. "
            "Ensure you're using ZenithModel within a web request context, "
            "or manually set the database session with set_current_db_session()."
        ) from e


def _get_default_database():
    """
    Get the default database instance.

    This is a helper function to get the database when no session
    is available in the context. Applications must explicitly set
    the default database using set_default_database().
    """
    global _default_database

    if _default_database is not None:
        return _default_database

    raise RuntimeError(
        "No database session available. "
        "Ensure you're using ZenithModel within a web request context, "
        "or set the default database with set_default_database(app.database)."
    )


def set_default_database(database) -> None:
    """
    Set the default database instance.

    This should be called during application initialization to set
    the default database for models to use when no session is available
    in the context.

    Args:
        database: The Database instance to use as default
    """
    global _default_database
    _default_database = database


def clear_default_database() -> None:
    """Clear the default database instance."""
    global _default_database
    _default_database = None


async def create_database_session():
    """
    Create a new database session using the default database.

    This is a convenience function for creating sessions outside
    of the web request context.

    Returns:
        AsyncSession: A new database session

    Raises:
        RuntimeError: If no default database is configured
    """
    db = _get_default_database()
    return await db.session().__aenter__()
