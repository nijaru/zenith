"""
Sustained load and performance tests.

Tests the framework under realistic production load patterns,
memory leaks, and performance degradation over time.
"""

import asyncio
import gc
import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict
from unittest.mock import Mock
import tempfile
import random
import statistics

import pytest

from zenith import Zenith
from zenith.testing import TestClient
from zenith.db import ZenithModel
from sqlmodel import Field


# Test models
class LoadTestUser(ZenithModel, table=True):
    """User model for load testing."""
    __tablename__ = "load_test_users"

    id: int | None = Field(primary_key=True)
    username: str = Field(unique=True)
    email: str
    created_at: datetime = Field(default_factory=datetime.now)
    request_count: int = Field(default=0)


class LoadTestMetric(ZenithModel, table=True):
    """Metrics collection for load testing."""
    __tablename__ = "load_test_metrics"

    id: int | None = Field(primary_key=True)
    endpoint: str
    response_time_ms: float
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.now)


def get_memory_usage():
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


@pytest.mark.asyncio
class TestSustainedLoad:
    """Test framework under sustained load."""

    async def test_sustained_request_load(self):
        """Test handling sustained request load."""
        app = Zenith()

        # Track metrics
        request_times = []
        error_count = 0

        @app.get("/load/simple")
        async def simple_endpoint():
            return {"status": "ok", "timestamp": datetime.now().isoformat()}

        @app.get("/load/compute")
        async def compute_endpoint():
            # Simulate some computation
            result = sum(i * i for i in range(1000))
            return {"result": result}

        @app.post("/load/data")
        async def data_endpoint(data: dict):
            # Simulate processing
            await asyncio.sleep(0.01)
            return {"processed": len(data), "status": "complete"}

        async with TestClient(app) as client:
            start_time = time.time()
            duration = 5  # Run for 5 seconds

            async def make_request(endpoint: str, method: str = "GET", data: dict = None):
                """Make a request and track metrics."""
                nonlocal error_count

                req_start = time.time()
                try:
                    if method == "GET":
                        response = await client.get(endpoint)
                    else:
                        response = await client.post(endpoint, json=data or {})

                    req_time = (time.time() - req_start) * 1000  # Convert to ms
                    request_times.append(req_time)

                    if response.status_code != 200:
                        error_count += 1

                    return response
                except Exception:
                    error_count += 1
                    return None

            # Generate load
            request_count = 0
            while time.time() - start_time < duration:
                # Mix of different endpoints
                tasks = []

                # Simple endpoints (60%)
                for _ in range(6):
                    tasks.append(make_request("/load/simple"))

                # Compute endpoints (30%)
                for _ in range(3):
                    tasks.append(make_request("/load/compute"))

                # Data endpoints (10%)
                tasks.append(make_request(
                    "/load/data",
                    "POST",
                    {"data": [i for i in range(100)]}
                ))

                await asyncio.gather(*tasks)
                request_count += 10

                # Small delay between batches
                await asyncio.sleep(0.05)

            # Analyze results
            avg_response_time = statistics.mean(request_times)
            p95_response_time = statistics.quantile(request_times, 0.95)
            p99_response_time = statistics.quantile(request_times, 0.99)

            # Performance assertions
            assert avg_response_time < 100  # Average under 100ms
            assert p95_response_time < 200  # 95th percentile under 200ms
            assert p99_response_time < 500  # 99th percentile under 500ms
            assert error_count < request_count * 0.01  # Less than 1% errors

            # Log results for debugging
            print(f"\nLoad Test Results:")
            print(f"  Total Requests: {request_count}")
            print(f"  Average Response: {avg_response_time:.2f}ms")
            print(f"  P95 Response: {p95_response_time:.2f}ms")
            print(f"  P99 Response: {p99_response_time:.2f}ms")
            print(f"  Error Rate: {(error_count/request_count)*100:.2f}%")

    async def test_memory_leak_detection(self):
        """Test for memory leaks under sustained load."""
        app = Zenith()

        @app.post("/memory/allocate")
        async def allocate_memory(size: int = 1000):
            # Allocate some memory
            data = "x" * size
            return {"allocated": size, "sample": data[:10]}

        @app.get("/memory/process")
        async def process_data():
            # Create and process data
            data = [i * i for i in range(1000)]
            result = sum(data)
            return {"result": result}

        async with TestClient(app) as client:
            # Force garbage collection and get baseline
            gc.collect()
            baseline_memory = get_memory_usage()

            # Run sustained load
            for iteration in range(10):
                # Make many requests
                tasks = []
                for _ in range(100):
                    tasks.append(client.post("/memory/allocate", json={"size": 10000}))
                    tasks.append(client.get("/memory/process"))

                await asyncio.gather(*tasks)

                # Force garbage collection
                gc.collect()

                # Check memory after each iteration
                current_memory = get_memory_usage()
                memory_increase = current_memory - baseline_memory

                print(f"Iteration {iteration}: Memory increase: {memory_increase:.2f}MB")

            # Final memory check
            gc.collect()
            final_memory = get_memory_usage()
            total_increase = final_memory - baseline_memory

            # Should not leak excessively (allow some increase for caches)
            assert total_increase < 50  # Less than 50MB increase

    async def test_concurrent_user_simulation(self):
        """Simulate realistic concurrent user load."""
        app = Zenith()

        # Setup database
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            app.config.database_url = f"sqlite+aiosqlite:///{tmp.name}"

            # User session tracking
            active_sessions = {}

            @app.post("/auth/login")
            async def login(username: str, password: str):
                # Simulate authentication
                await asyncio.sleep(0.05)  # Simulate password check
                session_id = f"session_{username}_{time.time()}"
                active_sessions[session_id] = {
                    "username": username,
                    "login_time": datetime.now()
                }
                return {"session_id": session_id}

            @app.get("/api/profile")
            async def get_profile(session_id: str):
                if session_id not in active_sessions:
                    return {"error": "Not authenticated"}, 401

                session = active_sessions[session_id]
                return {
                    "username": session["username"],
                    "login_time": session["login_time"].isoformat()
                }

            @app.post("/api/action")
            async def perform_action(session_id: str, action: str):
                if session_id not in active_sessions:
                    return {"error": "Not authenticated"}, 401

                # Simulate processing
                await asyncio.sleep(random.uniform(0.01, 0.1))

                return {
                    "action": action,
                    "result": "completed",
                    "timestamp": datetime.now().isoformat()
                }

            @app.post("/auth/logout")
            async def logout(session_id: str):
                if session_id in active_sessions:
                    del active_sessions[session_id]
                return {"status": "logged out"}

            async with TestClient(app) as client:
                await app.database.create_all()

                async def simulate_user(user_id: int):
                    """Simulate a user session."""
                    username = f"user_{user_id}"

                    # Login
                    login_resp = await client.post("/auth/login", json={
                        "username": username,
                        "password": "password"
                    })
                    session_id = login_resp.json()["session_id"]

                    # Perform various actions
                    for _ in range(random.randint(5, 15)):
                        # Random action
                        action_type = random.choice([
                            "view_profile",
                            "update_settings",
                            "fetch_data",
                            "submit_form"
                        ])

                        # Get profile
                        await client.get(f"/api/profile?session_id={session_id}")

                        # Perform action
                        await client.post("/api/action", json={
                            "session_id": session_id,
                            "action": action_type
                        })

                        # Random think time
                        await asyncio.sleep(random.uniform(0.1, 0.5))

                    # Logout
                    await client.post("/auth/logout", json={"session_id": session_id})

                # Simulate many concurrent users
                user_count = 50
                start_time = time.time()

                # Create user tasks
                user_tasks = [simulate_user(i) for i in range(user_count)]
                await asyncio.gather(*user_tasks)

                elapsed = time.time() - start_time

                print(f"\nConcurrent User Simulation:")
                print(f"  Users: {user_count}")
                print(f"  Total Time: {elapsed:.2f}s")
                print(f"  Peak Sessions: {len(active_sessions)}")

                # Should handle all users efficiently
                assert elapsed < 30  # Should complete in under 30 seconds


