"""
Integration tests for Redis session storage.

Tests the Redis session backend in realistic scenarios.
This component had 20% coverage and NO integration tests.
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from zenith import Zenith
from zenith.sessions import SessionMiddleware
from zenith.sessions.manager import Session, SessionManager
from zenith.sessions.redis import RedisSessionStore
from zenith.testing import TestClient


@pytest.mark.asyncio
class TestRedisSessionStore:
    """Test Redis session store backend."""

    @patch("redis.asyncio.from_url")
    async def test_redis_session_basic_operations(self, mock_redis_from_url):
        """Test basic Redis session operations - save, load, delete."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis_from_url.return_value = mock_redis

        # Create Redis session store
        store = RedisSessionStore("redis://localhost:6379/1")

        # Create a test session
        session = Session(
            session_id="test123",
            data={"user_id": 456, "username": "testuser"},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        # Test save
        await store.save(session)

        # Should have called Redis setex with TTL
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "zenith:session:test123"  # key
        assert call_args[0][1] > 0  # TTL > 0

        # Test delete
        await store.delete("test123")
        mock_redis.delete.assert_called_with("zenith:session:test123")

        # Test load (not found)
        mock_redis.get.return_value = None
        result = await store.load("nonexistent")
        assert result is None

        await store.close()

    @patch("redis.asyncio.from_url")
    async def test_redis_session_health_check(self, mock_redis_from_url):
        """Test Redis session store health check."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.keys.return_value = [
            b"zenith:session:sess1",
            b"zenith:session:sess2",
        ]
        mock_redis_from_url.return_value = mock_redis

        store = RedisSessionStore("redis://localhost:6379/1")

        health = await store.health_check()

        assert health["status"] == "healthy"
        assert health["backend"] == "redis"
        assert health["url"] == "redis://localhost:6379/1"
        assert health["session_count"] == 2
        assert health["key_prefix"] == "zenith:session:"

        await store.close()

    @patch("redis.asyncio.from_url")
    async def test_redis_session_middleware_integration(self, mock_redis_from_url):
        """Test Redis session store integrated with session middleware."""
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # No existing session
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis_from_url.return_value = mock_redis

        app = Zenith()

        # Create Redis session store
        redis_store = RedisSessionStore("redis://localhost:6379/1")
        session_manager = SessionManager(store=redis_store, max_age=timedelta(hours=1))
        app.add_middleware(SessionMiddleware, session_manager=session_manager)

        @app.get("/redis-session-test")
        async def redis_session_test(request):
            request.session["redis_data"] = "stored_in_redis"
            request.session["timestamp"] = time.time()
            return {"status": "redis_session_set"}

        async with TestClient(app) as client:
            response = await client.get("/redis-session-test")
            assert response.status_code == 200

            # Should have saved to Redis
            mock_redis.setex.assert_called()

        # Clean up
        await redis_store.close()
