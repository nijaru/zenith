"""
Context system for organizing business logic and domain operations.

Contexts provide a way to organize related functionality and maintain
clear boundaries between different areas of the application.
"""

import asyncio
from abc import ABC
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from zenith.core.container import DIContainer


class EventBus:
    """Simple event bus for context communication."""
    __slots__ = ('_listeners', '_async_listeners')

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


class Context(ABC):
    """Base class for business contexts."""
    __slots__ = ('container', 'events', '_initialized')

    def __init__(self, container: DIContainer):
        self.container = container
        self.events: EventBus = container.get("events")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the context. Override for custom initialization."""
        if self._initialized:
            return
        self._initialized = True

    async def shutdown(self) -> None:
        """Cleanup context resources. Override for custom cleanup."""
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


class ContextRegistry:
    """Registry for managing application contexts."""
    __slots__ = ('container', '_contexts', '_context_classes')

    def __init__(self, container: DIContainer):
        self.container = container
        self._contexts: dict[str, Context] = {}
        self._context_classes: dict[str, type] = {}

    def register(self, name: str, context_class: type) -> None:
        """Register a context class."""
        self._context_classes[name] = context_class

    async def get(self, name: str) -> Context:
        """Get or create a context instance."""
        if name not in self._contexts:
            if name not in self._context_classes:
                raise KeyError(f"Context not registered: {name}")

            context_class = self._context_classes[name]
            context = context_class(self.container)
            await context.initialize()
            self._contexts[name] = context

        return self._contexts[name]

    async def get_by_type(self, context_type: type) -> Context:
        """Get a context by its type."""
        # Find the name for this context type
        for name, cls in self._context_classes.items():
            if cls == context_type:
                return await self.get(name)
        raise KeyError(f"Context type not registered: {context_type.__name__}")

    async def shutdown_all(self) -> None:
        """Shutdown all contexts."""
        for context in self._contexts.values():
            await context.shutdown()
        self._contexts.clear()

    def list_contexts(self) -> list[str]:
        """List all registered context names."""
        return list(self._context_classes.keys())
