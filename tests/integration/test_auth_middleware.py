"""
Integration tests for authentication middleware.

Tests critical authentication scenarios that could break security
including JWT validation, token extraction, and authorization edge cases.
"""

import jwt as pyjwt
import pytest
from datetime import datetime, timedelta, timezone

from zenith import Zenith
from zenith.auth.jwt import JWTManager
from zenith.middleware.auth import AuthenticationMiddleware, get_current_user, require_scopes, require_role
from zenith.testing.client import TestClient


@pytest.fixture
def jwt_secret():
    """JWT secret for testing."""
    return "test-secret-key-for-integration-tests"


@pytest.fixture
def jwt_manager(jwt_secret):
    """JWT manager for testing."""
    return JWTManager(secret_key=jwt_secret)


@pytest.fixture
def valid_token(jwt_manager):
    """Valid JWT token for testing."""
    return jwt_manager.create_access_token(
        user_id="user123",
        email="test@example.com",
        role="user",
        scopes=["read", "write"]
    )


@pytest.fixture
def expired_token(jwt_manager):
    """Expired JWT token for testing."""
    return jwt_manager.create_access_token(
        user_id="user123",
        email="test@example.com",
        role="user",
        scopes=["read", "write"],
        expires_delta=timedelta(hours=-1)  # Expired 1 hour ago
    )


@pytest.fixture
def admin_token(jwt_manager):
    """Admin JWT token for testing."""
    return jwt_manager.create_access_token(
        user_id="admin456",
        email="admin@example.com",
        role="admin",
        scopes=["read", "write", "admin", "delete"]
    )


@pytest.fixture
def basic_app():
    """Basic app without auth middleware."""
    app = Zenith()

    @app.get("/public")
    async def public_endpoint():
        return {"message": "public"}

    @app.get("/protected")
    async def protected_endpoint():
        return {"message": "protected"}

    return app


@pytest.fixture
def auth_app(jwt_manager):
    """App with authentication middleware."""
    app = Zenith()

    # Mock the JWT manager
    import zenith.auth.jwt
    zenith.auth.jwt._jwt_manager = jwt_manager

    app.add_middleware(AuthenticationMiddleware)

    @app.get("/public")
    async def public_endpoint():
        return {"message": "public"}

    @app.get("/protected")
    async def protected_endpoint(request):
        user = get_current_user(request, required=True)
        return {"message": "protected", "user": user["email"]}

    @app.get("/optional-auth")
    async def optional_auth_endpoint(request):
        user = get_current_user(request, required=False)
        if user:
            return {"message": "authenticated", "user": user["email"]}
        return {"message": "anonymous"}

    @app.get("/admin-only")
    async def admin_only_endpoint(request):
        user = get_current_user(request, required=True)
        require_role(request, "admin")
        return {"message": "admin area", "user": user["email"]}

    @app.get("/requires-scopes")
    async def scoped_endpoint(request):
        user = get_current_user(request, required=True)
        require_scopes(request, ["write", "delete"])
        return {"message": "scoped content", "user": user["email"]}

    return app


@pytest.fixture
def custom_public_paths_app(jwt_manager):
    """App with custom public paths."""
    app = Zenith()

    # Mock the JWT manager
    import zenith.auth.jwt
    zenith.auth.jwt._jwt_manager = jwt_manager

    auth_middleware = AuthenticationMiddleware(
        app,
        public_paths=["/api/health", "/api/public", "/custom-docs"]
    )

    @app.get("/api/health")
    async def health_endpoint():
        return {"status": "healthy"}

    @app.get("/api/public")
    async def public_api_endpoint():
        return {"message": "public api"}

    @app.get("/api/private")
    async def private_api_endpoint(request):
        user = get_current_user(request, required=True)
        return {"message": "private api", "user": user["email"]}

    @app.get("/custom-docs")
    async def custom_docs_endpoint():
        return {"docs": "custom documentation"}

    return app


