"""
Authentication configuration helpers for Zenith framework.

Provides simple setup functions that wire together all auth components
with sensible defaults and minimal boilerplate.
"""

import logging

from zenith.auth.jwt import configure_jwt

logger = logging.getLogger("zenith.auth.config")


def configure_auth(
    app,
    secret_key: str,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
    public_paths: list[str] | None = None,
):
    """
    Configure authentication for a Zenith application.

    This is the main setup function that configures JWT and adds
    authentication middleware with sensible defaults.

    Args:
        app: Zenith application instance
        secret_key: JWT signing secret (must be >=32 chars)
        algorithm: JWT algorithm (default: HS256)
        access_token_expire_minutes: Access token lifetime
        refresh_token_expire_days: Refresh token lifetime
        public_paths: Paths that don't require authentication

    Example:
        from zenith import Zenith
        from zenith.auth import configure_auth

        app = Zenith()
        configure_auth(app, secret_key="your-secret-key-here")

        @app.get("/protected")
        async def protected(current_user = Auth()):
            return {"user": current_user}
    """

    # Check if auth is already configured
    from zenith.middleware.auth import AuthenticationMiddleware

    for middleware in app.middleware:
        if hasattr(middleware, "cls") and middleware.cls == AuthenticationMiddleware:
            raise RuntimeError("Authentication already configured")

    # Set up default public paths
    if public_paths is None:
        public_paths = ["/docs", "/redoc", "/openapi.json", "/health", "/ping"]

    # Configure JWT manager
    jwt_manager = configure_jwt(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )

    # Add authentication middleware to the app
    # Import here to avoid circular import
    from zenith.middleware.auth import AuthenticationMiddleware

    app.add_middleware(AuthenticationMiddleware, public_paths=public_paths)
    logger.info("Authentication configured successfully")

    return jwt_manager


def auth_required(scopes: list[str] | None = None):
    """
    Decorator factory for requiring authentication on route handlers.

    This is an alternative to using Auth() dependency injection.

    Args:
        scopes: Required permission scopes

    Example:
        @app.get("/admin")
        @auth_required(scopes=["admin"])
        async def admin_endpoint():
            return {"message": "Admin access"}
    """

    def decorator(func):
        # Mark function as requiring auth
        # The middleware will check this
        func._auth_required = True
        func._auth_scopes = scopes or []
        return func

    return decorator


def optional_auth():
    """
    Decorator for endpoints with optional authentication.

    User info will be available if token is provided and valid,
    but the endpoint works without authentication too.

    Example:
        @app.get("/maybe-protected")
        @optional_auth()
        async def maybe_protected():
            return {"message": "Works with or without auth"}
    """

    def decorator(func):
        func._auth_required = False
        func._auth_optional = True
        return func

    return decorator
