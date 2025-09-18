"""
Tests for configuration management.
"""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from zenith.core.config import Config


class TestConfig:
    """Test configuration management."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.debug  # Default to True in development environment (detected via NODE_ENV)
        assert config.log_level == "INFO"
        assert config.worker_count == 1
        assert config.max_connections == 1000

    def test_env_config(self):
        """Test configuration from environment variables."""
        # Set environment variables
        os.environ["DEBUG"] = "true"
        os.environ["HOST"] = "0.0.0.0"
        os.environ["PORT"] = "3000"
        os.environ["LOG_LEVEL"] = "DEBUG"

        config = Config()

        assert config.debug
        assert config.host == "0.0.0.0"
        assert config.port == 3000
        assert config.log_level == "DEBUG"

        # Cleanup
        del os.environ["DEBUG"]
        del os.environ["HOST"]
        del os.environ["PORT"]
        del os.environ["LOG_LEVEL"]

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        env_content = """DEBUG=true
HOST=0.0.0.0
PORT=4000
SECRET_KEY=test-secret
"""

        # Store original env vars to restore later
        original_env = {
            key: os.environ.get(key)
            for key in ["DEBUG", "HOST", "PORT", "SECRET_KEY"]
        }

        with NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            env_file = f.name

        try:
            config = Config.from_env(env_file)

            assert config.debug
            assert config.host == "0.0.0.0"
            assert config.port == 4000
            assert config.secret_key == "test-secret"
        finally:
            # Clean up temp file
            Path(env_file).unlink()

            # Restore original environment variables
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_custom_config(self):
        """Test custom configuration values."""
        config = Config()
        config.set("my_setting", "my_value")

        assert config.get("my_setting") == "my_value"
        assert config.get("nonexistent", "default") == "default"

    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()

        # Valid config should not raise
        config.validate()

        # Invalid port should raise
        config.port = -1
        with pytest.raises(ValueError, match="Invalid port"):
            config.validate()

        # Invalid worker count should raise
        config.port = 8000
        config.worker_count = 0
        with pytest.raises(ValueError, match="Invalid worker_count"):
            config.validate()
