"""
Main Zenith class - the entry point for creating Zenith applications.

Combines the power of:
- FastAPI-style routing and dependency injection
- Phoenix contexts and real-time features
- Rails-style conventions and developer experience
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from uvicorn import run

from zenith.core.application import Application
from zenith.core.config import Config
from zenith.core.context import Context
from zenith.core.routing import Router
from zenith.mixins import MiddlewareMixin, RoutingMixin, DocsMixin, ServicesMixin


class Zenith(MiddlewareMixin, RoutingMixin, DocsMixin, ServicesMixin):
    """
    Main Zenith application class.

    The high-level API for creating Zenith applications with:
    - FastAPI-style decorators and dependency injection
    - Phoenix contexts for business logic
    - Built-in real-time features via LiveView
    - Rails-style conventions and tooling

    Example:
        app = Zenith()

        @app.get("/items/{id}")
        async def get_item(id: int, items: ItemsContext = Context()) -> dict:
            return await items.get_item(id)
    """

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
        
        if debug is not None:
            self.config._debug_explicitly_set = True
        else:
            self.config._debug_explicitly_set = False

        # Auto-detect environment if not explicitly set (BEFORE creating Application)
        self._detect_environment()

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
        from zenith.performance_optimizations import PerformanceMiddlewareConfig
        from zenith.middleware import (
            SecurityHeadersMiddleware,
            RateLimitMiddleware, 
            RequestLoggingMiddleware,
            CompressionMiddleware,
            ExceptionHandlerMiddleware,
            RequestIDMiddleware,
        )
        
        # Get optimized configuration (56% better performance than default)
        config = PerformanceMiddlewareConfig.api_optimized()
        
        # 1. Exception handling (always first)
        self.add_middleware(
            ExceptionHandlerMiddleware,
            debug=self.config.debug
        )
        
        # 2. Request ID tracking (early for all subsequent middleware/handlers)
        self.add_middleware(RequestIDMiddleware)
        
        # Apply performance-optimized middleware stack in order:
        # (fastest middleware first, most expensive last for maximum performance)
        
        # 3. Security headers (fast header additions)
        self.add_middleware(SecurityHeadersMiddleware, config=config['security'])
        
        # 4. Rate limiting (fast memory/Redis operations) 
        self.add_middleware(RateLimitMiddleware, default_limits=config['rate_limits'])
        
        # 5. Minimal logging (only if needed for performance)
        if config['logging'].level <= 30:  # Only add if INFO or higher
            self.add_middleware(RequestLoggingMiddleware, config=config['logging'])
        
        # 6. Compression last (most expensive)
        self.add_middleware(CompressionMiddleware, config=config['compression'])

    def _setup_contexts(self) -> None:
        """Auto-register common contexts."""
        # No default contexts in framework - users register their own
        pass

    def _setup_static_files(self) -> None:
        """Auto-configure static file serving with sensible defaults."""
        import os
        from pathlib import Path
        
        # Common static file directories to check
        static_dirs = [
            ("static", "/static"),      # Most common
            ("assets", "/assets"),      # Modern frontend
            ("public", "/public"),      # Alternative
        ]
        
        for dir_name, url_path in static_dirs:
            static_path = Path(dir_name)
            if static_path.exists() and static_path.is_dir():
                # Only mount if directory has files
                if any(static_path.iterdir()):
                    self.mount_static(url_path, str(static_path))
                    self.logger.info(f"Auto-mounted static files: {url_path} -> {static_path}")
    
    def _detect_environment(self) -> None:
        """Auto-detect development vs production environment."""
        import os
        
        # Only auto-detect if debug wasn't explicitly set via constructor
        if not hasattr(self.config, '_debug_explicitly_set') or not self.config._debug_explicitly_set:
            
            # Check if DEBUG environment variable was explicitly set
            debug_env = os.getenv('DEBUG')
            if debug_env is not None:
                # DEBUG was explicitly set in environment
                mode = "development" if self.config.debug else "production"
                self.logger.info(f"{mode.title()} mode (DEBUG env var)")
                return
            
            # Check other common environment indicators
            env_indicators = [
                os.getenv('ENVIRONMENT', '').lower(),
                os.getenv('ENV', '').lower(), 
                os.getenv('FLASK_ENV', '').lower(),  # Common from Flask
                os.getenv('NODE_ENV', '').lower(),   # Common from Node.js
            ]
            
            is_production = any(env in ['production', 'prod'] for env in env_indicators)
            is_development = any(env in ['development', 'dev', 'debug'] for env in env_indicators)
            
            if is_production:
                self.config.debug = False
                self.logger.info("Production mode detected")
            elif is_development:
                self.config.debug = True  
                self.logger.info("Development mode detected")
            else:
                # Default to development for ease of use (override the config default)
                self.config.debug = True
                self.logger.info("Development mode (default)")
        else:
            mode = "development" if self.config.debug else "production"
            self.logger.info(f"{mode.title()} mode (explicit)")
    
    def _add_health_endpoints(self) -> None:
        """Add health check endpoints."""
        # Add built-in health endpoints
        @self._app_router.get("/health")
        async def health_check():
            """Health check endpoint."""
            from zenith.web.health import health_endpoint
            return await health_endpoint(None)
        
        @self._app_router.get("/ready") 
        async def readiness_check():
            """Readiness check endpoint."""
            from zenith.web.health import readiness_endpoint
            return await readiness_endpoint(None)
        
        @self._app_router.get("/live")
        async def liveness_check():
            """Liveness check endpoint.""" 
            from zenith.web.health import liveness_endpoint
            return await liveness_endpoint(None)
    
    def _add_openapi_endpoints(
        self, 
        docs_url: str | None = None,
        redoc_url: str | None = None,
        openapi_url: str = "/openapi.json"
    ) -> None:
        """Add OpenAPI documentation endpoints."""
        from zenith.openapi import generate_openapi_spec
        from starlette.responses import JSONResponse, HTMLResponse
        
        # Only register OpenAPI spec endpoint
        @self._app_router.get(openapi_url)
        async def openapi_spec():
            """OpenAPI specification endpoint."""
            # Collect all routes from all routers
            all_routes = []
            for router in self.routers:
                all_routes.extend(router.routes)
            
            spec = generate_openapi_spec(
                routes=all_routes,
                title=f"{self.__class__.__name__} API",
                version="1.0.0",
                description="API documentation generated by Zenith Framework"
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
                from zenith.web.metrics import metrics_endpoint as get_metrics
                content = await get_metrics()
                return PlainTextResponse(content, media_type="text/plain; version=0.0.4")


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
        if hasattr(self, '_static_mounts'):
            mount_routes.extend(self._static_mounts)
        
        # Add mount routes (for spa() and mount() methods)
        if hasattr(self, '_mount_routes'):
            for route in self._mount_routes:
                # Put SPA routes (mounted at root) at the end
                if hasattr(route, 'path') and route.path in ('/', ''):
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
        
        async def not_found_handler(request: Request, exc: HTTPException) -> OptimizedJSONResponse:
            """Return JSON for 404 errors."""
            return OptimizedJSONResponse(
                content={
                    "error": "NotFound",
                    "message": "The requested resource was not found",
                    "status_code": 404,
                    "path": str(request.url.path)
                },
                status_code=404
            )
        
        async def method_not_allowed_handler(request: Request, exc: HTTPException) -> OptimizedJSONResponse:
            """Return JSON for 405 errors."""
            return OptimizedJSONResponse(
                content={
                    "error": "MethodNotAllowed",
                    "message": f"Method {request.method} not allowed for this endpoint",
                    "status_code": 405,
                    "path": str(request.url.path)
                },
                status_code=405
            )
        
        exception_handlers = {
            404: not_found_handler,
            405: method_not_allowed_handler,
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
                    import aioquic
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
        except ImportError:
            raise RuntimeError(
                "HTTP/3 support requires 'aioquic'. Install with: pip install zenith-web[http3]"
            )
        
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

    def __repr__(self) -> str:
        return f"Zenith(debug={self.config.debug})"


# Convenience function for quick app creation
def create_app(
    config: Config | None = None,
    debug: bool = False,
    add_middleware: bool = True,
    cors: bool = True,
    rate_limiting: bool = True,
    docs: bool = True,
) -> Zenith:
    """
    Create a Zenith application with sensible defaults.

    Args:
        config: Application configuration
        debug: Enable debug mode
        add_middleware: Whether to add essential middleware
        cors: Whether to add CORS middleware
        rate_limiting: Whether to add rate limiting
        docs: Whether to add OpenAPI documentation

    Returns:
        Configured Zenith application
    """
    if config is None:
        config = Config.from_env()
        config.debug = debug

    app = Zenith(config=config)

    if add_middleware:
        # Always add exception handling (essential for production)
        app.add_exception_handling(debug=debug)

        # Add CORS if requested (usually needed for APIs)
        if cors:
            app.add_cors(
                allow_origins=["*"] if debug else [],  # Restrict in production
                allow_credentials=not debug,  # More secure in production
            )

        # Add rate limiting if requested (protect against abuse)
        if rate_limiting:
            app.add_rate_limiting(
                default_limit=10000 if debug else 1000,  # More lenient in debug
                window_seconds=3600,
            )

        # Add documentation if requested (developer experience)
        if docs:
            app.add_docs(
                title="Zenith API", description="API built with Zenith framework"
            )

    return app
