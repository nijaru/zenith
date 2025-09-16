"""
Job queue implementation with Redis backend.

Provides persistent job storage, status tracking, and job scheduling.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

import msgspec
import redis.asyncio as redis

logger = logging.getLogger("zenith.jobs.queue")


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class RedisJobQueue:
    """
    Redis-backed job queue.

    Features:
    - Persistent job storage
    - Status tracking and updates
    - Job scheduling and delays
    - Retry logic with exponential backoff
    - Dead letter queue for failed jobs
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize job queue.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis = redis.from_url(redis_url)

        # Redis key prefixes
        self.job_prefix = "zenith:job:"
        self.queue_key = "zenith:queue:pending"
        self.running_key = "zenith:queue:running"
        self.failed_key = "zenith:queue:failed"
        self.scheduled_key = "zenith:queue:scheduled"

    async def enqueue(
        self,
        job_id: str,
        job_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
        scheduled_at: datetime | None = None,
        max_retries: int = 3,
        retry_delay_secs: int = 60,
        timeout_secs: int = 300,
    ) -> None:
        """
        Add a job to the queue.

        Args:
            job_id: Unique job identifier
            job_name: Name of the job function
            args: Positional arguments
            kwargs: Keyword arguments
            scheduled_at: When to run the job (None = immediately)
            max_retries: Maximum retry attempts
            retry_delay_secs: Delay between retries (seconds)
            timeout_secs: Job execution timeout (seconds)
        """
        kwargs = kwargs or {}

        job_data = {
            "id": job_id,
            "name": job_name,
            "args": args,
            "kwargs": kwargs,
            "status": JobStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            "started_at": None,
            "completed_at": None,
            "max_retries": max_retries,
            "retry_delay": retry_delay_secs,
            "timeout": timeout_secs,
            "retry_count": 0,
            "error": None,
            "result": None,
        }

        # Store job data
        job_key = f"{self.job_prefix}{job_id}"
        await self.redis.set(job_key, msgspec.json.encode(job_data).decode())

        # Add to appropriate queue
        if scheduled_at:
            # Scheduled job - add to sorted set with timestamp
            timestamp = scheduled_at.timestamp()
            await self.redis.zadd(self.scheduled_key, {job_id: timestamp})
        else:
            # Immediate job - add to pending queue
            await self.redis.lpush(self.queue_key, job_id)

        logger.debug(f"Enqueued job {job_id} ({job_name})")

    async def dequeue(self, timeout_secs: int = 10) -> dict | None:
        """
        Get the next available job.

        Args:
            timeout_secs: Blocking timeout in seconds

        Returns:
            Job data or None if timeout
        """
        # First, move any scheduled jobs that are ready
        await self._move_scheduled_jobs()

        # Get job from pending queue (blocking)
        result = await self.redis.brpop(self.queue_key, timeout=timeout_secs)
        if not result:
            return None

        _, job_id = result
        job_id = job_id.decode() if isinstance(job_id, bytes) else job_id

        # Get job data
        job_data = await self._get_job_data(job_id)
        if not job_data:
            logger.warning(f"Job {job_id} not found in storage")
            return None

        # Move to running queue
        await self.redis.lpush(self.running_key, job_id)

        # Update status
        job_data["status"] = JobStatus.RUNNING
        job_data["started_at"] = datetime.utcnow().isoformat()
        await self._update_job_data(job_id, job_data)

        return job_data

    async def complete_job(self, job_id: str, result: Any = None) -> None:
        """Mark a job as completed."""
        job_data = await self._get_job_data(job_id)
        if not job_data:
            return

        job_data["status"] = JobStatus.COMPLETED
        job_data["completed_at"] = datetime.utcnow().isoformat()
        job_data["result"] = result

        await self._update_job_data(job_id, job_data)
        await self.redis.lrem(self.running_key, 1, job_id)

        logger.debug(f"Completed job {job_id}")

    async def fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed and handle retries."""
        job_data = await self._get_job_data(job_id)
        if not job_data:
            return

        job_data["retry_count"] += 1
        job_data["error"] = error

        # Check if we should retry
        if job_data["retry_count"] < job_data["max_retries"]:
            # Schedule retry with exponential backoff
            delay = job_data["retry_delay"] * (2 ** (job_data["retry_count"] - 1))
            retry_at = datetime.utcnow().timestamp() + delay

            job_data["status"] = JobStatus.RETRYING
            job_data["scheduled_at"] = datetime.fromtimestamp(retry_at).isoformat()

            await self._update_job_data(job_id, job_data)
            await self.redis.lrem(self.running_key, 1, job_id)
            await self.redis.zadd(self.scheduled_key, {job_id: retry_at})

            logger.info(
                f"Retrying job {job_id} in {delay}s (attempt {job_data['retry_count']})"
            )
        else:
            # Max retries exceeded - move to failed queue
            job_data["status"] = JobStatus.FAILED
            job_data["completed_at"] = datetime.utcnow().isoformat()

            await self._update_job_data(job_id, job_data)
            await self.redis.lrem(self.running_key, 1, job_id)
            await self.redis.lpush(self.failed_key, job_id)

            logger.error(
                f"Job {job_id} failed after {job_data['retry_count']} retries: {error}"
            )

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job_data = await self._get_job_data(job_id)
        if not job_data or job_data["status"] not in [
            JobStatus.PENDING,
            JobStatus.RETRYING,
        ]:
            return False

        job_data["status"] = JobStatus.CANCELLED
        job_data["completed_at"] = datetime.utcnow().isoformat()

        await self._update_job_data(job_id, job_data)

        # Remove from queues
        await self.redis.lrem(self.queue_key, 1, job_id)
        await self.redis.zrem(self.scheduled_key, job_id)

        logger.info(f"Cancelled job {job_id}")
        return True

    async def retry(self, job_id: str) -> bool:
        """Retry a failed job."""
        job_data = await self._get_job_data(job_id)
        if not job_data or job_data["status"] != JobStatus.FAILED:
            return False

        # Reset job state
        job_data["status"] = JobStatus.PENDING
        job_data["retry_count"] = 0
        job_data["error"] = None
        job_data["started_at"] = None
        job_data["completed_at"] = None

        await self._update_job_data(job_id, job_data)

        # Move from failed to pending
        await self.redis.lrem(self.failed_key, 1, job_id)
        await self.redis.lpush(self.queue_key, job_id)

        logger.info(f"Retrying failed job {job_id}")
        return True

    async def get_status(self, job_id: str) -> JobStatus | None:
        """Get job status."""
        job_data = await self._get_job_data(job_id)
        return JobStatus(job_data["status"]) if job_data else None

    async def get_failed(self, limit: int = 100) -> list[dict]:
        """Get failed jobs."""
        job_ids = await self.redis.lrange(self.failed_key, 0, limit - 1)
        jobs = []

        for job_id in job_ids:
            job_id = job_id.decode() if isinstance(job_id, bytes) else job_id
            job_data = await self._get_job_data(job_id)
            if job_data:
                jobs.append(job_data)

        return jobs

    async def clear_failed(self) -> int:
        """Clear all failed jobs."""
        count = await self.redis.llen(self.failed_key)
        if count > 0:
            await self.redis.delete(self.failed_key)

            # Also delete job data
            job_ids = await self.redis.lrange(self.failed_key, 0, -1)
            for job_id in job_ids:
                job_id = job_id.decode() if isinstance(job_id, bytes) else job_id
                await self.redis.delete(f"{self.job_prefix}{job_id}")

        return count

    async def health_check(self) -> dict:
        """Get queue health information."""
        return {
            "pending": await self.redis.llen(self.queue_key),
            "running": await self.redis.llen(self.running_key),
            "failed": await self.redis.llen(self.failed_key),
            "scheduled": await self.redis.zcard(self.scheduled_key),
        }

    async def _get_job_data(self, job_id: str) -> dict | None:
        """Get job data from Redis."""
        job_key = f"{self.job_prefix}{job_id}"
        data = await self.redis.get(job_key)
        if data:
            return msgspec.json.decode(data.encode())
        return None

    async def _update_job_data(self, job_id: str, job_data: dict) -> None:
        """Update job data in Redis."""
        job_key = f"{self.job_prefix}{job_id}"
        await self.redis.set(job_key, msgspec.json.encode(job_data).decode())

    async def _move_scheduled_jobs(self) -> None:
        """Move scheduled jobs that are ready to the pending queue."""
        now = datetime.utcnow().timestamp()

        # Get jobs scheduled to run now or earlier
        ready_jobs = await self.redis.zrangebyscore(self.scheduled_key, 0, now)

        for job_id in ready_jobs:
            job_id = job_id.decode() if isinstance(job_id, bytes) else job_id

            # Move to pending queue
            await self.redis.zrem(self.scheduled_key, job_id)
            await self.redis.lpush(self.queue_key, job_id)

            # Update job status
            job_data = await self._get_job_data(job_id)
            if job_data:
                job_data["status"] = JobStatus.PENDING
                job_data["scheduled_at"] = None
                await self._update_job_data(job_id, job_data)
