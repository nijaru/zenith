"""
Exception handling middleware for Zenith applications.

Provides comprehensive error handling with proper HTTP status codes,
logging, and user-friendly error responses.
"""

import logging
import traceback
from typing import Any, Callable, Dict, Optional, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp
from pydantic import ValidationError

# Get logger
logger = logging.getLogger("zenith.exceptions")


class ZenithException(Exception):
    """Base exception class for Zenith framework."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


class ValidationException(ZenithException):
    """Exception for validation errors."""

    def __init__(
        self, message: str = "Validation failed", details: Dict[str, Any] = None
    ):
        super().__init__(message, status_code=422, details=details)


class AuthenticationException(ZenithException):
    """Exception for authentication errors."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationException(ZenithException):
    """Exception for authorization errors."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class NotFoundException(ZenithException):
    """Exception for resource not found errors."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictException(ZenithException):
    """Exception for resource conflict errors."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class RateLimitException(ZenithException):
    """Exception for rate limiting errors."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
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
        handlers: Optional[Dict[type, Callable]] = None,
    ):
        super().__init__(app)
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
        self.handlers[KeyError] = self._handle_key_error
        self.handlers[FileNotFoundError] = self._handle_file_not_found
        self.handlers[PermissionError] = self._handle_permission_error

    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle exceptions from the application."""

        try:
            response = await call_next(request)
            return response

        except Exception as exc:
            # Log the exception
            logger.error(
                f"Exception in {request.method} {request.url.path}: {exc}",
                exc_info=True,
            )

            # Handle the exception
            return await self._handle_exception(request, exc)

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

        error_response = {
            "error": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
        }

        # Add details in debug mode or for client errors (4xx)
        if self.debug or exc.status_code < 500:
            if exc.details:
                error_response["details"] = exc.details

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

        error_response = {
            "error": "ValueError",
            "message": "Invalid value provided",
            "status_code": 400,
        }

        if self.debug:
            error_response["details"] = str(exc)

        return JSONResponse(content=error_response, status_code=400)

    async def _handle_key_error(self, request: Request, exc: KeyError) -> Response:
        """Handle KeyError exceptions."""

        error_response = {
            "error": "KeyError",
            "message": "Required field missing",
            "status_code": 400,
        }

        if self.debug:
            error_response["details"] = f"Missing key: {str(exc)}"

        return JSONResponse(content=error_response, status_code=400)

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
            error_response["details"] = {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "traceback": traceback.format_exc().split("\n"),
            }

        return JSONResponse(content=error_response, status_code=500)

    def add_handler(self, exc_type: type, handler: Callable):
        """Add a custom exception handler."""
        self.handlers[exc_type] = handler


def exception_middleware(
    debug: bool = False, handlers: Optional[Dict[type, Callable]] = None
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
