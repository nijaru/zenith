"""
Response processing and content negotiation.

Handles response formatting, content negotiation, template rendering,
and other response-related concerns.
"""

from typing import Any

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

from zenith.web.responses import OptimizedJSONResponse


class ResponseProcessor:
    """
    Processes handler responses with content negotiation and formatting.

    Responsibilities:
    - Content negotiation (JSON vs HTML)
    - Template rendering
    - Response serialization
    - Error response formatting
    """

    async def process_response(
        self, result: Any, request: Request, route_spec, background_tasks=None
    ) -> Response:
        """Process handler result into appropriate Response."""
        from zenith.core.routing.specs import RouteSpec

        # Get handler from route spec
        handler = (
            route_spec.handler if isinstance(route_spec, RouteSpec) else route_spec
        )

        # If already a Response, add background tasks if needed
        if isinstance(result, Response):
            if background_tasks:
                result.background = background_tasks._tasks
            return result

        # Check if route has a specific response_class configured
        if isinstance(route_spec, RouteSpec) and route_spec.response_class:
            # Use the specified response class with background tasks
            response = route_spec.response_class(result)
            if background_tasks:
                response.background = background_tasks._tasks
            return response

        # Check for content negotiation decorator
        wants_html = self._should_render_html(request, handler)

        # Handle template rendering
        if self._should_use_template(handler, wants_html):
            response = await self._render_template(result, request, handler)
            if background_tasks:
                response.background = background_tasks._tasks
            return response

        # Default to JSON response with background tasks
        response = self._create_json_response(result)
        if background_tasks:
            response.background = background_tasks._tasks
        return response

    def _should_render_html(self, request: Request, handler) -> bool:
        """Determine if client wants HTML response."""
        if not hasattr(handler, "_zenith_negotiate"):
            return False

        accept_header = request.headers.get("accept", "")
        return "text/html" in accept_header and (
            accept_header.find("text/html") < accept_header.find("application/json")
            or "application/json" not in accept_header
        )

    def _should_use_template(self, handler, wants_html: bool) -> bool:
        """Check if we should render a template."""
        # Template decorator without negotiation
        if hasattr(handler, "_zenith_template") and not hasattr(
            handler, "_zenith_negotiate"
        ):
            return True

        # Content negotiation wanting HTML with template available
        return (
            hasattr(handler, "_zenith_negotiate")
            and wants_html
            and hasattr(handler, "_zenith_template")
        )

    async def _render_template(
        self, result: Any, request: Request, handler
    ) -> Response:
        """Render template response."""
        from starlette.templating import Jinja2Templates

        templates = Jinja2Templates(directory="templates")

        # Prepare template context
        context = {"request": request}
        if isinstance(result, dict):
            context.update(result)
        elif isinstance(result, BaseModel):
            context.update(result.model_dump())
        else:
            context["data"] = result

        # Add any template kwargs from decorator
        if hasattr(handler, "_zenith_template_kwargs"):
            context.update(handler._zenith_template_kwargs)

        return templates.TemplateResponse(handler._zenith_template, context)

    def _create_json_response(self, result: Any) -> OptimizedJSONResponse:
        """Create high-performance JSON response from handler result."""
        status_code = 200
        content = result

        # Handle tuple returns with (content, status_code)
        if isinstance(result, tuple) and len(result) == 2:
            content, status_code = result

        # Process content based on type
        if isinstance(content, BaseModel):
            content = content.model_dump()
        elif isinstance(content, list):
            # Handle list of BaseModel objects
            if content and isinstance(content[0], BaseModel):
                content = [item.model_dump() for item in content]
        elif isinstance(content, dict):
            pass  # Keep as-is
        elif content is None:
            # Wrap None values for consistent API responses
            content = {"result": None}
        elif isinstance(content, (str, int, float, bool)):
            # Wrap primitive values for consistent API responses
            content = {"result": content}
        else:
            # Wrap complex values in a result object
            content = {"result": content}

        return OptimizedJSONResponse(content=content, status_code=status_code)
