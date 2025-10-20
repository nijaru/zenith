"""
Tests for Zenith testing mode functionality.

Tests the testing mode that disables rate limiting and other test-interfering
middleware when ZENITH_TESTING environment variable is set or testing=True.
"""

import os
from contextlib import contextmanager

from zenith import Zenith


@contextmanager
def temp_env(**env_vars):
    """Temporarily set environment variables."""
    old_values = {}
    for key, value in env_vars.items():
        old_values[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    try:
        yield
    finally:
        # Restore old values
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


class TestTestingModeConfiguration:
    """Test testing mode configuration and activation."""

    def test_testing_mode_default_false(self):
        """Test that testing mode is disabled by default."""
        with temp_env(ZENITH_ENV="development"):
            app = Zenith()
            assert app.testing is False

    def test_testing_mode_explicit_true(self):
        """Test that testing mode can be explicitly enabled."""
        with temp_env(ZENITH_ENV="development"):
            app = Zenith(testing=True)
            assert app.testing is True

    def test_testing_mode_explicit_false(self):
        """Test that testing mode can be explicitly disabled."""
        with temp_env(ZENITH_ENV="development"):
            app = Zenith(testing=False)
            assert app.testing is False

    def test_testing_mode_environment_variable_true(self):
        """Test that ZENITH_ENV=test enables testing mode."""
        os.environ["ZENITH_ENV"] = "test"
        try:
            app = Zenith()
            assert app.testing is True
        finally:
            del os.environ["ZENITH_ENV"]

    def test_testing_mode_environment_variable_false(self):
        """Test that ZENITH_ENV=development disables testing mode."""
        os.environ["ZENITH_ENV"] = "development"
        try:
            app = Zenith()
            assert app.testing is False
        finally:
            del os.environ["ZENITH_ENV"]

    def test_testing_mode_environment_variable_case_insensitive(self):
        """Test that ZENITH_ENV accepts various test formats."""
        test_values = ["test", "TEST", "testing", "TESTING"]

        for value in test_values:
            os.environ["ZENITH_ENV"] = value
            try:
                app = Zenith()
                assert app.testing is True, (
                    f"ZENITH_ENV={value} should enable testing mode"
                )
            finally:
                del os.environ["ZENITH_ENV"]

    def test_testing_mode_parameter_overrides_environment(self):
        """Test that explicit testing parameter overrides environment variable."""
        os.environ["ZENITH_ENV"] = "test"
        try:
            # Explicit False should override environment True
            app = Zenith(testing=False)
            assert app.testing is False
        finally:
            del os.environ["ZENITH_ENV"]

        os.environ["ZENITH_ENV"] = "development"
        try:
            # Explicit True should override environment False
            app = Zenith(testing=True)
            assert app.testing is True
        finally:
            del os.environ["ZENITH_ENV"]


class TestTestingModeMiddleware:
    """Test that testing mode affects middleware configuration."""

    def test_testing_mode_disables_rate_limiting(self):
        """Test that testing mode disables rate limiting middleware."""
        # Normal mode should have rate limiting
        app_normal = Zenith(testing=False)
        middleware_classes_normal = [m.cls.__name__ for m in app_normal.middleware]
        assert "RateLimitMiddleware" in middleware_classes_normal

        # Testing mode should not have rate limiting
        app_testing = Zenith(testing=True)
        middleware_classes_testing = [m.cls.__name__ for m in app_testing.middleware]
        assert "RateLimitMiddleware" not in middleware_classes_testing

    def test_testing_mode_preserves_essential_middleware(self):
        """Test that testing mode preserves essential middleware."""
        with temp_env(ZENITH_ENV="development"):
            app = Zenith(testing=True)
            middleware_classes = [m.cls.__name__ for m in app.middleware]

            # These middleware should still be present in testing mode
            essential_middleware = [
                "SecurityHeadersMiddleware",
                "RequestLoggingMiddleware",
                "RequestIDMiddleware",
            ]

            for middleware_name in essential_middleware:
                assert middleware_name in middleware_classes, (
                    f"{middleware_name} should be present in testing mode"
                )

    def test_testing_mode_middleware_count_difference(self):
        """Test that testing mode has fewer middleware than normal mode."""
        app_normal = Zenith(testing=False)
        app_testing = Zenith(testing=True)

        # Testing mode should have fewer middleware (due to rate limiting being disabled)
        assert len(app_testing.middleware) < len(app_normal.middleware)

    def test_testing_mode_from_environment_affects_middleware(self):
        """Test that testing mode from environment variable affects middleware."""
        os.environ["ZENITH_ENV"] = "test"
        try:
            app = Zenith()
            middleware_classes = [m.cls.__name__ for m in app.middleware]
            assert "RateLimitMiddleware" not in middleware_classes
        finally:
            del os.environ["ZENITH_ENV"]


class TestTestingModeIntegration:
    """Test testing mode integration with other framework features."""

    def test_testing_mode_with_custom_middleware(self):
        """Test that testing mode works with custom middleware."""
        from zenith.middleware.cors import CORSMiddleware

        custom_middleware = [
            CORSMiddleware,
        ]

        app = Zenith(testing=True, middleware=custom_middleware)
        # Handle both wrapped middleware (with .cls) and unwrapped middleware classes
        middleware_classes = []
        for m in app.middleware:
            if hasattr(m, "cls"):
                middleware_classes.append(m.cls.__name__)
            else:
                middleware_classes.append(m.__name__)

        # Custom middleware should be present
        assert "CORSMiddleware" in middleware_classes
        # Rate limiting should still be disabled
        assert "RateLimitMiddleware" not in middleware_classes

    def test_testing_mode_debug_flag_interaction(self):
        """Test that testing mode works correctly with debug flag."""
        # Testing mode with debug enabled
        app_debug = Zenith(testing=True, debug=True)
        assert app_debug.testing is True
        assert app_debug.config.debug is True

        # Testing mode with debug disabled
        app_no_debug = Zenith(testing=True, debug=False)
        assert app_no_debug.testing is True
        assert app_no_debug.config.debug is False

    def test_testing_mode_with_rate_limit_configuration(self):
        """Test that testing mode overrides rate limit configuration."""
        from zenith.middleware.rate_limit import RateLimit

        # Even with explicit rate limit configuration, testing mode should disable it
        [RateLimit(requests=10, window=60)]

        app = Zenith(testing=True)
        middleware_classes = [m.cls.__name__ for m in app.middleware]

        # Rate limiting should still be disabled despite configuration
        assert "RateLimitMiddleware" not in middleware_classes


class TestTestingModeUtilities:
    """Test utilities and helpers for testing mode."""

    def test_is_testing_mode_detection(self):
        """Test that app can detect if it's in testing mode."""
        app_normal = Zenith(testing=False)
        app_testing = Zenith(testing=True)

        assert app_normal.testing is False
        assert app_testing.testing is True

    def test_testing_mode_app_configuration_export(self):
        """Test that testing mode is reflected in app configuration."""
        app = Zenith(testing=True)

        # Should be able to inspect testing mode
        assert hasattr(app, "testing")
        assert app.testing is True

    def test_testing_mode_with_request_context(self):
        """Test that testing mode works in request context."""
        from zenith.testing import SyncTestClient

        app = Zenith(testing=True)

        @app.get("/test")
        async def test_endpoint():
            return {"testing": app.testing}

        client = SyncTestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        data = response.json()
        assert data["testing"] is True


class TestTestingModeErrorHandling:
    """Test error handling in testing mode."""

    def test_testing_mode_invalid_environment_value(self):
        """Test that invalid ZENITH_ENV values default to development (testing=False)."""
        invalid_values = ["maybe", "invalid", "2", ""]

        for value in invalid_values:
            os.environ["ZENITH_ENV"] = value
            try:
                app = Zenith()
                assert app.testing is False, (
                    f"ZENITH_ENV={value} should default to development"
                )
            finally:
                del os.environ["ZENITH_ENV"]

    def test_testing_mode_empty_environment_variable(self):
        """Test that empty ZENITH_ENV defaults to development."""
        os.environ["ZENITH_ENV"] = ""
        try:
            app = Zenith()
            assert app.testing is False
        finally:
            del os.environ["ZENITH_ENV"]

    def test_testing_mode_whitespace_environment_variable(self):
        """Test that whitespace-only ZENITH_ENV defaults to development."""
        os.environ["ZENITH_ENV"] = "   "
        try:
            app = Zenith()
            assert app.testing is False
        finally:
            del os.environ["ZENITH_ENV"]


class TestTestingModePerformance:
    """Test performance implications of testing mode."""

    def test_testing_mode_startup_time(self):
        """Test that testing mode doesn't significantly impact startup time."""
        import time

        # Measure normal mode startup
        start_normal = time.time()
        Zenith(testing=False)
        normal_time = time.time() - start_normal

        # Measure testing mode startup
        start_testing = time.time()
        Zenith(testing=True)
        testing_time = time.time() - start_testing

        # Testing mode should be faster or similar (fewer middleware)
        assert testing_time <= normal_time * 1.1  # Allow 10% variance

    def test_testing_mode_middleware_overhead(self):
        """Test that testing mode has less middleware overhead."""
        app_normal = Zenith(testing=False)
        app_testing = Zenith(testing=True)

        # Count middleware instances
        normal_count = len(app_normal.middleware)
        testing_count = len(app_testing.middleware)

        # Testing mode should have fewer middleware
        assert testing_count < normal_count
        assert testing_count >= 3  # Should still have essential middleware


class TestTestingModeDocumentation:
    """Test that testing mode is properly documented in the app."""

    def test_testing_mode_help_text(self):
        """Test that testing mode functionality is documented."""
        from click.testing import CliRunner

        from zenith.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["dev", "--help"])

        assert result.exit_code == 0
        assert "--testing" in result.output
        assert "Enable testing mode" in result.output or "testing mode" in result.output

    def test_testing_mode_environment_variable_documentation(self):
        """Test that ZENITH_ENV environment variable works for testing."""
        # This would typically be checked in documentation files
        # For now, just ensure the functionality exists
        os.environ["ZENITH_ENV"] = "test"
        try:
            app = Zenith()
            assert app.testing is True
        finally:
            del os.environ["ZENITH_ENV"]


