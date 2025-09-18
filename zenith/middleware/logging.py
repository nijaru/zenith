"""
Request/response logging middleware with structured logging support.

Provides comprehensive request/response logging with configurable
formats, filtering, and integration with request ID tracking.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

import msgspec
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestLoggingConfig:
    """Configuration for request logging middleware."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        level: int = logging.INFO,
        include_headers: bool = False,
        include_body: bool = False,
        exclude_paths: set[str] | None = None,
        exclude_health_checks: bool = True,
        max_body_size: int = 1024,
        formatter: Callable[[dict], str] | None = None,
    ):
        self.logger = logger or logging.getLogger("zenith.requests")
        self.level = level
        self.include_headers = include_headers
        self.include_body = include_body
        self.max_body_size = max_body_size

        # Default exclude patterns
        self.exclude_paths = exclude_paths or set()
        if exclude_health_checks:
            self.exclude_paths.update({"/health", "/health/", "/healthz", "/ping"})

        # Default formatter
        self.formatter = formatter or self._create_default_formatter()

    def _create_default_formatter(self) -> Callable[[dict], str]:
        """Create the default formatter for log messages."""

        def formatter(log_data: dict[str, Any]) -> str:
            req = log_data["request"]
            resp = log_data["response"]
            duration = log_data["duration_ms"]

            return (
                f"{req['method']} {req['path']} "
                f"- {resp['status_code']} "
                f"({duration}ms) "
                f"[{req['client_ip']}]"
            )

        return formatter


class RequestLoggingMiddleware:
    """
    Middleware that logs HTTP requests and responses with structured data.

    Supports filtering by path patterns, configurable log formats,
    and integration with request ID tracking.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: RequestLoggingConfig | None = None,
        # Individual parameters (for backward compatibility)
        logger: logging.Logger | None = None,
        level: int = logging.INFO,
        include_headers: bool = False,
        include_body: bool = False,
        exclude_paths: set[str] | None = None,
        exclude_health_checks: bool = True,
        max_body_size: int = 1024,
        formatter: Callable[[dict], str] | None = None,
    ):
        """
        Initialize the request logging middleware.

        Args:
            app: The ASGI application
            config: Request logging configuration object
            logger: Logger instance to use (defaults to 'zenith.requests')
            level: Log level for request logs
            include_headers: Whether to log request/response headers
            include_body: Whether to log request/response body
            exclude_paths: Set of paths to exclude from logging
            exclude_health_checks: Whether to exclude health check endpoints
            max_body_size: Maximum body size to log in bytes
            formatter: Custom formatter function for log messages
        """
        self.app = app

        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.logger = config.logger
            self.level = config.level
            self.include_headers = config.include_headers
            self.include_body = config.include_body
            self.max_body_size = config.max_body_size
            self.exclude_paths = config.exclude_paths
            self.formatter = config.formatter
        else:
            self.logger = logger or logging.getLogger("zenith.requests")
            self.level = level
            self.include_headers = include_headers
            self.include_body = include_body
            self.max_body_size = max_body_size

            # Default exclude patterns
            self.exclude_paths = set(exclude_paths) if exclude_paths else set()
            if exclude_health_checks:
                self.exclude_paths.update({"/health", "/health/", "/healthz", "/ping"})

            # Default formatter
            self.formatter = formatter or self._create_default_formatter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with request logging."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if this path should be excluded
        path = scope.get("path", "")
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Record start time
        start_time = time.perf_counter()

        # Create request object to read headers/body
        request = Request(scope, receive)

        # Get request ID from scope state if available
        request_id = scope.get("state", {}).get("request_id", None)

        # Prepare request data
        request_data = await self._prepare_request_data(request)

        # Variables to capture response data
        response_status = 500
        response_headers = {}
        response_body = b""
        response_started = False

        # Wrap send to capture response data
        async def send_wrapper(message):
            nonlocal response_status, response_headers, response_body, response_started

            if message["type"] == "http.response.start":
                response_started = True
                response_status = message["status"]
                response_headers = dict(message.get("headers", []))

            elif message["type"] == "http.response.body":
                if self.include_body:
                    body_bytes = message.get("body", b"")
                    if isinstance(body_bytes, bytes):
                        response_body += body_bytes

                # Check if this is the last body message
                more_body = message.get("more_body", False)
                if not more_body:
                    # This is the end of the response, now we can log
                    await self._log_request(
                        scope,
                        request_data,
                        response_status,
                        response_headers,
                        response_body,
                        start_time,
                        request_id,
                    )

            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _log_request(
        self,
        scope: Scope,
        request_data: dict[str, Any],
        response_status: int,
        response_headers: dict[bytes, bytes],
        response_body: bytes,
        start_time: float,
        request_id: str | None,
    ):
        """Log the completed request."""
        # Calculate duration
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Prepare response data
        response_data = {
            "status_code": response_status,
            "content_type": response_headers.get(b"content-type", b"").decode(
                "latin-1"
            ),
            "content_length": response_headers.get(b"content-length", b"").decode(
                "latin-1"
            ),
        }

        if self.include_headers:
            response_data["headers"] = {
                k.decode("latin-1"): v.decode("latin-1")
                for k, v in response_headers.items()
            }

        if self.include_body and response_body:
            if len(response_body) <= self.max_body_size:
                try:
                    response_data["body"] = msgspec.json.decode(response_body)
                except (msgspec.DecodeError, UnicodeDecodeError):
                    response_data["body"] = response_body.decode(
                        "utf-8", errors="replace"
                    )[: self.max_body_size]
            else:
                response_data["body_size"] = len(response_body)
                response_data["body"] = "[Body too large for logging]"

        # Combine log data
        log_data = {
            "request_id": request_id,
            "request": request_data,
            "response": response_data,
            "duration_ms": duration_ms,
        }

        # Log the request
        message = self.formatter(log_data)
        self.logger.log(self.level, message, extra={"request_data": log_data})

        # Record metrics if available
        try:
            from zenith.monitoring.metrics import record_request_metrics

            record_request_metrics(
                method=scope.get("method", "GET"),
                path=scope.get("path", ""),
                status_code=response_status,
                duration_seconds=duration_ms / 1000.0,
            )
        except ImportError:
            # Metrics not available, skip
            pass

    async def _prepare_request_data(self, request: Request) -> dict[str, Any]:
        """Prepare request data for logging."""
        data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
        }

        if self.include_headers:
            data["headers"] = dict(request.headers)

        from zenith.core.patterns import METHODS_WITH_BODY

        if self.include_body and request.method in METHODS_WITH_BODY:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    # Try to decode as JSON for better formatting
                    try:
                        data["body"] = msgspec.json.decode(body)
                    except (msgspec.DecodeError, UnicodeDecodeError):
                        data["body"] = body.decode("utf-8", errors="replace")[
                            : self.max_body_size
                        ]
                else:
                    data["body_size"] = len(body)
                    data["body"] = "[Body too large for logging]"
            except Exception:
                data["body"] = "[Error reading body]"

        return data

    async def _prepare_response_data(
        self, response: Response, duration_ms: float
    ) -> dict[str, Any]:
        """Prepare response data for logging."""
        data = {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
        }

        if self.include_headers:
            data["headers"] = dict(response.headers)

        if self.include_body and hasattr(response, "body"):
            try:
                body = response.body
                if isinstance(body, bytes) and len(body) <= self.max_body_size:
                    # Try to decode as JSON for better formatting
                    try:
                        data["body"] = msgspec.json.decode(body)
                    except (msgspec.DecodeError, UnicodeDecodeError):
                        data["body"] = body.decode("utf-8", errors="replace")[
                            : self.max_body_size
                        ]
                else:
                    data["body_size"] = (
                        len(body) if isinstance(body, bytes) else "unknown"
                    )
                    data["body"] = "[Body too large for logging]"
            except Exception:
                data["body"] = "[Error reading body]"

        return data

    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address from request headers."""
        # Check for forwarded headers from reverse proxies
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def _create_default_formatter(self) -> Callable[[dict], str]:
        """Create the default formatter for log messages."""

        def formatter(log_data: dict[str, Any]) -> str:
            req = log_data["request"]
            resp = log_data["response"]
            duration = log_data["duration_ms"]

            return (
                f"{req['method']} {req['path']} "
                f"- {resp['status_code']} "
                f"({duration}ms) "
                f"[{req['client_ip']}]"
            )

        return formatter


