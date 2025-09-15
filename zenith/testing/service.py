"""
Service testing utilities for isolated business logic testing.

Provides TestService for testing services in isolation with database
transaction rollback and dependency injection mocking.
"""

from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from zenith.core.container import DIContainer
from zenith.core.service import Service
from zenith.db import Base, Database

T = TypeVar("T", bound=Service)


class TestService:
    """
    Test wrapper for Zenith services with database transaction rollback.

    Allows testing business logic services in complete isolation with:
    - Automatic database transaction rollback after each test
    - Dependency injection container setup
    - Mock dependency registration
    - Async context manager support

    Example:
        async def test_user_creation():
            async with TestService(Users) as users:
                # This will be rolled back
                user = await users.create_user({
                    "email": "test@example.com",
                    "name": "Test User"
                })
                assert user.id

            # Database is clean for next test
    """

    def __init__(
        self,
        service_class: type[T],
        database_url: str = "sqlite+aiosqlite:///:memory:",
        dependencies: dict[str, Any] | None = None,
    ):
        """
        Initialize test service.

        Args:
            service_class: Service class to test
            database_url: Test database URL (defaults to in-memory SQLite)
            dependencies: Mock dependencies to register
        """
        self.service_class = service_class
        self.database_url = database_url
        self.dependencies = dependencies or {}

        # Test infrastructure
        self.engine = None
        self.session = None
        self.transaction = None
        self.database = None
        self.container = None
        self.service_instance = None

    async def __aenter__(self) -> T:
        """Set up test service with database transaction."""
        # Create test database
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
            if "sqlite" in self.database_url
            else {},
        )

        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Start transaction that will be rolled back
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()

        # Create session bound to transaction
        async_session = sessionmaker(
            bind=self.connection, class_=AsyncSession, expire_on_commit=False
        )
        self.session = async_session()

        # Set up test database wrapper
        self.database = TestDatabase(self.session)

        # Set up dependency injection container
        self.container = DIContainer()
        await self.container.startup()

        # Register test database
        self.container.register(Database, self.database)

        # Register mock dependencies
        for service_type, implementation in self.dependencies.items():
            self.container.register(service_type, implementation)

        # Create service instance with test dependencies
        self.service_instance = self.service_class()
        self.service_instance._container = self.container

        # Initialize service
        await self.service_instance.startup()

        return self.service_instance

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up test service and rollback transaction."""
        if self.service_instance:
            await self.service_instance.shutdown()

        if self.container:
            await self.container.shutdown()

        if self.session:
            await self.session.close()

        if self.transaction:
            await self.transaction.rollback()

        if self.connection:
            await self.connection.close()

        if self.engine:
            await self.engine.dispose()


class TestDatabase:
    """Test database wrapper that provides session management for tests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @asynccontextmanager
    async def session(self):
        """Provide database session for service operations."""
        yield self.session

    async def close(self):
        """Close database connections."""
        await self.session.close()


@asynccontextmanager
async def test_database(database_url: str = "sqlite+aiosqlite:///:memory:"):
    """
    Context manager for test database with automatic cleanup.

    Creates a test database, runs all migrations, and cleans up afterward.

    Example:
        async def test_with_database():
            async with test_database() as db:
                # Use database for testing
                async with db.session() as session:
                    # Database operations
                    pass
    """
    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    )

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create database wrapper
        async_session = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create Database instance for services
        db = TestDatabase(async_session())

        yield db

    finally:
        await engine.dispose()


class MockService(Service):
    """
    Mock service for testing dependencies.

    Provides a simple way to mock service dependencies in tests.
    """

    def __init__(self, **methods):
        """
        Create mock service with specified methods.

        Args:
            **methods: Method name to implementation mapping
        """
        super().__init__()
        for name, implementation in methods.items():
            setattr(self, name, implementation)


# Convenience functions for common test scenarios
async def create_test_service[T: Service](
    service_class: type[T], dependencies: dict[str, Any] | None = None
) -> T:
    """
    Create a service instance with test dependencies.

    Note: This doesn't provide database transaction rollback.
    Use TestService context manager for full isolation.
    """
    container = DIContainer()
    await container.startup()

    # Register dependencies
    if dependencies:
        for service_type, implementation in dependencies.items():
            container.register(service_type, implementation)

    # Create and initialize service
    service = service_class()
    service._container = container
    await service.startup()

    return service