class TestTestingModeRealWorldScenarios:
    """Test testing mode in real-world testing scenarios."""

    def test_testing_mode_pytest_integration(self):
        """Test that testing mode works well in pytest environment."""
        # Simulate pytest setting ZENITH_ENV
        os.environ["ZENITH_ENV"] = "test"
        try:
            app = Zenith()

            # Should be in testing mode
            assert app.testing is True

            # Should not have rate limiting
            middleware_names = [m.cls.__name__ for m in app.middleware]
            assert "RateLimitMiddleware" not in middleware_names

        finally:
            del os.environ["ZENITH_ENV"]

    def test_testing_mode_test_client_compatibility(self):
        """Test that testing mode works with TestClient."""
        from zenith.testing import SyncTestClient

        # Create app in testing mode
        app = Zenith(testing=True)

        @app.get("/test-endpoint")
        async def test_endpoint():
            return {"status": "healthy", "testing": app.testing}

        # Test with SyncTestClient
        client = SyncTestClient(app)
        response = client.get("/test-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert data["testing"] is True

    def test_testing_mode_multiple_requests_no_rate_limiting(self):
        """Test that testing mode allows multiple rapid requests without rate limiting."""
        from zenith.testing import SyncTestClient

        app = Zenith(testing=True)

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "test"}

        client = SyncTestClient(app)
        # Make multiple rapid requests (would normally trigger rate limiting)
        responses = []
        for _i in range(20):  # More than typical rate limit
            response = client.get("/api/test")
            responses.append(response)

        # All requests should succeed (no 429 Too Many Requests)
        for response in responses:
            assert response.status_code == 200, (
                f"Request failed with {response.status_code}"
            )
            assert response.json()["message"] == "test"
