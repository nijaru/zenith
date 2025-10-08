"""
Background task management for Zenith applications.

Provides both simple background tasks and a comprehensive job queue system
for handling long-running operations with automatic retry, error handling,
and lifecycle management.
"""

import asyncio
import contextlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Job(BaseModel):
    """Background job representation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    status: JobStatus = JobStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    progress: float = 0.0
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    result: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobBackend(ABC):
    """Abstract base for job storage backends."""

    @abstractmethod
    async def store_job(self, job: Job) -> None:
        """Store a job."""
        pass

    @abstractmethod
    async def get_job(self, job_id: UUID) -> Job | None:
        """Retrieve a job by ID."""
        pass

    @abstractmethod
    async def update_job(self, job: Job) -> None:
        """Update job status/progress."""
        pass

    @abstractmethod
    async def list_jobs(self, status: JobStatus | None = None) -> list[Job]:
        """List jobs, optionally filtered by status."""
        pass


class MemoryJobBackend(JobBackend):
    """In-memory job storage backend."""

    def __init__(self):
        self._jobs: dict[UUID, Job] = {}

    async def store_job(self, job: Job) -> None:
        self._jobs[job.id] = job

    async def get_job(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    async def update_job(self, job: Job) -> None:
        if job.id in self._jobs:
            self._jobs[job.id] = job

    async def list_jobs(self, status: JobStatus | None = None) -> list[Job]:
        jobs = list(self._jobs.values())
        if status:
            jobs = [job for job in jobs if job.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)


class BackgroundTaskManager:
    """
    Enhanced background task manager addressing yt-text production needs.

    Provides automatic cleanup, error handling, and monitoring for async tasks.
    """

    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self._tasks: dict[UUID, asyncio.Task] = {}
        self._task_metadata: dict[UUID, dict[str, Any]] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def start(self):
        """Start the task manager with automatic cleanup."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Background task manager started (max_concurrent={self.max_concurrent_tasks})"
        )

    async def stop(self):
        """Stop the task manager and cleanup all tasks."""
        logger.info("Stopping background task manager...")

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Cancel all running tasks
        for task_id, task in self._tasks.items():
            if not task.done():
                logger.info(f"Cancelling task {task_id}")
                task.cancel()

        # Wait for all tasks to complete/cancel
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._tasks.clear()
        self._task_metadata.clear()
        logger.info("Background task manager stopped")

    async def add_task(
        self,
        func: Callable,
        *args,
        name: str | None = None,
        timeout: float | None = None,
        **kwargs,
    ) -> UUID:
        """
        Add a background task with automatic lifecycle management.

        Args:
            func: Async function to execute
            *args: Function arguments
            name: Optional task name for identification
            timeout: Optional timeout in seconds
            **kwargs: Function keyword arguments

        Returns:
            Task UUID for tracking
        """
        if len(self._tasks) >= self.max_concurrent_tasks:
            raise RuntimeError(
                f"Maximum concurrent tasks ({self.max_concurrent_tasks}) reached"
            )

        task_id = uuid4()
        task_name = name or f"{func.__name__}_{task_id.hex[:8]}"

        # Wrap function with error handling and metadata
        async def wrapped_task():
            start_time = time.time()
            try:
                logger.info(f"Starting background task: {task_name}")

                if timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=timeout
                    )
                else:
                    result = await func(*args, **kwargs)

                duration = time.time() - start_time
                logger.info(f"Background task completed: {task_name} ({duration:.2f}s)")
                return result

            except asyncio.CancelledError:
                logger.info(f"Background task cancelled: {task_name}")
                raise
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Background task failed: {task_name} ({duration:.2f}s) - {e!s}"
                )
                raise

        task = asyncio.create_task(wrapped_task())
        self._tasks[task_id] = task
        self._task_metadata[task_id] = {
            "name": task_name,
            "created_at": time.time(),
            "timeout": timeout,
        }

        logger.info(f"Added background task: {task_name} ({task_id})")
        return task_id

    async def get_task_status(self, task_id: UUID) -> dict[str, Any]:
        """Get status information for a task."""
        if task_id not in self._tasks:
            return {"status": "not_found"}

        task = self._tasks[task_id]
        metadata = self._task_metadata.get(task_id, {})

        status = {
            "id": str(task_id),
            "name": metadata.get("name", "unnamed"),
            "created_at": metadata.get("created_at"),
            "timeout": metadata.get("timeout"),
        }

        if task.done():
            if task.cancelled():
                status["status"] = "cancelled"
            elif task.exception():
                status["status"] = "failed"
                status["error"] = str(task.exception())
            else:
                status["status"] = "completed"
                try:
                    status["result"] = task.result()
                except Exception as e:
                    status["error"] = str(e)
        else:
            status["status"] = "running"

        return status

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a running task."""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        if not task.done():
            task.cancel()
            logger.info(f"Cancelled task {task_id}")
            return True
        return False

    async def list_tasks(self) -> list[dict[str, Any]]:
        """List all tasks with their status."""
        tasks = []
        for task_id in self._tasks:
            status = await self.get_task_status(task_id)
            tasks.append(status)
        return tasks

    async def _cleanup_loop(self):
        """Periodic cleanup of completed tasks."""
        while True:
            try:
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                await self._cleanup_completed_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_completed_tasks(self):
        """Remove completed tasks from tracking."""
        completed_tasks = []
        for task_id, task in self._tasks.items():
            if task.done():
                completed_tasks.append(task_id)

        for task_id in completed_tasks:
            del self._tasks[task_id]
            del self._task_metadata[task_id]

        if completed_tasks:
            logger.debug(f"Cleaned up {len(completed_tasks)} completed tasks")


class JobQueue:
    """
    Comprehensive job queue system for complex background processing.

    Addresses yt-text needs for:
    - Job persistence and monitoring
    - Automatic retry with exponential backoff
    - Progress tracking
    - Error recovery
    """

    def __init__(
        self,
        backend: JobBackend | None = None,
        max_workers: int = 4,
        default_max_retries: int = 3,
    ):
        self.backend = backend or MemoryJobBackend()
        self.max_workers = max_workers
        self.default_max_retries = default_max_retries
        self._workers: list[asyncio.Task] = []
        self._job_handlers: dict[str, Callable] = {}
        self._shutdown_event = asyncio.Event()
        self._queue: asyncio.Queue = asyncio.Queue()

    def register_handler(self, job_name: str, handler: Callable):
        """Register a job handler function."""
        self._job_handlers[job_name] = handler
        logger.info(f"Registered job handler: {job_name}")

    async def enqueue_job(
        self,
        job_name: str,
        data: Any = None,
        max_retries: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """
        Enqueue a new job for processing.

        Args:
            job_name: Name of the job (must have registered handler)
            data: Job data/payload
            max_retries: Maximum retry attempts (defaults to queue default)
            metadata: Additional job metadata

        Returns:
            Job UUID for tracking
        """
        if job_name not in self._job_handlers:
            raise ValueError(f"No handler registered for job: {job_name}")

        job = Job(
            name=job_name,
            max_retries=max_retries or self.default_max_retries,
            metadata=metadata or {},
        )

        # Store job payload in metadata (simple approach for now)
        job.metadata["data"] = data

        await self.backend.store_job(job)
        await self._queue.put(job.id)

        logger.info(f"Enqueued job: {job_name} ({job.id})")
        return job.id

    async def get_job_status(self, job_id: UUID) -> Job | None:
        """Get job status and details."""
        return await self.backend.get_job(job_id)

    async def start_workers(self):
        """Start background worker tasks."""
        logger.info(f"Starting {self.max_workers} job workers")

        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

    async def stop_workers(self):
        """Stop all workers and wait for completion."""
        logger.info("Stopping job workers...")
        self._shutdown_event.set()

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("Job workers stopped")

    async def _worker_loop(self, worker_id: int):
        """Main worker loop for processing jobs."""
        logger.info(f"Worker {worker_id} started")

        try:
            while not self._shutdown_event.is_set():
                try:
                    # Wait for job with timeout to check shutdown periodically
                    job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    await self._process_job(worker_id, job_id)
                except TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")

        except asyncio.CancelledError:
            pass

        logger.info(f"Worker {worker_id} stopped")

    async def _process_job(self, worker_id: int, job_id: UUID):
        """Process a single job with error handling and retries."""
        job = await self.backend.get_job(job_id)
        if not job:
            logger.error(f"Worker {worker_id}: Job {job_id} not found")
            return

        handler = self._job_handlers.get(job.name)
        if not handler:
            logger.error(f"Worker {worker_id}: No handler for job {job.name}")
            job.status = JobStatus.FAILED
            job.error = f"No handler registered for job type: {job.name}"
            await self.backend.update_job(job)
            return

        logger.info(f"Worker {worker_id}: Processing job {job.name} ({job.id})")

        # Update job status to running
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        await self.backend.update_job(job)

        try:
            # Execute job handler with data from metadata
            data = job.metadata.get("data")
            result = await handler(data, job)

            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.progress = 1.0
            job.result = result
            await self.backend.update_job(job)

            logger.info(f"Worker {worker_id}: Job {job.name} completed ({job.id})")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Worker {worker_id}: Job {job.name} failed: {error_msg}")

            # Handle retries
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                job.error = f"Attempt {job.retry_count}: {error_msg}"
                await self.backend.update_job(job)

                # Exponential backoff: 2^retry_count seconds
                delay = 2**job.retry_count
                logger.info(
                    f"Worker {worker_id}: Retrying job {job.name} in {delay}s (attempt {job.retry_count + 1})"
                )

                # Re-queue job after delay
                asyncio.create_task(self._requeue_job_after_delay(job.id, delay))
            else:
                # Max retries exceeded
                job.status = JobStatus.FAILED
                job.completed_at = time.time()
                job.error = f"Max retries exceeded: {error_msg}"
                await self.backend.update_job(job)

                logger.error(
                    f"Worker {worker_id}: Job {job.name} failed permanently ({job.id})"
                )

    async def _requeue_job_after_delay(self, job_id: UUID, delay: float):
        """Re-queue a job after retry delay."""
        await asyncio.sleep(delay)
        await self._queue.put(job_id)


# Decorator for easy background task creation
def background_task(
    task_manager: BackgroundTaskManager | None = None,
    name: str | None = None,
    timeout: float | None = None,
):
    """
    Decorator to mark functions as background tasks.

    Example:
        @background_task(name="process_video", timeout=300)
        async def process_transcription(video_url: str, job: Job):
            # Long-running transcription work
            pass
    """

    def decorator(func: Callable):
        func._is_background_task = True
        func._task_name = name or func.__name__
        func._task_timeout = timeout

        async def wrapper(*args, **kwargs):
            if task_manager:
                return await task_manager.add_task(
                    func, *args, name=name, timeout=timeout, **kwargs
                )
            else:
                # Execute directly if no task manager provided
                return await func(*args, **kwargs)

        wrapper._original_func = func
        return wrapper

    return decorator


# Export main classes and functions
__all__ = [
    "BackgroundTaskManager",
    "Job",
    "JobBackend",
    "JobQueue",
    "JobStatus",
    "MemoryJobBackend",
    "background_task",
]
