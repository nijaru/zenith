"""
Tests for one-liner convenience methods - Rails-like DX improvements.

Tests for:
- app.add_auth() - JWT authentication setup
- app.add_admin() - Admin dashboard setup
- app.add_api() - API documentation setup
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from zenith import Zenith
from zenith.core.config import Config


class TestConvenienceMethods:
    """Test one-liner convenience methods."""

    @pytest.fixture
    def app(self):
        """Create test Zenith app."""
        config = Config(
            secret_key="test-secret-key-for-testing-32-chars",
            database_url="sqlite+aiosqlite:///:memory:",
            debug=True
        )
        return Zenith(config=config, middleware=[])  # Empty middleware to avoid complexity

    def test_add_auth_with_secret_key(self, app):
        """Test app.add_auth() with provided secret key."""
        result = app.add_auth(secret_key="test-secret-key-32-characters-long")

        # Should return self for chaining
        assert result is app

        # Should have added auth middleware
        assert len(app.middleware) >= 1

        # Should have added login route
        routes = [route.path for route in app._app_router.routes]
        assert "/auth/login" in routes

    def test_add_auth_with_config_secret(self, app):
        """Test app.add_auth() using secret from config."""
        result = app.add_auth()

        assert result is app
        assert len(app.middleware) >= 1

        routes = [route.path for route in app._app_router.routes]
        assert "/auth/login" in routes

    def test_add_auth_without_secret_raises_error(self):
        """Test app.add_auth() raises error when no secret available."""
        config = Config(
            secret_key=None,  # No secret key
            database_url="sqlite+aiosqlite:///:memory:",
            debug=True
        )
        app = Zenith(config=config, middleware=[])

        with pytest.raises(ValueError) as exc_info:
            app.add_auth()

        assert "Secret key required for authentication" in str(exc_info.value)

    def test_add_auth_with_custom_settings(self, app):
        """Test app.add_auth() with custom algorithm and expiration."""
        result = app.add_auth(
            secret_key="test-secret-key-32-characters-long",
            algorithm="HS512",
            expire_minutes=60
        )

        assert result is app
        routes = [route.path for route in app._app_router.routes]
        assert "/auth/login" in routes

    def test_add_admin_default_route(self, app):
        """Test app.add_admin() with default /admin route."""
        result = app.add_admin()

        # Should return self for chaining
        assert result is app

        # Should have added admin routes
        routes = [route.path for route in app._app_router.routes]
        assert "/admin" in routes
        assert "/admin/health" in routes
        assert "/admin/stats" in routes

    def test_add_admin_custom_route(self, app):
        """Test app.add_admin() with custom route."""
        result = app.add_admin(route="/dashboard")

        assert result is app

        routes = [route.path for route in app._app_router.routes]
        assert "/dashboard" in routes
        assert "/dashboard/health" in routes
        assert "/dashboard/stats" in routes

    def test_add_api_default_settings(self, app):
        """Test app.add_api() with default settings."""
        result = app.add_api()

        # Should return self for chaining
        assert result is app

        # Should have added API info route
        routes = [route.path for route in app._app_router.routes]
        assert "/api/info" in routes

    def test_add_api_custom_settings(self, app):
        """Test app.add_api() with custom settings."""
        result = app.add_api(
            title="Custom API",
            version="2.0.0",
            description="Custom API description",
            docs_url="/custom-docs",
            redoc_url="/custom-redoc"
        )

        assert result is app

        routes = [route.path for route in app._app_router.routes]
        assert "/api/info" in routes

    def test_method_chaining(self, app):
        """Test that convenience methods can be chained together."""
        result = (app
                 .add_auth(secret_key="test-secret-key-32-characters-long")
                 .add_admin("/dashboard")
                 .add_api("Chained API", "1.0.0"))

        # Should return same app instance for all chained calls
        assert result is app

        # Should have all routes from chained methods
        routes = [route.path for route in app._app_router.routes]
        assert "/auth/login" in routes
        assert "/dashboard" in routes
        assert "/dashboard/health" in routes
        assert "/dashboard/stats" in routes
        assert "/api/info" in routes


class TestConvenienceMethodsIntegration:
    """Integration tests for convenience methods."""

    @pytest.fixture
    def app(self):
        """Create test app for integration tests."""
        config = Config(
            secret_key="test-secret-key-for-testing-32-chars",
            database_url="sqlite+aiosqlite:///:memory:",
            debug=True
        )
        return Zenith(config=config, middleware=[])

    async def test_admin_health_endpoint_functionality(self, app):
        """Test that admin health endpoint actually works."""
        app.add_admin()

        # Mock the database health check
        with patch.object(app.app.database, 'health_check', return_value=True) as mock_health:
            # Get the admin health route function
            admin_health_route = None
            for route in app._app_router.routes:
                if route.path == "/admin/health":
                    admin_health_route = route.endpoint
                    break

            assert admin_health_route is not None

            # Call the endpoint
            result = await admin_health_route()

            assert result['status'] == 'healthy'
            assert result['database'] == 'connected'
            assert result['version'] == '0.3.0'
            mock_health.assert_called_once()

    async def test_admin_health_endpoint_unhealthy(self, app):
        """Test admin health endpoint when database is unhealthy."""
        app.add_admin()

        # Mock the database health check to return False
        with patch.object(app.app.database, 'health_check', return_value=False):
            admin_health_route = None
            for route in app._app_router.routes:
                if route.path == "/admin/health":
                    admin_health_route = route.endpoint
                    break

            result = await admin_health_route()

            assert result['status'] == 'unhealthy'
            assert result['database'] == 'disconnected'

    async def test_admin_stats_endpoint_functionality(self, app):
        """Test that admin stats endpoint returns correct statistics."""
        app.add_admin()

        # Get the admin stats route function
        admin_stats_route = None
        for route in app._app_router.routes:
            if route.path == "/admin/stats":
                admin_stats_route = route.endpoint
                break

        assert admin_stats_route is not None

        # Call the endpoint
        result = await admin_stats_route()

        assert 'routes_count' in result
        assert 'middleware_count' in result
        assert 'debug_mode' in result
        assert result['debug_mode'] is True  # From config
        assert isinstance(result['routes_count'], int)
        assert isinstance(result['middleware_count'], int)

    async def test_api_info_endpoint_functionality(self, app):
        """Test that API info endpoint returns correct information."""
        app.add_api(
            title="Test API",
            version="1.2.3",
            description="Test API description",
            docs_url="/test-docs"
        )

        # Get the API info route function
        api_info_route = None
        for route in app._app_router.routes:
            if route.path == "/api/info":
                api_info_route = route.endpoint
                break

        assert api_info_route is not None

        # Call the endpoint
        result = await api_info_route()

        assert result['title'] == "Test API"
        assert result['version'] == "1.2.3"
        assert result['description'] == "Test API description"
        assert result['docs_url'] == "/test-docs"


class TestConvenienceMethodsErrorHandling:
    """Test error handling in convenience methods."""

    def test_add_auth_handles_import_errors_gracefully(self):
        """Test add_auth handles missing auth components gracefully."""
        config = Config(
            secret_key="test-secret-key-for-testing-32-chars",
            database_url="sqlite+aiosqlite:///:memory:",
            debug=True
        )
        app = Zenith(config=config, middleware=[])

        # Mock import error for auth components
        with patch('zenith.auth.JWTManager', side_effect=ImportError("Auth not available")):
            with pytest.raises(ImportError):
                app.add_auth()

    async def test_admin_health_handles_database_errors(self, app):
        """Test admin health endpoint handles database errors gracefully."""
        app = Zenith(config=Config(
            secret_key="test-secret-key-for-testing-32-chars",
            database_url="sqlite+aiosqlite:///:memory:",
            debug=True
        ), middleware=[])

        app.add_admin()

        # Mock database health check to raise exception
        with patch.object(app.app.database, 'health_check', side_effect=Exception("Database error")):
            admin_health_route = None
            for route in app._app_router.routes:
                if route.path == "/admin/health":
                    admin_health_route = route.endpoint
                    break

            result = await admin_health_route()

            assert result['status'] == 'unhealthy'
            assert 'error' in result
            assert 'Database error' in result['error']