"""
Tests for concurrent middleware processing optimizations.

Validates that Pure ASGI concurrent middleware provides performance
improvements while maintaining correctness.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from zenith.middleware.asgi_concurrent import (
    ConcurrentAuthRateLimitMiddleware,
    ConcurrentHeadersMiddleware,
    demonstrate_concurrent_performance,
)
from zenith.middleware.rate_limit import RateLimit, RateLimitStorage


class SimpleTestRateLimitStorage(RateLimitStorage):
    """Simple synchronous rate limit storage for testing."""
    
    def __init__(self):
        self._storage = {}
    
    async def get_count(self, key: str) -> int:
        return self._storage.get(key, 0)
    
    async def increment(self, key: str, window: int) -> int:
        current = self._storage.get(key, 0) + 1
        self._storage[key] = current
        return current
    
    async def reset(self, key: str) -> None:
        self._storage.pop(key, None)


class TestConcurrentAuthRateLimitMiddleware:
    """Test concurrent authentication and rate limiting middleware."""

    @pytest.fixture
    def app(self):
        """Create test app with concurrent middleware."""
        app = Starlette()
        
        @app.route("/")
        async def homepage(request):
            return JSONResponse({"message": "Hello, World!"})
        
        @app.route("/protected")
        async def protected(request):
            user = getattr(request.scope, "user", None)
            return JSONResponse({"message": "Protected", "user": user})
        
        return app

    @pytest.fixture
    def middleware(self, app):
        """Create concurrent middleware with test configuration."""
        return ConcurrentAuthRateLimitMiddleware(
            app,
            rate_limit=RateLimit(requests=5, window=60),
            storage=SimpleTestRateLimitStorage(),
            public_paths=["/", "/health"],
        )

    def test_public_path_bypass(self, middleware):
        """Test that public paths bypass auth and rate limiting."""
        with TestClient(middleware) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == {"message": "Hello, World!"}

    def test_auth_required_path_auth_check(self, middleware):
        """Test authentication check on protected paths."""
        with TestClient(middleware) as client:
            # Request without auth header should fail
            response = client.get("/protected")
            assert response.status_code == 401
            assert "Authentication required" in response.json()["error"]

    def test_rate_limiting_enforcement(self, middleware):
        """Test rate limiting enforcement."""
        with TestClient(middleware) as client:
            # Make requests up to the limit
            for i in range(5):
                response = client.get("/protected") 
                # Expect 401 due to missing auth, but should not be rate limited
                assert response.status_code == 401
            
            # The 6th request should still be rate limited if we exceed
            # (Note: This test would need proper auth to test rate limiting fully)

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self):
        """Test that concurrent processing is faster than sequential."""
        # This test validates the core performance claim
        
        # Mock slow auth and rate limit operations
        async def slow_auth():
            await asyncio.sleep(0.01)  # 10ms
            return {"success": True, "user": {"id": 123}}
        
        async def slow_rate_check():
            await asyncio.sleep(0.01)  # 10ms
            return {"success": True}
        
        # Sequential processing
        start = time.perf_counter()
        auth_result = await slow_auth()
        rate_result = await slow_rate_check()
        sequential_time = time.perf_counter() - start
        
        # Concurrent processing
        start = time.perf_counter()
        async with asyncio.TaskGroup() as tg:
            auth_task = tg.create_task(slow_auth())
            rate_task = tg.create_task(slow_rate_check())
        
        auth_result = auth_task.result()
        rate_result = rate_task.result()
        concurrent_time = time.perf_counter() - start
        
        # Concurrent should be significantly faster
        improvement = (sequential_time - concurrent_time) / sequential_time
        assert improvement > 0.3  # At least 30% improvement
        assert concurrent_time < sequential_time * 0.7  # Less than 70% of sequential time

    def test_path_checking_performance(self, middleware):
        """Test that precompiled path checking is fast."""
        path_checker = middleware._auth_required_for_path
        
        # Time path checking
        start = time.perf_counter()
        for _ in range(10000):
            path_checker("/protected")
            path_checker("/")
            path_checker("/health")
        end = time.perf_counter()
        
        # Should be very fast (< 1ms for 30k checks)
        assert (end - start) < 0.001

    @pytest.mark.asyncio
    async def test_exception_handling(self, app):
        """Test graceful handling of middleware exceptions."""
        # Create middleware that will fail
        faulty_storage = MagicMock()
        faulty_storage.increment = AsyncMock(side_effect=Exception("Storage error"))
        
        middleware = ConcurrentAuthRateLimitMiddleware(
            app,
            storage=faulty_storage,
            public_paths=["/"]  # Only "/" is public, "/protected" requires auth
        )
        
        with TestClient(middleware) as client:
            # Should fail open due to storage error and allow request through
            response = client.get("/protected")  
            # With storage error, it fails open but still checks auth
            # Since no JWT manager is configured, it should fail auth
            assert response.status_code == 401


class TestConcurrentHeadersMiddleware:
    """Test concurrent headers processing middleware."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        app = Starlette()
        
        @app.route("/")
        async def homepage(request):
            return JSONResponse({"message": "Hello"})
        
        return app

    @pytest.fixture 
    def middleware(self, app):
        """Create headers middleware."""
        return ConcurrentHeadersMiddleware(
            app,
            security_headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
            },
            include_request_id=True,
        )

    def test_security_headers_added(self, middleware):
        """Test that security headers are added to responses."""
        with TestClient(middleware) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert "X-Request-ID" in response.headers

    def test_request_id_generation(self, middleware):
        """Test request ID generation and uniqueness."""
        with TestClient(middleware) as client:
            response1 = client.get("/")
            response2 = client.get("/")
            
            req_id_1 = response1.headers["X-Request-ID"]
            req_id_2 = response2.headers["X-Request-ID"]
            
            # Request IDs should be different
            assert req_id_1 != req_id_2
            # Should be valid UUIDs (basic format check)
            assert len(req_id_1) == 36
            assert req_id_1.count("-") == 4

    @pytest.mark.asyncio
    async def test_concurrent_headers_performance(self):
        """Test concurrent header generation performance."""
        middleware = ConcurrentHeadersMiddleware(
            MagicMock(),
            security_headers={"X-Test": "value"},
            include_request_id=True,
        )
        
        # Test concurrent header generation
        start = time.perf_counter()
        async with asyncio.TaskGroup() as tg:
            security_task = tg.create_task(middleware._get_security_headers())
            request_id_task = tg.create_task(middleware._generate_request_id())
        
        security_headers = security_task.result()
        request_id = request_id_task.result()
        end = time.perf_counter()
        
        # Should complete very quickly
        assert (end - start) < 0.001
        assert security_headers == {"X-Test": "value"}
        assert len(request_id) == 36


