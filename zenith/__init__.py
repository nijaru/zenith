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
from zenith.zenith import Zenith, create_app

# Core application components
from zenith.core.application import Application
from zenith.core.config import Config

# ============================================================================
# ROUTING & DEPENDENCY INJECTION  
# ============================================================================

# Routing system
from zenith.core.routing import Router, Auth, File

# Dependency markers for clean injection
from zenith.core.routing.dependencies import (
    AuthDependency,
    ContextDependency, 
    FileUploadDependency,
)

# Context marker for dependency injection
from zenith.core.routing import Context

# ============================================================================
# BUSINESS LOGIC ORGANIZATION
# ============================================================================

# Base class for business logic services
from zenith.core.context import Context as Service

# ============================================================================
# DATABASE & MIGRATIONS
# ============================================================================

# Database integration
from zenith.db import Database, Base, AsyncSession

# SQLModel integration (modern unified models)
from zenith.db import SQLModel, Field, Relationship, ZenithSQLModel, SQLModelRepository, create_repository

# Migration management  
from zenith.db.migrations import MigrationManager

# ============================================================================
# MIDDLEWARE & UTILITIES
# ============================================================================

# Essential middleware (auto-configured in framework)
from zenith.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    CompressionMiddleware,
    SecurityHeadersMiddleware,
    CORSMiddleware,
    CSRFMiddleware,
)

# Web utilities
from zenith.web import (
    metrics,
    health_manager,
    success_response,
    error_response,
    json_response,
    OptimizedJSONResponse,
)

# Static file and SPA serving (for convenience)
from zenith.web.static import serve_spa_files, serve_css_js, serve_images

# ============================================================================
# BACKGROUND PROCESSING
# ============================================================================

# Background tasks
from zenith.background import BackgroundTasks, background_task

# Job system
from zenith.jobs import JobManager, JobQueue, Worker

# Sessions
from zenith.sessions import SessionManager, SessionMiddleware

# ============================================================================
# WEBSOCKETS & REAL-TIME
# ============================================================================

# WebSocket support
from zenith.websockets import WebSocket, WebSocketDisconnect, WebSocketManager

# ============================================================================
# HTTP EXCEPTIONS
# ============================================================================

# Exception classes and helpers
from zenith.exceptions import (
    HTTPException,
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    ValidationException,
    InternalServerException,
    # Additional middleware exceptions
    AuthenticationException,
    AuthorizationException,
    RateLimitException,
    # Helper functions
    bad_request,
    unauthorized,
    forbidden,
    not_found,
    conflict,
    validation_error,
    internal_error,
)

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
