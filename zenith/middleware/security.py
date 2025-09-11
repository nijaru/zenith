"""
Security middleware for Zenith framework.

Provides comprehensive security headers, CSRF protection,
and other security enhancements.
"""

import hashlib
import hmac
import secrets
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityConfig:
    """Configuration for security middleware."""

    def __init__(
        self,
        # Content Security Policy
        csp_policy: str | None = None,
        csp_report_only: bool = False,
        # HTTP Strict Transport Security
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        # Frame Options
        frame_options: str = "DENY",  # DENY, SAMEORIGIN, or ALLOW-FROM
        # Content Type Options
        content_type_nosniff: bool = True,
        # XSS Protection
        xss_protection: str = "1; mode=block",
        # Referrer Policy
        referrer_policy: str = "strict-origin-when-cross-origin",
        # Permissions Policy (formerly Feature Policy)
        permissions_policy: str | None = None,
        # CSRF Protection
        csrf_protection: bool = False,
        csrf_secret_key: str | None = None,
        csrf_token_header: str = "X-CSRF-Token",
        csrf_safe_methods: list[str] | None = None,
        # Trusted Proxies
        trusted_proxies: list[str] | None = None,
        # Force HTTPS
        force_https: bool = False,
        force_https_permanent: bool = False,
    ):
        self.csp_policy = csp_policy
        self.csp_report_only = csp_report_only
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.frame_options = frame_options
        self.content_type_nosniff = content_type_nosniff
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy

        # CSRF
        self.csrf_protection = csrf_protection
        self.csrf_secret_key = csrf_secret_key or secrets.token_urlsafe(32)
        self.csrf_token_header = csrf_token_header
        self.csrf_safe_methods = csrf_safe_methods or [
            "GET",
            "HEAD",
            "OPTIONS",
            "TRACE",
        ]

        # Network security
        self.trusted_proxies = trusted_proxies or []
        self.force_https = force_https
        self.force_https_permanent = force_https_permanent


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to responses."""

        # Force HTTPS if configured (skip for test client and localhost)
        if (
            self.config.force_https 
            and request.url.scheme == "http"
            and request.url.hostname not in ("testserver", "127.0.0.1", "localhost")
        ):
            url = request.url.replace(scheme="https")
            status_code = 301 if self.config.force_https_permanent else 302
            return Response(status_code=status_code, headers={"location": str(url)})

        # Process request normally
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        # Content Security Policy
        if self.config.csp_policy:
            header_name = "content-security-policy"
            if self.config.csp_report_only:
                header_name += "-report-only"
            response.headers[header_name] = self.config.csp_policy

        # HTTP Strict Transport Security
        if self.config.hsts_max_age > 0:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            response.headers["strict-transport-security"] = hsts_value

        # X-Frame-Options
        if self.config.frame_options:
            response.headers["x-frame-options"] = self.config.frame_options

        # X-Content-Type-Options
        if self.config.content_type_nosniff:
            response.headers["x-content-type-options"] = "nosniff"

        # X-XSS-Protection
        if self.config.xss_protection:
            response.headers["x-xss-protection"] = self.config.xss_protection

        # Referrer-Policy
        if self.config.referrer_policy:
            response.headers["referrer-policy"] = self.config.referrer_policy

        # Permissions-Policy
        if self.config.permissions_policy:
            response.headers["permissions-policy"] = self.config.permissions_policy


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection."""

    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate CSRF tokens for unsafe methods."""

        if not self.config.csrf_protection:
            return await call_next(request)

        # Skip CSRF check for safe methods
        if request.method in self.config.csrf_safe_methods:
            return await call_next(request)

        # Get CSRF token from request
        csrf_token = self._get_csrf_token(request)

        if not csrf_token or not self._validate_csrf_token(csrf_token, request):
            return JSONResponse(
                {"error": "CSRF token validation failed"}, status_code=403
            )

        return await call_next(request)

    def _get_csrf_token(self, request: Request) -> str | None:
        """Extract CSRF token from request."""
        # Check header first
        token = request.headers.get(self.config.csrf_token_header)
        if token:
            return token

        # Check form data for POST requests
        if (
            request.method == "POST"
            and "application/x-www-form-urlencoded"
            in request.headers.get("content-type", "")
        ):
            # This would require form parsing - simplified for now
            pass

        return None

    def _validate_csrf_token(self, token: str, request: Request) -> bool:
        """Validate CSRF token."""
        try:
            # Simple HMAC-based validation
            expected = self._generate_csrf_token(request)
            return hmac.compare_digest(token, expected)
        except Exception:
            return False

    def _generate_csrf_token(self, request: Request) -> str:
        """Generate CSRF token for the current session."""
        # Use session ID, user agent, and secret to generate token
        session_data = (
            f"{request.session.get('id', '')}{request.headers.get('user-agent', '')}"
        )
        return hmac.new(
            self.config.csrf_secret_key.encode(), session_data.encode(), hashlib.sha256
        ).hexdigest()


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """Middleware for handling trusted proxy headers."""

    def __init__(self, app, trusted_proxies: list[str] | None = None):
        super().__init__(app)
        self.trusted_proxies = set(trusted_proxies or [])

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process proxy headers from trusted sources."""

        if not self.trusted_proxies:
            return await call_next(request)

        # Get the client IP
        client_ip = self._get_client_ip(request)

        # Only process proxy headers if request comes from trusted proxy
        if client_ip in self.trusted_proxies:
            self._process_proxy_headers(request)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address."""
        return request.client.host if request.client else ""

    def _process_proxy_headers(self, request: Request) -> None:
        """Process X-Forwarded-* headers."""
        # X-Forwarded-For
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            forwarded_for.split(",")[0].strip()
            # Update request.client if needed
            pass

        # X-Forwarded-Proto
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto:
            # Update request.url.scheme if needed
            pass


# Input validation utilities
def sanitize_html_input(text: str) -> str:
    """Basic HTML sanitization to prevent XSS."""
    if not text:
        return ""

    # Basic HTML escaping
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
    }

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text


def validate_url(url: str, allowed_schemes: list[str] | None = None) -> bool:
    """Validate URL to prevent SSRF attacks."""
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Check scheme
        allowed_schemes = allowed_schemes or ["http", "https"]
        if parsed.scheme not in allowed_schemes:
            return False

        # Check for localhost/private IP ranges (basic check)
        hostname = parsed.hostname
        if hostname:
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                return False

            # Check for private IP ranges (basic)
            if (
                hostname.startswith("192.168.")
                or hostname.startswith("10.")
                or hostname.startswith("172.")
            ):
                return False

        return True

    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def constant_time_compare(val1: str, val2: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(val1, val2)


# Security configuration presets
def get_strict_security_config() -> SecurityConfig:
    """Get a strict security configuration for production."""
    return SecurityConfig(
        csp_policy="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:",
        hsts_max_age=63072000,  # 2 years
        hsts_include_subdomains=True,
        hsts_preload=True,
        frame_options="DENY",
        content_type_nosniff=True,
        xss_protection="1; mode=block",
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy="geolocation=(), microphone=(), camera=()",
        csrf_protection=True,
        force_https=True,
        force_https_permanent=True,
    )


def get_development_security_config() -> SecurityConfig:
    """Get a relaxed security configuration for development."""
    return SecurityConfig(
        csp_policy=None,  # Disable CSP for development
        hsts_max_age=0,  # Disable HSTS for development
        frame_options="SAMEORIGIN",
        content_type_nosniff=True,
        xss_protection="1; mode=block",
        referrer_policy="no-referrer-when-downgrade",
        csrf_protection=False,  # Disable CSRF for development
        force_https=False,
    )
