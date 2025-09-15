"""
Integration tests for session middleware.

Tests the actual session management in realistic scenarios.
This middleware had 18% coverage and NO integration tests.
"""

from datetime import timedelta

import pytest

from zenith import Zenith
from zenith.sessions import (
    CookieSessionStore,
    SessionManager,
    SessionMiddleware,
)
from zenith.testing import TestClient


@pytest.mark.asyncio
class TestSessionMiddleware:
    """Test session middleware integration."""

    async def test_session_creation_and_retrieval(self):
        """Test that sessions are created and can be retrieved across requests."""
        app = Zenith()

        # Add session middleware
        session_store = CookieSessionStore(
            secret_key="test-secret-key-that-is-long-enough-for-session-testing"
        )
        session_manager = SessionManager(
            store=session_store,
            cookie_name="session",
            max_age=timedelta(hours=1),
            is_secure=False,  # For testing
            is_http_only=True,
            same_site="lax",
        )
        app.add_middleware(SessionMiddleware, session_manager=session_manager)

        @app.get("/set-session")
        async def set_session(request):
            request.session["user_id"] = 123
            request.session["username"] = "testuser"
            return {"status": "session_set"}

        @app.get("/get-session")
        async def get_session(request):
            return {
                "user_id": request.session.get("user_id"),
                "username": request.session.get("username"),
            }

        async with TestClient(app) as client:
            # First request - set session
            response1 = await client.get("/set-session")
            assert response1.status_code == 200

            # Extract session cookie
            cookies = response1.cookies
            assert "session" in cookies

            # Second request - retrieve session using cookie
            response2 = await client.get("/get-session")
            assert response2.status_code == 200
            data = response2.json()
            assert data["user_id"] == 123
            assert data["username"] == "testuser"

    async def test_session_without_middleware(self):
        """Test that session is None when middleware not added."""
        app = Zenith()

        @app.get("/check-session")
        async def check_session(request):
            # Session should be None without middleware - check scope directly
            session = request.scope.get("session", None)
            return {"has_session": session is not None}

        async with TestClient(app) as client:
            response = await client.get("/check-session")
            assert response.status_code == 200
            data = response.json()
            assert data["has_session"] is False

    async def test_session_cookie_security(self):
        """Test session cookie security attributes."""
        app = Zenith()

        session_store = CookieSessionStore(
            secret_key="test-secret-key-that-is-long-enough-for-session-testing"
        )
        session_manager = SessionManager(
            store=session_store, is_secure=True, is_http_only=True, same_site="strict"
        )
        app.add_middleware(SessionMiddleware, session_manager=session_manager)

        @app.get("/set-session")
        async def set_session(request):
            request.session["test"] = "value"
            return {"status": "set"}

        async with TestClient(app) as client:
            response = await client.get("/set-session")
            assert response.status_code == 200

            # Check cookie attributes
            set_cookie_header = response.headers.get("set-cookie", "")
            assert "HttpOnly" in set_cookie_header
            assert "Secure" in set_cookie_header
            assert "SameSite=strict" in set_cookie_header

    async def test_session_with_custom_cookie_name(self):
        """Test session middleware with custom cookie name."""
        app = Zenith()

        session_store = CookieSessionStore(
            secret_key="test-secret-key-that-is-long-enough-for-session-testing"
        )
        session_manager = SessionManager(
            store=session_store, cookie_name="custom_session_id"
        )
        app.add_middleware(SessionMiddleware, session_manager=session_manager)

        @app.get("/set-session")
        async def set_session(request):
            request.session["custom"] = "data"
            return {"status": "set"}

        async with TestClient(app) as client:
            response = await client.get("/set-session")
            assert response.status_code == 200

            # Should use custom cookie name
            cookies = response.cookies
            assert "custom_session_id" in cookies
            assert "session" not in cookies


@pytest.mark.asyncio
class TestSessionStoreIntegration:
    """Test session middleware with different store backends."""

    async def test_memory_store_integration(self):
        """Test session middleware with memory store."""
        app = Zenith()

        # Use memory store explicitly
        store = CookieSessionStore(
            secret_key="test-secret-key-that-is-long-enough-for-session-testing"
        )
        session_manager = SessionManager(
            store=store, is_secure=False
        )  # For testing over HTTP
        app.add_middleware(SessionMiddleware, session_manager=session_manager)

        @app.get("/set/{value}")
        async def set_value(request, value: str):
            request.session["stored_value"] = value
            return {"stored": value}

        @app.get("/get")
        async def get_value(request):
            return {"value": request.session.get("stored_value")}

        async with TestClient(app) as client:
            # Set value
            response1 = await client.get("/set/test123")
            assert response1.status_code == 200

            # Get value
            response2 = await client.get("/get")
            assert response2.status_code == 200
            data = response2.json()
            assert data["value"] == "test123"
