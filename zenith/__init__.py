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
    Session,  # Database session shortcut (the one true way)
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
from zenith.core.scoped import Depends, RequestScoped, request_scoped

# ============================================================================
# BACKGROUND TASK MANAGEMENT
# ============================================================================
from zenith.background import (
    BackgroundTaskManager,  # Simple async task management with automatic cleanup
    JobQueue,  # Comprehensive job queue with persistence and retry
    Job,  # Job data model
    JobStatus,  # Job status enum
    background_task,  # Decorator for background task functions
)

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
# BACKGROUND PROCESSING & JOBS (LEGACY)
# ============================================================================
from zenith.jobs import JobManager, RedisJobQueue, Worker

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
from zenith.tasks.background import BackgroundTasks, TaskQueue

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
    "Zenith",
    "Application",
    "Config",
    "__version__",
    # Database & Models
    "AsyncSession",
    "Base",
    "Database",
    "Field",
    "Relationship",
    "SQLModel",
    "SQLModelRepository",
    "ZenithSQLModel",
    # Dependency Injection (Rails-like shortcuts)
    "Session",           # Database session shortcut (the one true way)
    "Auth",              # Authentication dependency
    "CurrentUser",       # Current authenticated user
    "Cache",             # Cache client shortcut
    "Request",           # Request object shortcut
    "Inject",            # Service injection
    "File",              # File dependency function for uploads
    # Request-scoped dependencies
    "Depends",
    "RequestScoped",
    # Background Processing
    "BackgroundTaskManager",
    "JobQueue",
    "Job",
    "JobStatus",
    "background_task",
    "BackgroundTasks",
    # HTTP Exceptions
    "AuthenticationException",
    "AuthorizationException",
    "BadRequestException",
    "BusinessLogicException",
    "ConcurrencyException",
    "ConflictException",
    "DatabaseException",
    "DataIntegrityException",
    "ForbiddenException",
    "GoneException",
    "HTTPException",
    "IntegrationException",
    "InternalServerException",
    "NotFoundException",
    "PaymentException",
    "PreconditionFailedException",
    "RateLimitException",
    "ResourceLockedException",
    "ServiceUnavailableException",
    "UnauthorizedException",
    "ValidationException",
    "ZenithException",
    # Middleware
    "CompressionMiddleware",
    "CORSMiddleware",
    "CSRFMiddleware",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
    # Business Logic
    "Service",
    # Routing
    "Router",
    # Sessions
    "SessionManager",
    "SessionMiddleware",
    # Jobs & Background Processing
    "JobManager",
    "RedisJobQueue",
    "Worker",
    "TaskQueue",
    # Database Migrations
    "MigrationManager",
    "create_repository",
    # Web Responses & Utilities
    "OptimizedJSONResponse",
    "json_response",
    "error_response",
    "success_response",
    # Exception Helpers
    "bad_request",
    "conflict",
    "forbidden",
    "internal_error",
    "not_found",
    "unauthorized",
    "validation_error",
    # Pagination
    "Paginate",
    "PaginatedResponse",
    "CursorPagination",
    "paginate",
    # Server-Sent Events
    "ServerSentEvents",
    "SSEConnection",
    "SSEConnectionState",
    "SSEEventManager",
    "create_sse_response",
    "sse",
    # WebSockets
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    # Static File Serving
    "serve_css_js",
    "serve_images",
    "serve_spa_files",
    # High-level Decorators
    "cache",
    "rate_limit",
    "validate",
    "returns",
    "auth_required",
    "transaction",
    "request_scoped",
]
