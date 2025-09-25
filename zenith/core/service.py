"""
Service system for organizing business logic and domain operations.

Services provide a clean architecture pattern for organizing business logic
separate from web concerns, with built-in dependency injection, event handling,
and lifecycle management.

Key Features:
    - Clear separation of concerns between web and business logic
    - Built-in dependency injection container
    - Event-driven communication between services
    - Transaction support for database operations
    - Async initialization and shutdown lifecycle
    - Service registry for centralized management

Example Usage:
    from zenith import Service, Inject

    class UserService(Service):
        async def initialize(self):
            # Optional: setup any resources you need
            self.cache = {}
            await super().initialize()

        async def create_user(self, email: str, name: str):
            # Your business logic here
            user = User(email=email, name=name)
            # Save to database, validate, etc.
            return user

        async def find_user(self, user_id: int):
            # Your business logic with validation, caching, etc.
            if user_id in self.cache:
                return self.cache[user_id]

            user = await User.find(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            self.cache[user_id] = user
            return user

    # Using in routes with dependency injection
    @app.post("/users")
    async def create_user(
        data: UserCreate,
        users: UserService = Inject(UserService)
    ):
        return await users.create_user(data.email, data.name)

Service Lifecycle:
    1. Service classes are registered with the ServiceRegistry
    2. Services are instantiated on-demand with dependency injection
    3. initialize() is called once per service instance
    4. Services remain alive for application lifetime (singleton by default)
    5. shutdown() is called during application cleanup

Event System:
    Services can communicate through events without tight coupling:

    class EmailService(Service):
        async def initialize(self):
            # Subscribe to user events
            self.subscribe("user.created", self.send_welcome_email)
            await super().initialize()

        async def send_welcome_email(self, user):
            # Send email to new user
            await self.send_email(user.email, "Welcome!")

Transaction Support:
    Services can provide transactional contexts:

    class OrderService(Service):
        async def create_order(self, items):
            async with self.transaction():
                order = await Order.create(items=items)
                await self.update_inventory(items)
                await self.emit("order.created", order)
                return order
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


class ContainerService(ABC):
    """
    Base class for business services.

    Provides a foundation for organizing business logic with:
    - Dependency injection container access
    - Event-driven communication
    - Lifecycle management (initialize/shutdown)
    - Transaction support

    Attributes:
        container: Dependency injection container for accessing shared resources
        events: Event bus for emitting and subscribing to domain events
        _initialized: Flag tracking initialization state

    Methods:
        initialize(): Async initialization hook for setting up resources
        shutdown(): Async cleanup hook for releasing resources
        emit(event, data): Emit a domain event to all subscribers
        subscribe(event, callback): Subscribe to domain events
        transaction(): Context manager for database transactions

    Example:
        class PaymentService(Service):
            async def initialize(self):
                self.stripe = await self.container.get("stripe_client")
                self.subscribe("order.completed", self.process_payment)
                await super().initialize()

            async def process_payment(self, order):
                async with self.transaction():
                    payment = await self.stripe.charge(order.total)
                    await self.emit("payment.processed", payment)
                    return payment
    """

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


class Service:
    """
    Base class for organizing business logic in services.

    Services provide a clean way to organize business logic separate from
    web concerns, with optional container integration and event handling.

    Example:
        class UserService(Service):
            async def initialize(self):
                # Optional: set up any resources you need
                self.cache = {}
                await super().initialize()

            async def create_user(self, email: str, name: str):
                user = User(email=email, name=name)
                # Your business logic here
                return user
    """

    __slots__ = ("_initialized", "container", "events")

    def __init__(self):
        """Initialize without requiring container - it will be injected later."""
        self.container = None
        self.events = None
        self._initialized = False

    def _inject_container(self, container: DIContainer):
        """Internal method to inject container after instantiation."""
        self.container = container
        self.events = container.get("events") if container else None

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
        if self.events:
            await self.events.emit(event, data)

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to a domain event."""
        if self.events:
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
        self._services: dict[str, Service | ContainerService] = {}
        self._service_classes: dict[str, type] = {}

    def register(self, name: str, service_class: type) -> None:
        """Register a service class."""
        self._service_classes[name] = service_class

    async def get(self, name: str) -> Service | ContainerService:
        """Get or create a service instance."""
        if name not in self._services:
            if name not in self._service_classes:
                raise KeyError(f"Service not registered: {name}")

            service_class = self._service_classes[name]

            # Check if it's a Service that doesn't need container in constructor
            if issubclass(service_class, Service):
                service = service_class()
                service._inject_container(self.container)
            else:
                # ContainerService that requires container
                service = service_class(self.container)

            await service.initialize()
            self._services[name] = service

        return self._services[name]

    async def get_by_type(self, service_class: type) -> Service | ContainerService:
        """Get or create a service instance by class type."""
        # Find the service name by class type
        service_name = None
        for name, registered_class in self._service_classes.items():
            if registered_class == service_class:
                service_name = name
                break

        if service_name is None:
            # Try to use the class name as the service name
            service_name = service_class.__name__
            if service_name not in self._service_classes:
                raise KeyError(f"Service not registered: {service_class.__name__}")

        return await self.get(service_name)

    async def shutdown_all(self) -> None:
        """Shutdown all services."""
        for service in self._services.values():
            await service.shutdown()
        self._services.clear()

    def list_services(self) -> list[str]:
        """List all registered service names."""
        return list(self._service_classes.keys())
