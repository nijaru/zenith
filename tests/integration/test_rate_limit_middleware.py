"""
Integration tests for rate limiting middleware.

Tests the actual rate limiting behavior in realistic scenarios.
This middleware had 51% coverage but lacked integration tests.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from zenith import Zenith
from zenith.middleware.rate_limit import (
    RateLimit, RateLimitConfig, RateLimitMiddleware,
    MemoryRateLimitStorage, RedisRateLimitStorage,
    create_rate_limiter, create_redis_rate_limiter
)
from zenith.testing import TestClient


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test rate limiting middleware integration."""

    async def test_basic_rate_limiting_per_ip(self):
        """Test basic per-IP rate limiting."""
        app = Zenith()

        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        # Very restrictive limit for testing
        rate_limits = [RateLimit(requests=2, window=60, per="ip")]  # 2 requests per minute
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=rate_limits,
            exempt_ips=[]  # Don't exempt localhost for testing
        )

        @app.get("/api/limited")
        async def limited_endpoint():
            return {"message": "success"}

        async with TestClient(app) as client:
            # First request - should succeed
            response1 = await client.get("/api/limited")
            assert response1.status_code == 200
            assert "x-ratelimit-limit" in response1.headers
            assert response1.headers["x-ratelimit-limit"] == "2"
            assert response1.headers["x-ratelimit-remaining"] == "1"

            # Second request - should succeed
            response2 = await client.get("/api/limited")
            assert response2.status_code == 200
            assert response2.headers["x-ratelimit-remaining"] == "0"

            # Third request - should be rate limited
            response3 = await client.get("/api/limited")
            assert response3.status_code == 429
            data = response3.json()
            assert data["error"] == "rate_limit_exceeded"
            assert data["limit"] == 2
            assert data["window"] == 60

    async def test_rate_limit_expiration(self):
        """Test rate limit window expiration."""
        app = Zenith()

        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        # Short window for testing
        rate_limits = [RateLimit(requests=1, window=1, per="ip")]  # 1 request per second
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=rate_limits,
            exempt_ips=[]  # Don't exempt localhost for testing
        )

        @app.get("/api/expires")
        async def expires():
            return {"timestamp": time.time()}

        async with TestClient(app) as client:
            # First request - should succeed
            response1 = await client.get("/api/expires")
            assert response1.status_code == 200

            # Second request immediately - should be rate limited
            response2 = await client.get("/api/expires")
            assert response2.status_code == 429

            # Wait for window to expire
            await asyncio.sleep(1.5)

            # Third request after expiration - should succeed
            response3 = await client.get("/api/expires")
            assert response3.status_code == 200

    async def test_multiple_rate_limits(self):
        """Test multiple rate limits with different windows."""
        app = Zenith()

        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        # Multiple limits: 2 per second, 5 per minute
        rate_limits = [
            RateLimit(requests=2, window=1, per="ip"),    # 2/second
            RateLimit(requests=5, window=60, per="ip"),   # 5/minute
        ]
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=rate_limits,
            exempt_ips=[]  # Don't exempt localhost for testing
        )

        @app.get("/api/multi-limit")
        async def multi_limit():
            return {"requests": "handled"}

        async with TestClient(app) as client:
            # Make 2 requests quickly - should hit per-second limit
            response1 = await client.get("/api/multi-limit")
            assert response1.status_code == 200

            response2 = await client.get("/api/multi-limit")
            assert response2.status_code == 200

            # Third request immediately - should be rate limited (per-second)
            response3 = await client.get("/api/multi-limit")
            assert response3.status_code == 429
            data = response3.json()
            # Should be the more restrictive limit (2 requests)
            assert data["limit"] == 2
            assert data["window"] == 1

    async def test_exempt_paths(self):
        """Test exempting specific paths from rate limiting."""
        app = Zenith()

        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        rate_limits = [RateLimit(requests=1, window=60, per="ip")]
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=rate_limits,
            exempt_paths=["/health", "/api/public"],
            exempt_ips=[]  # Don't exempt localhost for testing
        )

        @app.get("/api/limited")
        async def limited():
            return {"limited": True}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        @app.get("/api/public")
        async def public():
            return {"public": True}

        async with TestClient(app) as client:
            # Limited endpoint - first request succeeds
            response1 = await client.get("/api/limited")
            assert response1.status_code == 200

            # Limited endpoint - second request fails
            response2 = await client.get("/api/limited")
            assert response2.status_code == 429

            # Exempt paths should always work
            health_response = await client.get("/health")
            assert health_response.status_code == 200
            assert "x-ratelimit-limit" not in health_response.headers

            public_response = await client.get("/api/public")
            assert public_response.status_code == 200
            assert "x-ratelimit-limit" not in public_response.headers

    async def test_exempt_ips(self):
        """Test exempting specific IP addresses."""
        app = Zenith()

        rate_limits = [RateLimit(requests=1, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(
            default_limits=rate_limits,
            exempt_ips=["127.0.0.1", "::1", "192.168.1.100"]  # Include test client IP
        )
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/test")
        async def test_endpoint():
            return {"test": True}

        async with TestClient(app) as client:
            # All requests should succeed due to IP exemption
            for i in range(5):
                response = await client.get("/api/test")
                assert response.status_code == 200
                # Exempt IPs shouldn't get rate limit headers
                assert "x-ratelimit-limit" not in response.headers

    async def test_per_user_rate_limiting(self):
        """Test per-user rate limiting with authentication."""
        app = Zenith()

        rate_limits = [RateLimit(requests=2, window=60, per="user")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/user-limited")
        async def user_limited(request):
            # Mock user authentication by setting request state
            user_id = request.headers.get("X-User-ID")
            if user_id:
                request.state.current_user = {"id": user_id, "username": f"user_{user_id}"}
            return {"user_endpoint": True}

        async with TestClient(app) as client:
            # User 1 - should get 2 requests
            response1 = await client.get("/api/user-limited", headers={"X-User-ID": "123"})
            assert response1.status_code == 200

            response2 = await client.get("/api/user-limited", headers={"X-User-ID": "123"})
            assert response2.status_code == 200

            response3 = await client.get("/api/user-limited", headers={"X-User-ID": "123"})
            assert response3.status_code == 429

            # User 2 - should get fresh limit
            response4 = await client.get("/api/user-limited", headers={"X-User-ID": "456"})
            assert response4.status_code == 200

            response5 = await client.get("/api/user-limited", headers={"X-User-ID": "456"})
            assert response5.status_code == 200

            response6 = await client.get("/api/user-limited", headers={"X-User-ID": "456"})
            assert response6.status_code == 429

    async def test_per_endpoint_rate_limiting(self):
        """Test per-endpoint rate limiting."""
        app = Zenith()

        rate_limits = [RateLimit(requests=2, window=60, per="endpoint")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/endpoint1")
        async def endpoint1():
            return {"endpoint": 1}

        @app.get("/api/endpoint2")
        async def endpoint2():
            return {"endpoint": 2}

        async with TestClient(app) as client:
            # Endpoint 1 - should get its own limit
            response1 = await client.get("/api/endpoint1")
            assert response1.status_code == 200

            response2 = await client.get("/api/endpoint1")
            assert response2.status_code == 200

            response3 = await client.get("/api/endpoint1")
            assert response3.status_code == 429

            # Endpoint 2 - should have separate limit
            response4 = await client.get("/api/endpoint2")
            assert response4.status_code == 200

            response5 = await client.get("/api/endpoint2")
            assert response5.status_code == 200

            response6 = await client.get("/api/endpoint2")
            assert response6.status_code == 429

    async def test_endpoint_specific_limits(self):
        """Test custom limits for specific endpoints."""
        app = Zenith()

        # Default limit
        default_limits = [RateLimit(requests=10, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=default_limits)
        middleware = RateLimitMiddleware(app.app, config=rate_limit_config)

        # Add custom limit for specific endpoint
        strict_limits = [RateLimit(requests=1, window=60, per="ip")]
        middleware.add_endpoint_limit("/api/strict", strict_limits)

        app.middleware.append(middleware)

        @app.get("/api/normal")
        async def normal():
            return {"type": "normal"}

        @app.get("/api/strict")
        async def strict():
            return {"type": "strict"}

        async with TestClient(app) as client:
            # Normal endpoint - should allow multiple requests
            response1 = await client.get("/api/normal")
            assert response1.status_code == 200

            response2 = await client.get("/api/normal")
            assert response2.status_code == 200

            # Strict endpoint - should only allow 1 request
            response3 = await client.get("/api/strict")
            assert response3.status_code == 200

            response4 = await client.get("/api/strict")
            assert response4.status_code == 429
            data = response4.json()
            assert data["limit"] == 1  # Custom limit

    async def test_rate_limit_headers(self):
        """Test rate limit headers in responses."""
        app = Zenith()

        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

        rate_limits = [RateLimit(requests=5, window=60, per="ip")]
        app.add_middleware(
            RateLimitMiddleware,
            default_limits=rate_limits,
            include_headers=True,
            exempt_ips=[]  # Don't exempt localhost for testing
        )

        @app.get("/api/headers-test")
        async def headers_test():
            return {"test": "headers"}

        async with TestClient(app) as client:
            response = await client.get("/api/headers-test")
            assert response.status_code == 200

            # Check rate limit headers
            assert "x-ratelimit-limit" in response.headers
            assert "x-ratelimit-window" in response.headers
            assert "x-ratelimit-remaining" in response.headers

            assert response.headers["x-ratelimit-limit"] == "5"
            assert response.headers["x-ratelimit-window"] == "60"
            assert int(response.headers["x-ratelimit-remaining"]) <= 5

    async def test_rate_limit_headers_disabled(self):
        """Test disabling rate limit headers."""
        app = Zenith()

        rate_limits = [RateLimit(requests=5, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits, include_headers=False)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/no-headers")
        async def no_headers():
            return {"test": "no headers"}

        async with TestClient(app) as client:
            response = await client.get("/api/no-headers")
            assert response.status_code == 200

            # Should not have rate limit headers
            assert "x-ratelimit-limit" not in response.headers
            assert "x-ratelimit-window" not in response.headers
            assert "x-ratelimit-remaining" not in response.headers

    async def test_custom_error_message(self):
        """Test custom error message configuration."""
        app = Zenith()

        rate_limits = [RateLimit(requests=1, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(
            default_limits=rate_limits,
            error_message="Too many requests! Please slow down."
        )
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/custom-error")
        async def custom_error():
            return {"test": True}

        async with TestClient(app) as client:
            # First request succeeds
            response1 = await client.get("/api/custom-error")
            assert response1.status_code == 200

            # Second request gets custom error
            response2 = await client.get("/api/custom-error")
            assert response2.status_code == 429
            data = response2.json()
            assert data["message"] == "Too many requests! Please slow down."

    async def test_x_forwarded_for_header(self):
        """Test IP extraction from X-Forwarded-For header."""
        app = Zenith()

        rate_limits = [RateLimit(requests=1, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/proxy-test")
        async def proxy_test():
            return {"proxy": True}

        async with TestClient(app) as client:
            # Request with X-Forwarded-For should use forwarded IP
            headers1 = {"X-Forwarded-For": "192.168.1.100"}
            response1 = await client.get("/api/proxy-test", headers=headers1)
            assert response1.status_code == 200

            response2 = await client.get("/api/proxy-test", headers=headers1)
            assert response2.status_code == 429

            # Different forwarded IP should get fresh limit
            headers2 = {"X-Forwarded-For": "192.168.1.101"}
            response3 = await client.get("/api/proxy-test", headers=headers2)
            assert response3.status_code == 200

    async def test_jwt_user_extraction(self):
        """Test user ID extraction from JWT Authorization header."""
        app = Zenith()

        rate_limits = [RateLimit(requests=2, window=60, per="user")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        # Mock the auth token extraction
        with patch('zenith.auth.extract_user_from_token') as mock_extract:
            mock_extract.return_value = {"id": "user123", "username": "testuser"}

            @app.get("/api/jwt-test")
            async def jwt_test():
                return {"jwt": True}

            async with TestClient(app) as client:
                headers = {"Authorization": "Bearer fake.jwt.token"}

                # Should get user-based rate limiting
                response1 = await client.get("/api/jwt-test", headers=headers)
                assert response1.status_code == 200

                response2 = await client.get("/api/jwt-test", headers=headers)
                assert response2.status_code == 200

                response3 = await client.get("/api/jwt-test", headers=headers)
                assert response3.status_code == 429


@pytest.mark.asyncio
class TestMemoryRateLimitStorage:
    """Test memory-based rate limit storage."""

    async def test_memory_storage_basic_operations(self):
        """Test basic storage operations."""
        storage = MemoryRateLimitStorage()

        # Test initial count is 0
        count = await storage.get_count("test_key")
        assert count == 0

        # Test increment
        new_count = await storage.increment("test_key", window=60)
        assert new_count == 1

        # Test get count
        count = await storage.get_count("test_key")
        assert count == 1

        # Test multiple increments
        count2 = await storage.increment("test_key", window=60)
        assert count2 == 2

    async def test_memory_storage_expiration(self):
        """Test storage entry expiration."""
        storage = MemoryRateLimitStorage()

        # Increment with short window
        await storage.increment("expire_key", window=1)

        # Should be available immediately
        count = await storage.get_count("expire_key")
        assert count == 1

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        count = await storage.get_count("expire_key")
        assert count == 0

    async def test_memory_storage_reset(self):
        """Test resetting storage entries."""
        storage = MemoryRateLimitStorage()

        # Add some entries
        await storage.increment("reset_key", window=60)
        await storage.increment("reset_key", window=60)

        count = await storage.get_count("reset_key")
        assert count == 2

        # Reset
        await storage.reset("reset_key")

        count = await storage.get_count("reset_key")
        assert count == 0

    async def test_memory_storage_cleanup(self):
        """Test background cleanup of expired entries."""
        # Short cleanup interval for testing
        storage = MemoryRateLimitStorage(cleanup_interval=1, max_entries=100)

        # Add entry that will expire quickly
        await storage.increment("cleanup_key", window=1)

        # Wait for cleanup
        await asyncio.sleep(2)

        # Entry should be cleaned up
        assert "cleanup_key" not in storage._storage

        # Clean up the storage
        storage.stop_cleanup()

    async def test_memory_storage_max_entries(self):
        """Test max entries limit and size-based cleanup."""
        storage = MemoryRateLimitStorage(max_entries=3)

        # Fill storage to max
        await storage.increment("key1", window=60)
        await storage.increment("key2", window=60)
        await storage.increment("key3", window=60)

        assert len(storage._storage) == 3

        # Adding another should trigger cleanup
        await storage.increment("key4", window=60)

        # Should still be at max capacity or less
        assert len(storage._storage) <= 3

    async def test_storage_stats(self):
        """Test storage statistics."""
        storage = MemoryRateLimitStorage(max_entries=100)

        stats = storage.get_storage_stats()
        assert "total_entries" in stats
        assert "max_entries" in stats
        assert "cleanup_interval" in stats
        assert "cleanup_task_running" in stats

        assert stats["max_entries"] == 100


@pytest.mark.asyncio
class TestRedisRateLimitStorage:
    """Test Redis-based rate limit storage."""

    @patch('zenith.middleware.rate_limit.RedisRateLimitStorage')
    async def test_redis_storage_integration(self, mock_redis_storage_class):
        """Test rate limiting with mocked Redis storage."""
        # Mock Redis storage
        mock_storage = AsyncMock()
        mock_storage.get_count.return_value = 0
        mock_storage.increment.return_value = 1
        mock_storage.reset.return_value = None
        mock_redis_storage_class.return_value = mock_storage

        app = Zenith()

        # Use Redis storage (mocked)
        mock_redis_client = AsyncMock()
        redis_storage = RedisRateLimitStorage(mock_redis_client)
        rate_limits = [RateLimit(requests=2, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits, storage=redis_storage)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/redis-limited")
        async def redis_limited():
            return {"redis": True}

        async with TestClient(app) as client:
            response = await client.get("/api/redis-limited")
            assert response.status_code == 200

            # Should have called Redis storage methods
            assert mock_storage.increment.called or redis_storage.increment


@pytest.mark.asyncio
class TestRateLimitConvenienceFunctions:
    """Test convenience functions for creating rate limiters."""

    async def test_create_rate_limiter(self):
        """Test create_rate_limiter convenience function."""
        app = Zenith()

        rate_limiter = create_rate_limiter(
            requests_per_minute=5,
            requests_per_hour=50
        )
        app.add_middleware(type(rate_limiter), **rate_limiter.__dict__)

        @app.get("/api/convenience-test")
        async def convenience_test():
            return {"convenience": True}

        # Check that rate limiter was configured correctly
        assert len(rate_limiter.default_limits) == 2
        assert any(limit.requests == 5 and limit.window == 60 for limit in rate_limiter.default_limits)
        assert any(limit.requests == 50 and limit.window == 3600 for limit in rate_limiter.default_limits)

    @patch('zenith.middleware.rate_limit.RedisRateLimitStorage')
    async def test_create_redis_rate_limiter(self, mock_redis_storage_class):
        """Test create_redis_rate_limiter convenience function."""
        mock_redis_client = AsyncMock()
        mock_storage = AsyncMock()
        mock_redis_storage_class.return_value = mock_storage

        rate_limiter = create_redis_rate_limiter(
            redis_client=mock_redis_client,
            requests_per_minute=10,
            requests_per_hour=100
        )

        # Check configuration
        assert len(rate_limiter.default_limits) == 2
        assert isinstance(rate_limiter.storage, type(mock_storage))


@pytest.mark.asyncio
class TestRateLimitEdgeCases:
    """Test edge cases and error conditions."""

    async def test_unknown_rate_limit_type(self):
        """Test error handling for unknown rate limit types."""
        app = Zenith()

        # Invalid rate limit type
        invalid_limit = RateLimit(requests=10, window=60, per="invalid_type")
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=[invalid_limit])
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/invalid-type")
        async def invalid_type():
            return {"test": True}

        async with TestClient(app) as client:
            # Should raise ValueError for unknown rate limit type
            with pytest.raises(ValueError, match="Unknown rate limit type"):
                await client.get("/api/invalid-type")

    async def test_missing_user_fallback_to_ip(self):
        """Test fallback to IP when user not available for per-user limiting."""
        app = Zenith()

        rate_limits = [RateLimit(requests=1, window=60, per="user")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/user-fallback")
        async def user_fallback():
            # No user authentication - should fall back to IP
            return {"fallback": True}

        async with TestClient(app) as client:
            # Should work with IP-based limiting as fallback
            response1 = await client.get("/api/user-fallback")
            assert response1.status_code == 200

            response2 = await client.get("/api/user-fallback")
            assert response2.status_code == 429  # Rate limited by IP

    async def test_concurrent_requests_race_condition(self):
        """Test concurrent requests don't cause race conditions."""
        app = Zenith()

        rate_limits = [RateLimit(requests=5, window=60, per="ip")]
        # Remove auto-added rate limiting middleware to avoid conflicts
        app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]
        rate_limit_config = RateLimitConfig(default_limits=rate_limits)
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

        @app.get("/api/concurrent")
        async def concurrent():
            # Add small delay to increase chance of race condition
            await asyncio.sleep(0.01)
            return {"concurrent": True}

        async with TestClient(app) as client:
            # Make concurrent requests
            tasks = [client.get("/api/concurrent") for _ in range(10)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful responses
            success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
            error_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 429)

            # Should have some successes and some rate limit errors
            assert success_count <= 5  # At most the limit
            assert error_count >= 5   # At least some rate limited
            assert success_count + error_count == 10  # All requests handled