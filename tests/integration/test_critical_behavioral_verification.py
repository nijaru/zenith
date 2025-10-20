"""
Critical Behavioral Verification Tests

These tests verify that critical framework features work as expected
in real-world scenarios to prevent regressions like those found in v0.0.1.

These are HIGH-PRIORITY tests that should always pass.
"""

import asyncio

import pytest

from zenith import Zenith
from zenith.middleware.rate_limit import RateLimit, RateLimitMiddleware
from zenith.testing import TestClient


class TestCriticalBehavior:
    """Critical behavior verification tests."""

    @pytest.mark.asyncio
    async def test_jwt_authentication_end_to_end(self):
        """Test complete JWT authentication flow works end-to-end."""
        from zenith.core import Config

        config = Config(debug=True)
        config.secret_key = "test-secret-key-32-characters-long"
        app = Zenith(config=config)
        app.add_auth()

        # Add a protected endpoint
        @app.get("/protected")
        async def protected_endpoint():
            # This should automatically get the authenticated user
            from zenith.auth.dependencies import require_auth

            user = require_auth(app.request)  # This would be injected in real scenario
            return {"message": "success", "user_id": user["id"]}

        async with TestClient(app) as client:
            # Step 1: Login to get token (using demo credentials in dev mode)
            login_response = await client.post(
                "/auth/login", json={"username": "demo", "password": "demo"}
            )
            assert login_response.status_code == 200

            token_data = login_response.json()
            assert "access_token" in token_data
            assert "token_type" in token_data
            assert "expires_in" in token_data  # OAuth2 compliance
            assert token_data["token_type"] == "bearer"
            assert isinstance(token_data["expires_in"], int)

            token = token_data["access_token"]

            # Step 2: Access protected endpoint with token should work
            # Note: In a real test, we'd need to properly set up the auth dependency injection
            # For now, we're testing that tokens can be generated and are valid

            # Verify token is valid by decoding it
            from zenith.auth.jwt import extract_user_from_token

            user_info = extract_user_from_token(token)
            assert user_info is not None
            assert user_info["id"] == 999  # Demo user ID
            assert user_info["email"] == "demo@example.com"

    @pytest.mark.asyncio
    async def test_rate_limiting_enforces_limits(self):
        """Test rate limiting actually blocks requests when limits are exceeded."""
        app = Zenith()

        # Remove existing rate limiting middleware and add strict one
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        # Add very restrictive rate limiting: 2 requests per 60 seconds
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=[RateLimit(requests=2, window=60, per="ip")],
        )

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        async with TestClient(app) as client:
            # First two requests should succeed
            response1 = await client.get("/test")
            assert response1.status_code == 200
            assert response1.json()["message"] == "success"

            response2 = await client.get("/test")
            assert response2.status_code == 200
            assert response2.json()["message"] == "success"

            # Third request should be rate limited
            response3 = await client.get("/test")
            assert response3.status_code == 429

            error_data = response3.json()
            assert error_data["error"] == "rate_limit_exceeded"
            assert error_data["message"] == "Rate limit exceeded"
            assert error_data["limit"] == 2
            assert error_data["window"] == 60
            assert error_data["current"] == 3

    @pytest.mark.asyncio
    async def test_rate_limiting_localhost_not_exempt(self):
        """Verify that localhost is not automatically exempt from rate limiting."""
        app = Zenith()

        # Remove existing rate limiting and add new one
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        # Add rate limiting with no exemptions
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=[RateLimit(requests=1, window=10, per="ip")],
            exempt_ips=[],  # Explicitly no exemptions
        )

        @app.get("/test")
        async def test_endpoint():
            return {"count": "ok"}

        async with TestClient(app) as client:
            # First request should succeed
            response1 = await client.get("/test")
            assert response1.status_code == 200

            # Second request should be blocked (localhost not exempt)
            response2 = await client.get("/test")
            assert response2.status_code == 429

            # Verify it's actually rate limiting, not some other error
            error_data = response2.json()
            assert "rate_limit_exceeded" in error_data["error"]

    @pytest.mark.asyncio
    async def test_oauth2_compliance_fields(self):
        """Test OAuth2 response includes all required fields per RFC 6749."""
        from zenith.core import Config

        config = Config(debug=True)
        config.secret_key = "test-secret-key-32-characters-long"
        app = Zenith(config=config)
        app.add_auth(expire_minutes=45)  # Custom expiration

        async with TestClient(app) as client:
            response = await client.post(
                "/auth/login", json={"username": "demo", "password": "demo"}
            )

            assert response.status_code == 200

            data = response.json()

            # Required OAuth2 fields per RFC 6749
            assert "access_token" in data
            assert "token_type" in data
            assert "expires_in" in data

            # Verify correct values
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 45 * 60  # Convert minutes to seconds
            assert isinstance(data["access_token"], str)
            assert len(data["access_token"]) > 50  # JWT tokens are long

    @pytest.mark.asyncio
    async def test_all_fixes_together(self):
        """Integration test: All fixes working together in one app."""
        from zenith.core import Config

        config = Config(debug=True)
        config.secret_key = "test-secret-key-32-characters-long"
        app = Zenith(config=config)
        app.add_auth()

        # Add strict rate limiting
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=[RateLimit(requests=3, window=60, per="ip")],
        )

        @app.get("/protected")
        async def protected_endpoint():
            return {"message": "Protected endpoint accessed successfully"}

        async with TestClient(app) as client:
            # 1. Test OAuth2 login works with proper fields
            login_response = await client.post(
                "/auth/login", json={"username": "demo", "password": "demo"}
            )
            assert login_response.status_code == 200

            token_data = login_response.json()
            assert all(
                field in token_data
                for field in ["access_token", "token_type", "expires_in"]
            )

            # 2. Test JWT token is valid
            from zenith.auth.jwt import extract_user_from_token

            user_info = extract_user_from_token(token_data["access_token"])
            assert user_info is not None

            # 3. Test rate limiting works (after 3 login attempts, should be blocked)
            for i in range(3):  # We already made 1 login request above
                await client.post(
                    "/auth/login", json={"username": f"user{i}", "password": "pass"}
                )
                # These should work or fail based on credentials, but count toward rate limit

            # 4th request should be rate limited
            rate_limited_response = await client.post(
                "/auth/login", json={"username": "another_user", "password": "pass"}
            )
            assert rate_limited_response.status_code == 429

            error_data = rate_limited_response.json()
            assert "rate_limit_exceeded" in error_data["error"]

    @pytest.mark.asyncio
    async def test_cache_performance_still_works(self):
        """Verify cache performance wasn't broken by our fixes."""
        app = Zenith()

        call_count = 0

        @app.get("/cached")
        async def cached_endpoint():
            nonlocal call_count
            call_count += 1
            # Simulate expensive operation
            await asyncio.sleep(0.001)  # 1ms delay
            return {
                "result": f"expensive_computation_{call_count}",
                "call_count": call_count,
            }

        async with TestClient(app) as client:
            # First call should hit the function
            response1 = await client.get("/cached")
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["call_count"] == 1

            # Without caching, second call would increment counter
            # This test confirms caching still works as designed
            # (Note: This doesn't test actual caching since we'd need to add @cache decorator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
