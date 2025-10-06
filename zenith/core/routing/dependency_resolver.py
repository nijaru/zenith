"""
Dependency injection resolver for route handlers.

Handles Context, Auth, File, and other dependency injection patterns
with clean separation from routing logic.
"""

import asyncio
from typing import Any

from starlette.requests import Request

from ..scoped import RequestScoped
from .dependencies import AuthDependency, FileDependency, InjectDependency

# Global singleton registry for services
_service_instances: dict[type, Any] = {}
_service_lock = asyncio.Lock()


class DependencyResolver:
    """
    Resolves dependencies for route handler parameters.

    Supports:
    - Context injection (business logic contexts)
    - Authentication injection (current user, scopes)
    - File upload injection (uploaded files)
    - Request-scoped dependencies (database sessions, etc.)
    - Custom dependency patterns
    """

    async def resolve_dependency(
        self, dependency_marker: Any, param_type: type, request: Request, app
    ) -> Any:
        """Resolve a dependency based on its marker type."""

        if isinstance(dependency_marker, RequestScoped):
            return await dependency_marker.get_or_create(request)

        elif isinstance(dependency_marker, InjectDependency):
            return await self._resolve_context(
                dependency_marker, param_type, request, app
            )

        elif isinstance(dependency_marker, AuthDependency):
            return await self._resolve_auth(dependency_marker, request)

        elif isinstance(dependency_marker, FileDependency):
            return await self._resolve_file_upload(dependency_marker, request)

        # Not a recognized dependency marker
        return None

    async def _resolve_context(
        self, dependency: InjectDependency, param_type: type, request: Request, app
    ) -> Any:
        """
        Resolve a Service dependency with constructor injection.

        Uses DIContainer's _create_instance for automatic dependency resolution.
        """
        # Use the specified service class, or infer from parameter type
        service_class = dependency.service_class or param_type

        # Check if service is already created (singleton pattern)
        if service_class in _service_instances:
            instance = _service_instances[service_class]
            # Inject request context (services are singletons but request changes)
            from zenith.core.service import Service

            if isinstance(instance, Service) and request:
                instance._inject_request(request)
            return instance

        # Create new instance with thread-safe lock
        async with _service_lock:
            # Double-check pattern - another request might have created it
            if service_class in _service_instances:
                instance = _service_instances[service_class]
                from zenith.core.service import Service

                if isinstance(instance, Service) and request:
                    instance._inject_request(request)
                return instance

            # Try to get from registered contexts first (for backward compatibility)
            if app and hasattr(app, "contexts"):
                try:
                    instance = await app.contexts.get_by_type(service_class)
                    _service_instances[service_class] = instance
                    # Inject request context
                    from zenith.core.service import Service

                    if isinstance(instance, Service) and request:
                        instance._inject_request(request)
                    return instance
                except (KeyError, AttributeError):
                    pass  # Not registered, create directly

            # Use DIContainer's injection for constructor dependencies
            if app and hasattr(app, "container"):
                try:
                    instance = app.container._create_instance(service_class)
                except KeyError:
                    # If dependency resolution fails, try without args (backward compat)
                    instance = service_class()
            else:
                # No container available, instantiate without dependencies
                instance = service_class()

            # Inject framework internals for Service instances
            from zenith.core.service import Service

            if isinstance(instance, Service):
                if app and hasattr(app, "container"):
                    instance._inject_container(app.container)
                # Inject request context
                if request:
                    instance._inject_request(request)

            # Initialize if it has an async initialize method
            if hasattr(instance, "initialize") and callable(instance.initialize):
                await instance.initialize()

            # Store singleton
            _service_instances[service_class] = instance
            return instance

    async def _resolve_auth(self, dependency: AuthDependency, request: Request) -> Any:
        """Resolve an Auth dependency (current user)."""
        from zenith.middleware.auth import get_current_user, require_scopes

        try:
            # Get current user from auth middleware
            user = get_current_user(request, required=dependency.required)

            # Check required scopes if user is authenticated
            if user and dependency.scopes:
                require_scopes(request, dependency.scopes)

            return user

        except Exception as e:
            # Handle authentication/authorization exceptions
            from zenith.exceptions import HTTPException

            if isinstance(e, HTTPException):
                # Return JSON error response for API consistency
                raise e  # Let middleware handle it properly
            raise

    async def _resolve_file_upload(
        self, dependency: FileDependency, request: Request
    ) -> Any:
        """Resolve a File upload dependency."""
        from zenith.web.files import handle_file_upload

        return await handle_file_upload(
            request,
            field_name=dependency.field_name,
            config=dependency.config,
        )
