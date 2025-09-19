"""
Authentication dependencies for Zenith applications.

Provides dependency injection helpers for authentication and authorization
in route handlers and middleware.
"""

from typing import Any

from starlette.requests import Request


def get_current_user(request: Request) -> dict[str, Any] | None:
    """
    Dependency to get the current authenticated user.

    Returns None if no user is authenticated.
    Does not require authentication.
    """
    # Get user from request state (set by AuthenticationMiddleware)
    return getattr(request.state, "current_user", None)


def require_auth(request: Request) -> dict[str, Any]:
    """
    Dependency that requires authentication.

    Returns the current user information.
    Raises AuthenticationException if not authenticated.
    """
    user = get_current_user(request)
    if not user:
        from zenith.exceptions import AuthenticationException

        raise AuthenticationException("Authentication required")
    return user


def require_roles(*roles: str):
    """
    Dependency factory that requires specific user roles.

    Args:
        *roles: Required role names

    Returns:
        Function that validates user role and returns user info
    """

    def dependency(request: Request) -> dict[str, Any]:
        user = require_auth(request)

        # Check if user has any of the required roles
        user_role = user.get("role", "user")

        if user_role not in roles:
            from zenith.exceptions import AuthorizationException

            raise AuthorizationException(
                f"Access denied. Required roles: {', '.join(roles)}, "
                f"Current role: {user_role}"
            )

        return user

    return dependency


def require_scopes(*scopes: str):
    """
    Dependency factory that requires specific permission scopes.

    Args:
        *scopes: Required scope names

    Returns:
        Function that validates user scopes and returns user info
    """

    def dependency(request: Request) -> dict[str, Any]:
        user = require_auth(request)
        require_scopes(request, list(scopes))
        return user

    return dependency


def require_admin(request: Request) -> dict[str, Any]:
    """
    Convenience dependency that requires admin role.
    """
    return require_roles("admin")(request)


def require_moderator(request: Request) -> dict[str, Any]:
    """
    Convenience dependency that requires moderator role or higher.
    """
    return require_roles("admin", "moderator")(request)
