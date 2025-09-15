"""
Response utilities for Zenith framework.

Provides convenient response helpers for common web application needs.
"""

from pathlib import Path
from typing import Any, Literal

from starlette.responses import (
    FileResponse,
    HTMLResponse,
    Response,
    StreamingResponse,
)
from starlette.responses import (
    RedirectResponse as StarletteRedirect,
)

from zenith.core.json_encoder import _json_dumps

# High-performance JSON handling
try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


class OptimizedJSONResponse(Response):
    """
    High-performance JSON response using orjson for 2-3x faster serialization.
    Falls back to standard json if orjson is not available.
    """

    media_type = "application/json"

    def _json_default(self, obj):
        """Custom JSON encoder for non-standard types."""
        from datetime import date, datetime
        from decimal import Decimal
        from pathlib import Path
        from uuid import UUID

        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, UUID):
            return str(obj)
        elif hasattr(obj, "model_dump"):
            # Pydantic model
            return obj.model_dump()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _make_serializable(self, obj):
        """Recursively make object JSON serializable."""
        from pathlib import Path

        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, "model_dump"):
            return obj.model_dump()
        return obj

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
    ):
        if HAS_ORJSON:
            # Use orjson for high-performance serialization
            # orjson returns bytes, which is perfect for HTTP responses
            try:
                json_bytes = orjson.dumps(
                    content,
                    option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
                    default=self._json_default,
                )
            except TypeError:
                # Fallback for unserializable types
                content = self._make_serializable(content)
                json_bytes = orjson.dumps(
                    content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
                )
            super().__init__(
                content=json_bytes,
                status_code=status_code,
                headers=headers,
                media_type=media_type or self.media_type,
            )
        else:
            # Fallback to standard JSONResponse
            super().__init__(
                content=_json_dumps(content),
                status_code=status_code,
                headers=headers,
                media_type=media_type or self.media_type,
            )


# Convenient response functions


def json_response(
    content: Any,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str = "application/json",
) -> OptimizedJSONResponse:
    """Create a high-performance JSON response with optional headers."""
    return OptimizedJSONResponse(
        content=content, status_code=status_code, headers=headers, media_type=media_type
    )


def success_response(
    data: Any = None, message: str = "Success", status_code: int = 200
) -> OptimizedJSONResponse:
    """Create a standardized success response."""
    response_data = {"success": True, "message": message}
    if data is not None:
        response_data["data"] = data
    return json_response(response_data, status_code)


def error_response(
    message: str,
    status_code: int = 400,
    error_code: str | None = None,
    details: Any = None,
) -> OptimizedJSONResponse:
    """Create a standardized error response."""
    response_data = {
        "success": False,
        "error": error_code or "error",
        "message": message,
    }
    if details is not None:
        response_data["details"] = details
    return json_response(response_data, status_code)


def redirect_response(
    url: str, status_code: int = 302, headers: dict[str, str] | None = None
) -> StarletteRedirect:
    """Create a redirect response."""
    return StarletteRedirect(url=url, status_code=status_code, headers=headers)


def permanent_redirect(url: str) -> StarletteRedirect:
    """Create a permanent redirect (301) response."""
    return redirect_response(url, status_code=301)


def file_download_response(
    file_path: str | Path,
    filename: str | None = None,
    media_type: str | None = None,
    headers: dict[str, str] | None = None,
) -> FileResponse:
    """Create a file download response with proper headers."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Determine filename for download
    download_filename = filename or file_path.name

    # Set up headers
    download_headers = headers or {}
    download_headers["content-disposition"] = (
        f'attachment; filename="{download_filename}"'
    )

    return FileResponse(
        path=str(file_path),
        filename=download_filename,
        media_type=media_type,
        headers=download_headers,
    )


def inline_file_response(
    file_path: str | Path,
    media_type: str | None = None,
    headers: dict[str, str] | None = None,
) -> FileResponse:
    """Create an inline file response (display in browser)."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Set up headers for inline display
    inline_headers = headers or {}
    inline_headers["content-disposition"] = "inline"

    return FileResponse(
        path=str(file_path), media_type=media_type, headers=inline_headers
    )


def streaming_response(
    generator,
    media_type: str = "text/plain",
    headers: dict[str, str] | None = None,
    status_code: int = 200,
) -> StreamingResponse:
    """Create a streaming response."""
    return StreamingResponse(
        generator, media_type=media_type, headers=headers, status_code=status_code
    )


def html_response(
    content: str, status_code: int = 200, headers: dict[str, str] | None = None
) -> HTMLResponse:
    """Create an HTML response."""
    return HTMLResponse(content=content, status_code=status_code, headers=headers)


def no_content_response(headers: dict[str, str] | None = None) -> Response:
    """Create a 204 No Content response."""
    return Response(status_code=204, headers=headers)


def created_response(
    data: Any = None, location: str | None = None
) -> OptimizedJSONResponse:
    """Create a 201 Created response with optional location header."""
    headers = {}
    if location:
        headers["location"] = location

    return success_response(data=data, message="Created", status_code=201)


def accepted_response(
    message: str = "Request accepted for processing",
) -> OptimizedJSONResponse:
    """Create a 202 Accepted response."""
    return success_response(message=message, status_code=202)


# Pagination helper
def paginated_response(
    data: list,
    page: int,
    page_size: int,
    total_count: int,
    next_page: str | None = None,
    prev_page: str | None = None,
) -> OptimizedJSONResponse:
    """Create a paginated response with metadata."""
    total_pages = (total_count + page_size - 1) // page_size

    response_data = {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": next_page,
            "prev_page": prev_page,
        },
    }

    return json_response(response_data)


# Cookie utilities
def set_cookie_response(
    response: Response,
    key: str,
    value: str,
    max_age: int | None = None,
    expires: str | None = None,
    path: str = "/",
    domain: str | None = None,
    secure: bool = True,  # Default to secure cookies for security
    httponly: bool = True,  # Default to HttpOnly for XSS protection
    samesite: Literal["lax", "strict", "none"] | None = "lax",
) -> Response:
    """Add a cookie to a response with secure defaults.

    Args:
        response: Response object to add cookie to
        key: Cookie name
        value: Cookie value
        max_age: Cookie lifetime in seconds
        expires: Cookie expiration date string
        path: Cookie path
        domain: Cookie domain
        secure: Send only over HTTPS (default True for security)
        httponly: Prevent JavaScript access (default True for XSS protection)
        samesite: SameSite attribute for CSRF protection

    Note:
        Defaults to secure=True and httponly=True for security.
        Set secure=False only for development over HTTP.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        expires=expires,
        path=path,
        domain=domain,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
    )
    return response


def delete_cookie_response(
    response: Response, key: str, path: str = "/", domain: str | None = None
) -> Response:
    """Delete a cookie from a response."""
    response.delete_cookie(key=key, path=path, domain=domain)
    return response


# Content negotiation helper
def negotiate_response(data: Any, accept_header: str = "application/json") -> Response:
    """Create a response based on Accept header."""
    accept_header = accept_header.lower()

    if "application/json" in accept_header:
        return json_response(data)
    elif "text/html" in accept_header:
        # Basic HTML representation
        if isinstance(data, dict):
            content = "<pre>" + _json_dumps(data) + "</pre>"
        else:
            content = f"<pre>{data!s}</pre>"
        return html_response(content)
    elif "text/plain" in accept_header:
        content = _json_dumps(data) if isinstance(data, dict | list) else str(data)
        return Response(content, media_type="text/plain")
    else:
        # Default to JSON
        return json_response(data)
