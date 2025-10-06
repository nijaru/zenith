"""
Job manager for background task processing.

Provides a simple decorator-based API for defining background jobs
and queueing them for execution.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any, TypeVar
from uuid import uuid4

from zenith.jobs.queue import JobStatus, RedisJobQueue

logger = logging.getLogger("zenith.jobs.manager")

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class JobManager:
    """
    Central manager for background jobs.

    Features:
    - Decorator-based job definition
    - Async job execution
    - Retry logic with exponential backoff
    - Job status tracking
    - Redis-backed persistence
    """

    __slots__ = ("jobs", "queue", "redis_url", "running")

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize job manager.

        Args:
            redis_url: Redis connection URL for job persistence
        """
        self.redis_url = redis_url
        self.queue = RedisJobQueue(redis_url)
        self.jobs: dict[str, Callable] = {}
        self.running = False

    def job(
        self,
        name: str | None = None,
        max_retries: int = 3,
        retry_delay_secs: int = 60,
        timeout_secs: int = 300,
    ) -> Callable[[F], F]:
        """
        Decorator to register a background job.

        Args:
            name: Job name (defaults to function name)
            max_retries: Maximum retry attempts
            retry_delay_secs: Delay between retries in seconds
            timeout_secs: Job execution timeout in seconds

        Example:
            @job_manager.job(name="send_email", max_retries=5)
            async def send_email(to: str, subject: str, body: str):
                # Send email logic here
                pass

            # Queue the job
            await send_email.delay(
                to="user@example.com",
                subject="Welcome!",
                body="Welcome to our service"
            )
        """

        def decorator(func: F) -> F:
            job_name = name or func.__name__

            # Store job configuration
            func._job_config = {
                "name": job_name,
                "max_retries": max_retries,
                "retry_delay": retry_delay_secs,
                "timeout": timeout_secs,
            }

            # Register the job
            self.jobs[job_name] = func

            # Add delay method for queueing
            async def delay(*args, **kwargs) -> str:
                """Queue this job for background execution."""
                job_id = str(uuid4())
                await self.queue.enqueue(
                    job_id=job_id,
                    job_name=job_name,
                    args=args,
                    kwargs=kwargs,
                    max_retries=max_retries,
                    retry_delay=retry_delay_secs,
                    timeout=timeout_secs,
                )
                logger.info(f"Queued job {job_name} with ID {job_id}")
                return job_id

            func.delay = delay
            return func

        return decorator

    async def enqueue(
        self, job_name: str, *args, delay: timedelta | None = None, **kwargs
    ) -> str:
        """
        Manually enqueue a job.

        Args:
            job_name: Name of the registered job
            *args: Positional arguments for the job
            delay: Delay before job execution
            **kwargs: Keyword arguments for the job

        Returns:
            job_id: Unique identifier for the job
        """
        if job_name not in self.jobs:
            raise ValueError(f"Job {job_name} not registered")

        job_id = str(uuid4())
        job_func = self.jobs[job_name]
        config = getattr(job_func, "_job_config", {})

        scheduled_at = None
        if delay:
            scheduled_at = datetime.utcnow() + delay

        await self.queue.enqueue(
            job_id=job_id,
            job_name=job_name,
            args=args,
            kwargs=kwargs,
            scheduled_at=scheduled_at,
            max_retries=config.get("max_retries", 3),
            retry_delay=config.get("retry_delay", 60),
            timeout=config.get("timeout", 300),
        )

        logger.info(f"Queued job {job_name} with ID {job_id}")
        return job_id

    async def get_job_status(self, job_id: str) -> JobStatus | None:
        """Get the status of a job."""
        return await self.queue.get_status(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        return await self.queue.cancel(job_id)

    async def retry_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        return await self.queue.retry(job_id)

    async def get_failed_jobs(self, limit: int = 100) -> list[dict]:
        """Get list of failed jobs."""
        return await self.queue.get_failed(limit)

    async def clear_failed_jobs(self) -> int:
        """Clear all failed jobs."""
        return await self.queue.clear_failed()

    async def start_worker(self, concurrency: int = 1) -> None:
        """
        Start processing jobs.

        Args:
            concurrency: Number of concurrent job processors
        """
        from zenith.jobs.worker import Worker

        self.running = True
        worker = Worker(self.queue, self.jobs)

        logger.info(f"Starting job worker with concurrency {concurrency}")

        # Start multiple worker coroutines
        tasks = [asyncio.create_task(worker.process_jobs()) for _ in range(concurrency)]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Job worker stopped")
        finally:
            self.running = False

    def stop_worker(self):
        """Stop job processing."""
        self.running = False

    async def health_check(self) -> dict:
        """Get job system health information."""
        return await self.queue.health_check()


# Global job manager instance
_job_manager = None


def get_job_manager() -> JobManager:
    """Get the global job manager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def job(
    name: str | None = None,
    max_retries: int = 3,
    retry_delay_secs: int = 60,
    timeout_secs: int = 300,
) -> Callable[[F], F]:
    """
    Decorator to register a background job with the global manager.

    This is a convenience function that uses the global job manager.

    Example:
        from zenith.jobs import job

        @job(name="process_image", max_retries=5)
        async def process_image(image_path: str):
            # Image processing logic
            pass

        # Queue the job
        await process_image.delay("/path/to/image.jpg")
    """
    return get_job_manager().job(name, max_retries, retry_delay_secs, timeout_secs)
