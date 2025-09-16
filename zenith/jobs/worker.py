"""
Job worker for executing background tasks.

Handles job processing, error handling, timeouts, and resource management.
"""

import asyncio
import logging
import signal
import traceback
from collections.abc import Callable

from zenith.jobs.queue import RedisJobQueue

logger = logging.getLogger("zenith.jobs.worker")


class Worker:
    """
    Background job worker.

    Features:
    - Async job execution
    - Timeout handling
    - Graceful shutdown
    - Error capture and retry logic
    - Resource cleanup
    """

    __slots__ = ("current_job", "jobs", "queue", "running")

    def __init__(self, queue: RedisJobQueue, jobs: dict[str, Callable]):
        """
        Initialize worker.

        Args:
            queue: Job queue instance
            jobs: Dictionary of registered job functions
        """
        self.queue = queue
        self.jobs = jobs
        self.running = False
        self.current_job = None

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    async def process_jobs(self) -> None:
        """
        Main job processing loop.

        Continuously polls for jobs and executes them until stopped.
        """
        self.running = True
        logger.info("Job worker started")

        while self.running:
            try:
                # Get next job (blocking with timeout)
                job_data = await self.queue.dequeue(timeout=5)
                if not job_data:
                    continue  # Timeout - check if we should keep running

                self.current_job = job_data
                await self._execute_job(job_data)

            except asyncio.CancelledError:
                logger.info("Job worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in job processing loop: {e}")
                # Continue processing other jobs

        logger.info("Job worker stopped")

    async def _execute_job(self, job_data: dict) -> None:
        """
        Execute a single job.

        Args:
            job_data: Job information from queue
        """
        job_id = job_data["id"]
        job_name = job_data["name"]

        logger.info(f"Executing job {job_name} (ID: {job_id})")

        try:
            # Get job function
            if job_name not in self.jobs:
                raise ValueError(f"Job function {job_name} not found")

            job_func = self.jobs[job_name]

            # Execute with timeout
            timeout = job_data.get("timeout", 300)

            result = await asyncio.wait_for(
                job_func(*job_data["args"], **job_data["kwargs"]), timeout=timeout
            )

            # Mark as completed
            await self.queue.complete_job(job_id, result)
            logger.info(f"Completed job {job_name} (ID: {job_id})")

        except TimeoutError:
            error = f"Job {job_name} timed out after {timeout}s"
            logger.error(error)
            await self.queue.fail_job(job_id, error)

        except Exception as e:
            error = f"Job {job_name} failed: {e!s}\
{traceback.format_exc()}"
            logger.error(error)
            await self.queue.fail_job(job_id, str(e))

        finally:
            self.current_job = None

    def stop(self) -> None:
        """Stop job processing."""
        self.running = False

        # If currently executing a job, let it finish gracefully
        if self.current_job:
            logger.info(
                f"Waiting for current job {self.current_job['id']} to complete..."
            )

    async def health_check(self) -> dict:
        """Get worker health information."""
        return {
            "running": self.running,
            "current_job": self.current_job["id"] if self.current_job else None,
            "registered_jobs": list(self.jobs.keys()),
        }
