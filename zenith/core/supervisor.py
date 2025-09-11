"""
Supervisor system for fault tolerance and process management.

Inspired by Erlang/Elixir supervision trees, provides automatic
restart of failed services with configurable strategies.
"""

import asyncio
import contextlib
import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class RestartStrategy(Enum):
    """Restart strategies for supervised processes."""

    NONE = "none"  # Never restart
    PERMANENT = "permanent"  # Always restart
    TRANSIENT = "transient"  # Restart only if abnormal exit
    TEMPORARY = "temporary"  # Restart only during startup


class RestartPolicy(Enum):
    """Restart policies for supervisor behavior."""

    ONE_FOR_ONE = "one_for_one"  # Restart only failed child
    ONE_FOR_ALL = "one_for_all"  # Restart all children
    REST_FOR_ONE = "rest_for_one"  # Restart failed + started after it


@dataclass
class SupervisorSpec:
    """Configuration for supervisor behavior."""

    max_restarts: int = 5  # Max restarts in time period
    max_seconds: int = 60  # Time period for restart counting
    restart_policy: RestartPolicy = RestartPolicy.ONE_FOR_ONE
    restart_strategy: RestartStrategy = RestartStrategy.PERMANENT


@dataclass
class ChildSpec:
    """Specification for supervised child process."""

    id: str
    start_func: Callable
    restart_strategy: RestartStrategy = RestartStrategy.PERMANENT
    args: tuple = ()
    kwargs: dict | None = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class SupervisedTask:
    """Wrapper for supervised async tasks."""

    def __init__(self, spec: ChildSpec, supervisor: "Supervisor"):
        self.spec = spec
        self.supervisor = supervisor
        self.task: asyncio.Task | None = None
        self.restart_count = 0
        self.last_restart = 0.0
        self.logger = logging.getLogger(f"zenith.supervisor.{spec.id}")

    async def start(self) -> None:
        """Start the supervised task."""
        if self.task and not self.task.done():
            return

        self.logger.info(f"Starting supervised task: {self.spec.id}")

        try:
            coro = self.spec.start_func(*self.spec.args, **self.spec.kwargs)
            self.task = asyncio.create_task(coro)
            self.task.add_done_callback(self._on_task_done)
        except Exception as e:
            self.logger.error(f"Failed to start task {self.spec.id}: {e}")
            await self.supervisor._handle_child_failure(self, e)

    def _on_task_done(self, task: asyncio.Task) -> None:
        """Handle task completion."""
        if task.cancelled():
            self.logger.info(f"Task {self.spec.id} was cancelled")
            return

        exception = task.exception()
        if exception:
            self.logger.error(f"Task {self.spec.id} failed: {exception}")
            asyncio.create_task(self.supervisor._handle_child_failure(self, exception))
        else:
            self.logger.info(f"Task {self.spec.id} completed normally")
            if self.spec.restart_strategy == RestartStrategy.PERMANENT:
                asyncio.create_task(self.supervisor._restart_child(self))

    async def stop(self) -> None:
        """Stop the supervised task."""
        if self.task and not self.task.done():
            self.logger.info(f"Stopping supervised task: {self.spec.id}")
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.task is not None and not self.task.done()


class Supervisor:
    """Process supervisor with fault tolerance."""

    def __init__(self, spec: SupervisorSpec = None):
        self.spec = spec or SupervisorSpec()
        self.children: dict[str, SupervisedTask] = {}
        self.restart_times: list[float] = []
        self.logger = logging.getLogger("zenith.supervisor")
        self._shutdown = False

    def add_child(self, spec: ChildSpec) -> None:
        """Add a child process to supervision."""
        if spec.id in self.children:
            raise ValueError(f"Child {spec.id} already exists")

        self.children[spec.id] = SupervisedTask(spec, self)
        self.logger.info(f"Added child to supervision: {spec.id}")

    async def start_tree(self) -> None:
        """Start the supervision tree."""
        self.logger.info("Starting supervision tree")
        self._shutdown = False

        for child in self.children.values():
            await child.start()

    async def stop_tree(self) -> None:
        """Stop the supervision tree."""
        self.logger.info("Stopping supervision tree")
        self._shutdown = True

        # Stop all children
        for child in self.children.values():
            await child.stop()

    async def _handle_child_failure(
        self, child: SupervisedTask, exception: BaseException
    ) -> None:
        """Handle child process failure."""
        if self._shutdown:
            return

        self.logger.error(f"Child {child.spec.id} failed: {exception}")
        self.logger.debug(traceback.format_exc())

        # Check restart strategy
        should_restart = self._should_restart(child, exception)
        if not should_restart:
            self.logger.info(
                f"Not restarting child {child.spec.id} due to restart strategy"
            )
            return

        # Check restart limits
        current_time = asyncio.get_event_loop().time()
        if not self._check_restart_limits(current_time):
            self.logger.error("Restart limit exceeded, shutting down supervisor")
            await self._shutdown_supervisor()
            return

        # Apply restart policy
        await self._apply_restart_policy(child)

    def _should_restart(self, child: SupervisedTask, exception: Exception) -> bool:
        """Determine if child should be restarted based on strategy."""
        strategy = child.spec.restart_strategy

        match strategy:
            case RestartStrategy.NONE:
                return False
            case RestartStrategy.PERMANENT:
                return True
            case RestartStrategy.TRANSIENT:
                # Restart only on abnormal exit (exceptions)
                return exception is not None
            case RestartStrategy.TEMPORARY:
                # Only restart during initial startup
                return child.restart_count == 0
            case _:
                return False

    def _check_restart_limits(self, current_time: float) -> bool:
        """Check if restart limits are exceeded."""
        # Remove old restart times
        cutoff = current_time - self.spec.max_seconds
        self.restart_times = [t for t in self.restart_times if t > cutoff]

        # Check if we're under the limit
        if len(self.restart_times) >= self.spec.max_restarts:
            return False

        # Record this restart
        self.restart_times.append(current_time)
        return True

    async def _apply_restart_policy(self, failed_child: SupervisedTask) -> None:
        """Apply restart policy when child fails."""
        policy = self.spec.restart_policy

        match policy:
            case RestartPolicy.ONE_FOR_ONE:
                await self._restart_child(failed_child)
            case RestartPolicy.ONE_FOR_ALL:
                await self._restart_all_children()
            case RestartPolicy.REST_FOR_ONE:
                await self._restart_child_and_rest(failed_child)

    async def _restart_child(self, child: SupervisedTask) -> None:
        """Restart a specific child."""
        if self._shutdown:
            return

        await child.stop()
        await asyncio.sleep(0.1)  # Brief delay before restart

        child.restart_count += 1
        child.last_restart = asyncio.get_event_loop().time()

        await child.start()

    async def _restart_all_children(self) -> None:
        """Restart all children (one_for_all policy)."""
        self.logger.info("Restarting all children due to one_for_all policy")

        # Stop all children
        for child in self.children.values():
            await child.stop()

        await asyncio.sleep(0.1)

        # Start all children
        for child in self.children.values():
            child.restart_count += 1
            child.last_restart = asyncio.get_event_loop().time()
            await child.start()

    async def _restart_child_and_rest(self, failed_child: SupervisedTask) -> None:
        """Restart failed child and those started after it."""
        # For simplicity, restart all for now
        # In a real implementation, we'd track start order
        await self._restart_all_children()

    async def _shutdown_supervisor(self) -> None:
        """Shutdown supervisor due to excessive failures."""
        self.logger.critical("Supervisor shutting down due to excessive failures")
        await self.stop_tree()

        # Could trigger application shutdown here
        # raise SystemExit("Supervisor failed")
