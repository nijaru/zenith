"""
Integration tests for CSRF middleware.

Tests the actual CSRF protection in realistic scenarios.
This middleware had 16% coverage and NO integration tests.
"""

import pytest
from zenith import Zenith
from zenith.middleware.csrf import CSRFConfig, CSRFMiddleware
from zenith.testing import TestClient


@pytest.mark.asyncio
class TestCSRFMiddleware:
    """Test CSRF middleware integration."""

    async def test_csrf_blocks_post_without_token(self):
        """Test that CSRF middleware blocks POST requests without valid tokens."""
        app = Zenith()

        # Add CSRF middleware
        csrf_config = CSRFConfig(
            secret_key="test-secret-key-that-is-long-enough-for-csrf-testing"
        )
        app.add_middleware(CSRFMiddleware, config=csrf_config)

        @app.post("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        async with TestClient(app) as client:
            # POST without CSRF token should be blocked
            response = await client.post("/protected", json={"data": "test"})
            assert response.status_code == 403
            assert "CSRF" in response.text

    async def test_csrf_allows_post_with_valid_token(self):
        """Test that CSRF middleware allows POST requests with valid tokens."""
        app = Zenith()

        csrf_config = CSRFConfig(
            secret_key="test-secret-key-that-is-long-enough-for-csrf-testing"
        )
        app.add_middleware(CSRFMiddleware, config=csrf_config)

        @app.get("/get-token")
        async def get_token():
            # The CSRF middleware will automatically generate and set the token
            return {"message": "Token set in cookie and header"}

        @app.post("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        async with TestClient(app) as client:
            # Get CSRF token first - middleware will set it in cookie or header
            token_response = await client.get("/get-token")

            # Try to get token from response header first, then from cookie
            csrf_token = token_response.headers.get("x-csrf-token")
            if not csrf_token:
                # Get from cookie if available
                csrf_token = None
                for cookie in token_response.cookies.jar:
                    if cookie.name == "csrf_token":
                        csrf_token = cookie.value
                        break

            assert csrf_token is not None, "CSRF token should be set by middleware"

            # POST with valid token should succeed
            response = await client.post(
                "/protected",
                json={"data": "test"},
                headers={"X-CSRF-Token": csrf_token},
            )
            assert response.status_code == 200
            assert response.json()["message"] == "success"

    async def test_csrf_allows_safe_methods(self):
        """Test that CSRF middleware allows safe methods (GET, HEAD, OPTIONS)."""
        app = Zenith()

        csrf_config = CSRFConfig(
            secret_key="test-secret-key-that-is-long-enough-for-csrf-testing"
        )
        app.add_middleware(CSRFMiddleware, config=csrf_config)

        @app.get("/safe")
        async def safe_get():
            return {"method": "GET"}

        @app.head("/safe")
        async def safe_head():
            return {"method": "HEAD"}

        @app.options("/safe")
        async def safe_options():
            return {"method": "OPTIONS"}

        async with TestClient(app) as client:
            # Safe methods should work without CSRF tokens
            get_response = await client.get("/safe")
            assert get_response.status_code == 200

            head_response = await client.head("/safe")
            assert head_response.status_code == 200

            options_response = await client.options("/safe")
            assert options_response.status_code == 200

    async def test_csrf_with_custom_header_name(self):
        """Test CSRF middleware with custom header name."""
        app = Zenith()

        csrf_config = CSRFConfig(
            secret_key="test-secret-key-that-is-long-enough-for-csrf-testing",
            header_name="X-Custom-CSRF-Token",
        )
        app.add_middleware(CSRFMiddleware, config=csrf_config)

        @app.get("/get-token")
        async def get_token():
            # The CSRF middleware will automatically generate and set the token
            return {"message": "Token set in cookie and header"}

        @app.post("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        async with TestClient(app) as client:
            # Get CSRF token first - middleware will set it in cookie or header
            token_response = await client.get("/get-token")

            # Try to get token from response header first, then from cookie
            csrf_token = token_response.headers.get("x-csrf-token")
            if not csrf_token:
                # Get from cookie if available
                csrf_token = None
                for cookie in token_response.cookies.jar:
                    if cookie.name == "csrf_token":
                        csrf_token = cookie.value
                        break

            assert csrf_token is not None, "CSRF token should be set by middleware"

            # POST with custom header should work
            response = await client.post(
                "/protected",
                json={"data": "test"},
                headers={"X-Custom-CSRF-Token": csrf_token},
            )
            assert response.status_code == 200

    async def test_csrf_blocks_invalid_token(self):
        """Test that CSRF middleware blocks requests with invalid tokens."""
        app = Zenith()

        csrf_config = CSRFConfig(
            secret_key="test-secret-key-that-is-long-enough-for-csrf-testing"
        )
        app.add_middleware(CSRFMiddleware, config=csrf_config)

        @app.post("/protected")
        async def protected_endpoint():
            return {"message": "success"}

        async with TestClient(app) as client:
            # POST with invalid token should be blocked
            response = await client.post(
                "/protected",
                json={"data": "test"},
                headers={"X-CSRF-Token": "invalid-token-12345"},
            )
            assert response.status_code == 403
            assert "CSRF" in response.text

    async def test_csrf_exempt_paths(self):
        """Test CSRF middleware exempts configured paths."""
        app = Zenith()

        csrf_config = CSRFConfig(
            secret_key="test-secret-key-that-is-long-enough-for-csrf-testing",
            exempt_paths=["/api/webhook"],
        )
        app.add_middleware(CSRFMiddleware, config=csrf_config)

        @app.post("/api/webhook")
        async def webhook():
            return {"message": "webhook received"}

        @app.post("/protected")
        async def protected():
            return {"message": "protected"}

        async with TestClient(app) as client:
            # Exempt path should work without CSRF token
            webhook_response = await client.post(
                "/api/webhook", json={"data": "webhook"}
            )
            assert webhook_response.status_code == 200

            # Protected path should still require token
            protected_response = await client.post("/protected", json={"data": "test"})
            assert protected_response.status_code == 403