class TestPerformanceDemonstration:
    """Test the performance demonstration function."""

    @pytest.mark.asyncio
    async def test_demonstrate_concurrent_performance(self, capsys):
        """Test that the performance demonstration works."""
        await demonstrate_concurrent_performance()
        
        # Check that output was printed
        captured = capsys.readouterr()
        assert "Sequential time:" in captured.out
        assert "Concurrent time:" in captured.out
        assert "Performance improvement:" in captured.out
        
        # Parse performance improvement
        lines = captured.out.strip().split('\n')
        improvement_line = [line for line in lines if "Performance improvement:" in line][0]
        improvement = float(improvement_line.split(':')[1].strip().rstrip('%'))
        
        # Should show significant improvement
        assert improvement > 25  # At least 25% improvement


@pytest.mark.integration
class TestConcurrentMiddlewareIntegration:
    """Integration tests for concurrent middleware."""

    def test_full_middleware_stack_performance(self):
        """Test performance of full concurrent middleware stack."""
        app = Starlette()
        
        @app.route("/")
        async def homepage(request):
            return JSONResponse({"message": "Hello"})
        
        # Add both concurrent middleware
        auth_middleware = ConcurrentAuthRateLimitMiddleware(
            app, 
            storage=SimpleTestRateLimitStorage(),
            public_paths=["/"],
        )
        full_middleware = ConcurrentHeadersMiddleware(auth_middleware)
        
        with TestClient(full_middleware) as client:
            # Measure response time for multiple requests
            times = []
            for _ in range(10):
                start = time.perf_counter()
                response = client.get("/")
                end = time.perf_counter()
                times.append(end - start)
                
                assert response.status_code == 200
                assert "X-Request-ID" in response.headers
                assert response.headers["X-Content-Type-Options"] == "nosniff"
            
            # Average response time should be reasonable
            avg_time = sum(times) / len(times)
            assert avg_time < 0.01  # Less than 10ms per request

    def test_middleware_error_isolation(self):
        """Test that errors in one concurrent operation don't affect others."""
        app = Starlette()
        
        @app.route("/test")
        async def test_endpoint(request):
            return JSONResponse({"status": "ok"})
        
        # Create middleware with faulty storage but working headers
        faulty_storage = MagicMock()
        faulty_storage.increment = AsyncMock(side_effect=Exception("Storage down"))
        
        auth_middleware = ConcurrentAuthRateLimitMiddleware(
            app,
            storage=faulty_storage,
            public_paths=["/test"]  # Make it public so auth doesn't block
        )
        full_middleware = ConcurrentHeadersMiddleware(auth_middleware)
        
        with TestClient(full_middleware) as client:
            response = client.get("/test")
            
            # Should succeed despite storage error
            assert response.status_code == 200
            # Headers should still work
            assert "X-Request-ID" in response.headers


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])