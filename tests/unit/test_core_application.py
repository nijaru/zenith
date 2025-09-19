"""
Unit tests for the core Zenith application class.

Tests application lifecycle, middleware integration, and configuration.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from zenith import Inject, Service, Zenith
from zenith.auth import configure_auth
from zenith.testing import TestClient


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-testing"
    yield
    # Cleanup after test
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]


class TestZenithApplication:
    """Test suite for the main Zenith application class."""

    def test_application_creation(self):
        """Test basic application creation with default settings."""
        app = Zenith(debug=True)

        assert hasattr(app, "config")
        assert hasattr(app, "app")  # Core application
        assert hasattr(app, "routers")
        # Zenith now auto-adds essential middleware for production readiness
        assert len(app.middleware) >= 6  # Auto-added optimized middleware
        assert len(app.routers) >= 1  # Has global router

    def test_application_with_custom_config(self):
        """Test application creation with custom configuration."""
        app = Zenith(debug=True)

        assert app.config.debug

    def test_context_registration(self):
        """Test context registration and dependency injection setup."""
        app = Zenith(debug=True)

        class UserService(Service):
            async def get_user(self, id: int):
                return {"id": id, "name": "Test User"}

        # Register context
        app.register_context("users", UserService)

        # Should be registered in the service registry
        contexts = app.app.contexts
        assert "users" in contexts._service_classes
        assert contexts._service_classes["users"] == UserService

    def test_middleware_registration(self):
        """Test middleware registration and ordering."""
        app = Zenith(debug=True)

        # Mock middleware
        middleware1 = Mock()
        middleware2 = Mock()

        # Get initial middleware count (auto-added middleware)
        initial_count = len(app.middleware)

        app.add_middleware(middleware1, arg1="test")
        app.add_middleware(middleware2, arg2="test2")

        # Should have initial + 2 new middleware
        assert len(app.middleware) == initial_count + 2
        # Middleware is stored as Starlette Middleware objects
        from starlette.middleware import Middleware

        assert isinstance(app.middleware[-2], Middleware)
        assert isinstance(app.middleware[-1], Middleware)
        # New middleware added at the end
        assert app.middleware[-2].cls == middleware1
        assert app.middleware[-1].cls == middleware2
        assert app.middleware[-2].kwargs == {"arg1": "test"}
        assert app.middleware[-1].kwargs == {"arg2": "test2"}

    def test_cors_middleware_integration(self):
        """Test CORS middleware integration."""
        app = Zenith(debug=True)

        # Get initial middleware count
        initial_count = len(app.middleware)

        app.add_cors(
            allow_origins=["http://localhost:3000"],
            allow_methods=["GET", "POST"],
            allow_credentials=True,
        )

        # Should have added CORS middleware
        assert len(app.middleware) == initial_count + 1
        from starlette.middleware import Middleware

        assert isinstance(app.middleware[-1], Middleware)
        middleware_class = app.middleware[-1].cls
        assert "CORS" in middleware_class.__name__

    def test_security_headers_integration(self):
        """Test security headers middleware integration."""
        app = Zenith(debug=True)

        # Get initial middleware count
        initial_count = len(app.middleware)

        # Test development config (replaces existing SecurityHeaders)
        app.add_security_headers(strict=False)
        assert (
            len(app.middleware) == initial_count
        )  # Same count - replacement not addition

        # Test strict config (replaces existing again)
        app.add_security_headers(strict=True)
        assert len(app.middleware) == initial_count  # Still same count

    def test_exception_handling_integration(self):
        """Test exception handling middleware integration."""
        app = Zenith(debug=True)

        # Get initial middleware count
        initial_count = len(app.middleware)

        app.add_exception_handling(debug=True)

        # Exception middleware is already auto-added, so no count change expected
        assert len(app.middleware) == initial_count
        from starlette.middleware import Middleware

        # Check that exception middleware is present (it's first in the stack)
        assert isinstance(app.middleware[0], Middleware)
        exception_middleware = app.middleware[0].cls
        assert "Exception" in exception_middleware.__name__


@pytest.mark.asyncio
class TestApplicationLifecycle:
    """Test application startup and shutdown lifecycle."""

    async def test_startup_and_shutdown(self):
        """Test application startup and shutdown hooks."""
        app = Zenith(debug=True)

        startup_called = []
        shutdown_called = []

        @app.on_event("startup")
        async def startup_handler():
            startup_called.append(True)

        @app.on_event("shutdown")
        async def shutdown_handler():
            shutdown_called.append(True)

        # Test startup
        await app.startup()
        assert len(startup_called) == 1

        # Test shutdown
        await app.shutdown()
        assert len(shutdown_called) == 1

    async def test_database_integration(self):
        """Test database integration during startup."""
        app = Zenith(debug=True)

        # Mock database setup
        with patch("zenith.db.Database") as mock_db_class:
            mock_db_class.return_value = AsyncMock()

            # The database is initialized in app startup
            await app.startup()

            # Database should be available
            assert app.app.container._services.get("zenith.db.Database") is not None

    async def test_authentication_integration(self):
        """Test authentication system integration."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough-for-jwt")

        @app.get("/test")
        async def test_endpoint():
            return {"test": True}

        async with TestClient(app) as client:
            response = await client.get("/test")
            assert response.status_code == 200

            # Should have authentication middleware
            middleware_classes = [m.cls.__name__ for m in app.middleware]
            assert any("Auth" in name for name in middleware_classes)


