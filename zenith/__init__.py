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

# Rails-like dependency shortcuts - these are pre-configured Depends objects
from zenith.core.dependencies import (
    DB,  # Database session shortcut
    CurrentUser,  # Current authenticated user
    Cache,  # Cache client shortcut
    Request,  # Request object shortcut
)

# ============================================================================
# ROUTING & DEPENDENCY INJECTION
# ============================================================================
from zenith.core.routing import Router
from zenith.core.routing.dependencies import (
    Auth,  # Auth dependency function for custom requirements
    File,  # File dependency function for uploads
    Inject,  # Service injection
)

# Request-scoped dependencies (FastAPI-compatible)
from zenith.core.scoped import DatabaseSession, Depends, RequestScoped, request_scoped

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================
from zenith.core.service import Service  # Service base class for business logic

# ============================================================================
# HIGH-LEVEL DECORATORS & UTILITIES
# ============================================================================
from zenith.decorators import (
    cache,
    rate_limit,
    validate,
    paginate,
    returns,
    auth_required,
    transaction,
)
from zenith.pagination import (
    Paginate,
    PaginatedResponse,
    CursorPagination,
)

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
    BusinessLogicException,
    ConcurrencyException,
    ConflictException,
    DatabaseException,
    DataIntegrityException,
    ForbiddenException,
    GoneException,
    HTTPException,
    IntegrationException,
    InternalServerException,
    NotFoundException,
    PaymentException,
    PreconditionFailedException,
    RateLimitException,
    ResourceLockedException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
    ZenithException,
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
from zenith.tasks.background import BackgroundTasks, TaskQueue, background_task

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
    "DB",
    "Application",
    # Database & Models
    "AsyncSession",
    # Routing & Dependencies
    "Auth",
    # HTTP Exceptions
    "AuthenticationException",
    "AuthorizationException",
    # Background Processing
    "BackgroundTasks",
    "BadRequestException",
    "Base",
    "BusinessLogicException",
    "CORSMiddleware",
    "CSRFMiddleware",
    "Cache",
    # Middleware
    "CompressionMiddleware",
    "ConcurrencyException",
    "Config",
    "ConflictException",
    "CurrentUser",
    "CursorPagination",
    "DataIntegrityException",
    "Database",
    "DatabaseException",
    "DatabaseSession",
    "Depends",
    "Field",
    "File",
    "ForbiddenException",
    "GoneException",
    "HTTPException",
    "Inject",
    "IntegrationException",
    "InternalServerException",
    "JobManager",
    "JobQueue",
    "MigrationManager",
    "NotFoundException",
    # Web Responses & Utilities
    "OptimizedJSONResponse",
    "Paginate",
    "PaginatedResponse",
    "PaymentException",
    "PreconditionFailedException",
    "RateLimitException",
    "Relationship",
    "Request",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "RequestScoped",
    "ResourceLockedException",
    "Router",
    "SQLModel",
    "SQLModelRepository",
    # Server-Sent Events
    "SSEConnection",
    "SSEConnectionState",
    "SSEEventManager",
    "SecurityHeadersMiddleware",
    "ServerSentEvents",
    # Business Logic
    "Service",
    "ServiceUnavailableException",
    # Sessions
    "SessionManager",
    "SessionMiddleware",
    "TaskQueue",
    "UnauthorizedException",
    "ValidationException",
    # WebSockets
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    "Worker",
    "Zenith",
    "ZenithException",
    "ZenithSQLModel",
    # Core Framework
    "__version__",
    "auth_required",
    "background_task",
    # Exception Helpers
    "bad_request",
    "cache",
    "conflict",
    "create_repository",
    "create_sse_response",
    "error_response",
    "forbidden",
    "internal_error",
    "json_response",
    "not_found",
    "paginate",
    "rate_limit",
    "request_scoped",
    "returns",
    # Static File Serving
    "serve_css_js",
    "serve_images",
    "serve_spa_files",
    "sse",
    "success_response",
    "transaction",
    "unauthorized",
    "validate",
    "validation_error",
]
