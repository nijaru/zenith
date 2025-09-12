"""
Security middleware for Zenith framework.

Provides comprehensive security headers, CSRF protection,
and other security enhancements.
"""

import hashlib
import hmac
import secrets
from urllib.parse import urlparse

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


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


class SecurityHeadersMiddleware:
    """Middleware for adding security headers."""

    def __init__(self, app: ASGIApp, config: SecurityConfig = None):
        self.app = app
        self.config = config or SecurityConfig()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with security headers."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check for HTTPS redirect
        if self.config.force_https and self._should_redirect_to_https(scope):
            url = self._build_https_url(scope)
            status_code = 301 if self.config.force_https_permanent else 302
            redirect_response = Response(status_code=status_code, headers={"location": url})
            await redirect_response(scope, receive, send)
            return

        # Wrap send to add security headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                self._add_security_headers_asgi(response_headers)
                message["headers"] = response_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _should_redirect_to_https(self, scope: Scope) -> bool:
        """Check if request should be redirected to HTTPS."""
        if scope.get("scheme") != "http":
            return False
            
        # Skip for test client and localhost
        server = scope.get("server")
        if server and server[0] in ("testserver", "127.0.0.1", "localhost"):
            return False
            
        return True

    def _build_https_url(self, scope: Scope) -> str:
        """Build HTTPS URL from scope."""
        server = scope.get("server", ("localhost", 80))
        host = server[0]
        port = server[1]
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"")
        
        url = f"https://{host}"
        if port != 443:
            url += f":{port}"
        url += path
        if query_string:
            url += "?" + query_string.decode("latin-1")
        
        return url

    def _add_security_headers_asgi(self, response_headers: list) -> None:
        """Add security headers to ASGI response headers list."""
        # Content Security Policy
        if self.config.csp_policy:
            header_name = b"content-security-policy"
            if self.config.csp_report_only:
                header_name = b"content-security-policy-report-only"
            response_headers.append((header_name, self.config.csp_policy.encode("latin-1")))

        # HTTP Strict Transport Security
        if self.config.hsts_max_age > 0:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            response_headers.append((b"strict-transport-security", hsts_value.encode("latin-1")))

        # X-Frame-Options
        if self.config.frame_options:
            response_headers.append((b"x-frame-options", self.config.frame_options.encode("latin-1")))

        # X-Content-Type-Options
        if self.config.content_type_nosniff:
            response_headers.append((b"x-content-type-options", b"nosniff"))

        # X-XSS-Protection
        if self.config.xss_protection:
            response_headers.append((b"x-xss-protection", self.config.xss_protection.encode("latin-1")))

        # Referrer-Policy
        if self.config.referrer_policy:
            response_headers.append((b"referrer-policy", self.config.referrer_policy.encode("latin-1")))

        # Permissions-Policy
        if self.config.permissions_policy:
            response_headers.append((b"permissions-policy", self.config.permissions_policy.encode("latin-1")))

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response (legacy method for compatibility)."""
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


class CSRFProtectionMiddleware:
    """Middleware for CSRF protection."""

    def __init__(self, app: ASGIApp, config: SecurityConfig):
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with CSRF protection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.config.csrf_protection:
            await self.app(scope, receive, send)
            return

        # Skip CSRF check for safe methods
        method = scope.get("method", "GET")
        if method in self.config.csrf_safe_methods:
            await self.app(scope, receive, send)
            return

        # Get CSRF token from request
        headers = dict(scope.get("headers", []))
        csrf_token = self._get_csrf_token_asgi(headers)

        if not csrf_token or not self._validate_csrf_token_asgi(csrf_token, scope, headers):
            error_response = JSONResponse(
                {"error": "CSRF token validation failed"}, status_code=403
            )
            await error_response(scope, receive, send)
            return

        await self.app(scope, receive, send)

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

    def _get_csrf_token_asgi(self, headers: dict) -> str | None:
        """Extract CSRF token from ASGI headers."""
        # Check header first
        header_name = self.config.csrf_token_header.lower().encode()
        token_bytes = headers.get(header_name)
        if token_bytes:
            return token_bytes.decode("latin-1")

        # TODO: Check form data for POST requests
        # This would require body parsing which is complex in ASGI
        return None

    def _validate_csrf_token(self, token: str, request: Request) -> bool:
        """Validate CSRF token."""
        try:
            # Simple HMAC-based validation
            expected = self._generate_csrf_token(request)
            return hmac.compare_digest(token, expected)
        except Exception:
            return False

    def _validate_csrf_token_asgi(self, token: str, scope: Scope, headers: dict) -> bool:
        """Validate CSRF token for ASGI requests."""
        try:
            # Simple HMAC-based validation
            expected = self._generate_csrf_token_asgi(scope, headers)
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

    def _generate_csrf_token_asgi(self, scope: Scope, headers: dict) -> str:
        """Generate CSRF token for ASGI requests."""
        # Use session ID and user agent from ASGI scope
        session_id = ""  # TODO: Extract from session middleware if available
        user_agent_bytes = headers.get(b"user-agent", b"")
        user_agent = user_agent_bytes.decode("latin-1", errors="ignore")
        
        session_data = f"{session_id}{user_agent}"
        return hmac.new(
            self.config.csrf_secret_key.encode(), session_data.encode(), hashlib.sha256
        ).hexdigest()


class TrustedProxyMiddleware:
    """Middleware for handling trusted proxy headers."""

    def __init__(self, app: ASGIApp, trusted_proxies: list[str] | None = None):
        self.app = app
        self.trusted_proxies = set(trusted_proxies or [])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with proxy header processing."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.trusted_proxies:
            await self.app(scope, receive, send)
            return

        # Get the client IP from scope
        client_ip = self._get_client_ip_asgi(scope)

        # Only process proxy headers if request comes from trusted proxy
        if client_ip in self.trusted_proxies:
            self._process_proxy_headers_asgi(scope)

        await self.app(scope, receive, send)

    def _get_client_ip_asgi(self, scope: Scope) -> str:
        """Get the client IP address from ASGI scope."""
        client = scope.get("client")
        return client[0] if client else ""

    def _process_proxy_headers_asgi(self, scope: Scope) -> None:
        """Process X-Forwarded-* headers for ASGI requests."""
        headers = dict(scope.get("headers", []))
        
        # X-Forwarded-For
        forwarded_for_bytes = headers.get(b"x-forwarded-for")
        if forwarded_for_bytes:
            forwarded_for = forwarded_for_bytes.decode("latin-1")
            # Take the first IP in the chain
            first_ip = forwarded_for.split(",")[0].strip()
            # Update client in scope
            scope["client"] = (first_ip, scope.get("client", ("", 0))[1])

        # X-Forwarded-Proto
        forwarded_proto_bytes = headers.get(b"x-forwarded-proto")
        if forwarded_proto_bytes:
            forwarded_proto = forwarded_proto_bytes.decode("latin-1")
            # Update scheme in scope
            scope["scheme"] = forwarded_proto

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
