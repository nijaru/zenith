"""
Rails-like model extensions for SQLModel.

Provides ActiveRecord-style convenience methods for database operations
while maintaining SQLModel's type safety and FastAPI integration.
"""

from __future__ import annotations

from typing import Any, Self, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel, select

from ..exceptions import NotFoundError

__all__ = ["NotFoundError", "QueryBuilder", "ZenithModel"]

ModelType = TypeVar("ModelType", bound="ZenithModel")


class QueryBuilder[ModelType: "ZenithModel"]:
    """
    Rails-inspired query builder for chaining database operations.

    Supports lazy session initialization for seamless chaining:
        users = await User.where(active=True).order_by('-created_at').limit(10).all()
        user = await User.where(email="test@example.com").first()

    Example usage:
        users = await User.where(active=True).order_by('-created_at').limit(10)
        posts = await Post.where(published=True).includes('author').all()
    """

    def __init__(
        self,
        model_class: type[ModelType],
        session: AsyncSession | None = None,
        session_getter=None,
    ):
        self.model_class = model_class
        self.session = session
        self._session_getter = session_getter
        self._query = select(model_class)
        self._includes: list[str] = []

    async def _ensure_session(self) -> AsyncSession:
        """Get or fetch the session lazily when needed."""
        if self.session is None:
            if self._session_getter:
                self.session = await self._session_getter()
            else:
                raise RuntimeError(
                    f"No session available for {self.model_class.__name__}. "
                    "Ensure database is configured and session context is set."
                )
        return self.session

    def where(self, **conditions) -> QueryBuilder[ModelType]:
        """Add WHERE conditions to the query."""
        for key, value in conditions.items():
            if hasattr(self.model_class, key):
                attr = getattr(self.model_class, key)
                self._query = self._query.where(attr == value)
        return self

    def order_by(self, *columns: str) -> QueryBuilder[ModelType]:
        """Add ORDER BY clauses. Use '-column' for DESC order."""
        for column in columns:
            desc = False
            if column.startswith("-"):
                desc = True
                column = column[1:]

            if not hasattr(self.model_class, column):
                raise ValueError(
                    f"Invalid order_by column '{column}' for {self.model_class.__name__}. "
                    f"Available columns: {', '.join(self.model_class.model_fields.keys())}"
                )

            attr = getattr(self.model_class, column)
            if desc:
                self._query = self._query.order_by(attr.desc())
            else:
                self._query = self._query.order_by(attr)
        return self

    def limit(self, count: int) -> QueryBuilder[ModelType]:
        """Limit the number of results."""
        self._query = self._query.limit(count)
        return self

    def offset(self, count: int) -> QueryBuilder[ModelType]:
        """Skip the first 'count' results."""
        self._query = self._query.offset(count)
        return self

    def includes(self, *relationships: str) -> QueryBuilder[ModelType]:
        """Eagerly load relationships (Rails-style includes)."""
        for rel in relationships:
            if hasattr(self.model_class, rel):
                attr = getattr(self.model_class, rel)
                # Use selectinload for better performance with async
                self._query = self._query.options(selectinload(attr))
                # Track included relationships
                self._includes.append(rel)
        return self

    async def all(self) -> list[ModelType]:
        """Execute query and return all results."""
        session = await self._ensure_session()
        result = await session.execute(self._query)
        return list(result.scalars().all())

    async def first(self) -> ModelType | None:
        """Execute query and return first result or None."""
        session = await self._ensure_session()
        self._query = self._query.limit(1)
        result = await session.execute(self._query)
        return result.scalars().first()

    async def count(self) -> int:
        """Count the number of records matching the query."""
        from sqlalchemy import func

        session = await self._ensure_session()
        # Use subquery approach to preserve all filters, limits, joins
        # This ensures count matches the actual query results
        count_query = select(func.count()).select_from(self._query.subquery())
        result = await session.execute(count_query)
        return result.scalar() or 0

    async def exists(self) -> bool:
        """Check if any records match the query."""
        from sqlalchemy import exists as sql_exists

        session = await self._ensure_session()
        exists_query = select(sql_exists(self._query))
        result = await session.execute(exists_query)
        return result.scalar() or False

    def __aiter__(self):
        """Support async iteration over results."""
        return self._async_iter()

    async def _async_iter(self):
        """Async iterator implementation."""
        results = await self.all()
        for result in results:
            yield result


