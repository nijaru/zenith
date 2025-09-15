"""
CSRF (Cross-Site Request Forgery) protection middleware.

Provides comprehensive CSRF protection for forms and AJAX requests
with configurable token generation and validation.
"""

import hashlib
import hmac
import secrets
import time

from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_403_FORBIDDEN
from starlette.types import ASGIApp, Receive, Scope, Send


class CSRFError(Exception):
    """CSRF validation error."""

    pass


class CSRFConfig:
    """Configuration for CSRF middleware."""

    def __init__(
        self,
        secret_key: str,
        token_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        cookie_name: str = "csrf_token",
        cookie_secure: bool = True,
        cookie_httponly: bool = False,
        cookie_samesite: str = "Lax",
        max_age_seconds: int = 3600,  # 1 hour
        exempt_methods: set[str] | None = None,
        exempt_paths: set[str] | None = None,
        require_token: bool = True,
    ):
        if len(secret_key) < 32:
            raise ValueError("CSRF secret key must be at least 32 characters long")

        self.secret_key = secret_key
        self.token_name = token_name
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self.max_age_seconds = max_age_seconds
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS", "TRACE"}
        self.exempt_paths = exempt_paths or set()
        self.require_token = require_token


class CSRFMiddleware:
    """
    CSRF protection middleware.

    Features:
    - Token generation and validation
    - Configurable exempt methods and paths
    - Cookie and header token support
    - Time-based token expiration
    - Secure token generation using secrets
    """

    def __init__(
        self,
        app: ASGIApp,
        config: CSRFConfig | None = None,
        # Individual parameters (for backward compatibility)
        *,
        secret_key: str | None = None,
        token_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        cookie_name: str = "csrf_token",
        cookie_secure: bool = True,
        cookie_httponly: bool = False,
        cookie_samesite: str = "Lax",
        max_age_seconds: int = 3600,  # 1 hour
        exempt_methods: set[str] | None = None,
        exempt_paths: set[str] | None = None,
        require_token: bool = True,
    ):
        """
        Initialize CSRF middleware.

        Args:
            app: ASGI application
            config: CSRF configuration object
            secret_key: Secret key for token signing (must be >=32 chars)
            token_name: Form field name for CSRF token
            header_name: HTTP header name for CSRF token
            cookie_name: Cookie name for CSRF token
            cookie_secure: Use secure cookies (HTTPS only)
            cookie_httponly: Make cookies HTTP-only
            cookie_samesite: SameSite cookie attribute
            max_age_seconds: Token lifetime in seconds
            exempt_methods: HTTP methods exempt from CSRF
            exempt_paths: URL paths exempt from CSRF
            require_token: Whether to require CSRF tokens
        """
        self.app = app

        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.secret_key = config.secret_key.encode()
            self.token_name = config.token_name
            self.header_name = config.header_name
            self.cookie_name = config.cookie_name
            self.cookie_secure = config.cookie_secure
            self.cookie_httponly = config.cookie_httponly
            self.cookie_samesite = config.cookie_samesite
            self.max_age_seconds = config.max_age_seconds
            self.exempt_methods = config.exempt_methods
            self.exempt_paths = config.exempt_paths
            self.require_token = config.require_token
        else:
            if secret_key is None:
                raise ValueError("secret_key is required when not using config object")

            if len(secret_key) < 32:
                raise ValueError("CSRF secret key must be at least 32 characters long")

            self.secret_key = secret_key.encode()
            self.token_name = token_name
            self.header_name = header_name
            self.cookie_name = cookie_name
            self.cookie_secure = cookie_secure
            self.cookie_httponly = cookie_httponly
            self.cookie_samesite = cookie_samesite
            self.max_age_seconds = max_age_seconds
            self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS", "TRACE"}
            self.exempt_paths = exempt_paths or set()
            self.require_token = require_token

    def _generate_token(self, user_agent: str = "", remote_addr: str = "") -> str:
        """
        Generate a CSRF token.

        Token format: timestamp:random:signature
        """
        timestamp = str(int(time.time()))
        random_part = secrets.token_urlsafe(16)

        # Create signature based on timestamp, random part, user agent, and IP
        message = f"{timestamp}:{random_part}:{user_agent}:{remote_addr}"
        signature = hmac.new(
            self.secret_key, message.encode(), hashlib.sha256
        ).hexdigest()

        return f"{timestamp}:{random_part}:{signature}"

    def _validate_token(
        self, token: str, user_agent: str = "", remote_addr: str = ""
    ) -> bool:
        """Validate a CSRF token."""
        try:
            timestamp_str, random_part, signature = token.split(":", 2)
            timestamp = int(timestamp_str)
        except (ValueError, IndexError):
            return False

        # Check token age
        if time.time() - timestamp > self.max_age_seconds:
            return False

        # Verify signature
        message = f"{timestamp_str}:{random_part}:{user_agent}:{remote_addr}"
        expected_signature = hmac.new(
            self.secret_key, message.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def _get_token_from_request(self, request: Request) -> str | None:
        """Extract CSRF token from request (deprecated - use async version)."""
        # Try headers only (form data requires async)
        return request.headers.get(self.header_name)

    def _should_exempt(self, request: Request) -> bool:
        """Check if request should be exempt from CSRF protection."""
        # Check method exemptions
        if request.method in self.exempt_methods:
            return True

        # Check path exemptions
        path = request.url.path
        if path in self.exempt_paths:
            return True

        # Check path patterns
        for exempt_path in self.exempt_paths:
            if exempt_path.endswith("*") and path.startswith(exempt_path[:-1]):
                return True

        return False

    def _get_client_info(self, request: Request) -> tuple[str, str]:
        """Get client user agent and IP address."""
        user_agent = request.headers.get("User-Agent", "")

        # Get real IP (considering proxies)
        remote_addr = request.headers.get("X-Forwarded-For", "")
        if remote_addr:
            remote_addr = remote_addr.split(",")[0].strip()
        else:
            remote_addr = request.headers.get("X-Real-IP", "")

        if not remote_addr and request.client:
            remote_addr = request.client.host

        return user_agent, remote_addr or "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with CSRF protection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip CSRF for exempt requests
        if self._should_exempt(request):
            await self._handle_exempt_request(request, scope, receive, send)
            return

        # Get client information
        user_agent, remote_addr = self._get_client_info(request)

        # Get existing token from cookie
        existing_token = request.cookies.get(self.cookie_name)

        if self.require_token:
            # Get token from request (need to read form data if POST)
            submitted_token = await self._get_token_from_request_async(request)

            # Validate submitted token
            if not submitted_token:
                await self._send_csrf_error(send, "CSRF token missing")
                return

            if not self._validate_token(submitted_token, user_agent, remote_addr):
                await self._send_csrf_error(send, "CSRF token invalid or expired")
                return

        # Process request with CSRF cookie handling
        await self._handle_protected_request(
            request, scope, receive, send, existing_token, user_agent, remote_addr
        )

    async def _handle_exempt_request(
        self, request: Request, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Handle exempt requests with CSRF cookie setting."""
        await self._handle_request_with_csrf_cookie(
            request, scope, receive, send, None, None, None
        )

    async def _handle_protected_request(
        self,
        request: Request,
        scope: Scope,
        receive: Receive,
        send: Send,
        existing_token: str | None,
        user_agent: str,
        remote_addr: str,
    ) -> None:
        """Handle protected requests with CSRF validation and cookie setting."""
        await self._handle_request_with_csrf_cookie(
            request, scope, receive, send, existing_token, user_agent, remote_addr
        )

    async def _handle_request_with_csrf_cookie(
        self,
        request: Request,
        scope: Scope,
        receive: Receive,
        send: Send,
        existing_token: str | None,
        user_agent: str | None,
        remote_addr: str | None,
    ) -> None:
        """Handle request and set CSRF cookie on response."""
        if user_agent is None or remote_addr is None:
            user_agent, remote_addr = self._get_client_info(request)

        # Determine if we need a new token
        new_token = None
        if not existing_token or not self._validate_token(
            existing_token, user_agent, remote_addr
        ):
            new_token = self._generate_token(user_agent, remote_addr)

        async def send_wrapper(message):
            if message["type"] == "http.response.start" and new_token:
                # Add CSRF cookie to response headers
                headers = list(message.get("headers", []))

                # Create cookie header
                cookie_value = f"{self.cookie_name}={new_token}"
                if self.cookie_secure:
                    cookie_value += "; Secure"
                if self.cookie_httponly:
                    cookie_value += "; HttpOnly"
                if self.cookie_samesite:
                    cookie_value += f"; SameSite={self.cookie_samesite}"
                cookie_value += f"; Max-Age={self.max_age_seconds}"

                headers.append((b"set-cookie", cookie_value.encode("latin-1")))
                headers.append((b"x-csrf-token", new_token.encode("latin-1")))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _send_csrf_error(self, send: Send, error_message: str) -> None:
        """Send CSRF error response."""
        response_body = f'{{"error": "{error_message}"}}'.encode()

        await send(
            {
                "type": "http.response.start",
                "status": HTTP_403_FORBIDDEN,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(response_body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": response_body})

    async def _get_token_from_request_async(self, request: Request) -> str | None:
        """Extract CSRF token from request (async version for form data)."""
        # Try headers first (most common for AJAX)
        token = request.headers.get(self.header_name)
        if token:
            return token

        # Try form data for POST requests
        from zenith.core.patterns import HTTP_POST

        if request.method == HTTP_POST:
            try:
                form_data = await request.form()
                token = form_data.get(self.token_name)
                if token:
                    return str(token)
            except Exception:
                # Form parsing failed, continue to other methods
                pass

        return None

    def _set_csrf_cookie(
        self,
        request: Request,
        response: Response,
        existing_token: str | None = None,
        user_agent: str | None = None,
        remote_addr: str | None = None,
    ) -> Response:
        """Set CSRF token cookie on response (deprecated - handled in ASGI wrapper)."""
        if user_agent is None or remote_addr is None:
            user_agent, remote_addr = self._get_client_info(request)

        # Generate new token if needed
        if not existing_token or not self._validate_token(
            existing_token, user_agent, remote_addr
        ):
            new_token = self._generate_token(user_agent, remote_addr)

            response.set_cookie(
                self.cookie_name,
                new_token,
                secure=self.cookie_secure,
                httponly=self.cookie_httponly,
                samesite=self.cookie_samesite,
                max_age=self.max_age_seconds,
            )

            # Also add token to response headers for AJAX requests
            response.headers["X-CSRF-Token"] = new_token

        return response


# Convenience functions
def create_csrf_middleware(
    secret_key: str, exempt_paths: list[str] | None = None, **kwargs
) -> CSRFMiddleware:
    """
    Create CSRF protection middleware with common defaults.

    Args:
        secret_key: Secret key for CSRF token generation (min 32 characters)
        exempt_paths: Additional paths to exempt from CSRF protection
        **kwargs: Additional arguments passed to CSRFMiddleware

    Returns:
        Configured CSRFMiddleware instance with common exempt paths
    """
    exempt_paths_set = set(exempt_paths or [])

    # Add common exempt paths
    exempt_paths_set.update(
        {
            "/health",
            "/metrics",
            "/api/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    )

    return CSRFMiddleware(
        app=None,  # Will be set by framework
        secret_key=secret_key,
        exempt_paths=exempt_paths_set,
        **kwargs,
    )


def get_csrf_token(request: Request) -> str | None:
    """Get CSRF token from request cookie."""
    return request.cookies.get("csrf_token")
