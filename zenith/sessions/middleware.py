"""
Session middleware for Zenith applications.

Integrates session management into the request/response cycle.
"""

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from zenith.sessions.cookie import CookieSessionStore
from zenith.sessions.manager import SessionManager

logger = logging.getLogger("zenith.sessions.middleware")


class SessionMiddleware:
    """
    Session middleware for automatic session handling.

    Features:
    - Automatic session loading from cookies
    - Session creation for new users
    - Cookie setting/clearing
    - Session cleanup on response
    - Integration with Zenith's dependency injection
    """

    def __init__(
        self,
        app: ASGIApp,
        session_manager: SessionManager,
        auto_create: bool = True,
    ):
        """
        Initialize session middleware.

        Args:
            app: ASGI application
            session_manager: Session manager instance
            auto_create: Automatically create sessions for new users
        """
        self.app = app
        self.session_manager = session_manager
        self.auto_create = auto_create

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with session handling."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object to work with cookies
        request = Request(scope, receive)

        # Load session from cookie
        session = await self._load_session(request)

        # Add session to scope for Starlette compatibility
        scope["session"] = session

        # Also add to state for our own access patterns
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["session"] = session

        # Track if response has been started
        response_started = False
        session_to_save = session

        # Wrap send to handle session saving and cookie setting
        async def send_wrapper(message):
            nonlocal response_started, session_to_save

            if message["type"] == "http.response.start" and not response_started:
                response_started = True

                # Only set cookie if session is new or modified
                should_set_cookie = False

                if session_to_save:
                    # Check if we need to set cookie BEFORE saving (save calls mark_clean)
                    should_set_cookie = session_to_save.is_dirty or session_to_save.is_new

                    # Save session if dirty or new
                    if should_set_cookie:
                        await self.session_manager.save_session(session_to_save)

                    if should_set_cookie:
                        # Get cookie configuration
                        cookie_config = self.session_manager.get_cookie_config()

                        # Determine cookie value
                        if isinstance(self.session_manager.store, CookieSessionStore):
                            # For cookie sessions, get the encoded cookie value
                            cookie_value = self.session_manager.store.get_cookie_value(
                                session_to_save
                            )
                        else:
                            # For Redis/DB sessions, set the session ID
                            cookie_value = session_to_save.session_id

                        if cookie_value:
                            # Add session cookie to response headers
                            cookie_name = self.session_manager.cookie_name

                            # Build cookie string
                            cookie_parts = [f"{cookie_name}={cookie_value}"]

                            # Add cookie attributes
                            if cookie_config.get("max_age"):
                                cookie_parts.append(
                                    f"Max-Age={cookie_config['max_age']}"
                                )
                            if cookie_config.get("path"):
                                cookie_parts.append(f"Path={cookie_config['path']}")
                            if cookie_config.get("domain"):
                                cookie_parts.append(f"Domain={cookie_config['domain']}")
                            if cookie_config.get("secure"):
                                cookie_parts.append("Secure")
                            if cookie_config.get("httponly"):
                                cookie_parts.append("HttpOnly")
                            if cookie_config.get("samesite"):
                                cookie_parts.append(
                                    f"SameSite={cookie_config['samesite']}"
                                )

                            cookie_header = "; ".join(cookie_parts).encode("latin-1")

                            # Add to headers
                            headers = list(message.get("headers", []))
                            headers.append((b"set-cookie", cookie_header))
                            message["headers"] = headers

                            logger.debug(
                                f"Set session cookie for {session_to_save.session_id} (new={session_to_save.is_new}, dirty={session_to_save.is_dirty})"
                            )

            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _load_session(self, request: Request) -> Any:
        """Load session from request cookie."""
        cookie_name = self.session_manager.cookie_name
        session_id = request.cookies.get(cookie_name)

        session = None

        if session_id:
            # Try to load existing session
            if isinstance(self.session_manager.store, CookieSessionStore):
                # For cookie sessions, the "session_id" is actually the cookie value
                session = await self.session_manager.get_session(session_id)
            else:
                # For Redis/DB sessions, session_id is the key
                session = await self.session_manager.get_session(session_id)

        # Create new session if needed
        if not session and self.auto_create:
            session = await self.session_manager.create_session()
            logger.debug(f"Created new session {session.session_id}")

        return session

    async def _save_session(
        self, request: Request, response: Response, session: Any
    ) -> None:
        """Save session and set cookie."""
        if not session:
            return

        # Save session if dirty
        await self.session_manager.save_session(session)

        # Set cookie
        cookie_config = self.session_manager.get_cookie_config()

        if isinstance(self.session_manager.store, CookieSessionStore):
            # For cookie sessions, get the encoded cookie value
            cookie_value = self.session_manager.store.get_cookie_value(session)
            if cookie_value:
                response.set_cookie(value=cookie_value, **cookie_config)
        else:
            # For Redis/DB sessions, set the session ID
            response.set_cookie(value=session.session_id, **cookie_config)

        logger.debug(f"Set session cookie for {session.session_id}")


def get_session(request: Request) -> Any:
    """
    Get session from request.

    This function can be used for dependency injection:

    @app.get("/profile")
    async def profile(session = Depends(get_session)):
        user_id = session.get("user_id")
        return {"user_id": user_id}
    """
    # Try Starlette's standard location first
    if "session" in request.scope:
        return request.scope["session"]

    # Try request.state for compatibility
    if hasattr(request.state, "session"):
        return request.state.session

    # Fall back to scope state
    return request.scope.get("state", {}).get("session", None)


# Zenith-specific session dependency
class Session:
    """
    Session dependency marker for Zenith's dependency injection.

    Usage:
        from zenith.sessions import Session

        @app.get("/profile")
        async def profile(session = Session()):
            user_id = session.get("user_id")
            return {"user_id": user_id}
    """

    def __init__(self):
        self.required = True

    def __call__(self, request: Request) -> Any:
        # Try Starlette's standard location first
        session = request.scope.get("session")
        if session is None:
            # Try request.state for compatibility
            session = getattr(request.state, "session", None)
        if session is None:
            # Fall back to scope state
            session = request.scope.get("state", {}).get("session", None)

        if not session and self.required:
            raise RuntimeError(
                "No session available. Make sure SessionMiddleware is installed."
            )
        return session
