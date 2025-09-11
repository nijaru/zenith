"""
Dependency injection resolver for route handlers.

Handles Context, Auth, File, and other dependency injection patterns
with clean separation from routing logic.
"""

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from .dependencies import AuthDependency, ContextDependency, FileUploadDependency


class DependencyResolver:
    """
    Resolves dependencies for route handler parameters.
    
    Supports:
    - Context injection (business logic contexts)
    - Authentication injection (current user, scopes)
    - File upload injection (uploaded files)
    - Custom dependency patterns
    """

    async def resolve_dependency(
        self, 
        dependency_marker: Any, 
        param_type: type, 
        request: Request, 
        app
    ) -> Any:
        """Resolve a dependency based on its marker type."""
        
        if isinstance(dependency_marker, ContextDependency):
            return await self._resolve_context(dependency_marker, param_type, app)
        
        elif isinstance(dependency_marker, AuthDependency):
            return await self._resolve_auth(dependency_marker, request)
        
        elif isinstance(dependency_marker, FileUploadDependency):
            return await self._resolve_file_upload(dependency_marker, request)
        
        # Not a recognized dependency marker
        return None

    async def _resolve_context(self, dependency: ContextDependency, param_type: type, app) -> Any:
        """Resolve a Context dependency."""
        if not app:
            raise RuntimeError("Router not attached to application")
        
        # Use the specified context class, or infer from parameter type
        context_class = dependency.context_class or param_type
        
        # Get context instance from the application
        return await app.contexts.get_by_type(context_class)

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

    async def _resolve_file_upload(self, dependency: FileUploadDependency, request: Request) -> Any:
        """Resolve a File upload dependency."""
        from zenith.web.files import handle_file_upload

        return await handle_file_upload(
            request,
            field_name=dependency.field_name,
            config=dependency.config,
        )