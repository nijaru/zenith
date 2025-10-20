"""
Tests for QueryBuilder lazy session and seamless chaining.

Addresses Issue 1 from ZENITH_ISSUES_ALTTEXT.md:
- .where() should be synchronous and return chainable QueryBuilder
- Session should be fetched lazily when executing terminal methods
"""

import os

import pytest
import pytest_asyncio
from sqlmodel import Field

from zenith.db import ZenithModel

# Force pytest-asyncio to use function-scoped event loops for isolation
pytestmark = pytest.mark.asyncio(scope="function")


class ChainUser(ZenithModel, table=True):
    """Test user model for chaining tests."""

    __tablename__ = "chain_users"

    id: int | None = Field(primary_key=True)
    email: str = Field(unique=True)
    name: str
    active: bool = True


@pytest_asyncio.fixture
async def app_with_database():
    """Create app with test database - single database with table truncation."""
    from zenith import Zenith
    from zenith.core.container import set_default_database

    # Use DATABASE_URL from environment (PostgreSQL in CI) or SQLite (local)
    # Single database for all tests with table truncation for isolation
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///test_querybuilder.db")

    app = Zenith(middleware=[])
    app.config.database_url = database_url

    # Create tables (idempotent - won't fail if already exist)
    await app.app.database.create_all()

    # Set this database as the default for ZenithModel operations
    set_default_database(app.app.database)

    yield app

    # Cleanup - truncate all tables for test isolation
    from sqlmodel import SQLModel

    try:
        async with app.app.database.engine.begin() as conn:
            # Truncate tables in reverse order to handle foreign keys
            for table in reversed(SQLModel.metadata.sorted_tables):
                await conn.execute(table.delete())
    except Exception:
        pass

    # Clear default database
    set_default_database(None)


@pytest.mark.asyncio
async def test_where_returns_querybuilder_immediately(app_with_database):
    """Test that .where() returns QueryBuilder synchronously (no await needed)."""
    from zenith.testing import TestClient

    app = app_with_database

    async with TestClient(app):
        # This should work WITHOUT await before .first()
        # Previously would fail with: TypeError: 'coroutine' object has no attribute 'first'
        builder = ChainUser.where(email="test@example.com")
        assert builder is not None
        assert hasattr(builder, "first")
        assert hasattr(builder, "all")
        assert hasattr(builder, "order_by")


@pytest.mark.asyncio
async def test_where_chaining_single_statement(app_with_database):
    """Test seamless chaining: await ChainUser.where(...).first()"""
    import uuid

    from zenith.testing import TestClient

    app = app_with_database
    # Use unique email per test run to avoid conflicts
    email = f"alice_{uuid.uuid4().hex[:8]}@example.com"

    async with TestClient(app):
        # Create test user
        await ChainUser.create(email=email, name="Alice", active=True)

        # This is the KEY test - single-line chaining should work
        user = await ChainUser.where(email=email).first()

        assert user is not None
        assert user.email == email
        assert user.name == "Alice"


@pytest.mark.asyncio
async def test_where_chaining_with_multiple_methods(app_with_database):
    """Test chaining multiple QueryBuilder methods."""
    import uuid

    from zenith.testing import TestClient

    app = app_with_database
    uid = uuid.uuid4().hex[:8]

    async with TestClient(app):
        # Create test users with unique emails
        await ChainUser.create(
            email=f"alice_{uid}@example.com", name="Alice", active=True
        )
        await ChainUser.create(email=f"bob_{uid}@example.com", name="Bob", active=True)
        await ChainUser.create(
            email=f"charlie_{uid}@example.com", name="Charlie", active=False
        )

        # Chain multiple methods
        users = await ChainUser.where(active=True).order_by("-name").limit(10).all()

        assert len(users) == 2
        assert users[0].name == "Bob"  # Descending order
        assert users[1].name == "Alice"


