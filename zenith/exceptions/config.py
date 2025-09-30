"""
Configuration-related exceptions with helpful error messages.

Provides detailed error messages for common configuration mistakes
to improve developer experience.
"""

from typing import Any


class ZenithConfigError(Exception):
    """Base exception for configuration errors."""

    def __init__(self, message: str, suggestions: list[str] | None = None):
        self.suggestions = suggestions or []
        full_message = message
        if self.suggestions:
            full_message += "\n\nSuggestions:\n"
            for suggestion in self.suggestions:
                full_message += f"  • {suggestion}\n"
        super().__init__(full_message)


class MiddlewareConfigError(ZenithConfigError):
    """Exception for middleware configuration errors."""

    @classmethod
    def invalid_parameter(
        cls,
        middleware_name: str,
        param_name: str,
        valid_params: list[str] | None = None,
        example: str | None = None,
    ):
        """Create error for invalid middleware parameter."""
        message = f"{middleware_name} does not accept '{param_name}'."

        suggestions = []
        if valid_params:
            suggestions.append(f"Available options: {', '.join(valid_params)}")
        if example:
            suggestions.append(f"Example: {example}")

        return cls(message, suggestions)

    @classmethod
    def missing_required(
        cls, middleware_name: str, param_name: str, description: str | None = None
    ):
        """Create error for missing required parameter."""
        message = f"{middleware_name} requires '{param_name}' parameter."

        suggestions = []
        if description:
            suggestions.append(description)

        return cls(message, suggestions)

    @classmethod
    def invalid_type(
        cls,
        middleware_name: str,
        param_name: str,
        expected_type: str,
        actual_value: Any,
        example: str | None = None,
    ):
        """Create error for wrong parameter type."""
        actual_type = type(actual_value).__name__
        message = (
            f"{middleware_name}: '{param_name}' must be {expected_type}, "
            f"got {actual_type} instead."
        )

        suggestions = []
        if example:
            suggestions.append(f"Example: {example}")

        return cls(message, suggestions)


class ServiceConfigError(ZenithConfigError):
    """Exception for service configuration errors."""

    @classmethod
    def not_registered(cls, service_name: str):
        """Create error for unregistered service."""
        return cls(
            f"Service '{service_name}' is not registered.",
            [
                f"Register the service: app.services.register('{service_name}', {service_name})",
                "Or use @app.service decorator on the service class",
                "Check that the service extends zenith.Service base class",
            ],
        )

    @classmethod
    def invalid_injection(cls, service_name: str):
        """Create error for invalid service injection."""
        return cls(
            f"Cannot inject '{service_name}' - not a valid Service class.",
            [
                "Ensure the class extends zenith.Service",
                "Use Inject() for service injection: service: MyService = Inject()",
                "For database sessions, use Session dependency instead",
            ],
        )


class DatabaseConfigError(ZenithConfigError):
    """Exception for database configuration errors."""

    @classmethod
    def async_loop_error(cls):
        """Create error for async event loop binding issue."""
        return cls(
            "Database operation failed: Future attached to different event loop.",
            [
                "Use RequestScoped or Session for proper async context isolation:",
                "  from zenith import Session",
                "  async def get_db():",
                "      async with SessionLocal() as session:",
                "          yield session",
                "  @app.get('/items')",
                "  async def get_items(session: AsyncSession = Session):",
                "      ...",
                "Avoid creating database engines at module level",
                "See examples/16-async-database-scoped.py for full example",
            ],
        )

    @classmethod
    def invalid_url(cls, url: str, error: str):
        """Create error for invalid database URL."""
        return cls(
            f"Invalid database URL: {url}",
            [
                f"Error: {error}",
                "Format: dialect+driver://username:password@host:port/database",
                "Examples:",
                "  PostgreSQL: postgresql+asyncpg://user:pass@localhost/dbname",
                "  MySQL: mysql+aiomysql://user:pass@localhost/dbname",
                "  SQLite: sqlite+aiosqlite:///path/to/db.sqlite",
            ],
        )


class RouteConfigError(ZenithConfigError):
    """Exception for route configuration errors."""

    @classmethod
    def duplicate_route(cls, method: str, path: str):
        """Create error for duplicate route registration."""
        return cls(
            f"Route already exists: {method} {path}",
            [
                "Check for duplicate route decorators",
                "Use different paths or HTTP methods",
                "Consider using path parameters: /items/{item_id}",
            ],
        )

    @classmethod
    def invalid_response_model(cls, model_name: str, error: str):
        """Create error for invalid response model."""
        return cls(
            f"Invalid response model '{model_name}': {error}",
            [
                "Ensure the model is a valid Pydantic model",
                "Check that all fields have proper type hints",
                "For lists, use response_model=list[ItemModel]",
            ],
        )
