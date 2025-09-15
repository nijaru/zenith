"""
Integration tests for cache middleware.

Tests the actual response caching in realistic scenarios.
This middleware had 19% coverage and NO integration tests.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from zenith import Zenith
from zenith.middleware.cache import (
    CacheConfig,
    MemoryCache,
    ResponseCacheMiddleware,
)
from zenith.testing import TestClient


@pytest.mark.asyncio
class TestCacheMiddleware:
    """Test cache middleware integration."""

    async def test_basic_cache_hit_and_miss(self):
        """Test basic caching behavior - cache miss then cache hit."""
        app = Zenith()

        cache_config = CacheConfig(default_ttl=300)
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/data")
        async def get_data():
            return {"data": "cached_response", "timestamp": time.time()}

        async with TestClient(app) as client:
            # First request - should be cache MISS
            response1 = await client.get("/api/data")
            assert response1.status_code == 200
            assert response1.headers.get("x-cache") == "MISS"
            data1 = response1.json()

            # Second request - should be cache HIT
            response2 = await client.get("/api/data")
            assert response2.status_code == 200
            assert response2.headers.get("x-cache") == "HIT"
            data2 = response2.json()

            # Data should be identical (cached)
            assert data1 == data2

    async def test_cache_expiration(self):
        """Test cache expiration behavior."""
        app = Zenith()

        # Very short TTL for testing
        cache_config = CacheConfig(default_ttl=1)  # 1 second
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/expires")
        async def expires():
            return {"timestamp": time.time()}

        async with TestClient(app) as client:
            # First request - cache MISS
            response1 = await client.get("/api/expires")
            assert response1.headers.get("x-cache") == "MISS"
            data1 = response1.json()

            # Second request immediately - cache HIT
            response2 = await client.get("/api/expires")
            assert response2.headers.get("x-cache") == "HIT"
            data2 = response2.json()
            assert data1 == data2

            # Wait for cache to expire
            import asyncio

            await asyncio.sleep(1.5)

            # Third request after expiration - cache MISS
            response3 = await client.get("/api/expires")
            assert response3.headers.get("x-cache") == "MISS"
            data3 = response3.json()
            # Should be different timestamp (not cached)
            assert data3["timestamp"] != data1["timestamp"]

    async def test_method_filtering(self):
        """Test that only configured HTTP methods are cached."""
        app = Zenith()

        cache_config = CacheConfig(
            cache_methods=["GET", "HEAD"],  # Don't cache POST
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/item")
        async def get_item():
            return {"method": "GET", "timestamp": time.time()}

        @app.post("/api/item")
        async def create_item():
            return {"method": "POST", "timestamp": time.time()}

        async with TestClient(app) as client:
            # GET should be cached
            response1 = await client.get("/api/item")
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get("/api/item")
            assert response2.headers.get("x-cache") == "HIT"

            # POST should NOT be cached
            response3 = await client.post("/api/item")
            assert (
                "x-cache" not in response3.headers
                or response3.headers.get("x-cache") != "HIT"
            )

            response4 = await client.post("/api/item")
            assert (
                "x-cache" not in response4.headers
                or response4.headers.get("x-cache") != "HIT"
            )

    async def test_status_code_filtering(self):
        """Test that only configured status codes are cached."""
        app = Zenith()

        cache_config = CacheConfig(
            cache_status_codes=[200],  # Only cache 200 OK
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/success")
        async def success():
            return {"status": "success"}

        @app.get("/api/error")
        async def error():
            from starlette.responses import JSONResponse

            return JSONResponse({"error": "not found"}, status_code=404)

        async with TestClient(app) as client:
            # 200 OK should be cached
            response1 = await client.get("/api/success")
            assert response1.status_code == 200
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get("/api/success")
            assert response2.headers.get("x-cache") == "HIT"

            # 404 should NOT be cached
            response3 = await client.get("/api/error")
            assert response3.status_code == 404
            # Should still have cache miss header but not be cached
            response4 = await client.get("/api/error")
            assert response4.status_code == 404
            # No cache hit for error responses

    async def test_path_filtering_cache_paths(self):
        """Test caching only specific paths."""
        app = Zenith()

        cache_config = CacheConfig(
            cache_paths=["/api/cached"],  # Only cache this path
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/cached")
        async def cached_endpoint():
            return {"cached": True, "timestamp": time.time()}

        @app.get("/api/uncached")
        async def uncached_endpoint():
            return {"cached": False, "timestamp": time.time()}

        async with TestClient(app) as client:
            # Cached path should be cached
            response1 = await client.get("/api/cached")
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get("/api/cached")
            assert response2.headers.get("x-cache") == "HIT"

            # Uncached path should NOT be cached
            response3 = await client.get("/api/uncached")
            assert "x-cache" not in response3.headers

            response4 = await client.get("/api/uncached")
            assert "x-cache" not in response4.headers

    async def test_path_filtering_ignore_paths(self):
        """Test ignoring specific paths from caching."""
        app = Zenith()

        cache_config = CacheConfig(
            ignore_paths=["/api/dynamic"],  # Don't cache this path
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/static")
        async def static_endpoint():
            return {"type": "static", "timestamp": time.time()}

        @app.get("/api/dynamic")
        async def dynamic_endpoint():
            return {"type": "dynamic", "timestamp": time.time()}

        async with TestClient(app) as client:
            # Static path should be cached
            response1 = await client.get("/api/static")
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get("/api/static")
            assert response2.headers.get("x-cache") == "HIT"

            # Dynamic path should NOT be cached
            response3 = await client.get("/api/dynamic")
            assert "x-cache" not in response3.headers

            response4 = await client.get("/api/dynamic")
            assert "x-cache" not in response4.headers

    async def test_query_parameter_handling(self):
        """Test cache key generation with query parameters."""
        app = Zenith()

        cache_config = CacheConfig(
            ignore_query_params=["timestamp"],  # Ignore timestamp param
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/search")
        async def search(request):
            params = dict(request.query_params)
            return {"query": params}

        async with TestClient(app) as client:
            # Same query (ignoring timestamp) should be cached
            response1 = await client.get("/api/search?q=test&timestamp=123")
            assert response1.headers.get("x-cache") == "MISS"

            # Different timestamp, same other params - should be cache HIT
            response2 = await client.get("/api/search?q=test&timestamp=456")
            assert response2.headers.get("x-cache") == "HIT"

            # Different query param - should be cache MISS
            response3 = await client.get("/api/search?q=different&timestamp=789")
            assert response3.headers.get("x-cache") == "MISS"

    async def test_header_variation(self):
        """Test cache key variation based on headers."""
        app = Zenith()

        cache_config = CacheConfig(
            vary_headers=["Authorization"],  # Vary cache by auth header
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/user-data")
        async def user_data(request):
            auth = request.headers.get("Authorization", "none")
            return {"auth": auth, "data": "user_specific"}

        async with TestClient(app) as client:
            # First user
            response1 = await client.get(
                "/api/user-data", headers={"Authorization": "Bearer user1"}
            )
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get(
                "/api/user-data", headers={"Authorization": "Bearer user1"}
            )
            assert response2.headers.get("x-cache") == "HIT"

            # Different user - should be cache MISS (different cache key)
            response3 = await client.get(
                "/api/user-data", headers={"Authorization": "Bearer user2"}
            )
            assert response3.headers.get("x-cache") == "MISS"

    async def test_memory_cache_lru_eviction(self):
        """Test LRU eviction in memory cache."""
        app = Zenith()

        # Small cache size for testing eviction
        cache_config = CacheConfig(
            max_cache_items=2,  # Only cache 2 items
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/item/{item_id}")
        async def get_item(item_id: str):
            return {"item_id": item_id, "timestamp": time.time()}

        async with TestClient(app) as client:
            # Fill cache with 2 items
            response1 = await client.get("/api/item/1")
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get("/api/item/2")
            assert response2.headers.get("x-cache") == "MISS"

            # Verify both are cached
            response1_hit = await client.get("/api/item/1")
            assert response1_hit.headers.get("x-cache") == "HIT"

            response2_hit = await client.get("/api/item/2")
            assert response2_hit.headers.get("x-cache") == "HIT"

            # Add third item - should evict oldest (item 1)
            response3 = await client.get("/api/item/3")
            assert response3.headers.get("x-cache") == "MISS"

            # Item 2 and 3 should still be cached
            response2_still = await client.get("/api/item/2")
            assert response2_still.headers.get("x-cache") == "HIT"

            response3_still = await client.get("/api/item/3")
            assert response3_still.headers.get("x-cache") == "HIT"

            # Item 1 should be evicted (cache miss) - test this last to avoid re-caching
            response1_evicted = await client.get("/api/item/1")
            assert response1_evicted.headers.get("x-cache") == "MISS"


@pytest.mark.asyncio
class TestMemoryCache:
    """Test memory cache backend directly."""

    async def test_memory_cache_basic_operations(self):
        """Test basic memory cache operations."""
        cache = MemoryCache(max_size=3)

        # Test set and get
        cache.set(
            "key1",
            {
                "content": b"data1",
                "media_type": "application/json",
                "headers": [],
                "status_code": 200,
            },
            ttl=300,
        )

        item = cache.get("key1")
        assert item is not None
        assert item["content"] == b"data1"
        assert item["status_code"] == 200

        # Test non-existent key
        assert cache.get("nonexistent") is None

    async def test_memory_cache_expiration(self):
        """Test memory cache TTL expiration."""
        cache = MemoryCache()

        # Set with very short TTL
        cache.set(
            "expire_key",
            {
                "content": b"expires",
                "media_type": "application/json",
                "headers": [],
                "status_code": 200,
            },
            ttl=1,
        )

        # Should be available immediately
        assert cache.get("expire_key") is not None

        # Wait for expiration
        import asyncio

        await asyncio.sleep(1.5)

        # Should be expired
        assert cache.get("expire_key") is None

    async def test_memory_cache_lru_behavior(self):
        """Test LRU eviction behavior."""
        cache = MemoryCache(max_size=2)

        data_template = {
            "content": b"data",
            "media_type": "application/json",
            "headers": [],
            "status_code": 200,
        }

        # Fill cache
        cache.set("key1", {**data_template, "content": b"data1"}, ttl=300)
        cache.set("key2", {**data_template, "content": b"data2"}, ttl=300)

        # Both should be available
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None

        # Add third item - should evict oldest
        cache.set("key3", {**data_template, "content": b"data3"}, ttl=300)

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    async def test_memory_cache_update_existing(self):
        """Test updating existing cache items."""
        cache = MemoryCache()

        data1 = {
            "content": b"original",
            "media_type": "application/json",
            "headers": [],
            "status_code": 200,
        }

        data2 = {
            "content": b"updated",
            "media_type": "application/json",
            "headers": [],
            "status_code": 200,
        }

        # Set initial value
        cache.set("update_key", data1, ttl=300)
        assert cache.get("update_key")["content"] == b"original"

        # Update value
        cache.set("update_key", data2, ttl=300)
        assert cache.get("update_key")["content"] == b"updated"


@pytest.mark.asyncio
class TestRedisCacheIntegration:
    """Test Redis cache backend integration."""

    @patch("zenith.middleware.cache.RedisCache")
    async def test_redis_cache_integration(self, mock_redis_cache_class):
        """Test cache middleware with mocked Redis backend."""
        # Mock Redis cache instance (RedisCache methods are synchronous)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # No cached data initially
        mock_cache.set.return_value = None
        mock_redis_cache_class.return_value = mock_cache

        app = Zenith()

        # Use Redis cache
        cache_config = CacheConfig(
            use_redis=True,
            redis_client=MagicMock(),  # Mock Redis client
            default_ttl=300,
        )
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/redis-test")
        async def redis_test():
            return {"backend": "redis", "timestamp": time.time()}

        async with TestClient(app) as client:
            response = await client.get("/api/redis-test")
            assert response.status_code == 200

            # Should have attempted to get from cache
            mock_cache.get.assert_called()


@pytest.mark.asyncio
class TestCacheConfiguration:
    """Test various cache configuration scenarios."""

    async def test_default_ignore_paths(self):
        """Test that default health/metrics paths are ignored."""
        from zenith.middleware.cache import create_cache_middleware

        app = Zenith()
        cache_middleware = create_cache_middleware()
        app.add_middleware(ResponseCacheMiddleware, config=cache_middleware.config)

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        @app.get("/api/data")
        async def data():
            return {"data": "cacheable"}

        async with TestClient(app) as client:
            # Health endpoint should not be cached
            response1 = await client.get("/health")
            response2 = await client.get("/health")
            assert "x-cache" not in response1.headers
            assert "x-cache" not in response2.headers

            # Regular API should be cached
            response3 = await client.get("/api/data")
            assert response3.headers.get("x-cache") == "MISS"

            response4 = await client.get("/api/data")
            assert response4.headers.get("x-cache") == "HIT"

    async def test_cache_control_headers_utility(self):
        """Test cache control headers utility function."""
        from zenith.middleware.cache import cache_control_headers

        headers = cache_control_headers(max_age_secs=600, is_public=True)
        assert headers["Cache-Control"] == "public, max-age=600"
        assert "ETag" in headers

        private_headers = cache_control_headers(max_age_secs=300, is_public=False)
        assert private_headers["Cache-Control"] == "private, max-age=300"

    async def test_cache_with_different_response_types(self):
        """Test caching different response types."""
        app = Zenith()

        cache_config = CacheConfig(default_ttl=300)
        app.add_middleware(ResponseCacheMiddleware, config=cache_config)

        @app.get("/api/json")
        async def json_response():
            return {"type": "json", "timestamp": time.time()}

        @app.get("/api/text")
        async def text_response():
            return f"Plain text response at {time.time()}"

        @app.get("/api/custom")
        async def custom_response():
            from starlette.responses import Response

            return Response(
                content=f"Custom response at {time.time()}", media_type="text/custom"
            )

        async with TestClient(app) as client:
            # JSON response caching
            response1 = await client.get("/api/json")
            assert response1.headers.get("x-cache") == "MISS"

            response2 = await client.get("/api/json")
            assert response2.headers.get("x-cache") == "HIT"

            # Text response caching
            response3 = await client.get("/api/text")
            assert response3.headers.get("x-cache") == "MISS"

            response4 = await client.get("/api/text")
            assert response4.headers.get("x-cache") == "HIT"

            # Custom response caching
            response5 = await client.get("/api/custom")
            assert response5.headers.get("x-cache") == "MISS"

            response6 = await client.get("/api/custom")
            assert response6.headers.get("x-cache") == "HIT"
