"""
JWT token management for Zenith applications.

Provides secure token generation, validation, and user authentication
using industry-standard JWT (JSON Web Tokens).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

logger = logging.getLogger("zenith.auth.jwt")


class JWTManager:
    """
    JWT token manager with secure defaults.

    Features:
    - Configurable secret key and algorithm
    - Token expiration and refresh
    - Secure token validation
    - User payload embedding
    - Automatic expiration checking
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        if not secret_key or len(secret_key) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 characters long. "
                "Use a secure random string in production."
            )

        if not self._has_sufficient_entropy(secret_key):
            raise ValueError(
                "JWT secret key has insufficient entropy. "
                "Avoid repeating characters or simple patterns. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def _has_sufficient_entropy(self, key: str) -> bool:
        """Check if key has sufficient entropy (not just repeated characters)."""
        if len(key) < 32:
            return False

        unique_chars = len(set(key))
        if unique_chars < 16:
            return False

        char_freqs = {}
        for char in key:
            char_freqs[char] = char_freqs.get(char, 0) + 1

        max_freq = max(char_freqs.values())
        return not max_freq > len(key) * 0.25

    def create_access_token(
        self,
        user_id: int | str,
        email: str,
        role: str = "user",
        scopes: list | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_id: User identifier
            email: User email address
            role: User role (admin, user, moderator, etc.)
            scopes: List of permission scopes
            expires_delta: Custom expiration time

        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=self.access_token_expire_minutes
            )

        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "role": role,
            "scopes": scopes or [],
            "exp": expire,
            "iat": datetime.now(UTC),  # Issued at
            "type": "access",
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created access token for user {user_id}")
            return token
        except (
            jwt.InvalidKeyError,
            jwt.InvalidAlgorithmError,
            TypeError,
            ValueError,
        ) as e:
            logger.error(f"Failed to create JWT token: {e}")
            raise

    def create_refresh_token(self, user_id: int | str) -> str:
        """Create a refresh token for long-term authentication."""
        expire = datetime.now(UTC) + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "refresh",
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created refresh token for user {user_id}")
            return token
        except (
            jwt.InvalidKeyError,
            jwt.InvalidAlgorithmError,
            TypeError,
            ValueError,
        ) as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token to verify

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )

            # Validate token type (should be access token for most operations)
            if payload.get("type") != "access":
                logger.warning(f"Invalid token type: {payload.get('type')}")
                return None

            logger.debug(f"Successfully verified token for user {payload.get('sub')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    def verify_refresh_token(self, token: str) -> dict[str, Any] | None:
        """Verify a refresh token specifically."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )

            if payload.get("type") != "refresh":
                logger.warning("Token is not a refresh token")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None

    def extract_user_from_token(self, token: str) -> dict[str, Any] | None:
        """Extract user information from a valid token."""
        payload = self.verify_token(token)
        if not payload:
            return None

        return {
            "id": int(payload["sub"]) if payload["sub"].isdigit() else payload["sub"],
            "email": payload["email"],
            "role": payload["role"],
            "scopes": payload.get("scopes", []),
            "expires_at": payload["exp"],
        }


# Global JWT manager instance (configured by application)
_jwt_manager: JWTManager | None = None


def configure_jwt(
    secret_key: str,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
) -> JWTManager:
    """Configure the global JWT manager."""
    global _jwt_manager
    _jwt_manager = JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )
    return _jwt_manager


def get_jwt_manager() -> JWTManager:
    """Get the configured JWT manager."""
    if _jwt_manager is None:
        raise RuntimeError("JWT manager not configured. Call configure_jwt() first.")
    return _jwt_manager


# Convenience functions
def create_access_token(
    user_id: int | str,
    email: str,
    role: str = "user",
    scopes: list | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create access token using global JWT manager."""
    return get_jwt_manager().create_access_token(
        user_id, email, role, scopes, expires_delta
    )


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify access token using global JWT manager."""
    return get_jwt_manager().verify_token(token)


def extract_user_from_token(token: str) -> dict[str, Any] | None:
    """Extract user from token using global JWT manager."""
    return get_jwt_manager().extract_user_from_token(token)