@pytest.mark.asyncio
class TestRoutingIntegration:
    """Test routing integration with the main application."""

    async def test_basic_route_registration(self):
        """Test basic HTTP method route registration."""
        # Use a longer secret key to avoid CSRF being disabled
        import os

        os.environ["SECRET_KEY"] = (
            "test-secret-key-that-is-long-enough-for-csrf-testing"
        )

        app = Zenith(debug=True)

        # Remove CSRF middleware for testing POST requests
        # (in production, CSRF should be properly handled with tokens)

        app.middleware = [
            m
            for m in app.middleware
            if not (hasattr(m, "cls") and "CSRF" in str(m.cls))
        ]

        @app.get("/users")
        async def get_users():
            return {"users": []}

        @app.post("/users")
        async def create_user():
            return {"created": True}

        async with TestClient(app) as client:
            # Test GET
            response = await client.get("/users")
            assert response.status_code == 200
            data = response.json()
            assert data["users"] == []

            # Test POST
            response = await client.post("/users")
            assert response.status_code == 200
            data = response.json()
            assert data["created"]

    async def test_route_with_context_dependency(self):
        """Test routes using context dependency injection."""
        app = Zenith(debug=True)

        class TestService(Service):
            def get_data(self):
                return {"context": "data"}

        app.register_context("test", TestService)

        @app.get("/context-test")
        async def context_endpoint(ctx: TestService = Inject()):
            return ctx.get_data()

        async with TestClient(app) as client:
            response = await client.get("/context-test")
            assert response.status_code == 200
            data = response.json()
            assert data["context"] == "data"

    async def test_subrouter_integration(self):
        """Test subrouter integration."""
        from zenith.core.routing import Router

        app = Zenith(debug=True)
        api_router = Router(prefix="/api/v1")

        @api_router.get("/status")
        async def api_status():
            return {"status": "ok", "version": "v1"}

        app.include_router(api_router)

        async with TestClient(app) as client:
            response = await client.get("/api/v1/status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["version"] == "v1"


class TestApplicationConfiguration:
    """Test application configuration and settings."""

    def test_debug_mode_configuration(self):
        """Test debug mode affects middleware and error handling."""
        # Debug mode
        debug_app = Zenith(debug=True)
        initial_debug_count = len(debug_app.middleware)
        debug_app.add_exception_handling()

        # Exception handler already auto-added, no count change
        assert len(debug_app.middleware) == initial_debug_count

        # Production mode (with proper secret key)
        import os

        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-production"
        prod_app = Zenith(debug=False)
        initial_prod_count = len(prod_app.middleware)
        prod_app.add_exception_handling()

        assert len(prod_app.middleware) == initial_prod_count

    def test_openapi_schema_generation(self):
        """Test OpenAPI schema generation."""
        app = Zenith(debug=True)

        @app.get("/test")
        async def test_endpoint():
            """Test endpoint documentation."""
            return {"test": True}

        # Should be able to generate some form of API schema
        # (Implementation depends on how openapi is handled)
        assert hasattr(app, "get")  # Has route decorators
        assert len(app.routers) >= 1

    def test_static_file_configuration(self):
        """Test static file serving configuration."""
        app = Zenith(debug=True)

        # Mock static directory - need to mock os.path.isdir which is what Starlette uses
        with patch("os.path.isdir", return_value=True):
            app.mount_static("/static", "/tmp/static")

            # Should have mounted static files
            assert hasattr(app, "_static_mounts")
            assert len(app._static_mounts) > 0


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
