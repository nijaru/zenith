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
    Session,
    Auth,
    DatabaseContext,
    Inject,
    Request,
    ServiceContext,
)
# HTTP patterns and constants
from zenith.core.patterns import (
    HTTP_GET, HTTP_POST, HTTP_PUT, HTTP_PATCH, HTTP_DELETE, HTTP_HEAD, HTTP_OPTIONS,
    METHODS_WITH_BODY, CACHEABLE_METHODS, SAFE_METHODS,
    extract_path_params
)

# Service decorator removed - use Service base class from zenith.core.service instead
from zenith.core.service import Service
from zenith.core.supervisor import Supervisor

__all__ = [
    "Session",
    "Application",
    "Auth",
    "AutoConfig",
    "Config",
    "DIContainer",
    "DatabaseContext",
    "Environment",
    "Inject",
    "Request",
    "Service",
    "ServiceContext",
    "Supervisor",
    # HTTP patterns
    "HTTP_GET", "HTTP_POST", "HTTP_PUT", "HTTP_PATCH", "HTTP_DELETE", "HTTP_HEAD", "HTTP_OPTIONS",
    "METHODS_WITH_BODY", "CACHEABLE_METHODS", "SAFE_METHODS",
    "extract_path_params",
    # Auto-config functions
    "create_auto_config",
    "detect_environment",
    "get_database_url",
    "get_secret_key",
    "is_development",
    "is_production",
    "is_staging",
    "is_testing",
]
