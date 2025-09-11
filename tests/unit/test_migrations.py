"""Tests for database migrations functionality."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from zenith.db.migrations import MigrationManager, create_migration_manager


class TestMigrationManager:
    """Test MigrationManager functionality."""

    @pytest.fixture
    def mock_database(self):
        """Mock database instance."""
        database = MagicMock()
        database.url = "postgresql+asyncpg://user:pass@localhost/test"
        return database

    @pytest.fixture
    def temp_migrations_dir(self, tmp_path):
        """Create temporary migrations directory."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()
        return migrations_dir

    def test_migration_manager_init(self, mock_database, temp_migrations_dir):
        """Test MigrationManager initialization."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        assert manager.database == mock_database
        assert manager.migrations_dir == temp_migrations_dir
        assert temp_migrations_dir.exists()
        
        # Should create alembic config
        assert manager.alembic_cfg is not None
        assert manager.alembic_cfg.get_main_option("sqlalchemy.url") == mock_database.url

    def test_alembic_config_creation(self, mock_database, temp_migrations_dir):
        """Test Alembic configuration creation."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        alembic_ini_path = temp_migrations_dir / "alembic.ini"
        assert alembic_ini_path.exists()
        
        ini_content = alembic_ini_path.read_text()
        assert "script_location" in ini_content
        assert "file_template" in ini_content
        assert "black" in ini_content  # Code formatter hook

    @patch('zenith.db.migrations.command')
    def test_init_migrations(self, mock_command, mock_database, temp_migrations_dir):
        """Test migrations initialization."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        manager.init_migrations()
        
        mock_command.init.assert_called_once_with(
            manager.alembic_cfg, 
            manager.script_location
        )

    @patch('zenith.db.migrations.command')
    def test_init_migrations_already_exists(self, mock_command, mock_database, temp_migrations_dir):
        """Test migrations init when already exists."""
        mock_command.init.side_effect = Exception("already exists")
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        # Should not raise exception
        manager.init_migrations()
        
        mock_command.init.assert_called_once()

    def test_env_py_update(self, mock_database, temp_migrations_dir):
        """Test env.py creation for async SQLAlchemy."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        # Create empty env.py
        env_py_path = temp_migrations_dir / "env.py"
        env_py_path.write_text("# placeholder")
        
        manager._update_env_py()
        
        env_py_content = env_py_path.read_text()
        assert "async def run_async_migrations" in env_py_content
        assert "create_async_engine" in env_py_content
        assert "from zenith.db import Base" in env_py_content

    @patch('zenith.db.migrations.command')
    def test_create_migration_autogenerate(self, mock_command, mock_database, temp_migrations_dir):
        """Test creating migration with autogenerate."""
        mock_revision = MagicMock()
        mock_revision.revision = "abc123"
        mock_command.revision.return_value = mock_revision
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        revision_id = manager.create_migration("Add user table", autogenerate=True)
        
        assert revision_id == "abc123"
        mock_command.revision.assert_called_once_with(
            manager.alembic_cfg,
            message="Add user table",
            autogenerate=True
        )

    @patch('zenith.db.migrations.command')
    def test_create_migration_manual(self, mock_command, mock_database, temp_migrations_dir):
        """Test creating manual migration."""
        mock_revision = MagicMock()
        mock_revision.revision = "def456"
        mock_command.revision.return_value = mock_revision
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        revision_id = manager.create_migration("Custom migration", autogenerate=False)
        
        assert revision_id == "def456"
        mock_command.revision.assert_called_once_with(
            manager.alembic_cfg,
            message="Custom migration"
        )

    @patch('zenith.db.migrations.command')
    def test_create_migration_error(self, mock_command, mock_database, temp_migrations_dir):
        """Test migration creation error handling."""
        mock_command.revision.side_effect = Exception("Migration failed")
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        revision_id = manager.create_migration("Failed migration")
        
        assert revision_id is None

    @patch('zenith.db.migrations.command')
    def test_upgrade_database(self, mock_command, mock_database, temp_migrations_dir):
        """Test database upgrade."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        result = manager.upgrade("head")
        
        assert result is True
        mock_command.upgrade.assert_called_once_with(manager.alembic_cfg, "head")

    @patch('zenith.db.migrations.command')
    def test_upgrade_database_error(self, mock_command, mock_database, temp_migrations_dir):
        """Test database upgrade error."""
        mock_command.upgrade.side_effect = Exception("Upgrade failed")
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        result = manager.upgrade("head")
        
        assert result is False

    @patch('zenith.db.migrations.command')
    def test_downgrade_database(self, mock_command, mock_database, temp_migrations_dir):
        """Test database downgrade."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        result = manager.downgrade("abc123")
        
        assert result is True
        mock_command.downgrade.assert_called_once_with(manager.alembic_cfg, "abc123")

    @patch('zenith.db.migrations.command')
    def test_downgrade_database_error(self, mock_command, mock_database, temp_migrations_dir):
        """Test database downgrade error."""
        mock_command.downgrade.side_effect = Exception("Downgrade failed")
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        result = manager.downgrade("abc123")
        
        assert result is False

    @patch('sqlalchemy.create_engine')
    @patch('zenith.db.migrations.ScriptDirectory')
    def test_current_revision(self, mock_script_dir, mock_create_engine, mock_database, temp_migrations_dir):
        """Test getting current database revision."""
        # Mock engine and connection
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_create_engine.return_value = mock_engine
        
        # Mock revision context
        mock_context = MagicMock()
        mock_context.get_current_revision.return_value = "abc123"
        
        with patch('zenith.db.migrations.MigrationContext') as mock_migration_context:
            mock_migration_context.configure.return_value = mock_context
            
            manager = MigrationManager(mock_database, str(temp_migrations_dir))
            current = manager.current_revision()
            
            assert current == "abc123"

    @patch('zenith.db.migrations.ScriptDirectory')
    def test_migration_history(self, mock_script_dir, mock_database, temp_migrations_dir):
        """Test getting migration history."""
        # Mock script directory and revisions
        mock_script = MagicMock()
        mock_script_dir.from_config.return_value = mock_script
        
        mock_revision1 = MagicMock()
        mock_revision1.revision = "abc123"
        mock_revision1.doc = "Add user table"
        mock_revision1.down_revision = None
        
        mock_revision2 = MagicMock()
        mock_revision2.revision = "def456"
        mock_revision2.doc = "Add posts table"
        mock_revision2.down_revision = "abc123"
        
        mock_script.walk_revisions.return_value = [mock_revision1, mock_revision2]
        
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        history = manager.migration_history()
        
        assert len(history) == 2
        assert history[0]["revision"] == "abc123"
        assert history[0]["message"] == "Add user table"
        assert history[1]["revision"] == "def456"
        assert history[1]["down_revision"] == "abc123"

    def test_status(self, mock_database, temp_migrations_dir):
        """Test migration status."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        with patch.object(manager, 'current_revision', return_value="abc123"), \
             patch.object(manager, 'migration_history', return_value=[
                 {"revision": "abc123", "message": "Rev 1", "down_revision": None},
                 {"revision": "def456", "message": "Rev 2", "down_revision": "abc123"}
             ]):
            
            status = manager.status()
            
            assert status["current_revision"] == "abc123"
            assert status["total_migrations"] == 2
            assert status["pending_migrations"] == 1  # def456 is pending

    @patch('zenith.db.migrations.Database')
    def test_create_migration_manager_helper(self, mock_database_class):
        """Test helper function for creating migration manager."""
        database_url = "postgresql://user:pass@localhost/test"
        mock_db_instance = MagicMock()
        mock_db_instance.url = database_url
        mock_database_class.return_value = mock_db_instance
        
        manager = create_migration_manager(database_url, "test_migrations")
        
        assert isinstance(manager, MigrationManager)
        mock_database_class.assert_called_once_with(database_url)
        assert manager.database == mock_db_instance


class TestMigrationCLI:
    """Test migration CLI integration."""

    def test_cli_integration_structure(self):
        """Test that CLI functions exist and have correct structure."""
        from zenith.db.migrations import setup_migrations_cli
        
        # Should be a callable function
        assert callable(setup_migrations_cli)
        
        # Test with mock app
        mock_app = MagicMock()
        mock_cli = MagicMock()
        mock_app.cli = mock_cli
        
        # Should not raise exception
        setup_migrations_cli(mock_app)
        
        # Should register db group
        mock_cli.group.assert_called_once()


class TestMigrationUtilities:
    """Test migration utility functions."""

    @pytest.fixture
    def mock_database(self):
        """Mock database instance."""
        database = MagicMock()
        database.url = "postgresql+asyncpg://user:pass@localhost/test"
        return database

    @pytest.fixture
    def temp_migrations_dir(self, tmp_path):
        """Create temporary migrations directory."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()
        return migrations_dir

    @patch('asyncio.run')
    def test_auto_create_migrations_table(self, mock_asyncio_run):
        """Test automatic Alembic version table creation."""
        from zenith.db.migrations import auto_create_migrations_table
        
        mock_engine = AsyncMock()
        
        # Should call asyncio.run
        auto_create_migrations_table(mock_engine)
        
        mock_asyncio_run.assert_called_once()

    def test_migration_manager_error_handling(self, mock_database, temp_migrations_dir):
        """Test error handling in migration manager methods."""
        manager = MigrationManager(mock_database, str(temp_migrations_dir))
        
        # Test current_revision error
        with patch.object(manager, 'database') as mock_db:
            mock_db.url = "invalid://url"
            current = manager.current_revision()
            assert current is None
        
        # Test migration_history error  
        with patch('zenith.db.migrations.ScriptDirectory') as mock_script_dir:
            mock_script_dir.from_config.side_effect = Exception("Script error")
            history = manager.migration_history()
            assert history == []