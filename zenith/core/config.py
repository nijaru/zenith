"""
Configuration management for Zenith applications.

Handles environment variables, configuration files, and runtime settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Config:
    """Application configuration with environment variable support."""

    # Environment detection (used to set defaults)
    _environment: str = field(default_factory=lambda: Config._get_environment())

    # Core settings
    debug: bool = field(default_factory=lambda: Config._get_debug_default())
    secret_key: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    )

    # Server settings
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:///./zenith.db"
        )
    )

    # Redis
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
    )

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Performance
    worker_count: int = field(
        default_factory=lambda: int(os.getenv("WORKER_COUNT", "1"))
    )
    max_connections: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONNECTIONS", "1000"))
    )

    # Custom settings
    custom: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Config":
        """Create config from environment variables and optional .env file."""
        if env_file:
            cls._load_env_file(env_file)
        return cls()

    @classmethod
    def _load_env_file(cls, env_file: str | Path) -> None:
        """Load environment variables from .env file."""
        env_path = Path(env_file)
        if not env_path.exists():
            return

        with env_path.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    if key and value:
                        os.environ.setdefault(key.strip(), value.strip())

    def get(self, key: str, default: Any = None) -> Any:
        """Get custom configuration value."""
        return self.custom.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set custom configuration value."""
        self.custom[key] = value

    @staticmethod
    def _get_environment() -> str:
        """Get the current environment from ZENITH_ENV."""
        env_aliases = {
            "dev": "development",
            "prod": "production",
            "test": "test",
            "testing": "test",
            "stage": "staging",
        }

        env = os.getenv("ZENITH_ENV", "").lower()
        if env in env_aliases:
            return env_aliases[env]
        elif env in ("development", "production", "test", "staging"):
            return env

        # Check explicit DEBUG env var as secondary option
        if os.getenv("DEBUG"):
            debug_val = os.getenv("DEBUG", "").lower()
            if debug_val == "true":
                return "development"
            elif debug_val == "false":
                return "production"

        # Check legacy environment variables for compatibility
        legacy_vars = [
            os.getenv("ENVIRONMENT", "").lower(),
            os.getenv("ENV", "").lower(),
            os.getenv("FLASK_ENV", "").lower(),
            os.getenv("NODE_ENV", "").lower(),
        ]

        for var in legacy_vars:
            if var in ("development", "dev", "develop"):
                return "development"
            elif var in ("production", "prod"):
                return "production"
            elif var in ("test", "testing"):
                return "test"
            elif var in ("staging", "stage"):
                return "staging"

        return "development"  # Default to development for local development

    @staticmethod
    def _get_debug_default() -> bool:
        """Get debug default based on environment."""
        env = Config._get_environment()

        # Check explicit DEBUG override first
        debug_env = os.getenv("DEBUG")
        if debug_env:
            return debug_env.lower() == "true"

        # Otherwise use environment-based defaults
        return env in ("development", "test")

    def validate(self) -> None:
        """Validate configuration settings."""
        # Check if we're in production-like environment
        is_production = self._environment in ("production", "staging")

        # Auto-generate secret key for development if not set
        if not self.secret_key or self.secret_key == "dev-secret-change-in-prod":
            import logging
            import secrets
            import string

            if is_production:
                raise ValueError(
                    "SECRET_KEY must be set in production/staging environments.\n"
                    "Generate with:\n"
                    "  zen keygen                    # Print to stdout\n"
                    "  zen keygen --output .env      # Save to .env file"
                )

            # Development/test mode - generate temporary key
            chars = string.ascii_letters + string.digits
            self.secret_key = "".join(secrets.choice(chars) for _ in range(64))

            logger = logging.getLogger("zenith.config")
            logger.info(
                f"Generated temporary SECRET_KEY for {self._environment} environment"
            )

        # Validate secret key strength in production
        if is_production and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")

        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")

        if self.worker_count < 1:
            raise ValueError(f"Invalid worker_count: {self.worker_count}")

        if self.max_connections < 1:
            raise ValueError(f"Invalid max_connections: {self.max_connections}")
