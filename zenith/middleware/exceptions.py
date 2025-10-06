"""
Exception handling middleware for Zenith applications.

Provides comprehensive error handling with proper HTTP status codes,
logging, and user-friendly error responses.
"""

import logging
import re
import traceback
from collections.abc import Callable

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from zenith.exceptions import ZenithException

# Get logger
logger = logging.getLogger("zenith.exceptions")


def _enhance_async_error_message(
    exc: Exception, tb: traceback.TracebackException
) -> str | None:
    """
    Enhance error messages for common async patterns that cause confusion.

    Addresses WealthScope feedback about cryptic async context errors.
    Returns enhanced error message or None if no enhancement is needed.
    """
    exc_str = str(exc)
    exc_type = type(exc).__name__

    # Pattern 1: Variable naming conflicts in async context managers
    if (
        exc_type == "UnboundLocalError"
        and "cannot access local variable" in exc_str
        and "where it is not associated" in exc_str
    ):
        # Extract variable name from error
        var_match = re.search(r"cannot access local variable '(\w+)'", exc_str)
        if var_match:
            var_name = var_match.group(1)

            # Look through traceback for async context manager patterns
            for frame in tb.stack:
                if frame.filename and frame.lineno:
                    try:
                        from pathlib import Path

                        with Path(frame.filename).open() as f:
                            lines = f.readlines()
                            if frame.lineno <= len(lines):
                                line = lines[frame.lineno - 1].strip()

                                # Check for common problematic patterns
                                if (
                                    f"async with {var_name}.session() as {var_name}:"
                                    in line
                                ):
                                    return (
                                        f"AsyncContextError: Variable name conflict in database session context.\n"
                                        f"Found: {line}\n"
                                        f"Problem: Using '{var_name}' as both the source and target variable creates a conflict.\n"
                                        f"Solution: Use different variable names, e.g.:\n"
                                        f"  async with {var_name}.session() as session:\n"
                                        f"Or better yet, use dependency injection:\n"
                                        f"  def your_function(session: AsyncSession = Session):\n"
                                        f"File: {frame.filename}, Line: {frame.lineno}"
                                    )
                    except (OSError, IndexError):
                        pass

    # Pattern 2: Event loop context errors
    if "got Future" in exc_str and "attached to a different loop" in exc_str:
        return (
            f"AsyncLoopError: Database session created in wrong event loop context.\n"
            f"Problem: {exc_str}\n"
            f"Common causes:\n"
            f"  • Creating database engine/session at module level\n"
            f"  • Reusing sessions across requests\n"
            f"Solutions:\n"
            f"  • Use dependency injection: session: AsyncSession = Session\n"
            f"  • Create sessions within request context\n"
            f"  • Avoid module-level async database operations"
        )

    # Pattern 3: Session not in async context
    if "SQLAlchemy" in exc_str and ("await" in exc_str or "async" in exc_str):
        if "not within an async" in exc_str or "not awaitable" in exc_str:
            return (
                f"AsyncSQLAlchemyError: Database operation not properly awaited.\n"
                f"Problem: {exc_str}\n"
                f"Solutions:\n"
                f"  • Use 'await db.execute()' instead of 'db.execute()'\n"
                f"  • Use 'await db.commit()' instead of 'db.commit()'\n"
                f"  • Use 'await db.refresh(obj)' instead of 'db.refresh(obj)'\n"
                f"  • Ensure you're using AsyncSession, not regular Session"
            )

    return None


