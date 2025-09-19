"""
Database migrations system with Alembic integration.

Provides automatic Alembic configuration, migration generation,
and database version management for Zenith applications.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from zenith.db import Database


class MigrationManager:
    """
    Manages database migrations using Alembic.

    Handles automatic Alembic configuration, migration generation,
    and version management with async SQLAlchemy support.
    """

    def __init__(
        self,
        database: Database,
        migrations_dir: str = "migrations",
        script_location: str | None = None,
    ):
        """
        Initialize migration manager.

        Args:
            database: Database instance
            migrations_dir: Directory for migration files
            script_location: Custom script location (optional)
        """
        self.database = database
        self.migrations_dir = Path(migrations_dir)
        self.script_location = script_location or str(self.migrations_dir)
        self.logger = logging.getLogger("zenith.migrations")

        # Ensure migrations directory exists
        self.migrations_dir.mkdir(exist_ok=True)

        # Create Alembic configuration
        self.alembic_cfg = self._create_alembic_config()

    def _create_alembic_config(self) -> Config:
        """Create Alembic configuration."""
        # Create alembic.ini content
        alembic_ini_content = f"""
# Alembic configuration for Zenith application

[alembic]
# Path to migration scripts
script_location = {self.script_location}

# Template used to generate migration files
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(slug)s

# Timezone to use when rendering the date
# within the migration file as well as the filename.
timezone =

# Max length of characters to apply to the
# "slug" field
truncate_slug_length = 40

# Set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
revision_environment = false

# Set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
sourceless = false

# Version location specification
version_locations = %(here)s/versions

# The output encoding used when revision files
# are written from script.py.mako
output_encoding = utf-8

# Database URL (will be set programmatically)
sqlalchemy.url =

