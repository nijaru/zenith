"""
Web layer components - controllers, middleware, routing.

Provides utilities for:
- HTTP responses with standardized formats
- File uploads and static serving
- Health checks and monitoring
- Production-ready utilities
"""

from .files import FileUpload, FileUploader, UploadedFile
from .responses import (
    OptimizedJSONResponse,
    accepted_response,
    created_response,
    delete_cookie_response,
    error_response,
    file_download_response,
    html_response,
    inline_file_response,
    json_response,
    negotiate_response,
    no_content_response,
    paginated_response,
    permanent_redirect,
    redirect_response,
    set_cookie_response,
    streaming_response,
    success_response,
)
from .sse import (
    ServerSentEvents,
    SSEConnection,
    SSEConnectionState,
    SSEEventManager,
    create_sse_response,
    sse,
)
from .static import (
    create_static_route,
    serve_css_js,
    serve_images,
    serve_spa_files,
    serve_uploads,
)
from .websockets import WebSocket, WebSocketDisconnect, WebSocketManager

__all__ = [
    "FileUpload",
    "FileUploader",
    "OptimizedJSONResponse",
    "SSEConnection",
    "SSEConnectionState",
    "SSEEventManager",
    "ServerSentEvents",
    "UploadedFile",
    # WebSocket exports
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    "accepted_response",
    "create_sse_response",
    "create_static_route",
    "created_response",
    "delete_cookie_response",
    "error_response",
    "file_download_response",
    "html_response",
    "inline_file_response",
    "json_response",
    "negotiate_response",
    "no_content_response",
    "paginated_response",
    "permanent_redirect",
    "redirect_response",
    "serve_css_js",
    "serve_images",
    "serve_spa_files",
    "serve_uploads",
    "set_cookie_response",
    "sse",
    "streaming_response",
    "success_response",
]