class ZenithModel(SQLModel):
    """
    Extended SQLModel with Rails-like ActiveRecord methods.

    Provides convenient database operations while maintaining
    SQLModel's type safety and FastAPI compatibility.

    Example usage:
        # Create
        user = await User.create(name="Alice", email="alice@example.com")

        # Find
        user = await User.find(123)
        user = await User.find_or_404(123)
        users = await User.where(active=True).limit(10)

        # Update
        await user.update(name="Alice Smith")

        # Delete
        await user.destroy()

        # Count
        count = await User.count()
    """

    @classmethod
    async def _get_session(cls) -> AsyncSession:
        """
        Get the current database session with seamless integration.

        Automatically uses:
        1. Request-scoped session (set by Zenith app middleware)
        2. Manually set session context (via set_current_db_session)
        3. Falls back to creating new session from container

        This enables seamless integration with Zenith app - no manual session management needed!

        Raises:
            RuntimeError: If no database session is available
        """
        from ..core.container import get_current_db_session

        current_session = get_current_db_session()
        if current_session is not None:
            return current_session

        from ..core.container import get_db_session

        session = await get_db_session()
        if session is None:
            raise RuntimeError(
                "No database session available. Ensure you're using ZenithModel within a web request context, "
                "or manually set the database session with set_current_db_session()."
            )
        return session

    @classmethod
    async def all(cls) -> list[Self]:
        """
        Get all records of this model.

        Returns:
            List of all model instances

        Example:
            users = await User.all()
        """
        session = await cls._get_session()
        result = await session.execute(select(cls))
        return list(result.scalars().all())

    @classmethod
    async def first(cls) -> Self | None:
        """
        Get the first record of this model.

        Returns:
            First model instance or None if no records

        Example:
            user = await User.first()
        """
        session = await cls._get_session()
        result = await session.execute(select(cls).limit(1))
        return result.scalars().first()

    @classmethod
    async def find(cls, id: Any) -> Self | None:
        """
        Find a record by primary key.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found

        Example:
            user = await User.find(123)
            if user:
                print(user.name)
        """
        session = await cls._get_session()
        return await session.get(cls, id)

    @classmethod
    async def find_or_404(cls, id: Any) -> Self:
        """
        Find a record by primary key or raise 404 error.

        Args:
            id: Primary key value

        Returns:
            Model instance

        Raises:
            NotFoundError: If record not found

        Example:
            user = await User.find_or_404(123)  # Always returns user or raises 404
        """
        record = await cls.find(id)
        if record is None:
            raise NotFoundError(f"{cls.__name__} with id {id} not found")
        return record

    @classmethod
    async def find_by(cls, **conditions) -> Self | None:
        """
        Find first record matching conditions.

        Args:
            **conditions: Field conditions to match

        Returns:
            First matching model instance or None

        Example:
            user = await User.find_by(email="alice@example.com")
        """
        builder = cls.where(**conditions)
        return await builder.first()

    @classmethod
    async def find_by_or_404(cls, **conditions) -> Self:
        """
        Find first record matching conditions or raise 404 error.

        Args:
            **conditions: Field conditions to match

        Returns:
            First matching model instance

        Raises:
            NotFoundError: If no record found

        Example:
            user = await User.find_by_or_404(email="alice@example.com")
        """
        record = await cls.find_by(**conditions)
        if record is None:
            condition_str = ", ".join(f"{k}={v}" for k, v in conditions.items())
            raise NotFoundError(f"{cls.__name__} with {condition_str} not found")
        return record

    @classmethod
    def where(cls, **conditions) -> QueryBuilder[Self]:
        """
        Start a query with WHERE conditions (synchronous for chaining).

        Sessions are fetched lazily when executing terminal methods.

        Args:
            **conditions: Field conditions to match

        Returns:
            QueryBuilder for chaining more conditions

        Example:
            # Chaining works seamlessly:
            users = await User.where(active=True).order_by('-created_at').limit(10).all()
            user = await User.where(email="test@example.com").first()
            count = await User.where(active=True).count()
        """
        builder = QueryBuilder(cls, session=None, session_getter=cls._get_session)
        return builder.where(**conditions)

    @classmethod
    async def create(cls, **data) -> Self:
        """
        Create and save a new record.

        Args:
            **data: Field values for the new record

        Returns:
            Created model instance

        Example:
            user = await User.create(name="Alice", email="alice@example.com")
        """
        session = await cls._get_session()
        instance = cls(**data)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    @classmethod
    async def count(cls) -> int:
        """
        Count all records of this model.

        Returns:
            Total number of records

        Example:
            user_count = await User.count()
        """
        from sqlalchemy import func

        session = await cls._get_session()
        result = await session.execute(select(func.count(cls.id)))
        return result.scalar() or 0

    @classmethod
    async def exists(cls, **conditions) -> bool:
        """
        Check if any records exist matching conditions.

        Args:
            **conditions: Field conditions to match

        Returns:
            True if matching records exist

        Example:
            exists = await User.exists(email="alice@example.com")
        """
        builder = cls.where(**conditions)
        return await builder.exists()

    async def save(self) -> Self:
        """
        Save this instance to the database.

        Returns:
            Self for method chaining

        Example:
            user.name = "Updated Name"
            await user.save()
        """
        session = await self._get_session()
        session.add(self)
        await session.commit()
        await session.refresh(self)
        return self

    async def update(self, **data) -> Self:
        """
        Update this instance with new data and save.

        Args:
            **data: Field values to update

        Returns:
            Self for method chaining

        Example:
            await user.update(name="Alice Smith", active=False)
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return await self.save()

    async def destroy(self) -> bool:
        """
        Delete this record from the database.

        Returns:
            True if deletion was successful

        Example:
            await user.destroy()
        """
        session = await self._get_session()
        await session.delete(self)
        await session.commit()
        return True

    async def reload(self) -> Self:
        """
        Reload this instance from the database.

        Returns:
            Self with fresh data from database

        Example:
            user = await user.reload()  # Get latest data
        """
        session = await self._get_session()
        await session.refresh(self)
        return self
