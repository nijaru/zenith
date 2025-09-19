"""
Job scheduler for recurring and delayed tasks.

Provides cron-like scheduling functionality for background jobs.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TypeVar

from zenith.jobs.manager import get_job_manager

logger = logging.getLogger("zenith.jobs.scheduler")

F = TypeVar("F", bound=Callable[..., Awaitable])


class JobScheduler:
    """
    Job scheduler for recurring and delayed tasks.

    Features:
    - Cron-like scheduling syntax
    - One-time delayed execution
    - Recurring job management
    - Schedule persistence across restarts
    """

    def __init__(self, job_manager=None):
        """Initialize scheduler with optional job manager."""
        self.job_manager = job_manager or get_job_manager()
        self.schedules: dict[str, dict] = {}
        self.running = False

    def schedule(
        self,
        cron: str | None = None,
        every: timedelta | None = None,
        at: datetime | None = None,
        name: str | None = None,
    ):
        """
        Decorator to schedule a job for recurring or delayed execution.

        Args:
            cron: Cron expression (e.g., "0 9 * * *" for daily at 9am)
            every: Recurring interval (e.g., timedelta(hours=1))
            at: One-time execution datetime
            name: Schedule name (defaults to function name)

        Examples:
            @schedule(cron="0 9 * * *")  # Daily at 9am
            async def daily_report():
                pass

            @schedule(every=timedelta(hours=1))  # Every hour
            async def hourly_cleanup():
                pass

            @schedule(at=datetime(2024, 1, 1, 0, 0))  # One-time
            async def new_year_task():
                pass
        """

        def decorator(func: F) -> F:
            schedule_name = name or func.__name__

            # Validate scheduling parameters
            if sum(x is not None for x in [cron, every, at]) != 1:
                raise ValueError(
                    "Exactly one of 'cron', 'every', or 'at' must be specified"
                )

            # Store schedule configuration
            schedule_config = {
                "function": func,
                "cron": cron,
                "every": every,
                "at": at,
                "name": schedule_name,
                "next_run": None,
                "last_run": None,
            }

            # Calculate next run time
            if at:
                schedule_config["next_run"] = at
            elif every:
                schedule_config["next_run"] = datetime.utcnow() + every
            elif cron:
                schedule_config["next_run"] = self._parse_cron_next(cron)

            self.schedules[schedule_name] = schedule_config
            logger.info(
                f"Scheduled job {schedule_name} for {schedule_config['next_run']}"
            )

            return func

        return decorator

    async def run_scheduler(self) -> None:
        """
        Run the scheduler loop.

        Continuously checks for scheduled jobs that are ready to run.
        """
        self.running = True
        logger.info("Job scheduler started")

        while self.running:
            try:
                now = datetime.utcnow()

                # Check each scheduled job
                for schedule_name, config in self.schedules.items():
                    next_run = config["next_run"]

                    if next_run and now >= next_run:
                        await self._execute_scheduled_job(schedule_name, config)

                # Sleep for a bit before checking again
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

        logger.info("Job scheduler stopped")

    async def _execute_scheduled_job(self, schedule_name: str, config: dict) -> None:
        """Execute a scheduled job and update its next run time."""
        try:
            func = config["function"]

            # Queue the job for execution
            job_id = await self.job_manager.enqueue(
                func.__name__,
                # No args/kwargs for scheduled jobs by default
                # Could be extended to support parameters
            )

            # Update last run time
            config["last_run"] = datetime.utcnow()

            # Calculate next run time
            if config["every"]:
                # Recurring job
                config["next_run"] = datetime.utcnow() + config["every"]
            elif config["cron"]:
                # Cron job
                config["next_run"] = self._parse_cron_next(config["cron"])
            else:
                # One-time job
                config["next_run"] = None

            logger.info(
                f"Executed scheduled job {schedule_name} (ID: {job_id}), "
                f"next run: {config['next_run']}"
            )

        except Exception as e:
            logger.error(f"Error executing scheduled job {schedule_name}: {e}")

    def _parse_cron_next(self, cron: str) -> datetime:
        """
        Parse cron expression and return next execution time.

        This is a simplified cron parser. For production use,
        consider using a library like 'croniter'.
        """
        # This is a basic implementation
        # For full cron support, use: pip install croniter

        parts = cron.split()
        if len(parts) != 5:
            raise ValueError(
                "Cron expression must have 5 parts: minute hour day month weekday"
            )

        # For now, just support simple cases
        minute, hour, day, month, weekday = parts

        now = datetime.utcnow()
        next_run = now.replace(second=0, microsecond=0)

        # Simple daily schedule (e.g., "0 9 * * *")
        if (
            minute.isdigit()
            and hour.isdigit()
            and day == "*"
            and month == "*"
            and weekday == "*"
        ):
            target_hour = int(hour)
            target_minute = int(minute)

            next_run = next_run.replace(hour=target_hour, minute=target_minute)

            # If time has passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)

            return next_run

        # For more complex cron expressions, recommend using croniter
        raise NotImplementedError(
            f"Cron expression '{cron}' not supported by simple parser. "
            "Install 'croniter' for full cron support."
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False

    def get_schedules(self) -> dict:
        """Get all configured schedules."""
        return {
            name: {
                "cron": config["cron"],
                "every": str(config["every"]) if config["every"] else None,
                "at": config["at"].isoformat() if config["at"] else None,
                "next_run": config["next_run"].isoformat()
                if config["next_run"]
                else None,
                "last_run": config["last_run"].isoformat()
                if config["last_run"]
                else None,
            }
            for name, config in self.schedules.items()
        }

    async def trigger_schedule(self, schedule_name: str) -> str | None:
        """Manually trigger a scheduled job."""
        if schedule_name not in self.schedules:
            return None

        config = self.schedules[schedule_name]
        func = config["function"]

        job_id = await self.job_manager.enqueue(func.__name__)
        logger.info(f"Manually triggered scheduled job {schedule_name} (ID: {job_id})")

        return job_id


# Global scheduler instance
_scheduler = None


def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler


def schedule(
    cron: str | None = None,
    every: timedelta | None = None,
    at: datetime | None = None,
    name: str | None = None,
):
    """
    Decorator to schedule a job with the global scheduler.

    Examples:
        from zenith.jobs import schedule
        from datetime import timedelta

        @schedule(every=timedelta(hours=1))
        async def hourly_cleanup():
            # Cleanup logic here
            pass
    """
    return get_scheduler().schedule(cron, every, at, name)
