"""
Unit tests for middleware components.

Tests authentication, security, CORS, rate limiting, and exception middleware.
"""

import asyncio

import pytest

from zenith import Zenith
from zenith.auth import configure_auth
from zenith.middleware.security import SecurityConfig
from zenith.testing import TestClient


@pytest.mark.asyncio
class TestAuthenticationMiddleware:
    """Test authentication middleware functionality."""

    async def test_public_paths_bypass_auth(self):
        """Test that public paths bypass authentication."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough-for-jwt")

        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        async with TestClient(app) as client:
            # Health endpoint should be public by default
            response = await client.get("/health")
            assert response.status_code == 200

            # Custom public endpoint
            response = await client.get("/public")
            assert response.status_code == 200

    async def test_token_extraction_and_validation(self):
        """Test JWT token extraction and validation."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough-for-jwt")
        app.add_exception_handling(debug=True)

        @app.get("/protected")
        async def protected_endpoint(request):
            # Access request state directly to test middleware
            return {
                "has_token": hasattr(request.state, "auth_token"),
                "has_user": hasattr(request.state, "current_user"),
                "user": getattr(request.state, "current_user", None),
                "error": getattr(request.state, "auth_error", None),
            }

        async with TestClient(app) as client:
            # Test without token
            response = await client.get("/protected")
            assert response.status_code == 200
            data = response.json()
            assert data["has_token"]
            assert data["has_user"]
            assert data["user"] is None
            assert data["error"] is None

            # Test with valid token
            client.set_auth_token("test@example.com", user_id=123, role="admin")
            response = await client.get("/protected")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["id"] == 123
            assert data["user"]["email"] == "test@example.com"
            assert data["error"] is None

    async def test_invalid_token_handling(self):
        """Test handling of invalid JWT tokens."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough-for-jwt")
        app.add_exception_handling(debug=True)

        @app.get("/test")
        async def test_endpoint(request):
            return {
                "user": getattr(request.state, "current_user", None),
                "error": getattr(request.state, "auth_error", None),
            }

        async with TestClient(app) as client:
            # Test with malformed token
            headers = {"authorization": "Bearer invalid.jwt.token"}
            response = await client.get("/test", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["user"] is None
            assert "Invalid" in str(data.get("error", "")) or data["user"] is None


@pytest.mark.asyncio
class TestSecurityMiddleware:
    """Test security headers middleware."""

    async def test_security_headers_applied(self):
        """Test that security headers are properly applied."""
        app = Zenith(debug=True)
        app.add_security_headers(strict=False)  # Development config

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")
            assert response.status_code == 200

            # Check for security headers
            headers = response.headers
            assert "x-frame-options" in headers
            assert "x-content-type-options" in headers
            assert "x-xss-protection" in headers
            assert "referrer-policy" in headers

            # Check values match development config
            assert headers["x-frame-options"] == "SAMEORIGIN"
            assert headers["x-content-type-options"] == "nosniff"

    async def test_strict_security_config(self):
        """Test strict security configuration."""
        app = Zenith(debug=True)
        app.add_security_headers(strict=True)

        @app.get("/test")
        async def test_endpoint():
            return {"secure": True}

        async with TestClient(app, base_url="https://testserver") as client:
            response = await client.get("/test")
            headers = response.headers

            # Strict config should have HSTS
            assert "strict-transport-security" in headers
            assert "max-age=" in headers["strict-transport-security"]

            # Should have CSP
            assert "content-security-policy" in headers

    async def test_security_config_customization(self):
        """Test custom security configuration."""

        app = Zenith(debug=True)
        custom_config = SecurityConfig(
            frame_options="DENY",
            xss_protection="1; mode=block",
            csp_policy="default-src 'self'",
        )
        app.add_security_headers(config=custom_config)

        @app.get("/test")
        async def test_endpoint():
            return {"custom": True}

        async with TestClient(app) as client:
            response = await client.get("/test")
            headers = response.headers

            assert headers["x-frame-options"] == "DENY"
            assert headers["x-xss-protection"] == "1; mode=block"
            assert headers["content-security-policy"] == "default-src 'self'"


@pytest.mark.asyncio
class TestExceptionMiddleware:
    """Test exception handling middleware."""

    async def test_python_exception_handling(self):
        """Test handling of standard Python exceptions."""
        app = Zenith(debug=True)
        app.add_exception_handling(debug=True)

        @app.get("/value-error")
        async def value_error():
            raise ValueError("Test value error")

        @app.get("/type-error")
        async def type_error():
            raise TypeError("Test type error")

        @app.get("/key-error")
        async def key_error():
            data = {}
            return data["missing_key"]  # KeyError

        async with TestClient(app) as client:
            # Test ValueError
            response = await client.get("/value-error")
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "message" in data

            # Test TypeError
            response = await client.get("/type-error")
            assert response.status_code == 400
            data = response.json()
            assert "TypeError" in data["error"] or "error" in data

            # Test KeyError
            response = await client.get("/key-error")
            assert response.status_code == 500  # Internal server error for KeyError
            data = response.json()
            assert "error" in data

    async def test_custom_exception_handling(self):
        """Test handling of custom framework exceptions."""
        app = Zenith(debug=True)
        app.add_exception_handling(debug=True)

        @app.get("/not-found")
        async def not_found():
            from zenith.exceptions import NotFoundException

            raise NotFoundException("Resource not found")

        @app.get("/auth-error")
        async def auth_error():
            from zenith.exceptions import AuthenticationException

            raise AuthenticationException("Invalid credentials")

        @app.get("/forbidden")
        async def forbidden():
            from zenith.exceptions import AuthorizationException

            raise AuthorizationException("Access denied")

        async with TestClient(app) as client:
            # Test NotFoundException
            response = await client.get("/not-found")
            assert response.status_code == 404
            data = response.json()
            assert "Resource not found" in data["message"]

            # Test AuthenticationException
            response = await client.get("/auth-error")
            assert response.status_code == 401
            data = response.json()
            assert "Invalid credentials" in data["message"]

            # Test AuthorizationException
            response = await client.get("/forbidden")
            assert response.status_code == 403
            data = response.json()
            assert "Access denied" in data["message"]

    async def test_debug_vs_production_mode(self):
        """Test different error responses in debug vs production mode."""
        # Test debug mode (detailed errors)
        debug_app = Zenith(debug=True)
        debug_app.add_exception_handling(debug=True)

        @debug_app.get("/error")
        async def debug_error():
            raise ValueError("Detailed error for debugging")

        async with TestClient(debug_app) as client:
            response = await client.get("/error")
            assert response.status_code == 400
            data = response.json()
            assert "details" in data  # Should include error details
            assert "traceback" in data["details"]

        # Test production mode (minimal errors)
        prod_app = Zenith(debug=True)
        prod_app.add_exception_handling(debug=False)

        @prod_app.get("/error")
        async def prod_error():
            raise ValueError("Sensitive error information")

        async with TestClient(prod_app) as client:
            response = await client.get("/error")
            assert response.status_code == 400
            data = response.json()
            # Should not include sensitive details in production
            assert "traceback" not in data.get("details", {})


@pytest.mark.asyncio
class TestCORSMiddleware:
    """Test CORS middleware functionality."""

    async def test_cors_headers(self):
        """Test CORS headers are properly set."""
        app = Zenith(debug=True)
        app.add_cors(
            allow_origins=["http://localhost:3000", "https://example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
            allow_credentials=True,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"cors": "enabled"}

        async with TestClient(app) as client:
            # Test preflight request
            response = await client._client.options(
                "/test",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )

            assert response.status_code == 200
            headers = response.headers
            assert "access-control-allow-origin" in headers
            assert "access-control-allow-methods" in headers
            assert "access-control-allow-headers" in headers

    async def test_cors_origin_validation(self):
        """Test CORS origin validation."""
        app = Zenith(debug=True)
        app.add_cors(allow_origins=["https://allowed.com"])

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            # Test allowed origin
            response = await client._client.get(
                "/test", headers={"Origin": "https://allowed.com"}
            )
            assert response.status_code == 200

            # Test forbidden origin (should still work but without CORS headers)
            response = await client._client.get(
                "/test", headers={"Origin": "https://forbidden.com"}
            )
            assert response.status_code == 200


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.mark.slow
    async def test_rate_limiting_basic(self):
        """Test basic rate limiting functionality."""
        from zenith.middleware.rate_limit import RateLimit, RateLimitMiddleware

        app = Zenith(debug=True)
        # Add rate limiting middleware directly with no exempt IPs (including localhost)
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=[RateLimit(requests=5, window=1, per="ip")],
            exempt_ips=[],  # No exempt IPs - test localhost too!
        )
        app.add_exception_handling(debug=True)

        @app.get("/limited")
        async def limited_endpoint():
            return {"request": "processed"}

        async with TestClient(app) as client:
            # Should allow first 5 requests
            for _i in range(5):
                response = await client.get("/limited")
                assert response.status_code == 200

            # 6th request should be rate limited
            response = await client.get("/limited")
            assert response.status_code == 429  # Too Many Requests

            # Wait for window to reset
            await asyncio.sleep(1.1)

            # Should allow requests again
            response = await client.get("/limited")
            assert response.status_code == 200


class TestSecurityUtilities:
    """Test security utility functions."""

    def test_html_sanitization(self):
        """Test HTML input sanitization."""
        from zenith.middleware.security import sanitize_html_input

        # Test basic XSS prevention
        unsafe_html = '<script>alert("xss")</script>Hello'
        safe_html = sanitize_html_input(unsafe_html)
        assert "<script>" not in safe_html
        assert "&lt;script&gt;" in safe_html
        assert "Hello" in safe_html

        # Test multiple dangerous tags
        unsafe_html = '<img src="x" onerror="alert(1)"><div>Safe content</div>'
        safe_html = sanitize_html_input(unsafe_html)
        # The tags should be escaped, making them safe even though the text "onerror" is still present
        assert "&lt;img" in safe_html
        assert "&lt;div&gt;" in safe_html
        assert "Safe content" in safe_html
        # Verify it's been HTML escaped (no raw < or > characters)
        assert "<img" not in safe_html
        assert "<div>" not in safe_html

        # Test empty input
        assert sanitize_html_input("") == ""
        assert sanitize_html_input(None) == ""

    def test_url_validation(self):
        """Test URL validation for SSRF prevention."""
        from zenith.middleware.security import validate_url

        # Valid URLs
        assert validate_url("https://example.com")
        assert validate_url("http://example.com/path")
        assert validate_url("https://api.example.com/v1/data")

        # Invalid schemes
        assert not validate_url("javascript:alert(1)")
        assert not validate_url("data:text/html,<script>alert(1)</script>")
        assert not validate_url("file:///etc/passwd")

        # Local/private addresses
        assert not validate_url("http://localhost/admin")
        assert not validate_url("http://127.0.0.1/api")
        assert not validate_url("http://192.168.1.1/config")
        assert not validate_url("http://10.0.0.1/internal")

        # Edge cases
        assert not validate_url("")
        assert not validate_url("not-a-url")

    def test_secure_token_generation(self):
        """Test cryptographically secure token generation."""
        from zenith.middleware.security import (
            constant_time_compare,
            generate_secure_token,
        )

        # Test token generation
        token1 = generate_secure_token(32)
        token2 = generate_secure_token(32)

        assert len(token1) > 40  # Base64 encoded should be longer
        assert len(token2) > 40
        assert token1 != token2  # Should be unique

        # Test different lengths
        short_token = generate_secure_token(16)
        long_token = generate_secure_token(64)
        assert len(short_token) < len(long_token)

        # Test constant time comparison
        secret = "super-secret-value"
        assert constant_time_compare(secret, secret)
        assert not constant_time_compare(secret, "wrong-value")
        assert constant_time_compare("", "")


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
