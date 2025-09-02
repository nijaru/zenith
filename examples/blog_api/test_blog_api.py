"""
Example tests for Blog API using Zenith Testing Framework.

Demonstrates:
- API endpoint testing with TestClient
- Context testing with TestContext
- Authentication testing
- Database transaction rollback
"""

import pytest
from typing import Optional, List

from pydantic import BaseModel, EmailStr
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from zenith import Zenith, Router, Context, Auth
from zenith.core.context import Context as BaseContext
from zenith.auth import configure_auth
from zenith.db import Base
from zenith.testing import TestClient, TestContext, create_test_user, mock_auth


# Mock application models for testing
class User(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_active: bool = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserTable(Base):
    __tablename__ = "test_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Users(BaseContext):
    """Mock users context for testing."""

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return User(
            id=user_id,
            email=f"user{user_id}@example.com",
            name=f"User {user_id}",
            is_active=True,
        )

    async def create_user(self, user_data: UserCreate) -> User:
        """Create new user."""
        return User(id=1, email=user_data.email, name=user_data.name, is_active=True)

    async def list_users(self, page: int = 1, per_page: int = 20) -> List[User]:
        """List users with pagination."""
        return [
            User(id=1, email="user1@example.com", name="User 1"),
            User(id=2, email="user2@example.com", name="User 2"),
        ]


# Test application setup
@pytest.fixture
def test_app():
    """Create test application."""
    app = Zenith(debug=True)

    # Configure authentication
    configure_auth(app, secret_key="test-secret-key-for-testing")

    # Register context
    app.register_context("users", Users)

    # Create API router
    api = Router(prefix="/api")

    @api.get("/users/{user_id}")
    async def get_user(
        user_id: int, users: Users = Context(), current_user=Auth(required=True)
    ) -> User:
        user = await users.get_user(user_id)
        if not user:
            from starlette.responses import JSONResponse

            return JSONResponse({"error": "User not found"}, status_code=404)
        return user

    @api.post("/users")
    async def create_user(
        user_data: UserCreate,
        users: Users = Context(),
        current_user=Auth(required=True, scopes=["admin"]),
    ) -> User:
        return await users.create_user(user_data)

    @api.get("/users")
    async def list_users(users: Users = Context()) -> List[User]:
        return await users.list_users()

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    app.include_router(api)

    return app


class TestBlogAPIEndpoints:
    """Test API endpoints using TestClient."""

    async def test_health_endpoint(self, test_app):
        """Test health check endpoint."""
        async with TestClient(test_app) as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    async def test_list_users_public(self, test_app):
        """Test public users list endpoint."""
        async with TestClient(test_app) as client:
            response = await client.get("/api/users")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["email"] == "user1@example.com"

    async def test_get_user_requires_auth(self, test_app):
        """Test that get user endpoint requires authentication."""
        async with TestClient(test_app) as client:
            response = await client.get("/api/users/1")

            assert response.status_code == 401

    async def test_get_user_with_auth(self, test_app):
        """Test authenticated user retrieval."""
        async with TestClient(test_app) as client:
            # Set authentication token
            client.set_auth_token("test@example.com", role="user")

            response = await client.get("/api/users/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["email"] == "user1@example.com"

    async def test_create_user_requires_admin(self, test_app):
        """Test that user creation requires admin role."""
        async with TestClient(test_app) as client:
            # Regular user token
            client.set_auth_token("test@example.com", role="user")

            response = await client.post(
                "/api/users",
                json={
                    "email": "new@example.com",
                    "name": "New User",
                    "password": "password123",
                },
            )

            # Should fail due to insufficient permissions
            assert response.status_code == 403

    async def test_create_user_with_admin(self, test_app):
        """Test user creation with admin privileges."""
        async with TestClient(test_app) as client:
            # Admin token
            client.set_auth_token("admin@example.com", role="admin", scopes=["admin"])

            response = await client.post(
                "/api/users",
                json={
                    "email": "new@example.com",
                    "name": "New User",
                    "password": "password123",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "new@example.com"
            assert data["name"] == "New User"


class TestUsersContext:
    """Test Users context in isolation using TestContext."""

    async def test_get_user(self):
        """Test user retrieval in context."""
        async with TestContext(Users) as users:
            user = await users.get_user(1)

            assert user is not None
            assert user.id == 1
            assert user.email == "user1@example.com"

    async def test_create_user(self):
        """Test user creation in context."""
        async with TestContext(Users) as users:
            user_data = UserCreate(
                email="test@example.com", name="Test User", password="password123"
            )

            user = await users.create_user(user_data)

            assert user.id == 1
            assert user.email == "test@example.com"
            assert user.name == "Test User"

    async def test_list_users(self):
        """Test user listing in context."""
        async with TestContext(Users) as users:
            user_list = await users.list_users()

            assert len(user_list) == 2
            assert all(isinstance(user, User) for user in user_list)


class TestAuthenticationFlow:
    """Test authentication and authorization flows."""

    async def test_jwt_token_creation(self):
        """Test JWT token creation and validation."""
        from zenith.testing.auth import create_test_token

        token = create_test_token(
            email="test@example.com", role="admin", scopes=["admin", "user"]
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    async def test_mock_authentication(self):
        """Test mock authentication for context testing."""
        auth_mock = mock_auth(email="admin@example.com", role="admin", scopes=["admin"])

        # Test mock auth functions
        current_user = auth_mock.get_current_user()
        assert current_user["email"] == "admin@example.com"
        assert current_user["role"] == "admin"

        # Test require_auth
        auth_user = auth_mock.require_auth()
        assert auth_user == current_user

    async def test_context_with_mock_auth(self):
        """Test context with mocked authentication dependency."""
        auth_mock = mock_auth(email="test@example.com", role="user")

        async with TestContext(Users, dependencies={"auth": auth_mock}) as users:
            # Context can access mock authentication
            user = await users.get_user(1)
            assert user is not None


# Integration test combining multiple components
class TestIntegration:
    """Integration tests combining API, contexts, and authentication."""

    async def test_full_user_workflow(self, test_app):
        """Test complete user management workflow."""
        async with TestClient(test_app) as client:
            # 1. Check health
            health_response = await client.get("/health")
            assert health_response.status_code == 200

            # 2. List users (public)
            users_response = await client.get("/api/users")
            assert users_response.status_code == 200
            initial_users = users_response.json()

            # 3. Try to get user without auth (should fail)
            unauth_response = await client.get("/api/users/1")
            assert unauth_response.status_code == 401

            # 4. Set authentication and get user
            client.set_auth_token("user@example.com", role="user")
            auth_response = await client.get("/api/users/1")
            assert auth_response.status_code == 200

            # 5. Try to create user as regular user (should fail)
            client.clear_auth()
            client.set_auth_token("user@example.com", role="user")
            create_fail_response = await client.post(
                "/api/users",
                json={
                    "email": "newuser@example.com",
                    "name": "New User",
                    "password": "password123",
                },
            )
            assert create_fail_response.status_code == 403

            # 6. Create user as admin (should succeed)
            client.clear_auth()
            client.set_auth_token("admin@example.com", role="admin", scopes=["admin"])
            create_success_response = await client.post(
                "/api/users",
                json={
                    "email": "newuser@example.com",
                    "name": "New User",
                    "password": "password123",
                },
            )
            assert create_success_response.status_code == 200
            new_user = create_success_response.json()
            assert new_user["email"] == "newuser@example.com"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
