"""
Zenith Framework - Modern Python web framework for production-ready APIs.

Zero-configuration framework with state-of-the-art defaults:
- Automatic OpenAPI documentation
- Production middleware (CSRF, CORS, compression, logging)
- Request ID tracking and structured logging
- Health checks and Prometheus metrics
- Database migrations with Alembic
- Type-safe dependency injection
- Context-driven business logic organization

Build production-ready APIs with minimal configuration.
"""

from zenith.__version__ import __version__

__author__ = "Nick"

# ============================================================================
# MAIN FRAMEWORK
# ============================================================================

# Primary framework class with performance optimizations by default
# ============================================================================
# BACKGROUND PROCESSING
# ============================================================================
# Background tasks
from zenith.background import BackgroundTasks, background_task

# Core application components
from zenith.core.application import Application
from zenith.core.config import Config

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================
# Base class for business logic services
from zenith.core.context import Context as Service

# ============================================================================
# ROUTING & DEPENDENCY INJECTION
# ============================================================================
# Routing system
# Context marker for dependency injection
from zenith.core.routing import Auth, Context, File, Router

# Dependency markers for clean injection
from zenith.core.routing.dependencies import (
    AuthDependency,
    ContextDependency,
    FileUploadDependency,
)

# ============================================================================
# DATABASE & MIGRATIONS
# ============================================================================
# Database integration
# SQLModel integration (modern unified models)
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

# Migration management
from zenith.db.migrations import MigrationManager

# ============================================================================
# HTTP EXCEPTIONS
# ============================================================================
# Exception classes and helpers
from zenith.exceptions import (
    # Additional middleware exceptions
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

# Job system
from zenith.jobs import JobManager, JobQueue, Worker

# ============================================================================
# MIDDLEWARE & UTILITIES
# ============================================================================
# Essential middleware (auto-configured in framework)
from zenith.middleware import (
    CompressionMiddleware,
    CORSMiddleware,
    CSRFMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)

# Sessions
from zenith.sessions import SessionManager, SessionMiddleware

# Web utilities
from zenith.web import (
    OptimizedJSONResponse,
    error_response,
    health_manager,
    json_response,
    metrics,
    success_response,
)

# Static file and SPA serving (for convenience)
from zenith.web.static import serve_css_js, serve_images, serve_spa_files

# ============================================================================
# WEBSOCKETS & REAL-TIME
# ============================================================================
# WebSocket support
from zenith.websockets import WebSocket, WebSocketDisconnect, WebSocketManager

# Server-Sent Events with built-in backpressure optimizations
from zenith.web.sse import (
    ServerSentEvents,
    SSEEventManager,
    SSEConnection,
    SSEConnectionState,
    create_sse_response,
    sse,
)
from zenith.zenith import Zenith, create_app

__all__ = [
    # ========================================================================
    # MAIN FRAMEWORK
    # ========================================================================
    "__version__",
    "Zenith",
    "create_app",
    "Application",
    "Config",
    # ========================================================================
    # ROUTING & DEPENDENCY INJECTION
    # ========================================================================
    "Router",
    "Auth",
    "Context",
    "File",
    "AuthDependency",
    "ContextDependency",
    "FileUploadDependency",
    # ========================================================================
    # BUSINESS LOGIC
    # ========================================================================
    "Service",
    # ========================================================================
    # DATABASE & MIGRATIONS
    # ========================================================================
    "Database",
    "Base",
    "AsyncSession",
    "MigrationManager",
    # SQLModel integration
    "SQLModel",
    "Field",
    "Relationship",
    "ZenithSQLModel",
    "SQLModelRepository",
    "create_repository",
    # ========================================================================
    # MIDDLEWARE & UTILITIES
    # ========================================================================
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "CompressionMiddleware",
    "SecurityHeadersMiddleware",
    "CORSMiddleware",
    "CSRFMiddleware",
    "metrics",
    "health_manager",
    "success_response",
    "error_response",
    "json_response",
    "OptimizedJSONResponse",
    # Static file serving
    "serve_spa_files",
    "serve_css_js",
    "serve_images",
    # ========================================================================
    # BACKGROUND PROCESSING
    # ========================================================================
    "BackgroundTasks",
    "background_task",
    "JobManager",
    "JobQueue",
    "Worker",
    "SessionManager",
    "SessionMiddleware",
    # ========================================================================
    # WEBSOCKETS & REAL-TIME
    # ========================================================================
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    # Server-Sent Events with built-in optimizations
    "ServerSentEvents",
    "SSEEventManager",
    "SSEConnection", 
    "SSEConnectionState",
    "create_sse_response",
    "sse",
    # ========================================================================
    # HTTP EXCEPTIONS
    # ========================================================================
    "HTTPException",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "ConflictException",
    "ValidationException",
    "InternalServerException",
    # Additional middleware exceptions
    "AuthenticationException",
    "AuthorizationException",
    "RateLimitException",
    # Exception helpers
    "bad_request",
    "unauthorized",
    "forbidden",
    "not_found",
    "conflict",
    "validation_error",
    "internal_error",
]