class ExceptionHandlerMiddleware:
    """
    Comprehensive exception handling middleware.

    Features:
    - Catches all unhandled exceptions
    - Provides proper HTTP status codes
    - Logs errors with full traceback
    - Returns user-friendly error responses
    - Supports custom exception handlers
    - Hides internal errors in production

    Example:
        from zenith.middleware import ExceptionHandlerMiddleware

        app = Zenith(middleware=[
            ExceptionHandlerMiddleware(debug=False)
        ])
    """

    def __init__(
        self,
        app: ASGIApp,
        debug: bool = False,
        handlers: dict[type, Callable] | None = None,
    ):
        self.app = app
        self.debug = debug
        self.handlers = handlers or {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default exception handlers."""

        # Zenith framework exceptions
        self.handlers[ZenithException] = self._handle_zenith_exception

        # Pydantic validation errors
        self.handlers[ValidationError] = self._handle_validation_error

        # Generic exceptions
        self.handlers[ValueError] = self._handle_value_error
        self.handlers[TypeError] = self._handle_type_error
        self.handlers[KeyError] = self._handle_key_error
        self.handlers[FileNotFoundError] = self._handle_file_not_found
        self.handlers[PermissionError] = self._handle_permission_error

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with exception handling."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request for exception handling
        request = Request(scope, receive)
        response_started = False

        async def send_wrapper(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            # Log the exception
            logger.error(
                f"Exception in {request.method} {request.url.path}: {exc}",
                exc_info=True,
            )

            # Don't send response if it was already started
            if not response_started:
                response = await self._handle_exception(request, exc)
                await response(scope, receive, send)
            else:
                # If response was already started, we can't send our error response
                # This is a limitation of the ASGI protocol
                logger.error("Cannot send error response - response already started")
                raise

    async def _handle_exception(self, request: Request, exc: Exception) -> Response:
        """Handle a specific exception."""

        # Check for registered handlers
        for exc_type, handler in self.handlers.items():
            if isinstance(exc, exc_type):
                return await handler(request, exc)

        # Default handler for unhandled exceptions
        return await self._handle_generic_exception(request, exc)

    async def _handle_zenith_exception(
        self, request: Request, exc: ZenithException
    ) -> Response:
        """Handle Zenith framework exceptions."""

        # Use the built-in to_response method for consistent API format
        if hasattr(exc, "to_response"):
            return exc.to_response()

        # Fallback for exceptions that don't have to_response method
        error_response = {
            "detail": getattr(exc, "detail", str(exc)),
        }

        # Add error code if available
        error_code = getattr(exc, "error_code", None)
        if error_code:
            error_response["error_code"] = error_code

        # Add details in debug mode or for client errors (4xx)
        details = getattr(exc, "details", None)
        if (self.debug or exc.status_code < 500) and details:
            error_response["details"] = details

        return JSONResponse(content=error_response, status_code=exc.status_code)

    async def _handle_validation_error(
        self, request: Request, exc: ValidationError
    ) -> Response:
        """Handle Pydantic validation errors."""

        error_response = {
            "error": "ValidationError",
            "message": "Request validation failed",
            "status_code": 422,
            "details": exc.errors(),
        }

        return JSONResponse(content=error_response, status_code=422)

    async def _handle_value_error(self, request: Request, exc: ValueError) -> Response:
        """Handle ValueError exceptions."""
        import traceback

        error_response = {
            "error": "ValueError",
            "message": "Invalid value provided",
            "status_code": 400,
        }

        if self.debug:
            error_response["details"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

        return JSONResponse(content=error_response, status_code=400)

    async def _handle_type_error(self, request: Request, exc: TypeError) -> Response:
        """Handle TypeError exceptions."""

        error_response = {
            "error": "TypeError",
            "message": "Type error in request",
            "status_code": 400,
        }

        if self.debug:
            error_response["details"] = str(exc)

        return JSONResponse(content=error_response, status_code=400)

    async def _handle_key_error(self, request: Request, exc: KeyError) -> Response:
        """Handle KeyError exceptions."""

        error_response = {
            "error": "KeyError",
            "message": "Internal server error: missing key",
            "status_code": 500,
        }

        if self.debug:
            error_response["details"] = f"Missing key: {exc!s}"

        return JSONResponse(content=error_response, status_code=500)

    async def _handle_file_not_found(
        self, request: Request, exc: FileNotFoundError
    ) -> Response:
        """Handle FileNotFoundError exceptions."""

        error_response = {
            "error": "FileNotFoundError",
            "message": "File not found",
            "status_code": 404,
        }

        if self.debug:
            error_response["details"] = str(exc)

        return JSONResponse(content=error_response, status_code=404)

    async def _handle_permission_error(
        self, request: Request, exc: PermissionError
    ) -> Response:
        """Handle PermissionError exceptions."""

        error_response = {
            "error": "PermissionError",
            "message": "Insufficient permissions",
            "status_code": 403,
        }

        if self.debug:
            error_response["details"] = str(exc)

        return JSONResponse(content=error_response, status_code=403)

    async def _handle_generic_exception(
        self, request: Request, exc: Exception
    ) -> Response:
        """Handle any unhandled exception."""

        error_response = {
            "error": "InternalServerError",
            "message": "An internal server error occurred",
            "status_code": 500,
        }

        # In debug mode, include exception details
        if self.debug:
            # Try to enhance async-related error messages (WealthScope improvement)
            tb = traceback.TracebackException.from_exception(exc)
            enhanced_message = _enhance_async_error_message(exc, tb)

            error_response["details"] = {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "traceback": traceback.format_exc().split("\n"),
            }

            # Add enhanced message for better debugging (WealthScope request)
            if enhanced_message:
                error_response["enhanced_error"] = enhanced_message
                error_response["message"] = (
                    "Enhanced error information available in development mode"
                )
                # Also log the enhanced message for visibility
                logger.warning(f"Enhanced error context: {enhanced_message}")

        return JSONResponse(content=error_response, status_code=500)

    def add_handler(self, exc_type: type, handler: Callable):
        """Add a custom exception handler."""
        self.handlers[exc_type] = handler


def exception_middleware(
    debug: bool = False, handlers: dict[type, Callable] | None = None
):
    """
    Helper function to create exception handling middleware.

    Example:
        from zenith.middleware.exceptions import exception_middleware

        app = Zenith(middleware=[
            exception_middleware(debug=True)
        ])
    """

    def create_middleware(app: ASGIApp):
        return ExceptionHandlerMiddleware(app=app, debug=debug, handlers=handlers)

    return create_middleware
