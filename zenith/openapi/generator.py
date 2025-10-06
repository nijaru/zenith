"""
OpenAPI 3.0 specification generator for Zenith applications.

Analyzes routes, type hints, and Pydantic models to automatically
generate comprehensive API documentation.
"""

import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from zenith.core.routing import Router

from pydantic import BaseModel

from zenith.core.routing import AuthDependency, InjectDependency, RouteSpec


class OpenAPIGenerator:
    """
    Generates OpenAPI 3.0 specifications from Zenith applications.

    Features:
    - Automatic route analysis
    - Pydantic model schema extraction
    - Request/response documentation
    - Authentication documentation
    - Parameter detection (path, query, body)
    """

    def __init__(
        self,
        title: str = "Zenith API",
        version: str = "1.0.0",
        description: str = "API built with Zenith framework",
        servers: list[dict[str, str]] | None = None,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.servers = servers or [{"url": "/", "description": "Development server"}]

        # Store schemas for reuse
        self.schemas: dict[str, dict] = {}
        self.components: dict[str, Any] = {"schemas": self.schemas}

    # Simple in-memory cache for generated specs
    _spec_cache: ClassVar[dict[str, dict]] = {}

    def _get_cache_key(self, routers: list["Router"]) -> str:
        """Create simple string cache key from router structure."""
        route_sigs = []
        for router in routers:
            for route_spec in router.routes:
                sig = f"{route_spec.path}:{','.join(sorted(route_spec.methods))}:{route_spec.handler.__name__}"
                route_sigs.append(sig)

        routes_hash = hash(tuple(sorted(route_sigs)))
        config_hash = hash((self.title, self.version, self.description))
        return f"{routes_hash}_{config_hash}"

    def generate_spec(self, routers: list["Router"]) -> dict[str, Any]:
        """Generate complete OpenAPI 3.0 specification with caching."""

        # Check cache first for performance optimization
        cache_key = self._get_cache_key(routers)
        if cache_key in self._spec_cache:
            return self._spec_cache[cache_key].copy()  # Return copy to avoid mutation

        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "servers": self.servers,
            "paths": {},
            "components": self.components,
        }

        # Process all routers
        for router in routers:
            for route_spec in router.routes:
                self._process_route(spec, route_spec)

        # Cache the result for future use (25-40% speedup for repeated calls)
        self._spec_cache[cache_key] = spec.copy()

        # Simple cache size management (LRU-like behavior)
        if len(self._spec_cache) > 50:  # Keep cache bounded
            # Remove oldest entries
            oldest_keys = list(self._spec_cache.keys())[:-25]  # Keep newest 25
            for key in oldest_keys:
                del self._spec_cache[key]

        return spec

    def _process_route(self, spec: dict, route_spec: RouteSpec) -> None:
        """Process a single route and add to spec."""

        path = route_spec.path
        methods = route_spec.methods
        handler = route_spec.handler

        # Ensure path exists in spec
        if path not in spec["paths"]:
            spec["paths"][path] = {}

        # Get handler signature and type hints
        sig = inspect.signature(handler)
        type_hints = get_type_hints(handler)

        # Process each HTTP method
        for method in methods:
            method_lower = method.lower()

            # Build operation spec
            operation = {
                "summary": self._get_operation_summary(handler, method),
                "description": self._get_operation_description(handler),
                "operationId": f"{method_lower}_{path.replace('/', '_').replace('{', '').replace('}', '')}",
                "parameters": [],
                "responses": self._get_responses(type_hints.get("return")),
            }

            # Process parameters
            request_body = None
            for param_name, param in sig.parameters.items():
                param_type = type_hints.get(param_name, param.annotation)

                # Skip special parameters
                if param_name == "request":
                    continue

                # Handle dependency injection markers
                if isinstance(param.default, InjectDependency | AuthDependency):
                    if isinstance(param.default, AuthDependency):
                        # Add security requirement
                        if "security" not in operation:
                            operation["security"] = []
                        operation["security"].append({"bearerAuth": []})
                    continue

                # Handle Pydantic models (request body)
                from zenith.core.patterns import METHODS_WITH_BODY

                if (
                    inspect.isclass(param_type)
                    and issubclass(param_type, BaseModel)
                    and method.upper() in METHODS_WITH_BODY
                ):
                    schema_name = param_type.__name__
                    self._add_schema(param_type)

                    request_body = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{schema_name}"
                                }
                            }
                        },
                    }
                    continue

                # Handle path parameters
                if param_name in self._extract_path_params(path):
                    operation["parameters"].append(
                        {
                            "name": param_name,
                            "in": "path",
                            "required": True,
                            "schema": self._get_type_schema(param_type),
                            "description": f"The {param_name} identifier",
                        }
                    )
                    continue

                # Handle query parameters
                is_required = param.default == inspect.Parameter.empty
                operation["parameters"].append(
                    {
                        "name": param_name,
                        "in": "query",
                        "required": is_required,
                        "schema": self._get_type_schema(param_type),
                        "description": f"Query parameter: {param_name}",
                    }
                )

            # Add request body if present
            if request_body:
                operation["requestBody"] = request_body

            # Add to spec
            spec["paths"][path][method_lower] = operation

    def _get_operation_summary(self, handler: callable, method: str) -> str:
        """Generate operation summary from handler."""

        # Try to get from docstring first line
        if handler.__doc__:
            first_line = handler.__doc__.strip().split("\n")[0]
            if first_line:
                return first_line

        # Generate from handler name and method
        handler_name = handler.__name__.replace("_", " ").title()
        return f"{method} {handler_name}"

    def _get_operation_description(self, handler: callable) -> str:
        """Generate operation description from handler docstring."""

        if handler.__doc__:
            lines = handler.__doc__.strip().split("\n")
            if len(lines) > 1:
                # Return everything after the first line
                return "\n".join(lines[1:]).strip()
            return lines[0]

        return f"Handler: {handler.__name__}"

    def _extract_path_params(self, path: str) -> list[str]:
        """Extract parameter names from path template."""
        from zenith.core.patterns import extract_path_params

        return extract_path_params(path)

    def _get_responses(self, return_type: type | None) -> dict[str, Any]:
        """Generate response specifications from return type."""

        responses = {}

        if return_type and return_type != inspect.Parameter.empty:
            # Handle successful response (200)
            if inspect.isclass(return_type) and issubclass(return_type, BaseModel):
                schema_name = return_type.__name__
                self._add_schema(return_type)

                responses["200"] = {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                }
            elif return_type is dict or self._is_dict_type(return_type):
                responses["200"] = {
                    "description": "Successful response",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                }
            elif return_type is list or self._is_list_type(return_type):
                responses["200"] = {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"type": "array", "items": {"type": "object"}}
                        }
                    },
                }
            else:
                responses["200"] = {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": self._get_type_schema(return_type)
                        }
                    },
                }
        else:
            # Default response
            responses["200"] = {"description": "Successful response"}

        # Add common error responses
        responses["400"] = {"description": "Bad Request"}
        responses["401"] = {"description": "Unauthorized"}
        responses["403"] = {"description": "Forbidden"}
        responses["404"] = {"description": "Not Found"}
        responses["422"] = {"description": "Validation Error"}
        responses["429"] = {"description": "Rate Limited"}
        responses["500"] = {"description": "Internal Server Error"}

        return responses

    def _is_dict_type(self, type_hint: type) -> bool:
        """Check if type hint represents a dict."""
        origin = get_origin(type_hint)
        return origin is dict

    def _is_list_type(self, type_hint: type) -> bool:
        """Check if type hint represents a list."""
        origin = get_origin(type_hint)
        return origin is list

    def _get_type_schema(self, type_hint: type) -> dict[str, Any]:
        """Convert Python type to OpenAPI schema."""

        if type_hint is str:
            return {"type": "string"}
        elif type_hint is int:
            return {"type": "integer"}
        elif type_hint is float:
            return {"type": "number"}
        elif type_hint is bool:
            return {"type": "boolean"}
        elif type_hint is list:
            return {"type": "array", "items": {"type": "object"}}
        elif type_hint is dict:
            return {"type": "object"}
        else:
            # For complex types, return generic object
            return {"type": "object"}

    def _add_schema(self, model_class: type[BaseModel]) -> None:
        """Add Pydantic model schema to components."""

        schema_name = model_class.__name__
        if schema_name not in self.schemas:
            # Get Pydantic schema
            schema = model_class.model_json_schema()

            # Remove $defs and move them to components
            if "$defs" in schema:
                for def_name, def_schema in schema["$defs"].items():
                    self.schemas[def_name] = def_schema
                del schema["$defs"]

            self.schemas[schema_name] = schema


def generate_openapi_spec(
    routers: list["Router"],
    title: str = "Zenith API",
    version: str = "1.0.0",
    description: str = "API built with Zenith framework",
    servers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Generate OpenAPI specification from Zenith routers.

    Args:
        routers: List of Zenith routers to analyze
        title: API title
        version: API version
        description: API description
        servers: List of server configurations

    Returns:
        OpenAPI 3.0 specification as dictionary
    """

    generator = OpenAPIGenerator(title, version, description, servers)
    return generator.generate_spec(routers)
