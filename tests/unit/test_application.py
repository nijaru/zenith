"""
Tests for core Application kernel.
"""

import pytest

from zenith.core.application import Application
from zenith.core.config import Config
from zenith.core.context import Context


class MockTestContext(Context):
    """Test context for testing."""

    async def initialize(self):
        await super().initialize()
        self.test_data = "initialized"


class TestApplication:
    """Test core application functionality."""

    @pytest.mark.asyncio
    async def test_application_startup_and_shutdown(self):
        """Test basic application lifecycle."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        assert not app.is_running()
        assert not app.is_startup_complete()

        await app.startup()

        assert app.is_running()
        assert app.is_startup_complete()

        await app.shutdown()

        assert not app.is_running()

    @pytest.mark.asyncio
    async def test_application_lifespan_context(self):
        """Test application lifespan context manager."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        async with app.lifespan():
            assert app.is_running()

        assert not app.is_running()

    def test_service_registration(self):
        """Test service registration with application."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        test_service = "test_value"
        app.register_service("test", test_service)

        retrieved = app.container.get("test")
        assert retrieved == test_service

    def test_context_registration(self):
        """Test context registration."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        app.register_context("test_context", MockTestContext)

        # Check that context is registered
        context_names = app.contexts.list_contexts()
        assert "test_context" in context_names

    @pytest.mark.asyncio
    async def test_get_context(self):
        """Test getting context instances."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        app.register_context("test_context", MockTestContext)
        await app.startup()

        try:
            context = await app.get_context("test_context")

            assert isinstance(context, MockTestContext)
            assert hasattr(context, "test_data")
            assert context.test_data == "initialized"
        finally:
            await app.shutdown()

    def test_core_services_registered(self):
        """Test that core services are automatically registered."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        # Check core services are registered
        assert app.container.get("config") == config
        assert app.container.get("events") == app.events
        assert app.container.get("contexts") == app.contexts
        assert app.container.get("supervisor") == app.supervisor
        assert app.container.get("application") == app

    @pytest.mark.asyncio
    async def test_shutdown_hooks(self):
        """Test shutdown hook functionality."""
        config = Config()
        config.debug = True  # Avoid SECRET_KEY validation in tests
        app = Application(config)

        hook_called = []

        def sync_hook():
            hook_called.append("sync")

        async def async_hook():
            hook_called.append("async")

        app.register_shutdown_hook(sync_hook)
        app.register_shutdown_hook(async_hook)

        await app.startup()
        await app.shutdown()

        assert "sync" in hook_called
        assert "async" in hook_called

    def test_config_validation(self):
        """Test that invalid config raises error."""
        config = Config()
        config.port = -1  # Invalid port

        with pytest.raises(ValueError):
            Application(config)
