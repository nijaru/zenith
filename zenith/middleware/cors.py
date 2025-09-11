"""
CORS middleware for Zenith applications.

Handles Cross-Origin Resource Sharing (CORS) headers for browser security.
Essential for APIs that will be called from web applications.
"""

import re
from re import Pattern

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class CORSConfig:
    """Configuration for CORS middleware."""
    
    def __init__(
        self,
        allow_origins: list[str] | None = None,
        allow_origin_regex: str | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = False,
        expose_headers: list[str] | None = None,
        max_age_secs: int = 600,
    ):
        self.allow_origins = allow_origins or []
        self.allow_origin_regex = allow_origin_regex
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age_secs


class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware that handles Cross-Origin Resource Sharing headers.

    Features:
    - Configurable allowed origins (exact match or patterns)
    - Configurable allowed methods and headers
    - Automatic preflight request handling
    - Credential support
    - Wildcard origin support with safety checks

    Example:
        from zenith.middleware import CORSMiddleware

        app = Zenith(middleware=[
            CORSMiddleware(
                allow_origins=["https://myapp.com", "http://localhost:3000"],
                allow_methods=["GET", "POST", "PUT", "DELETE"],
                allow_headers=["Authorization", "Content-Type"],
                allow_credentials=True
            )
        ])
    """

    def __init__(
        self,
        app: ASGIApp,
        config: CORSConfig | None = None,
        # Individual parameters (for backward compatibility)
        allow_origins: list[str] | None = None,
        allow_origin_regex: str | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = False,
        expose_headers: list[str] | None = None,
        max_age_secs: int = 600,
    ):
        super().__init__(app)

        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.allow_origins: set[str] = set(config.allow_origins)
            self.allow_methods: set[str] = {method.upper() for method in config.allow_methods}
            self.allow_headers: set[str] = {header.lower() for header in config.allow_headers}
            self.allow_credentials = config.allow_credentials
            self.expose_headers = config.expose_headers
            self.max_age = config.max_age
            
            # Compile origin regex if provided
            self.allow_origin_regex: Pattern | None = None
            if config.allow_origin_regex is not None:
                self.allow_origin_regex = re.compile(config.allow_origin_regex)
        else:
            # Use individual parameters with defaults
            origins = allow_origins or []
            methods = allow_methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
            headers = allow_headers or [
                "Accept", "Accept-Language", "Content-Language", "Content-Type", "Authorization"
            ]
            
            self.allow_origins: set[str] = set(origins)
            self.allow_methods: set[str] = {method.upper() for method in methods}
            self.allow_headers: set[str] = {header.lower() for header in headers}
            self.allow_credentials = allow_credentials
            self.expose_headers = expose_headers or []
            self.max_age = max_age_secs

            # Compile origin regex if provided
            self.allow_origin_regex: Pattern | None = None
            if allow_origin_regex is not None:
                self.allow_origin_regex = re.compile(allow_origin_regex)

        # Store computed values
        self.allow_all_origins = "*" in self.allow_origins
        self.allow_all_headers = "*" in self.allow_headers

        # Validation
        if self.allow_all_origins and self.allow_credentials:
            raise ValueError(
                "Cannot use wildcard origin '*' with credentials. "
                "Specify explicit origins when using credentials."
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle CORS for incoming requests."""

        # Get the origin header
        origin = request.headers.get("origin")

        # Handle preflight requests (OPTIONS method)
        if request.method == "OPTIONS" and origin:
            return self._handle_preflight(request, origin)

        # Process the actual request
        response = await call_next(request)

        # Add CORS headers to response
        if origin and self._is_origin_allowed(origin):
            self._add_cors_headers(response, origin)

        return response

    def _handle_preflight(self, request: Request, origin: str) -> Response:
        """Handle CORS preflight OPTIONS requests."""

        # Check if origin is allowed
        if not self._is_origin_allowed(origin):
            return Response(status_code=400, content="CORS: Origin not allowed")

        # Get requested method and headers
        requested_method = request.headers.get("access-control-request-method")
        requested_headers = request.headers.get("access-control-request-headers")

        # Validate requested method
        if requested_method and requested_method.upper() not in self.allow_methods:
            return Response(status_code=400, content="CORS: Method not allowed")

        # Validate requested headers
        if requested_headers:
            # Fast path for wildcard headers
            if not self.allow_all_headers:
                requested_headers_list = [
                    header.strip().lower() for header in requested_headers.split(",")
                ]
                if not all(
                    header in self.allow_headers for header in requested_headers_list
                ):
                    return Response(status_code=400, content="CORS: Headers not allowed")

        # Create preflight response
        response = Response(status_code=200)
        self._add_cors_headers(response, origin, is_preflight=True)

        return response

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is allowed."""

        # Allow all origins (fast path)
        if self.allow_all_origins:
            return True

        # Exact match in allowed origins (fast path)
        if origin in self.allow_origins:
            return True

        # Regex match (slower path)
        if self.allow_origin_regex:
            return bool(self.allow_origin_regex.match(origin))
            
        return False

    def _add_cors_headers(
        self, response: Response, origin: str, is_preflight: bool = False
    ) -> None:
        """Add CORS headers to response."""

        # Set allowed origin
        response.headers["access-control-allow-origin"] = origin

        # Set credentials header if needed
        if self.allow_credentials:
            response.headers["access-control-allow-credentials"] = "true"

        # Set exposed headers
        if self.expose_headers:
            response.headers["access-control-expose-headers"] = ", ".join(
                self.expose_headers
            )

        # Preflight-specific headers
        if is_preflight:
            response.headers["access-control-allow-methods"] = ", ".join(
                self.allow_methods
            )
            response.headers["access-control-allow-headers"] = ", ".join(
                self.allow_headers
            )
            response.headers["access-control-max-age"] = str(self.max_age)


def cors_middleware(
    allow_origins: list[str] | None = None,
    allow_origin_regex: str | None = None,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
    allow_credentials: bool = False,
    expose_headers: list[str] | None = None,
    max_age: int = 600,
):
    """
    Helper function to create CORS middleware with configuration.

    This provides a more convenient way to add CORS middleware:

    Example:
        from zenith.middleware.cors import cors_middleware

        app = Zenith(middleware=[
            cors_middleware(
                allow_origins=["http://localhost:3000"],
                allow_credentials=True
            )
        ])
    """

    def create_middleware(app: ASGIApp):
        return CORSMiddleware(
            app=app,
            allow_origins=allow_origins,
            allow_origin_regex=allow_origin_regex,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
            expose_headers=expose_headers,
            max_age=max_age,
        )

    return create_middleware
