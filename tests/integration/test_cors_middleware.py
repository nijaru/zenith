"""
Integration tests for CORS middleware.

Tests critical production scenarios that could break CORS functionality
including preflight handling, origin validation, and edge cases.
"""

import pytest

from zenith import Zenith
from zenith.middleware.cors import CORSConfig, CORSMiddleware
from zenith.testing.client import TestClient


@pytest.fixture
def basic_app():
    """Basic app with CORS middleware."""
    app = Zenith()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.post("/api/data")
    async def api_endpoint(data: dict):
        return {"received": data}

    return app


@pytest.fixture
def cors_app():
    """App with configured CORS middleware."""
    app = Zenith()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://example.com", "http://localhost:3000"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=True,
        expose_headers=["X-Custom-Header"],
        max_age_secs=3600
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.post("/api/data")
    async def api_endpoint(data: dict):
        return {"received": data}

    return app


@pytest.fixture
def wildcard_cors_app():
    """App with wildcard CORS (no credentials)."""
    app = Zenith()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_credentials=False
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


@pytest.fixture
def regex_cors_app():
    """App with regex origin matching."""
    app = Zenith()

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https://.*\.example\.com",
        allow_methods=["GET", "POST"]
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


class TestCORSBasicFunctionality:
    """Test basic CORS functionality."""

    async def test_simple_cors_request_allowed_origin(self, cors_app):
        """Test simple CORS request from allowed origin."""
        async with TestClient(cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://example.com"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://example.com"
            assert response.headers["access-control-allow-credentials"] == "true"
            assert "X-Custom-Header" in response.headers["access-control-expose-headers"]

    async def test_simple_cors_request_disallowed_origin(self, cors_app):
        """Test simple CORS request from disallowed origin."""
        async with TestClient(cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://evil.com"
            })

            assert response.status_code == 200
            # CORS headers should not be present for disallowed origins
            assert "access-control-allow-origin" not in response.headers
            assert "access-control-allow-credentials" not in response.headers

    async def test_no_origin_header(self, cors_app):
        """Test request without Origin header."""
        async with TestClient(cors_app) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            # No CORS headers should be present
            assert "access-control-allow-origin" not in response.headers


class TestCORSPreflightRequests:
    """Test CORS preflight handling."""

    async def test_preflight_request_allowed_origin(self, cors_app):
        """Test preflight request from allowed origin."""
        async with TestClient(cors_app) as client:
            response = await client.options("/api/data", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://example.com"
            assert response.headers["access-control-allow-credentials"] == "true"
            assert "POST" in response.headers["access-control-allow-methods"]
            assert "content-type" in response.headers["access-control-allow-headers"].lower()
            assert "authorization" in response.headers["access-control-allow-headers"].lower()
            assert response.headers["access-control-max-age"] == "3600"

    async def test_preflight_request_disallowed_origin(self, cors_app):
        """Test preflight request from disallowed origin."""
        async with TestClient(cors_app) as client:
            response = await client.options("/api/data", headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "POST"
            })

            assert response.status_code == 400
            assert "CORS: Origin not allowed" in response.text

    async def test_preflight_disallowed_method(self, cors_app):
        """Test preflight request with disallowed method."""
        async with TestClient(cors_app) as client:
            response = await client.options("/api/data", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "PATCH"  # Not in allowed methods
            })

            assert response.status_code == 400
            assert "CORS: Method not allowed" in response.text

    async def test_preflight_disallowed_headers(self, cors_app):
        """Test preflight request with disallowed headers."""
        async with TestClient(cors_app) as client:
            response = await client.options("/api/data", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Custom-Auth"  # Not in allowed headers
            })

            assert response.status_code == 400
            assert "CORS: Headers not allowed" in response.text

    async def test_preflight_with_wildcard_headers(self):
        """Test preflight with wildcard headers configuration."""
        app = Zenith()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            allow_headers=["*"]  # Wildcard headers
        )

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.options("/test", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Custom-Header,X-Another-Header"
            })

            assert response.status_code == 200
            # Should allow any headers due to wildcard