@pytest.mark.asyncio
async def test_where_with_count(app_with_database):
    """Test chaining with count()."""
    import uuid

    from zenith.testing import TestClient

    app = app_with_database
    uid = uuid.uuid4().hex[:8]

    async with TestClient(app):
        # Create test users with unique emails
        await ChainUser.create(
            email=f"alice_{uid}@example.com", name="Alice", active=True
        )
        await ChainUser.create(email=f"bob_{uid}@example.com", name="Bob", active=True)
        await ChainUser.create(
            email=f"charlie_{uid}@example.com", name="Charlie", active=False
        )

        # Single-line chaining with count()
        count = await ChainUser.where(active=True).count()

        assert count == 2


@pytest.mark.asyncio
async def test_where_with_exists(app_with_database):
    """Test chaining with exists()."""
    from zenith.testing import TestClient

    app = app_with_database
    import uuid

    uid = uuid.uuid4().hex[:8]

    async with TestClient(app):
        # Create test user
        await ChainUser.create(
            email=f"alice_{uid}@example.com", name="Alice", active=True
        )

        # Single-line chaining with exists()
        exists = await ChainUser.where(email=f"alice_{uid}@example.com").exists()
        not_exists = await ChainUser.where(email="nobody@example.com").exists()

        assert exists is True
        assert not_exists is False


@pytest.mark.asyncio
async def test_find_by_uses_synchronous_where(app_with_database):
    """Test that find_by() works with synchronous where()."""
    from zenith.testing import TestClient

    app = app_with_database
    import uuid

    uid = uuid.uuid4().hex[:8]

    async with TestClient(app):
        # Create test user
        await ChainUser.create(
            email=f"alice_{uid}@example.com", name="Alice", active=True
        )

        # find_by should work seamlessly
        user = await ChainUser.find_by(email=f"alice_{uid}@example.com")

        assert user is not None
        assert user.email == f"alice_{uid}@example.com"


@pytest.mark.asyncio
async def test_where_lazy_session_only_fetched_on_execution(app_with_database):
    """Test that session is only fetched when executing terminal methods."""
    from zenith.testing import TestClient

    app = app_with_database

    async with TestClient(app):
        # Building the query should not fetch session yet
        builder = ChainUser.where(active=True).order_by("-name").limit(5)

        # Session should be None until execution
        assert builder.session is None

        # Now execute - this should fetch session
        users = await builder.all()

        # After execution, session should be set
        assert builder.session is not None
        assert isinstance(users, list)


@pytest.mark.asyncio
async def test_complex_chaining_scenario(app_with_database):
    """Test the exact scenario from the issue report."""
    from zenith.testing import TestClient

    app = app_with_database
    import uuid

    uid = uuid.uuid4().hex[:8]

    async with TestClient(app):
        # Create test data
        await ChainUser.create(
            email=f"alice_{uid}@example.com", name="Alice", active=True
        )
        await ChainUser.create(email=f"bob_{uid}@example.com", name="Bob", active=True)
        await ChainUser.create(
            email=f"charlie_{uid}@example.com", name="Charlie", active=True
        )

        # This is the exact pattern from the issue that should now work:
        # user = await ChainUser.where(email=email).first()
        user = await ChainUser.where(email=f"bob_{uid}@example.com").first()

        assert user is not None
        assert user.email == f"bob_{uid}@example.com"
        assert user.name == "Bob"

        # And also this pattern:
        # users = await ChainUser.where(active=True).limit(10).all()
        users = await ChainUser.where(active=True).limit(10).all()

        assert len(users) == 3
        assert all(u.active for u in users)


@pytest.mark.asyncio
async def test_where_no_results(app_with_database):
    """Test chaining when no results match."""
    from zenith.testing import TestClient

    app = app_with_database

    async with TestClient(app):
        # Query with no matches
        user = await ChainUser.where(email="nobody@example.com").first()
        users = await ChainUser.where(active=False).all()
        count = await ChainUser.where(email="nobody@example.com").count()

        assert user is None
        assert users == []
        assert count == 0
