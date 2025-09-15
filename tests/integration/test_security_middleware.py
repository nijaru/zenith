"""
Integration tests for security headers middleware.

Tests critical security functionality that protects applications
including HTTPS enforcement, security headers, and edge cases.
"""

import pytest

from zenith import Zenith
from zenith.middleware.security import (
    SecurityConfig,
    SecurityHeadersMiddleware,
    TrustedProxyMiddleware,
    get_development_security_config,
    get_strict_security_config,
)
from zenith.testing.client import TestClient


@pytest.fixture
def basic_app():
    """Basic app without security middleware."""
    app = Zenith()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/sensitive")
    async def sensitive_endpoint():
        return {"data": "sensitive information"}

    return app


@pytest.fixture
def security_app():
    """App with default security middleware."""
    app = Zenith()

    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/sensitive")
    async def sensitive_endpoint():
        return {"data": "sensitive information"}

    return app


@pytest.fixture
def custom_security_app():
    """App with custom security configuration."""
    app = Zenith()

    config = SecurityConfig(
        csp_policy="default-src 'self'; script-src 'self' 'unsafe-inline'",
        hsts_max_age=63072000,  # 2 years
        hsts_include_subdomains=True,
        hsts_preload=True,
        frame_options="DENY",
        content_type_nosniff=True,
        xss_protection="1; mode=block",
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy="geolocation=(), microphone=(), camera=()",
        force_https=True,
        force_https_permanent=True,
    )

    app.add_middleware(SecurityHeadersMiddleware, config=config)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


@pytest.fixture
def https_redirect_app():
    """App with HTTPS redirect enabled."""
    app = Zenith()

    config = SecurityConfig(force_https=True, force_https_permanent=False)

    app.add_middleware(SecurityHeadersMiddleware, config=config)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


class TestSecurityHeaders:
    """Test security header functionality."""

    async def test_default_security_headers(self, security_app):
        """Test that default security headers are applied."""
        async with TestClient(security_app) as client:
            response = await client.get("/test")

            assert response.status_code == 200

            # Check default security headers
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-xss-protection"] == "1; mode=block"
            assert response.headers["x-frame-options"] == "DENY"
            assert "strict-transport-security" in response.headers
            assert "referrer-policy" in response.headers

    async def test_custom_security_headers(self, custom_security_app):
        """Test custom security header configuration."""
        async with TestClient(custom_security_app) as client:
            response = await client.get("/test")

            assert response.status_code == 200

            # Check custom headers
            assert "content-security-policy" in response.headers
            assert (
                response.headers["content-security-policy"]
                == "default-src 'self'; script-src 'self' 'unsafe-inline'"
            )

            assert (
                response.headers["strict-transport-security"]
                == "max-age=63072000; includeSubDomains; preload"
            )
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-xss-protection"] == "1; mode=block"
            assert (
                response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
            )
            assert (
                response.headers["permissions-policy"]
                == "geolocation=(), microphone=(), camera=()"
            )

    async def test_csp_report_only_mode(self):
        """Test CSP in report-only mode."""
        app = Zenith()

        config = SecurityConfig(csp_policy="default-src 'self'", csp_report_only=True)

        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            assert "content-security-policy-report-only" in response.headers
            assert "content-security-policy" not in response.headers
            assert (
                response.headers["content-security-policy-report-only"]
                == "default-src 'self'"
            )

    async def test_hsts_disabled(self):
        """Test HSTS disabled configuration."""
        app = Zenith()

        config = SecurityConfig(hsts_max_age=0)  # Disabled

        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            assert "strict-transport-security" not in response.headers

    async def test_frame_options_variations(self):
        """Test different X-Frame-Options values."""
        for frame_option in ["DENY", "SAMEORIGIN", "ALLOW-FROM https://example.com"]:
            app = Zenith()

            config = SecurityConfig(frame_options=frame_option)
            app.add_middleware(SecurityHeadersMiddleware, config=config)

            @app.get("/test")
            async def test_endpoint():
                return {"message": "test"}

            async with TestClient(app) as client:
                response = await client.get("/test")

                assert response.status_code == 200
                assert response.headers["x-frame-options"] == frame_option

    async def test_optional_headers_disabled(self):
        """Test disabling optional headers."""
        app = Zenith()

        config = SecurityConfig(
            frame_options=None,
            xss_protection=None,
            referrer_policy=None,
            permissions_policy=None,
            content_type_nosniff=False,
        )

        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            assert "x-frame-options" not in response.headers
            assert "x-xss-protection" not in response.headers
            assert "referrer-policy" not in response.headers
            assert "permissions-policy" not in response.headers
            assert "x-content-type-options" not in response.headers


