"""
Structured logging configuration for Zenith applications.

Provides centralized logging configuration using structlog with:
- Request context binding (request_id, user_id, etc.)
- JSON output for production
- Human-readable console output for development
- Integration with standard library logging
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

import structlog
from structlog.types import Processor

if TYPE_CHECKING:
    from structlog.typing import EventDict

# Context variable for request-scoped log context
_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context")


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (defaults to 'zenith')

    Returns:
        A bound structlog logger

    Example:
        from zenith.logging import get_logger

        logger = get_logger(__name__)
        logger.info("user_created", user_id=123, email="user@example.com")
    """
    return structlog.get_logger(name or "zenith")


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to all loggers in the current context.

    Useful for adding request-scoped data like request_id, user_id, etc.

    Example:
        bind_context(request_id="abc-123", user_id=456)
        logger.info("processing_request")  # includes request_id and user_id
    """
    try:
        current = _log_context.get()
    except LookupError:
        current = {}
    _log_context.set({**current, **kwargs})


def clear_context() -> None:
    """Clear all bound context variables."""
    _log_context.set({})


def _add_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Processor that adds context variables to log events."""
    try:
        context = _log_context.get()
        if context:
            event_dict.update(context)
    except LookupError:
        pass  # No context set
    return event_dict


def configure_logging(
    level: str | int = "INFO",
    json_logs: bool | None = None,
    log_file: str | None = None,
    include_timestamp: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Use JSON format (auto-detected if None: True for non-TTY)
        log_file: Optional file path to write logs to
        include_timestamp: Include timestamps in log output

    Example:
        from zenith.logging import configure_logging

        # Development (auto-detects console)
        configure_logging(level="DEBUG")

        # Production (JSON logs)
        configure_logging(level="INFO", json_logs=True)
    """
    # Auto-detect JSON mode if not specified
    if json_logs is None:
        json_logs = not sys.stderr.isatty()

    # Convert string level to int
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _add_context,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if include_timestamp:
        processors.insert(0, structlog.processors.TimeStamper(fmt="iso"))

    # Add exception formatting
    processors.append(structlog.processors.format_exc_info)

    # Choose output format
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=sys.stderr.isatty(),
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Add file handler if specified
    handlers: list[logging.Handler] = [handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=handlers,
        force=True,
    )

    # Set levels for common noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def configure_for_development() -> None:
    """Configure logging for development with colored console output."""
    configure_logging(level="DEBUG", json_logs=False, include_timestamp=True)


def configure_for_production() -> None:
    """Configure logging for production with JSON output."""
    configure_logging(level="INFO", json_logs=True, include_timestamp=True)


class LoggingMiddleware:
    """
    ASGI middleware that adds request context to all logs.

    Automatically binds request_id, method, path, and client_ip to log context.
    """

    def __init__(self, app, *, log_requests: bool = True):
        """
        Initialize the logging middleware.

        Args:
            app: The ASGI application
            log_requests: Whether to log request start/end
        """
        self.app = app
        self.log_requests = log_requests
        self.logger = get_logger("zenith.http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        import uuid

        # Generate request ID
        request_id = scope.get("state", {}).get("request_id") or str(uuid.uuid4())[:8]

        # Get request details
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        client = scope.get("client", ("unknown", 0))
        client_ip = client[0] if client else "unknown"

        # Bind context for all logs in this request
        bind_context(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
        )

        # Store request_id in scope for other middleware
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            if self.log_requests:
                self.logger.info("request_started")

            await self.app(scope, receive, send_wrapper)

            if self.log_requests:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                self.logger.info(
                    "request_completed",
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.exception(
                "request_failed",
                status_code=500,
                duration_ms=duration_ms,
                error=str(e),
            )
            raise
        finally:
            clear_context()


# Export commonly used items
__all__ = [
    "LoggingMiddleware",
    "bind_context",
    "clear_context",
    "configure_for_development",
    "configure_for_production",
    "configure_logging",
    "get_logger",
]
