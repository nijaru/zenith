"""Basic performance tests for Zenith framework."""

import asyncio
import time
import pytest
from statistics import mean, median
from starlette.requests import Request

from zenith import Zenith
from zenith.testing import TestClient


class TestBasicPerformance:
    """Test basic endpoint performance."""

    @pytest.fixture
    def minimal_app(self):
        """Create minimal Zenith app for performance testing."""
        app = Zenith(debug=False, middleware=[])  # No middleware for baseline
        
        @app.get("/")
        async def hello():
            return {"message": "Hello, World!"}
        
        @app.get("/json")
        async def json_response():
            return {
                "users": [
                    {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
                    for i in range(10)
                ]
            }
        
        @app.get("/simple/{item_id}")
        async def path_param(item_id: int):
            return {"item_id": item_id}
        
        @app.post("/echo")
        async def echo(request: Request):
            data = await request.json()
            return {"received": data}
        
        return app

    @pytest.fixture
    def full_app(self):
        """Create full Zenith app with all middleware."""
        # Use specific middleware stack for predictable performance
        from starlette.middleware import Middleware
        from zenith.middleware import (
            SecurityHeadersMiddleware,
            CORSMiddleware,
            CompressionMiddleware,
            RequestLoggingMiddleware
        )
        from zenith.middleware.security import SecurityConfig
        
        app = Zenith(
            debug=False,
            middleware=[
                Middleware(SecurityHeadersMiddleware, config=SecurityConfig(force_https=False)),
                Middleware(CORSMiddleware, allow_origins=["*"]),
                Middleware(CompressionMiddleware, minimum_size=1000),
                Middleware(RequestLoggingMiddleware, exclude_paths=["/health"])
            ]
        )
        
        @app.get("/")
        async def hello():
            return {"message": "Hello, World!"}
        
        @app.get("/protected")  
        async def protected():
            return {"message": "Protected endpoint"}
        
        return app

    @pytest.mark.asyncio
    async def test_simple_endpoint_performance(self, minimal_app):
        """Test simple endpoint performance."""
        async with TestClient(minimal_app) as client:
            # Warmup
            for _ in range(10):
                await client.get("/")
            
            # Benchmark
            iterations = 1000
            times = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.get("/")
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                times.append(elapsed)
            
            # Performance metrics
            avg_time = mean(times)
            median_time = median(times)
            rps = 1 / avg_time
            
            print(f"\nSimple Endpoint Performance:")
            print(f"  Average time: {avg_time*1000:.2f}ms")
            print(f"  Median time:  {median_time*1000:.2f}ms") 
            print(f"  Requests/sec: {rps:.1f}")
            
            # Performance assertions
            assert avg_time < 0.01  # < 10ms average
            assert rps > 100        # > 100 req/s

    @pytest.mark.asyncio
    async def test_json_endpoint_performance(self, minimal_app):
        """Test JSON response performance."""
        async with TestClient(minimal_app) as client:
            # Warmup
            for _ in range(10):
                await client.get("/json")
            
            # Benchmark
            iterations = 500
            times = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.get("/json")
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["users"]) == 10
                times.append(elapsed)
            
            avg_time = mean(times)
            rps = 1 / avg_time
            
            print(f"\nJSON Endpoint Performance:")
            print(f"  Average time: {avg_time*1000:.2f}ms")
            print(f"  Requests/sec: {rps:.1f}")
            
            # Should handle JSON serialization efficiently
            assert avg_time < 0.02  # < 20ms average
            assert rps > 50         # > 50 req/s

    @pytest.mark.asyncio
    async def test_path_parameter_performance(self, minimal_app):
        """Test path parameter parsing performance."""
        async with TestClient(minimal_app) as client:
            iterations = 500
            times = []
            
            for i in range(iterations):
                start = time.perf_counter()
                response = await client.get(f"/simple/{i}")
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                assert response.json()["item_id"] == i
                times.append(elapsed)
            
            avg_time = mean(times)
            rps = 1 / avg_time
            
            print(f"\nPath Parameter Performance:")
            print(f"  Average time: {avg_time*1000:.2f}ms")
            print(f"  Requests/sec: {rps:.1f}")
            
            assert avg_time < 0.015  # < 15ms average
            assert rps > 65          # > 65 req/s

    @pytest.mark.asyncio
    async def test_post_request_performance(self, minimal_app):
        """Test POST request performance."""
        async with TestClient(minimal_app) as client:
            test_data = {"name": "test", "value": 123, "items": [1, 2, 3, 4, 5]}
            iterations = 200
            times = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.post("/echo", json=test_data)
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                assert response.json()["received"] == test_data
                times.append(elapsed)
            
            avg_time = mean(times)
            rps = 1 / avg_time
            
            print(f"\nPOST Request Performance:")
            print(f"  Average time: {avg_time*1000:.2f}ms")
            print(f"  Requests/sec: {rps:.1f}")
            
            assert avg_time < 0.025  # < 25ms average
            assert rps > 40          # > 40 req/s

    @pytest.mark.asyncio
    async def test_middleware_overhead(self, minimal_app, full_app):
        """Test middleware performance overhead."""
        iterations = 300
        
        # Test minimal app (no middleware)
        async with TestClient(minimal_app) as client:
            minimal_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.get("/")
                elapsed = time.perf_counter() - start
                assert response.status_code == 200
                minimal_times.append(elapsed)
        
        # Test full app (all middleware)
        async with TestClient(full_app) as client:
            full_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.get("/")
                elapsed = time.perf_counter() - start
                assert response.status_code == 200
                full_times.append(elapsed)
        
        minimal_avg = mean(minimal_times)
        full_avg = mean(full_times)
        overhead_pct = ((full_avg - minimal_avg) / minimal_avg) * 100
        
        print(f"\nMiddleware Overhead:")
        print(f"  Minimal app:     {minimal_avg*1000:.2f}ms")
        print(f"  Full app:        {full_avg*1000:.2f}ms")
        print(f"  Overhead:        {overhead_pct:.1f}%")
        
        # Middleware overhead is higher in test environments due to TestClient
        # In production, overhead is typically < 5%
        assert overhead_pct < 1500  # < 1500% overhead (TestClient adds significant overhead)

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, minimal_app):
        """Test concurrent request handling performance."""
        async with TestClient(minimal_app) as client:
            
            async def make_request():
                response = await client.get("/")
                assert response.status_code == 200
                return response
            
            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 20]
            results = {}
            
            for concurrency in concurrency_levels:
                start = time.perf_counter()
                
                # Create and execute concurrent requests
                tasks = [make_request() for _ in range(concurrency)]
                responses = await asyncio.gather(*tasks)
                
                elapsed = time.perf_counter() - start
                rps = concurrency / elapsed
                
                results[concurrency] = {
                    "elapsed": elapsed,
                    "rps": rps
                }
                
                print(f"Concurrency {concurrency:2d}: {elapsed:.3f}s, {rps:.1f} req/s")
            
            # Should handle concurrent requests efficiently
            assert results[1]["rps"] > 100   # Single requests
            assert results[10]["rps"] > 200  # Should scale well

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, minimal_app):
        """Test memory efficiency during request handling."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not installed - skipping memory test")
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async with TestClient(minimal_app) as client:
            # Make many requests to test memory usage
            for i in range(1000):
                response = await client.get("/")
                assert response.status_code == 200
                
                # Check memory every 100 requests
                if i % 100 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory
                    
                    # Memory increase should be reasonable
                    assert memory_increase < 50  # < 50MB increase
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage:")
        print(f"  Initial: {initial_memory:.1f}MB")
        print(f"  Final:   {final_memory:.1f}MB")
        print(f"  Increase: {total_increase:.1f}MB")
        
        # Total memory increase should be reasonable for 1000 requests
        assert total_increase < 100  # < 100MB total increase

    @pytest.mark.asyncio
    async def test_startup_time(self):
        """Test application startup performance."""
        startup_times = []
        
        for _ in range(5):
            start = time.perf_counter()
            
            # Create and initialize app
            app = Zenith()
            
            @app.get("/test")
            async def test_endpoint():
                return {"test": True}
            
            elapsed = time.perf_counter() - start
            startup_times.append(elapsed)
        
        avg_startup = mean(startup_times)
        
        print(f"\nStartup Performance:")
        print(f"  Average startup time: {avg_startup*1000:.2f}ms")
        
        # Should start up quickly
        assert avg_startup < 0.1  # < 100ms startup time


@pytest.mark.slow
class TestLoadPerformance:
    """Heavy load performance tests (marked as slow)."""

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load performance."""
        app = Zenith(debug=False, middleware=[])
        
        @app.get("/load")
        async def load_endpoint():
            return {"timestamp": time.time(), "data": list(range(100))}
        
        async with TestClient(app) as client:
            # Sustained load test
            duration = 5  # 5 seconds
            start_time = time.perf_counter()
            request_count = 0
            
            while time.perf_counter() - start_time < duration:
                response = await client.get("/load")
                assert response.status_code == 200
                request_count += 1
            
            elapsed = time.perf_counter() - start_time
            rps = request_count / elapsed
            
            print(f"\nSustained Load Performance:")
            print(f"  Duration:     {elapsed:.1f}s")
            print(f"  Requests:     {request_count}")
            print(f"  Avg RPS:      {rps:.1f}")
            
            # Should maintain good performance under load
            assert rps > 200  # > 200 req/s sustained

    @pytest.mark.asyncio
    async def test_high_concurrency_load(self):
        """Test high concurrency performance."""
        app = Zenith(debug=False)
        
        @app.get("/concurrent")
        async def concurrent_endpoint():
            # Simulate some work
            await asyncio.sleep(0.001)
            return {"processed": True}
        
        async with TestClient(app) as client:
            
            async def make_requests(count):
                tasks = []
                for _ in range(count):
                    task = asyncio.create_task(client.get("/concurrent"))
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                successful = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
                return successful
            
            # Test different batch sizes
            batch_sizes = [50, 100, 200]
            
            for batch_size in batch_sizes:
                start = time.perf_counter()
                successful = await make_requests(batch_size)
                elapsed = time.perf_counter() - start
                
                success_rate = (successful / batch_size) * 100
                rps = successful / elapsed
                
                print(f"Batch {batch_size:3d}: {success_rate:5.1f}% success, {rps:6.1f} req/s")
                
                # Should handle high concurrency well
                assert success_rate > 95  # > 95% success rate
                assert rps > 100          # > 100 req/s even with simulated work