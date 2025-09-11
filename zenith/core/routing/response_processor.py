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
        self, 
        result: Any, 
        request: Request, 
        handler
    ) -> Response:
        """Process handler result into appropriate Response."""
        
        # If already a Response, return as-is
        if isinstance(result, Response):
            return result

        # Check for content negotiation decorator
        wants_html = self._should_render_html(request, handler)

        # Handle template rendering
        if self._should_use_template(handler, wants_html):
            return await self._render_template(result, request, handler)

        # Default to JSON response
        return self._create_json_response(result)

    def _should_render_html(self, request: Request, handler) -> bool:
        """Determine if client wants HTML response."""
        if not hasattr(handler, '_zenith_negotiate'):
            return False

        accept_header = request.headers.get("accept", "")
        return (
            "text/html" in accept_header and
            (
                accept_header.find("text/html") < accept_header.find("application/json")
                or "application/json" not in accept_header
            )
        )

    def _should_use_template(self, handler, wants_html: bool) -> bool:
        """Check if we should render a template."""
        # Template decorator without negotiation
        if hasattr(handler, '_zenith_template') and not hasattr(handler, '_zenith_negotiate'):
            return True
        
        # Content negotiation wanting HTML with template available
        return (
            hasattr(handler, '_zenith_negotiate') and 
            wants_html and 
            hasattr(handler, '_zenith_template')
        )

    async def _render_template(self, result: Any, request: Request, handler) -> Response:
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
        if hasattr(handler, '_zenith_template_kwargs'):
            context.update(handler._zenith_template_kwargs)

        return templates.TemplateResponse(handler._zenith_template, context)

    def _create_json_response(self, result: Any) -> OptimizedJSONResponse:
        """Create high-performance JSON response from handler result."""
        if isinstance(result, BaseModel):
            content = result.model_dump()
        elif isinstance(result, list):
            # Handle list of BaseModel objects
            if result and isinstance(result[0], BaseModel):
                content = [item.model_dump() for item in result]
            else:
                content = result
        elif isinstance(result, dict):
            content = result
        else:
            # Wrap simple values in a result object
            content = {"result": result}

        return OptimizedJSONResponse(content=content)