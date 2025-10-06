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
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
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


class Service:
    """
    Base class for organizing business logic in services.

    Services provide a clean architecture for organizing business logic with
    automatic dependency injection, request context access, and event handling.

    Usage Patterns:

    1. Simple Service (no dependencies):
        class ProductService(Service):
            async def get_product(self, product_id: int):
                return await Product.find(product_id)

    2. Service with Dependencies (constructor injection):
        class OrderService(Service):
            def __init__(self, products: ProductService, payments: PaymentService):
                self.products = products
                self.payments = payments

            async def create_order(self, data: OrderCreate):
                product = await self.products.get_product(data.product_id)
                payment = await self.payments.charge(data.total)
                return await Order.create(product=product, payment=payment)

    3. Using in Routes:
        @app.post("/orders")
        async def create_order(
            data: OrderCreate,
            orders: OrderService = Inject()  # Fully wired with dependencies!
        ):
            return await orders.create_order(data)

    4. Request Context Access:
        class AuditService(Service):
            async def log_action(self, action: str):
                # Auto-available in request context
                user_id = self.user.id if self.user else None
                ip = self.request.client.host if self.request else "unknown"
                await AuditLog.create(user_id=user_id, ip=ip, action=action)

    Key Features:
        - Constructor injection: Dependencies auto-resolved from type hints
        - Request context: Access current request and user via properties
        - Event system: Publish/subscribe for service communication
        - Lifecycle hooks: initialize() and shutdown() for resource management
        - Database access: Auto-managed sessions via ZenithModel
    """

    __slots__ = ("_container", "_events", "_initialized", "_request")

    def __init__(self):
        """
        Initialize service.

        Note: User services don't need to call super().__init__().
        Framework attributes are initialized lazily.

        Example:
            class OrderService(Service):
                def __init__(self, products: ProductService):
                    # No need to call super().__init__()!
                    self.products = products
        """
        # Initialize framework attributes
        # These will be initialized lazily if subclass overrides __init__
        self._init_framework_attrs()

    def _init_framework_attrs(self):
        """Initialize framework attributes (can be called multiple times safely)."""
        if not hasattr(self, "_container"):
            self._container: DIContainer | None = None
        if not hasattr(self, "_request"):
            self._request: Any = None
        if not hasattr(self, "_events"):
            self._events: EventBus | None = None
        if not hasattr(self, "_initialized"):
            self._initialized = False

    @classmethod
    async def create(cls, *args, **kwargs):
        """
        Factory method to create and initialize a service instance.

        Useful for standalone usage outside of DI context (CLI, helpers, tests).

        Example:
            service = await MyService.create()
            result = await service.do_something()
        """
        instance = cls(*args, **kwargs)
        await instance.initialize()
        return instance

    # Request Context Properties (auto-available in request context)

    @property
    def request(self) -> Any:
        """
        Current request object (when in request context).

        Returns None when service is used outside of a web request
        (e.g., in background jobs, CLI commands, or tests).

        Example:
            class AuditService(Service):
                async def log_action(self, action: str):
                    if self.request:
                        ip = self.request.client.host
                        user_agent = self.request.headers.get('user-agent')
        """
        self._init_framework_attrs()
        return self._request

    @property
    def user(self) -> Any:
        """
        Current authenticated user (when in request context with auth).

        Returns None when:
        - Not in request context
        - Request is not authenticated
        - No auth middleware configured

        Example:
            class OrderService(Service):
                async def create_order(self, data: OrderCreate):
                    if self.user:
                        order = await Order.create(user_id=self.user.id, ...)
                    else:
                        raise ValueError("Authentication required")
        """
        self._init_framework_attrs()
        if self._request and hasattr(self._request, "state"):
            return getattr(self._request.state, "user", None)
        return None

    @property
    def session(self):
        """
        Database session (auto-managed via request context).

        Returns the current database session from the request context.
        In most cases, you don't need this - use ZenithModel instead.

        Example:
            # Prefer this (ZenithModel handles sessions):
            users = await User.where(active=True).all()

            # Only use self.session for raw queries:
            result = await self.session.execute(select(User))
        """
        from zenith.core.container import get_current_db_session

        return get_current_db_session()

    @property
    def events(self) -> EventBus | None:
        """Event bus for pub/sub communication between services."""
        self._init_framework_attrs()
        if self._events is None and self._container:
            with suppress(KeyError):
                self._events = self._container.get("events")
        return self._events

    # Lifecycle Methods

    async def initialize(self) -> None:
        """
        Initialize the service (called once after construction).

        Override this for async setup like connecting to external services,
        loading configuration, or initializing caches.

        Example:
            class CacheService(Service):
                async def initialize(self):
                    self.redis = await connect_redis()
                    await super().initialize()
        """
        self._init_framework_attrs()
        if self._initialized:
            return
        self._initialized = True

    async def shutdown(self) -> None:
        """
        Cleanup service resources (called during app shutdown).

        Override this to close connections, flush caches, or cleanup resources.

        Example:
            class CacheService(Service):
                async def shutdown(self):
                    if self.redis:
                        await self.redis.close()
        """
        pass

    # Event System

    async def emit(self, event: str, data: Any = None) -> None:
        """
        Emit a domain event to all subscribers.

        Example:
            class UserService(Service):
                async def create_user(self, data):
                    user = await User.create(**data)
                    await self.emit("user.created", user)
                    return user
        """
        self._init_framework_attrs()
        if self.events:
            await self.events.emit(event, data)

    def subscribe(self, event: str, callback: Callable) -> None:
        """
        Subscribe to a domain event.

        Example:
            class EmailService(Service):
                async def initialize(self):
                    self.subscribe("user.created", self.send_welcome_email)
                    await super().initialize()

                async def send_welcome_email(self, user):
                    await send_email(user.email, "Welcome!")
        """
        self._init_framework_attrs()
        if self.events:
            self.events.subscribe(event, callback)

    # Transaction Support

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.

        Override in subclasses for custom transaction handling.

        Example:
            class OrderService(Service):
                async def create_order(self, items):
                    async with self.transaction():
                        order = await Order.create(items=items)
                        await self.update_inventory(items)
                        return order
        """
        # Default implementation - no transaction support
        yield

    # Internal Framework Methods

    def _inject_container(self, container: DIContainer) -> None:
        """Internal: Inject DI container (called by framework)."""
        self._init_framework_attrs()
        self._container = container

    def _inject_request(self, request: Any) -> None:
        """Internal: Inject request context (called by framework)."""
        self._init_framework_attrs()
        self._request = request

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class ServiceRegistry:
    """Registry for managing application services with dependency injection."""

    __slots__ = ("_service_classes", "_services", "container")

    def __init__(self, container: DIContainer):
        self.container = container
        self._services: dict[str, Service] = {}
        self._service_classes: dict[str, type[Service]] = {}

    def register(self, name: str, service_class: type[Service]) -> None:
        """Register a service class."""
        self._service_classes[name] = service_class

    async def get(self, name: str) -> Service:
        """Get or create a service instance with dependency injection."""
        if name not in self._services:
            if name not in self._service_classes:
                raise KeyError(f"Service not registered: {name}")

            service_class = self._service_classes[name]

            # Use DIContainer's injection for constructor DI
            service = self.container._create_instance(service_class)

            # Inject framework internals
            if isinstance(service, Service):
                service._inject_container(self.container)

            # Initialize
            await service.initialize()
            self._services[name] = service

        return self._services[name]

    async def get_by_type(self, service_class: type[Service]) -> Service:
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
