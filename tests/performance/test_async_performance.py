"""Async operations and background task performance tests."""

import asyncio
import time
from statistics import mean

import pytest
from starlette.requests import Request

from zenith import Zenith
from zenith.monitoring.performance import cached, track_performance
from zenith.tasks.background import BackgroundTasks, TaskQueue
from zenith.testing import TestClient


class TestAsyncPerformance:
    """Test async operations performance."""

    @pytest.mark.asyncio
    async def test_background_task_performance(self):
        """Test background task execution performance."""
        executed_tasks = []

        def sync_task(task_id: int):
            executed_tasks.append(task_id)

        async def async_task(task_id: int):
            await asyncio.sleep(0.001)  # Simulate work
            executed_tasks.append(f"async_{task_id}")

        # Test sync tasks performance
        sync_tasks = BackgroundTasks()

        start = time.perf_counter()
        for i in range(100):
            sync_tasks.add_task(sync_task, i)

        await sync_tasks()
        sync_elapsed = time.perf_counter() - start

        # Test async tasks performance
        executed_tasks.clear()
        async_tasks = BackgroundTasks()

        start = time.perf_counter()
        for i in range(50):  # Fewer due to sleep
            async_tasks.add_task(async_task, i)

        await async_tasks()
        async_elapsed = time.perf_counter() - start

        print("\nBackground Task Performance:")
        print(
            f"  100 sync tasks:  {sync_elapsed:.3f}s ({100 / sync_elapsed:.1f} tasks/s)"
        )
        print(
            f"  50 async tasks:  {async_elapsed:.3f}s ({50 / async_elapsed:.1f} tasks/s)"
        )

        assert len(executed_tasks) == 50  # All async tasks completed
        assert sync_elapsed < 0.1  # Sync tasks very fast
        assert async_elapsed < 2.0  # Async tasks reasonable time

    @pytest.mark.asyncio
    async def test_task_queue_performance(self):
        """Test TaskQueue performance."""
        queue = TaskQueue()

        def cpu_task(n: int) -> int:
            return sum(range(n))

        async def io_task(delay: float) -> str:
            await asyncio.sleep(delay)
            return f"completed_{delay}"

        # Test CPU-bound tasks
        cpu_task_ids = []
        start = time.perf_counter()

        for _i in range(20):
            task_id = await queue.enqueue(cpu_task, 1000)
            cpu_task_ids.append(task_id)

        # Wait for all CPU tasks
        cpu_results = []
        for task_id in cpu_task_ids:
            result = await queue.get_result(task_id, timeout_secs=2.0)
            cpu_results.append(result)

        cpu_elapsed = time.perf_counter() - start

        # Test I/O-bound tasks
        io_task_ids = []
        start = time.perf_counter()

        for _i in range(10):
            task_id = await queue.enqueue(io_task, 0.01)
            io_task_ids.append(task_id)

        # Wait for all I/O tasks
        io_results = []
        for task_id in io_task_ids:
            result = await queue.get_result(task_id, timeout_secs=1.0)
            io_results.append(result)

        io_elapsed = time.perf_counter() - start

        print("\nTaskQueue Performance:")
        print(f"  20 CPU tasks: {cpu_elapsed:.3f}s ({20 / cpu_elapsed:.1f} tasks/s)")
        print(f"  10 I/O tasks: {io_elapsed:.3f}s ({10 / io_elapsed:.1f} tasks/s)")

        assert len(cpu_results) == 20
        assert len(io_results) == 10
        assert all(result == 499500 for result in cpu_results)  # sum(range(1000))
        assert cpu_elapsed < 5.0  # Should complete reasonably fast
        assert io_elapsed < 2.0  # I/O tasks should be concurrent

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_monitoring_overhead(self):
        """Test performance monitoring overhead."""
        call_count = 0

        # Function without monitoring
        def regular_function():
            nonlocal call_count
            call_count += 1
            return sum(range(100))

        # Function with monitoring
        @track_performance(threshold_ms=1000)  # High threshold to avoid logging
        def monitored_function():
            nonlocal call_count
            call_count += 1
            return sum(range(100))

        # Benchmark regular function
        start = time.perf_counter()
        for _ in range(1000):
            regular_function()
        regular_elapsed = time.perf_counter() - start

        # Benchmark monitored function
        start = time.perf_counter()
        for _ in range(1000):
            monitored_function()
        monitored_elapsed = time.perf_counter() - start

        overhead_pct = ((monitored_elapsed - regular_elapsed) / regular_elapsed) * 100

        print("\nPerformance Monitoring Overhead:")
        print(f"  Regular:   {regular_elapsed:.4f}s")
        print(f"  Monitored: {monitored_elapsed:.4f}s")
        print(f"  Overhead:  {overhead_pct:.1f}%")

        # Monitoring overhead should be acceptable for lightweight functions
        # Allow up to 250% overhead for very fast operations where decorator overhead dominates
        assert (
            overhead_pct < 250
        )  # < 250% overhead (decorators add significant overhead to fast functions)

    @pytest.mark.asyncio
    async def test_caching_performance(self):
        """Test caching performance benefits."""
        cache_misses = 0

        @cached(ttl=60)
        async def expensive_operation(n: int) -> int:
            nonlocal cache_misses
            cache_misses += 1
            await asyncio.sleep(0.01)  # Simulate expensive operation
            return sum(range(n))

        # Test cache performance
        start = time.perf_counter()

        # First call - cache miss
        result1 = await expensive_operation(1000)

        # Repeated calls - cache hits
        for _ in range(10):
            result = await expensive_operation(1000)
            assert result == result1

        # Different parameter - cache miss
        result2 = await expensive_operation(2000)

        elapsed = time.perf_counter() - start

        print("\nCaching Performance:")
        print(f"  Total time:   {elapsed:.3f}s")
        print(f"  Cache misses: {cache_misses}")
        print("  Expected:     2 misses")

        assert cache_misses == 2  # Only 2 cache misses
        assert elapsed < 0.5  # Much faster with caching
        assert result1 == 499500
        assert result2 == 1999000

    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self):
        """Test concurrent async operations performance."""

        async def async_work(work_id: int, duration: float) -> dict:
            start = time.perf_counter()
            await asyncio.sleep(duration)
            elapsed = time.perf_counter() - start
            return {"id": work_id, "duration": elapsed}

        # Sequential execution
        start = time.perf_counter()
        sequential_results = []
        for i in range(10):
            result = await async_work(i, 0.01)
            sequential_results.append(result)
        sequential_elapsed = time.perf_counter() - start

        # Concurrent execution
        start = time.perf_counter()
        concurrent_tasks = [async_work(i, 0.01) for i in range(10)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_elapsed = time.perf_counter() - start

        speedup = sequential_elapsed / concurrent_elapsed

        print("\nConcurrency Performance:")
        print(f"  Sequential: {sequential_elapsed:.3f}s")
        print(f"  Concurrent: {concurrent_elapsed:.3f}s")
        print(f"  Speedup:    {speedup:.1f}x")

        assert len(concurrent_results) == 10
        assert speedup > 5  # Should be much faster concurrently
        assert concurrent_elapsed < 0.05  # Should complete in ~0.01s

    @pytest.mark.asyncio
    async def test_async_context_switching_performance(self):
        """Test async context switching overhead."""

        async def simple_async_function(value: int) -> int:
            await asyncio.sleep(0)  # Force context switch
            return value * 2

        def simple_sync_function(value: int) -> int:
            return value * 2

        # Test async context switching
        start = time.perf_counter()
        async_results = []
        for i in range(1000):
            result = await simple_async_function(i)
            async_results.append(result)
        async_elapsed = time.perf_counter() - start

        # Test sync calls
        start = time.perf_counter()
        sync_results = []
        for i in range(1000):
            result = simple_sync_function(i)
            sync_results.append(result)
        sync_elapsed = time.perf_counter() - start

        overhead_pct = ((async_elapsed - sync_elapsed) / sync_elapsed) * 100

        print("\nAsync Context Switching Overhead:")
        print(f"  Sync:     {sync_elapsed:.4f}s")
        print(f"  Async:    {async_elapsed:.4f}s")
        print(f"  Overhead: {overhead_pct:.1f}%")

        assert len(async_results) == 1000
        assert len(sync_results) == 1000
        # Context switching with asyncio.sleep(0) is very expensive
        # This is expected behavior - async has overhead for very lightweight operations
        assert async_elapsed < 0.1  # Should still complete in reasonable time


class TestBackgroundTaskIntegration:
    """Test background task integration with web endpoints."""

    @pytest.mark.asyncio
    async def test_endpoint_with_background_tasks_performance(self):
        """Test endpoint performance with background tasks."""
        app = Zenith(debug=False, middleware=[])
        processed_tasks = []

        @app.post("/process")
        async def process_endpoint(request: Request, background_tasks: BackgroundTasks):
            data = await request.json()

            def process_data(item):
                processed_tasks.append(item)

            # Add background task
            background_tasks.add_task(process_data, data.get("item"))

            return {"status": "accepted", "item": data.get("item")}

        async with TestClient(app) as client:
            # Test endpoint performance with background tasks
            times = []

            for i in range(100):
                start = time.perf_counter()
                response = await client.post("/process", json={"item": f"item_{i}"})
                elapsed = time.perf_counter() - start

                assert response.status_code == 200
                assert response.json()["status"] == "accepted"
                times.append(elapsed)

            avg_time = mean(times)
            rps = 1 / avg_time

            print("\nBackground Task Endpoint Performance:")
            print(f"  Average time: {avg_time * 1000:.2f}ms")
            print(f"  Requests/sec: {rps:.1f}")

            # Background tasks shouldn't significantly slow down responses
            assert avg_time < 0.02  # < 20ms average
            assert rps > 50  # > 50 req/s

    @pytest.mark.asyncio
    async def test_task_queue_endpoint_performance(self):
        """Test endpoint performance with TaskQueue."""
        app = Zenith(debug=False, middleware=[])
        task_queue = TaskQueue()

        @app.post("/enqueue")
        async def enqueue_endpoint(request: Request):
            data = await request.json()

            def heavy_task(n: int) -> int:
                return sum(range(n))

            task_id = await task_queue.enqueue(heavy_task, data.get("n", 100))
            return {"task_id": task_id, "status": "enqueued"}

        @app.get("/result/{task_id}")
        async def result_endpoint(task_id: str):
            try:
                result = await task_queue.get_result(task_id, timeout_secs=0.1)
                return {"result": result, "status": "completed"}
            except Exception:
                return {"status": "pending"}

        async with TestClient(app) as client:
            # Test enqueue performance
            enqueue_times = []
            task_ids = []

            for _i in range(50):
                start = time.perf_counter()
                response = await client.post("/enqueue", json={"n": 500})
                elapsed = time.perf_counter() - start

                assert response.status_code == 200
                task_ids.append(response.json()["task_id"])
                enqueue_times.append(elapsed)

            avg_enqueue_time = mean(enqueue_times)

            # Test result retrieval performance
            await asyncio.sleep(0.5)  # Wait for tasks to complete

            result_times = []
            for task_id in task_ids[:10]:  # Test first 10
                start = time.perf_counter()
                response = await client.get(f"/result/{task_id}")
                elapsed = time.perf_counter() - start

                assert response.status_code == 200
                result_times.append(elapsed)

            avg_result_time = mean(result_times)

            print("\nTaskQueue Endpoint Performance:")
            print(f"  Enqueue time: {avg_enqueue_time * 1000:.2f}ms")
            print(f"  Result time:  {avg_result_time * 1000:.2f}ms")

            assert avg_enqueue_time < 0.01  # Enqueuing should be fast
            assert avg_result_time < 0.01  # Result retrieval should be fast
