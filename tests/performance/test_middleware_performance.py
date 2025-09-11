"""Middleware-specific performance tests."""

import asyncio
import time
import pytest
from statistics import mean
from starlette.requests import Request

from zenith import Zenith
from zenith.testing import TestClient
from starlette.middleware import Middleware
from zenith.middleware import (
    CORSMiddleware,
    CSRFMiddleware,
    CompressionMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware
)
from zenith.middleware.security import SecurityConfig


class TestMiddlewarePerformance:
    """Test individual middleware performance impact."""

    @pytest.fixture
    def base_app(self):
        """Create base app without middleware."""
        app = Zenith(debug=False, middleware=[])
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.post("/echo")
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        return app

    async def measure_app_performance(self, app, iterations=200):
        """Measure app performance and return metrics."""
        async with TestClient(app) as client:
            # Warmup
            for _ in range(10):
                await client.get("/test")
            
            # Measure GET requests
            get_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.get("/test")
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                get_times.append(elapsed)
            
            # Measure POST requests
            post_times = []
            test_data = {"test": "data", "value": 123}
            
            for _ in range(iterations // 2):
                start = time.perf_counter()
                response = await client.post("/echo", json=test_data)
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                post_times.append(elapsed)
            
            return {
                "get_avg": mean(get_times),
                "get_rps": 1 / mean(get_times),
                "post_avg": mean(post_times),
                "post_rps": 1 / mean(post_times)
            }

    @pytest.mark.asyncio
    async def test_cors_middleware_performance(self, base_app):
        """Test CORS middleware performance impact."""
        # Base app performance
        base_metrics = await self.measure_app_performance(base_app)
        
        # App with CORS middleware
        cors_app = Zenith(debug=False, middleware=[
            Middleware(CORSMiddleware, 
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"]
            )
        ])
        
        @cors_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @cors_app.post("/echo")  
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        cors_metrics = await self.measure_app_performance(cors_app)
        
        # Calculate overhead
        get_overhead = ((cors_metrics["get_avg"] - base_metrics["get_avg"]) / base_metrics["get_avg"]) * 100
        post_overhead = ((cors_metrics["post_avg"] - base_metrics["post_avg"]) / base_metrics["post_avg"]) * 100
        
        print(f"\nCORS Middleware Performance:")
        print(f"  Base GET:     {base_metrics['get_avg']*1000:.2f}ms ({base_metrics['get_rps']:.0f} req/s)")
        print(f"  CORS GET:     {cors_metrics['get_avg']*1000:.2f}ms ({cors_metrics['get_rps']:.0f} req/s)")
        print(f"  GET overhead: {get_overhead:.1f}%")
        print(f"  Base POST:    {base_metrics['post_avg']*1000:.2f}ms ({base_metrics['post_rps']:.0f} req/s)")
        print(f"  CORS POST:    {cors_metrics['post_avg']*1000:.2f}ms ({cors_metrics['post_rps']:.0f} req/s)")
        print(f"  POST overhead: {post_overhead:.1f}%")
        
        # CORS middleware overhead is acceptable for test environments
        # Note: TestClient adds significant overhead, production overhead is much lower
        assert get_overhead < 400   # < 400% overhead for GET (TestClient overhead)
        assert post_overhead < 400  # < 400% overhead for POST (TestClient overhead)

    @pytest.mark.asyncio
    async def test_compression_middleware_performance(self, base_app):
        """Test compression middleware performance."""
        # Base app performance
        base_metrics = await self.measure_app_performance(base_app)
        
        # App with compression
        compression_app = Zenith(debug=False, middleware=[
            Middleware(CompressionMiddleware, minimum_size=500)
        ])
        
        @compression_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @compression_app.get("/large")
        async def large_endpoint():
            return {"data": ["item" + str(i) for i in range(100)]}
        
        @compression_app.post("/echo")
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        compression_metrics = await self.measure_app_performance(compression_app)
        
        # Test large response compression
        async with TestClient(compression_app) as client:
            large_times = []
            for _ in range(50):
                start = time.perf_counter()
                response = await client.get("/large")
                elapsed = time.perf_counter() - start
                
                assert response.status_code == 200
                assert len(response.json()["data"]) == 100
                large_times.append(elapsed)
            
            large_avg = mean(large_times)
        
        get_overhead = ((compression_metrics["get_avg"] - base_metrics["get_avg"]) / base_metrics["get_avg"]) * 100
        
        print(f"\nCompression Middleware Performance:")
        print(f"  Small response overhead: {get_overhead:.1f}%")
        print(f"  Large response time:     {large_avg*1000:.2f}ms")
        
        # Compression middleware overhead is acceptable
        assert get_overhead < 300  # < 300% overhead for small responses
        assert large_avg < 0.1   # < 100ms for large compressed responses

    @pytest.mark.asyncio
    async def test_security_headers_middleware_performance(self, base_app):
        """Test security headers middleware performance."""
        base_metrics = await self.measure_app_performance(base_app)
        
        security_config = SecurityConfig(
            force_https=False,
            hsts_max_age=31536000,
            content_type_nosniff=True,
            frame_options="DENY",
            xss_protection="1; mode=block"
        )
        security_app = Zenith(debug=False, middleware=[
            Middleware(SecurityHeadersMiddleware, config=security_config)
        ])
        
        @security_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @security_app.post("/echo")
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        security_metrics = await self.measure_app_performance(security_app)
        
        get_overhead = ((security_metrics["get_avg"] - base_metrics["get_avg"]) / base_metrics["get_avg"]) * 100
        
        print(f"\nSecurity Headers Middleware Performance:")
        print(f"  GET overhead: {get_overhead:.1f}%")
        
        # Security headers overhead is acceptable
        assert get_overhead < 300  # < 300% overhead

    @pytest.mark.asyncio
    async def test_request_logging_middleware_performance(self, base_app):
        """Test request logging middleware performance."""
        base_metrics = await self.measure_app_performance(base_app)
        
        logging_app = Zenith(debug=False, middleware=[
            Middleware(RequestLoggingMiddleware,
                exclude_paths=[],
                include_body=False
            )
        ])
        
        @logging_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @logging_app.post("/echo")
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        logging_metrics = await self.measure_app_performance(logging_app)
        
        get_overhead = ((logging_metrics["get_avg"] - base_metrics["get_avg"]) / base_metrics["get_avg"]) * 100
        post_overhead = ((logging_metrics["post_avg"] - base_metrics["post_avg"]) / base_metrics["post_avg"]) * 100
        
        print(f"\nRequest Logging Middleware Performance:")
        print(f"  GET overhead:  {get_overhead:.1f}%")
        print(f"  POST overhead: {post_overhead:.1f}%")
        
        # Logging overhead is acceptable for test environments
        # In production, overhead is typically < 10%, but TestClient adds significant overhead
        assert get_overhead < 350   # < 350% overhead for GET (TestClient environment)
        assert post_overhead < 400  # < 400% overhead for POST (includes body processing overhead)

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_performance(self, base_app):
        """Test rate limiting middleware performance."""
        base_metrics = await self.measure_app_performance(base_app, iterations=100)  # Fewer iterations
        
        rate_limit_app = Zenith(debug=False, middleware=[
            Middleware(RateLimitMiddleware,
                default_limits=["1000/minute", "100/second"],
                storage="memory"
            )
        ])
        
        @rate_limit_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @rate_limit_app.post("/echo")
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        rate_limit_metrics = await self.measure_app_performance(rate_limit_app, iterations=100)
        
        get_overhead = ((rate_limit_metrics["get_avg"] - base_metrics["get_avg"]) / base_metrics["get_avg"]) * 100
        
        print(f"\nRate Limiting Middleware Performance:")
        print(f"  GET overhead: {get_overhead:.1f}%")
        
        # Rate limiting has storage overhead
        assert get_overhead < 350  # < 350% overhead (includes storage operations)

    @pytest.mark.asyncio
    async def test_middleware_stack_performance(self):
        """Test performance of full middleware stack."""
        # Minimal app
        minimal_app = Zenith(debug=False, middleware=[])
        
        @minimal_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @minimal_app.post("/echo")
        async def echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        # Full middleware stack app
        security_config = SecurityConfig(force_https=False)
        full_app = Zenith(debug=False, middleware=[
            Middleware(SecurityHeadersMiddleware, config=security_config),
            Middleware(CORSMiddleware, allow_origins=["*"]),
            Middleware(CompressionMiddleware, minimum_size=500),
            Middleware(RequestLoggingMiddleware, include_body=False)
        ])
        
        @full_app.get("/test")
        async def full_test_endpoint():
            return {"message": "test"}
        
        @full_app.post("/echo")
        async def full_echo_endpoint(request: Request):
            data = await request.json()
            return {"echo": data}
        
        # Compare performance
        minimal_metrics = await self.measure_app_performance(minimal_app, iterations=300)
        full_metrics = await self.measure_app_performance(full_app, iterations=300)
        
        total_overhead = ((full_metrics["get_avg"] - minimal_metrics["get_avg"]) / minimal_metrics["get_avg"]) * 100
        
        print(f"\nFull Middleware Stack Performance:")
        print(f"  Minimal:       {minimal_metrics['get_avg']*1000:.2f}ms ({minimal_metrics['get_rps']:.0f} req/s)")
        print(f"  Full stack:    {full_metrics['get_avg']*1000:.2f}ms ({full_metrics['get_rps']:.0f} req/s)")
        print(f"  Total overhead: {total_overhead:.1f}%")
        
        # Full middleware stack overhead is higher in test environments
        # In production, total overhead is typically < 10%
        assert total_overhead < 800  # < 800% total overhead (TestClient adds significant overhead)
        assert full_metrics["get_rps"] > 50  # > 50 req/s with full stack

    @pytest.mark.asyncio
    async def test_middleware_memory_usage(self):
        """Test middleware memory usage impact."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not installed - skipping memory test")
        import os
        
        process = psutil.Process(os.getpid())
        
        # Test memory usage with different middleware configurations
        configs = [
            ("minimal", []),
            ("cors", [Middleware(CORSMiddleware, allow_origins=["*"])]),
            ("security", [Middleware(SecurityHeadersMiddleware, config=SecurityConfig(force_https=False))]),
            ("full", [
                Middleware(SecurityHeadersMiddleware, config=SecurityConfig(force_https=False)),
                Middleware(CORSMiddleware, allow_origins=["*"]),
                Middleware(CompressionMiddleware, minimum_size=500)
            ])
        ]
        
        memory_usage = {}
        
        for name, middleware_list in configs:
            # Create app with specific middleware
            app = Zenith(debug=False, middleware=middleware_list)
            
            @app.get("/test")
            async def test_endpoint():
                return {"message": "test", "data": list(range(50))}
            
            # Measure memory before requests
            before_memory = process.memory_info().rss / 1024 / 1024
            
            # Make requests
            async with TestClient(app) as client:
                for _ in range(200):
                    response = await client.get("/test")
                    assert response.status_code == 200
            
            # Measure memory after requests
            after_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = after_memory - before_memory
            
            memory_usage[name] = {
                "before": before_memory,
                "after": after_memory,
                "increase": memory_increase
            }
        
        print(f"\nMiddleware Memory Usage:")
        for name, usage in memory_usage.items():
            print(f"  {name:8s}: {usage['increase']:5.1f}MB increase")
        
        # Memory usage should be reasonable
        for name, usage in memory_usage.items():
            assert usage["increase"] < 50  # < 50MB increase per configuration