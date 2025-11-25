"""
HTTP client with connection pooling for external API calls.

Provides a managed httpx AsyncClient that reuses connections for better
performance when making external HTTP requests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from zenith.logging import get_logger

if TYPE_CHECKING:
    import httpx

logger = get_logger("zenith.http.client")

# Global client instance
_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    """
    Get the shared HTTP client instance.

    Returns:
        httpx.AsyncClient with connection pooling

    Raises:
        RuntimeError: If client not initialized (call init_client first)

    Example:
        from zenith.http.client import get_client

        client = await get_client()
        response = await client.get("https://api.example.com/data")
    """
    global _client
    if _client is None:
        raise RuntimeError(
            "HTTP client not initialized. Call init_client() in your app's startup, "
            "or use the http_client() context manager."
        )
    return _client


async def init_client(
    timeout: float = 30.0,
    max_connections: int = 100,
    max_keepalive_connections: int = 20,
    keepalive_expiry: float = 5.0,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """
    Initialize the shared HTTP client.

    Call this during application startup to enable connection pooling.

    Args:
        timeout: Request timeout in seconds (default 30)
        max_connections: Maximum concurrent connections (default 100)
        max_keepalive_connections: Max idle connections to keep (default 20)
        keepalive_expiry: Seconds to keep idle connections (default 5)
        **kwargs: Additional arguments passed to httpx.AsyncClient

    Returns:
        Configured httpx.AsyncClient

    Example:
        from zenith.http.client import init_client, close_client

        @app.on_event("startup")
        async def startup():
            await init_client(timeout=10.0)

        @app.on_event("shutdown")
        async def shutdown():
            await close_client()
    """
    global _client

    import httpx

    if _client is not None:
        logger.warning("HTTP client already initialized, closing existing client")
        await close_client()

    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry,
    )

    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        limits=limits,
        **kwargs,
    )

    logger.info(
        "http_client_initialized",
        timeout=timeout,
        max_connections=max_connections,
        max_keepalive=max_keepalive_connections,
    )

    return _client


async def close_client() -> None:
    """
    Close the shared HTTP client.

    Call this during application shutdown.
    """
    global _client

    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("http_client_closed")


@asynccontextmanager
async def http_client(
    timeout: float = 30.0,
    max_connections: int = 100,
    **kwargs: Any,
):
    """
    Context manager for HTTP client lifecycle.

    Use this in your app's lifespan for automatic setup/teardown.

    Example:
        from contextlib import asynccontextmanager
        from zenith.http.client import http_client, get_client

        @asynccontextmanager
        async def lifespan(app):
            async with http_client(timeout=10.0):
                yield

        # In your routes:
        @app.get("/proxy")
        async def proxy_request():
            client = await get_client()
            response = await client.get("https://api.example.com/data")
            return response.json()
    """
    await init_client(timeout=timeout, max_connections=max_connections, **kwargs)
    try:
        yield _client
    finally:
        await close_client()


class HTTPClientMixin:
    """
    Mixin for Zenith app to add HTTP client management.

    Example:
        app = Zenith()
        app.add_http_client(timeout=10.0)
    """

    _http_client: httpx.AsyncClient | None = None

    def add_http_client(
        self,
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        **kwargs: Any,
    ) -> HTTPClientMixin:
        """
        Add managed HTTP client to the application.

        The client is automatically initialized on startup and closed on shutdown.

        Args:
            timeout: Request timeout in seconds
            max_connections: Maximum concurrent connections
            max_keepalive_connections: Max idle connections to keep
            **kwargs: Additional httpx.AsyncClient arguments

        Returns:
            Self for method chaining
        """

        async def _startup():
            await init_client(
                timeout=timeout,
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                **kwargs,
            )

        async def _shutdown():
            await close_client()

        # Register hooks (works with both Application and Zenith)
        if hasattr(self, "app") and hasattr(self.app, "add_startup_hook"):
            self.app.add_startup_hook(_startup)
            self.app.add_shutdown_hook(_shutdown)
        elif hasattr(self, "add_startup_hook"):
            self.add_startup_hook(_startup)
            self.add_shutdown_hook(_shutdown)

        return self


__all__ = [
    "HTTPClientMixin",
    "close_client",
    "get_client",
    "http_client",
    "init_client",
]
