"""
Middleware configuration mixin for Zenith applications.

Contains all methods related to adding and configuring middleware.

Middleware Execution Order:
---------------------------
Middleware in Zenith follows the "onion" model - middleware added LAST executes FIRST
for requests and LAST for responses:

    Request flow:  Client -> Middleware3 -> Middleware2 -> Middleware1 -> Handler
    Response flow: Handler -> Middleware1 -> Middleware2 -> Middleware3 -> Client

Example:
    app.add_middleware(AuthMiddleware)       # Added 1st, executes 3rd
    app.add_middleware(RateLimitMiddleware)  # Added 2nd, executes 2nd
    app.add_middleware(LoggingMiddleware)    # Added 3rd, executes 1st

This means LoggingMiddleware sees all requests first and all responses last.

Best Practice Order:
1. Logging/Monitoring (add last, executes first)
2. Security Headers (add second-to-last)
3. Rate Limiting (add in middle)
4. Authentication (add in middle)
5. Business Logic Middleware (add early)
6. Error Handling (add first, executes last)

Note: Some middleware like CORS must be added early in the stack to handle
preflight requests before authentication middleware.
"""


class MiddlewareMixin:
    """Mixin for middleware configuration methods."""

    def add_middleware(self, middleware_class, **kwargs) -> None:
        """
        Add middleware to the application.

        By default, prevents duplicate middleware. Use replace=True to replace existing middleware
        of the same type, or allow_duplicates=True to explicitly allow duplicates.
        """
        from starlette.middleware import Middleware

        # Extract control flags from kwargs
        replace = kwargs.pop("replace", True)  # Default to replacing
        allow_duplicates = kwargs.pop("allow_duplicates", False)

        # For CORS middleware, validate configuration early to catch errors
        if (
            hasattr(middleware_class, "__name__")
            and middleware_class.__name__ == "CORSMiddleware"
        ):
            # Temporarily instantiate to trigger validation (this will raise if invalid)
            try:
                # Create a dummy ASGI app for validation
                def dummy_app(scope, receive, send):
                    return None

                middleware_class(dummy_app, **kwargs)
            except Exception:
                # Re-raise the validation error
                raise

        # Check for existing middleware of the same class
        existing_middleware = [mw.cls for mw in self.middleware]
        middleware_exists = middleware_class in existing_middleware

        if middleware_exists and not allow_duplicates:
            if replace:
                # Replace existing middleware with the same class
                for i, mw in enumerate(self.middleware):
                    if mw.cls == middleware_class:
                        self.middleware[i] = Middleware(middleware_class, **kwargs)
                        break
            else:
                # Raise error if duplicate middleware and not replacing
                raise ValueError(
                    f"Middleware {middleware_class.__name__} already exists. "
                    f"Use replace=True to replace it or allow_duplicates=True to add another instance."
                )
        else:
            # Add new middleware
            self.middleware.append(Middleware(middleware_class, **kwargs))

        # Invalidate cached Starlette app so it gets rebuilt with new middleware
        self._starlette_app = None

    def add_cors(
        self,
        allow_origins: list[str] | None = None,
        allow_credentials: bool = False,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        **kwargs,
    ) -> None:
        """Add CORS middleware with configuration."""
        from zenith.middleware.cors import CORSMiddleware

        self.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins or ["*"],
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            **kwargs,
        )

    def add_exception_handling(self, debug: bool | None = None, **kwargs) -> None:
        """Add exception handling middleware."""
        from zenith.middleware.exceptions import ExceptionHandlerMiddleware

        self.add_middleware(
            ExceptionHandlerMiddleware,
            debug=debug if debug is not None else self.config.debug,
            **kwargs,
        )

    def add_rate_limiting(
        self, default_limit: int = 1000, window_seconds: int = 3600, **kwargs
    ) -> None:
        """Add rate limiting middleware."""
        from zenith.middleware.rate_limit import RateLimit, RateLimitMiddleware

        # Create default limits from the provided parameters
        default_limits = [
            RateLimit(requests=default_limit, window=window_seconds, per="ip")
        ]

        self.add_middleware(
            RateLimitMiddleware,
            default_limits=default_limits,
            **kwargs,
        )

    def add_security_headers(self, config=None, strict: bool = False, **kwargs) -> None:
        """Add or replace security headers middleware."""
        from zenith.middleware.security import (
            SecurityHeadersMiddleware,
            get_development_security_config,
            get_strict_security_config,
        )

        if config is None:
            if strict:
                config = get_strict_security_config()
            else:
                config = get_development_security_config()

        # Apply any kwargs overrides
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Remove existing SecurityHeadersMiddleware if present
        from starlette.middleware import Middleware

        self.middleware = [
            m
            for m in self.middleware
            if not (isinstance(m, Middleware) and m.cls == SecurityHeadersMiddleware)
        ]

        # Add the new one with custom config
        self.add_middleware(SecurityHeadersMiddleware, config=config)

    def add_csrf_protection(
        self,
        secret_key: str | None = None,
        csrf_token_header: str = "X-CSRF-Token",
        exempt_methods: list[str] | None = None,
        **kwargs,
    ) -> None:
        """Add CSRF protection middleware."""
        from zenith.middleware.csrf import CSRFConfig, CSRFMiddleware

        if secret_key is None:
            raise ValueError("CSRF secret key is required")

        config = CSRFConfig(
            secret_key=secret_key,
            header_name=csrf_token_header,
            exempt_methods=set(exempt_methods or ["GET", "HEAD", "OPTIONS", "TRACE"]),
            **kwargs,
        )

        self.add_middleware(CSRFMiddleware, config=config)

    def add_trusted_proxies(self, trusted_proxies: list[str]) -> None:
        """Add trusted proxy middleware."""
        from zenith.middleware.security import TrustedProxyMiddleware

        self.add_middleware(TrustedProxyMiddleware, trusted_proxies=trusted_proxies)
