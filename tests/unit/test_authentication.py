"""
Unit tests for the authentication system.

Tests JWT token generation/validation, password hashing, and auth middleware.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from zenith import Zenith
from zenith.auth import configure_auth
from zenith.auth.jwt import (
    JWTManager,
    configure_jwt,
)
from zenith.auth.password import hash_password, verify_password
from zenith.core.routing import Auth
from zenith.testing import TestClient, create_test_token


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-testing"
    yield
    # Cleanup after test
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_jwt_manager_creation(self):
        """Test JWT manager with defaults."""
        manager = JWTManager(secret_key="test-secret-key-that-is-long-enough")

        assert manager.secret_key == "test-secret-key-that-is-long-enough"
        assert manager.algorithm == "HS256"
        assert manager.access_token_expire_minutes == 30
        assert manager.refresh_token_expire_days == 7

    def test_jwt_manager_custom_values(self):
        """Test JWT manager with custom values."""
        manager = JWTManager(
            secret_key="custom-secret-key-that-is-long-enough",
            algorithm="HS512",
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
        )

        assert manager.secret_key == "custom-secret-key-that-is-long-enough"
        assert manager.algorithm == "HS512"
        assert manager.access_token_expire_minutes == 60
        assert manager.refresh_token_expire_days == 30

    def test_create_access_token(self):
        """Test creating JWT access tokens."""
        manager = JWTManager(secret_key="test-secret-key-that-is-long-enough")

        token = manager.create_access_token(
            user_id=123, email="test@example.com", role="user", scopes=["read", "write"]
        )

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

        # Decode and verify structure
        decoded = jwt.decode(token, manager.secret_key, algorithms=[manager.algorithm])
        assert decoded["sub"] == "123"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "user"
        assert decoded["scopes"] == ["read", "write"]
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_token_with_custom_expiry(self):
        """Test creating tokens with custom expiry times."""
        manager = JWTManager(
            secret_key="test-secret-key-that-is-long-enough",
            access_token_expire_minutes=60,
        )

        token = manager.create_access_token(user_id=123, email="test@example.com")

        decoded = jwt.decode(token, manager.secret_key, algorithms=[manager.algorithm])
        exp_time = datetime.fromtimestamp(decoded["exp"])
        iat_time = datetime.fromtimestamp(decoded["iat"])

        # Should expire in approximately 60 minutes
        expected_diff = timedelta(minutes=60)
        actual_diff = exp_time - iat_time
        assert abs(actual_diff - expected_diff) < timedelta(seconds=5)

    def test_verify_valid_token(self):
        """Test verifying valid JWT tokens."""
        manager = JWTManager(secret_key="test-secret-key-that-is-long-enough")

        token = manager.create_access_token(
            user_id=123, email="test@example.com", role="admin"
        )

        user_data = manager.extract_user_from_token(token)

        assert user_data is not None
        assert user_data["id"] == 123
        assert user_data["email"] == "test@example.com"
        assert user_data["role"] == "admin"
        assert isinstance(user_data["scopes"], list)

    def test_verify_invalid_token(self):
        """Test verifying invalid JWT tokens."""
        manager = JWTManager(secret_key="test-secret-key-that-is-long-enough")

        # Invalid token format
        invalid_token = "invalid.jwt.token"
        user_data = manager.extract_user_from_token(invalid_token)
        assert user_data is None

        # Token with wrong signature
        wrong_manager = JWTManager(
            secret_key="wrong-secret-key-that-is-different-and-long-enough"
        )
        valid_token = manager.create_access_token(user_id=123, email="test@example.com")
        user_data = wrong_manager.extract_user_from_token(valid_token)
        assert user_data is None

    def test_verify_expired_token(self):
        """Test verifying expired JWT tokens."""
        manager = JWTManager(
            secret_key="test-secret-key-that-is-long-enough",
            access_token_expire_minutes=0,  # Expire immediately
        )

        # Create token that expires immediately
        with patch("zenith.auth.jwt.datetime") as mock_datetime:
            # Mock current time
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            token = manager.create_access_token(user_id=123, email="test@example.com")

        # Token should be expired when verified
        user_data = manager.extract_user_from_token(token)
        assert user_data is None


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "secure_password_123"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password  # Should be hashed, not plain text
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert hash1 != hash2

    def test_hash_same_password_different_salts(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "same_password"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different due to random salt

    def test_verify_correct_password(self):
        """Test verifying correct passwords."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed)

    def test_verify_incorrect_password(self):
        """Test verifying incorrect passwords."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert not verify_password(wrong_password, hashed)

    def test_verify_empty_password(self):
        """Test verifying empty passwords."""
        hashed = hash_password("password")

        assert not verify_password("", hashed)
        assert not verify_password(None, hashed)

    def test_verify_invalid_hash(self):
        """Test verifying with invalid hash."""
        password = "password"
        invalid_hash = "invalid_hash_format"

        assert not verify_password(password, invalid_hash)


class TestTestingUtilities:
    """Test authentication testing utilities."""

    def test_create_test_token(self):
        """Test creating test tokens for testing."""
        # Configure JWT for testing
        configure_jwt("test-secret-key-that-is-long-enough-for-testing")

        token = create_test_token("test@example.com", user_id=123, role="admin")

        assert isinstance(token, str)
        assert len(token) > 50

        # Should be decodeable with configured secret
        from zenith.auth.jwt import get_jwt_manager

        manager = get_jwt_manager()
        decoded = jwt.decode(token, manager.secret_key, algorithms=["HS256"])
        assert decoded["email"] == "test@example.com"
        assert decoded["sub"] == "123"
        assert decoded["role"] == "admin"

    def test_create_test_token_with_scopes(self):
        """Test creating test tokens with scopes."""
        # Configure JWT for testing
        configure_jwt("test-secret-key-that-is-long-enough-for-testing")

        token = create_test_token(
            "test@example.com",
            user_id=456,
            role="user",
            scopes=["read", "write", "delete"],
        )

        from zenith.auth.jwt import get_jwt_manager

        manager = get_jwt_manager()
        decoded = jwt.decode(token, manager.secret_key, algorithms=["HS256"])
        assert decoded["scopes"] == ["read", "write", "delete"]


@pytest.mark.asyncio
class TestAuthenticationMiddleware:
    """Test authentication middleware integration."""

    async def test_middleware_with_valid_token(self):
        """Test middleware processing valid tokens."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough")

        @app.get("/protected")
        async def protected_endpoint(current_user=Auth(required=True)):
            return {"user": current_user, "message": "authenticated"}

        async with TestClient(app) as client:
            client.set_auth_token("test@example.com", user_id=123, role="user")

            response = await client.get("/protected")
            assert response.status_code == 200

            data = response.json()
            assert data["user"]["email"] == "test@example.com"
            assert data["user"]["id"] == 123
            assert data["message"] == "authenticated"

    async def test_middleware_with_invalid_token(self):
        """Test middleware processing invalid tokens."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough")
        app.add_exception_handling(debug=True)

        @app.get("/protected")
        async def protected_endpoint(current_user=Auth(required=True)):
            return {"user": current_user}

        async with TestClient(app) as client:
            # Invalid token
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer invalid.jwt.token"}
            )
            assert response.status_code == 401

    async def test_middleware_optional_auth(self):
        """Test middleware with optional authentication."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough")

        @app.get("/optional")
        async def optional_endpoint(current_user=Auth(required=False)):
            return {"authenticated": current_user is not None, "user": current_user}

        async with TestClient(app) as client:
            # Without token
            response = await client.get("/optional")
            assert response.status_code == 200
            data = response.json()
            assert not data["authenticated"]
            assert data["user"] is None

            # With token
            client.set_auth_token("test@example.com", user_id=123)
            response = await client.get("/optional")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"]
            assert data["user"]["email"] == "test@example.com"

    async def test_middleware_scope_validation(self):
        """Test middleware validating token scopes."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough")

        @app.get("/admin-only")
        async def admin_endpoint(current_user=Auth(required=True, scopes=["admin"])):
            return {"message": "admin access"}

        async with TestClient(app) as client:
            # User without admin scope
            client.set_auth_token(
                "user@example.com", role="user", scopes=["read", "write"]
            )

            response = await client.get("/admin-only")
            assert response.status_code == 403  # Forbidden - insufficient scopes

            # User with admin scope
            client.set_auth_token("admin@example.com", role="admin", scopes=["admin"])

            response = await client.get("/admin-only")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "admin access"


class TestAuthenticationConfiguration:
    """Test authentication configuration and setup."""

    @pytest.mark.asyncio
    async def test_configure_auth_basic(self):
        """Test basic authentication configuration."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough")

        # Should have added auth middleware
        middleware_classes = [m.cls.__name__ for m in app.middleware]
        assert any("Auth" in name for name in middleware_classes)

        # Should have JWT manager configured
        from zenith.auth.jwt import get_jwt_manager

        manager = get_jwt_manager()
        assert manager.secret_key == "test-secret-key-that-is-long-enough"

    @pytest.mark.asyncio
    async def test_configure_auth_custom_config(self):
        """Test authentication with custom configuration."""
        app = Zenith(debug=True)

        configure_auth(
            app,
            secret_key="custom-secret-key-that-is-long-enough",
            algorithm="HS512",
            access_token_expire_minutes=120,
        )

        from zenith.auth.jwt import get_jwt_manager

        manager = get_jwt_manager()
        assert manager.secret_key == "custom-secret-key-that-is-long-enough"
        assert manager.algorithm == "HS512"
        assert manager.access_token_expire_minutes == 120

    def test_configure_auth_invalid_secret(self):
        """Test authentication configuration with invalid secret."""
        app = Zenith(debug=True)

        # Too short secret key
        with pytest.raises(
            ValueError, match="JWT secret key must be at least 32 characters"
        ):
            configure_auth(app, secret_key="short")

    def test_configure_auth_weak_entropy(self):
        """Test authentication configuration with weak entropy."""
        app = Zenith(debug=True)

        # Key with insufficient unique characters (only 10 unique chars)
        with pytest.raises(
            ValueError, match="JWT secret key has insufficient entropy"
        ):
            configure_auth(app, secret_key="aaaaaaaabbbbbbbbccccccccdddddddd")

        # Key with character frequency >25% (50 a's out of 64 = 78%)
        with pytest.raises(
            ValueError, match="JWT secret key has insufficient entropy"
        ):
            configure_auth(
                app, secret_key="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabcdefghijkl"
            )

    @pytest.mark.asyncio
    async def test_multiple_auth_configurations(self):
        """Test that multiple auth configurations raise error."""
        app = Zenith(debug=True)
        configure_auth(app, secret_key="test-secret-key-that-is-long-enough")

        # Attempting to configure auth again should raise error
        with pytest.raises(RuntimeError, match="Authentication already configured"):
            configure_auth(app, secret_key="another-secret-key-that-is-long-enough")


class TestAuthenticationHelpers:
    """Test authentication helper functions."""

    def test_get_password_hash_and_verify(self):
        """Test complete password hash and verify cycle."""
        password = "user_password_123"

        # Hash password
        hashed = hash_password(password)

        # Verify correct password
        assert verify_password(password, hashed)

        # Verify incorrect password
        assert not verify_password("wrong_password", hashed)

    def test_jwt_token_lifecycle(self):
        """Test complete JWT token lifecycle."""
        manager = JWTManager(secret_key="test-secret-key-that-is-long-enough")

        # Create token
        token = manager.create_access_token(
            user_id=123, email="user@example.com", role="user", scopes=["read"]
        )

        # Verify token
        user_data = manager.extract_user_from_token(token)
        assert user_data["id"] == 123
        assert user_data["email"] == "user@example.com"
        assert user_data["role"] == "user"
        assert user_data["scopes"] == ["read"]


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
