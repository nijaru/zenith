"""
Route specifications and HTTP method definitions.

Defines the structure and types used for route definitions.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from starlette.middleware import Middleware


class HTTPMethod(Enum):
    """HTTP methods supported by the router."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"


@dataclass(slots=True)
class RouteSpec:
    """Route specification containing all route information."""

    path: str
    handler: Callable[..., Any]
    methods: list[str]
    name: str | None = None
    middleware: list[Middleware] | None = None
    include_in_schema: bool = True
    response_model: type | None = None
    response_class: type | None = (
        None  # Custom response class (HTMLResponse, PlainTextResponse, etc.)
    )
    status_code: int = 200
    tags: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    response_description: str = "Successful Response"
    dependencies: list[Any] | None = None
    # For WebSocket routes that need special handling
    raw_handler: Callable[..., Any] | None = None