[post_write_hooks]
# Hooks for code formatters
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = --line-length 88 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

        # Write alembic.ini if it doesn't exist
        alembic_ini_path = self.migrations_dir / "alembic.ini"
        if not alembic_ini_path.exists():
            alembic_ini_path.write_text(alembic_ini_content.strip())

        # Create Alembic config
        config = Config(str(alembic_ini_path))
        config.set_main_option("script_location", self.script_location)
        config.set_main_option("sqlalchemy.url", self.database.url)

        return config

    def init_migrations(self) -> None:
        """Initialize the migrations directory with Alembic."""
        try:
            command.init(self.alembic_cfg, self.script_location)
            self.logger.info(f"Initialized migrations in {self.migrations_dir}")
        except Exception as e:
            if "already exists" in str(e).lower():
                self.logger.info(
                    f"Migrations already initialized in {self.migrations_dir}"
                )
            else:
                raise

        # Update env.py to work with async SQLAlchemy
        self._update_env_py()

    def _update_env_py(self) -> None:
        """Update env.py to support async SQLAlchemy."""
        env_py_path = self.migrations_dir / "env.py"

        if not env_py_path.exists():
            return

        env_py_content = '''"""Alembic environment for Zenith async database."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import your models here for autogeneration
# from your_app.models import Base

# Load Zenith base if available
try:
    from zenith.db import Base
    target_metadata = Base.metadata
except ImportError:
    # Fallback if no models imported yet
    target_metadata = None

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

        env_py_path.write_text(env_py_content)
        self.logger.info("Updated env.py for async SQLAlchemy")

    def create_migration(self, message: str, autogenerate: bool = True) -> str | None:
        """
        Create a new migration.

        Args:
            message: Migration message/description
            autogenerate: Whether to auto-generate from model changes

        Returns:
            Migration revision ID if successful
        """
        try:
            if autogenerate:
                revision = command.revision(
                    self.alembic_cfg, message=message, autogenerate=True
                )
            else:
                revision = command.revision(self.alembic_cfg, message=message)

            self.logger.info(f"Created migration: {message}")
            return revision.revision if revision else None

        except Exception as e:
            self.logger.error(f"Failed to create migration: {e}")
            return None

    def upgrade(self, revision: str = "head") -> bool:
        """
        Upgrade database to a specific revision.

        Args:
            revision: Target revision ("head" for latest)

        Returns:
            True if successful
        """
        try:
            command.upgrade(self.alembic_cfg, revision)
            self.logger.info(f"Upgraded database to {revision}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upgrade database: {e}")
            return False

    def downgrade(self, revision: str) -> bool:
        """
        Downgrade database to a specific revision.

        Args:
            revision: Target revision

        Returns:
            True if successful
        """
        try:
            command.downgrade(self.alembic_cfg, revision)
            self.logger.info(f"Downgraded database to {revision}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to downgrade database: {e}")
            return False

    def current_revision(self) -> str | None:
        """Get current database revision."""
        try:
            # This is a bit tricky with async engines, need to use sync approach
            ScriptDirectory.from_config(self.alembic_cfg)

            def get_current(connection):
                context = MigrationContext.configure(connection)
                return context.get_current_revision()

            # We'll need to create a sync engine for this check
            from sqlalchemy import create_engine

            sync_url = self.database.url.replace("+asyncpg", "").replace(
                "+aiomysql", ""
            )
            sync_engine = create_engine(sync_url)

            with sync_engine.connect() as connection:
                current = get_current(connection)

            sync_engine.dispose()
            return current

        except Exception as e:
            self.logger.error(f"Failed to get current revision: {e}")
            return None

    def migration_history(self) -> list[dict]:
        """Get migration history."""
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []

            for revision in script.walk_revisions():
                revisions.append(
                    {
                        "revision": revision.revision,
                        "message": revision.doc,
                        "down_revision": revision.down_revision,
                    }
                )

            return revisions

        except Exception as e:
            self.logger.error(f"Failed to get migration history: {e}")
            return []

    def status(self) -> dict:
        """Get migration status."""
        current = self.current_revision()
        history = self.migration_history()

        return {
            "current_revision": current,
            "total_migrations": len(history),
            "pending_migrations": len([r for r in history if r["revision"] != current]),
        }


# CLI integration functions
def setup_migrations_cli(app) -> None:
    """Add migration commands to the Zenith CLI."""
    import click

    @app.cli.group()
    def db():
        """Database migration commands."""
        pass

    @db.command()
    def init():
        """Initialize migrations directory."""
        # This would need access to the database instance
        # Implementation depends on how the CLI accesses the app
        click.echo("Initializing migrations...")

    @db.command()
    @click.argument("message")
    @click.option(
        "--autogenerate/--no-autogenerate",
        default=True,
        help="Automatically detect model changes",
    )
    def revision(message, autogenerate):
        """Create a new migration revision."""
        click.echo(f"Creating migration: {message}")

    @db.command()
    @click.argument("revision", default="head")
    def upgrade(revision):
        """Upgrade database to revision (default: head)."""
        click.echo(f"Upgrading to {revision}")

    @db.command()
    @click.argument("revision")
    def downgrade(revision):
        """Downgrade database to revision."""
        click.echo(f"Downgrading to {revision}")

    @db.command()
    def current():
        """Show current database revision."""
        click.echo("Current revision: ...")

    @db.command()
    def history():
        """Show migration history."""
        click.echo("Migration history:")


# Helper functions for integration
def create_migration_manager(
    database_url: str, migrations_dir: str = "migrations"
) -> MigrationManager:
    """Create a migration manager with database URL."""
    database = Database(database_url)
    return MigrationManager(database, migrations_dir)


def auto_create_migrations_table(engine: AsyncEngine) -> None:
    """Ensure Alembic version table exists."""

    async def _create_table():
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                )
            """)
            )

    import asyncio

    asyncio.run(_create_table())


__all__ = [
    "MigrationManager",
    "auto_create_migrations_table",
    "create_migration_manager",
    "setup_migrations_cli",
]
