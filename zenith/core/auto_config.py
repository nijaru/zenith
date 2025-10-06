"""
Zero-configuration application setup with environment intelligence.

Provides Rails-like auto-configuration that detects the environment and
sets up appropriate defaults for database, middleware, security, and more.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from pydantic import BaseModel

__all__ = ["AutoConfig", "Environment", "create_auto_config", "detect_environment"]


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def detect(cls) -> Environment:
        """
        Detect the current environment from various sources.

        Checks in order:
        1. ZENITH_ENV environment variable
        2. NODE_ENV environment variable (common in deployments)
        3. ENVIRONMENT environment variable
        4. Python __debug__ flag
        5. Domain patterns and file presence
        6. Defaults to development
        """
        # Explicit environment variables
        env_var = os.getenv("ZENITH_ENV", "").lower()
        if env_var in [e.value for e in cls]:
            return cls(env_var)

        # Node.js style environment
        node_env = os.getenv("NODE_ENV", "").lower()
        if node_env == "production":
            return cls.PRODUCTION
        elif node_env in ["test", "testing"]:
            return cls.TESTING
        elif node_env in ["development", "dev"]:
            return cls.DEVELOPMENT
        elif node_env in ["staging", "stage"]:
            return cls.STAGING

        # Generic environment variable
        generic_env = os.getenv("ENVIRONMENT", "").lower()
        if generic_env in [e.value for e in cls]:
            return cls(generic_env)

        # Debug mode detection
        if not __debug__:
            # Python was run with -O flag, likely production
            return cls.PRODUCTION

        # Domain-based detection
        server_name = os.getenv("SERVER_NAME", "")
        # Check staging patterns first since staging domains often have .com/.org/etc
        if any(stage in server_name for stage in ["stage", "staging", "test"]):
            return cls.STAGING
        elif any(
            prod in server_name for prod in ["api.", "prod", ".com", ".org", ".net"]
        ):
            return cls.PRODUCTION

        # File-based detection
        from pathlib import Path

        if Path("/.dockerenv").exists():
            # Running in Docker, likely production/staging
            return cls.PRODUCTION
        elif Path("pytest.ini").exists() or Path("conftest.py").exists():
            # Testing environment detected
            return cls.TESTING

        # Default to development
        return cls.DEVELOPMENT


class DatabaseConfig(BaseModel):
    """Database configuration with smart defaults."""

    url: str | None = None
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 30

    @classmethod
    def from_environment(cls, env: Environment) -> DatabaseConfig:
        """Create database config based on environment."""
        url = os.getenv("DATABASE_URL")

        if not url:
            # Smart defaults based on environment
            if env == Environment.TESTING:
                url = "sqlite+aiosqlite:///:memory:"
            elif env == Environment.DEVELOPMENT:
                url = "sqlite+aiosqlite:///app.db"
            else:
                # Production/staging needs explicit configuration
                raise ValueError(
                    "DATABASE_URL environment variable required for production. "
                    "Example: postgresql+asyncpg://user:pass@host/db"
                )

        # Environment-specific settings
        if env == Environment.DEVELOPMENT:
            return cls(url=url, echo=True, pool_size=5, max_overflow=10)
        elif env == Environment.TESTING:
            return cls(url=url, echo=False, pool_size=1, max_overflow=5)
        else:
            # Production/staging
            return cls(url=url, echo=False, pool_size=20, max_overflow=30)


class SecurityConfig(BaseModel):
    """Security configuration with environment-appropriate defaults."""

    secret_key: str | None = None
    require_https: bool = False
    cors_origins: list[str] = []
    cors_allow_credentials: bool = False

    @classmethod
    def from_environment(cls, env: Environment) -> SecurityConfig:
        """Create security config based on environment."""
        secret_key = os.getenv("SECRET_KEY")

        if not secret_key:
            if env in [Environment.PRODUCTION, Environment.STAGING]:
                raise ValueError(
                    "SECRET_KEY environment variable required for production.\n"
                    "Generate with:\n"
                    "  zen keygen                    # Print to stdout\n"
                    "  zen keygen --output .env      # Save to .env file"
                )
            else:
                # Development/testing default (insecure but convenient)
                secret_key = "dev-key-not-for-production-use-only"

        # Environment-specific security settings
        if env == Environment.PRODUCTION:
            return cls(
                secret_key=secret_key,
                require_https=True,
                cors_origins=["https://yourdomain.com"],  # Restrictive by default
                cors_allow_credentials=True,
            )
        elif env == Environment.STAGING:
            return cls(
                secret_key=secret_key,
                require_https=True,
                cors_origins=["https://staging.yourdomain.com"],
                cors_allow_credentials=True,
            )
        elif env == Environment.TESTING:
            return cls(
                secret_key=secret_key,
                require_https=False,
                cors_origins=["*"],  # Permissive for testing
                cors_allow_credentials=False,
            )
        else:  # Development
            return cls(
                secret_key=secret_key,
                require_https=False,
                cors_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                cors_allow_credentials=True,
            )


class MiddlewareConfig(BaseModel):
    """Middleware configuration with smart defaults."""

    enable_cors: bool = True
    enable_security_headers: bool = True
    enable_compression: bool = True
    enable_rate_limiting: bool = False
    enable_request_logging: bool = True
    enable_debug_toolbar: bool = False

    @classmethod
    def from_environment(cls, env: Environment) -> MiddlewareConfig:
        """Create middleware config based on environment."""
        if env == Environment.PRODUCTION or env == Environment.STAGING:
            return cls(
                enable_cors=True,
                enable_security_headers=True,
                enable_compression=True,
                enable_rate_limiting=True,
                enable_request_logging=True,
                enable_debug_toolbar=False,
            )
        elif env == Environment.TESTING:
            return cls(
                enable_cors=True,
                enable_security_headers=False,
                enable_compression=False,
                enable_rate_limiting=False,
                enable_request_logging=False,
                enable_debug_toolbar=False,
            )
        else:  # Development
            return cls(
                enable_cors=True,
                enable_security_headers=False,
                enable_compression=False,
                enable_rate_limiting=False,
                enable_request_logging=True,
                enable_debug_toolbar=True,
            )


class AutoConfig(BaseModel):
    """Complete auto-configuration for a Zenith application."""

    environment: Environment
    debug: bool
    database: DatabaseConfig
    security: SecurityConfig
    middleware: MiddlewareConfig

    @classmethod
    def create(cls, env: Environment | None = None) -> AutoConfig:
        """Create auto-configuration for the detected or specified environment."""
        if env is None:
            env = Environment.detect()

        return cls(
            environment=env,
            debug=env in [Environment.DEVELOPMENT, Environment.TESTING],
            database=DatabaseConfig.from_environment(env),
            security=SecurityConfig.from_environment(env),
            middleware=MiddlewareConfig.from_environment(env),
        )


def detect_environment() -> Environment:
    """Detect the current application environment."""
    return Environment.detect()


def create_auto_config(env: Environment | None = None) -> AutoConfig:
    """Create auto-configuration for the application."""
    return AutoConfig.create(env)


def get_database_url() -> str:
    """
    Get the database URL with smart defaults.

    Returns:
        Database URL string

    Raises:
        ValueError: If no URL can be determined for production
    """
    env = detect_environment()
    config = DatabaseConfig.from_environment(env)
    return config.url


def get_secret_key() -> str:
    """
    Get the secret key with smart defaults.

    Returns:
        Secret key string

    Raises:
        ValueError: If no secret key for production
    """
    env = detect_environment()
    config = SecurityConfig.from_environment(env)
    return config.secret_key


def should_enable_debug() -> bool:
    """Determine if debug mode should be enabled."""
    env = detect_environment()
    return env in [Environment.DEVELOPMENT, Environment.TESTING]


def get_cors_origins() -> list[str]:
    """Get CORS origins based on environment."""
    env = detect_environment()
    config = SecurityConfig.from_environment(env)
    return config.cors_origins


def get_middleware_config() -> dict[str, Any]:
    """Get middleware configuration as a dictionary."""
    env = detect_environment()
    config = MiddlewareConfig.from_environment(env)
    return config.model_dump()


# Convenience functions for specific checks
def is_production() -> bool:
    """Check if running in production environment."""
    return detect_environment() == Environment.PRODUCTION


def is_development() -> bool:
    """Check if running in development environment."""
    return detect_environment() == Environment.DEVELOPMENT


def is_testing() -> bool:
    """Check if running in testing environment."""
    return detect_environment() == Environment.TESTING


def is_staging() -> bool:
    """Check if running in staging environment."""
    return detect_environment() == Environment.STAGING
