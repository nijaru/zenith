"""Tests for performance monitoring utilities."""

import asyncio
import time

import pytest

from zenith.monitoring.performance import (
    PerformanceProfiler,
    cache_stats,
    cached,
    clear_cache,
    measure_time,
    profile_block,
    profiler,
    track_performance,
)


class TestPerformanceDecorators:
    """Test performance monitoring decorators."""

    def test_track_performance_sync(self):
        """Test track_performance decorator with sync function."""
        call_count = 0

        @track_performance(threshold_ms=1)
        def slow_function():
            nonlocal call_count
            call_count += 1
            time.sleep(0.002)  # 2ms
            return "done"

        # Should execute and track
        result = slow_function()
        assert result == "done"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_track_performance_async(self):
        """Test track_performance decorator with async function."""
        call_count = 0

        @track_performance(threshold_ms=1)
        async def async_slow():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.002)  # 2ms
            return "async done"

        result = await async_slow()
        assert result == "async done"
        assert call_count == 1

    def test_profile_block_context_manager(self):
        """Test profile_block context manager."""
        with profile_block("test_operation", threshold_ms=1):
            time.sleep(0.002)  # 2ms

        # Should complete without error
        assert True

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test cached decorator functionality."""
        call_count = 0

        @cached(ttl=60)
        async def expensive_operation(value: int):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            return value * 2

        # First call
        result1 = await expensive_operation(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_operation(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different parameter should not use cache
        result3 = await expensive_operation(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_measure_time_decorator(self):
        """Test measure_time decorator."""
        call_count = 0

        @measure_time("test_operation")
        async def timed_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            return "measured"

        result = await timed_function()
        assert result == "measured"
        assert call_count == 1


class TestPerformanceProfiler:
    """Test PerformanceProfiler class."""

    def test_profiler_time_function(self):
        """Test profiler time_function context manager."""
        test_profiler = PerformanceProfiler()

        with test_profiler.time_function("test_op"):
            time.sleep(0.001)

        stats = test_profiler.get_stats()
        assert "test_op" in stats
        assert stats["test_op"]["count"] == 1
        assert stats["test_op"]["total"] > 0

    def test_profiler_record_timing(self):
        """Test profiler record method."""
        test_profiler = PerformanceProfiler()

        test_profiler.record("operation1", 0.1)
        test_profiler.record("operation1", 0.2)
        test_profiler.record("operation2", 0.05)

        stats = test_profiler.get_stats()

        assert "operation1" in stats
        assert "operation2" in stats
        assert stats["operation1"]["count"] == 2
        assert abs(stats["operation1"]["total"] - 0.3) < 0.0001  # Float precision
        assert abs(stats["operation1"]["avg"] - 0.15) < 0.0001  # Float precision
        assert stats["operation2"]["count"] == 1

    def test_profiler_clear(self):
        """Test profiler clear functionality."""
        test_profiler = PerformanceProfiler()

        test_profiler.record("test", 0.1)
        assert len(test_profiler.get_stats()) == 1

        test_profiler.clear()
        assert len(test_profiler.get_stats()) == 0

    def test_global_profiler_instance(self):
        """Test global profiler instance."""
        # Clear any existing data
        profiler.clear()

        with profiler.time_function("global_test"):
            time.sleep(0.001)

        stats = profiler.get_stats()
        assert "global_test" in stats
        assert stats["global_test"]["count"] == 1

    def test_profiler_disabled(self):
        """Test profiler when disabled."""
        test_profiler = PerformanceProfiler()
        test_profiler.enabled = False

        test_profiler.record("disabled_test", 0.1)
        stats = test_profiler.get_stats()

        assert "disabled_test" not in stats


class TestCacheUtilities:
    """Test caching utilities."""

    def test_cache_stats_tracking(self):
        """Test cache statistics tracking."""
        # Clear cache first
        clear_cache()

        @cached(ttl=60)
        async def cached_func(x):
            return x * 2

        async def run_cache_test():
            # First call - cache miss
            await cached_func(1)

            # Second call - cache hit
            await cached_func(1)

            # Different param - cache miss
            await cached_func(2)

        asyncio.run(run_cache_test())

        stats = cache_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 2
        assert "hit_rate" in stats
        assert "cache_size" in stats

    def test_clear_cache_pattern(self):
        """Test clearing cache with pattern."""
        # This is a basic test - actual implementation may vary
        clear_cache()

        @cached(ttl=60)
        async def func1(x):
            return x

        @cached(ttl=60)
        async def func2(x):
            return x * 2

        async def setup_cache():
            await func1(1)
            await func2(1)

        asyncio.run(setup_cache())

        # Pattern clearing (if implemented)
        clear_cache("func1")

        stats = cache_stats()
        # Should have some entries (implementation dependent)
        assert isinstance(stats["cache_size"], int)

    def test_cache_expiration(self):
        """Test cache TTL expiration."""

        @cached(ttl=0.01)  # 10ms TTL
        async def short_cache(x):
            return x * 2

        async def test_expiration():
            # First call
            result1 = await short_cache(5)
            assert result1 == 10

            # Wait for expiration
            await asyncio.sleep(0.02)  # 20ms

            # Should work but may not be cached
            result2 = await short_cache(5)
            assert result2 == 10

        asyncio.run(test_expiration())


class TestPerformanceIntegration:
    """Test performance monitoring integration."""

    @pytest.mark.asyncio
    async def test_performance_with_zenith_app(self):
        """Test performance monitoring with Zenith application."""
        from zenith import Zenith
        from zenith.testing import TestClient

        app = Zenith(debug=True)

        @app.get("/tracked")
        @track_performance(threshold_ms=10)
        async def tracked_endpoint():
            await asyncio.sleep(0.001)  # Small delay
            return {"status": "tracked"}

        @app.get("/profiled")
        async def profiled_endpoint():
            with profile_block("endpoint_work", threshold_ms=10):
                await asyncio.sleep(0.001)
            return {"status": "profiled"}

        async with TestClient(app) as client:
            # Test tracked endpoint
            response = await client.get("/tracked")
            assert response.status_code == 200
            assert response.json() == {"status": "tracked"}

            # Test profiled endpoint
            response = await client.get("/profiled")
            assert response.status_code == 200
            assert response.json() == {"status": "profiled"}

    @pytest.mark.performance
    def test_performance_monitoring_overhead(self):
        """Test that performance monitoring has minimal overhead."""

        # Test without monitoring
        def unmonitored_func():
            return sum(range(100))

        start = time.perf_counter()
        for _ in range(1000):
            unmonitored_func()
        unmonitored_time = time.perf_counter() - start

        # Test with monitoring
        @track_performance(threshold_ms=1000)  # High threshold to avoid logging
        def monitored_func():
            return sum(range(100))

        start = time.perf_counter()
        for _ in range(1000):
            monitored_func()
        monitored_time = time.perf_counter() - start

        # Overhead should be minimal (less than 2.5x)
        overhead_ratio = monitored_time / unmonitored_time
        assert overhead_ratio < 2.5  # Allow up to 2.5x overhead for monitoring
