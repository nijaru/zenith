"""
Services and mounting mixin for Zenith applications.

Contains methods for managing services, contexts, databases, and mounting.
"""

from typing import Any

from zenith.core.routing import Router
from zenith.core.service import Service


class ServicesMixin:
    """Mixin for service registration and mounting methods."""

    def register_context(self, name: str, context_class: type[Service]) -> None:
        """Register a business service."""
        self.app.register_context(name, context_class)

    def register_service(self, service_type: type, implementation: Any = None) -> None:
        """Register a service for dependency injection."""
        self.app.register_service(service_type, implementation)

    def setup_database(
        self, database_url: str, migrations_dir: str = "migrations"
    ) -> None:
        """
        Set up database connection and migrations.

        Args:
            database_url: Database connection URL
            migrations_dir: Directory for migration files
        """
        from zenith.core.container import set_default_database
        from zenith.db import Database, MigrationManager

        # Set up database connection
        self.database = Database(database_url)

        # Set as default database for models to use
        set_default_database(self.database)

        # Set up migrations
        self.migration_manager = MigrationManager(self.database, migrations_dir)

        # Register database as a service for dependency injection
        self.register_service(Database, self.database)

        # Add database health check
        from zenith.monitoring.health import health_manager

        health_manager.add_simple_check(
            "database", self.database.health_check, timeout=5.0, critical=True
        )

    def mount(self, path: str, app, name: str | None = None) -> None:
        """Mount a sub-application or static files at the given path."""
        from starlette.routing import Mount

        # Create a mount route
        mount_route = Mount(path, app, name=name)

        # Add directly to the app routes
        if not hasattr(self, "_mount_routes"):
            self._mount_routes = []
        self._mount_routes.append(mount_route)

        # If app is already built, add to the underlying Starlette app
        if hasattr(self, "app") and hasattr(self.app, "_app"):
            self.app._app.routes.append(mount_route)

    def mount_static(self, path: str, directory: str, **config) -> None:
        """
        Mount static file serving at the given path.

        Args:
            path: URL path prefix for static files (e.g., "/static")
            directory: Directory containing static files
            **config: Additional configuration for static files
        """
        from zenith.web.static import create_static_route

        static_mount = create_static_route(path, directory, **config)
        # Store for later mounting when app is built
        if not hasattr(self, "_static_mounts"):
            self._static_mounts = []
        self._static_mounts.append(static_mount)

    def spa(
        self,
        framework_or_directory: str | None = None,
        path: str = "/",
        index: str = "index.html",
        exclude: list[str] | None = None,
        **config,
    ) -> None:
        """
        Serve a Single Page Application with intelligent defaults.

        Args:
            framework_or_directory: Framework ("react", "vue", "solidjs") or directory path
            path: URL path to mount SPA (default: "/")
            index: Index file to serve (default: "index.html")
            exclude: Path patterns to exclude from SPA fallback (e.g., ["/api/*"])
            **config: Additional configuration (max_age, etc.)

        Examples:
            app.spa()                                    # Auto-detect dist/ or build/
            app.spa("dist")                             # Serve from dist/
            app.spa("react")                            # React (uses build/)
            app.spa("dist", index="app.html")           # Custom index file
            app.spa("dist", exclude=["/api/*"])         # Exclude API routes
        """
        from pathlib import Path

        from zenith.web.static import serve_spa_files

        # Framework-specific defaults
        framework_defaults = {
            "react": "build",
            "vue": "dist",
            "solidjs": "dist",
            "svelte": "build",
            "angular": "dist",
        }

        if framework_or_directory is None:
            # Auto-detect common directories
            for candidate in ["dist", "build", "public"]:
                if Path(candidate).exists() and any(Path(candidate).iterdir()):
                    directory = candidate
                    break
            else:
                directory = "dist"  # Fallback
        elif framework_or_directory in framework_defaults:
            # Framework-specific
            directory = framework_defaults[framework_or_directory]
        else:
            # Treat as directory path
            directory = framework_or_directory

        spa_app = serve_spa_files(
            directory=directory, index=index, exclude=exclude, **config
        )
        self.mount(path, spa_app)

    def static(
        self, path: str = "/static", directory: str = "static", **config
    ) -> None:
        """
        Serve static files at the given path.

        Args:
            path: URL path prefix (e.g., "/static", "/assets")
            directory: Local directory containing static files
            **config: Additional configuration (max_age, etc.)

        Examples:
            app.static()                    # /static/ -> ./static/
            app.static("/assets", "public") # /assets/ -> ./public/
        """
        self.mount_static(path, directory, **config)

    def include_router(self, router: Router, prefix: str = "") -> None:
        """Include a router with optional prefix."""
        if prefix:
            router.prefix = prefix + router.prefix

        # Set app reference for dependency injection
        router._app = self.app

        self.routers.append(router)
