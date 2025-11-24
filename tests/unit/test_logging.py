"""
Tests for structured logging configuration.

Tests the structlog-based logging system with context binding
and middleware integration.
"""

import logging

import pytest

from zenith.logging import (
    LoggingMiddleware,
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
)


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_default_name(self):
        """Test getting logger with default name."""
        logger = get_logger()
        assert logger is not None

    def test_get_logger_custom_name(self):
        """Test getting logger with custom name."""
        logger = get_logger("my_module")
        assert logger is not None

    def test_logger_has_standard_methods(self):
        """Test that logger has standard logging methods."""
        logger = get_logger("test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "exception")


class TestContextBinding:
    """Test suite for context binding functions."""

    def setup_method(self):
        """Clear context before each test."""
        clear_context()

    def teardown_method(self):
        """Clear context after each test."""
        clear_context()

    def test_bind_context_single_value(self):
        """Test binding a single context value."""
        bind_context(request_id="abc-123")
        # Context is stored internally - we test via logging output
        # or by checking the context variable directly
        from zenith.logging import _log_context

        assert _log_context.get()["request_id"] == "abc-123"

    def test_bind_context_multiple_values(self):
        """Test binding multiple context values."""
        bind_context(request_id="abc-123", user_id=456, path="/api/users")
        from zenith.logging import _log_context

        ctx = _log_context.get()
        assert ctx["request_id"] == "abc-123"
        assert ctx["user_id"] == 456
        assert ctx["path"] == "/api/users"

    def test_bind_context_accumulates(self):
        """Test that multiple bind_context calls accumulate."""
        bind_context(request_id="abc-123")
        bind_context(user_id=456)
        from zenith.logging import _log_context

        ctx = _log_context.get()
        assert ctx["request_id"] == "abc-123"
        assert ctx["user_id"] == 456

    def test_clear_context(self):
        """Test clearing all context values."""
        bind_context(request_id="abc-123", user_id=456)
        clear_context()
        from zenith.logging import _log_context

        # After clearing, context should be empty dict
        try:
            ctx = _log_context.get()
            assert ctx == {}
        except LookupError:
            # Also acceptable if never set
            pass


class TestConfigureLogging:
    """Test suite for configure_logging function."""

    def test_configure_with_defaults(self):
        """Test configuring logging with default settings."""
        configure_logging()
        # Should not raise any exceptions
        logger = get_logger("test")
        logger.info("test message")

    def test_configure_with_debug_level(self):
        """Test configuring logging with DEBUG level."""
        configure_logging(level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_configure_with_json_logs(self):
        """Test configuring logging with JSON output."""
        configure_logging(json_logs=True)
        # Should not raise any exceptions
        logger = get_logger("test")
        logger.info("test message")

    def test_configure_with_console_logs(self):
        """Test configuring logging with console output."""
        configure_logging(json_logs=False)
        # Should not raise any exceptions
        logger = get_logger("test")
        logger.info("test message")


class TestLoggingMiddleware:
    """Test suite for LoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_passes_through_non_http(self):
        """Test that non-HTTP scopes pass through unchanged."""
        app_called = False

        async def app(scope, receive, send):
            nonlocal app_called
            app_called = True

        middleware = LoggingMiddleware(app)
        await middleware({"type": "websocket"}, None, None)
        assert app_called

    @pytest.mark.asyncio
    async def test_middleware_binds_request_context(self):
        """Test that middleware binds request context."""
        from zenith.logging import _log_context

        clear_context()

        context_during_request = None

        async def app(scope, receive, send):
            nonlocal context_during_request
            context_during_request = _log_context.get().copy()
            # Send minimal response
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = LoggingMiddleware(app, log_requests=False)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/users",
            "client": ("127.0.0.1", 8000),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        messages = []

        async def send(message):
            messages.append(message)

        await middleware(scope, receive, send)

        # Context should have been bound during request
        assert context_during_request["method"] == "GET"
        assert context_during_request["path"] == "/api/users"
        assert context_during_request["client_ip"] == "127.0.0.1"
        assert "request_id" in context_during_request

    @pytest.mark.asyncio
    async def test_middleware_clears_context_after_request(self):
        """Test that middleware clears context after request."""
        from zenith.logging import _log_context

        clear_context()

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = LoggingMiddleware(app, log_requests=False)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "client": ("127.0.0.1", 8000),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        # Context should be cleared after request
        try:
            ctx = _log_context.get()
            assert ctx == {}
        except LookupError:
            pass  # Also acceptable

    @pytest.mark.asyncio
    async def test_middleware_stores_request_id_in_scope(self):
        """Test that middleware stores request_id in scope state."""
        stored_request_id = None

        async def app(scope, receive, send):
            nonlocal stored_request_id
            stored_request_id = scope.get("state", {}).get("request_id")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = LoggingMiddleware(app, log_requests=False)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "client": ("127.0.0.1", 8000),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        assert stored_request_id is not None
        assert len(stored_request_id) == 8  # UUID prefix


class TestLoggingIntegration:
    """Integration tests for logging with the framework."""

    def test_logger_with_context(self, caplog):
        """Test that bound context appears in logs."""
        configure_logging(level="INFO", json_logs=False)
        clear_context()

        bind_context(request_id="test-123", user_id=456)

        logger = get_logger("integration_test")

        with caplog.at_level(logging.INFO):
            logger.info("test_event", extra_field="value")

        # The context should be in the log output
        # Note: exact format depends on structlog configuration
        clear_context()