class TestCORSWildcardOrigins:
    """Test wildcard origin handling."""

    async def test_wildcard_origin_simple_request(self, wildcard_cors_app):
        """Test wildcard origin for simple request."""
        async with TestClient(wildcard_cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://anywhere.com"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://anywhere.com"
            # Should not have credentials header for wildcard
            assert "access-control-allow-credentials" not in response.headers

    async def test_wildcard_with_credentials_error(self):
        """Test that wildcard with credentials raises error."""
        app = Zenith()

        with pytest.raises(ValueError, match="Cannot use wildcard origin"):
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True  # This should raise error
            )

    async def test_wildcard_preflight_request(self, wildcard_cors_app):
        """Test wildcard origin preflight request."""
        async with TestClient(wildcard_cors_app) as client:
            response = await client.options("/test", headers={
                "Origin": "https://anywhere.com",
                "Access-Control-Request-Method": "GET"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://anywhere.com"


class TestCORSRegexOrigins:
    """Test regex origin matching."""

    async def test_regex_origin_match(self, regex_cors_app):
        """Test regex origin matching for allowed subdomain."""
        async with TestClient(regex_cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://api.example.com"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://api.example.com"

    async def test_regex_origin_no_match(self, regex_cors_app):
        """Test regex origin for non-matching origin."""
        async with TestClient(regex_cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://api.evil.com"
            })

            assert response.status_code == 200
            # No CORS headers for non-matching origin
            assert "access-control-allow-origin" not in response.headers

    async def test_regex_origin_preflight(self, regex_cors_app):
        """Test regex origin preflight request."""
        async with TestClient(regex_cors_app) as client:
            response = await client.options("/test", headers={
                "Origin": "https://cdn.example.com",
                "Access-Control-Request-Method": "GET"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://cdn.example.com"


class TestCORSEdgeCases:
    """Test CORS edge cases and potential bugs."""

    async def test_case_insensitive_method_check(self, cors_app):
        """Test that method checking is case insensitive."""
        async with TestClient(cors_app) as client:
            response = await client.options("/api/data", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "post"  # lowercase
            })

            assert response.status_code == 200

    async def test_multiple_request_headers(self, cors_app):
        """Test multiple request headers separated by commas."""
        async with TestClient(cors_app) as client:
            response = await client.options("/api/data", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization, X-Requested-With"
            })

            # Should fail because X-Requested-With is not allowed
            assert response.status_code == 400
            assert "CORS: Headers not allowed" in response.text

    async def test_empty_origin_header(self, cors_app):
        """Test empty Origin header."""
        async with TestClient(cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": ""
            })

            assert response.status_code == 200
            # Empty origin should be treated as no origin
            assert "access-control-allow-origin" not in response.headers

    async def test_non_options_method_with_preflight_headers(self, cors_app):
        """Test non-OPTIONS request with preflight headers (should be ignored)."""
        async with TestClient(cors_app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",  # Should be ignored for GET
                "Access-Control-Request-Headers": "Authorization"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://example.com"
            # No preflight-specific headers for non-OPTIONS requests
            assert "access-control-allow-methods" not in response.headers
            assert "access-control-max-age" not in response.headers

    async def test_cors_with_config_object(self):
        """Test CORS middleware with config object instead of individual parameters."""
        app = Zenith()

        config = CORSConfig(
            allow_origins=["https://config-test.com"],
            allow_methods=["GET", "POST"],
            allow_credentials=True
        )

        app.add_middleware(CORSMiddleware, config=config)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://config-test.com"
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "https://config-test.com"
            assert response.headers["access-control-allow-credentials"] == "true"

    async def test_cors_with_special_characters_in_origin(self, cors_app):
        """Test CORS with special characters in origin."""
        async with TestClient(cors_app) as client:
            # Test with port number
            response = await client.get("/test", headers={
                "Origin": "http://localhost:3000"  # This should be allowed
            })

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    async def test_cors_performance_with_precomputed_values(self):
        """Test that CORS middleware precomputes values for performance."""
        app = Zenith()

        config = CORSConfig(
            allow_origins=["https://performance-test.com"],
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["Content-Type", "Authorization"]
        )

        app.add_middleware(CORSMiddleware, config=config)

        # We can't easily access the middleware instance here, so this test
        # would need to be restructured or we test it in unit tests instead
        # This integration test focuses on functionality rather than internals

    async def test_cors_without_preflight_headers(self, cors_app):
        """Test OPTIONS request without preflight headers."""
        async with TestClient(cors_app) as client:
            # OPTIONS request with origin but no preflight headers
            response = await client.options("/test", headers={
                "Origin": "https://example.com"
                # No Access-Control-Request-Method
            })

            # This should pass through to the app (not handled as preflight)
            assert response.status_code == 405  # Method not allowed for regular OPTIONS


class TestCORSInStack:
    """Test CORS middleware in middleware stack."""

    async def test_cors_with_other_middleware(self):
        """Test CORS middleware working with other middleware."""
        from zenith.middleware.security import SecurityHeadersMiddleware

        app = Zenith()

        # Add both security and CORS middleware
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(CORSMiddleware, allow_origins=["https://example.com"])

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        async with TestClient(app) as client:
            response = await client.get("/test", headers={
                "Origin": "https://example.com"
            })

            assert response.status_code == 200
            # Should have both CORS and security headers
            assert response.headers["access-control-allow-origin"] == "https://example.com"
            assert "x-content-type-options" in response.headers  # From security middleware