@pytest.mark.asyncio
class TestPerformanceDegradation:
    """Test for performance degradation over time."""

    async def test_response_time_consistency(self):
        """Test that response times remain consistent over time."""
        app = Zenith()

        request_counter = 0

        @app.get("/consistent")
        async def consistent_endpoint():
            nonlocal request_counter
            request_counter += 1
            # Simulate some work
            result = sum(i for i in range(1000))
            return {"count": request_counter, "result": result}

        async with TestClient(app) as client:
            buckets = []  # Store response times in buckets

            # Run for multiple time buckets
            for bucket_id in range(10):
                bucket_times = []

                # Make requests in this bucket
                for _ in range(100):
                    start = time.time()
                    response = await client.get("/consistent")
                    elapsed = (time.time() - start) * 1000
                    bucket_times.append(elapsed)

                    assert response.status_code == 200

                # Calculate bucket statistics
                bucket_avg = statistics.mean(bucket_times)
                buckets.append(bucket_avg)

                # Small delay between buckets
                await asyncio.sleep(0.1)

            # Check for degradation
            first_bucket_avg = buckets[0]
            last_bucket_avg = buckets[-1]

            # Performance should not degrade significantly
            degradation = (last_bucket_avg - first_bucket_avg) / first_bucket_avg
            assert degradation < 0.2  # Less than 20% degradation

            print(f"\nPerformance Consistency:")
            print(f"  First Bucket Avg: {first_bucket_avg:.2f}ms")
            print(f"  Last Bucket Avg: {last_bucket_avg:.2f}ms")
            print(f"  Degradation: {degradation * 100:.2f}%")

    async def test_cache_performance(self):
        """Test cache performance under load."""
        app = Zenith()

        cache = {}
        cache_hits = 0
        cache_misses = 0

        @app.get("/cached/{key}")
        async def cached_endpoint(key: str):
            nonlocal cache_hits, cache_misses

            if key in cache:
                cache_hits += 1
                return {"data": cache[key], "cached": True}
            else:
                cache_misses += 1
                # Simulate expensive operation
                await asyncio.sleep(0.05)
                value = f"computed_value_for_{key}"
                cache[key] = value
                return {"data": value, "cached": False}

        async with TestClient(app) as client:
            # Warm up cache
            for i in range(10):
                await client.get(f"/cached/key_{i}")

            # Test cache performance
            request_times = []
            for _ in range(100):
                # Mix of cached and new keys
                if random.random() < 0.7:  # 70% cached
                    key = f"key_{random.randint(0, 9)}"
                else:  # 30% new
                    key = f"key_{random.randint(100, 200)}"

                start = time.time()
                response = await client.get(f"/cached/{key}")
                elapsed = (time.time() - start) * 1000
                request_times.append(elapsed)

            # Analyze cache performance
            hit_rate = cache_hits / (cache_hits + cache_misses)
            avg_time = statistics.mean(request_times)

            print(f"\nCache Performance:")
            print(f"  Hit Rate: {hit_rate * 100:.2f}%")
            print(f"  Average Response: {avg_time:.2f}ms")

            # Cache should improve performance
            assert hit_rate > 0.6  # At least 60% hit rate
            assert avg_time < 30  # Good average response time


