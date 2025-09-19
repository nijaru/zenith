"""
🌊 Proper Middleware Architecture - Separation of Concerns

This example demonstrates the correct way to use Zenith's middleware system
with proper separation of concerns. Each middleware has a single responsibility
and can be configured independently.

Key Architecture Principles:
- Separation of concerns - each middleware handles one responsibility
- Individual configuration - can enable/disable middleware independently
- Clean, maintainable architecture
- No forced coupling of unrelated functionality

Prerequisites:
    None - uses standard middleware

Run with: python examples/19-proper-middleware-architecture.py
Visit: http://localhost:8019

Endpoints:
- GET  /                     - Public endpoint
- GET  /protected            - Protected endpoint (auth required)
- GET  /admin               - Admin endpoint (auth + rate limiting demo)
- GET  /metrics             - Middleware information
"""

import time
from datetime import datetime

from pydantic import BaseModel

from zenith import Zenith
from zenith.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = Zenith(
    title="Proper Middleware Architecture Demo",
    version="1.0.0",
    description="Demonstrates clean separation of concerns with individual middleware",
)

# ============================================================================
# PROPER MIDDLEWARE STACK - SEPARATION OF CONCERNS
# ============================================================================

# 1. Security Headers Middleware - Adds security headers
app.add_middleware(
    SecurityHeadersMiddleware,
    config={
        "content_type_nosniff": True,
        "frame_deny": True,
        "xss_protection": True,
        "custom_headers": {
            "X-Architecture": "Proper-Separation-Of-Concerns",
        },
    },
)

# 2. Request ID Middleware - Adds unique request identifiers
app.add_middleware(
    RequestIDMiddleware,
    config={
        "request_id_header": "X-Request-ID",
        "response_id_header": "X-Request-ID",
    },
)

# 3. Authentication Middleware - Handles JWT authentication
app.add_middleware(
    AuthenticationMiddleware,
    public_paths=["/", "/metrics", "/docs", "/redoc", "/openapi.json"],
)

# 4. Rate Limiting Middleware - Handles request rate limiting
app.add_middleware(
    RateLimitMiddleware,
    config={
        "default_limits": ["10/minute"],  # 10 requests per minute per IP
        "exempt_paths": ["/", "/metrics", "/docs", "/redoc", "/openapi.json"],
    },
)

# ============================================================================
# MODELS
# ============================================================================


class MiddlewareInfo(BaseModel):
    """Middleware information."""

    request_id: str
    processing_time_ms: float
    middleware_stack: list[str]
    architecture_principles: list[str]
    timestamp: str


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def home():
    """Public homepage - demonstrates proper middleware architecture."""
    return {
        "message": "🌊 Proper Middleware Architecture Demo",
        "description": "Clean separation of concerns with individual middleware",
        "features": [
            "Individual middleware responsibilities",
            "Independent configuration",
            "No forced coupling",
            "Maintainable architecture",
        ],
        "endpoints": {
            "/": "Public homepage",
            "/protected": "Requires authentication",
            "/admin": "Requires auth + demonstrates rate limiting",
            "/metrics": "Middleware information",
        },
        "architecture_benefits": [
            "Each middleware handles one concern",
            "Can configure middleware independently",
            "Easy to test individual components",
            "Flexible and maintainable",
        ],
    }


@app.get("/protected")
async def protected_route():
    """
    Protected endpoint demonstrating authentication middleware.

    Requires valid JWT token in Authorization header.
    """
    return {
        "message": "Access granted to protected resource",
        "architecture": "Individual AuthenticationMiddleware",
        "benefit": "Can use authentication without being forced to use rate limiting",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/admin")
async def admin_route():
    """
    Admin endpoint demonstrating both auth and rate limiting.

    This shows how the two middleware work together while remaining separate.
    Try accessing this multiple times quickly to see rate limiting.
    """
    return {
        "message": "Admin access granted",
        "architecture": "Separate AuthenticationMiddleware + RateLimitMiddleware",
        "benefit": "Each middleware configured independently",
        "rate_limit_info": "10 requests per minute per IP",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def metrics_info() -> MiddlewareInfo:
    """
    Middleware architecture information.
    """
    # Simulate processing time measurement
    processing_start = time.time()
    await asyncio.sleep(0.001)  # Small delay to simulate processing
    processing_time = (time.time() - processing_start) * 1000

    return MiddlewareInfo(
        request_id="generated-by-request-id-middleware",
        processing_time_ms=round(processing_time, 2),
        middleware_stack=[
            "SecurityHeadersMiddleware",
            "RequestIDMiddleware",
            "AuthenticationMiddleware",
            "RateLimitMiddleware",
        ],
        architecture_principles=[
            "Separation of concerns",
            "Single responsibility per middleware",
            "Independent configuration",
            "No forced coupling",
        ],
        timestamp=datetime.now().isoformat(),
    )


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == "__main__":
    import asyncio

    import uvicorn

    print("🌊 Proper Middleware Architecture Demo")
    print("=" * 65)
    print()
    print("🏗️ Architecture Principles:")
    print("   • Separation of concerns")
    print("   • Individual middleware responsibilities")
    print("   • Independent configuration")
    print("   • No forced coupling")
    print()
    print("🔗 Key Endpoints:")
    print("   GET  /                     - Public homepage")
    print("   GET  /protected            - Protected endpoint (auth required)")
    print("   GET  /admin               - Admin endpoint (auth + rate limiting)")
    print("   GET  /metrics              - Middleware information")
    print()
    print("📖 Interactive Docs: http://localhost:8019/docs")
    print()
    print("💡 Benefits: Individual middleware can be configured, tested,")
    print("   and maintained independently without forced coupling.")

    uvicorn.run(app, host="0.0.0.0", port=8019)
