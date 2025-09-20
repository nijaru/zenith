"""
Background task support for Zenith applications.

Provides simple async background task execution using Starlette's BackgroundTasks.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from starlette.background import BackgroundTasks as StarletteBackgroundTasks


class BackgroundTasks:
    """
    Background task manager for Zenith.

    Allows adding tasks to run after the response is sent.

    Usage:
        from zenith import BackgroundTasks

        @app.post("/send-email")
        async def send_email_endpoint(
            email: str,
            background: BackgroundTasks = BackgroundTasks()
        ):
            # Add task to run after response
            background.add_task(send_email_async, email)
            return {"message": "Email queued"}
    """

    def __init__(self):
        """Initialize background tasks."""
        self._tasks = StarletteBackgroundTasks()

    def add_task(self, func: Callable[..., Any] | Coroutine, *args, **kwargs) -> None:
        """
        Add a task to run in the background.

        Args:
            func: Function or coroutine to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        import logging

        def safe_task():
            """Wrap task with exception handling for isolation."""
            try:
                return func(*args, **kwargs)
            except Exception:
                logger = logging.getLogger("zenith.background")
                logger.exception(f"Error in background task {func.__name__}")

        async def safe_async_task():
            """Wrap async task with exception handling for isolation."""
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger = logging.getLogger("zenith.background")
                logger.exception(f"Error in async background task {func.__name__}")

        # Check if function is async
        import asyncio

        if asyncio.iscoroutinefunction(func):
            self._tasks.add_task(safe_async_task)
        else:
            self._tasks.add_task(safe_task)

    async def __call__(self) -> None:
        """Execute all background tasks."""
        # Individual tasks are already wrapped with exception handling
        # so this should not raise exceptions
        await self._tasks()


def background_task(func: Callable) -> Callable:
    """
    Decorator to mark a function as a background task.

    This is mainly for documentation - the function can still
    be called normally or added to BackgroundTasks.

    Usage:
        @background_task
        async def send_welcome_email(user_id: int):
            # Send email logic here
            pass
    """
    func._is_background_task = True
    return func


class TaskQueue:
    """
    Simple in-memory task queue for development.

    For production, use Celery, RQ, or similar.

    Usage:
        queue = TaskQueue()

        # Add task
        task_id = await queue.enqueue(send_email, user_id=123)

        # Check status
        status = await queue.get_status(task_id)
    """

    def __init__(self):
        """Initialize task queue."""

        self.tasks = {}
        self.results = {}
        self._running = set()

    async def enqueue(self, func: Callable, *args, **kwargs) -> str:
        """
        Add a task to the queue.

        Returns:
            Task ID for tracking
        """
        import asyncio
        from uuid import uuid4

        task_id = str(uuid4())

        async def run_task():
            self._running.add(task_id)
            try:
                result = (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )
                self.results[task_id] = {"status": "completed", "result": result}
            except Exception as e:
                self.results[task_id] = {"status": "failed", "error": str(e)}
            finally:
                self._running.discard(task_id)

        # Create task but don't await it
        task = asyncio.create_task(run_task())
        self.tasks[task_id] = task

        return task_id

    async def get_status(self, task_id: str) -> dict:
        """Get task status."""
        if task_id in self._running:
            return {"status": "running"}
        elif task_id in self.results:
            return self.results[task_id]
        elif task_id in self.tasks:
            return {"status": "pending"}
        else:
            return {"status": "not_found"}

    async def get_result(self, task_id: str, timeout_secs: float | None = None) -> Any:
        """
        Wait for task result.

        Args:
            task_id: Task ID
            timeout_secs: Maximum wait time in seconds

        Returns:
            Task result

        Raises:
            TimeoutError: If timeout exceeded
            Exception: If task failed
        """
        import asyncio

        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        if timeout_secs:
            await asyncio.wait_for(task, timeout=timeout_secs)
        else:
            await task

        result = self.results.get(task_id, {})
        if result.get("status") == "failed":
            raise Exception(result.get("error"))

        return result.get("result")
