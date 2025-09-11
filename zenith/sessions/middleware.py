"""
Session middleware for Zenith applications.

Integrates session management into the request/response cycle.
"""

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from zenith.sessions.cookie import CookieSessionStore
from zenith.sessions.manager import SessionManager

logger = logging.getLogger("zenith.sessions.middleware")


class SessionMiddleware(BaseHTTPMiddleware):
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
        app,
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
        super().__init__(app)
        self.session_manager = session_manager
        self.auto_create = auto_create

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process session for incoming requests."""

        # Load session from cookie
        session = await self._load_session(request)

        # Add session to request state
        request.state.session = session

        # Process request
        response = await call_next(request)

        # Save session changes
        await self._save_session(request, response, session)

        return response

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
        self,
        request: Request,
        response: Response,
        session: Any
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
    return getattr(request.state, "session", None)


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
        session = getattr(request.state, "session", None)
        if not session and self.required:
            raise RuntimeError(
                "No session available. Make sure SessionMiddleware is installed."
            )
        return session
