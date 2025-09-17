"""
OpenAPI specification generator for Zenith applications.

Provides automatic OpenAPI/Swagger documentation generation from routes.
"""

import inspect
from typing import Any, Dict, List
from starlette.routing import Route
from pydantic import BaseModel


def generate_openapi_spec(
    routes: List[Route],
    title: str = "Zenith API",
    version: str = "1.0.0",
    description: str = "API documentation",
    servers: List[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Generate OpenAPI 3.0 specification from Starlette routes.

    Args:
        routes: List of Starlette Route objects
        title: API title
        version: API version
        description: API description
        servers: List of server configurations

    Returns:
        OpenAPI specification as a dictionary
    """
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        },
    }

    if servers:
        spec["servers"] = servers

    # Process each route
    for route in routes:
        if not isinstance(route, Route):
            continue

        # Skip internal routes
        if route.path.startswith("/_") or route.path in ["/openapi.json", "/docs", "/redoc"]:
            continue

        # Get path with OpenAPI parameter format
        path = _convert_path_params(route.path)

        if path not in spec["paths"]:
            spec["paths"][path] = {}

        # Process each HTTP method
        for method in route.methods:
            method_lower = method.lower()
            endpoint = route.endpoint

            # Get operation info from function
            operation = {
                "summary": _get_summary(endpoint),
                "description": _get_description(endpoint),
                "operationId": f"{method_lower}_{route.name or endpoint.__name__}",
                "responses": _get_responses(endpoint),
            }

            # Add parameters
            params = _get_parameters(endpoint, route.path)
            if params:
                operation["parameters"] = params

            # Add request body if needed
            if method in ["POST", "PUT", "PATCH"]:
                request_body = _get_request_body(endpoint)
                if request_body:
                    operation["requestBody"] = request_body

            # Add security if endpoint requires auth
            if _requires_auth(endpoint):
                operation["security"] = [{"bearerAuth": []}]

            # Add tags based on route path
            tags = _get_tags(route.path)
            if tags:
                operation["tags"] = tags

            spec["paths"][path][method_lower] = operation

    return spec


def _convert_path_params(path: str) -> str:
    """Convert Starlette path params to OpenAPI format."""
    # Convert {param:type} to {param}
    import re
    return re.sub(r"\{([^}:]+):[^}]+\}", r"{\1}", path)


def _get_summary(endpoint) -> str:
    """Extract summary from endpoint docstring."""
    if endpoint.__doc__:
        lines = endpoint.__doc__.strip().split("\n")
        return lines[0].strip() if lines else ""
    return endpoint.__name__.replace("_", " ").title()


def _get_description(endpoint) -> str:
    """Extract description from endpoint docstring."""
    if endpoint.__doc__:
        lines = endpoint.__doc__.strip().split("\n")
        if len(lines) > 1:
            # Skip first line (summary) and join the rest
            return "\n".join(line.strip() for line in lines[1:] if line.strip())
    return ""


def _get_parameters(endpoint, path: str) -> List[Dict[str, Any]]:
    """Extract parameters from endpoint signature."""
    params = []
    sig = inspect.signature(endpoint)

    # Add path parameters
    import re
    path_params = re.findall(r"\{([^}:]+)(?::[^}]+)?\}", path)
    for param_name in path_params:
        param_info = {
            "name": param_name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }

        # Check if parameter is in signature for type info
        if param_name in sig.parameters:
            param = sig.parameters[param_name]
            if param.annotation != inspect.Parameter.empty:
                param_info["schema"] = _get_schema_from_type(param.annotation)

        params.append(param_info)

    # Add query parameters
    for name, param in sig.parameters.items():
        # Skip special parameters
        if name in ["self", "request", "response", "background_tasks", "db", "user", "current_user"]:
            continue

        # Skip path parameters we already added
        if name in path_params:
            continue

        # Skip if it's a Pydantic model (request body)
        if param.annotation != inspect.Parameter.empty:
            if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
                continue

        # Add as query parameter
        param_info = {
            "name": name,
            "in": "query",
            "required": param.default == inspect.Parameter.empty,
            "schema": _get_schema_from_type(param.annotation),
        }

        if param.default != inspect.Parameter.empty:
            param_info["schema"]["default"] = param.default

        params.append(param_info)

    return params


def _get_request_body(endpoint) -> Dict[str, Any] | None:
    """Extract request body schema from endpoint signature."""
    sig = inspect.signature(endpoint)

    for name, param in sig.parameters.items():
        if param.annotation != inspect.Parameter.empty:
            # Check if it's a Pydantic model
            if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
                return {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": _get_pydantic_schema(param.annotation)
                        }
                    }
                }

    return None


def _get_responses(endpoint) -> Dict[str, Any]:
    """Generate response schemas from endpoint."""
    responses = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object"}
                }
            }
        }
    }

    # Check return type annotation
    sig = inspect.signature(endpoint)
    if sig.return_annotation != inspect.Parameter.empty:
        return_type = sig.return_annotation
        # Handle Optional, Union, etc.
        if hasattr(return_type, "__origin__"):
            # Extract the actual type
            if return_type.__origin__ is list:
                responses["200"]["content"]["application/json"]["schema"] = {
                    "type": "array",
                    "items": _get_schema_from_type(return_type.__args__[0])
                }
            else:
                responses["200"]["content"]["application/json"]["schema"] = _get_schema_from_type(return_type)
        elif inspect.isclass(return_type) and issubclass(return_type, BaseModel):
            responses["200"]["content"]["application/json"]["schema"] = _get_pydantic_schema(return_type)

    # Add common error responses
    if _requires_auth(endpoint):
        responses["401"] = {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string"}
                        }
                    }
                }
            }
        }

    return responses


def _get_schema_from_type(type_hint) -> Dict[str, Any]:
    """Convert Python type hint to OpenAPI schema."""
    if type_hint == inspect.Parameter.empty:
        return {"type": "string"}

    # Handle basic types
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array", "items": {"type": "string"}},
        dict: {"type": "object"},
    }

    if type_hint in type_map:
        return type_map[type_hint]

    # Handle Optional types
    if hasattr(type_hint, "__origin__"):
        origin = type_hint.__origin__
        if origin is list:
            return {
                "type": "array",
                "items": _get_schema_from_type(type_hint.__args__[0]) if type_hint.__args__ else {"type": "string"}
            }
        elif origin is dict:
            return {"type": "object"}

    # Default to string
    return {"type": "string"}


def _get_pydantic_schema(model: type[BaseModel]) -> Dict[str, Any]:
    """Generate OpenAPI schema from Pydantic model."""
    try:
        # Try Pydantic v2 first
        return model.model_json_schema()
    except AttributeError:
        # Fall back to Pydantic v1
        return model.schema()


def _requires_auth(endpoint) -> bool:
    """Check if endpoint requires authentication."""
    # Check function signature for auth parameters
    sig = inspect.signature(endpoint)
    auth_params = ["user", "current_user", "auth"]

    for param_name in sig.parameters:
        if param_name in auth_params:
            return True

    # Check for auth_required decorator
    if hasattr(endpoint, "__wrapped__"):
        # Function has decorators
        return "auth_required" in str(endpoint)

    return False


def _get_tags(path: str) -> List[str]:
    """Generate tags from route path."""
    parts = path.strip("/").split("/")
    if parts and parts[0]:
        # Use first path segment as tag
        tag = parts[0].replace("_", " ").title()
        return [tag]
    return []