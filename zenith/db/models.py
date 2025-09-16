"""
Rails-like model extensions for SQLModel.

Provides ActiveRecord-style convenience methods for database operations
while maintaining SQLModel's type safety and FastAPI integration.
"""

from __future__ import annotations

from typing import Any, Generic, Self, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel, select

# Avoid circular imports by importing only when needed
# from ..web.responses import JSONResponse  # Not needed yet
from ..exceptions import HTTPException


class NotFoundError(HTTPException):
    """Exception raised when a database record is not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


__all__ = ["QueryBuilder", "ZenithModel"]

ModelType = TypeVar("ModelType", bound="ZenithModel")


class QueryBuilder(Generic[ModelType]):
    """
    Rails-inspired query builder for chaining database operations.

    Example usage:
        users = await User.where(active=True).order_by('-created_at').limit(10)
        posts = await Post.where(published=True).includes('author').all()
    """

    def __init__(self, model_class: type[ModelType], session: AsyncSession):
        self.model_class = model_class
        self.session = session
        self._query = select(model_class)
        self._includes: list[str] = []

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
            if column.startswith('-'):
                column = column[1:]
                if hasattr(self.model_class, column):
                    attr = getattr(self.model_class, column)
                    self._query = self._query.order_by(attr.desc())
            else:
                if hasattr(self.model_class, column):
                    attr = getattr(self.model_class, column)
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
        result = await self.session.execute(self._query)
        return list(result.scalars().all())

    async def first(self) -> ModelType | None:
        """Execute query and return first result or None."""
        self._query = self._query.limit(1)
        result = await self.session.execute(self._query)
        return result.scalars().first()

    async def count(self) -> int:
        """Count the number of records matching the query."""
        from sqlalchemy import func
        count_query = select(func.count()).select_from(self._query.subquery())
        result = await self.session.execute(count_query)
        return result.scalar() or 0

    async def exists(self) -> bool:
        """Check if any records match the query."""
        from sqlalchemy import exists as sql_exists
        exists_query = select(sql_exists(self._query))
        result = await self.session.execute(exists_query)
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
        """
        # First check for current session (set by app middleware or manually)
        from ..core.container import get_current_db_session
        current_session = get_current_db_session()
        if current_session is not None:
            return current_session

        # Fall back to container session
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
        builder = await cls.where(**conditions)
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
    async def where(cls, **conditions) -> QueryBuilder[Self]:
        """
        Start a query with WHERE conditions.

        Args:
            **conditions: Field conditions to match

        Returns:
            QueryBuilder for chaining more conditions

        Example:
            users = await User.where(active=True).order_by('-created_at').limit(10)
        """
        session = await cls._get_session()
        builder = QueryBuilder(cls, session)
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
        builder = await cls.where(**conditions)
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

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            exclude: Set of field names to exclude

        Returns:
            Dictionary representation of the model

        Example:
            user_data = user.to_dict(exclude={'password_hash'})
        """
        exclude = exclude or set()
        return {
            field: getattr(self, field)
            for field in self.__class__.model_fields
            if field not in exclude
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create model instance from dictionary data.

        Args:
            data: Dictionary with model field data

        Returns:
            Model instance (not yet saved)

        Example:
            user = User.from_dict({"name": "Alice", "email": "alice@example.com"})
            await user.save()
        """
        return cls(**data)
