"""
Core application kernel for Zenith framework.

Manages application lifecycle, supervision tree, dependency injection,
and coordinates all framework components.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import Any

from zenith.core.config import Config
from zenith.core.container import DIContainer
from zenith.core.service import EventBus, ServiceRegistry
from zenith.core.supervisor import (
    ChildSpec,
    RestartStrategy,
    Supervisor,
    SupervisorSpec,
)
from zenith.db import Database


class Application:
    """Main application class that coordinates all framework components."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.config.validate()

        # Core components
        self.container = DIContainer()
        self.supervisor = Supervisor(SupervisorSpec())
        self.contexts = ServiceRegistry(self.container)
        self.events = EventBus()

        # Database setup (convert database_url if it uses postgresql:// to async version)
        db_url = self.config.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        elif db_url.startswith("sqlite://"):
            db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

        self.database = Database(url=db_url, echo=self.config.debug, pool_size=20)

        # Register database as default for ZenithModel
        from zenith.core.container import set_default_database

        set_default_database(self.database)

        # State
        self._running = False
        self._startup_complete = False
        self._startup_hooks = []
        self._shutdown_hooks = []

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger("zenith.application")

        # Register core services
        self._register_core_services()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _register_core_services(self) -> None:
        """Register core services in the DI container."""
        self.container.register("config", self.config)
        self.container.register("events", self.events)
        self.container.register("contexts", self.contexts)
        self.container.register("supervisor", self.supervisor)
        self.container.register(Database, self.database)

        # Register self for services that need the application
        self.container.register("application", self)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        try:
            # Only works on Unix-like systems
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except (AttributeError, ValueError):
            # Windows or other platforms that don't support these signals
            pass

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(self.shutdown())

    def register_service(
        self, service_type: type, implementation: Any = None, singleton: bool = True
    ) -> None:
        """Register a service with the application."""
        self.container.register(service_type, implementation, singleton)

    def register_context(self, name: str, context_class: type) -> None:
        """Register a business context."""
        self.contexts.register(name, context_class)

    def register_supervised_service(
        self,
        service_id: str,
        start_func,
        restart_strategy: RestartStrategy = RestartStrategy.PERMANENT,
        *args,
        **kwargs,
    ) -> None:
        """Register a service to be managed by the supervisor."""
        spec = ChildSpec(
            id=service_id,
            start_func=start_func,
            restart_strategy=restart_strategy,
            args=args,
            kwargs=kwargs,
        )
        self.supervisor.add_child(spec)

    def add_startup_hook(self, hook) -> None:
        """Register a function to be called during startup."""
        self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook) -> None:
        """Register a function to be called during shutdown."""
        self._shutdown_hooks.append(hook)

    async def startup(self) -> None:
        """Start the application and all its components."""
        if self._running:
            return

        self.logger.info("Starting Zenith application")

        try:
            # Start DI container
            await self.container.startup()

            # Start supervision tree
            await self.supervisor.start_tree()

            # Run startup hooks
            for hook in self._startup_hooks:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
                except Exception as e:
                    self.logger.error(f"Error in startup hook: {e}")

            # Mark as running
            self._running = True
            self._startup_complete = True

            self.logger.info("Application startup complete")

        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            await self.shutdown()
            raise

    async def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        if not self._running:
            return

        self.logger.info("Shutting down Zenith application")
        self._running = False

        try:
            # Run shutdown hooks
            for hook in reversed(self._shutdown_hooks):
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
                except Exception as e:
                    self.logger.error(f"Error in shutdown hook: {e}")

            # Shutdown contexts
            await self.contexts.shutdown_all()

            # Stop supervision tree
            await self.supervisor.stop_tree()

            # Close database connections
            await self.database.close()

            # Shutdown DI container
            await self.container.shutdown()

            self.logger.info("Application shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def run_until_complete(self) -> None:
        """Start the application and run until shutdown."""
        await self.startup()

        try:
            # Keep running until shutdown
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()

    @asynccontextmanager
    async def lifespan(self):
        """Context manager for application lifecycle."""
        await self.startup()
        try:
            yield self
        finally:
            await self.shutdown()

    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running

    def is_startup_complete(self) -> bool:
        """Check if application startup is complete."""
        return self._startup_complete

    async def get_context(self, name: str):
        """Get a business context by name."""
        return await self.contexts.get(name)

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"Application(config={self.config}, status={status})"
