"""
Request ID middleware for distributed tracing and logging correlation.

Adds a unique request ID to each request that can be used for
distributed tracing and log correlation across services.
"""

import uuid
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDConfig:
    """Configuration for request ID middleware."""
    
    def __init__(
        self,
        header_name: str = "X-Request-ID",
        state_key: str = "request_id",
        generator: Callable[[], str] | None = None,
    ):
        self.header_name = header_name
        self.state_key = state_key
        self.generator = generator or (lambda: str(uuid.uuid4()))


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    
    The request ID is available in the request.state.request_id and
    is also added as a response header for client correlation.
    """
    
    def __init__(
        self,
        app: Any,
        config: RequestIDConfig | None = None,
        # Individual parameters (for backward compatibility)
        header_name: str = "X-Request-ID",
        state_key: str = "request_id",
        generator: Callable[[], str] | None = None,
    ):
        """
        Initialize the RequestID middleware.
        
        Args:
            app: The ASGI application
            config: Request ID configuration object
            header_name: Name of the header to add the request ID to
            state_key: Key to store the request ID in request.state
            generator: Function to generate request IDs (defaults to uuid4)
        """
        super().__init__(app)
        
        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.header_name = config.header_name
            self.state_key = config.state_key
            self.generator = config.generator
        else:
            self.header_name = header_name
            self.state_key = state_key
            self.generator = generator or (lambda: str(uuid.uuid4()))
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add request ID."""
        # Check if request already has an ID from upstream proxy/load balancer
        request_id = request.headers.get(self.header_name)
        
        # Generate new ID if not present
        if not request_id:
            request_id = self.generator()
        
        # Store in request state for access in handlers
        setattr(request.state, self.state_key, request_id)
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers[self.header_name] = request_id
        
        return response


def get_request_id(request: Request, state_key: str = "request_id") -> str | None:
    """
    Get the request ID from the current request.
    
    Args:
        request: The current request object
        state_key: The key used to store the request ID in request.state
        
    Returns:
        The request ID string or None if not available
    """
    return getattr(request.state, state_key, None)


def create_request_id_middleware(
    header_name: str = "X-Request-ID",
    state_key: str = "request_id",
    generator: Callable[[], str] | None = None,
) -> type[RequestIDMiddleware]:
    """
    Factory function to create a configured RequestID middleware.
    
    Args:
        header_name: Name of the header to add the request ID to
        state_key: Key to store the request ID in request.state  
        generator: Function to generate request IDs (defaults to uuid4)
        
    Returns:
        Configured RequestIDMiddleware class
    """
    def middleware_factory(app):
        return RequestIDMiddleware(
            app=app,
            header_name=header_name,
            state_key=state_key,
            generator=generator,
        )
    
    return middleware_factory