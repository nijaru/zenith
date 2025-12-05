"""
Route execution engine with dependency injection.

Handles calling route handlers with proper dependency resolution,
parameter injection, and error handling.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import Response

from zenith.exceptions import ValidationException
from zenith.web.responses import OptimizedJSONResponse

# Import dependency types at module level (not per-request)
from .dependencies import AuthDependency, FileDependency, InjectDependency
from .dependency_resolver import DependencyResolver
from .response_processor import ResponseProcessor
from .specs import RouteSpec

_POST_METHODS = frozenset(["POST", "PUT", "PATCH"])
_DEPENDENCY_TYPES = (AuthDependency, InjectDependency, FileDependency)

# Pre-check JSON decoder at module load (not per-request)
try:
    import orjson

    _json_loads = orjson.loads
except ImportError:
    import json

    _json_loads = json.loads


@dataclass(slots=True)
class _CachedHandlerInfo:
    """Cached handler metadata to avoid per-request introspection."""

    signature: inspect.Signature
    type_hints: dict[str, Any]
    parameters: dict[str, inspect.Parameter]


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
        # Cache handler metadata to avoid per-request introspection
        self._handler_cache: dict[Callable, _CachedHandlerInfo] = {}

    def _get_handler_info(self, handler: Callable) -> _CachedHandlerInfo:
        """Get cached handler info or create it."""
        if handler not in self._handler_cache:
            sig = inspect.signature(handler)
            try:
                hints = get_type_hints(handler)
            except Exception:
                hints = {}
            self._handler_cache[handler] = _CachedHandlerInfo(
                signature=sig,
                type_hints=hints,
                parameters=dict(sig.parameters),
            )
        return self._handler_cache[handler]

    async def execute_route(
        self, request: Request, route_spec: RouteSpec, app
    ) -> Response:
        """Execute a route handler with full dependency injection."""
        try:
            # Set up request context for dependency injection
            await self._setup_request_context(request)

            # Prepare handler arguments and track background tasks
            kwargs, background_tasks = await self._resolve_handler_args_with_bg(
                request, route_spec.handler, app
            )

            # Execute handler
            result = await route_spec.handler(**kwargs)

            # Process response with background tasks
            return await self.response_processor.process_response(
                result, request, route_spec, background_tasks
            )

        except ValidationError as e:
            return OptimizedJSONResponse(
                {"error": "Validation failed", "details": e.errors()},
                status_code=422,
            )
        except Exception:
            # Re-raise for middleware to handle
            raise
        finally:
            # Clean up contexts
            await self._cleanup_request_context()

    async def _setup_request_context(self, request: Request) -> None:
        """Set up request context for dependency injection."""
        try:
            from ..scoped import set_current_request

            set_current_request(request)
        except Exception:
            # Don't block if request context setup fails
            pass

    async def _cleanup_request_context(self) -> None:
        """Clean up request context."""
        try:
            from ..scoped import clear_current_request

            clear_current_request()
        except Exception as e:
            import logging

            logger = logging.getLogger("zenith.routing")
            logger.warning(f"Failed to cleanup request context: {e}")

    async def _resolve_handler_args_with_bg(
        self, request: Request, handler, app
    ) -> tuple[dict[str, Any], Any]:
        """Resolve handler arguments and return background tasks if any."""
        kwargs = await self._resolve_handler_args(request, handler, app)

        # Find BackgroundTasks instance if any
        background_tasks = None
        for value in kwargs.values():
            if (
                hasattr(value, "__class__")
                and value.__class__.__name__ == "BackgroundTasks"
            ):
                background_tasks = value
                break

        return kwargs, background_tasks

    async def _resolve_handler_args(
        self, request: Request, handler, app
    ) -> dict[str, Any]:
        """Resolve all arguments needed for the handler."""
        # Use cached handler info instead of per-request introspection
        info = self._get_handler_info(handler)
        kwargs = {}

        for param_name, param in info.parameters.items():
            param_type = info.type_hints.get(param_name, param.annotation)

            # Direct request injection
            if param_name == "request":
                kwargs[param_name] = request
                continue

            # Path parameters
            # Check scope["path_params"] explicitly for RadixRouter compatibility
            path_params = request.path_params or request.scope.get("path_params", {})
            if param_name in path_params:
                kwargs[param_name] = self._convert_path_param(
                    path_params[param_name], param_type, param_name
                )
                continue

            # Query parameters
            if param_name in request.query_params:
                kwargs[param_name] = self._convert_query_param(
                    request.query_params[param_name], param_type, param_name
                )
                continue

            # Dependency injection (Context, Auth, File, etc.)
            if param.default != inspect.Parameter.empty:
                # Check if this is a dependency marker (using module-level imports)
                is_dependency = isinstance(param.default, _DEPENDENCY_TYPES)

                # Also check for Depends objects (from FastAPI or our mock)
                is_depends = (
                    hasattr(param.default, "__class__")
                    and param.default.__class__.__name__ == "Depends"
                )

                # Check if it has a dependency attribute (our Depends objects)
                has_dependency_attr = hasattr(param.default, "dependency")

                if is_dependency:
                    resolved = await self.dependency_resolver.resolve_dependency(
                        param.default, param_type, request, app
                    )
                    kwargs[param_name] = resolved  # Can be None for optional Auth
                    continue
                elif is_depends or has_dependency_attr:
                    # Handle Depends objects
                    if hasattr(param.default, "dependency"):
                        # Our Depends object has a dependency function
                        dep_func = param.default.dependency
                        if inspect.iscoroutinefunction(dep_func):
                            result = await dep_func()
                        elif inspect.isasyncgenfunction(dep_func):
                            # Handle async generators (like get_database_session)
                            gen = dep_func()
                            result = await gen.__anext__()
                            # Store generator for cleanup later if needed
                            # For now, we'll just get the value
                        else:
                            result = dep_func()
                        kwargs[param_name] = result
                    else:
                        # Unknown Depends format, use param.default
                        kwargs[param_name] = param.default
                    continue
                else:
                    # Regular default value
                    kwargs[param_name] = param.default
                    continue

            # BackgroundTasks injection
            if param_type.__name__ == "BackgroundTasks" or (
                hasattr(param_type, "__module__")
                and param_type.__module__ == "zenith.background"
                and param_type.__name__ == "BackgroundTasks"
            ):
                from zenith.tasks.background import BackgroundTasks

                kwargs[param_name] = BackgroundTasks()
                continue

            # Pydantic models (request body)
            if (
                inspect.isclass(param_type)
                and issubclass(param_type, BaseModel)
                and request.method in _POST_METHODS
            ):
                body = await self._parse_json_body(request)
                kwargs[param_name] = param_type.model_validate(body)
                continue

            # Rails-like dict parameter for request body (simplified DX)
            if param_type is dict and request.method in _POST_METHODS:
                body = await self._parse_json_body(request)
                if not isinstance(body, dict):
                    raise ValidationException(
                        "Request body must be a JSON object for dict parameters"
                    )
                kwargs[param_name] = body
                continue

        return kwargs

    def _convert_path_param(self, value: str, param_type: type, param_name: str) -> Any:
        """Convert path parameter to the expected type.

        Raises ValidationException for invalid values (returns 400, not 500).
        """
        try:
            if param_type is int:
                return int(value)
            elif param_type is float:
                return float(value)
            return value
        except (ValueError, TypeError) as e:
            raise ValidationException(
                f"Invalid path parameter '{param_name}': expected {param_type.__name__}, got '{value}'"
            ) from e

    def _convert_query_param(
        self, value: str, param_type: type, param_name: str
    ) -> Any:
        """Convert query parameter to the expected type.

        Raises ValidationException for invalid values (returns 400, not 500).
        """
        try:
            if param_type is int:
                return int(value)
            elif param_type is float:
                return float(value)
            elif param_type is bool:
                return value.lower() in ("true", "1", "yes")
            return value
        except (ValueError, TypeError) as e:
            raise ValidationException(
                f"Invalid query parameter '{param_name}': expected {param_type.__name__}, got '{value}'"
            ) from e

    async def _parse_json_body(self, request: Request) -> dict:
        """Parse JSON body from request with proper error handling."""
        body_bytes = await request.body()
        try:
            # Use pre-checked decoder (orjson or json, determined at module load)
            return _json_loads(body_bytes)
        except Exception as e:
            if (
                "JSONDecodeError" in type(e).__name__
                or "decode" in str(type(e)).lower()
            ):
                raise ValidationException(f"Invalid JSON in request body: {e!s}") from e
            raise ValidationException(f"Failed to parse request body: {e!s}") from e
