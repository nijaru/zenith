"""
Authentication testing utilities.

Provides helpers for creating test users, generating test tokens,
and mocking authentication in Zenith application tests.
"""

from datetime import datetime, timedelta
from typing import Any

from zenith.auth.jwt import create_access_token
from zenith.auth.password import hash_password


def create_test_token(
    email: str,
    user_id: int | str = 1,
    role: str = "user",
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a test JWT token for authentication testing.

    Args:
        email: User email
        user_id: User ID
        role: User role
        scopes: Permission scopes
        expires_delta: Custom expiration time

    Returns:
        JWT token string

    Example:
        # Create admin token
        admin_token = create_test_token(
            "admin@example.com",
            role="admin",
            scopes=["admin", "user"]
        )

        # Use in test client
        client.set_auth_token("admin@example.com", role="admin")
    """
    return create_access_token(
        user_id=user_id,
        email=email,
        role=role,
        scopes=scopes or [],
        expires_delta=expires_delta,
    )


def create_test_user(
    email: str = "test@example.com",
    name: str = "Test User",
    password: str = "testpassword123",
    role: str = "user",
    user_id: int = 1,
    scopes: list[str] | None = None,
    **extra_fields,
) -> dict[str, Any]:
    """
    Create test user data with hashed password.

    Args:
        email: User email
        name: User name
        password: Plain text password (will be hashed)
        role: User role
        user_id: User ID
        scopes: Permission scopes
        **extra_fields: Additional user fields

    Returns:
        User data dict with hashed password

    Example:
        user_data = create_test_user(
            email="admin@example.com",
            role="admin",
            scopes=["admin"]
        )
    """
    user_data = {
        "id": user_id,
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "role": role,
        "scopes": scopes or [],
        "is_active": True,
        "created_at": datetime.utcnow(),
        **extra_fields,
    }

    return user_data


class MockAuth:
    """
    Mock authentication for testing contexts that require current user.

    Allows injecting fake user data for testing business logic
    that depends on authentication.
    """

    def __init__(
        self,
        email: str = "test@example.com",
        user_id: int | str = 1,
        role: str = "user",
        scopes: list[str] | None = None,
        **extra_fields,
    ):
        """
        Initialize mock authentication.

        Args:
            email: Mock user email
            user_id: Mock user ID
            role: Mock user role
            scopes: Mock user scopes
            **extra_fields: Additional user fields
        """
        self.user_data = {
            "id": user_id,
            "email": email,
            "role": role,
            "scopes": scopes or [],
            **extra_fields,
        }

    def get_current_user(self, required: bool = True) -> dict[str, Any] | None:
        """Mock get_current_user function."""
        if required:
            return self.user_data
        return self.user_data

    def require_auth(self) -> dict[str, Any]:
        """Mock require_auth function."""
        return self.user_data

    def require_roles(self, *roles: str) -> dict[str, Any]:
        """Mock require_roles function."""
        user_role = self.user_data.get("role", "user")
        if user_role not in roles:
            raise PermissionError(
                f"User role '{user_role}' not in required roles: {roles}"
            )
        return self.user_data


def mock_auth(
    email: str = "test@example.com",
    user_id: int | str = 1,
    role: str = "user",
    scopes: list[str] | None = None,
    **extra_fields,
) -> MockAuth:
    """
    Create mock authentication instance.

    Convenience function for creating MockAuth instances.

    Args:
        email: Mock user email
        user_id: Mock user ID
        role: Mock user role
        scopes: Mock user scopes
        **extra_fields: Additional user fields

    Returns:
        MockAuth instance

    Example:
        # Test context with mock authentication
        auth_mock = mock_auth(email="admin@example.com", role="admin")

        async with TestService(Users, dependencies={"auth": auth_mock}) as users:
            # Context methods can access current user through mock
            result = await users.get_current_user_profile()
            assert result["email"] == "admin@example.com"
    """
    return MockAuth(
        email=email, user_id=user_id, role=role, scopes=scopes, **extra_fields
    )


class TestAuthManager:
    """
    Test authentication manager for complex test scenarios.

    Provides utilities for managing multiple test users,
    switching authentication contexts, and testing permission scenarios.
    """

    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.current_user: str | None = None

    def add_user(
        self,
        identifier: str,
        email: str,
        role: str = "user",
        scopes: list[str] | None = None,
        **extra_fields,
    ) -> None:
        """Add a test user to the manager."""
        self.users[identifier] = create_test_user(
            email=email, role=role, scopes=scopes, **extra_fields
        )

    def set_current_user(self, identifier: str) -> None:
        """Set the current user for authentication."""
        if identifier not in self.users:
            raise ValueError(f"User '{identifier}' not found")
        self.current_user = identifier

    def get_current_user_data(self) -> dict[str, Any] | None:
        """Get current user data."""
        if not self.current_user:
            return None
        return self.users[self.current_user]

    def create_token_for_user(self, identifier: str) -> str:
        """Create JWT token for a specific user."""
        if identifier not in self.users:
            raise ValueError(f"User '{identifier}' not found")

        user = self.users[identifier]
        return create_test_token(
            email=user["email"],
            user_id=user["id"],
            role=user["role"],
            scopes=user.get("scopes", []),
        )

    def create_token_for_current_user(self) -> str | None:
        """Create JWT token for current user."""
        if not self.current_user:
            return None
        return self.create_token_for_user(self.current_user)
