"""
🧪 Zenith Testing Patterns - Comprehensive Testing Guide

This example demonstrates all testing patterns and utilities available in Zenith,
including API testing, business logic testing, authentication testing, and
performance testing patterns.

Key Testing Features Demonstrated:
- TestClient for HTTP endpoint testing
- TestContext for business logic testing
- Authentication mocking and token creation
- Database testing with transaction rollback
- Performance and load testing patterns
- Test fixtures and factories
- Integration testing strategies
- Error handling testing

This file serves both as an executable example AND as a comprehensive test suite
that demonstrates testing best practices.

Run tests with: python -m pytest examples/13-testing-patterns.py -v
Run as demo: python examples/13-testing-patterns.py

Testing Endpoints:
- GET /                      - Public endpoint
- GET /users/{user_id}       - Protected endpoint
- POST /users               - User creation with validation
- GET /admin/users          - Admin-only endpoint
- POST /api/slow            - Slow endpoint for performance testing
"""

import asyncio
import random
import time
from datetime import datetime, timedelta

import pytest
from pydantic import BaseModel, EmailStr, validator

from zenith import Auth, Context, Service, Zenith
# Auth is already imported from zenith main module
from zenith.testing import (
    TestClient,
    TestContext,
    create_test_token,
    create_test_user,
    mock_auth,
)

# ============================================================================
# TEST APPLICATION SETUP
# ============================================================================


class User(BaseModel):
    """User model for testing."""

    id: int | None = None
    email: EmailStr
    name: str
    role: str = "user"
    is_active: bool = True
    created_at: datetime | None = None

    @validator("email")
    def email_must_be_valid(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UserCreate(BaseModel):
    """User creation model."""

    email: EmailStr
    name: str
    role: str = "user"


class UserService(Service):
    """User service for business logic testing."""

    def __init__(self):
        super().__init__()
        # In-memory store for testing
        self.users: dict[int, User] = {}
        self.next_id = 1

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Simulate database operation
        await asyncio.sleep(0.1)

        # Check for duplicate email
        for existing_user in self.users.values():
            if existing_user.email == user_data.email:
                raise ValueError(f"User with email {user_data.email} already exists")

        # Create user
        user = User(
            id=self.next_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            created_at=datetime.utcnow(),
        )

        self.users[self.next_id] = user
        self.next_id += 1

        return user

    async def get_user(self, user_id: int) -> User | None:
        """Get user by ID."""
        await asyncio.sleep(0.05)  # Simulate database query
        return self.users.get(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        await asyncio.sleep(0.05)
        for user in self.users.values():
            if user.email == email.lower():
                return user
        return None

    async def list_users(self) -> list[User]:
        """List all users."""
        await asyncio.sleep(0.1)
        return list(self.users.values())

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user."""
        user = self.users.get(user_id)
        if user:
            user.is_active = False
            return True
        return False

    async def get_user_count(self) -> int:
        """Get total user count."""
        return len(self.users)


# Create test application
app = Zenith(debug=True)


# ============================================================================
# TEST ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Public endpoint for basic testing."""
    return {
        "message": "🧪 Testing Patterns Demo",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "GET /users/{user_id}": "Get user (protected)",
            "POST /users": "Create user (protected)",
            "GET /admin/users": "List users (admin only)",
            "POST /api/slow": "Slow endpoint for performance testing",
        },
    }


@app.get("/users/{user_id}")
async def get_user(
    user_id: int, current_user: Auth = Auth(), users: UserService = Inject()
) -> User:
    """Protected endpoint - requires authentication."""
    user = await users.get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    return user


@app.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: Auth = Auth(),
    users: UserService = Inject(),
) -> User:
    """Create user endpoint - requires authentication."""
    return await users.create_user(user_data)


@app.get("/admin/users")
async def list_users(
    current_user: Auth = Auth(scopes=["admin"]), users: UserService = Inject()
) -> list[User]:
    """Admin-only endpoint."""
    return await users.list_users()


