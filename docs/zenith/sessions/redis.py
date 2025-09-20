"""
Redis-backed session storage.

Provides persistent session storage using Redis with automatic expiration.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import redis.asyncio as redis

from zenith.core.json_encoder import _json_dumps, _json_loads
from zenith.sessions.manager import Session
from zenith.sessions.store import SessionStore

logger = logging.getLogger("zenith.sessions.redis")


class RedisSessionStore(SessionStore):
    """
    Redis session storage backend.

    Features:
    - Persistent session storage
    - Automatic expiration using Redis TTL
    - JSON serialization
    - Connection pooling
    - High performance and scalability
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/1",
        key_prefix: str = "zenith:session:",
        serializer: str = "json",
    ):
        """
        Initialize Redis session store.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for session keys in Redis
            serializer: Serialization format ("json" only for now)
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.serializer = serializer

        if serializer != "json":
            raise ValueError("Only 'json' serializer is currently supported")

        # Create Redis connection
        self.redis = redis.from_url(redis_url)

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for session ID."""
        return f"{self.key_prefix}{session_id}"

    async def load(self, session_id: str) -> Session | None:
        """Load session from Redis."""
        from zenith.sessions.manager import Session

        key = self._get_key(session_id)

        try:
            data = await self.redis.get(key)
            if not data:
                return None

            # Deserialize session data
            session_dict = _json_loads(data)
            session = Session.from_dict(session_dict)

            # Check if expired (additional safety check)
            if session.is_expired():
                await self.delete(session_id)
                return None

            return session

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    async def save(self, session: Session) -> None:
        """Save session to Redis."""
        key = self._get_key(session.session_id)

        try:
            # Serialize session data
            session_dict = session.to_dict()
            data = _json_dumps(session_dict)

            # Calculate TTL in seconds
            ttl = None
            if session.expires_at:
                # Use timezone-aware datetime for consistency
                now = (
                    datetime.now(UTC)
                    if session.expires_at.tzinfo
                    else datetime.utcnow()
                )
                ttl_seconds = (session.expires_at - now).total_seconds()
                if ttl_seconds > 0:
                    ttl = int(ttl_seconds)
                else:
                    # Session already expired
                    await self.delete(session.session_id)
                    return

            # Save to Redis with TTL
            if ttl:
                await self.redis.setex(key, ttl, data)
            else:
                await self.redis.set(key, data)

            logger.debug(f"Saved session {session.session_id} with TTL {ttl}s")

        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}")
            raise

    async def delete(self, session_id: str) -> None:
        """Delete session from Redis."""
        key = self._get_key(session_id)

        try:
            deleted = await self.redis.delete(key)
            if deleted:
                logger.debug(f"Deleted session {session_id}")
            else:
                logger.debug(f"Session {session_id} not found for deletion")

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")

    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        For Redis, expired keys are automatically cleaned up by TTL,
        so this method just counts and reports cleanup.
        """
        # Redis handles TTL cleanup automatically
        # We could scan for expired keys, but it's not necessary
        logger.info("Redis TTL handles automatic cleanup of expired sessions")
        return 0

    async def get_session_count(self) -> int:
        """Get total number of active sessions."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Error counting sessions: {e}")
            return 0

    async def get_session_ids(self, limit: int = 100) -> list[str]:
        """Get list of active session IDs."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)

            # Extract session IDs from keys
            session_ids = []
            for key in keys[:limit]:
                key_str = key.decode() if isinstance(key, bytes) else key
                session_id = key_str.replace(self.key_prefix, "")
                session_ids.append(session_id)

            return session_ids

        except Exception as e:
            logger.error(f"Error getting session IDs: {e}")
            return []

    async def health_check(self) -> dict:
        """Get Redis session store health information."""
        try:
            # Test Redis connection
            await self.redis.ping()

            # Get session count
            session_count = await self.get_session_count()

            return {
                "status": "healthy",
                "backend": "redis",
                "url": self.redis_url,
                "session_count": session_count,
                "key_prefix": self.key_prefix,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "redis",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()
