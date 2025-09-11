"""
Modern Zenith routing system with clean architecture.

Provides state-of-the-art routing with dependency injection,
separated concerns, and excellent developer experience.
"""

# Core routing components
from .router import Router
from .executor import RouteExecutor
from .dependency_resolver import DependencyResolver
from .response_processor import ResponseProcessor

# Route specifications and dependency markers
from .specs import HTTPMethod, RouteSpec
from .dependencies import (
    Auth,
    AuthDependency,
    Context,
    ContextDependency,
    File,
    FileUploadDependency,
)

# Utilities
from .utils import (
    validate_response_type,
    create_route_name,
    extract_route_tags,
    normalize_path,
)

# LiveViewRouter for Phoenix-style patterns
class LiveViewRouter(Router):
    """Router for Phoenix-style LiveView routes."""
    
    def live(self, path: str, **kwargs):
        """LiveView route decorator."""
        return self.route(path, ["GET", "POST"], **kwargs)

__all__ = [
    # Core classes
    "Router",
    "LiveViewRouter",
    "RouteExecutor",
    "DependencyResolver", 
    "ResponseProcessor",
    # Dependencies
    "Auth",
    "AuthDependency",
    "Context", 
    "ContextDependency",
    "File",
    "FileUploadDependency",
    # Specs
    "HTTPMethod",
    "RouteSpec",
    # Utilities
    "validate_response_type",
    "create_route_name",
    "extract_route_tags", 
    "normalize_path",
]