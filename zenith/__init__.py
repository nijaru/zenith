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

# ============================================================================
# BACKGROUND PROCESSING (SIMPLIFIED)
# ============================================================================
from zenith.background import (
    Job,  # Job data model
    JobQueue,  # Comprehensive job queue with persistence and retry
    JobStatus,  # Job status enum
)
from zenith.core.application import Application
from zenith.core.config import Config

# Rails-like dependency shortcuts - these are pre-configured Depends objects
from zenith.core.dependencies import (
    ARCHIVE_TYPES,
    AUDIO_TYPES,
    DOCUMENT_TYPES,
    GB,
    # File upload constants for better DX
    IMAGE_TYPES,
    KB,  # Size constants
    MB,
    VIDEO_TYPES,
    Auth,  # Authentication dependency (the one true way)
    CurrentUser,  # Current authenticated user
    File,  # File upload dependency with validation
    Request,  # Request object shortcut
    Session,  # Database session shortcut (the one true way)
)

# ============================================================================
# ROUTING & DEPENDENCY INJECTION
# ============================================================================
from zenith.core.routing import Router
from zenith.core.routing.dependencies import (
    Inject,  # Service injection
)

# Request-scoped dependencies (FastAPI-compatible)
from zenith.core.scoped import Depends, RequestScoped, request_scoped

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================
from zenith.core.service import (
    Service,  # Unified service base class for business logic
)

# ============================================================================
# DATABASE & MIGRATIONS
# ============================================================================
from zenith.db import (
    AsyncSession,
    Base,
    Database,
    Field,
    Model,  # Recommended base class for database models
    Relationship,
    SQLModel,
    SQLModelRepository,
    ZenithModel,  # Rails-like ActiveRecord model with async methods
    create_repository,
)
from zenith.db.migrations import MigrationManager

# ============================================================================
# HIGH-LEVEL DECORATORS & UTILITIES
# ============================================================================
from zenith.decorators import (
    auth_required,
    cache,
    paginate,
    rate_limit,
    returns,
    transaction,
    validate,
)

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

# Note: Legacy job systems (JobManager, RedisJobQueue, Worker) have been removed
# Use BackgroundTasks for simple tasks or JobQueue for comprehensive job processing
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
from zenith.pagination import (
    CursorPagination,
    Paginate,
    PaginatedResponse,
)

# ============================================================================
# SESSIONS
# ============================================================================
from zenith.sessions import SessionManager, SessionMiddleware
from zenith.tasks.background import (
    BackgroundTasks,  # Simple tasks that run after response is sent
    background_task,  # Decorator for background task functions
)

# ============================================================================
# WEB UTILITIES & RESPONSES
# ============================================================================
from zenith.web import (
    OptimizedJSONResponse,
    error_response,
    json_response,
    success_response,
)

# File upload types
from zenith.web.files import UploadedFile

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
    "ARCHIVE_TYPES",
    "AUDIO_TYPES",
    "DOCUMENT_TYPES",
    "GB",
    # File upload helpers
    "IMAGE_TYPES",
    "KB",
    "MB",
    "VIDEO_TYPES",
    "Application",
    # Database & Models
    "AsyncSession",
    "Auth",  # Authentication dependency
    # HTTP Exceptions
    "AuthenticationException",
    "AuthorizationException",
    # Background Processing (Simplified API)
    "BackgroundTasks",  # Simple tasks that run after response
    "BadRequestException",
    "Base",
    "BusinessLogicException",
    "CORSMiddleware",
    "CSRFMiddleware",
    # Middleware
    "CompressionMiddleware",
    "ConcurrencyException",
    "Config",
    "ConflictException",
    "CurrentUser",  # Current authenticated user
    "CursorPagination",
    "DataIntegrityException",
    "Database",
    "DatabaseException",
    # Request-scoped dependencies
    "Depends",
    "Field",
    "File",  # File upload dependency with validation
    "ForbiddenException",
    "GoneException",
    "HTTPException",
    "Inject",  # Service injection
    "IntegrationException",
    "InternalServerException",
    "Job",  # Job data model
    "JobQueue",  # Comprehensive job processing with retry
    "JobStatus",  # Job status enum
    # Note: Legacy job systems removed for API clarity
    # Database Migrations
    "MigrationManager",
    "Model",  # Recommended base class for database models
    "NotFoundException",
    # Web Responses & Utilities
    "OptimizedJSONResponse",
    # Pagination
    "Paginate",
    "PaginatedResponse",
    "PaymentException",
    "PreconditionFailedException",
    "RateLimitException",
    "Relationship",
    "Request",  # Request object shortcut
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "RequestScoped",
    "ResourceLockedException",
    # Routing
    "Router",
    "SQLModel",
    "SQLModelRepository",
    "SSEConnection",
    "SSEConnectionState",
    "SSEEventManager",
    "SecurityHeadersMiddleware",
    # Server-Sent Events
    "ServerSentEvents",
    # Business Logic
    "Service",
    "ServiceUnavailableException",
    # Dependency Injection (Rails-like shortcuts)
    "Session",  # Database session shortcut (the one true way)
    # Sessions
    "SessionManager",
    "SessionMiddleware",
    "UnauthorizedException",
    "UploadedFile",
    "ValidationException",
    # WebSockets
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    # Core Framework
    "Zenith",
    "ZenithException",
    "ZenithModel",  # Rails-like ActiveRecord model with async methods
    "__version__",
    "auth_required",
    "background_task",  # Decorator for background task functions
    # Exception Helpers
    "bad_request",
    # High-level Decorators
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
