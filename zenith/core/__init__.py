"""
Core framework components - application kernel, contexts, routing.
"""

from zenith.core.application import Application
from zenith.core.config import Config
from zenith.core.container import DIContainer
from zenith.core.service import Service
from zenith.core.supervisor import Supervisor

# Enhanced dependency injection
from zenith.core.dependencies import (
    Auth,
    Cache,
    DB,
    DatabaseContext,
    Inject,
    Request,
    Service as ServiceDecorator,
    ServiceContext,
)

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

__all__ = [
    "Application",
    "Auth",
    "AutoConfig",
    "Cache",
    "Config",
    "DB",
    "DIContainer",
    "DatabaseContext",
    "Environment",
    "Inject",
    "Request",
    "Service",
    "ServiceDecorator",
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
