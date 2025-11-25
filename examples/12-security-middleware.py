"""
[*] Zenith Security Middleware - Complete Production Security Stack

This example demonstrates a comprehensive security configuration for production
applications, including all security headers, CSRF protection, compression,
and request tracking.

Key Security Features Demonstrated:
- Security Headers (HSTS, CSP, X-Frame-Options, etc.)
- CSRF Protection with token validation
- Response Compression (Gzip/Brotli)
- Request ID tracking for debugging
- Secure cookie configuration
- Production-ready security hardening

Run with: python examples/11-security-middleware.py
Visit: http://localhost:8001

Security Endpoints:
- GET /                    - Public homepage with security info
- GET /secure              - CSRF-protected page with token
- POST /api/secure         - CSRF-protected API endpoint
- GET /headers             - Shows all security headers
- GET /metrics             - Request metrics with correlation
"""

import os
import secrets
from datetime import datetime

from pydantic import BaseModel

from zenith import Zenith
from zenith.middleware.compression import CompressionConfig, CompressionMiddleware
from zenith.middleware.csrf import CSRFConfig, CSRFMiddleware
from zenith.middleware.logging import RequestLoggingMiddleware
from zenith.middleware.request_id import RequestIDMiddleware
from zenith.middleware.security import SecurityConfig, SecurityHeadersMiddleware

# ============================================================================
# MODELS
# ============================================================================


class SecurityInfo(BaseModel):
    """Security configuration information."""

    csrf_enabled: bool
    hsts_enabled: bool
    csp_enabled: bool
    compression_enabled: bool
    request_tracking: bool
    secure_cookies: bool


class SecureData(BaseModel):
    """Data for CSRF-protected operations."""

    message: str
    priority: str = "normal"


class SecurityHeaders(BaseModel):
    """Security headers information."""

    headers: dict[str, str]
    description: dict[str, str]


# ============================================================================
# APPLICATION SETUP - PRODUCTION SECURITY CONFIGURATION
# ============================================================================

# Generate secure secret key (in production, use environment variable)
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)

# Use ZENITH_ENV=production for production deployment
app = Zenith()

# ============================================================================
# SECURITY MIDDLEWARE STACK - ORDER MATTERS!
# ============================================================================

# 1. Request ID Middleware (first - for tracking)
app.add_middleware(RequestIDMiddleware)

# 2. Request Logging (after request ID for correlation)
app.add_middleware(RequestLoggingMiddleware, include_body=True)

# 3. Security Headers Middleware (comprehensive protection)
security_config = SecurityConfig(
    # Content Security Policy - Restrict resource loading
    csp_policy=(
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
    # HTTP Strict Transport Security - Force HTTPS
    hsts_max_age=31536000,  # 1 year
    hsts_include_subdomains=True,
    hsts_preload=True,
    # Frame protection
    frame_options="DENY",
    # Content type protection
    content_type_nosniff=True,
    # Referrer policy
    referrer_policy="strict-origin-when-cross-origin",
    # Permissions policy (modern browsers)
    permissions_policy=(
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    ),
    # Force HTTPS in production
    force_https=False,  # Set to True in production with HTTPS
)

app.add_middleware(SecurityHeadersMiddleware, config=security_config)

# 4. CSRF Protection Middleware
csrf_config = CSRFConfig(
    secret_key=SECRET_KEY,
    token_name="csrf_token",
    header_name="X-CSRF-Token",
    cookie_name="csrf_token",
    cookie_secure=False,  # Set to True in production with HTTPS
    cookie_httponly=False,  # Allow JavaScript access for AJAX
    cookie_samesite="Lax",  # CSRF protection
    max_age_seconds=3600,  # 1 hour
    exempt_methods={"GET", "HEAD", "OPTIONS"},
    exempt_paths={"/", "/headers", "/metrics"},  # Public endpoints
)

app.add_middleware(CSRFMiddleware, config=csrf_config)

# 5. Compression Middleware (last - compress final response)
compression_config = CompressionConfig(
    minimum_size=500,  # Only compress responses > 500 bytes
    compressible_types={
        "application/json",
        "application/javascript",
        "text/html",
        "text/css",
        "text/plain",
        "text/xml",
    },
    exclude_paths={"/metrics"},  # Don't compress metrics
)

app.add_middleware(CompressionMiddleware, config=compression_config)


# ============================================================================
# SECURITY HELPER FUNCTIONS
# ============================================================================


def get_security_info() -> SecurityInfo:
    """Get current security configuration information."""
    return SecurityInfo(
        csrf_enabled=True,
        hsts_enabled=True,
        csp_enabled=True,
        compression_enabled=True,
        request_tracking=True,
        secure_cookies=False,  # Would be True in production with HTTPS
    )


def describe_security_headers() -> SecurityHeaders:
    """Describe all security headers and their purposes."""
    headers_info = {
        "X-Content-Type-Options": "Prevents MIME type sniffing attacks",
        "X-Frame-Options": "Prevents clickjacking by blocking framing",
        "X-XSS-Protection": "Enables browser XSS filtering",
        "Strict-Transport-Security": "Forces HTTPS connections",
        "Content-Security-Policy": "Prevents code injection attacks",
        "Referrer-Policy": "Controls referrer information leakage",
        "Permissions-Policy": "Controls browser feature access",
        "X-Request-ID": "Unique identifier for request tracing",
    }

    return SecurityHeaders(headers=dict(headers_info.items()), description=headers_info)


# ============================================================================
# PUBLIC ENDPOINTS (NO CSRF PROTECTION)
# ============================================================================


@app.get("/")
async def security_overview():
    """Public homepage showing security configuration."""
    security_info = get_security_info()

    return {
        "message": "[*] Welcome to Zenith Security Middleware Demo",
        "security": security_info.model_dump(),
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "/secure": "CSRF-protected page (GET for token, POST for action)",
            "/api/secure": "CSRF-protected API endpoint",
            "/headers": "View all security headers",
            "/metrics": "Request metrics and correlation info",
        },
        "csrf_note": "CSRF protection is active. Use /secure to get a token.",
        "security_note": "Check response headers to see security measures in action.",
    }


