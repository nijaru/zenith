"""
Routing utilities and helper functions.

Common functionality used across the routing system.
"""

from typing import Any, Union

from pydantic import ValidationError


def validate_response_type(result: Any, return_type: type) -> Any:
    """Validate response against return type hint."""
    if not return_type or return_type is type(None):
        return result

    # Handle Optional types (T | None)
    if hasattr(return_type, "__origin__") and return_type.__origin__ is Union:
        args = return_type.__args__
        if len(args) == 2 and type(None) in args:
            # This is T | None, get the non-None type
            return_type = args[0] if args[1] is type(None) else args[1]
            if result is None:
                return result  # None is valid for Optional types

    # Handle List types
    if hasattr(return_type, "__origin__") and return_type.__origin__ is list:
        if not isinstance(result, list):
            from zenith.exceptions import ValidationException

            raise ValidationException(
                f"Expected list response, got {type(result).__name__}"
            )
        return result

    # Handle Dict types
    if hasattr(return_type, "__origin__") and return_type.__origin__ is dict:
        if not isinstance(result, dict):
            from zenith.exceptions import ValidationException

            raise ValidationException(
                f"Expected dict response, got {type(result).__name__}"
            )
        return result

    # Handle Pydantic models
    import inspect

    from pydantic import BaseModel

    if inspect.isclass(return_type) and issubclass(return_type, BaseModel):
        if isinstance(result, return_type):
            return result  # Already correct type
        elif isinstance(result, dict):
            # Try to create model from dict
            try:
                return return_type.model_validate(result)
            except ValidationError as e:
                from zenith.exceptions import ValidationException

                raise ValidationException(
                    f"Response validation failed for {return_type.__name__}",
                    details={"validation_errors": e.errors()},
                ) from e
        else:
            from zenith.exceptions import ValidationException

            raise ValidationException(
                f"Expected {return_type.__name__} or dict, got {type(result).__name__}"
            )

    # For basic types, let Python handle it naturally
    return result


def create_route_name(path: str, methods: list[str]) -> str:
    """Generate a route name from path and methods."""
    # Convert /users/{id}/posts -> users_id_posts
    name_parts = [part for part in path.split("/") if part]
    name_parts = [part.replace("{", "").replace("}", "") for part in name_parts]

    # Add method prefix for non-GET routes
    if methods != ["GET"]:
        method_prefix = "_".join(methods).lower()
        return f"{method_prefix}_{'_'.join(name_parts)}"

    return "_".join(name_parts) or "root"


def extract_route_tags(handler) -> list[str]:
    """Extract tags from handler for OpenAPI generation."""
    tags = []

    # Check for explicit tags attribute
    if hasattr(handler, "_zenith_tags"):
        tags.extend(handler._zenith_tags)

    # Infer from module/class name
    if hasattr(handler, "__module__"):
        module_parts = handler.__module__.split(".")
        if len(module_parts) > 1:
            tags.append(module_parts[-1])

    return tags or ["default"]


def normalize_path(path: str) -> str:
    """Normalize route path for consistency."""
    # Ensure path starts with /
    if not path.startswith("/"):
        path = "/" + path

    # Remove trailing slash except for root
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return path
