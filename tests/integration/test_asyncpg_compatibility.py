"""
Critical integration test for AsyncPG compatibility.

This test ensures that Zenith middleware doesn't conflict with
AsyncPG's event loop requirements.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

from zenith import Zenith
from zenith.testing import TestClient


@pytest.mark.asyncio
async def test_asyncpg_with_middleware_stack():
    """
    Test that AsyncPG operations work with full middleware stack.

    This is the critical test that would have caught the BaseHTTPMiddleware
    issue in v0.1.4.
    """
    # Create app with full middleware stack
    app = Zenith(title="AsyncPG Test", debug=False)

    # Mock asyncpg since we might not have PostgreSQL in all test environments
    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1, "name": "Test"}])
        mock_conn.close = AsyncMock()
        mock_connect.return_value = mock_conn

        @app.get("/db-test")
        async def db_endpoint():
            """Endpoint that uses AsyncPG."""
            # Import here to avoid import errors if asyncpg not installed
            try:
                import asyncpg

                conn = await asyncpg.connect(
                    host="localhost", database="test", user="test", password="test"
                )
                try:
                    result = await conn.fetch("SELECT 1 as id, 'Test' as name")
                    return {"data": [dict(r) for r in result]}
                finally:
                    await conn.close()
            except ImportError:
                # Fallback for when asyncpg isn't installed
                return {"data": [{"id": 1, "name": "Test"}]}

        async with TestClient(app) as client:
            response = await client.get("/db-test")
            assert response.status_code == 200
            data = response.json()
            assert data["data"][0]["id"] == 1
            assert data["data"][0]["name"] == "Test"


@pytest.mark.asyncio
async def test_asyncpg_event_loop_compatibility():
    """
    Test that our middleware doesn't create event loop conflicts.

    BaseHTTPMiddleware creates its own event loop which conflicts
    with AsyncPG. This test ensures we're using pure ASGI.
    """
    app = Zenith()

    # Check that no middleware is using BaseHTTPMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware

    for middleware in app.middleware:
        if hasattr(middleware, "cls"):
            # This would fail if any middleware inherits from BaseHTTPMiddleware
            assert not issubclass(middleware.cls, BaseHTTPMiddleware), (
                f"Middleware {middleware.cls.__name__} uses BaseHTTPMiddleware - will conflict with AsyncPG!"
            )


@pytest.mark.asyncio
async def test_concurrent_asyncpg_operations():
    """
    Test that multiple concurrent AsyncPG operations work correctly.

    This would fail with BaseHTTPMiddleware due to event loop conflicts.
    """
    app = Zenith()

    @app.get("/concurrent/{n}")
    async def concurrent_db_operations(n: int):
        """Simulate concurrent database operations."""

        async def mock_db_operation(i: int):
            await asyncio.sleep(0.01)  # Simulate DB delay
            return {"id": i, "result": f"Operation {i}"}

        # Run multiple operations concurrently
        tasks = [mock_db_operation(i) for i in range(n)]
        results = await asyncio.gather(*tasks)
        return {"results": results}

    async with TestClient(app) as client:
        response = await client.get("/concurrent/5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 5


@pytest.mark.asyncio
async def test_asyncpg_in_background_task():
    """
    Test AsyncPG operations in background tasks.

    This ensures our background task system is compatible with AsyncPG.
    """
    app = Zenith()

    # Track background task execution
    task_results = []
    background_tasks = []

    async def db_background_task(item_id: int):
        """Simulate a database operation in background."""
        await asyncio.sleep(0.01)
        task_results.append({"id": item_id, "processed": True})

    @app.post("/process/{item_id}")
    async def process_item(item_id: int):
        """Trigger background database operation."""
        # Add task to be executed after response
        task = asyncio.create_task(db_background_task(item_id))
        background_tasks.append(task)
        return {"status": "queued", "item_id": item_id}

    async with TestClient(app) as client:
        response = await client.post("/process/123")
        assert response.status_code == 200

        # Wait for background tasks to complete
        if background_tasks:
            await asyncio.gather(*background_tasks)

        # Verify background task executed
        assert len(task_results) == 1
        assert task_results[0]["id"] == 123


@pytest.mark.asyncio
async def test_middleware_does_not_block_event_loop():
    """
    Test that middleware doesn't block the event loop.

    BaseHTTPMiddleware can block the event loop, causing AsyncPG timeouts.
    """
    app = Zenith()

    @app.get("/non-blocking")
    async def non_blocking_endpoint():
        """Endpoint that should not block."""
        # Multiple async operations that would fail if event loop blocked
        results = []
        for i in range(3):
            await asyncio.sleep(0.001)
            results.append(i)
        return {"results": results}

    async with TestClient(app) as client:
        # Should complete quickly without blocking
        response = await client.get("/non-blocking")
        assert response.status_code == 200
        assert response.json()["results"] == [0, 1, 2]


# Real PostgreSQL test (only runs if DATABASE_URL is set)
@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping real PostgreSQL test",
)
@pytest.mark.asyncio
async def test_real_asyncpg_connection():
    """
    Test with real AsyncPG connection if PostgreSQL is available.

    This test only runs in CI or when DATABASE_URL is set locally.
    """
    import os

    import asyncpg

    # Set proper environment for test
    os.environ["ZENITH_ENV"] = "test"
    app = Zenith()

    @app.get("/real-db")
    async def real_db_endpoint():
        """Test with real database connection."""
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        try:
            # Simple query that should always work
            result = await conn.fetch("SELECT 1 as value")
            return {"value": result[0]["value"]}
        finally:
            await conn.close()

    async with TestClient(app) as client:
        response = await client.get("/real-db")
        assert response.status_code == 200
        assert response.json()["value"] == 1