@app.get("/headers")
async def view_security_headers():
    """Show all security headers and their descriptions."""
    headers_info = describe_security_headers()

    return {
        "message": "[*] Security Headers Information",
        "headers_applied": headers_info.headers,
        "descriptions": headers_info.description,
        "note": "These headers are automatically applied to all responses",
        "production_tips": [
            "Set force_https=True in production",
            "Use secure=True for cookies with HTTPS",
            "Customize CSP policy for your specific needs",
            "Monitor CSP violations in production",
            "Use HSTS preload list for maximum security",
        ],
    }


@app.get("/metrics")
async def request_metrics():
    """Show request correlation and basic metrics."""
    return {
        "message": "[*] Request Metrics & Correlation",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "request_id": "Every request gets unique X-Request-ID header",
            "compression": "Responses compressed automatically",
            "security_headers": "All responses include security headers",
            "csrf_protection": "POST/PUT/DELETE require CSRF tokens",
        },
        "monitoring_tips": [
            "Use X-Request-ID for log correlation",
            "Monitor security header violations",
            "Track CSRF token validation failures",
            "Measure compression ratios",
            "Alert on security policy violations",
        ],
    }


# ============================================================================
# CSRF-PROTECTED ENDPOINTS
# ============================================================================


@app.get("/secure")
async def secure_page():
    """CSRF-protected page - provides token for subsequent requests."""
    return {
        "message": "[*] Secure Page - CSRF Protection Active",
        "csrf_info": {
            "token_location": "Check 'csrf_token' cookie in browser",
            "header_name": "X-CSRF-Token",
            "usage": "Include token in X-CSRF-Token header for POST requests",
        },
        "test_endpoints": {
            "POST /api/secure": "Try posting to this endpoint with CSRF token"
        },
        "example_curl": (
            "curl -X POST http://localhost:8001/api/secure "
            "-H 'X-CSRF-Token: YOUR_TOKEN_HERE' "
            "-H 'Content-Type: application/json' "
            '-d \'{"message": "Hello from secure endpoint"}\''
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/secure")
async def secure_api(data: SecureData):
    """CSRF-protected API endpoint."""
    return {
        "message": "Secure API Request Successful!",
        "received_data": data.model_dump(),
        "security_checks": {
            "csrf_validated": "CSRF token validated",
            "headers_applied": "Security headers added",
            "request_logged": "Request logged with correlation ID",
            "response_compressed": "Response will be compressed if eligible",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# SECURITY INFORMATION FOR DEVELOPERS
# ============================================================================


def get_csrf_error_info():
    """Get information about CSRF errors for developers."""
    return {
        "error": "CSRF Protection Error",
        "message": "Invalid or missing CSRF token",
        "help": {
            "1": "Visit GET /secure to obtain a CSRF token",
            "2": "Include token in X-CSRF-Token header",
            "3": "Check that csrf_token cookie is present",
            "4": "Ensure Content-Type is application/json for API calls",
        },
        "security_note": "This error indicates CSRF protection is working correctly",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# PRODUCTION SECURITY CHECKLIST
# ============================================================================

PRODUCTION_CHECKLIST = """
🏭 PRODUCTION SECURITY CHECKLIST

Security Headers:
   - HSTS with preload enabled
   - CSP configured for your specific needs
   - X-Frame-Options set to DENY
   - X-Content-Type-Options: nosniff

CSRF Protection:
   - Enabled for state-changing operations
   - Secure token generation
   - Proper token validation

HTTPS Configuration:
   - Force HTTPS in production (force_https=True)
   - Secure cookies (secure=True)
   - HSTS headers configured

Compression:
   - Enabled for appropriate content types
   - Configured compression thresholds
   - Monitoring compression ratios

Request Tracking:
   - Unique request IDs for correlation
   - Comprehensive request logging
   - Structured log format

[*] Environment Variables:
   - SECRET_KEY: Strong random key for CSRF
   - HTTPS_ENABLED: Enable HTTPS enforcement
   - SECURITY_LEVEL: Development/staging/production

[*] Monitoring:
   - CSP violation reports
   - CSRF token failures
   - Security header compliance
   - Request correlation tracking
"""

print(PRODUCTION_CHECKLIST)


if __name__ == "__main__":
    print("[*] Starting Zenith Security Middleware Demo")
    print("Visit: http://localhost:8001")
    print("Try the different endpoints to see security features in action!")
    print("\n" + PRODUCTION_CHECKLIST)

    app.run(host="127.0.0.1", port=8001, reload=True)
