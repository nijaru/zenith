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


# LiveViewRouter for Phoenix-style patterns
class LiveViewRouter(Router):
    """Router for Phoenix-style LiveView routes."""

    def live(self, path: str, **kwargs):
        """LiveView route decorator."""
        return self.route(path, ["GET", "POST"], **kwargs)


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
    "LiveViewRouter",
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
