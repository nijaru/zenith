"""
Route execution engine with dependency injection.

Handles calling route handlers with proper dependency resolution,
parameter injection, and error handling.
"""

import inspect
import sys
from typing import Any, get_type_hints, Final

from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import Response

from zenith.web.responses import OptimizedJSONResponse
from .dependency_resolver import DependencyResolver
from .response_processor import ResponseProcessor
from .specs import RouteSpec

# Intern common HTTP methods for faster string comparisons
_POST_METHODS: Final = frozenset([
    sys.intern("POST"), sys.intern("PUT"), sys.intern("PATCH")
])

_HTTP_METHODS: Final = {
    sys.intern("GET"), sys.intern("POST"), sys.intern("PUT"), 
    sys.intern("PATCH"), sys.intern("DELETE"), sys.intern("HEAD"), 
    sys.intern("OPTIONS"), sys.intern("TRACE")
}


class RouteExecutor:
    """
    Executes route handlers with dependency injection.
    
    Responsibilities:
    - Parameter extraction and type conversion
    - Dependency injection resolution
    - Request body validation
    - Handler execution
    - Response processing delegation
    """

    def __init__(self):
        self.dependency_resolver = DependencyResolver()
        self.response_processor = ResponseProcessor()

    async def execute_route(self, request: Request, route_spec: RouteSpec, app) -> Response:
        """Execute a route handler with full dependency injection."""
        try:
            # Prepare handler arguments
            kwargs = await self._resolve_handler_args(request, route_spec.handler, app)
            
            # Execute handler
            result = await route_spec.handler(**kwargs)
            
            # Process response
            return await self.response_processor.process_response(
                result, request, route_spec.handler
            )
            
        except ValidationError as e:
            return OptimizedJSONResponse(
                {"error": "Validation failed", "details": e.errors()},
                status_code=422,
            )
        except Exception as e:
            # Re-raise for middleware to handle
            raise

    async def _resolve_handler_args(self, request: Request, handler, app) -> dict[str, Any]:
        """Resolve all arguments needed for the handler."""
        sig = inspect.signature(handler)
        type_hints = get_type_hints(handler)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, param.annotation)

            # Direct request injection
            if param_name == "request":
                kwargs[param_name] = request
                continue

            # Path parameters
            if param_name in request.path_params:
                kwargs[param_name] = self._convert_path_param(
                    request.path_params[param_name], param_type
                )
                continue

            # Query parameters
            if param_name in request.query_params:
                kwargs[param_name] = self._convert_query_param(
                    request.query_params[param_name], param_type
                )
                continue

            # Dependency injection (Context, Auth, File, etc.)
            if param.default != inspect.Parameter.empty:
                from .dependencies import AuthDependency, ContextDependency, FileUploadDependency
                
                # Check if this is a dependency marker
                is_dependency = isinstance(param.default, (AuthDependency, ContextDependency, FileUploadDependency))
                
                if is_dependency:
                    resolved = await self.dependency_resolver.resolve_dependency(
                        param.default, param_type, request, app
                    )
                    kwargs[param_name] = resolved  # Can be None for optional Auth
                    continue
                else:
                    # Regular default value
                    kwargs[param_name] = param.default
                    continue

            # BackgroundTasks injection
            if param_type.__name__ == "BackgroundTasks" or (
                hasattr(param_type, "__module__") and 
                param_type.__module__ == "zenith.background" and
                param_type.__name__ == "BackgroundTasks"
            ):
                from zenith.background import BackgroundTasks
                kwargs[param_name] = BackgroundTasks()
                continue

            # Pydantic models (request body)
            if (
                inspect.isclass(param_type)
                and issubclass(param_type, BaseModel)
                and request.method in _POST_METHODS
            ):
                # Get raw body to handle special characters properly
                body_bytes = await request.body()
                try:
                    # Use orjson if available for better performance
                    try:
                        import orjson
                        body = orjson.loads(body_bytes)  # orjson handles bytes directly
                    except ImportError:
                        # Fallback to standard json with proper encoding
                        import json
                        try:
                            body_str = body_bytes.decode('utf-8', errors='strict')
                            body = json.loads(body_str)  # Use strict mode (default)
                        except UnicodeDecodeError as e:
                            raise ValidationError(f"Invalid UTF-8 encoding in request body: {str(e)}")
                except Exception as e:
                    # Provide helpful error message
                    if hasattr(e, '__class__') and e.__class__.__name__ == 'JSONDecodeError':
                        raise ValidationError(f"Invalid JSON in request body: {str(e)}")
                    raise ValidationError(f"Failed to parse request body: {str(e)}")
                kwargs[param_name] = param_type.model_validate(body)
                continue

        return kwargs

    def _convert_path_param(self, value: str, param_type: type) -> Any:
        """Convert path parameter to the expected type."""
        if param_type is int:
            return int(value)
        elif param_type is float:
            return float(value)
        return value

    def _convert_query_param(self, value: str, param_type: type) -> Any:
        """Convert query parameter to the expected type."""
        if param_type is int:
            return int(value)
        elif param_type is float:
            return float(value)
        elif param_type is bool:
            return value.lower() in ("true", "1", "yes")
        return value