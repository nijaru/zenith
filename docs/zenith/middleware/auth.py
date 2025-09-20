"""
Authentication middleware for JWT token validation.

Handles Bearer token extraction and validation, making user information
available to the dependency injection system.
"""

import logging
from typing import Any, Literal, overload

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from zenith.auth.jwt import get_jwt_manager

logger = logging.getLogger("zenith.middleware.auth")


class AuthenticationMiddleware:
    """
    JWT authentication middleware.

    Features:
    - Extracts Bearer tokens from Authorization header
    - Validates JWT tokens and makes user info available
    - Handles authentication errors gracefully
    - Optional authentication for public endpoints
    """

    def __init__(self, app: ASGIApp, public_paths: list | None = None):
        self.app = app
        self.public_paths = public_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with authentication."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get path from scope
        path = scope.get("path", "")

        # Skip auth for public paths
        if self._is_public_path(path):
            await self.app(scope, receive, send)
            return

        # Extract token from headers
        headers = dict(scope.get("headers", []))
        auth_header_bytes = headers.get(b"authorization")
        auth_header = auth_header_bytes.decode("latin-1") if auth_header_bytes else None
        token = self._extract_bearer_token(auth_header)

        # Create state if not exists
        if "state" not in scope:
            scope["state"] = {}

        # Store auth state in scope
        scope["state"]["auth_token"] = token
        scope["state"]["current_user"] = None
        scope["state"]["auth_error"] = None

        # If token provided, validate it
        if token:
            try:
                jwt_manager = get_jwt_manager()
                user_info = jwt_manager.extract_user_from_token(token)

                if user_info:
                    scope["state"]["current_user"] = user_info
                    logger.debug(f"Authenticated user {user_info['id']}")
                else:
                    scope["state"]["auth_error"] = "Invalid or expired token"
                    logger.warning("Invalid JWT token provided")

            except Exception as e:
                scope["state"]["auth_error"] = str(e)
                logger.error(f"Authentication error: {e}")

        await self.app(scope, receive, send)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no authentication required)."""
        return any(path.startswith(public_path) for public_path in self.public_paths)

    def _extract_bearer_token(self, auth_header: str | None) -> str | None:
        """Extract Bearer token from Authorization header."""
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]


@overload
def get_current_user(request: Request, required: Literal[True]) -> dict[str, Any]: ...


@overload
def get_current_user(
    request: Request, required: Literal[False] = False
) -> dict[str, Any] | None: ...


def get_current_user(request: Request, required: bool = True) -> dict[str, Any] | None:
    """
    Get current authenticated user from request state.

    Args:
        request: The incoming request
        required: Whether authentication is required

    Returns:
        User information dict or None

    Raises:
        HTTPException: If authentication is required but not provided/valid
    """
    # Check if user is already authenticated
    current_user = getattr(request.state, "current_user", None)

    if current_user:
        return current_user

    # If authentication is required but not provided
    if required:
        auth_error = getattr(request.state, "auth_error", None)

        if auth_error:
            # Invalid/expired token
            from zenith.exceptions import AuthenticationException

            raise AuthenticationException(f"Authentication failed: {auth_error}")
        else:
            # No token provided
            from zenith.exceptions import AuthenticationException

            raise AuthenticationException(
                "Authentication required. Provide a valid Bearer token."
            )

    return None


def require_scopes(request: Request, required_scopes: list) -> bool:
    """
    Check if current user has required scopes.

    Args:
        request: The incoming request
        required_scopes: List of required permission scopes

    Returns:
        True if user has all required scopes

    Raises:
        HTTPException: If user lacks required permissions
    """
    current_user = get_current_user(request, required=True)
    user_scopes = current_user.get("scopes", [])

    missing_scopes = [scope for scope in required_scopes if scope not in user_scopes]

    if missing_scopes:
        from zenith.exceptions import AuthorizationException

        raise AuthorizationException(
            f"Insufficient permissions. Missing scopes: {', '.join(missing_scopes)}"
        )

    return True


def require_role(request: Request, required_role: str) -> bool:
    """
    Check if current user has required role.

    Args:
        request: The incoming request
        required_role: Required user role

    Returns:
        True if user has required role

    Raises:
        HTTPException: If user lacks required role
    """
    current_user = get_current_user(request, required=True)
    user_role = current_user.get("role", "user")

    # Role hierarchy: admin > moderator > user
    role_hierarchy = {"admin": 3, "moderator": 2, "user": 1}

    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    if user_level < required_level:
        from zenith.exceptions import AuthorizationException

        raise AuthorizationException(
            f"Insufficient role. Required: {required_role}, Current: {user_role}"
        )

    return True
