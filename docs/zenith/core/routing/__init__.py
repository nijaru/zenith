"""
Modern Zenith routing system with clean architecture.

Provides state-of-the-art routing with dependency injection,
separated concerns, and excellent developer experience.
"""

# Core routing components
from .dependencies import (
    Auth,
    AuthDependency,
    File,
    FileDependency,
    Inject,
    InjectDependency,
)
from .dependency_resolver import DependencyResolver
from .executor import RouteExecutor
from .response_processor import ResponseProcessor
from .router import Router

# Route specifications and dependency markers
from .specs import HTTPMethod, RouteSpec

# Utilities
from .utils import (
    create_route_name,
    extract_route_tags,
    normalize_path,
    validate_response_type,
)

__all__ = [
    # Dependencies
    "Auth",
    "AuthDependency",
    "DependencyResolver",
    "File",
    "FileDependency",
    # Specs
    "HTTPMethod",
    "Inject",
    "InjectDependency",
    "ResponseProcessor",
    "RouteExecutor",
    "RouteSpec",
    # Core classes
    "Router",
    "create_route_name",
    "extract_route_tags",
    "normalize_path",
    # Utilities
    "validate_response_type",
]
