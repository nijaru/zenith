"""
Tests for dependency injection container.
"""

import pytest

from zenith.core.container import DIContainer


class TestService:
    """Test service class."""

    def __init__(self, value: str = "default"):
        self.value = value


class TestDependentService:
    """Test service with dependencies."""

    def __init__(self, dependency: TestService):
        self.dependency = dependency


class TestAsyncService:
    """Test async service."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.closed = True


class TestDIContainer:
    """Test dependency injection container."""

    def test_register_and_get_instance(self):
        """Test registering and getting service instances."""
        container = DIContainer()
        service_instance = TestService("test_value")

        container.register(TestService, service_instance)
        retrieved = container.get(TestService)

        assert retrieved == service_instance
        assert retrieved.value == "test_value"

    def test_register_and_get_class(self):
        """Test registering and auto-instantiating service classes."""
        container = DIContainer()

        container.register(TestService, TestService)
        retrieved = container.get(TestService)

        assert isinstance(retrieved, TestService)
        assert retrieved.value == "default"

    def test_singleton_behavior(self):
        """Test singleton service behavior."""
        container = DIContainer()

        container.register(TestService, TestService, singleton=True)

        instance1 = container.get(TestService)
        instance2 = container.get(TestService)

        assert instance1 is instance2

    def test_non_singleton_behavior(self):
        """Test non-singleton service behavior."""
        container = DIContainer()

        container.register(TestService, TestService, singleton=False)

        instance1 = container.get(TestService)
        instance2 = container.get(TestService)

        assert instance1 is not instance2
        assert isinstance(instance1, TestService)
        assert isinstance(instance2, TestService)

    def test_dependency_injection(self):
        """Test automatic dependency injection."""
        container = DIContainer()

        # Register dependency first
        container.register(TestService, TestService)
        # Register dependent service
        container.register(TestDependentService, TestDependentService)

        service = container.get(TestDependentService)

        assert isinstance(service, TestDependentService)
        assert isinstance(service.dependency, TestService)

    def test_string_key_registration(self):
        """Test registering services with string keys."""
        container = DIContainer()
        service_instance = TestService("string_key_test")

        container.register("test_service", service_instance)
        retrieved = container.get("test_service")

        assert retrieved == service_instance

    def test_service_not_found(self):
        """Test error when service not found."""
        container = DIContainer()

        with pytest.raises(KeyError, match="Service not registered"):
            container.get("nonexistent")

    @pytest.mark.asyncio
    async def test_startup_and_shutdown_hooks(self):
        """Test startup and shutdown hooks."""
        container = DIContainer()

        startup_called = []
        shutdown_called = []

        def startup_hook():
            startup_called.append(True)

        async def async_shutdown_hook():
            shutdown_called.append(True)

        container.register_startup(startup_hook)
        container.register_shutdown(async_shutdown_hook)

        await container.startup()
        assert len(startup_called) == 1

        await container.shutdown()
        assert len(shutdown_called) == 1

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """Test container lifespan context manager."""
        container = DIContainer()

        called = []

        def startup_hook():
            called.append("startup")

        def shutdown_hook():
            called.append("shutdown")

        container.register_startup(startup_hook)
        container.register_shutdown(shutdown_hook)

        async with container.lifespan():
            assert called == ["startup"]

        assert called == ["startup", "shutdown"]
