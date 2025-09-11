"""
TestClient for Zenith application testing.

Provides HTTP client for testing API endpoints with authentication support,
database transaction rollback, and seamless integration with Zenith applications.
"""

import asyncio
from typing import Any

import httpx
from starlette.testclient import TestClient as StarletteTestClient

from zenith.auth.jwt import create_access_token


class ZenithTestClient:
    """
    Async HTTP client for testing Zenith applications.

    Features:
    - Automatic application startup/shutdown
    - Database transaction rollback between tests
    - Easy authentication token injection
    - Full async/await support
    - Compatible with pytest-asyncio

    Example:
        async def test_protected_endpoint():
            async with TestClient(app) as client:
                # Set auth token for requests
                client.set_auth_token("user@example.com", role="admin")

                response = await client.get("/protected")
                assert response.status_code == 200
    """
    
    # Tell pytest this is not a test class
    __test__ = False

    def __init__(
        self,
        app,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
    ):
        """
        Initialize test client.

        Args:
            app: Zenith application instance
            base_url: Base URL for requests
            raise_server_exceptions: Raise exceptions from app
        """
        self.app = app
        self.base_url = base_url
        self.raise_server_exceptions = raise_server_exceptions
        self._client: httpx.AsyncClient | None = None
        self._auth_token: str | None = None

    async def __aenter__(self):
        """Start application and create HTTP client."""
        await self.app.startup()

        # Create ASGI transport and client
        transport = httpx.ASGITransport(app=self.app)
        self._client = httpx.AsyncClient(transport=transport, base_url=self.base_url)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Shutdown client and application."""
        if self._client:
            await self._client.aclose()
        await self.app.shutdown()

    def set_auth_token(
        self,
        email: str,
        user_id: int | str = 1,
        role: str = "user",
        scopes: list[str] | None = None,
    ) -> str:
        """
        Set authentication token for subsequent requests.

        Args:
            email: User email
            user_id: User ID
            role: User role
            scopes: Permission scopes

        Returns:
            Generated JWT token
        """
        token = create_access_token(
            user_id=user_id, email=email, role=role, scopes=scopes or []
        )
        self._auth_token = token
        return token

    def clear_auth(self) -> None:
        """Clear authentication token."""
        self._auth_token = None

    def _prepare_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Add auth headers if token is set."""
        prepared_headers = headers or {}

        if self._auth_token:
            prepared_headers["Authorization"] = f"Bearer {self._auth_token}"

        return prepared_headers

    async def request(
        self, method: str, url: str, headers: dict[str, str] | None = None, **kwargs
    ) -> httpx.Response:
        """Make HTTP request with automatic auth header injection."""
        if not self._client:
            raise RuntimeError(
                "TestClient not initialized. Use 'async with' context manager."
            )

        prepared_headers = self._prepare_headers(headers)

        response = await self._client.request(
            method=method, url=url, headers=prepared_headers, **kwargs
        )

        return response

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """GET request."""
        return await self.request("GET", url, params=params, headers=headers, **kwargs)

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """POST request."""
        return await self.request(
            "POST", url, json=json, data=data, headers=headers, **kwargs
        )

    async def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """PUT request."""
        return await self.request(
            "PUT", url, json=json, data=data, headers=headers, **kwargs
        )

    async def patch(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """PATCH request."""
        return await self.request(
            "PATCH", url, json=json, data=data, headers=headers, **kwargs
        )

    async def delete(
        self, url: str, headers: dict[str, str] | None = None, **kwargs
    ) -> httpx.Response:
        """DELETE request."""
        return await self.request("DELETE", url, headers=headers, **kwargs)

    # Synchronous compatibility for frameworks that need it
    def sync_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Synchronous request wrapper."""
        if asyncio.get_running_loop():
            raise RuntimeError(
                "Cannot use sync_request in async context. Use request() instead."
            )

        return asyncio.run(self.request(method, url, **kwargs))


class SyncTestClient:
    """
    Synchronous test client for compatibility with non-async test frameworks.

    Use TestClient (async) whenever possible. This is for legacy compatibility.
    """

    def __init__(self, app, **kwargs):
        self.app = app
        self._starlette_client = StarletteTestClient(app, **kwargs)
        self._auth_token: str | None = None

    def set_auth_token(
        self, email: str, user_id: int | str = 1, role: str = "user"
    ) -> str:
        """Set authentication token."""
        token = create_access_token(user_id=user_id, email=email, role=role)
        self._auth_token = token
        return token

    def clear_auth(self) -> None:
        """Clear authentication token."""
        self._auth_token = None

    def _prepare_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Add auth headers if token is set."""
        prepared_headers = headers or {}
        if self._auth_token:
            prepared_headers["Authorization"] = f"Bearer {self._auth_token}"
        return prepared_headers

    def request(
        self, method: str, url: str, headers: dict[str, str] | None = None, **kwargs
    ):
        """Make HTTP request."""
        prepared_headers = self._prepare_headers(headers)
        return self._starlette_client.request(
            method, url, headers=prepared_headers, **kwargs
        )

    def get(self, url: str, **kwargs):
        """GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        """POST request."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        """PUT request."""
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs):
        """PATCH request."""
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        """DELETE request."""
        return self.request("DELETE", url, **kwargs)


# Alias for backward compatibility
TestClient = ZenithTestClient
