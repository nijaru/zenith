"""
Tests for Service.create() factory method for standalone usage.

Addresses Issue 2 from ZENITH_ISSUES_ALTTEXT.md:
- Services should be instantiable outside of DI context
- Service.create() provides clean pattern for standalone usage
"""

import pytest

from zenith import Service
from zenith.testing import TestClient


class SimpleService(Service):
    """Simple service for testing standalone usage."""

    async def initialize(self):
        self.initialized = True
        await super().initialize()

    async def get_greeting(self, name: str) -> str:
        """Business logic that doesn't need container."""
        return f"Hello, {name}!"


class StatefulService(Service):
    """Service with state to test initialization."""

    async def initialize(self):
        self.cache = {}
        self.call_count = 0
        await super().initialize()

    async def increment(self) -> int:
        """Increment and return counter."""
        self.call_count += 1
        return self.call_count

    def get_cache(self, key: str):
        """Get from cache."""
        return self.cache.get(key)

    def set_cache(self, key: str, value):
        """Set in cache."""
        self.cache[key] = value


@pytest.mark.asyncio
async def test_service_create_factory():
    """Test Service.create() factory method."""
    # Create service without DI container
    service = await SimpleService.create()

    assert service is not None
    assert isinstance(service, SimpleService)
    assert service._initialized is True
    assert service._container is None  # No container in standalone mode
    assert service.events is None  # No events in standalone mode (property returns None)


@pytest.mark.asyncio
async def test_service_create_calls_initialize():
    """Test that Service.create() calls initialize()."""
    service = await SimpleService.create()

    # Should have been initialized
    assert hasattr(service, "initialized")
    assert service.initialized is True


@pytest.mark.asyncio
async def test_service_create_business_logic_works():
    """Test that business logic works in standalone service."""
    service = await SimpleService.create()

    # Business logic should work without container
    greeting = await service.get_greeting("World")

    assert greeting == "Hello, World!"


@pytest.mark.asyncio
async def test_stateful_service_create():
    """Test stateful service with cache."""
    service = await StatefulService.create()

    # Should be initialized with empty cache
    assert service.cache == {}
    assert service.call_count == 0

    # Use the service
    count1 = await service.increment()
    count2 = await service.increment()

    assert count1 == 1
    assert count2 == 2

    # Cache operations should work
    service.set_cache("key1", "value1")
    assert service.get_cache("key1") == "value1"


@pytest.mark.asyncio
async def test_service_create_multiple_instances():
    """Test that Service.create() creates independent instances."""
    service1 = await StatefulService.create()
    service2 = await StatefulService.create()

    # Each should have its own state
    await service1.increment()
    await service1.increment()
    await service2.increment()

    assert service1.call_count == 2
    assert service2.call_count == 1

    service1.set_cache("key", "value1")
    service2.set_cache("key", "value2")

    assert service1.get_cache("key") == "value1"
    assert service2.get_cache("key") == "value2"


@pytest.mark.asyncio
async def test_service_manual_instantiation_still_works():
    """Test that manual instantiation without create() still works."""
    # Old pattern should still work
    service = SimpleService()
    await service.initialize()

    greeting = await service.get_greeting("Manual")

    assert greeting == "Hello, Manual!"


@pytest.mark.asyncio
async def test_service_in_helper_function():
    """Test using Service.create() in a helper function (Issue 2 scenario)."""

    async def process_data(data: str) -> str:
        """Helper function that needs a service."""
        # This is the pattern from the issue - using service outside DI
        service = await SimpleService.create()
        return await service.get_greeting(data)

    # Should work seamlessly
    result = await process_data("Helper")

    assert result == "Hello, Helper!"


@pytest.mark.asyncio
async def test_service_with_di_still_works():
    """Test that Service still works with DI system."""
    from zenith import Inject, Zenith

    app = Zenith()

    @app.post("/test")
    async def test_endpoint(service: SimpleService = Inject()):
        return await service.get_greeting("DI")

    async with TestClient(app) as client:
        response = await client.post("/test")

        assert response.status_code == 200
        result = response.json()
        assert result == {"result": "Hello, DI!"}


@pytest.mark.asyncio
async def test_service_initialize_idempotent():
    """Test that initialize() can be called multiple times safely."""
    service = SimpleService()

    # Initialize multiple times
    await service.initialize()
    await service.initialize()
    await service.initialize()

    # Should only initialize once
    assert service._initialized is True


@pytest.mark.asyncio
async def test_service_create_with_custom_subclass():
    """Test Service.create() with custom subclass."""

    class CustomService(Service):
        async def initialize(self):
            self.custom_value = "initialized"
            await super().initialize()

        async def get_value(self):
            return self.custom_value

    service = await CustomService.create()

    assert await service.get_value() == "initialized"