"""
SQLModel integration for Zenith Framework.

Provides seamless integration between SQLModel and Zenith's database system,
enabling unified Pydantic + SQLAlchemy models for clean architecture.
"""

from typing import Type, TypeVar, Generic, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlmodel import SQLModel, Field
from pydantic import ConfigDict

T = TypeVar('T', bound=SQLModel)


class SQLModelRepository(Generic[T]):
    """
    Generic repository for SQLModel entities.
    
    Provides common CRUD operations with async/await support
    and integrates cleanly with Zenith's Context pattern.
    """
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
    
    async def create(self, obj: T) -> T:
        """Create a new entity."""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
    
    async def get(self, id: Any, with_relations: list[str] | None = None) -> T | None:
        """Get entity by ID with optional relationship loading."""
        if not with_relations:
            return await self.session.get(self.model, id)
        
        # Use select with relationship loading for complex cases
        from sqlalchemy.orm import selectinload
        stmt = select(self.model).where(self.model.id == id)
        for relation in with_relations:
            stmt = stmt.options(selectinload(getattr(self.model, relation)))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by(self, with_relations: list[str] | None = None, **filters) -> T | None:
        """Get entity by filters with optional relationship loading."""
        stmt = select(self.model)
        
        # Apply filters
        for key, value in filters.items():
            if key != 'with_relations':  # Skip the relations parameter
                stmt = stmt.where(getattr(self.model, key) == value)
        
        # Add relationship loading if specified
        if with_relations:
            from sqlalchemy.orm import selectinload
            for relation in with_relations:
                stmt = stmt.options(selectinload(getattr(self.model, relation)))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list(self, offset: int = 0, limit: int = 100, with_relations: list[str] | None = None, **filters) -> list[T]:
        """List entities with pagination, filtering, and optional relationship loading."""
        stmt = select(self.model).offset(offset).limit(limit)
        
        # Apply filters
        for key, value in filters.items():
            if key != 'with_relations' and hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        
        # Add relationship loading if specified
        if with_relations:
            from sqlalchemy.orm import selectinload
            for relation in with_relations:
                stmt = stmt.options(selectinload(getattr(self.model, relation)))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update(self, id: Any, **values) -> T | None:
        """Update entity by ID."""
        stmt = update(self.model).where(self.model.id == id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get(id)
    
    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class ZenithSQLModel(SQLModel):
    """
    Base SQLModel class with Zenith-specific enhancements.
    
    Provides common fields and utilities for all Zenith SQLModel entities.
    """
    
    id: int | None = Field(default=None, primary_key=True)
    
    model_config = ConfigDict(
        # Enable ORM mode for Pydantic compatibility
        from_attributes=True,
        # Use enum values for serialization
        use_enum_values=True,
        # Validate assignment
        validate_assignment=True
    )


def create_repository(session: AsyncSession, model: Type[T]) -> SQLModelRepository[T]:
    """
    Factory function to create repository instances.
    
    Usage in Context classes:
    
    ```python
    from zenith import Context
    from zenith.db.sqlmodel import create_repository
    
    class UserService(Context):
        def __init__(self, container):
            super().__init__(container)
            self.db = container.get(AsyncSession)
            self.users = create_repository(self.db, User)
        
        async def create_user(self, user_data: UserCreate) -> User:
            user = User(**user_data.model_dump())
            return await self.users.create(user)
    ```
    """
    return SQLModelRepository(session, model)


# Re-export SQLModel components for convenience
from sqlmodel import SQLModel, Field, Relationship, Session, select

__all__ = [
    "SQLModel",
    "Field", 
    "Relationship",
    "Session",
    "select",
    "ZenithSQLModel",
    "SQLModelRepository",
    "create_repository",
]