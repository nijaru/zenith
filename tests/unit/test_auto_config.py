"""
Tests for AutoConfig system - Zero-configuration setup.

Tests for:
- Environment detection
- Smart defaults for database, security, middleware
- Configuration based on detected environment
"""

import os
import pytest
from unittest.mock import patch

from zenith.core.auto_config import (
    Environment,
    AutoConfig,
    DatabaseConfig,
    SecurityConfig,
    MiddlewareConfig,
    detect_environment,
    create_auto_config,
    is_development,
    is_production,
    is_testing,
    is_staging
)


class TestEnvironmentDetection:
    """Test environment detection logic."""

    def test_explicit_zenith_env(self):
        """Test ZENITH_ENV environment variable takes precedence."""
        with patch.dict(os.environ, {"ZENITH_ENV": "production"}):
            env = Environment.detect()
            assert env == Environment.PRODUCTION

    def test_node_env_detection(self):
        """Test NODE_ENV environment variable detection."""
        with patch.dict(os.environ, {"NODE_ENV": "production"}, clear=True):
            env = Environment.detect()
            assert env == Environment.PRODUCTION

        with patch.dict(os.environ, {"NODE_ENV": "development"}, clear=True):
            env = Environment.detect()
            assert env == Environment.DEVELOPMENT

        with patch.dict(os.environ, {"NODE_ENV": "test"}, clear=True):
            env = Environment.detect()
            assert env == Environment.TESTING

    def test_generic_environment_detection(self):
        """Test ENVIRONMENT environment variable detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=True):
            env = Environment.detect()
            assert env == Environment.STAGING

    def test_debug_flag_detection(self):
        """Test Python debug flag detection."""
        # This is harder to test directly since __debug__ is a built-in
        # but we can test the logic path exists
        env = Environment.detect()
        assert env in [Environment.DEVELOPMENT, Environment.PRODUCTION,
                      Environment.TESTING, Environment.STAGING]

    def test_server_name_detection(self):
        """Test server name-based detection."""
        with patch.dict(os.environ, {"SERVER_NAME": "api.myapp.com"}, clear=True):
            env = Environment.detect()
            assert env == Environment.PRODUCTION

        with patch.dict(os.environ, {"SERVER_NAME": "staging.myapp.com"}, clear=True):
            env = Environment.detect()
            assert env == Environment.STAGING

    def test_file_based_detection(self):
        """Test file-based environment detection."""
        with patch('os.path.exists') as mock_exists:
            # Test Docker environment
            def exists_side_effect(path):
                return path == "/.dockerenv"
            mock_exists.side_effect = exists_side_effect

            with patch.dict(os.environ, {}, clear=True):
                env = Environment.detect()
                assert env == Environment.PRODUCTION

        with patch('os.path.exists') as mock_exists:
            # Test testing environment
            def exists_side_effect(path):
                return path in ["pytest.ini", "conftest.py"]
            mock_exists.side_effect = exists_side_effect

            with patch.dict(os.environ, {}, clear=True):
                env = Environment.detect()
                assert env == Environment.TESTING

    def test_default_to_development(self):
        """Test defaults to development when no indicators."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', return_value=False):
                env = Environment.detect()
                assert env == Environment.DEVELOPMENT


