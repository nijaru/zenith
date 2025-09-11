"""
Database layer for Zenith framework.

Provides SQLAlchemy 2.0 integration with async support, session management,
and transaction handling for the context system.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Naming conventions for database constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all database models."""

    metadata = metadata


class Database:
    """
    Database connection and session management.

    Provides async database operations with proper session handling
    and transaction support for Zenith contexts.
    """

    def __init__(self, url: str, echo: bool = False, pool_size: int = 20):
        """
        Initialize database connection.

        Args:
            url: Database URL (postgresql+asyncpg://...)
            echo: Enable SQL logging
            pool_size: Connection pool size
        """
        self.url = url
        self.echo = echo
        self.pool_size = pool_size

        # Create async engine
        self.engine: AsyncEngine = create_async_engine(
            url,
            echo=echo,
            pool_size=pool_size,
            pool_pre_ping=True,  # Verify connections before using
        )

        # Create session factory
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a new database session.

        Usage:
            async with db.session() as session:
                user = User(name="Alice")
                session.add(user)
                await session.commit()
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a database transaction.

        Automatically rolls back on exception.

        Usage:
            async with db.transaction() as session:
                # All operations here are in a transaction
                user = User(name="Bob")
                session.add(user)
                # Commits automatically if no exception
        """
        async with self.session() as session, session.begin():
            yield session

    async def create_all(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self) -> None:
        """Drop all database tables. Use with caution!"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()

    async def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception:
            return False


# Import migration system
from .migrations import MigrationManager, create_migration_manager

# Import SQLModel integration
from .sqlmodel import (
    SQLModel,
    Field,
    Relationship,
    ZenithSQLModel,
    SQLModelRepository,
    create_repository,
)

# Export commonly used components
__all__ = [
    "AsyncSession",
    "Base",
    "Database",
    "MigrationManager",
    "async_sessionmaker", 
    "create_async_engine",
    "create_migration_manager",
    # SQLModel components
    "SQLModel",
    "Field",
    "Relationship", 
    "ZenithSQLModel",
    "SQLModelRepository",
    "create_repository",
]
