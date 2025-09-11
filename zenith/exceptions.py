"""
HTTP exception handling for Zenith applications.

Provides proper error responses with appropriate status codes
and JSON formatting for API consistency.
"""


from starlette.responses import JSONResponse


class ZenithException(Exception):
    """Base exception class for Zenith framework."""
    pass


class HTTPException(ZenithException):
    """Base HTTP exception for Zenith applications."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict | None = None,
        error_code: str | None = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers or {}
        self.error_code = error_code
        super().__init__(detail)

    def to_response(self) -> JSONResponse:
        """Convert exception to JSON response."""
        content = {"detail": self.detail}
        if self.error_code:
            content["error_code"] = self.error_code

        return JSONResponse(
            content=content,
            status_code=self.status_code,
            headers=self.headers,
        )


class BadRequestException(HTTPException):
    """400 Bad Request"""
    def __init__(self, detail: str = "Bad request", **kwargs):
        super().__init__(400, detail, **kwargs)


class UnauthorizedException(HTTPException):
    """401 Unauthorized"""
    def __init__(self, detail: str = "Unauthorized", **kwargs):
        super().__init__(401, detail, **kwargs)


class ForbiddenException(HTTPException):
    """403 Forbidden"""
    def __init__(self, detail: str = "Forbidden", **kwargs):
        super().__init__(403, detail, **kwargs)


class NotFoundException(HTTPException):
    """404 Not Found"""
    def __init__(self, detail: str = "Not found", **kwargs):
        super().__init__(404, detail, **kwargs)


class ConflictException(HTTPException):
    """409 Conflict"""
    def __init__(self, detail: str = "Conflict", **kwargs):
        super().__init__(409, detail, **kwargs)


class ValidationException(HTTPException):
    """422 Validation Error"""
    def __init__(self, detail: str = "Validation error", errors: list | None = None, **kwargs):
        super().__init__(422, detail, **kwargs)
        self.errors = errors or []

    def to_response(self) -> JSONResponse:
        """Convert validation exception to JSON response."""
        content = {
            "detail": self.detail,
            "errors": self.errors
        }
        if self.error_code:
            content["error_code"] = self.error_code

        return JSONResponse(
            content=content,
            status_code=self.status_code,
            headers=self.headers,
        )


class InternalServerException(HTTPException):
    """500 Internal Server Error"""
    def __init__(self, detail: str = "Internal server error", **kwargs):
        super().__init__(500, detail, **kwargs)


class AuthenticationException(HTTPException):
    """401 Authentication Error - Alternative name for UnauthorizedException"""
    def __init__(self, detail: str = "Authentication required", **kwargs):
        super().__init__(401, detail, **kwargs)


class AuthorizationException(HTTPException):
    """403 Authorization Error - Alternative name for ForbiddenException"""
    def __init__(self, detail: str = "Insufficient permissions", **kwargs):
        super().__init__(403, detail, **kwargs)


class RateLimitException(HTTPException):
    """429 Rate Limit Exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded", **kwargs):
        super().__init__(429, detail, **kwargs)


def exception_to_http_exception(exc: Exception) -> HTTPException:
    """
    Convert common Python exceptions to HTTP exceptions.
    
    This provides sensible defaults for common errors:
    - ValueError -> 400 Bad Request
    - KeyError -> 404 Not Found  
    - PermissionError -> 403 Forbidden
    - FileNotFoundError -> 404 Not Found
    - etc.
    """
    if isinstance(exc, HTTPException):
        return exc

    # Map common Python exceptions to HTTP status codes
    exception_map = {
        ValueError: (400, "Invalid value"),
        KeyError: (404, "Resource not found"),
        FileNotFoundError: (404, "File not found"),
        PermissionError: (403, "Permission denied"),
        NotImplementedError: (501, "Not implemented"),
        TimeoutError: (408, "Request timeout"),
    }

    # Check for Pydantic validation errors
    try:
        from pydantic import ValidationError
        if isinstance(exc, ValidationError):
            errors = []
            for error in exc.errors():
                errors.append({
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                })
            return ValidationException(
                detail="Validation failed",
                errors=errors,
                error_code="validation_error"
            )
    except ImportError:
        pass

    # Map exception type to HTTP status
    exc_type = type(exc)
    if exc_type in exception_map:
        status_code, default_detail = exception_map[exc_type]
        detail = str(exc) if str(exc) else default_detail
        return HTTPException(status_code, detail, error_code=exc_type.__name__.lower())

    # Default to 500 Internal Server Error
    return InternalServerException(
        detail=str(exc) if str(exc) else "An unexpected error occurred",
        error_code="internal_error"
    )


# Convenience functions for common HTTP errors
def bad_request(detail: str = "Bad request", **kwargs) -> BadRequestException:
    """Raise 400 Bad Request."""
    raise BadRequestException(detail, **kwargs)


def unauthorized(detail: str = "Unauthorized", **kwargs) -> UnauthorizedException:
    """Raise 401 Unauthorized."""
    raise UnauthorizedException(detail, **kwargs)


def forbidden(detail: str = "Forbidden", **kwargs) -> ForbiddenException:
    """Raise 403 Forbidden."""
    raise ForbiddenException(detail, **kwargs)


def not_found(detail: str = "Not found", **kwargs) -> NotFoundException:
    """Raise 404 Not Found."""
    raise NotFoundException(detail, **kwargs)


def conflict(detail: str = "Conflict", **kwargs) -> ConflictException:
    """Raise 409 Conflict."""
    raise ConflictException(detail, **kwargs)


def validation_error(detail: str = "Validation error", errors: list | None = None, **kwargs) -> ValidationException:
    """Raise 422 Validation Error."""
    raise ValidationException(detail, errors, **kwargs)


def internal_error(detail: str = "Internal server error", **kwargs) -> InternalServerException:
    """Raise 500 Internal Server Error."""
    raise InternalServerException(detail, **kwargs)
