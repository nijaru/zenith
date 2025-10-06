"""
Main Zenith class - the entry point for creating Zenith applications.

Combines the power of:
- FastAPI-style routing and dependency injection
- Service-based architecture for business logic
- Modern Python patterns and developer experience
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from uvicorn import run

from zenith.core.application import Application
from zenith.core.config import Config
from zenith.core.routing import Router
from zenith.mixins import DocsMixin, MiddlewareMixin, RoutingMixin, ServicesMixin


class Zenith(MiddlewareMixin, RoutingMixin, DocsMixin, ServicesMixin):
    """
    Main Zenith application class.

    The high-level API for creating Zenith applications with:
    - FastAPI-style decorators and dependency injection
    - Service-based architecture for business logic
    - Production-ready middleware and tooling
    - Automatic database optimizations and session management

    Args:
        testing: Enable testing mode to disable rate limiting and strict CORS.
                Also enabled by ZENITH_TESTING environment variable.

    Example:
        app = Zenith()

        # For testing
        app = Zenith(testing=True)

        @app.get("/items/{id}")
        async def get_item(id: int, items: ItemService = Inject(ItemService)) -> dict:
            return await items.get_item(id)
    """

    class _DatabaseSessionMiddleware:
        """Built-in database session middleware for automatic request-scoped connection reuse."""

        def __init__(self, app, database):
            self.app = app
            self.database = database

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            # Automatically provide request-scoped database session
            async with self.database.request_scoped_session(scope) as session:
                # Also set in container context for ZenithModel seamless access
                from zenith.core.container import set_current_db_session

                set_current_db_session(session)
                try:
                    await self.app(scope, receive, send)
                finally:
                    # Clean up context
                    set_current_db_session(None)

    def __init__(
        self,
        config: Config | None = None,
        middleware: list[Middleware] | None = None,
        debug: bool | None = None,
        enable_optimizations: bool = True,
        # New parameters for easier configuration
        title: str | None = None,
        version: str = "1.0.0",
        description: str | None = None,
        # Testing mode to disable problematic middleware for test suites
        testing: bool | None = None,
    ):
        # Apply performance optimizations if enabled
        if enable_optimizations:
            try:
                from zenith.optimizations import optimize_zenith

                self._optimizations = optimize_zenith()
            except ImportError:
                self._optimizations = []
        else:
            self._optimizations = []

        # Initialize configuration
        self.config = config or Config.from_env()

        # Handle explicit debug parameter
        if debug is not None:
            self.config.debug = debug

        # Set up logger
        self.logger = logging.getLogger("zenith.application")

        # Use unified environment detection from Config
        self.environment = self.config._environment

        # Import os for environment variable access

        # Configure based on environment (unless explicitly overridden)
        if self.environment == "production":
            self.testing = testing if testing is not None else False
            if debug is None:
                self.config.debug = False
            # Skip production validation in testing mode (for test suites)
            if not self.testing:
                self._validate_production_config()
        elif self.environment == "staging":
            self.testing = testing if testing is not None else False
            if debug is None:
                self.config.debug = False
            if not self.testing:
                self._validate_production_config()
        elif self.environment == "test":
            self.testing = (
                testing if testing is not None else True
            )  # Default to True in test env
            if debug is None:
                self.config.debug = True
        else:  # development
            if testing is not None:
                # Explicit testing parameter overrides everything
                self.testing = testing
            else:
                self.testing = False  # Default to False in development
            if debug is None:
                self.config.debug = True

        if self.testing:
            self.logger.info(
                f"🧪 Testing mode enabled ({self.environment} environment)"
            )
        else:
            self.logger.info(f"🚀 Running in {self.environment} environment")

        if debug is not None:
            self.config._debug_explicitly_set = True
        else:
            self.config._debug_explicitly_set = False

        # Create core application (after environment is detected)
        self.app = Application(self.config)

        # Initialize routing
        self.routers: list[Router] = []
        self.middleware = middleware if middleware is not None else []
        # Skip essential middleware if middleware was explicitly provided (for testing/custom configs)
        self._skip_essential_middleware = middleware is not None

        # Create a new router for this app instance (not the global one)
        # This ensures test isolation and prevents route conflicts
        self._app_router = Router()
        self.include_router(self._app_router)

        # Add essential middleware with state-of-the-art defaults
        # Skip if middleware was explicitly provided (for testing/benchmarking/custom configs)
        if not self._skip_essential_middleware:
            self._add_essential_middleware()

        # Auto-setup common features
        self._setup_contexts()
        self._setup_static_files()
        self._add_health_endpoints()
        # OpenAPI endpoints are now only added when explicitly configured via add_docs()
        # self._add_openapi_endpoints()

        # Starlette app (created on demand)
        self._starlette_app = None

    def _add_essential_middleware(self) -> None:
        """Add essential middleware with performance-optimized defaults."""
        # Use performance-optimized middleware configuration by default
        from zenith.middleware import (
            CompressionMiddleware,
            ExceptionHandlerMiddleware,
            RateLimitMiddleware,
            RequestIDMiddleware,
            RequestLoggingMiddleware,
            SecurityHeadersMiddleware,
        )

        # 1. Exception handling (always first)
        self.add_middleware(ExceptionHandlerMiddleware, debug=self.config.debug)

        # 2. Request ID tracking (early for all subsequent middleware/handlers)
        self.add_middleware(RequestIDMiddleware)

        # 3. Database session reuse (automatic 15-25% DB performance improvement)
        self.add_middleware(self._DatabaseSessionMiddleware, database=self.app.database)

        # Apply performance-optimized middleware stack in order:
        # (fastest middleware first, most expensive last for maximum performance)

        # 4. Security headers (fast header additions)
        self.add_middleware(SecurityHeadersMiddleware)

        # 5. Rate limiting (fast memory/Redis operations) - Skip in testing mode
        if not self.testing:
            from zenith.middleware.rate_limit import RateLimit

            self.add_middleware(
                RateLimitMiddleware,
                default_limits=[RateLimit(requests=100, window=60, per="ip")],
            )

        # 6. Minimal logging
        if self.config.debug:
            self.add_middleware(RequestLoggingMiddleware)

        # 7. Compression last (most expensive)
        self.add_middleware(CompressionMiddleware)

    def _setup_contexts(self) -> None:
        """Auto-register common contexts."""
        # No default contexts in framework - users register their own
        pass

    def _setup_static_files(self) -> None:
        """Auto-configure static file serving with sensible defaults."""
        from pathlib import Path

        # Common static file directories to check
        static_dirs = [
            ("static", "/static"),  # Most common
            ("assets", "/assets"),  # Modern frontend
            ("public", "/public"),  # Alternative
        ]

        for dir_name, url_path in static_dirs:
            static_path = Path(dir_name)
            if static_path.exists() and static_path.is_dir():
                # Only mount if directory has files
                if any(static_path.iterdir()):
                    self.mount_static(url_path, str(static_path))
                    self.logger.info(
                        f"Auto-mounted static files: {url_path} -> {static_path}"
                    )

    def _looks_like_production(self) -> bool:
        """Detect if we're running in a production-like environment."""
        import os

        indicators = [
            # Cloud platforms
            os.getenv("KUBERNETES_SERVICE_HOST"),  # Kubernetes
            os.getenv("DYNO"),  # Heroku
            os.getenv("AWS_EXECUTION_ENV"),  # AWS Lambda
            os.getenv("GOOGLE_CLOUD_PROJECT"),  # Google Cloud
            os.getenv("WEBSITE_INSTANCE_ID"),  # Azure
            os.getenv("FLY_APP_NAME"),  # Fly.io
            os.getenv("RENDER"),  # Render
            os.getenv("RAILWAY_ENVIRONMENT"),  # Railway
            os.getenv("DETA_RUNTIME"),  # Deta
            # Container environments
            Path("/.dockerenv").exists(),  # Docker
            Path("/var/run/secrets/kubernetes.io").exists(),  # K8s
            # CI/CD environments (should not default to dev in CI)
            os.getenv("CI"),  # Generic CI
            os.getenv("GITHUB_ACTIONS"),  # GitHub Actions
            os.getenv("GITLAB_CI"),  # GitLab CI
            os.getenv("CIRCLECI"),  # CircleCI
        ]

        # Check if any production indicator is present and return
        return any(indicators)

    def _validate_production_config(self) -> None:
        """Validate that production requirements are met."""
        import os

        from zenith.exceptions import ConfigError

        # Require a proper secret key
        secret_key = os.getenv("SECRET_KEY") or self.config.secret_key

        # Check if using default secret key
        if secret_key in ("dev-secret-change-in-prod", "", None):
            raise ConfigError(
                f"SECRET_KEY must be set for {self.environment} environment.\n"
                "Generate a secure key with:\n"
                "  zen keygen                    # Print to stdout\n"
                "  zen keygen --output .env      # Save to .env file"
            )

        # Validate secret key strength
        if len(secret_key) < 32:
            raise ConfigError(
                f"SECRET_KEY must be at least 32 characters for {self.environment} environment.\n"
                f"Current length: {len(secret_key)}"
            )

    def _add_health_endpoints(self) -> None:
        """Add health check endpoints."""

        # Add built-in health endpoints
        @self._app_router.get("/health")
        async def health_check():
            """Health check endpoint."""
            from zenith.monitoring.health import health_endpoint

            return await health_endpoint(None)

        @self._app_router.get("/ready")
        async def readiness_check():
            """Readiness check endpoint."""
            from zenith.monitoring.health import readiness_endpoint

            return await readiness_endpoint(None)

        @self._app_router.get("/live")
        async def liveness_check():
            """Liveness check endpoint."""
            from zenith.monitoring.health import liveness_endpoint

            return await liveness_endpoint(None)

    def _add_openapi_endpoints(
        self,
        docs_url: str | None = None,
        redoc_url: str | None = None,
        openapi_url: str = "/openapi.json",
    ) -> None:
        """Add OpenAPI documentation endpoints."""
        from starlette.responses import HTMLResponse, JSONResponse

        from zenith.openapi import generate_openapi_spec

        # Only register OpenAPI spec endpoint
        @self._app_router.get(openapi_url)
        async def openapi_spec():
            """OpenAPI specification endpoint."""
            # Get title/version/description from config if set by add_docs()
            api_title = getattr(
                self.config, "api_title", f"{self.__class__.__name__} API"
            )
            api_version = getattr(self.config, "api_version", "1.0.0")
            api_description = getattr(
                self.config,
                "api_description",
                "API documentation generated by Zenith Framework",
            )

            # Pass the routers list, not routes
            spec = generate_openapi_spec(
                self.routers,  # Pass routers, not routes
                title=api_title,
                version=api_version,
                description=api_description,
            )
            return JSONResponse(spec)

        # Only register Swagger UI if docs_url is provided
        if docs_url:

            @self._app_router.get(docs_url)
            async def swagger_ui():
                """Swagger UI documentation."""
                html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>API Documentation</title>
                <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
                <style>
                    html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
                    *, *:before, *:after { box-sizing: inherit; }
                    body { margin:0; background: #fafafa; }
                </style>
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
                <script>
                    SwaggerUIBundle({
                        url: '/openapi.json',
                        dom_id: '#swagger-ui',
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIBundle.presets.standalone
                        ],
                        layout: "BaseLayout"
                    });
                </script>
            </body>
            </html>
            """
                return HTMLResponse(html_content)

        # Only register ReDoc if redoc_url is provided
        if redoc_url:

            @self._app_router.get(redoc_url)
            async def redoc():
                """ReDoc documentation."""
                html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>API Documentation</title>
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
                <style>
                    body { margin: 0; padding: 0; }
                </style>
            </head>
            <body>
                <redoc spec-url='/openapi.json'></redoc>
                <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
            </body>
            </html>
            """
                return HTMLResponse(html_content)

        # Add metrics endpoint (production only for security)
        if not self.config.debug:
            from starlette.responses import PlainTextResponse

            @self._app_router.get("/metrics")
            async def metrics_endpoint():
                """Prometheus metrics endpoint."""
                from zenith.monitoring.metrics import metrics_endpoint as get_metrics

                content = await get_metrics()
                return PlainTextResponse(
                    content, media_type="text/plain; version=0.0.4"
                )

    def on_event(self, event_type: str):
        """
        Decorator for registering event handlers.

        Args:
            event_type: "startup" or "shutdown"

        Example:
            @app.on_event("startup")
            async def startup_handler():
                self.logger.info("Starting up!")
        """

        def decorator(func):
            if event_type == "startup":
                self.app.add_startup_hook(func)
            elif event_type == "shutdown":
                self.app.add_shutdown_hook(func)
            else:
                raise ValueError(f"Unknown event type: {event_type}")
            return func

        return decorator

    @asynccontextmanager
    async def lifespan(self, scope):
        """ASGI lifespan handler."""
        # Startup
        await self.app.startup()
        yield
        # Shutdown
        await self.app.shutdown()

    def _build_starlette_app(self) -> Starlette:
        """Build the underlying Starlette application."""
        if self._starlette_app is not None:
            return self._starlette_app

        # Combine all routes from all routers
        routes = []
        for router in self.routers:
            starlette_router = router.build_starlette_router()
            routes.extend(starlette_router.routes)

        # Collect mount routes and sort them by specificity
        mount_routes = []
        spa_routes = []  # SPA routes (mounted at /) should go last

        # Add static mounts (for mount_static() method) - these should come before SPAs
        if hasattr(self, "_static_mounts"):
            mount_routes.extend(self._static_mounts)

        # Add mount routes (for spa() and mount() methods)
        if hasattr(self, "_mount_routes"):
            for route in self._mount_routes:
                # Put SPA routes (mounted at root) at the end
                if hasattr(route, "path") and route.path in ("/", ""):
                    spa_routes.append(route)
                else:
                    mount_routes.append(route)

        # Add routes in order: API routes, static mounts, then SPA catch-all
        routes.extend(mount_routes)
        routes.extend(spa_routes)

        # Create custom exception handlers for JSON responses
        from starlette.exceptions import HTTPException
        from starlette.requests import Request

        from zenith.web.responses import OptimizedJSONResponse

        async def not_found_handler(
            request: Request, exc: HTTPException
        ) -> OptimizedJSONResponse:
            """Return JSON for 404 errors."""
            return OptimizedJSONResponse(
                content={
                    "error": "NotFound",
                    "message": "The requested resource was not found",
                    "status_code": 404,
                    "path": str(request.url.path),
                },
                status_code=404,
            )

        async def method_not_allowed_handler(
            request: Request, exc: HTTPException
        ) -> OptimizedJSONResponse:
            """Return JSON for 405 errors."""
            return OptimizedJSONResponse(
                content={
                    "error": "MethodNotAllowed",
                    "message": f"Method {request.method} not allowed for this endpoint",
                    "status_code": 405,
                    "path": str(request.url.path),
                },
                status_code=405,
            )

        # Import exception handler for rate limiting
        from starlette.responses import JSONResponse

        from zenith.exceptions import RateLimitException

        def rate_limit_handler(request, exc):
            """Handle rate limit exceptions."""
            # Start with default headers
            headers = {
                "Retry-After": "60",  # Default retry after 60 seconds
            }

            # If the exception includes headers, use them
            if hasattr(exc, "headers") and exc.headers:
                headers.update(exc.headers)

            # Add standard rate limit headers if not present
            if "X-RateLimit-Limit" not in headers:
                # Try to extract from exception details
                if hasattr(exc, "limit"):
                    headers["X-RateLimit-Limit"] = str(exc.limit)

            if "X-RateLimit-Remaining" not in headers:
                # Set to 0 since we hit the limit
                headers["X-RateLimit-Remaining"] = "0"

            if "X-RateLimit-Reset" not in headers:
                # Calculate reset time
                import time

                retry_after = int(headers.get("Retry-After", 60))
                headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": str(exc),
                    "detail": exc.detail
                    if hasattr(exc, "detail")
                    else "Too many requests",
                },
                headers=headers,
            )

        exception_handlers = {
            404: not_found_handler,
            405: method_not_allowed_handler,
            RateLimitException: rate_limit_handler,
            429: rate_limit_handler,  # Also handle standard 429 status codes
        }

        # Create Starlette app
        self._starlette_app = Starlette(
            routes=routes,
            middleware=self.middleware,
            lifespan=self.lifespan,
            debug=self.config.debug,
            exception_handlers=exception_handlers,
        )

        return self._starlette_app

    async def __call__(self, scope, receive, send):
        """ASGI interface."""
        starlette_app = self._build_starlette_app()
        await starlette_app(scope, receive, send)

    def run(
        self,
        host: str | None = None,
        port: int | None = None,
        reload: bool = False,
        protocol: str = "auto",
        **kwargs,
    ) -> None:
        """
        Run the application with automatic protocol selection.

        Args:
            host: Host to bind to (defaults to config.host)
            port: Port to bind to (defaults to config.port)
            reload: Enable auto-reload for development
            protocol: Protocol to use ("http", "http3", "auto")
            **kwargs: Additional server options
        """
        # Smart protocol selection
        if protocol == "auto":
            # Use HTTP/3 for production (port 443) if available
            if port == 443 or self.config.port == 443:
                try:
                    import aioquic  # noqa: F401

                    protocol = "http3"
                    self.logger.info("Auto-selected HTTP/3 for production")
                except ImportError:
                    protocol = "http"
                    self.logger.info("HTTP/3 not available, using HTTP/2")
            else:
                protocol = "http"

        if protocol == "http3":
            self.run_http3(host=host, port=port, **kwargs)
        else:
            # Standard HTTP/2 with uvicorn
            run(
                self,
                host=host or self.config.host,
                port=port or self.config.port,
                reload=reload,
                **kwargs,
            )

    def run_http3(
        self,
        host: str | None = None,
        port: int | None = None,
        cert_path: str | None = None,
        key_path: str | None = None,
        enable_0rtt: bool = True,
        **kwargs,
    ) -> None:
        """
        Run the application using HTTP/3 (QUIC protocol).

        HTTP/3 Benefits:
        - 30-50% faster connection establishment
        - Better performance on lossy networks
        - No head-of-line blocking
        - Connection migration support
        - Built-in encryption

        Args:
            host: Host to bind to (defaults to config.host)
            port: Port to bind to (defaults to 443 for HTTPS)
            cert_path: Path to SSL certificate
            key_path: Path to SSL private key
            enable_0rtt: Enable 0-RTT for faster reconnection
            **kwargs: Additional HTTP/3 server options

        Raises:
            RuntimeError: If HTTP/3 support is not available
        """
        import asyncio

        try:
            from zenith.http3 import create_http3_server
        except ImportError as e:
            raise RuntimeError(
                "HTTP/3 support requires 'aioquic'. Install with: pip install zenithweb[http3]"
            ) from e

        # Use standard HTTPS port for HTTP/3
        actual_port = port or 443
        actual_host = host or self.config.host

        self.logger.info(f"Starting HTTP/3 server on {actual_host}:{actual_port}")

        # Create HTTP/3 server
        http3_server = create_http3_server(
            self,
            host=actual_host,
            port=actual_port,
            cert_path=cert_path,
            key_path=key_path,
            enable_0rtt=enable_0rtt,
            **kwargs,
        )

        # Run the server
        try:
            asyncio.run(http3_server.serve())
        except KeyboardInterrupt:
            self.logger.info("HTTP/3 server stopped by user")
        except Exception as e:
            self.logger.error(f"HTTP/3 server error: {e}")
            raise

    async def startup(self) -> None:
        """Start the application manually (for testing)."""
        await self.app.startup()

    async def shutdown(self) -> None:
        """Shutdown the application manually (for testing)."""
        await self.app.shutdown()

    def on_startup(self, func):
        """
        Decorator to register startup hooks.

        Usage:
            @app.on_startup
            async def setup_database():
                # Initialize database connection
                pass
        """
        self.app.add_startup_hook(func)
        return func

    def on_shutdown(self, func):
        """
        Decorator to register shutdown hooks.

        Usage:
            @app.on_shutdown
            async def cleanup():
                # Close database connections
                pass
        """
        self.app.add_shutdown_hook(func)
        return func

    # Service/DI Registration Methods
    def register_service(self, service_class: type, name: str | None = None) -> None:
        """
        Register a service class with the DI container.

        Args:
            service_class: The service class to register
            name: Optional name for the service (defaults to class name)

        Usage:
            app.register_service(UserService)
            app.register_service(EmailService, "email")
        """
        service_name = name or service_class.__name__
        self.app.contexts.register(service_name, service_class)
        self.logger.info(f"✅ Service registered: {service_name}")

    def register(
        self, dependency_type: type, implementation: Any = None, singleton: bool = True
    ) -> None:
        """
        Register a dependency with the DI container.

        Args:
            dependency_type: The type/interface to register
            implementation: The implementation (defaults to the type itself)
            singleton: Whether to use singleton pattern

        Usage:
            app.register(Database, MyDatabase())
            app.register(CacheInterface, RedisCache(), singleton=True)
        """
        self.app.container.register(
            dependency_type, implementation or dependency_type, singleton
        )
        self.logger.info(f"✅ Dependency registered: {dependency_type.__name__}")

    @property
    def container(self):
        """Access the dependency injection container."""
        return self.app.container

    @property
    def contexts(self):
        """Access the service registry."""
        return self.app.contexts

    # 🚀 One-liner convenience methods for better DX
    def add_auth(
        self,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        expire_minutes: int = 30,
    ) -> "Zenith":
        """
        Add JWT authentication in one line.

        Usage:
            app.add_auth()  # Uses secret from config or env
            app.add_auth("my-secret-key")
        """
        from zenith.middleware.auth import AuthenticationMiddleware

        # Use provided secret or fallback to config
        auth_secret = secret_key or self.config.secret_key
        if not auth_secret:
            raise ValueError(
                "Secret key required for authentication. Either pass secret_key parameter "
                "or set SECRET_KEY environment variable."
            )

        # Configure global JWT manager for middleware
        from zenith.auth.jwt import configure_jwt

        jwt_manager = configure_jwt(
            secret_key=auth_secret,
            algorithm=algorithm,
            access_token_expire_minutes=expire_minutes,
        )

        # Add auth middleware
        self.add_middleware(AuthenticationMiddleware)

        # Add login endpoint - DEMO ONLY - REPLACE WITH REAL AUTHENTICATION
        # Allow demo auth in debug mode OR development environment (for testing)
        if self.config.debug or self.environment == "development":
            # Only in dev mode - add a warning endpoint
            @self.post("/auth/login")
            async def dev_login_demo(credentials: dict):
                """
                DEVELOPMENT DEMO LOGIN - NOT FOR PRODUCTION!
                This endpoint is for development testing only.
                In production, implement real user authentication.
                """
                username = credentials.get("username")
                password = credentials.get("password")

                # In development only, warn about insecure demo login
                self.logger.warning(
                    "⚠️  Using DEMO authentication - NOT SECURE! "
                    "Replace with real authentication before production!"
                )

                if username == "demo" and password == "demo":
                    # Only allow specific demo credentials
                    token = jwt_manager.create_access_token(
                        user_id=999, email="demo@example.com", role="demo"
                    )
                    return {
                        "access_token": token,
                        "token_type": "bearer",
                        "expires_in": expire_minutes * 60,
                        "warning": "DEMO MODE - Not for production use!",
                    }
                else:
                    from starlette.exceptions import HTTPException

                    raise HTTPException(
                        status_code=401,
                        detail="Invalid credentials (hint: use demo/demo in dev mode)",
                    )
        else:
            # Production mode - require real implementation
            @self.post("/auth/login")
            async def login_not_implemented(credentials: dict):
                """Authentication endpoint - must be implemented."""
                from starlette.exceptions import HTTPException

                raise HTTPException(
                    status_code=501,
                    detail="Authentication not implemented. Please implement a real login handler.",
                )

        self.logger.info("✅ Authentication added - /auth/login endpoint available")
        return self

    def add_admin(self, route: str = "/admin") -> "Zenith":
        """
        Add admin interface in one line.

        Usage:
            app.add_admin()  # Mounts at /admin
            app.add_admin("/dashboard")  # Custom route
        """

        # Basic admin interface - can be enhanced with proper admin framework
        @self.get(f"{route}")
        async def admin_dashboard():
            """Simple admin dashboard - customize as needed."""
            return {
                "message": "Admin Dashboard",
                "routes": [
                    f"GET {route} - Dashboard",
                    f"GET {route}/health - System health",
                    f"GET {route}/stats - Application statistics",
                ],
            }

        @self.get(f"{route}/health")
        async def admin_health():
            """Admin health check."""
            try:
                db_healthy = await self.app.database.health_check()
                return {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "database": "connected" if db_healthy else "disconnected",
                    "version": "0.3.0",
                }
            except Exception as e:
                return {"status": "unhealthy", "error": str(e), "version": "0.3.0"}

        @self.get(f"{route}/stats")
        async def admin_stats():
            """Basic application statistics."""
            return {
                "routes_count": len(self._app_router.routes),
                "middleware_count": len(self.middleware),
                "debug_mode": self.config.debug,
            }

        self.logger.info(f"✅ Admin interface added at {route}")
        return self

    def add_docs(
        self,
        title: str | None = None,
        version: str = "1.0.0",
        description: str | None = None,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
    ) -> "Zenith":
        """
        Add OpenAPI documentation endpoints.

        Args:
            title: API title for documentation
            version: API version
            description: API description
            docs_url: URL for Swagger UI documentation
            redoc_url: URL for ReDoc documentation
            openapi_url: URL for OpenAPI JSON spec

        Returns:
            Self for method chaining
        """
        # Store API info in config for OpenAPI generation
        self.config.api_title = title or "Zenith API"
        self.config.api_version = version
        self.config.api_description = description or "API built with Zenith framework"

        # Add the OpenAPI endpoints
        self._add_openapi_endpoints(
            docs_url=docs_url, redoc_url=redoc_url, openapi_url=openapi_url
        )

        self.logger.info(
            f"📖 OpenAPI documentation enabled at {docs_url} and {redoc_url}"
        )
        return self

    def add_api(
        self,
        title: str | None = None,
        version: str = "1.0.0",
        description: str | None = None,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
    ) -> "Zenith":
        """
        Add API documentation in one line.

        Usage:
            app.add_api()  # Default OpenAPI docs
            app.add_api("My API", "1.2.0", "API for my app")
        """
        # Set API metadata
        api_title = title or "Zenith API"
        api_description = description or "API built with Zenith framework"

        # Add OpenAPI documentation
        self.add_docs(
            title=api_title,
            version=version,
            description=api_description,
            docs_url=docs_url,
            redoc_url=redoc_url,
        )

        # Add API info endpoint
        @self.get("/api/info")
        async def api_info():
            """API information endpoint."""
            return {
                "title": api_title,
                "version": version,
                "description": api_description,
                "docs_url": docs_url,
                "redoc_url": redoc_url,
            }

        self.logger.info(
            f"✅ API documentation added - {docs_url} and {redoc_url} available"
        )
        return self

    def __repr__(self) -> str:
        return f"Zenith(debug={self.config.debug})"
