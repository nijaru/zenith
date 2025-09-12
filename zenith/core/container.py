"""
Dependency injection container for service management.

Provides service registration, resolution, and lifecycle management.
"""

import asyncio
import inspect
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

T = TypeVar("T")


class DIContainer:
    """Dependency injection container with async support."""
    __slots__ = ('_services', '_singletons', '_factories', '_startup_hooks', '_shutdown_hooks')

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
        """Create instance with dependency injection."""
        sig = inspect.signature(factory)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependency = self.get(param.annotation)
                    kwargs[param_name] = dependency
                except KeyError:
                    if param.default == inspect.Parameter.empty:
                        raise KeyError(
                            f"Cannot resolve dependency: {param.annotation}"
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
        sync_hooks = [h for h in self._startup_hooks if not asyncio.iscoroutinefunction(h)]
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
        # Shutdown hooks should run in reverse order, but can parallelize async ones
        if self._shutdown_hooks:
            reversed_hooks = list(reversed(self._shutdown_hooks))
            sync_hooks = [h for h in reversed_hooks if not asyncio.iscoroutinefunction(h)]
            async_hooks = [h for h in reversed_hooks if asyncio.iscoroutinefunction(h)]
            
            # Run sync hooks first (they're usually faster)
            for hook in sync_hooks:
                hook()
                
            # Run async hooks in parallel
            if async_hooks:
                async with asyncio.TaskGroup() as tg:
                    for hook in async_hooks:
                        tg.create_task(hook())

        # Cleanup async services in parallel
        service_cleanup_tasks = []
        for service in self._services.values():
            if hasattr(service, "__aexit__"):
                service_cleanup_tasks.append(service.__aexit__(None, None, None))
            elif hasattr(service, "close") and asyncio.iscoroutinefunction(service.close):
                service_cleanup_tasks.append(service.close())
            elif hasattr(service, "close"):
                service.close()  # Sync close
                
        # Cleanup async services in parallel
        if service_cleanup_tasks:
            async with asyncio.TaskGroup() as tg:
                for cleanup_task in service_cleanup_tasks:
                    tg.create_task(cleanup_task)

    @asynccontextmanager
    async def lifespan(self):
        """Context manager for container lifecycle."""
        await self.startup()
        try:
            yield self
        finally:
            await self.shutdown()
