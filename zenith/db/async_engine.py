"""
Async database engine management for Zenith.

Solves the critical event loop binding issue with async SQLAlchemy engines.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any
from weakref import WeakKeyDictionary

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Context variable to store engine per event loop
_engines: WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncEngine] = (
    WeakKeyDictionary()
)
_engine_config: ContextVar[dict[str, Any] | None] = ContextVar(
    "engine_config", default=None
)


class AsyncEngineManager:
    """
    Manages async database engines per event loop.

    This solves the "Future attached to a different loop" error by ensuring
    each event loop gets its own engine instance.
    """

    def __init__(self, database_url: str, **engine_kwargs):
        """
        Initialize the engine manager.

        Args:
            database_url: Database connection URL
            **engine_kwargs: Additional arguments for create_async_engine
        """
        self.database_url = database_url
        self.engine_kwargs = engine_kwargs
        self._engines: WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncEngine] = (
            WeakKeyDictionary()
        )
        self._session_makers: WeakKeyDictionary[
            asyncio.AbstractEventLoop, async_sessionmaker
        ] = WeakKeyDictionary()

    def get_engine(self) -> AsyncEngine:
        """
        Get or create an engine for the current event loop.

        Returns:
            AsyncEngine instance for the current loop
        """
        loop = asyncio.get_event_loop()

        if loop not in self._engines:
            # Create new engine for this event loop
            engine = create_async_engine(self.database_url, **self.engine_kwargs)
            self._engines[loop] = engine

        return self._engines[loop]

    def get_session_maker(self) -> async_sessionmaker:
        """
        Get or create a session maker for the current event loop.

        Returns:
            async_sessionmaker instance for the current loop
        """
        loop = asyncio.get_event_loop()

        if loop not in self._session_makers:
            engine = self.get_engine()
            session_maker = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            self._session_makers[loop] = session_maker

        return self._session_makers[loop]

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session for the current request.

        Yields:
            AsyncSession instance
        """
        session_maker = self.get_session_maker()
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def dispose_all(self):
        """Dispose all engines (cleanup)."""
        for engine in self._engines.values():
            await engine.dispose()
        self._engines.clear()
        self._session_makers.clear()

    async def dispose_current(self):
        """Dispose the engine for the current event loop."""
        loop = asyncio.get_event_loop()
        if loop in self._engines:
            await self._engines[loop].dispose()
            del self._engines[loop]
        if loop in self._session_makers:
            del self._session_makers[loop]


# Global engine manager instance
_engine_manager: AsyncEngineManager | None = None


def init_async_engine(database_url: str, **engine_kwargs) -> AsyncEngineManager:
    """
    Initialize the global async engine manager.

    Args:
        database_url: Database connection URL
        **engine_kwargs: Additional arguments for create_async_engine

    Returns:
        AsyncEngineManager instance
    """
    global _engine_manager
    _engine_manager = AsyncEngineManager(database_url, **engine_kwargs)
    return _engine_manager


def get_async_engine_manager() -> AsyncEngineManager:
    """
    Get the global async engine manager.

    Returns:
        AsyncEngineManager instance

    Raises:
        RuntimeError: If engine manager not initialized
    """
    if _engine_manager is None:
        raise RuntimeError(
            "Async engine not initialized. Call init_async_engine() first."
        )
    return _engine_manager


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an async database session.

    This can be used with Zenith's dependency injection:

    ```python
    from zenith import Depends
    from zenith.db.async_engine import get_async_session

    @app.get("/users")
    async def get_users(db: AsyncSession = Depends(get_async_session)):
        result = await db.execute(select(User))
        return result.scalars().all()
    ```

    Yields:
        AsyncSession instance
    """
    manager = get_async_engine_manager()
    async for session in manager.get_session():
        yield session


class AsyncDatabase:
    """
    High-level async database interface for Zenith applications.

    Example:
        ```python
        from zenith.db import AsyncDatabase

        db = AsyncDatabase("postgresql+asyncpg://...")

        @app.on_event("startup")
        async def startup():
            await db.connect()

        @app.on_event("shutdown")
        async def shutdown():
            await db.disconnect()

        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(db.get_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
        ```
    """

    def __init__(self, database_url: str, **engine_kwargs):
        """
        Initialize the async database.

        Args:
            database_url: Database connection URL
            **engine_kwargs: Additional arguments for create_async_engine
        """
        self.manager = AsyncEngineManager(database_url, **engine_kwargs)

    async def connect(self):
        """Connect to the database (initialize engine for current loop)."""
        # This ensures the engine is created for the startup loop
        self.manager.get_engine()

    async def disconnect(self):
        """Disconnect from the database (dispose all engines)."""
        await self.manager.dispose_all()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session.

        Yields:
            AsyncSession instance
        """
        async for session in self.manager.get_session():
            yield session

    @property
    def session(self):
        """Dependency injection helper for session."""
        return self.get_session
