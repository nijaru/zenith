"""Tests for background task functionality."""

import asyncio

import pytest

from zenith import Zenith
from zenith.tasks.background import BackgroundTasks, TaskQueue, background_task
from zenith.testing import TestClient


class TestBackgroundTasks:
    """Test background task execution."""

    @pytest.mark.asyncio
    async def test_background_task_execution(self):
        """Test basic background task execution."""
        executed = []

        def sync_task(name: str, value: int):
            executed.append((name, value))

        tasks = BackgroundTasks()
        tasks.add_task(sync_task, "test", 42)

        # Execute tasks
        await tasks()

        assert executed == [("test", 42)]

    @pytest.mark.asyncio
    async def test_async_background_task(self):
        """Test async background task execution."""
        executed = []

        async def async_task(name: str):
            await asyncio.sleep(0.01)
            executed.append(name)

        tasks = BackgroundTasks()
        tasks.add_task(async_task, "async_test")

        # Execute tasks
        await tasks()

        assert executed == ["async_test"]

    @pytest.mark.asyncio
    async def test_multiple_background_tasks(self):
        """Test multiple background tasks execution."""
        executed = []

        def task1():
            executed.append("task1")

        def task2():
            executed.append("task2")

        tasks = BackgroundTasks()
        tasks.add_task(task1)
        tasks.add_task(task2)

        await tasks()

        assert "task1" in executed
        assert "task2" in executed
        assert len(executed) == 2

    @pytest.mark.asyncio
    async def test_background_task_with_exception(self):
        """Test background task exception handling."""

        def failing_task():
            raise ValueError("Task failed")

        tasks = BackgroundTasks()
        tasks.add_task(failing_task)

        # Should not raise exception, but log it
        await tasks()  # Should complete without raising

    @pytest.mark.asyncio
    async def test_background_task_decorator(self):
        """Test background_task decorator."""
        executed = []

        @background_task
        def background_func(name: str):
            executed.append(name)

        # Function should be marked as background task
        assert hasattr(background_func, "_is_background_task")
        assert background_func._is_background_task is True

        # Can still be called normally
        background_func("decorated_test")
        assert executed == ["decorated_test"]

        # Can be added to BackgroundTasks
        tasks = BackgroundTasks()
        tasks.add_task(background_func, "task_test")
        await tasks()

        assert "task_test" in executed


class TestBackgroundTasksIntegration:
    """Test background tasks integration with Zenith app."""

    @pytest.mark.asyncio
    async def test_route_with_background_task(self):
        """Test route handler with background task."""
        executed = []

        app = Zenith(debug=True, middleware=[])

        @app.post("/with-background")
        async def create_with_background(background_tasks: BackgroundTasks):
            def send_email():
                executed.append("email_sent")

            background_tasks.add_task(send_email)
            return {"status": "created"}

        async with TestClient(app) as client:
            response = await client.post("/with-background", json={})

            assert response.status_code == 200
            assert response.json() == {"status": "created"}

            # Background task should be executed after response
            # Our fix now properly executes background tasks
            await asyncio.sleep(0.01)  # Give tasks time to execute
            assert len(executed) == 1  # Task should have executed
            assert executed[0] == "email_sent"

    @pytest.mark.asyncio
    async def test_background_task_dependency_injection(self):
        """Test BackgroundTasks as dependency injection."""
        app = Zenith(debug=True)

        @app.get("/test-bg")
        async def test_endpoint(background_tasks: BackgroundTasks):
            # Should receive BackgroundTasks instance
            assert isinstance(background_tasks, BackgroundTasks)
            return {"background_tasks": "injected"}

        async with TestClient(app) as client:
            response = await client.get("/test-bg")
            assert response.status_code == 200
            assert response.json() == {"background_tasks": "injected"}

    @pytest.mark.asyncio
    async def test_background_tasks_with_complex_data(self):
        """Test background tasks with complex data structures."""
        results = []

        def process_data(data: dict, items: list):
            results.append({"data": data, "count": len(items)})

        tasks = BackgroundTasks()
        test_data = {"id": 1, "name": "test"}
        test_items = [1, 2, 3, 4, 5]

        tasks.add_task(process_data, test_data, test_items)
        await tasks()

        expected = {"data": {"id": 1, "name": "test"}, "count": 5}
        assert results == [expected]

    @pytest.mark.asyncio
    async def test_background_task_error_isolation(self):
        """Test that background task errors don't affect other tasks."""
        executed = []

        def good_task(name: str):
            executed.append(name)

        def bad_task():
            raise Exception("This task fails")

        tasks = BackgroundTasks()
        tasks.add_task(good_task, "task1")
        tasks.add_task(bad_task)
        tasks.add_task(good_task, "task2")

        # All tasks should attempt to run despite one failing
        await tasks()

        assert "task1" in executed
        assert "task2" in executed
        assert len(executed) == 2


class TestTaskQueue:
    """Test TaskQueue functionality."""

    @pytest.mark.asyncio
    async def test_task_queue_enqueue(self):
        """Test task queue enqueue functionality."""
        queue = TaskQueue()
        executed = []

        def simple_task(name: str):
            executed.append(name)
            return f"completed: {name}"

        task_id = await queue.enqueue(simple_task, "test_task")

        # Should return task ID
        assert isinstance(task_id, str)
        assert len(task_id) > 0

        # Wait for task completion
        result = await queue.get_result(task_id, timeout_secs=1.0)
        assert result == "completed: test_task"
        assert executed == ["test_task"]

    @pytest.mark.asyncio
    async def test_task_queue_async_task(self):
        """Test task queue with async task."""
        queue = TaskQueue()
        executed = []

        async def async_task(name: str):
            await asyncio.sleep(0.01)
            executed.append(name)
            return f"async: {name}"

        task_id = await queue.enqueue(async_task, "async_test")
        result = await queue.get_result(task_id, timeout_secs=1.0)

        assert result == "async: async_test"
        assert executed == ["async_test"]

    @pytest.mark.asyncio
    async def test_task_queue_status(self):
        """Test task queue status checking."""
        queue = TaskQueue()

        async def slow_task():
            await asyncio.sleep(0.1)
            return "done"

        task_id = await queue.enqueue(slow_task)

        # Should be pending or running initially
        status = await queue.get_status(task_id)
        assert status["status"] in ["pending", "running"]

        # Wait for completion
        await queue.get_result(task_id, timeout_secs=1.0)

        # Should be completed
        status = await queue.get_status(task_id)
        assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_queue_error_handling(self):
        """Test task queue error handling."""
        queue = TaskQueue()

        def failing_task():
            raise ValueError("Task failed")

        task_id = await queue.enqueue(failing_task)

        # Should capture the error
        with pytest.raises(Exception):
            await queue.get_result(task_id, timeout_secs=1.0)

        status = await queue.get_status(task_id)
        assert status["status"] == "failed"
        assert "error" in status