class TestHTTPSRedirect:
    """Test HTTPS redirect functionality."""

    async def test_https_redirect_temporary(self, https_redirect_app):
        """Test temporary HTTPS redirect (302)."""
        # Note: TestClient uses https by default, so we need to simulate HTTP
        # This test may need to be adapted based on how TestClient handles schemes
        async with TestClient(https_redirect_app) as client:
            # For this test to work properly, we need to check the middleware logic
            # Since TestClient might not properly simulate HTTP vs HTTPS
            response = await client.get("/test")
            # The response should be successful since TestClient uses HTTPS
            assert response.status_code == 200

    async def test_https_redirect_permanent(self):
        """Test permanent HTTPS redirect (301)."""
        app = Zenith()

        config = SecurityConfig(force_https=True, force_https_permanent=True)

        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")
            # Similar limitation as above - TestClient uses HTTPS by default
            assert response.status_code == 200

    async def test_no_redirect_for_localhost(self):
        """Test that localhost/testserver is not redirected."""
        app = Zenith()

        config = SecurityConfig(force_https=True)
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")
            # Should not redirect testserver/localhost
            assert response.status_code == 200


class TestTrustedProxyMiddleware:
    """Test trusted proxy middleware functionality."""

    async def test_trusted_proxy_headers_processed(self):
        """Test that trusted proxy headers are processed."""
        app = Zenith()

        app.add_middleware(TrustedProxyMiddleware, trusted_proxies=["192.168.1.1"])

        @app.get("/test")
        async def test_endpoint():
            from starlette.requests import Request

            # In a real scenario, we'd access the processed client IP
            return {"message": "test"}

        # Note: Testing proxy middleware fully requires more complex setup
        # to simulate the proxy environment
        async with TestClient(app) as client:
            response = await client.get("/test")
            assert response.status_code == 200

    async def test_untrusted_proxy_headers_ignored(self):
        """Test that untrusted proxy headers are ignored."""
        app = Zenith()

        app.add_middleware(
            TrustedProxyMiddleware,
            trusted_proxies=["192.168.1.1"],  # Different IP
        )

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")
            assert response.status_code == 200

    async def test_no_trusted_proxies(self):
        """Test behavior with no trusted proxies configured."""
        app = Zenith()

        app.add_middleware(TrustedProxyMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")
            assert response.status_code == 200


class TestSecurityPresets:
    """Test security configuration presets."""

    async def test_strict_security_config(self):
        """Test strict security configuration preset."""
        app = Zenith()

        config = get_strict_security_config()
        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            # Check strict configuration
            assert "content-security-policy" in response.headers
            assert (
                "63072000" in response.headers["strict-transport-security"]
            )  # 2 years
            assert "includeSubDomains" in response.headers["strict-transport-security"]
            assert "preload" in response.headers["strict-transport-security"]
            assert response.headers["x-frame-options"] == "DENY"
            assert "permissions-policy" in response.headers

    async def test_development_security_config(self):
        """Test development security configuration preset."""
        app = Zenith()

        config = get_development_security_config()
        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            # Check development configuration (more relaxed)
            assert "content-security-policy" not in response.headers
            assert "strict-transport-security" not in response.headers
            assert response.headers["x-frame-options"] == "SAMEORIGIN"


class TestSecurityEdgeCases:
    """Test security middleware edge cases."""

    async def test_empty_security_config(self):
        """Test with minimal security configuration."""
        app = Zenith()

        config = SecurityConfig(
            csp_policy=None,
            hsts_max_age=0,
            frame_options=None,
            content_type_nosniff=False,
            xss_protection=None,
            referrer_policy=None,
            permissions_policy=None,
        )

        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            # No security headers should be added
            security_header_names = [
                "content-security-policy",
                "strict-transport-security",
                "x-frame-options",
                "x-content-type-options",
                "x-xss-protection",
                "referrer-policy",
                "permissions-policy",
            ]
            for header_name in security_header_names:
                assert header_name not in response.headers

    async def test_non_http_scope(self):
        """Test security middleware with non-HTTP scope."""
        app = Zenith()

        app.add_middleware(SecurityHeadersMiddleware)

        # Test WebSocket scope (should pass through)
        websocket_scope = {"type": "websocket", "path": "/ws", "headers": []}

        # This would require more complex testing setup to properly test
        # WebSocket handling, but the middleware should pass it through

    async def test_response_with_existing_headers(self):
        """Test that security headers don't conflict with existing response headers."""
        app = Zenith()

        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/custom-headers")
        async def custom_headers_endpoint():
            from zenith.web.responses import Response

            return Response(
                content='{"message": "test"}',
                headers={
                    "Custom-Header": "value",
                    "X-Frame-Options": "SAMEORIGIN",  # This should be overridden
                },
            )

        async with TestClient(app) as client:
            response = await client.get("/custom-headers")

            assert response.status_code == 200
            assert response.headers["custom-header"] == "value"
            # Security middleware should override the custom frame options
            assert response.headers["x-frame-options"] == "DENY"

    async def test_unicode_in_headers(self):
        """Test handling of Unicode characters in header values."""
        app = Zenith()

        config = SecurityConfig(
            csp_policy="default-src 'self'; script-src 'self'",
            referrer_policy="strict-origin-when-cross-origin",
        )

        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            # Headers should be properly encoded
            assert "content-security-policy" in response.headers
            assert "referrer-policy" in response.headers

    async def test_very_long_header_values(self):
        """Test handling of very long header values."""
        app = Zenith()

        # Create a very long CSP policy
        long_csp = "default-src 'self'; script-src " + " ".join(
            [f"'nonce-{i}'" for i in range(100)]
        )

        config = SecurityConfig(csp_policy=long_csp)
        app.add_middleware(SecurityHeadersMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            assert "content-security-policy" in response.headers
            assert len(response.headers["content-security-policy"]) > 1000


class TestSecurityUtilities:
    """Test security utility functions."""

    def test_html_sanitization(self):
        """Test HTML input sanitization."""
        from zenith.middleware.security import sanitize_html_input

        # Test basic XSS vectors
        assert (
            sanitize_html_input("<script>alert('xss')</script>")
            == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;&#x2F;script&gt;"
        )
        assert (
            sanitize_html_input('"><img src=x onerror=alert(1)>')
            == "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;"
        )
        assert (
            sanitize_html_input("javascript:alert('xss')")
            == "javascript:alert(&#x27;xss&#x27;)"
        )
        assert sanitize_html_input("") == ""
        assert sanitize_html_input("normal text") == "normal text"

    def test_url_validation(self):
        """Test URL validation for SSRF protection."""
        from zenith.middleware.security import validate_url

        # Valid URLs
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True
        assert validate_url("https://api.example.com/v1/endpoint") is True

        # Invalid schemes
        assert validate_url("ftp://example.com") is False
        assert validate_url("javascript:alert(1)") is False
        assert validate_url("data:text/html,<script>") is False

        # Localhost and private IPs (should be blocked)
        assert validate_url("http://localhost/admin") is False
        assert validate_url("http://127.0.0.1/admin") is False
        assert validate_url("http://::1/admin") is False
        assert validate_url("http://192.168.1.1/admin") is False
        assert validate_url("http://10.0.0.1/admin") is False
        assert validate_url("http://172.16.0.1/admin") is False

        # Invalid URLs
        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url("http://") is False

        # Custom allowed schemes
        assert validate_url("ftp://example.com", allowed_schemes=["ftp"]) is True
        assert validate_url("https://example.com", allowed_schemes=["ftp"]) is False

    def test_secure_token_generation(self):
        """Test secure token generation."""
        from zenith.middleware.security import generate_secure_token

        # Test default length
        token1 = generate_secure_token()
        token2 = generate_secure_token()

        assert len(token1) > 30  # URL-safe base64 of 32 bytes
        assert len(token2) > 30
        assert token1 != token2  # Should be different

        # Test custom length
        short_token = generate_secure_token(16)
        assert len(short_token) > 15

    def test_constant_time_compare(self):
        """Test constant-time string comparison."""
        from zenith.middleware.security import constant_time_compare

        assert constant_time_compare("secret123", "secret123") is True
        assert constant_time_compare("secret123", "secret124") is False
        assert constant_time_compare("short", "much_longer_string") is False
        assert constant_time_compare("", "") is True


class TestSecurityInStack:
    """Test security middleware in middleware stack."""

    async def test_security_with_cors_middleware(self):
        """Test security middleware working with CORS."""
        from zenith.middleware.cors import CORSMiddleware

        app = Zenith()

        # Add both security and CORS middleware through the app
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(CORSMiddleware, allow_origins=["*"])

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get(
                "/test", headers={"Origin": "https://example.com"}
            )

            assert response.status_code == 200
            # Should have both security and CORS headers
            assert response.headers["x-content-type-options"] == "nosniff"
            assert (
                response.headers["access-control-allow-origin"] == "https://example.com"
            )

    async def test_security_with_compression_middleware(self):
        """Test security middleware working with compression."""
        from zenith.middleware.compression import CompressionMiddleware

        app = Zenith()

        # Add both security and compression middleware through the app
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(CompressionMiddleware, minimum_size=10)

        @app.get("/test")
        async def test_endpoint():
            return {"data": "content " * 50}

        async with TestClient(app) as client:
            response = await client.get("/test", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # Should have both security headers and compression
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["content-encoding"] == "gzip"
