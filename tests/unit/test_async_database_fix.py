"""
Test that verifies the async database event loop binding bug is fixed.

This tests the critical bug where async engines would fail with
"Future attached to a different loop" errors.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from zenith.db import Database


@pytest.mark.asyncio
async def test_async_database_different_event_loops():
    """
    Test that the database works across different event loops.

    This simulates the exact scenario that causes the bug:
    1. Create database in one event loop (startup)
    2. Use it in a different event loop (request handler)
    """
    # Use an in-memory SQLite database for testing
    db = Database("sqlite+aiosqlite:///:memory:")

    # Simulate startup - create tables in one event loop
    async def startup():
        await db.create_all()
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    # Simulate request handler - use database in different event loop
    async def request_handler():
        async with db.session() as session:
            result = await session.execute(text("SELECT 2"))
            assert result.scalar() == 2

    # Run startup in one event loop
    await startup()

    # Run request handler in a NEW event loop (this would fail with the bug)
    # We simulate this by running in a thread with its own event loop
    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(request_handler())
        finally:
            loop.close()

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_new_loop)
        future.result()  # This would raise "Future attached to different loop" with the bug

    # Clean up
    await db.close()


@pytest.mark.asyncio
async def test_multiple_concurrent_requests():
    """
    Test that multiple concurrent requests work correctly.

    Each request should get its own session without interference.
    """
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()

    async def make_request(request_id: int) -> int:
        """Simulate a request that uses the database."""
        async with db.session() as session:
            # Each request should work independently
            result = await session.execute(text(f"SELECT {request_id}"))
            return result.scalar()

    # Run multiple concurrent requests
    tasks = [make_request(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all requests completed successfully
    assert results == list(range(10))

    await db.close()


@pytest.mark.asyncio
async def test_request_scoped_session():
    """
    Test that request-scoped sessions work correctly.
    """
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()

    # Simulate a request scope
    scope = {}

    # First use creates the session
    async with db.request_scoped_session(scope) as session1:
        assert "db_session" in scope
        result = await session1.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Second use within same scope reuses the session
        async with db.request_scoped_session(scope) as session2:
            assert session1 is session2  # Same session object
            result = await session2.execute(text("SELECT 2"))
            assert result.scalar() == 2

    # After request, session is cleaned up
    assert "db_session" not in scope

    await db.close()


@pytest.mark.asyncio
async def test_transaction_rollback():
    """
    Test that transactions properly rollback on error.
    """
    db = Database("sqlite+aiosqlite:///:memory:")

    # Create a simple table for testing
    async with db.engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
        """))

    # Test transaction rollback
    with pytest.raises(Exception):
        async with db.transaction() as session:
            await session.execute(text("INSERT INTO test_table (value) VALUES ('test')"))
            # Force an error to trigger rollback
            raise Exception("Test error")

    # Verify the insert was rolled back
    async with db.session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM test_table"))
        count = result.scalar()
        assert count == 0

    await db.close()


@pytest.mark.asyncio
async def test_health_check():
    """
    Test that health check works correctly.
    """
    db = Database("sqlite+aiosqlite:///:memory:")

    # Health check should work
    is_healthy = await db.health_check()
    assert is_healthy is True

    await db.close()




@pytest.mark.asyncio
async def test_engine_per_loop_isolation():
    """
    Test that each event loop gets its own engine instance.
    """
    db = Database("sqlite+aiosqlite:///:memory:")

    # Get engine in main loop
    engine1 = db.engine
    engine1_id = id(engine1)

    # Get engine in a different loop
    def get_engine_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # This should create a NEW engine instance
            engine2 = db.engine
            return id(engine2)
        finally:
            loop.close()

    with ThreadPoolExecutor() as executor:
        future = executor.submit(get_engine_in_new_loop)
        engine2_id = future.result()

    # Verify different engine instances for different loops
    assert engine1_id != engine2_id

    await db.close()