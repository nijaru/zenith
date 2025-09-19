"""
Testing fixtures and utilities for Zenith applications.

Provides pytest fixtures and common testing patterns for database setup,
application testing, and authentication mocking.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest

from zenith import Zenith
from zenith.auth import configure_auth
from zenith.testing.auth import TestAuthManager
from zenith.testing.client import TestClient
from zenith.testing.service import TestDatabase, test_database


# Pytest event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for async tests.

    This fixture ensures that async tests run properly with pytest-asyncio.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_database_fixture() -> AsyncGenerator[TestDatabase, None]:
    """
    Pytest fixture for test database with automatic cleanup.

    Provides a clean database for each test with transaction rollback.

    Example:
        async def test_with_database(test_database_fixture):
            async with test_database_fixture.session() as session:
                # Database operations
                pass
    """
    async with test_database() as db:
        yield db


@pytest.fixture
def test_app() -> Zenith:
    """
    Create basic test application with authentication configured.

    Returns:
        Configured Zenith app instance

    Example:
        def test_app_creation(test_app):
            assert test_app is not None

        async def test_with_client(test_app):
            async with TestClient(test_app) as client:
                response = await client.get("/health")
                assert response.status_code == 200
    """
    app = Zenith(debug=True)

    # Configure authentication with test secret
    configure_auth(
        app, secret_key="test-secret-key-for-testing-only-never-use-in-production"
    )

    # Add basic health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "test-app"}

    return app


@pytest.fixture
async def test_client(test_app: Zenith) -> AsyncGenerator[TestClient, None]:
    """
    Pytest fixture for TestClient with automatic setup/teardown.

    Args:
        test_app: Zenith application fixture

    Yields:
        Configured TestClient instance

    Example:
        async def test_endpoint(test_client):
            response = await test_client.get("/health")
            assert response.status_code == 200
    """
    async with TestClient(test_app) as client:
        yield client


@pytest.fixture
def auth_manager() -> TestAuthManager:
    """
    Pytest fixture for authentication manager.

    Provides utilities for managing test users and authentication.

    Returns:
        TestAuthManager instance

    Example:
        def test_with_auth(auth_manager):
            auth_manager.add_user("admin", "admin@example.com", role="admin")
            auth_manager.set_current_user("admin")

            token = auth_manager.create_token_for_current_user()
            assert token is not None
    """
    manager = TestAuthManager()

    # Add common test users
    manager.add_user("user", "user@example.com", role="user")
    manager.add_user("admin", "admin@example.com", role="admin", scopes=["admin"])
    manager.add_user(
        "moderator", "mod@example.com", role="moderator", scopes=["moderator"]
    )

    return manager


@pytest.fixture
async def authenticated_client(
    test_app: Zenith, auth_manager: TestAuthManager
) -> AsyncGenerator[TestClient, None]:
    """
    Pytest fixture for authenticated test client.

    Provides TestClient with admin authentication pre-configured.

    Args:
        test_app: Zenith application fixture
        auth_manager: Authentication manager fixture

    Yields:
        TestClient with admin authentication

    Example:
        async def test_protected_endpoint(authenticated_client):
            # Already authenticated as admin
            response = await authenticated_client.get("/admin/users")
            assert response.status_code == 200
    """
    async with TestClient(test_app) as client:
        # Set admin authentication
        client.set_auth_token("admin@example.com", role="admin", scopes=["admin"])
        yield client


class TestDatabase:
    """
    Test database wrapper with utilities for test data setup.

    Provides convenience methods for creating test data and managing
    database state during tests.
    """

    def __init__(self, database_url: str = "sqlite+aiosqlite:///:memory:"):
        self.database_url = database_url
        self._database = None

    async def __aenter__(self):
        """Set up test database."""
        self._database = await test_database(self.database_url).__aenter__()
        return self._database

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up test database."""
        if self._database:
            await test_database(self.database_url).__aexit__(exc_type, exc_val, exc_tb)


# Pytest markers for test categorization
pytest_markers = {
    "unit": pytest.mark.asyncio,
    "integration": pytest.mark.asyncio,
    "database": pytest.mark.asyncio,
    "auth": pytest.mark.asyncio,
    "slow": pytest.mark.slow,
}


def pytest_configure(config):
    """Configure pytest with custom markers."""
    for name, marker in pytest_markers.items():
        config.addinivalue_line(
            "markers", f"{name}: {marker.__doc__ or f'{name} tests'}"
        )


# Utility functions for test setup
async def create_test_app(
    auth_secret: str = "test-secret-key",
    database_url: str = "sqlite+aiosqlite:///:memory:",
    debug: bool = True,
    **kwargs,
) -> Zenith:
    """
    Create a fully configured test application.

    Args:
        auth_secret: JWT secret key
        database_url: Database URL
        debug: Debug mode
        **kwargs: Additional app configuration

    Returns:
        Configured Zenith application

    Example:
        async def test_custom_app():
            app = await create_test_app(database_url="postgresql://...")
            async with TestClient(app) as client:
                response = await client.get("/health")
                assert response.status_code == 200
    """
    app = Zenith(debug=debug, **kwargs)

    # Configure authentication
    configure_auth(app, secret_key=auth_secret)

    # Add essential middleware
    app.add_exception_handling(debug=debug)
    app.add_cors()

    # Add documentation
    app.add_docs(title="Test API", description="Test application")

    return app


def assert_response_success(response, expected_status: int = 200):
    """Assert that response is successful with expected status."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text}"
    )


def assert_response_error(response, expected_status: int = 400):
    """Assert that response is an error with expected status."""
    assert response.status_code >= expected_status, (
        f"Expected error status >= {expected_status}, got {response.status_code}"
    )


def assert_response_json(response, expected_keys: list | None = None):
    """Assert that response contains valid JSON with expected keys."""
    assert response.headers.get("content-type", "").startswith("application/json")

    data = response.json()

    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Expected key '{key}' in response data"

    return data
