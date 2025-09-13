"""
Web layer components - controllers, middleware, routing.

Provides utilities for:
- HTTP responses with standardized formats
- File uploads and static serving
- Health checks and monitoring
- Application metrics collection
- Production-ready utilities
"""

from .files import FileUpload, FileUploader, UploadedFile
from .health import (
    HealthManager,
    HealthStatus,
    add_health_routes,
    health_endpoint,
    health_manager,
    liveness_endpoint,
    readiness_endpoint,
)
from .metrics import (
    MetricsCollector,
    MetricType,
    add_metrics_route,
    metrics,
    metrics_endpoint,
    record_request_metrics,
)
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
    SSEConnection,
    SSEConnectionState,
    SSEEventManager,
    ServerSentEvents,
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

__all__ = [
    "FileUpload",
    "FileUploader",
    "HealthManager",
    "HealthStatus",
    "MetricType",
    "MetricsCollector",
    "OptimizedJSONResponse",
    "UploadedFile",
    "accepted_response",
    "add_health_routes",
    "add_metrics_route",
    "create_static_route",
    "created_response",
    "delete_cookie_response",
    "error_response",
    "file_download_response",
    "health_endpoint",
    "health_manager",
    "html_response",
    "inline_file_response",
    "json_response",
    "liveness_endpoint",
    "metrics",
    "metrics_endpoint",
    "negotiate_response",
    "no_content_response",
    "paginated_response",
    "permanent_redirect",
    "readiness_endpoint",
    "record_request_metrics",
    "redirect_response",
    "serve_css_js",
    "serve_images",
    "serve_spa_files",
    "serve_uploads",
    "set_cookie_response",
    "SSEConnection",
    "SSEConnectionState", 
    "SSEEventManager",
    "ServerSentEvents",
    "sse",
    "streaming_response",
    "success_response",
    "create_sse_response",
]
