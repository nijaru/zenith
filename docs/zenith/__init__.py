"""
Zenith Framework - Modern Python web framework for production-ready APIs.

Zero-configuration framework with state-of-the-art defaults:
- Automatic OpenAPI documentation
- Production middleware (CSRF, CORS, compression, logging)
- Request ID tracking and structured logging
- Health checks and Prometheus metrics
- Database migrations with Alembic
- Type-safe dependency injection
- Service-driven business logic organization

Build production-ready APIs with minimal configuration.
"""

from zenith.__version__ import __version__

__author__ = "Nick"

# ============================================================================
# MAIN FRAMEWORK
# ============================================================================

from zenith.app import Zenith
from zenith.core.application import Application
from zenith.core.config import Config

# ============================================================================
# ROUTING & DEPENDENCY INJECTION
# ============================================================================

from zenith.core.routing import Auth, File, Router
from zenith.core.routing.dependencies import (
    AuthDependency,
    FileDependency,
    Inject,
    InjectDependency,
)

# Request-scoped dependencies (FastAPI-compatible)
from zenith.core.scoped import DatabaseSession, Depends, RequestScoped, request_scoped

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================

from zenith.core.service import Service

# ============================================================================
# DATABASE & MIGRATIONS
# ============================================================================

from zenith.db import (
    AsyncSession,
    Base,
    Database,
    Field,
    Relationship,
    SQLModel,
    SQLModelRepository,
    ZenithSQLModel,
    create_repository,
)
from zenith.db.migrations import MigrationManager

# ============================================================================
# HTTP EXCEPTIONS & ERROR HANDLING
# ============================================================================

from zenith.exceptions import (
    # Exception classes
    AuthenticationException,
    AuthorizationException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    HTTPException,
    InternalServerException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    ValidationException,
    # Helper functions
    bad_request,
    conflict,
    forbidden,
    internal_error,
    not_found,
    unauthorized,
    validation_error,
)

# ============================================================================
# BACKGROUND PROCESSING & JOBS
# ============================================================================

from zenith.jobs import JobManager, JobQueue, Worker
from zenith.tasks.background import BackgroundTasks, TaskQueue, background_task

# ============================================================================
# MIDDLEWARE
# ============================================================================

from zenith.middleware import (
    CompressionMiddleware,
    CORSMiddleware,
    CSRFMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)

# ============================================================================
# SESSIONS
# ============================================================================

from zenith.sessions import SessionManager, SessionMiddleware

# ============================================================================
# WEB UTILITIES & RESPONSES
# ============================================================================

from zenith.web import (
    OptimizedJSONResponse,
    error_response,
    json_response,
    success_response,
)

# Server-Sent Events
from zenith.web.sse import (
    ServerSentEvents,
    SSEConnection,
    SSEConnectionState,
    SSEEventManager,
    create_sse_response,
    sse,
)

# Static file serving
from zenith.web.static import serve_css_js, serve_images, serve_spa_files

# ============================================================================
# WEBSOCKETS & REAL-TIME
# ============================================================================

from zenith.web.websockets import WebSocket, WebSocketDisconnect, WebSocketManager

# ============================================================================
# PUBLIC API - ORGANIZED BY CATEGORY
# ============================================================================

__all__ = [
    # Core Framework
    "__version__",
    "Application",
    "Config",
    "Zenith",

    # Routing & Dependencies
    "Auth",
    "AuthDependency",
    "DatabaseSession",
    "Depends",
    "File",
    "FileDependency",
    "Inject",
    "InjectDependency",
    "RequestScoped",
    "Router",
    "request_scoped",

    # Business Logic
    "Service",

    # Database & Models
    "AsyncSession",
    "Base",
    "Database",
    "Field",
    "MigrationManager",
    "Relationship",
    "SQLModel",
    "SQLModelRepository",
    "ZenithSQLModel",
    "create_repository",

    # HTTP Exceptions
    "AuthenticationException",
    "AuthorizationException",
    "BadRequestException",
    "ConflictException",
    "ForbiddenException",
    "HTTPException",
    "InternalServerException",
    "NotFoundException",
    "RateLimitException",
    "UnauthorizedException",
    "ValidationException",

    # Exception Helpers
    "bad_request",
    "conflict",
    "forbidden",
    "internal_error",
    "not_found",
    "unauthorized",
    "validation_error",

    # Background Processing
    "BackgroundTasks",
    "JobManager",
    "JobQueue",
    "TaskQueue",
    "Worker",
    "background_task",

    # Middleware
    "CompressionMiddleware",
    "CORSMiddleware",
    "CSRFMiddleware",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",

    # Sessions
    "SessionManager",
    "SessionMiddleware",

    # Web Responses & Utilities
    "OptimizedJSONResponse",
    "error_response",
    "json_response",
    "success_response",

    # Server-Sent Events
    "SSEConnection",
    "SSEConnectionState",
    "SSEEventManager",
    "ServerSentEvents",
    "create_sse_response",
    "sse",

    # Static File Serving
    "serve_css_js",
    "serve_images",
    "serve_spa_files",

    # WebSockets
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
]
