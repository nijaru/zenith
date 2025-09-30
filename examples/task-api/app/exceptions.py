"""
Custom exceptions for API error handling.
"""

from typing import Any, Optional


class APIException(Exception):
    """Base exception for all API errors."""

    def __init__(
        self, message: str, status_code: int = 400, details: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(APIException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(APIException):
    """Resource conflict (duplicate, etc)."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class ValidationError(APIException):
    """Validation failed."""

    def __init__(self, message: str = "Validation failed", details: dict = None):
        super().__init__(message, status_code=422, details=details)


class PermissionError(APIException):
    """Permission denied."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class AuthenticationError(APIException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)