@pytest.mark.asyncio
class TestRealWorldScenarios:
    """Test realistic production scenarios."""

    async def test_api_rate_limiting_under_load(self):
        """Test rate limiting behavior under load."""
        app = Zenith()

        # Simple rate limiting
        request_counts = {}

        @app.get("/rate-limited")
        async def rate_limited_endpoint(client_id: str):
            # Track requests per client
            if client_id not in request_counts:
                request_counts[client_id] = []

            request_counts[client_id].append(time.time())

            # Simple rate limit: 10 requests per second
            recent_requests = [
                t for t in request_counts[client_id]
                if t > time.time() - 1
            ]

            if len(recent_requests) > 10:
                return {"error": "Rate limit exceeded"}, 429

            return {"status": "ok", "requests": len(recent_requests)}

        async with TestClient(app) as client:
            # Simulate multiple clients
            async def client_load(client_id: str, aggressive: bool = False):
                """Simulate client making requests."""
                success_count = 0
                rate_limited_count = 0

                request_delay = 0.05 if not aggressive else 0.01

                for _ in range(20):
                    response = await client.get(f"/rate-limited?client_id={client_id}")

                    if response.status_code == 200:
                        success_count += 1
                    elif response.status_code == 429:
                        rate_limited_count += 1

                    await asyncio.sleep(request_delay)

                return success_count, rate_limited_count

            # Run different client types
            results = await asyncio.gather(
                client_load("normal_1", False),
                client_load("normal_2", False),
                client_load("aggressive_1", True),
                client_load("aggressive_2", True),
            )

            # Normal clients should mostly succeed
            assert results[0][0] > 15  # Most requests succeed
            assert results[1][0] > 15

            # Aggressive clients should be rate limited
            assert results[2][1] > 0  # Some rate limiting
            assert results[3][1] > 0

    async def test_graceful_degradation(self):
        """Test graceful degradation under overload."""
        app = Zenith()

        processing_queue = []
        max_queue_size = 10

        @app.post("/process")
        async def process_request(data: dict):
            # Check queue size
            if len(processing_queue) >= max_queue_size:
                # Return degraded response
                return {
                    "status": "degraded",
                    "message": "System overloaded, try again later"
                }, 503

            # Add to queue
            processing_queue.append(data)

            try:
                # Simulate processing
                await asyncio.sleep(0.1)

                # Process data
                result = {"processed": True, "items": len(data)}
                return result
            finally:
                # Remove from queue
                if data in processing_queue:
                    processing_queue.remove(data)

        async with TestClient(app) as client:
            # Create overload
            async def make_requests(count: int):
                """Make many concurrent requests."""
                responses = []
                tasks = []

                for i in range(count):
                    data = {"id": i, "values": list(range(10))}
                    tasks.append(client.post("/process", json=data))

                responses = await asyncio.gather(*tasks)
                return responses

            # Send more requests than queue can handle
            responses = await make_requests(20)

            # Count response types
            success_count = sum(1 for r in responses if r.status_code == 200)
            degraded_count = sum(1 for r in responses if r.status_code == 503)

            print(f"\nGraceful Degradation:")
            print(f"  Success: {success_count}")
            print(f"  Degraded: {degraded_count}")

            # Should have both successes and degraded responses
            assert success_count > 0
            assert degraded_count > 0
            assert success_count + degraded_count == 20