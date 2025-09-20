"""
Dependency injection components for Zenith routing.

Provides Inject, Auth, and File dependency markers for route handlers.
"""

from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from zenith.core.service import Service as BaseService
    from zenith.web.files import FileUploadConfig


class InjectDependency:
    """Marker for service dependency injection."""

    __slots__ = ("service_class",)

    def __init__(self, service_class: type["BaseService"] | None = None):
        self.service_class = service_class


class AuthDependency:
    """Marker for authentication dependency injection."""

    __slots__ = ("required", "scopes")

    def __init__(self, required: bool = True, scopes: list[str] | None = None):
        self.required = required
        self.scopes = scopes or []


class FileDependency:
    """Marker for file upload dependency injection."""

    __slots__ = ("config", "field_name")

    def __init__(
        self,
        field_name: str = "file",
        config: Union["FileUploadConfig", dict[str, Any], None] = None,
    ):
        self.field_name = field_name
        self.config = config or {}


def Inject(service_class: type["BaseService"] | None = None) -> InjectDependency:
    """Create a service dependency injection marker."""
    return InjectDependency(service_class)


def Auth(required: bool = True, scopes: list[str] | None = None) -> AuthDependency:
    """Create an authentication dependency marker."""
    return AuthDependency(required, scopes)


def File(
    field_name: str = "file",
    config: Union["FileUploadConfig", dict[str, Any], None] = None,
) -> FileDependency:
    """Create a file upload dependency marker."""
    return FileDependency(field_name, config)
