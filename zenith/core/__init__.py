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
    Auth,
    DatabaseContext,
    Inject,
    Request,
    ServiceContext,
    Session,
)

# HTTP patterns and constants
from zenith.core.patterns import (
    CACHEABLE_METHODS,
    HTTP_DELETE,
    HTTP_GET,
    HTTP_HEAD,
    HTTP_OPTIONS,
    HTTP_PATCH,
    HTTP_POST,
    HTTP_PUT,
    METHODS_WITH_BODY,
    SAFE_METHODS,
    extract_path_params,
)

# Service decorator removed - use Service base class from zenith.core.service instead
from zenith.core.service import Service
from zenith.core.supervisor import Supervisor

__all__ = [
    "CACHEABLE_METHODS",
    "HTTP_DELETE",
    # HTTP patterns
    "HTTP_GET",
    "HTTP_HEAD",
    "HTTP_OPTIONS",
    "HTTP_PATCH",
    "HTTP_POST",
    "HTTP_PUT",
    "METHODS_WITH_BODY",
    "SAFE_METHODS",
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
    "Session",
    "Supervisor",
    # Auto-config functions
    "create_auto_config",
    "detect_environment",
    "extract_path_params",
    "get_database_url",
    "get_secret_key",
    "is_development",
    "is_production",
    "is_staging",
    "is_testing",
]
