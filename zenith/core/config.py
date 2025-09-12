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

    # Core settings
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true"
    )
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

    def validate(self) -> None:
        """Validate configuration settings."""
        # Auto-generate secret key for development if not set
        if not self.secret_key or self.secret_key == "dev-secret-change-in-prod":
            import secrets
            import string
            import logging
            
            chars = string.ascii_letters + string.digits
            self.secret_key = ''.join(secrets.choice(chars) for _ in range(64))
            
            logger = logging.getLogger("zenith.config")
            if self.debug:
                # Development mode - this is expected
                logger.info(
                    "Generated development SECRET_KEY (set SECRET_KEY environment variable for production)"
                )
            else:
                # Production mode without secret key - this is a warning
                logger.warning(
                    "No SECRET_KEY provided in production mode! "
                    "Generated temporary key. Set SECRET_KEY environment variable for security."
                )

        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")

        if self.worker_count < 1:
            raise ValueError(f"Invalid worker_count: {self.worker_count}")

        if self.max_connections < 1:
            raise ValueError(f"Invalid max_connections: {self.max_connections}")