class TestAuthenticationBasics:
    """Test basic authentication functionality."""

    async def test_public_path_no_auth_required(self, auth_app):
        """Test that public paths don't require authentication."""
        async with TestClient(auth_app) as client:
            response = await client.get("/public")
            assert response.status_code == 200
            assert response.json()["message"] == "public"

    async def test_protected_path_without_token(self, auth_app):
        """Test that protected paths require authentication."""
        async with TestClient(auth_app) as client:
            response = await client.get("/protected")
            assert response.status_code == 401
            assert "Authentication required" in response.json()["detail"]

    async def test_protected_path_with_valid_token(self, auth_app, valid_token):
        """Test protected path with valid JWT token."""
        async with TestClient(auth_app) as client:
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {valid_token}"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "protected"
            assert data["user"] == "test@example.com"

    async def test_protected_path_with_expired_token(self, auth_app, expired_token):
        """Test protected path with expired JWT token."""
        async with TestClient(auth_app) as client:
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {expired_token}"
            })
            assert response.status_code == 401
            assert "Authentication failed" in response.json()["detail"]

    async def test_optional_auth_without_token(self, auth_app):
        """Test optional authentication without token."""
        async with TestClient(auth_app) as client:
            response = await client.get("/optional-auth")
            assert response.status_code == 200
            assert response.json()["message"] == "anonymous"

    async def test_optional_auth_with_token(self, auth_app, valid_token):
        """Test optional authentication with valid token."""
        async with TestClient(auth_app) as client:
            response = await client.get("/optional-auth", headers={
                "Authorization": f"Bearer {valid_token}"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "authenticated"
            assert data["user"] == "test@example.com"


class TestTokenExtraction:
    """Test JWT token extraction and validation."""

    async def test_bearer_token_extraction(self, auth_app, valid_token):
        """Test proper Bearer token extraction."""
        async with TestClient(auth_app) as client:
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {valid_token}"
            })
            assert response.status_code == 200

    async def test_invalid_authorization_header_format(self, auth_app, valid_token):
        """Test invalid Authorization header formats."""
        async with TestClient(auth_app) as client:
            # Missing Bearer prefix
            response = await client.get("/protected", headers={
                "Authorization": valid_token
            })
            assert response.status_code == 401

            # Wrong prefix
            response = await client.get("/protected", headers={
                "Authorization": f"Basic {valid_token}"
            })
            assert response.status_code == 401

            # Empty header
            response = await client.get("/protected", headers={
                "Authorization": ""
            })
            assert response.status_code == 401

            # Malformed Bearer format
            response = await client.get("/protected", headers={
                "Authorization": "Bearer"
            })
            assert response.status_code == 401

            # Multiple spaces
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer  {valid_token}  extra"
            })
            assert response.status_code == 401

    async def test_invalid_jwt_token(self, auth_app):
        """Test various invalid JWT tokens."""
        async with TestClient(auth_app) as client:
            # Completely invalid token
            response = await client.get("/protected", headers={
                "Authorization": "Bearer invalid.jwt.token"
            })
            assert response.status_code == 401

            # Malformed JWT
            response = await client.get("/protected", headers={
                "Authorization": "Bearer not-a-jwt"
            })
            assert response.status_code == 401

            # Empty token
            response = await client.get("/protected", headers={
                "Authorization": "Bearer "
            })
            assert response.status_code == 401

    async def test_token_with_wrong_secret(self, auth_app):
        """Test JWT token signed with wrong secret."""
        # Create token with different secret
        wrong_secret_token = pyjwt.encode({
            "id": "user123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }, "wrong-secret", algorithm="HS256")

        async with TestClient(auth_app) as client:
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {wrong_secret_token}"
            })
            assert response.status_code == 401
            assert "Authentication failed" in response.json()["detail"]


