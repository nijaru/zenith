"""
Dependency injection components for Zenith routing.

Provides Context, Auth, and File dependency markers for route handlers.
"""

from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from zenith.core.context import Context as BaseContext
    from zenith.web.files import FileUploadConfig


class ContextDependency:
    """Marker for context dependency injection."""
    
    def __init__(self, context_class: type["BaseContext"] | None = None):
        self.context_class = context_class


class AuthDependency:
    """Marker for authentication dependency injection."""
    
    def __init__(self, required: bool = True, scopes: list[str] | None = None):
        self.required = required
        self.scopes = scopes or []


class FileUploadDependency:
    """Marker for file upload dependency injection."""
    
    def __init__(self, field_name: str = "file", config: Union["FileUploadConfig", dict[str, Any], None] = None):
        self.field_name = field_name
        self.config = config or {}


def Context(context_class: type["BaseContext"] | None = None) -> ContextDependency:
    """Create a context dependency marker."""
    return ContextDependency(context_class)


def Auth(required: bool = True, scopes: list[str] | None = None) -> AuthDependency:
    """Create an authentication dependency marker."""
    return AuthDependency(required, scopes)


def File(field_name: str = "file", config: Union["FileUploadConfig", dict[str, Any], None] = None) -> FileUploadDependency:
    """Create a file upload dependency marker."""
    return FileUploadDependency(field_name, config)