def create_request_logging_middleware(
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
    include_headers: bool = False,
    include_body: bool = False,
    exclude_paths: set[str] | None = None,
    exclude_health_checks: bool = True,
    max_body_size: int = 1024,
    formatter: Callable[[dict], str] | None = None,
) -> type[RequestLoggingMiddleware]:
    """
    Factory function to create a configured request logging middleware.

    Args:
        logger: Logger instance to use (defaults to 'zenith.requests')
        level: Log level for request logs
        include_headers: Whether to log request/response headers
        include_body: Whether to log request/response body
        exclude_paths: Set of paths to exclude from logging
        exclude_health_checks: Whether to exclude health check endpoints
        max_body_size: Maximum body size to log in bytes
        formatter: Custom formatter function for log messages

    Returns:
        Configured RequestLoggingMiddleware class
    """

    def middleware_factory(app):
        return RequestLoggingMiddleware(
            app=app,
            logger=logger,
            level=level,
            include_headers=include_headers,
            include_body=include_body,
            exclude_paths=exclude_paths,
            exclude_health_checks=exclude_health_checks,
            max_body_size=max_body_size,
            formatter=formatter,
        )

    return middleware_factory


def setup_structured_logging(
    level: int = logging.INFO,
    format_json: bool = False,
    include_timestamp: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Global log level
        format_json: Whether to use JSON formatting
        include_timestamp: Whether to include timestamps
    """
    # Configure root logger
    logging.basicConfig(level=level)

    # Create structured formatter
    if format_json:
        formatter = JsonFormatter(include_timestamp=include_timestamp)
    else:
        formatter = StructuredFormatter(include_timestamp=include_timestamp)

    # Configure Zenith loggers
    for logger_name in ["zenith.requests", "zenith.auth", "zenith.jobs"]:
        logger = logging.getLogger(logger_name)
        if logger.handlers:
            for handler in logger.handlers:
                handler.setFormatter(formatter)


class StructuredFormatter(logging.Formatter):
    """Structured log formatter for human-readable output."""

    def __init__(self, include_timestamp: bool = True):
        self.include_timestamp = include_timestamp

        if include_timestamp:
            fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        else:
            fmt = "[%(levelname)s] %(name)s: %(message)s"

        super().__init__(fmt, datefmt="%Y-%m-%d %H:%M:%S")


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging systems."""

    def __init__(self, include_timestamp: bool = True):
        self.include_timestamp = include_timestamp
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if self.include_timestamp:
            log_entry["timestamp"] = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")

        # Include extra data if present
        if hasattr(record, "request_data"):
            log_entry.update(record.request_data)

        return msgspec.json.encode(log_entry).decode()
