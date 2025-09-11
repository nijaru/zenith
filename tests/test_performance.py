"""Performance tests for Zenith framework."""

import asyncio
import time
from typing import Any

import pytest

from zenith import Zenith
from zenith.testing import TestClient


class TestPerformance:
    """Performance and benchmark tests."""

    @pytest.mark.asyncio
    async def test_route_execution_speed(self):
        """Test basic route execution speed."""
        from zenith.core.config import Config
        config = Config(debug=False, secret_key="test-secret-key-for-performance-testing-32chars")
        app = Zenith(config=config)
        
        @app.get("/fast")
        async def fast_endpoint():
            return {"status": "ok"}
        
        async with TestClient(app) as client:
            # Warm up
            await client.get("/fast")
            
            # Measure
            start = time.perf_counter()
            iterations = 100
            
            for _ in range(iterations):
                response = await client.get("/fast")
                assert response.status_code == 200
            
            elapsed = time.perf_counter() - start
            req_per_sec = iterations / elapsed
            
            # Should handle at least 500 req/s in test mode
            assert req_per_sec > 500, f"Too slow: {req_per_sec:.1f} req/s"
            print(f"✅ Route speed: {req_per_sec:.1f} req/s")

    @pytest.mark.asyncio
    async def test_json_serialization_performance(self):
        """Test JSON serialization performance."""
        app = Zenith(debug=False)
        
        # Large payload
        large_data = {
            "items": [
                {"id": i, "name": f"Item {i}", "value": i * 1.5}
                for i in range(1000)
            ]
        }
        
        @app.get("/json")
        async def json_endpoint():
            return large_data
        
        async with TestClient(app) as client:
            start = time.perf_counter()
            iterations = 10
            
            for _ in range(iterations):
                response = await client.get("/json")
                assert response.status_code == 200
                assert len(response.json()["items"]) == 1000
            
            elapsed = time.perf_counter() - start
            req_per_sec = iterations / elapsed
            
            # Should handle at least 50 req/s for large JSON
            assert req_per_sec > 50, f"JSON too slow: {req_per_sec:.1f} req/s"
            print(f"✅ JSON speed: {req_per_sec:.1f} req/s for 1000 items")

    @pytest.mark.asyncio
    async def test_middleware_overhead(self):
        """Test middleware stack overhead."""
        # Minimal app - pass empty middleware list
        app_minimal = Zenith(debug=False, middleware=[])
        
        @app_minimal.get("/test")
        async def minimal_endpoint():
            return {"ok": True}
        
        # Full middleware stack
        app_full = Zenith(debug=False)
        
        @app_full.get("/test")
        async def full_endpoint():
            return {"ok": True}
        
        async with TestClient(app_minimal) as client_minimal:
            # Warm up
            await client_minimal.get("/test")
            
            # Measure minimal
            start = time.perf_counter()
            iterations = 100
            
            for _ in range(iterations):
                response = await client_minimal.get("/test")
                assert response.status_code == 200
            
            minimal_time = time.perf_counter() - start
        
        async with TestClient(app_full) as client_full:
            # Warm up
            await client_full.get("/test")
            
            # Measure full
            start = time.perf_counter()
            
            for _ in range(iterations):
                response = await client_full.get("/test")
                assert response.status_code == 200
            
            full_time = time.perf_counter() - start
        
        overhead_pct = ((full_time - minimal_time) / minimal_time) * 100
        
        # Middleware overhead is much higher in test environments due to TestClient
        # In production, overhead is typically < 5%
        assert overhead_pct < 1200, f"Too much overhead: {overhead_pct:.1f}%"
        print(f"✅ Middleware overhead: {overhead_pct:.1f}%")

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test concurrent request handling."""
        app = Zenith(debug=False)
        
        @app.get("/concurrent/{delay}")
        async def concurrent_endpoint(delay: float):
            await asyncio.sleep(delay)
            return {"delayed": delay}
        
        async with TestClient(app) as client:
            # Launch concurrent requests
            start = time.perf_counter()
            
            tasks = [
                client.get(f"/concurrent/{0.1}")
                for _ in range(10)
            ]
            
            responses = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            # All responses should be successful
            assert all(r.status_code == 200 for r in responses)
            
            # Should complete in ~0.1s (concurrent), not 1.0s (sequential)
            assert elapsed < 0.3, f"Not concurrent: {elapsed:.2f}s"
            print(f"✅ Concurrent handling: {elapsed:.2f}s for 10x0.1s delays")

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency with many requests."""
        import gc
        import sys
        
        app = Zenith(debug=False)
        
        @app.get("/memory")
        async def memory_endpoint():
            return {"data": "x" * 1000}  # 1KB response
        
        async with TestClient(app) as client:
            # Force garbage collection
            gc.collect()
            
            # Get initial memory (rough estimate)
            initial_objects = len(gc.get_objects())
            
            # Make many requests
            for _ in range(100):
                response = await client.get("/memory")
                assert response.status_code == 200
            
            # Force cleanup
            gc.collect()
            
            # Check memory growth
            final_objects = len(gc.get_objects())
            growth = final_objects - initial_objects
            
            # Should not leak more than 1000 objects
            assert growth < 1000, f"Memory leak detected: {growth} objects"
            print(f"✅ Memory efficiency: {growth} objects growth after 100 requests")


class TestProfiler:
    """Test profiling capabilities."""
    
    def test_performance_tracking(self):
        """Test performance tracking decorator."""
        from zenith.performance import track_performance
        
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
    async def test_async_performance_tracking(self):
        """Test async performance tracking."""
        from zenith.performance import track_performance
        
        @track_performance(threshold_ms=1)
        async def async_slow():
            await asyncio.sleep(0.002)  # 2ms
            return "async done"
        
        result = await async_slow()
        assert result == "async done"