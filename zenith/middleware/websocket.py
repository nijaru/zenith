"""
WebSocket middleware for authentication and logging.

Provides middleware to secure and monitor WebSocket connections.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from zenith.logging import get_logger

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

logger = get_logger("zenith.websocket")


class WebSocketAuthMiddleware:
    """
    Middleware to authenticate WebSocket connections.

    Checks for a valid token before allowing the WebSocket handshake.
    Token can be passed via query parameter or header.

    Example:
        from zenith.middleware.websocket import WebSocketAuthMiddleware

        app.add_middleware(WebSocketAuthMiddleware, verify_token=my_verify_func)

        # Client connects with token:
        # ws://localhost:8000/ws?token=abc123
        # OR with header: Authorization: Bearer abc123
    """

    def __init__(
        self,
        app: ASGIApp,
        verify_token: callable | None = None,
        token_query_param: str = "token",
        allow_anonymous: bool = False,
        anonymous_paths: set[str] | None = None,
    ):
        """
        Initialize WebSocket auth middleware.

        Args:
            app: The ASGI application
            verify_token: Async function that takes token string and returns
                         user dict or None if invalid. If not provided, uses
                         default JWT verification from zenith.auth.
            token_query_param: Query parameter name for token (default "token")
            allow_anonymous: Allow connections without token (default False)
            anonymous_paths: Paths that don't require authentication
        """
        self.app = app
        self.verify_token = verify_token
        self.token_query_param = token_query_param
        self.allow_anonymous = allow_anonymous
        self.anonymous_paths = anonymous_paths or set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip auth for anonymous paths
        if path in self.anonymous_paths:
            await self.app(scope, receive, send)
            return

        # Extract token from query params or headers
        token = self._get_token(scope)

        if not token:
            if self.allow_anonymous:
                await self.app(scope, receive, send)
                return
            # Reject connection - close before accepting
            await self._reject_connection(scope, receive, send, 4001, "Missing token")
            return

        # Verify token
        user = await self._verify(token)
        if not user:
            await self._reject_connection(scope, receive, send, 4003, "Invalid token")
            return

        # Store user in scope state for handlers
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["user"] = user
        scope["state"]["user_id"] = user.get("id") or user.get("user_id")

        await self.app(scope, receive, send)

    def _get_token(self, scope: Scope) -> str | None:
        """Extract token from query params or Authorization header."""
        # Check query params first
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            params = dict(
                param.split("=", 1) for param in query_string.split("&") if "=" in param
            )
            if self.token_query_param in params:
                return params[self.token_query_param]

        # Check Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        return None

    async def _verify(self, token: str) -> dict[str, Any] | None:
        """Verify the token and return user info."""
        if self.verify_token:
            result = self.verify_token(token)
            # Handle both sync and async verify functions
            if hasattr(result, "__await__"):
                return await result
            return result

        # Default: use Zenith's JWT verification
        try:
            from zenith.auth import extract_user_from_token

            return extract_user_from_token(token)
        except Exception:
            return None

    async def _reject_connection(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        code: int,
        reason: str,
    ) -> None:
        """Reject WebSocket connection with close code."""
        # Wait for connection request
        while True:
            message = await receive()
            if message["type"] == "websocket.connect":
                break
            if message["type"] == "websocket.disconnect":
                return

        # Send close without accepting
        await send({"type": "websocket.close", "code": code, "reason": reason})

        logger.warning(
            "websocket_auth_rejected",
            path=scope.get("path"),
            code=code,
            reason=reason,
        )


class WebSocketLoggingMiddleware:
    """
    Middleware to log WebSocket connections and activity.

    Logs connection events, disconnections, and optionally message activity.

    Example:
        from zenith.middleware.websocket import WebSocketLoggingMiddleware

        app.add_middleware(WebSocketLoggingMiddleware, log_messages=False)
    """

    def __init__(
        self,
        app: ASGIApp,
        log_messages: bool = False,
        log_message_content: bool = False,
    ):
        """
        Initialize WebSocket logging middleware.

        Args:
            app: The ASGI application
            log_messages: Log individual message events (default False)
            log_message_content: Include message content in logs (default False)
        """
        self.app = app
        self.log_messages = log_messages
        self.log_message_content = log_message_content

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface."""
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        client = scope.get("client", ("unknown", 0))
        client_ip = client[0] if client else "unknown"
        start_time = time.perf_counter()

        # Track connection state
        connected = False
        message_count = {"received": 0, "sent": 0}

        async def receive_wrapper():
            nonlocal connected
            message = await receive()

            if message["type"] == "websocket.connect":
                logger.info(
                    "websocket_connecting",
                    path=path,
                    client_ip=client_ip,
                )
            elif message["type"] == "websocket.receive":
                message_count["received"] += 1
                if self.log_messages:
                    log_data = {"path": path, "direction": "receive"}
                    if self.log_message_content:
                        if "text" in message:
                            log_data["content"] = message["text"][:200]
                        elif "bytes" in message:
                            log_data["bytes_length"] = len(message["bytes"])
                    logger.debug("websocket_message", **log_data)
            elif message["type"] == "websocket.disconnect":
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.info(
                    "websocket_disconnected",
                    path=path,
                    client_ip=client_ip,
                    duration_ms=duration_ms,
                    messages_received=message_count["received"],
                    messages_sent=message_count["sent"],
                )

            return message

        async def send_wrapper(message):
            nonlocal connected

            if message["type"] == "websocket.accept":
                connected = True
                logger.info(
                    "websocket_connected",
                    path=path,
                    client_ip=client_ip,
                    user_id=scope.get("state", {}).get("user_id"),
                )
            elif message["type"] == "websocket.send":
                message_count["sent"] += 1
                if self.log_messages:
                    log_data = {"path": path, "direction": "send"}
                    if self.log_message_content:
                        if "text" in message:
                            log_data["content"] = message["text"][:200]
                        elif "bytes" in message:
                            log_data["bytes_length"] = len(message["bytes"])
                    logger.debug("websocket_message", **log_data)
            elif message["type"] == "websocket.close":
                if connected:
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    logger.info(
                        "websocket_closed",
                        path=path,
                        client_ip=client_ip,
                        code=message.get("code", 1000),
                        duration_ms=duration_ms,
                        messages_received=message_count["received"],
                        messages_sent=message_count["sent"],
                    )

            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "websocket_error",
                path=path,
                client_ip=client_ip,
                error=str(e),
                duration_ms=duration_ms,
            )
            raise


__all__ = [
    "WebSocketAuthMiddleware",
    "WebSocketLoggingMiddleware",
]
