"""
Request ID middleware for distributed tracing and logging correlation.

Adds a unique request ID to each request that can be used for
distributed tracing and log correlation across services.
"""

import uuid
from collections.abc import Callable

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send


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


class RequestIDMiddleware:
    """
    Middleware that adds a unique request ID to each request.

    The request ID is available in the request.state.request_id and
    is also added as a response header for client correlation.
    """

    def __init__(
        self,
        app: ASGIApp,
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
        self.app = app

        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.header_name = config.header_name
            self.state_key = config.state_key
            self.generator = config.generator
        else:
            self.header_name = header_name
            self.state_key = state_key
            self.generator = generator or (lambda: str(uuid.uuid4()))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get or generate request ID
        headers = dict(scope.get("headers", []))
        request_id_bytes = headers.get(self.header_name.lower().encode())

        if request_id_bytes:
            request_id = request_id_bytes.decode("latin-1")
        else:
            request_id = self.generator()

        # Store in scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"][self.state_key] = request_id

        # Wrap send to add response header
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Add request ID header
                headers.append(
                    (self.header_name.lower().encode(), request_id.encode("latin-1"))
                )
                message["headers"] = headers
            await send(message)

        # Call the next app with wrapped send
        await self.app(scope, receive, send_wrapper)


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
