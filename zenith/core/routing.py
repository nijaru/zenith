"""
FastAPI-style routing with type-based dependency injection.

Combines the best of FastAPI's decorator patterns with Phoenix contexts
and Rails conventions for maximum developer experience.
"""

import asyncio
import inspect
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)
from functools import wraps
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.routing import Route, Router as StarletteRouter
from starlette.middleware import Middleware

from zenith.core.context import Context


T = TypeVar("T")
HandlerFunc = Callable[..., Awaitable[Any]]


class HTTPMethod(Enum):
    """HTTP methods for routing."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class RouteSpec:
    """Specification for a route."""

    path: str
    methods: List[str]
    handler: HandlerFunc
    name: Optional[str] = None
    middleware: List[Middleware] = None


class ContextDependency:
    """Dependency marker for auto-injecting contexts."""

    def __init__(self, context_class: Type[Context]):
        self.context_class = context_class


class AuthDependency:
    """Dependency marker for authentication."""

    def __init__(self, required: bool = True, scopes: List[str] = None):
        self.required = required
        self.scopes = scopes or []


class FileUploadDependency:
    """Dependency marker for file upload handling."""

    def __init__(self, field_name: str = "file", config=None):
        self.field_name = field_name
        self.config = config


def Context(context_class: Optional[Type] = None):
    """Dependency injection marker for contexts."""
    return ContextDependency(context_class)


def Auth(required: bool = True, scopes: List[str] = None):
    """Dependency injection marker for authentication."""
    return AuthDependency(required, scopes)


def File(field_name: str = "file", config=None):
    """Dependency injection marker for file uploads."""
    return FileUploadDependency(field_name, config)


class Router:
    """
    Modern router with FastAPI-style decorators and type-based dependency injection.

    Features:
    - Automatic request/response validation via Pydantic
    - Type-based dependency injection
    - Context auto-injection
    - Authentication helpers
    - Middleware support
    """

    def __init__(self, prefix: str = "", middleware: List[Middleware] = None):
        self.prefix = prefix
        self.middleware = middleware or []
        self.routes: List[RouteSpec] = []
        self._app = None  # Will be set by Application

    def route(
        self,
        path: str,
        methods: List[str],
        name: Optional[str] = None,
        middleware: List[Middleware] = None,
    ):
        """Generic route decorator."""

        def decorator(handler: HandlerFunc) -> HandlerFunc:
            route_spec = RouteSpec(
                path=self.prefix + path,
                methods=methods,
                handler=handler,
                name=name,
                middleware=middleware,
            )
            self.routes.append(route_spec)
            return handler

        return decorator

    def get(self, path: str, **kwargs):
        """GET route decorator."""
        return self.route(path, ["GET"], **kwargs)

    def post(self, path: str, **kwargs):
        """POST route decorator."""
        return self.route(path, ["POST"], **kwargs)

    def put(self, path: str, **kwargs):
        """PUT route decorator."""
        return self.route(path, ["PUT"], **kwargs)

    def patch(self, path: str, **kwargs):
        """PATCH route decorator."""
        return self.route(path, ["PATCH"], **kwargs)

    def delete(self, path: str, **kwargs):
        """DELETE route decorator."""
        return self.route(path, ["DELETE"], **kwargs)

    async def _call_handler(self, request: Request, handler: HandlerFunc) -> Response:
        """
        Call handler with dependency injection.

        Analyzes the handler signature and injects dependencies:
        - Request object
        - Path/query parameters
        - Pydantic models for request body
        - Context instances
        - Authentication
        """
        try:
            # Get handler signature and type hints
            sig = inspect.signature(handler)
            type_hints = get_type_hints(handler)

            # Prepare arguments for handler
            kwargs = {}

            # Process each parameter
            for param_name, param in sig.parameters.items():
                param_type = type_hints.get(param_name, param.annotation)

                if param_name == "request":
                    kwargs[param_name] = request
                    continue

                # Handle path parameters
                if param_name in request.path_params:
                    value = request.path_params[param_name]
                    # Convert to appropriate type
                    if param_type == int:
                        kwargs[param_name] = int(value)
                    elif param_type == float:
                        kwargs[param_name] = float(value)
                    else:
                        kwargs[param_name] = value
                    continue

                # Handle query parameters
                if param_name in request.query_params:
                    value = request.query_params[param_name]
                    if param_type == int:
                        kwargs[param_name] = int(value)
                    elif param_type == float:
                        kwargs[param_name] = float(value)
                    elif param_type == bool:
                        kwargs[param_name] = value.lower() in ("true", "1", "yes")
                    else:
                        kwargs[param_name] = value
                    continue

                # Handle default values and dependency injection
                if param.default != inspect.Parameter.empty:
                    if isinstance(param.default, ContextDependency):
                        # Inject context
                        context_class = param.default.context_class or param_type
                        context = await self._app.get_context(
                            context_class.__name__.lower()
                        )
                        kwargs[param_name] = context
                        continue

                    elif isinstance(param.default, AuthDependency):
                        # Inject current user via auth middleware
                        from zenith.middleware.auth import (
                            get_current_user,
                            require_scopes,
                        )

                        user = get_current_user(
                            request, required=param.default.required
                        )

                        # Check required scopes if user is authenticated
                        if user and param.default.scopes:
                            require_scopes(request, param.default.scopes)

                        kwargs[param_name] = user
                        continue

                    elif isinstance(param.default, FileUploadDependency):
                        # Inject uploaded files
                        from zenith.web.files import handle_file_upload

                        uploaded_files = await handle_file_upload(
                            request,
                            field_name=param.default.field_name,
                            config=param.default.config,
                        )
                        kwargs[param_name] = uploaded_files
                        continue

                    else:
                        kwargs[param_name] = param.default
                        continue

                # Handle Pydantic models (request body)
                if (
                    inspect.isclass(param_type)
                    and issubclass(param_type, BaseModel)
                    and request.method in ["POST", "PUT", "PATCH"]
                ):
                    try:
                        body = await request.json()
                        model_instance = param_type.model_validate(body)
                        kwargs[param_name] = model_instance
                    except ValidationError as e:
                        return JSONResponse(
                            {"error": "Validation failed", "details": e.errors()},
                            status_code=422,
                        )
                    continue

            # Call handler with injected dependencies
            result = await handler(**kwargs)

            # Validate response against return type hint if available
            return_type = type_hints.get("return", None)
            if return_type and return_type != inspect.Parameter.empty:
                result = self._validate_response(result, return_type)

            # Handle response
            if isinstance(result, Response):
                return result
            elif isinstance(result, BaseModel):
                return JSONResponse(result.model_dump())
            elif isinstance(result, (dict, list)):
                return JSONResponse(result)
            else:
                return JSONResponse({"result": result})

        except Exception as e:
            # Re-raise exception to be handled by ExceptionHandlerMiddleware
            raise e

    def _validate_response(self, result: Any, return_type: Type) -> Any:
        """Validate response against return type hint."""

        # Handle Optional types (Union[T, None])
        if hasattr(return_type, "__origin__") and return_type.__origin__ is Union:
            # Check if it's Optional (Union[T, None])
            args = return_type.__args__
            if len(args) == 2 and type(None) in args:
                # This is Optional[T], get the non-None type
                return_type = args[0] if args[1] is type(None) else args[1]
                if result is None:
                    return result  # None is valid for Optional types

        # Handle List types
        if hasattr(return_type, "__origin__") and return_type.__origin__ is list:
            if not isinstance(result, list):
                from zenith.middleware.exceptions import ValidationException

                raise ValidationException(
                    f"Expected list response, got {type(result).__name__}"
                )
            return result

        # Handle Dict types
        if hasattr(return_type, "__origin__") and return_type.__origin__ is dict:
            if not isinstance(result, dict):
                from zenith.middleware.exceptions import ValidationException

                raise ValidationException(
                    f"Expected dict response, got {type(result).__name__}"
                )
            return result

        # Handle Pydantic models
        if inspect.isclass(return_type) and issubclass(return_type, BaseModel):
            if isinstance(result, return_type):
                return result  # Already correct type
            elif isinstance(result, dict):
                # Try to create model from dict
                try:
                    return return_type.model_validate(result)
                except ValidationError as e:
                    from zenith.middleware.exceptions import ValidationException

                    raise ValidationException(
                        f"Response validation failed for {return_type.__name__}",
                        details={"validation_errors": e.errors()},
                    )
            else:
                from zenith.middleware.exceptions import ValidationException

                raise ValidationException(
                    f"Expected {return_type.__name__} or dict, got {type(result).__name__}"
                )

        # For basic types, let Python handle it naturally
        return result

    def build_starlette_router(self) -> StarletteRouter:
        """Convert our routes to Starlette router."""
        starlette_routes = []

        for route_spec in self.routes:

            def create_endpoint(handler):
                async def endpoint(request: Request):
                    return await self._call_handler(request, handler)

                return endpoint

            starlette_route = Route(
                route_spec.path,
                endpoint=create_endpoint(route_spec.handler),
                methods=route_spec.methods,
                name=route_spec.name,
            )
            starlette_routes.append(starlette_route)

        return StarletteRouter(routes=starlette_routes, middleware=self.middleware)


class LiveViewRouter(Router):
    """Router for Phoenix-style LiveView routes."""

    def live(self, path: str, **kwargs):
        """LiveView route decorator."""
        return self.route(path, ["GET", "POST"], **kwargs)


# Global router instance for app-level routes
app_router = Router()

# Convenience decorators for the global router
get = app_router.get
post = app_router.post
put = app_router.put
patch = app_router.patch
delete = app_router.delete
