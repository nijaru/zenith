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
from zenith.app import Zenith

# Core application components
from zenith.core.application import Application
from zenith.core.config import Config

# ============================================================================
# ROUTING & DEPENDENCY INJECTION
# ============================================================================
# Routing system
from zenith.core.routing import Auth, File, Router

# Dependency markers for clean injection
from zenith.core.routing.dependencies import (
    AuthDependency,
    FileUploadDependency,
    Inject,
    InjectDependency,
)

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================
# Base class for business logic services
from zenith.core.service import Service

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
from zenith.tasks.background import BackgroundTasks, TaskQueue, background_task

# Web utilities
from zenith.web import (
    OptimizedJSONResponse,
    error_response,
    json_response,
    success_response,
)

# Server-Sent Events with built-in backpressure optimizations
from zenith.web.sse import (
    ServerSentEvents,
    SSEConnection,
    SSEConnectionState,
    SSEEventManager,
    create_sse_response,
    sse,
)

# Static file and SPA serving (for convenience)
from zenith.web.static import serve_css_js, serve_images, serve_spa_files

# ============================================================================
# WEBSOCKETS & REAL-TIME
# ============================================================================
# WebSocket support
from zenith.web.websockets import WebSocket, WebSocketDisconnect, WebSocketManager

__all__ = [
    "Application",
    "AsyncSession",
    "Auth",
    "AuthDependency",
    # Additional middleware exceptions
    "AuthenticationException",
    "AuthorizationException",
    # ========================================================================
    # BACKGROUND PROCESSING
    # ========================================================================
    "BackgroundTasks",
    "BadRequestException",
    "Base",
    "CORSMiddleware",
    "CSRFMiddleware",
    "CompressionMiddleware",
    "Config",
    "ConflictException",
    # ========================================================================
    # DATABASE & MIGRATIONS
    # ========================================================================
    "Database",
    "Field",
    "File",
    "FileUploadDependency",
    "ForbiddenException",
    # ========================================================================
    # HTTP EXCEPTIONS
    # ========================================================================
    "HTTPException",
    "Inject",
    "InjectDependency",
    "InternalServerException",
    "JobManager",
    "JobQueue",
    "MigrationManager",
    "NotFoundException",
    "OptimizedJSONResponse",
    "RateLimitException",
    "Relationship",
    # ========================================================================
    # MIDDLEWARE & UTILITIES
    # ========================================================================
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    # ========================================================================
    # ROUTING & DEPENDENCY INJECTION
    # ========================================================================
    "Router",
    # SQLModel integration
    "SQLModel",
    "SQLModelRepository",
    "SSEConnection",
    "SSEConnectionState",
    "SSEEventManager",
    "SecurityHeadersMiddleware",
    # Server-Sent Events with built-in optimizations
    "ServerSentEvents",
    # ========================================================================
    # BUSINESS LOGIC
    # ========================================================================
    "Service",
    "SessionManager",
    "SessionMiddleware",
    "TaskQueue",
    "UnauthorizedException",
    "ValidationException",
    # ========================================================================
    # WEBSOCKETS & REAL-TIME
    # ========================================================================
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    "Worker",
    "Zenith",
    "ZenithSQLModel",
    # ========================================================================
    # MAIN FRAMEWORK
    # ========================================================================
    "__version__",
    "background_task",
    # Exception helpers
    "bad_request",
    "conflict",
    "create_repository",
    "create_sse_response",
    "error_response",
    "forbidden",
    "health_manager",
    "internal_error",
    "json_response",
    "metrics",
    "not_found",
    "serve_css_js",
    "serve_images",
    # Static file serving
    "serve_spa_files",
    "sse",
    "success_response",
    "unauthorized",
    "validation_error",
]
