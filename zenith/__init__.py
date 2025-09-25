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

# Python version compatibility check
import sys
if sys.version_info >= (3, 13):
    import warnings
    warnings.warn(
        "Zenith currently supports Python 3.12. Python 3.13 support will be added "
        "when the dependency ecosystem stabilizes. Please use Python 3.12 for now.",
        UserWarning,
        stacklevel=2
    )

# ============================================================================
# MAIN FRAMEWORK
# ============================================================================

from zenith.app import Zenith
from zenith.core.application import Application
from zenith.core.config import Config

# Rails-like dependency shortcuts - these are pre-configured Depends objects
from zenith.core.dependencies import (
    Session,  # Database session shortcut (the one true way)
    Auth,  # Authentication dependency (the one true way)
    CurrentUser,  # Current authenticated user
    File,  # File upload dependency with validation
    Request,  # Request object shortcut
    # File upload constants for better DX
    IMAGE_TYPES, DOCUMENT_TYPES, AUDIO_TYPES, VIDEO_TYPES, ARCHIVE_TYPES,
    MB, GB, KB,  # Size constants
)

# File upload types
from zenith.web.files import UploadedFile

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
# BACKGROUND PROCESSING (SIMPLIFIED)
# ============================================================================
from zenith.background import (
    JobQueue,  # Comprehensive job queue with persistence and retry
    Job,  # Job data model
    JobStatus,  # Job status enum
)
from zenith.tasks.background import (
    BackgroundTasks,  # Simple tasks that run after response is sent
    background_task,  # Decorator for background task functions
)

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================
from zenith.core.service import (
    Service,  # Service base class for business logic (clean, standalone)
    ContainerService,  # Advanced service with full container features
)

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
    Model,  # Recommended base class for database models
    Relationship,
    SQLModel,
    SQLModelRepository,
    ZenithModel,  # Rails-like ActiveRecord model with async methods
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
    "Zenith",
    "Application",
    "Config",
    "__version__",
    # Database & Models
    "AsyncSession",
    "Base",
    "Database",
    "Field",
    "Model",             # Recommended base class for database models
    "Relationship",
    "SQLModel",
    "SQLModelRepository",
    "ZenithModel",       # Rails-like ActiveRecord model with async methods
    # Dependency Injection (Rails-like shortcuts)
    "Session",           # Database session shortcut (the one true way)
    "Auth",              # Authentication dependency
    "CurrentUser",       # Current authenticated user
    "File",              # File upload dependency with validation
    "Request",           # Request object shortcut
    "Inject",            # Service injection
    # File upload helpers
    "IMAGE_TYPES", "DOCUMENT_TYPES", "AUDIO_TYPES", "VIDEO_TYPES", "ARCHIVE_TYPES",
    "MB", "GB", "KB",
    # Request-scoped dependencies
    "Depends",
    "RequestScoped",
    # Background Processing (Simplified API)
    "BackgroundTasks",   # Simple tasks that run after response
    "JobQueue",          # Comprehensive job processing with retry
    "Job",               # Job data model
    "JobStatus",         # Job status enum
    "background_task",   # Decorator for background task functions
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
    "ContainerService",
    # Routing
    "Router",
    # Sessions
    "SessionManager",
    "SessionMiddleware",
# Note: Legacy job systems removed for API clarity
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
