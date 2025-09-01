"""
CORS middleware for Zenith applications.

Handles Cross-Origin Resource Sharing (CORS) headers for browser security.
Essential for APIs that will be called from web applications.
"""

import re
from typing import List, Optional, Pattern, Set, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


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
        allow_origins: List[str] = None,
        allow_origin_regex: Optional[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 600,
    ):
        super().__init__(app)
        
        # Default allowed origins
        if allow_origins is None:
            allow_origins = []
            
        # Default allowed methods
        if allow_methods is None:
            allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
            
        # Default allowed headers
        if allow_headers is None:
            allow_headers = [
                "Accept",
                "Accept-Language", 
                "Content-Language",
                "Content-Type",
                "Authorization"
            ]
            
        # Store configuration
        self.allow_all_origins = "*" in allow_origins
        self.allow_origins: Set[str] = set(allow_origins)
        self.allow_methods: Set[str] = set(method.upper() for method in allow_methods)
        self.allow_headers: Set[str] = set(header.lower() for header in allow_headers)
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        
        # Compile origin regex if provided
        self.allow_origin_regex: Optional[Pattern] = None
        if allow_origin_regex is not None:
            self.allow_origin_regex = re.compile(allow_origin_regex)
            
        # Validation
        if self.allow_all_origins and allow_credentials:
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
        if (requested_method and 
            requested_method.upper() not in self.allow_methods):
            return Response(status_code=400, content="CORS: Method not allowed")
        
        # Validate requested headers
        if requested_headers:
            requested_headers_list = [
                header.strip().lower() 
                for header in requested_headers.split(",")
            ]
            if not all(header in self.allow_headers for header in requested_headers_list):
                return Response(status_code=400, content="CORS: Headers not allowed")
        
        # Create preflight response
        response = Response(status_code=200)
        self._add_cors_headers(response, origin, is_preflight=True)
        
        return response
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is allowed."""
        
        # Allow all origins
        if self.allow_all_origins:
            return True
            
        # Exact match in allowed origins
        if origin in self.allow_origins:
            return True
            
        # Regex match
        if self.allow_origin_regex and self.allow_origin_regex.match(origin):
            return True
            
        return False
    
    def _add_cors_headers(
        self, 
        response: Response, 
        origin: str, 
        is_preflight: bool = False
    ) -> None:
        """Add CORS headers to response."""
        
        # Set allowed origin
        response.headers["access-control-allow-origin"] = origin
        
        # Set credentials header if needed
        if self.allow_credentials:
            response.headers["access-control-allow-credentials"] = "true"
        
        # Set exposed headers
        if self.expose_headers:
            response.headers["access-control-expose-headers"] = ", ".join(self.expose_headers)
        
        # Preflight-specific headers
        if is_preflight:
            response.headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
            response.headers["access-control-allow-headers"] = ", ".join(self.allow_headers)
            response.headers["access-control-max-age"] = str(self.max_age)


def cors_middleware(
    allow_origins: List[str] = None,
    allow_origin_regex: Optional[str] = None,
    allow_methods: List[str] = None,
    allow_headers: List[str] = None,
    allow_credentials: bool = False,
    expose_headers: List[str] = None,
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