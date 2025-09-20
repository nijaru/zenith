"""
Service system for organizing business logic and domain operations.

Services provide a way to organize related functionality and maintain
clear boundaries between different areas of the application.
"""

import asyncio
from abc import ABC
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from zenith.core.container import DIContainer


class EventBus:
    """Simple event bus for service communication."""

    __slots__ = ("_async_listeners", "_listeners")

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}
        self._async_listeners: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to an event."""
        if asyncio.iscoroutinefunction(callback):
            if event not in self._async_listeners:
                self._async_listeners[event] = []
            self._async_listeners[event].append(callback)
        else:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        if asyncio.iscoroutinefunction(callback):
            if event in self._async_listeners:
                self._async_listeners[event].remove(callback)
        else:
            if event in self._listeners:
                self._listeners[event].remove(callback)

    async def emit(self, event: str, data: Any = None) -> None:
        """Emit an event to all subscribers."""
        # Call sync listeners
        if event in self._listeners:
            for callback in self._listeners[event]:
                callback(data)

        # Call async listeners
        if event in self._async_listeners:
            tasks = []
            for callback in self._async_listeners[event]:
                tasks.append(callback(data))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)


class Service(ABC):
    """Base class for business services."""

    __slots__ = ("_initialized", "container", "events")

    def __init__(self, container: DIContainer):
        self.container = container
        self.events: EventBus = container.get("events")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the service. Override for custom initialization."""
        if self._initialized:
            return
        self._initialized = True

    async def shutdown(self) -> None:
        """Cleanup service resources. Override for custom cleanup."""
        pass

    async def emit(self, event: str, data: Any = None) -> None:
        """Emit a domain event."""
        await self.events.emit(event, data)

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to a domain event."""
        self.events.subscribe(event, callback)

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions. Override in subclasses."""
        # Default implementation - no transaction support
        yield

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class ServiceRegistry:
    """Registry for managing application services."""

    __slots__ = ("_service_classes", "_services", "container")

    def __init__(self, container: DIContainer):
        self.container = container
        self._services: dict[str, Service] = {}
        self._service_classes: dict[str, type] = {}

    def register(self, name: str, service_class: type) -> None:
        """Register a service class."""
        self._service_classes[name] = service_class

    async def get(self, name: str) -> Service:
        """Get or create a service instance."""
        if name not in self._services:
            if name not in self._service_classes:
                raise KeyError(f"Service not registered: {name}")

            service_class = self._service_classes[name]
            service = service_class(self.container)
            await service.initialize()
            self._services[name] = service

        return self._services[name]

    async def get_by_type(self, service_type: type) -> Service:
        """Get a service by its type."""
        # Find the name for this service type
        for name, cls in self._service_classes.items():
            if cls == service_type:
                return await self.get(name)
        raise KeyError(f"Service type not registered: {service_type.__name__}")

    async def shutdown_all(self) -> None:
        """Shutdown all services."""
        for service in self._services.values():
            await service.shutdown()
        self._services.clear()

    def list_services(self) -> list[str]:
        """List all registered service names."""
        return list(self._service_classes.keys())