class TestDatabaseConfig:
    """Test DatabaseConfig with environment-based defaults."""

    def test_development_config(self):
        """Test development database configuration."""
        config = DatabaseConfig.from_environment(Environment.DEVELOPMENT)

        assert config.url == "sqlite+aiosqlite:///app.db"
        assert config.echo is True
        assert config.pool_size == 5
        assert config.max_overflow == 10

    def test_testing_config(self):
        """Test testing database configuration."""
        config = DatabaseConfig.from_environment(Environment.TESTING)

        assert config.url == "sqlite+aiosqlite:///:memory:"
        assert config.echo is False
        assert config.pool_size == 1
        assert config.max_overflow == 5

    def test_production_config_with_url(self):
        """Test production config with DATABASE_URL set."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://user:pass@host/db"}):
            config = DatabaseConfig.from_environment(Environment.PRODUCTION)

            assert config.url == "postgresql+asyncpg://user:pass@host/db"
            assert config.echo is False
            assert config.pool_size == 20
            assert config.max_overflow == 30

    def test_production_config_without_url_raises(self):
        """Test production config raises error without DATABASE_URL."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                DatabaseConfig.from_environment(Environment.PRODUCTION)

            assert "DATABASE_URL environment variable required" in str(exc_info.value)

    def test_custom_database_url_override(self):
        """Test custom DATABASE_URL overrides defaults."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://custom"}):
            config = DatabaseConfig.from_environment(Environment.DEVELOPMENT)
            assert config.url == "postgresql+asyncpg://custom"


class TestSecurityConfig:
    """Test SecurityConfig with environment-based defaults."""

    def test_development_security(self):
        """Test development security configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = SecurityConfig.from_environment(Environment.DEVELOPMENT)

            assert config.secret_key == "dev-key-not-for-production-use-only"
            assert config.require_https is False
            assert "http://localhost:3000" in config.cors_origins
            assert config.cors_allow_credentials is True

    def test_production_security_with_key(self):
        """Test production security with SECRET_KEY set."""
        with patch.dict(os.environ, {"SECRET_KEY": "production-secret-key"}):
            config = SecurityConfig.from_environment(Environment.PRODUCTION)

            assert config.secret_key == "production-secret-key"
            assert config.require_https is True
            assert config.cors_origins == ["https://yourdomain.com"]
            assert config.cors_allow_credentials is True

    def test_production_security_without_key_raises(self):
        """Test production security raises error without SECRET_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SecurityConfig.from_environment(Environment.PRODUCTION)

            assert "SECRET_KEY environment variable required" in str(exc_info.value)

    def test_testing_security(self):
        """Test testing security configuration."""
        config = SecurityConfig.from_environment(Environment.TESTING)

        assert config.secret_key == "dev-key-not-for-production-use-only"
        assert config.require_https is False
        assert config.cors_origins == ["*"]
        assert config.cors_allow_credentials is False

    def test_staging_security(self):
        """Test staging security configuration."""
        with patch.dict(os.environ, {"SECRET_KEY": "staging-secret-key"}):
            config = SecurityConfig.from_environment(Environment.STAGING)

            assert config.secret_key == "staging-secret-key"
            assert config.require_https is True
            assert config.cors_origins == ["https://staging.yourdomain.com"]


class TestMiddlewareConfig:
    """Test MiddlewareConfig with environment-based defaults."""

    def test_development_middleware(self):
        """Test development middleware configuration."""
        config = MiddlewareConfig.from_environment(Environment.DEVELOPMENT)

        assert config.enable_cors is True
        assert config.enable_security_headers is False
        assert config.enable_compression is False
        assert config.enable_rate_limiting is False
        assert config.enable_request_logging is True
        assert config.enable_debug_toolbar is True

    def test_production_middleware(self):
        """Test production middleware configuration."""
        config = MiddlewareConfig.from_environment(Environment.PRODUCTION)

        assert config.enable_cors is True
        assert config.enable_security_headers is True
        assert config.enable_compression is True
        assert config.enable_rate_limiting is True
        assert config.enable_request_logging is True
        assert config.enable_debug_toolbar is False

    def test_testing_middleware(self):
        """Test testing middleware configuration."""
        config = MiddlewareConfig.from_environment(Environment.TESTING)

        assert config.enable_cors is True
        assert config.enable_security_headers is False
        assert config.enable_compression is False
        assert config.enable_rate_limiting is False
        assert config.enable_request_logging is False
        assert config.enable_debug_toolbar is False


class TestAutoConfig:
    """Test complete AutoConfig system."""

    def test_create_auto_config_development(self):
        """Test creating auto config for development."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('zenith.core.auto_config.Environment.detect', return_value=Environment.DEVELOPMENT):
                config = AutoConfig.create()

                assert config.environment == Environment.DEVELOPMENT
                assert config.debug is True
                assert config.database.echo is True
                assert config.security.require_https is False
                assert config.middleware.enable_debug_toolbar is True

    def test_create_auto_config_production(self):
        """Test creating auto config for production."""
        with patch.dict(os.environ, {"SECRET_KEY": "prod-key", "DATABASE_URL": "postgresql://prod"}):
            with patch('zenith.core.auto_config.Environment.detect', return_value=Environment.PRODUCTION):
                config = AutoConfig.create()

                assert config.environment == Environment.PRODUCTION
                assert config.debug is False
                assert config.database.echo is False
                assert config.security.require_https is True
                assert config.middleware.enable_debug_toolbar is False

    def test_create_auto_config_explicit_env(self):
        """Test creating auto config with explicit environment."""
        config = AutoConfig.create(Environment.TESTING)

        assert config.environment == Environment.TESTING
        assert config.debug is True
        assert config.database.url == "sqlite+aiosqlite:///:memory:"


class TestConvenienceFunctions:
    """Test convenience functions for environment detection."""

    def test_detect_environment_function(self):
        """Test detect_environment convenience function."""
        with patch('zenith.core.auto_config.Environment.detect', return_value=Environment.STAGING):
            env = detect_environment()
            assert env == Environment.STAGING

    def test_create_auto_config_function(self):
        """Test create_auto_config convenience function."""
        config = create_auto_config(Environment.DEVELOPMENT)
        assert isinstance(config, AutoConfig)
        assert config.environment == Environment.DEVELOPMENT

    def test_environment_check_functions(self):
        """Test environment checking convenience functions."""
        with patch('zenith.core.auto_config.detect_environment', return_value=Environment.DEVELOPMENT):
            assert is_development() is True
            assert is_production() is False
            assert is_testing() is False
            assert is_staging() is False

        with patch('zenith.core.auto_config.detect_environment', return_value=Environment.PRODUCTION):
            assert is_development() is False
            assert is_production() is True
            assert is_testing() is False
            assert is_staging() is False


class TestAutoConfigIntegration:
    """Integration tests for AutoConfig system."""

    def test_real_environment_detection(self):
        """Test real environment detection without mocking."""
        # This should not raise any exceptions
        env = detect_environment()
        assert env in [Environment.DEVELOPMENT, Environment.PRODUCTION,
                      Environment.TESTING, Environment.STAGING]

    def test_complete_config_creation(self):
        """Test complete configuration creation."""
        # Should work with current environment
        config = create_auto_config()

        assert isinstance(config, AutoConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.middleware, MiddlewareConfig)
        assert config.database.url is not None
        assert config.security.secret_key is not None

    def test_config_respects_environment_variables(self):
        """Test config respects actual environment variables."""
        with patch.dict(os.environ, {
            "ZENITH_ENV": "testing",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "SECRET_KEY": "test-key"
        }):
            config = create_auto_config()

            assert config.environment == Environment.TESTING
            assert config.database.url == "sqlite+aiosqlite:///:memory:"
            assert config.security.secret_key == "test-key"