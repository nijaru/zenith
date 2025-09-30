"""
Test user endpoints for TaskFlow API.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(client):
    """Create a test user and return credentials."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "testpass123",
    }

    # Register user
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    # Login to get token
    login_data = {"email": user_data["email"], "password": user_data["password"]}
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200

    token = response.json()["access_token"]
    user = response.json()["user"]

    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


class TestUserRegistration:
    """Test user registration and authentication."""

    async def test_register_success(self, client):
        """Test successful user registration."""
        response = await client.post(
            "/auth/register",
            json={
                "name": "Alice Smith",
                "email": "alice@example.com",
                "password": "secure123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice Smith"
        assert data["email"] == "alice@example.com"
        assert "password" not in data

    async def test_register_duplicate_email(self, client):
        """Test that duplicate emails are rejected."""
        user_data = {
            "name": "Bob Jones",
            "email": "bob@example.com",
            "password": "password123",
        }

        # First registration
        response = await client.post("/auth/register", json=user_data)
        assert response.status_code == 201

        # Duplicate registration
        response = await client.post("/auth/register", json=user_data)
        assert response.status_code == 409
        assert "already registered" in response.json()["error"]

    async def test_register_weak_password(self, client):
        """Test that weak passwords are rejected."""
        response = await client.post(
            "/auth/register",
            json={
                "name": "Charlie Brown",
                "email": "charlie@example.com",
                "password": "123",  # Too short
            },
        )

        assert response.status_code == 422


class TestAuthentication:
    """Test login and JWT authentication."""

    async def test_login_success(self, client):
        """Test successful login."""
        # Register user first
        await client.post(
            "/auth/register",
            json={
                "name": "Login Test",
                "email": "login@example.com",
                "password": "testpass123",
            },
        )

        # Login
        response = await client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login@example.com"

    async def test_login_invalid_credentials(self, client):
        """Test login with wrong password."""
        # Register user
        await client.post(
            "/auth/register",
            json={
                "name": "Test User",
                "email": "test2@example.com",
                "password": "correctpass",
            },
        )

        # Try login with wrong password
        response = await client.post(
            "/auth/login", json={"email": "test2@example.com", "password": "wrongpass"}
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["error"]


class TestUserCRUD:
    """Test user CRUD operations."""

    async def test_list_users(self, client):
        """Test listing users with pagination."""
        # Create multiple users
        for i in range(5):
            await client.post(
                "/auth/register",
                json={
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "password": "password123",
                },
            )

        # List users
        response = await client.get("/users?skip=0&limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
        assert int(response.headers["X-Total-Count"]) >= 5

    async def test_get_user(self, client, test_user):
        """Test getting a specific user."""
        user_id = test_user["user"]["id"]
        response = await client.get(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == test_user["user"]["email"]

    async def test_update_user(self, client, test_user):
        """Test updating user profile."""
        user_id = test_user["user"]["id"]
        headers = test_user["headers"]

        response = await client.patch(
            f"/users/{user_id}", json={"name": "Updated Name"}, headers=headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_update_other_user_forbidden(self, client, test_user):
        """Test that users can't update other users."""
        # Create another user
        response = await client.post(
            "/auth/register",
            json={
                "name": "Other User",
                "email": "other@example.com",
                "password": "password123",
            },
        )
        other_user_id = response.json()["id"]

        # Try to update other user with first user's token
        headers = test_user["headers"]
        response = await client.patch(
            f"/users/{other_user_id}", json={"name": "Hacked"}, headers=headers
        )

        assert response.status_code == 403
        assert "permission" in response.json()["error"].lower()

    async def test_search_users(self, client):
        """Test searching users by name or email."""
        # Create users with specific names
        await client.post(
            "/auth/register",
            json={
                "name": "Alice Wonderland",
                "email": "alice.w@example.com",
                "password": "password123",
            },
        )

        await client.post(
            "/auth/register",
            json={
                "name": "Bob Builder",
                "email": "bob.b@example.com",
                "password": "password123",
            },
        )

        # Search for "alice"
        response = await client.get("/users?search=alice")
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 1
        assert any("alice" in user["email"].lower() for user in users)
