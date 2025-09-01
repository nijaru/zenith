"""
Main Zenith class - the entry point for creating Zenith applications.

Combines the power of:
- FastAPI-style routing and dependency injection
- Phoenix contexts and real-time features  
- Rails-style conventions and developer experience
"""

import asyncio
from typing import List, Optional, Type, Any, Dict
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Router as StarletteRouter
from uvicorn import run

from zenith.core.application import Application
from zenith.core.config import Config
from zenith.core.routing import Router, app_router
from zenith.core.context import Context


class Zenith:
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
        config: Optional[Config] = None,
        middleware: List[Middleware] = None,
        debug: Optional[bool] = None
    ):
        # Initialize configuration
        self.config = config or Config.from_env()
        if debug is not None:
            self.config.debug = debug
        
        # Create core application
        self.app = Application(self.config)
        
        # Initialize routing
        self.routers: List[Router] = []
        self.middleware = middleware or []
        
        # Add essential middleware by default
        self._add_essential_middleware()
        
        # Add the global app router
        self.include_router(app_router)
        
        # Auto-register contexts
        self._setup_contexts()
        
        # Starlette app (created on demand)
        self._starlette_app = None
    
    def _add_essential_middleware(self) -> None:
        """Add essential middleware that every app needs."""
        # Framework doesn't add middleware by default - users configure as needed
        pass
    
    def _setup_contexts(self) -> None:
        """Auto-register common contexts."""
        # No default contexts in framework - users register their own
        pass
    
    def include_router(self, router: Router, prefix: str = "") -> None:
        """Include a router with optional prefix."""
        if prefix:
            router.prefix = prefix + router.prefix
        
        # Set app reference for dependency injection
        router._app = self.app
        
        self.routers.append(router)
    
    def register_context(self, name: str, context_class: Type[Context]) -> None:
        """Register a business context."""
        self.app.register_context(name, context_class)
    
    def register_service(self, service_type: Type, implementation: Any = None) -> None:
        """Register a service for dependency injection."""
        self.app.register_service(service_type, implementation)
    
    def add_middleware(self, middleware_class, **kwargs) -> None:
        """Add middleware to the application."""
        from starlette.middleware import Middleware
        self.middleware.append(Middleware(middleware_class, **kwargs))
    
    def add_cors(
        self,
        allow_origins: List[str] = None,
        allow_credentials: bool = False,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        **kwargs
    ) -> None:
        """Add CORS middleware with configuration."""
        from zenith.middleware.cors import CORSMiddleware
        self.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins or ["*"],
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            **kwargs
        )
    
    def add_exception_handling(self, debug: Optional[bool] = None, **kwargs) -> None:
        """Add exception handling middleware."""
        from zenith.middleware.exceptions import ExceptionHandlerMiddleware
        self.add_middleware(
            ExceptionHandlerMiddleware,
            debug=debug if debug is not None else self.config.debug,
            **kwargs
        )
    
    def add_rate_limiting(
        self,
        default_limit: int = 1000,
        window_seconds: int = 3600,
        **kwargs
    ) -> None:
        """Add rate limiting middleware."""
        from zenith.middleware.ratelimit import RateLimitMiddleware
        self.add_middleware(
            RateLimitMiddleware,
            default_limit=default_limit,
            window_seconds=window_seconds,
            **kwargs
        )
    
    def add_security_headers(
        self,
        config=None,
        strict: bool = False,
        **kwargs
    ) -> None:
        """Add security headers middleware."""
        from zenith.middleware.security import (
            SecurityHeadersMiddleware, 
            SecurityConfig,
            get_strict_security_config,
            get_development_security_config
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
        
        self.add_middleware(SecurityHeadersMiddleware, config=config)
    
    def add_csrf_protection(
        self,
        secret_key: Optional[str] = None,
        token_header: str = "X-CSRF-Token",
        safe_methods: List[str] = None,
        **kwargs
    ) -> None:
        """Add CSRF protection middleware."""
        from zenith.middleware.security import CSRFProtectionMiddleware, SecurityConfig
        
        config = SecurityConfig(
            csrf_protection=True,
            csrf_secret_key=secret_key,
            csrf_token_header=token_header,
            csrf_safe_methods=safe_methods,
            **kwargs
        )
        
        self.add_middleware(CSRFProtectionMiddleware, config=config)
    
    def add_trusted_proxies(self, trusted_proxies: List[str]) -> None:
        """Add trusted proxy middleware."""
        from zenith.middleware.security import TrustedProxyMiddleware
        self.add_middleware(TrustedProxyMiddleware, trusted_proxies=trusted_proxies)
    
    def add_docs(
        self,
        title: Optional[str] = None,
        version: str = "1.0.0", 
        description: Optional[str] = None,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
        servers: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """
        Add OpenAPI documentation routes.
        
        Args:
            title: API title (defaults to app name)
            version: API version
            description: API description
            docs_url: Swagger UI URL (set to None to disable)
            redoc_url: ReDoc URL (set to None to disable)
            openapi_url: OpenAPI spec JSON URL
            servers: Server configurations
        """
        from zenith.openapi.docs import setup_docs_routes
        
        docs_router = setup_docs_routes(
            routers=self.routers,
            title=title or "Zenith API",
            version=version,
            description=description or "API built with Zenith framework",
            docs_url=docs_url,
            redoc_url=redoc_url,
            openapi_url=openapi_url,
            servers=servers
        )
        
        self.include_router(docs_router)
    
    # Route decorators (delegate to global router)
    def get(self, path: str, **kwargs):
        """GET route decorator."""
        return app_router.get(path, **kwargs)
    
    def post(self, path: str, **kwargs):
        """POST route decorator."""
        return app_router.post(path, **kwargs)
    
    def put(self, path: str, **kwargs):
        """PUT route decorator."""
        return app_router.put(path, **kwargs)
    
    def patch(self, path: str, **kwargs):
        """PATCH route decorator."""
        return app_router.patch(path, **kwargs)
    
    def delete(self, path: str, **kwargs):
        """DELETE route decorator."""
        return app_router.delete(path, **kwargs)
    
    def route(self, path: str, methods: List[str], **kwargs):
        """Generic route decorator."""
        return app_router.route(path, methods, **kwargs)
    
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
        
        # Create Starlette app
        self._starlette_app = Starlette(
            routes=routes,
            middleware=self.middleware,
            lifespan=self.lifespan,
            debug=self.config.debug
        )
        
        return self._starlette_app
    
    async def __call__(self, scope, receive, send):
        """ASGI interface."""
        starlette_app = self._build_starlette_app()
        await starlette_app(scope, receive, send)
    
    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reload: bool = False,
        **kwargs
    ) -> None:
        """
        Run the application using Uvicorn.
        
        Args:
            host: Host to bind to (defaults to config.host)
            port: Port to bind to (defaults to config.port)
            reload: Enable auto-reload for development
            **kwargs: Additional Uvicorn options
        """
        run(
            self,
            host=host or self.config.host,
            port=port or self.config.port,
            reload=reload,
            **kwargs
        )
    
    async def startup(self) -> None:
        """Start the application manually (for testing)."""
        await self.app.startup()
    
    async def shutdown(self) -> None:
        """Shutdown the application manually (for testing)."""
        await self.app.shutdown()
    
    def __repr__(self) -> str:
        return f"Zenith(debug={self.config.debug})"


# Convenience function for quick app creation
def create_app(
    config: Optional[Config] = None,
    debug: bool = False,
    add_middleware: bool = True,
    cors: bool = True,
    rate_limiting: bool = True,
    docs: bool = True
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
                window_seconds=3600
            )
        
        # Add documentation if requested (developer experience)
        if docs:
            app.add_docs(
                title="Zenith API",
                description="API built with Zenith framework"
            )
    
    return app