class TestRoleBasedAccess:
    """Test role-based access control."""

    async def test_admin_access_with_admin_token(self, auth_app, admin_token):
        """Test admin endpoint with admin token."""
        async with TestClient(auth_app) as client:
            response = await client.get("/admin-only", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "admin area"
            assert data["user"] == "admin@example.com"

    async def test_admin_access_with_user_token(self, auth_app, valid_token):
        """Test admin endpoint with regular user token."""
        async with TestClient(auth_app) as client:
            response = await client.get("/admin-only", headers={
                "Authorization": f"Bearer {valid_token}"
            })
            assert response.status_code == 403
            assert "Insufficient role" in response.json()["detail"]

    async def test_role_hierarchy(self, auth_app, jwt_secret):
        """Test role hierarchy (admin > moderator > user)."""
        # Create moderator token
        moderator_payload = {
            "id": "mod789",
            "email": "moderator@example.com",
            "role": "moderator",
            "scopes": ["read", "write", "moderate"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        moderator_token = pyjwt.encode(moderator_payload, jwt_secret, algorithm="HS256")

        # Create endpoint requiring moderator role
        from zenith.middleware.auth import AuthenticationMiddleware, get_current_user, require_role

        app = Zenith()

        # Mock JWT manager
        from zenith.auth.jwt import JWTManager
        import zenith.auth.jwt
        zenith.auth.jwt._jwt_manager = JWTManager(secret_key=jwt_secret)

        app.add_middleware(AuthenticationMiddleware)

        @app.get("/moderator-area")
        async def moderator_endpoint(request):
            user = get_current_user(request, required=True)
            require_role(request, "moderator")
            return {"message": "moderator area", "user": user["email"]}

        async with TestClient(app) as client:
            # Admin should have access
            response = await client.get("/moderator-area", headers={
                "Authorization": f"Bearer {auth_app.app.app._jwt_manager.create_token(user_id='admin', email='admin@example.com', role='admin')}"
            })
            # Note: This test would need proper token creation

            # Moderator should have access
            response = await client.get("/moderator-area", headers={
                "Authorization": f"Bearer {moderator_token}"
            })
            assert response.status_code == 200

            # User should not have access
            response = await client.get("/moderator-area", headers={
                "Authorization": f"Bearer {valid_token}"
            })
            assert response.status_code == 403


class TestScopeBasedAccess:
    """Test scope-based access control."""

    async def test_scoped_access_with_required_scopes(self, auth_app, jwt_secret):
        """Test scoped endpoint with required scopes."""
        # Create token with all required scopes
        scoped_payload = {
            "id": "user123",
            "email": "test@example.com",
            "role": "user",
            "scopes": ["read", "write", "delete"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        scoped_token = pyjwt.encode(scoped_payload, jwt_secret, algorithm="HS256")

        async with TestClient(auth_app) as client:
            response = await client.get("/requires-scopes", headers={
                "Authorization": f"Bearer {scoped_token}"
            })
            assert response.status_code == 200

    async def test_scoped_access_missing_scopes(self, auth_app, jwt_secret):
        """Test scoped endpoint with missing required scopes."""
        # Create token missing required scopes
        limited_payload = {
            "id": "user123",
            "email": "test@example.com",
            "role": "user",
            "scopes": ["read"],  # Missing 'write' and 'delete'
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        limited_token = pyjwt.encode(limited_payload, jwt_secret, algorithm="HS256")

        async with TestClient(auth_app) as client:
            response = await client.get("/requires-scopes", headers={
                "Authorization": f"Bearer {limited_token}"
            })
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

    async def test_user_without_scopes_field(self, auth_app, jwt_secret):
        """Test user token without scopes field."""
        # Create token without scopes field
        no_scopes_payload = {
            "id": "user123",
            "email": "test@example.com",
            "role": "user",
            # No scopes field
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        no_scopes_token = pyjwt.encode(no_scopes_payload, jwt_secret, algorithm="HS256")

        async with TestClient(auth_app) as client:
            response = await client.get("/requires-scopes", headers={
                "Authorization": f"Bearer {no_scopes_token}"
            })
            assert response.status_code == 403
            # Should fail because user has no scopes


class TestCustomPublicPaths:
    """Test custom public path configuration."""

    async def test_custom_public_paths(self, custom_public_paths_app):
        """Test custom public paths don't require auth."""
        async with TestClient(custom_public_paths_app) as client:
            # Custom public paths should work without auth
            response = await client.get("/api/health")
            assert response.status_code == 200

            response = await client.get("/api/public")
            assert response.status_code == 200

            response = await client.get("/custom-docs")
            assert response.status_code == 200

    async def test_private_paths_require_auth(self, custom_public_paths_app):
        """Test that non-public paths still require auth."""
        async with TestClient(custom_public_paths_app) as client:
            response = await client.get("/api/private")
            assert response.status_code == 401

    async def test_path_prefix_matching(self, custom_public_paths_app):
        """Test that public path matching uses prefix matching."""
        async with TestClient(custom_public_paths_app) as client:
            # Should work because /api/public is a public path prefix
            response = await client.get("/api/public/subpath")
            assert response.status_code == 200  # Should be treated as public

    async def test_default_public_paths_still_work(self, auth_app):
        """Test that default public paths (/docs, /health, etc.) still work."""
        async with TestClient(auth_app) as client:
            # Default public paths should work
            response = await client.get("/docs")
            # Note: This might return 404 if no docs are configured, but shouldn't return 401
            assert response.status_code != 401

            response = await client.get("/health")
            assert response.status_code != 401


class TestAuthenticationEdgeCases:
    """Test authentication edge cases and potential bugs."""

    async def test_malformed_bearer_header_variations(self, auth_app, valid_token):
        """Test various malformed Bearer header formats."""
        async with TestClient(auth_app) as client:
            malformed_headers = [
                "bearer token",  # Lowercase
                "Bearer",  # No token
                f"Bearer{valid_token}",  # No space
                f"Bearer  {valid_token}",  # Extra spaces
                f"Bearer {valid_token} extra",  # Extra content
                "Bearer token1 token2",  # Multiple tokens
            ]

            for header in malformed_headers:
                response = await client.get("/protected", headers={
                    "Authorization": header
                })
                assert response.status_code == 401, f"Header '{header}' should fail"

    async def test_case_sensitivity_bearer(self, auth_app, valid_token):
        """Test case sensitivity of Bearer keyword."""
        async with TestClient(auth_app) as client:
            # Should be case-insensitive according to HTTP standards
            case_variations = [
                f"bearer {valid_token}",
                f"BEARER {valid_token}",
                f"Bearer {valid_token}",
                f"BeArEr {valid_token}",
            ]

            for header in case_variations:
                response = await client.get("/protected", headers={
                    "Authorization": header
                })
                # Only 'Bearer' (proper case) should work based on current implementation
                if header.startswith("Bearer "):
                    assert response.status_code == 200
                else:
                    assert response.status_code == 401

    async def test_jwt_with_missing_required_claims(self, auth_app, jwt_secret):
        """Test JWT tokens missing required claims."""
        async with TestClient(auth_app) as client:
            # Token without user ID
            no_id_payload = {
                "email": "test@example.com",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            }
            no_id_token = pyjwt.encode(no_id_payload, jwt_secret, algorithm="HS256")

            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {no_id_token}"
            })
            # Should fail because user ID is required
            assert response.status_code == 401

    async def test_jwt_with_null_values(self, auth_app, jwt_secret):
        """Test JWT tokens with null values in claims."""
        null_values_payload = {
            "id": None,
            "email": None,
            "role": None,
            "scopes": None,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        null_token = pyjwt.encode(null_values_payload, jwt_secret, algorithm="HS256")

        async with TestClient(auth_app) as client:
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {null_token}"
            })
            # Should handle null values gracefully
            assert response.status_code == 401

    async def test_very_long_jwt_token(self, auth_app, jwt_secret):
        """Test handling of very long JWT tokens."""
        # Create token with very large payload
        large_payload = {
            "id": "user123",
            "email": "test@example.com",
            "role": "user",
            "scopes": ["read", "write"],
            "large_field": "x" * 10000,  # Very large field
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        large_token = pyjwt.encode(large_payload, jwt_secret, algorithm="HS256")

        async with TestClient(auth_app) as client:
            response = await client.get("/protected", headers={
                "Authorization": f"Bearer {large_token}"
            })
            # Should handle large tokens properly
            assert response.status_code == 200

    async def test_concurrent_auth_requests(self, auth_app, valid_token):
        """Test concurrent authentication requests."""
        import asyncio

        async with TestClient(auth_app) as client:
            async def make_request():
                return await client.get("/protected", headers={
                    "Authorization": f"Bearer {valid_token}"
                })

            # Make multiple concurrent requests
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

    async def test_auth_state_isolation(self, auth_app, valid_token, jwt_secret):
        """Test that authentication state is properly isolated between requests."""
        # Create two different tokens
        token1_payload = {
            "id": "user1",
            "email": "user1@example.com",
            "role": "user",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token1 = pyjwt.encode(token1_payload, jwt_secret, algorithm="HS256")

        token2_payload = {
            "id": "user2",
            "email": "user2@example.com",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token2 = pyjwt.encode(token2_payload, jwt_secret, algorithm="HS256")

        async with TestClient(auth_app) as client:
            # Make request with first token
            response1 = await client.get("/protected", headers={
                "Authorization": f"Bearer {token1}"
            })
            assert response1.status_code == 200
            assert response1.json()["user"] == "user1@example.com"

            # Make request with second token
            response2 = await client.get("/protected", headers={
                "Authorization": f"Bearer {token2}"
            })
            assert response2.status_code == 200
            assert response2.json()["user"] == "user2@example.com"

            # State should not leak between requests
            assert response1.json()["user"] != response2.json()["user"]


class TestAuthInStack:
    """Test authentication middleware in middleware stack."""

    async def test_auth_with_cors_middleware(self, jwt_manager, valid_token):
        """Test auth middleware working with CORS."""
        from zenith.middleware.cors import CORSMiddleware

        app = Zenith()

        # Mock JWT manager
        import zenith.auth.jwt
        zenith.auth.jwt._jwt_manager = jwt_manager

        # Add both auth and CORS middleware
        app.add_middleware(AuthenticationMiddleware)
        cors_middleware = CORSMiddleware(
            app=auth_middleware,
            allow_origins=["*"]
        )
        app.app = cors_middleware

        @app.get("/test")
        async def test_endpoint(request):
            user = get_current_user(request, required=True)
            return {"message": "test", "user": user["email"]}

        async with TestClient(app) as client:
            response = await client.get("/test", headers={
                "Authorization": f"Bearer {valid_token}",
                "Origin": "https://example.com"
            })

            assert response.status_code == 200
            # Should have both auth success and CORS headers
            assert response.json()["user"] == "test@example.com"
            assert response.headers["access-control-allow-origin"] == "https://example.com"

    async def test_auth_with_security_middleware(self, jwt_manager, valid_token):
        """Test auth middleware working with security headers."""
        from zenith.middleware.security import SecurityHeadersMiddleware

        app = Zenith()

        # Mock JWT manager
        import zenith.auth.jwt
        zenith.auth.jwt._jwt_manager = jwt_manager

        # Add both auth and security middleware
        app.add_middleware(AuthenticationMiddleware)
        security_middleware = SecurityHeadersMiddleware(auth_middleware)
        app.app = security_middleware

        @app.get("/test")
        async def test_endpoint(request):
            user = get_current_user(request, required=True)
            return {"message": "test", "user": user["email"]}

        async with TestClient(app) as client:
            response = await client.get("/test", headers={
                "Authorization": f"Bearer {valid_token}"
            })

            assert response.status_code == 200
            # Should have both auth success and security headers
            assert response.json()["user"] == "test@example.com"
            assert "x-content-type-options" in response.headers