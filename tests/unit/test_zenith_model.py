"""
Tests for ZenithModel - Rails-like ActiveRecord functionality.

Comprehensive test coverage for all ZenithModel features:
- Basic CRUD operations
- Rails-like query methods
- QueryBuilder chaining
- Automatic session management
- Error handling and 404s
"""

import pytest
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch

from sqlmodel import Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from zenith.db.models import ZenithModel, QueryBuilder, NotFoundError
from zenith.core.container import set_current_db_session


# Test models for testing (renamed to avoid pytest collection issues)
class UserModel(ZenithModel, table=True):
    """Test user model."""

    __tablename__ = "test_users"

    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
    active: bool = Field(default=True)
    age: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)


class PostModel(ZenithModel, table=True):
    """Test post model."""

    __tablename__ = "test_posts"

    id: Optional[int] = Field(primary_key=True)
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    user_id: int = Field(foreign_key="test_users.id")
    created_at: datetime = Field(default_factory=datetime.now)


class TestZenithModel:
    """Test ZenithModel basic functionality."""

    @pytest.fixture
    async def mock_session(self):
        """Mock AsyncSession for testing."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    async def mock_session_context(self, mock_session):
        """Set up session in context."""
        set_current_db_session(mock_session)
        yield mock_session
        set_current_db_session(None)

    async def test_get_session_from_context(self, mock_session_context):
        """Test that _get_session retrieves session from context."""
        session = await UserModel._get_session()
        assert session == mock_session_context

    async def test_get_session_fallback_to_container(self):
        """Test _get_session falls back to container when no context session."""
        with patch("zenith.core.container.get_db_session") as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value = mock_session

            session = await UserModel._get_session()

            assert session == mock_session
            mock_get_db.assert_called_once()

    async def test_get_session_raises_error_when_no_session(self):
        """Test _get_session raises error when no session available."""
        with patch("zenith.core.container.get_db_session") as mock_get_db:
            mock_get_db.return_value = None

            with pytest.raises(RuntimeError) as exc_info:
                await UserModel._get_session()

            assert "No database session available" in str(exc_info.value)


class TestZenithModelCRUD:
    """Test CRUD operations."""

    @pytest.fixture
    async def mock_session(self):
        """Mock AsyncSession for CRUD tests."""
        session = AsyncMock(spec=AsyncSession)
        set_current_db_session(session)
        yield session
        set_current_db_session(None)

    async def test_all_method(self, mock_session):
        """Test User.all() returns all records."""
        # Mock execute result
        mock_result = Mock()
        mock_scalars = Mock()
        mock_user1 = UserModel(id=1, name="Alice", email="alice@example.com")
        mock_user2 = UserModel(id=2, name="Bob", email="bob@example.com")
        mock_scalars.all.return_value = [mock_user1, mock_user2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        users = await UserModel.all()

        assert len(users) == 2
        assert users[0].name == "Alice"
        assert users[1].name == "Bob"
        mock_session.execute.assert_called_once()

    async def test_find_method_success(self, mock_session):
        """Test User.find(id) finds user by ID."""
        mock_user = UserModel(id=1, name="Alice", email="alice@example.com")
        mock_session.get.return_value = mock_user

        user = await UserModel.find(1)

        assert user is not None
        assert user.name == "Alice"
        mock_session.get.assert_called_once_with(UserModel, 1)

    async def test_find_method_not_found(self, mock_session):
        """Test User.find(id) returns None when not found."""
        mock_session.get.return_value = None

        user = await UserModel.find(999)

        assert user is None
        mock_session.get.assert_called_once_with(UserModel, 999)

    async def test_find_or_404_success(self, mock_session):
        """Test User.find_or_404(id) returns user when found."""
        mock_user = UserModel(id=1, name="Alice", email="alice@example.com")
        mock_session.get.return_value = mock_user

        user = await UserModel.find_or_404(1)

        assert user.name == "Alice"

    async def test_find_or_404_raises_not_found(self, mock_session):
        """Test User.find_or_404(id) raises NotFoundError when not found."""
        mock_session.get.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await UserModel.find_or_404(999)

        assert "UserModel with id 999 not found" in str(exc_info.value)

    async def test_first_method(self, mock_session):
        """Test User.first() returns first record."""
        mock_result = Mock()
        mock_scalars = Mock()
        mock_user = UserModel(id=1, name="Alice", email="alice@example.com")
        mock_scalars.first.return_value = mock_user
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        user = await UserModel.first()

        assert user is not None
        assert user.name == "Alice"

    async def test_first_method_empty_result(self, mock_session):
        """Test User.first() returns None when no records."""
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        user = await UserModel.first()

        assert user is None

    async def test_create_method(self, mock_session):
        """Test User.create(**data) creates new record."""
        # Mock session operations
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Test create method
        user = await UserModel.create(name="Alice", email="alice@example.com")

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify user data
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    async def test_count_method(self, mock_session):
        """Test User.count() returns record count."""
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        count = await UserModel.count()

        assert count == 5
        mock_session.execute.assert_called_once()

    async def test_count_method_zero_result(self, mock_session):
        """Test User.count() handles zero/None result."""
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        count = await UserModel.count()

        assert count == 0

    async def test_exists_method_true(self, mock_session):
        """Test User.exists(**conditions) returns True when records exist."""
        # Mock the exists query result
        mock_result = Mock()
        mock_result.scalar.return_value = True
        mock_session.execute.return_value = mock_result

        exists = await UserModel.exists(name="Alice")

        assert exists is True

    async def test_exists_method_false(self, mock_session):
        """Test User.exists(**conditions) returns False when no records."""
        # Mock the exists query result
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        exists = await UserModel.exists(name="NonExistent")

        assert exists is False

    async def test_instance_save_method(self, mock_session):
        """Test user.save() saves instance."""
        user = UserModel(name="Alice", email="alice@example.com")

        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await user.save()

        assert result is user  # Returns self for chaining
        mock_session.add.assert_called_once_with(user)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(user)

    async def test_instance_update_method(self, mock_session):
        """Test user.update(**data) updates instance."""
        user = UserModel(id=1, name="Alice", email="alice@example.com")

        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await user.update(name="Updated Alice", active=False)

        assert result is user  # Returns self for chaining
        assert user.name == "Updated Alice"
        assert user.active is False
        mock_session.add.assert_called_once_with(user)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(user)

    async def test_instance_destroy_method(self, mock_session):
        """Test user.destroy() deletes instance."""
        user = UserModel(id=1, name="Alice", email="alice@example.com")

        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        result = await user.destroy()

        assert result is True
        mock_session.delete.assert_called_once_with(user)
        mock_session.commit.assert_called_once()

    async def test_instance_reload_method(self, mock_session):
        """Test user.reload() refreshes instance from database."""
        user = UserModel(id=1, name="Alice", email="alice@example.com")

        mock_session.refresh = AsyncMock()

        result = await user.reload()

        assert result is user  # Returns self for chaining
        mock_session.refresh.assert_called_once_with(user)

    def test_to_dict_method(self):
        """Test user.to_dict() converts to dictionary."""
        user = UserModel(
            id=1, name="Alice", email="alice@example.com", active=True, age=25
        )

        data = user.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == 1
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"
        assert data["active"] is True
        assert data["age"] == 25

    def test_to_dict_method_with_exclude(self):
        """Test user.to_dict(exclude=set) excludes specified fields."""
        user = UserModel(
            id=1, name="Alice", email="alice@example.com", active=True, age=25
        )

        data = user.to_dict(exclude={"email", "age"})

        assert "email" not in data
        assert "age" not in data
        assert data["id"] == 1
        assert data["name"] == "Alice"
        assert data["active"] is True


class TestQueryBuilder:
    """Test QueryBuilder chaining functionality."""

    @pytest.fixture
    async def mock_session(self):
        """Mock AsyncSession for QueryBuilder tests."""
        session = AsyncMock(spec=AsyncSession)
        return session

    async def test_where_method_single_condition(self, mock_session):
        """Test QueryBuilder.where() with single condition."""
        builder = QueryBuilder(UserModel, mock_session)

        result = builder.where(active=True)

        assert result is builder  # Returns self for chaining
        assert isinstance(result, QueryBuilder)

    async def test_where_method_multiple_conditions(self, mock_session):
        """Test QueryBuilder.where() with multiple conditions."""
        builder = QueryBuilder(UserModel, mock_session)

        result = builder.where(active=True, age=25)

        assert result is builder  # Returns self for chaining

    async def test_order_by_ascending(self, mock_session):
        """Test QueryBuilder.order_by() with ascending order."""
        builder = QueryBuilder(UserModel, mock_session)

        result = builder.order_by("name")

        assert result is builder  # Returns self for chaining

    async def test_order_by_descending(self, mock_session):
        """Test QueryBuilder.order_by() with descending order."""
        builder = QueryBuilder(UserModel, mock_session)

        result = builder.order_by("-created_at")

        assert result is builder  # Returns self for chaining

    async def test_order_by_invalid_column(self, mock_session):
        """Test QueryBuilder.order_by() with invalid column name."""
        builder = QueryBuilder(UserModel, mock_session)

        # Should raise ValueError for non-existent column
        with pytest.raises(
            ValueError, match="Invalid order_by column 'invalid_column' for UserModel"
        ):
            builder.order_by("invalid_column")

    async def test_order_by_invalid_column_descending(self, mock_session):
        """Test QueryBuilder.order_by() with invalid descending column."""
        builder = QueryBuilder(UserModel, mock_session)

        # Should raise ValueError even with - prefix
        with pytest.raises(
            ValueError, match="Invalid order_by column 'nonexistent' for UserModel"
        ):
            builder.order_by("-nonexistent")

    async def test_limit_method(self, mock_session):
        """Test QueryBuilder.limit() method."""
        builder = QueryBuilder(UserModel, mock_session)

        result = builder.limit(10)

        assert result is builder  # Returns self for chaining

    async def test_offset_method(self, mock_session):
        """Test QueryBuilder.offset() method."""
        builder = QueryBuilder(UserModel, mock_session)

        result = builder.offset(20)

        assert result is builder  # Returns self for chaining

    async def test_includes_method(self, mock_session):
        """Test QueryBuilder.includes() for eager loading."""
        builder = QueryBuilder(UserModel, mock_session)

        # Test with a field that doesn't exist - should not be added to includes
        result = builder.includes("nonexistent_field")
        assert result is builder  # Returns self for chaining
        assert "nonexistent_field" not in builder._includes

        # Test with a field that does exist on the model
        result = builder.includes("name")  # 'name' is a real field on UserModel
        assert result is builder  # Returns self for chaining
        # Note: 'name' is a simple field, not a relationship, so it won't be added to _includes
        # This tests the hasattr check works correctly

    async def test_method_chaining(self, mock_session):
        """Test that QueryBuilder methods can be chained."""
        builder = QueryBuilder(UserModel, mock_session)

        result = (
            builder.where(active=True)
            .order_by("-created_at")
            .limit(10)
            .offset(20)
            .includes("nonexistent_relationship")
        )

        assert result is builder
        # Since 'nonexistent_relationship' doesn't exist, it won't be in _includes
        assert "nonexistent_relationship" not in builder._includes

    async def test_all_method_execution(self, mock_session):
        """Test QueryBuilder.all() executes query and returns results."""
        builder = QueryBuilder(UserModel, mock_session)
        builder.where(active=True)

        # Mock execution result
        mock_result = Mock()
        mock_scalars = Mock()
        mock_users = [
            UserModel(id=1, name="Alice", email="alice@example.com"),
            UserModel(id=2, name="Bob", email="bob@example.com"),
        ]
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        users = await builder.all()

        assert len(users) == 2
        assert users[0].name == "Alice"
        assert users[1].name == "Bob"
        mock_session.execute.assert_called_once()

    async def test_first_method_execution(self, mock_session):
        """Test QueryBuilder.first() executes query and returns first result."""
        builder = QueryBuilder(UserModel, mock_session)
        builder.where(active=True)

        # Mock execution result
        mock_result = Mock()
        mock_scalars = Mock()
        mock_user = UserModel(id=1, name="Alice", email="alice@example.com")
        mock_scalars.first.return_value = mock_user
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        user = await builder.first()

        assert user is not None
        assert user.name == "Alice"
        mock_session.execute.assert_called_once()

    async def test_count_method_execution(self, mock_session):
        """Test QueryBuilder.count() executes count query."""
        builder = QueryBuilder(UserModel, mock_session)
        builder.where(active=True)

        # Mock execution result
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        count = await builder.count()

        assert count == 5
        mock_session.execute.assert_called_once()


class TestZenithModelWhereMethod:
    """Test the static where method that returns QueryBuilder."""

    async def test_where_returns_query_builder(self):
        """Test that User.where() returns QueryBuilder instance."""
        with patch("zenith.core.container.get_current_db_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            builder = UserModel.where(active=True)

            assert isinstance(builder, QueryBuilder)
            assert builder.model_class == UserModel

    async def test_where_method_chaining_integration(self):
        """Test complete where method chaining integration."""
        with patch("zenith.core.container.get_current_db_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            # Mock execution result
            mock_result = Mock()
            mock_scalars = Mock()
            mock_users = [UserModel(id=1, name="Alice", email="alice@example.com")]
            mock_scalars.all.return_value = mock_users
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result

            # Test chaining: where -> order_by -> limit -> all
            builder = UserModel.where(active=True)
            users = await builder.order_by("-created_at").limit(10).all()

            assert len(users) == 1
            assert users[0].name == "Alice"
            mock_session.execute.assert_called_once()


class TestZenithModelErrorHandling:
    """Test error handling in ZenithModel."""

    async def test_not_found_error_message(self):
        """Test NotFoundError includes helpful message."""
        error = NotFoundError("User with ID 123 not found")

        assert "User with ID 123 not found" in str(error)

    async def test_session_error_handling(self):
        """Test proper error handling when session operations fail."""
        with patch("zenith.core.container.get_current_db_session") as mock_get_session:
            mock_get_session.return_value = None

            with patch("zenith.core.container.get_db_session") as mock_get_db:
                mock_get_db.return_value = None

                with pytest.raises(RuntimeError) as exc_info:
                    await UserModel.all()

                assert "No database session available" in str(exc_info.value)
                assert "set_current_db_session" in str(exc_info.value)


class TestZenithModelIntegration:
    """Integration tests for ZenithModel with real-like scenarios."""

    @pytest.fixture
    async def mock_session_context(self):
        """Set up a mock session context for integration tests."""
        session = AsyncMock(spec=AsyncSession)
        set_current_db_session(session)

        # Default mock behaviors for common operations
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()

        yield session

        set_current_db_session(None)

    async def test_complete_crud_workflow(self, mock_session_context):
        """Test complete CRUD workflow with ZenithModel."""
        # Create
        user = await UserModel.create(name="Alice", email="alice@example.com")
        mock_session_context.add.assert_called()
        mock_session_context.commit.assert_called()
        assert user.name == "Alice"

        # Mock find
        mock_session_context.get.return_value = user
        found_user = await UserModel.find(1)
        assert found_user is not None

        # Mock update
        await found_user.update(name="Alice Updated")
        assert found_user.name == "Alice Updated"

        # Mock delete
        result = await found_user.destroy()
        assert result is True
        mock_session_context.delete.assert_called_with(found_user)

    async def test_query_chaining_workflow(self, mock_session_context):
        """Test complex query chaining workflow."""
        # Mock query result
        mock_result = Mock()
        mock_scalars = Mock()
        mock_users = [
            UserModel(
                id=1, name="Alice", email="alice@example.com", active=True, age=25
            ),
            UserModel(id=2, name="Bob", email="bob@example.com", active=True, age=30),
        ]
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session_context.execute.return_value = mock_result

        # Execute complex query chain
        builder = UserModel.where(active=True, age__gte=18)  # Adults only
        users = await (
            builder.order_by("-created_at")  # Newest first
            .limit(10)  # Max 10 results
            .includes("posts")  # Eager load posts
            .all()
        )

        assert len(users) == 2
        assert all(user.active for user in users)
        mock_session_context.execute.assert_called_once()