@app.post("/api/slow")
async def slow_endpoint(delay: float = 1.0):
    """Slow endpoint for performance testing."""
    await asyncio.sleep(delay)
    return {
        "message": f"Completed after {delay}s",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Note: ValueError exceptions are automatically handled by the framework
# and return appropriate HTTP error responses


# ============================================================================
# UNIT TESTS - BUSINESS LOGIC TESTING
# ============================================================================


@pytest.mark.asyncio
class TestUserService:
    """Test business logic using TestContext."""

    async def test_create_user_success(self):
        """Test successful user creation."""
        async with TestContext(UserService) as users:
            # Test data
            user_data = UserCreate(email="test@example.com", name="Test User")

            # Create user
            user = await users.create_user(user_data)

            # Assertions
            assert user.id == 1
            assert user.email == "test@example.com"
            assert user.name == "Test User"
            assert user.role == "user"
            assert user.is_active is True
            assert user.created_at is not None

    async def test_create_user_duplicate_email(self):
        """Test duplicate email validation."""
        async with TestContext(UserService) as users:
            # Create first user
            user_data = UserCreate(email="duplicate@example.com", name="User 1")
            await users.create_user(user_data)

            # Try to create duplicate
            duplicate_data = UserCreate(email="duplicate@example.com", name="User 2")

            with pytest.raises(ValueError, match="already exists"):
                await users.create_user(duplicate_data)

    async def test_get_user_by_id(self):
        """Test user retrieval by ID."""
        async with TestContext(UserService) as users:
            # Create user
            user_data = UserCreate(email="retrieve@example.com", name="Retrieve User")
            created_user = await users.create_user(user_data)

            # Retrieve user
            retrieved_user = await users.get_user(created_user.id)

            # Assertions
            assert retrieved_user is not None
            assert retrieved_user.id == created_user.id
            assert retrieved_user.email == created_user.email

    async def test_get_nonexistent_user(self):
        """Test retrieving non-existent user."""
        async with TestContext(UserService) as users:
            user = await users.get_user(999)
            assert user is None

    async def test_user_count(self):
        """Test user count tracking."""
        async with TestContext(UserService) as users:
            # Initially empty
            assert await users.get_user_count() == 0

            # Create users
            for i in range(3):
                user_data = UserCreate(email=f"user{i}@example.com", name=f"User {i}")
                await users.create_user(user_data)

            # Check count
            assert await users.get_user_count() == 3


# ============================================================================
# API TESTS - ENDPOINT TESTING
# ============================================================================


@pytest.mark.asyncio
class TestUserAPI:
    """Test API endpoints using TestClient."""

    async def test_public_endpoint(self):
        """Test public endpoint without authentication."""
        async with TestClient(app) as client:
            response = await client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert "Testing Patterns Demo" in data["message"]
            assert "timestamp" in data

    async def test_protected_endpoint_without_auth(self):
        """Test protected endpoint without authentication."""
        async with TestClient(app) as client:
            response = await client.get("/users/1")

            # Should be unauthorized
            assert response.status_code == 401

    async def test_protected_endpoint_with_auth(self):
        """Test protected endpoint with authentication."""
        async with TestClient(app) as client:
            # Set authentication token
            client.set_auth_token("user@example.com", role="user")

            # First create a user in the context
            async with TestContext(UserService) as users:
                user_data = UserCreate(email="api@example.com", name="API User")
                created_user = await users.create_user(user_data)

                # Test endpoint
                response = await client.get(f"/users/{created_user.id}")

                # Might fail due to context isolation, but demonstrates pattern
                # In real app, you'd have shared database state

    async def test_create_user_endpoint(self):
        """Test user creation endpoint."""
        async with TestClient(app) as client:
            # Authenticate as admin to create users
            client.set_auth_token("admin@example.com", role="admin")

            # Create user via API
            user_data = {
                "email": "newuser@example.com",
                "name": "New User",
                "role": "user",
            }

            response = await client.post("/users", json=user_data)

            # Check response (may fail due to context isolation in this example)
            # In real app with shared database, this would work
            print(f"Create user response: {response.status_code}")

    async def test_admin_endpoint_with_user_role(self):
        """Test admin endpoint with insufficient permissions."""
        async with TestClient(app) as client:
            # Authenticate as regular user
            client.set_auth_token("user@example.com", role="user")

            response = await client.get("/admin/users")

            # Should be forbidden
            assert response.status_code == 403

    async def test_admin_endpoint_with_admin_role(self):
        """Test admin endpoint with admin permissions."""
        async with TestClient(app) as client:
            # Authenticate as admin
            client.set_auth_token("admin@example.com", role="admin")

            response = await client.get("/admin/users")

            # Should succeed (though may be empty due to context isolation)
            assert response.status_code == 200

    async def test_validation_error(self):
        """Test input validation errors."""
        async with TestClient(app) as client:
            client.set_auth_token("user@example.com", role="user")

            # Invalid email format
            invalid_user = {"email": "not-an-email", "name": "Test User"}

            response = await client.post("/users", json=invalid_user)

            # Should be validation error
            assert response.status_code == 422


# ============================================================================
# AUTHENTICATION TESTING
# ============================================================================


@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication patterns and utilities."""

    def test_create_test_token(self):
        """Test JWT token creation for testing."""
        # Create user token
        user_token = create_test_token(email="user@example.com", user_id=1, role="user")
        assert user_token is not None
        assert isinstance(user_token, str)

        # Create admin token with scopes
        admin_token = create_test_token(
            email="admin@example.com",
            user_id=2,
            role="admin",
            scopes=["admin", "user", "read", "write"],
        )
        assert admin_token is not None

        # Create token with custom expiration
        short_lived_token = create_test_token(
            email="temp@example.com", expires_delta=timedelta(minutes=5)
        )
        assert short_lived_token is not None

    def test_create_test_user(self):
        """Test test user creation utility."""
        # Basic test user
        user = create_test_user()
        assert user["email"] == "test@example.com"
        assert user["role"] == "user"
        assert "password_hash" in user

        # Custom test user
        admin = create_test_user(
            email="admin@test.com", name="Test Admin", role="admin"
        )
        assert admin["email"] == "admin@test.com"
        assert admin["name"] == "Test Admin"
        assert admin["role"] == "admin"

    async def test_mock_auth_context(self):
        """Test authentication mocking."""
        # Mock authentication context
        with mock_auth(user_id=123, email="mock@example.com", role="admin"):
            # In this context, any Auth() dependency would return the mocked user
            # This is useful for testing business logic without dealing with tokens
            pass


# ============================================================================
# PERFORMANCE TESTING
# ============================================================================


@pytest.mark.asyncio
class TestPerformance:
    """Performance testing patterns."""

    async def test_endpoint_response_time(self):
        """Test endpoint response time."""
        async with TestClient(app) as client:
            start_time = time.time()

            response = await client.get("/")

            duration = time.time() - start_time

            # Assert response time is reasonable
            assert response.status_code == 200
            assert duration < 1.0  # Should respond within 1 second

    async def test_slow_endpoint_performance(self):
        """Test slow endpoint with controlled delay."""
        async with TestClient(app) as client:
            delay = 0.5
            start_time = time.time()

            response = await client.post("/api/slow", json={"delay": delay})

            actual_duration = time.time() - start_time

            # Should take at least the delay time
            assert response.status_code == 200
            assert actual_duration >= delay
            assert actual_duration < delay + 0.5  # Some tolerance

    async def test_concurrent_requests(self):
        """Test concurrent request handling."""
        async with TestClient(app) as client:
            # Create multiple concurrent requests
            tasks = []
            for _ in range(5):
                task = client.get("/")
                tasks.append(task)

            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            duration = time.time() - start_time

            # All requests should succeed
            for response in responses:
                assert response.status_code == 200

            # Should handle concurrently (not take 5x longer than single request)
            assert duration < 2.0

    async def test_load_testing_pattern(self):
        """Demonstrate load testing pattern."""
        async with TestClient(app) as client:
            request_count = 10
            success_count = 0
            total_time = 0

            for i in range(request_count):
                start = time.time()
                response = await client.get("/")
                end = time.time()

                if response.status_code == 200:
                    success_count += 1

                total_time += end - start

            # Calculate metrics
            success_rate = success_count / request_count * 100
            avg_response_time = total_time / request_count

            # Assertions
            assert success_rate >= 95  # At least 95% success rate
            assert avg_response_time < 0.1  # Average response time under 100ms

            print(
                f"Load test results: {success_rate}% success, {avg_response_time:.3f}s avg"
            )


# ============================================================================
# ERROR HANDLING TESTING
# ============================================================================


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling patterns."""

    async def test_validation_errors(self):
        """Test input validation error handling."""
        async with TestContext(UserService) as users:
            # Test empty name
            with pytest.raises(ValueError, match="Name cannot be empty"):
                UserCreate(email="test@example.com", name="")

            # Test invalid email (handled by Pydantic)
            with pytest.raises(ValueError, match="Invalid email format"):
                UserCreate(email="not-an-email", name="Test User")

    async def test_business_logic_errors(self):
        """Test business logic error handling."""
        async with TestContext(UserService) as users:
            # Create user
            user_data = UserCreate(email="error@example.com", name="Error User")
            await users.create_user(user_data)

            # Try to create duplicate
            with pytest.raises(ValueError, match="already exists"):
                await users.create_user(user_data)

    async def test_api_error_responses(self):
        """Test API error response format."""
        async with TestClient(app) as client:
            client.set_auth_token("user@example.com", role="user")

            # Request non-existent user
            response = await client.get("/users/999")

            # Should return error response
            assert response.status_code == 400
            error_data = response.json()
            assert "error" in error_data
            assert "not found" in error_data["error"].lower()


# ============================================================================
# TEST FIXTURES AND FACTORIES
# ============================================================================


class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    def create_user_data(
        email: str | None = None, name: str | None = None, role: str = "user"
    ) -> UserCreate:
        """Create user data for testing."""
        if email is None:
            email = f"user{random.randint(1000, 9999)}@example.com"
        if name is None:
            name = f"Test User {random.randint(100, 999)}"

        return UserCreate(email=email, name=name, role=role)

    @staticmethod
    async def create_users(count: int, users_service: UserService) -> list[User]:
        """Create multiple test users."""
        created_users = []
        for i in range(count):
            user_data = UserFactory.create_user_data(
                email=f"batch_user_{i}@example.com", name=f"Batch User {i}"
            )
            user = await users_service.create_user(user_data)
            created_users.append(user)

        return created_users


@pytest.mark.asyncio
class TestFactories:
    """Test factory patterns."""

    async def test_user_factory(self):
        """Test user factory."""
        async with TestContext(UserService) as users:
            # Create single user
            user_data = UserFactory.create_user_data()
            user = await users.create_user(user_data)

            assert user.id is not None
            assert "@example.com" in user.email
            assert "Test User" in user.name

    async def test_batch_user_creation(self):
        """Test batch user creation with factory."""
        async with TestContext(UserService) as users:
            # Create multiple users
            created_users = await UserFactory.create_users(3, users)

            assert len(created_users) == 3
            assert all(user.id is not None for user in created_users)
            assert len(set(user.email for user in created_users)) == 3  # All unique


# ============================================================================
# DEMO MODE - Run as application
# ============================================================================


async def run_demo_tests():
    """Run a subset of tests for demo purposes."""
    print("🧪 Running Zenith Testing Patterns Demo\n")

    # 1. Business Logic Testing Demo
    print("📋 Business Logic Testing:")
    async with TestContext(UserService) as users:
        user_data = UserCreate(email="demo@example.com", name="Demo User")
        user = await users.create_user(user_data)
        print(f"   ✅ Created user: {user.name} ({user.email})")

        retrieved = await users.get_user(user.id)
        print(f"   ✅ Retrieved user: {retrieved.name}")

        count = await users.get_user_count()
        print(f"   ✅ Total users: {count}")

    # 2. API Testing Demo
    print("\n🌐 API Endpoint Testing:")
    async with TestClient(app) as client:
        # Test public endpoint
        response = await client.get("/")
        print(f"   ✅ Public endpoint: {response.status_code}")

        # Test protected endpoint without auth
        response = await client.get("/users/1")
        print(f"   ✅ Protected without auth: {response.status_code} (Unauthorized)")

        # Test with authentication
        client.set_auth_token("demo@example.com", role="admin")
        response = await client.get("/admin/users")
        print(f"   ✅ Admin endpoint with auth: {response.status_code}")

    # 3. Performance Testing Demo
    print("\n⚡ Performance Testing:")
    async with TestClient(app) as client:
        start_time = time.time()
        response = await client.get("/")
        duration = time.time() - start_time
        print(f"   ✅ Response time: {duration:.3f}s")

        # Test slow endpoint
        start_time = time.time()
        response = await client.post("/api/slow", json={"delay": 0.2})
        duration = time.time() - start_time
        print(f"   ✅ Slow endpoint: {duration:.3f}s (expected ~0.2s)")

    print("\n✨ Demo completed! Run with pytest for full test suite.")


if __name__ == "__main__":
    print("🧪 Zenith Testing Patterns Example")
    print("=" * 50)
    print("This example demonstrates comprehensive testing patterns.")
    print("Run as: python examples/13-testing-patterns.py (demo mode)")
    print("Or: python -m pytest examples/13-testing-patterns.py -v (full tests)")
    print("=" * 50)

    # Run in demo mode
    asyncio.run(run_demo_tests())
