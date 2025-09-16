"""
Core framework components - application kernel, contexts, routing.
"""

from zenith.core.application import Application

# Zero-config auto-setup
from zenith.core.auto_config import (
    AutoConfig,
    Environment,
    create_auto_config,
    detect_environment,
    get_database_url,
    get_secret_key,
    is_development,
    is_production,
    is_staging,
    is_testing,
)
from zenith.core.config import Config
from zenith.core.container import DIContainer

# Enhanced dependency injection
from zenith.core.dependencies import (
    DB,
    Auth,
    Cache,
    DatabaseContext,
    Inject,
    Request,
    ServiceContext,
)
# Service decorator removed - use Service base class from zenith.core.service instead
from zenith.core.service import Service
from zenith.core.supervisor import Supervisor

__all__ = [
    "DB",
    "Application",
    "Auth",
    "AutoConfig",
    "Cache",
    "Config",
    "DIContainer",
    "DatabaseContext",
    "Environment",
    "Inject",
    "Request",
    "Service",
    "ServiceContext",
    "Supervisor",
    "create_auto_config",
    "detect_environment",
    "get_database_url",
    "get_secret_key",
    "is_development",
    "is_production",
    "is_staging",
    "is_testing",
]
