"""
Cookie-based session storage.

Stores session data directly in signed cookies for stateless sessions.
"""

from __future__ import annotations

import base64
import hmac
import logging

import msgspec

from zenith.sessions.manager import Session
from zenith.sessions.store import SessionStore

logger = logging.getLogger("zenith.sessions.cookie")


class CookieSessionStore(SessionStore):
    """
    Cookie-based session storage.

    Features:
    - Stateless sessions (no server storage)
    - Cryptographically signed cookies
    - Automatic expiration
    - Tamper detection
    - No Redis/database dependency

    Limitations:
    - 4KB cookie size limit
    - Client-side storage (less secure)
    - Session data visible to client (when base64 decoded)

    Best for:
    - Simple applications
    - Distributed deployments without shared storage
    - When Redis/database is not available
    """

    def __init__(
        self,
        secret_key: str,
        max_cookie_size: int = 4000,  # Leave room for other cookie data
    ):
        """
        Initialize cookie session store.

        Args:
            secret_key: Secret key for signing cookies (must be >=32 chars)
            max_cookie_size: Maximum cookie size in bytes
        """
        if len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")

        self.secret_key = secret_key.encode()
        self.max_cookie_size = max_cookie_size

    def _sign_data(self, data: str) -> str:
        """Sign data with HMAC."""
        signature = hmac.new(
            self.secret_key, data.encode(), digestmod="sha256"
        ).hexdigest()
        return f"{data}.{signature}"

    def _unsign_data(self, signed_data: str) -> str | None:
        """Verify and unsign data."""
        try:
            data, signature = signed_data.rsplit(".", 1)
        except ValueError:
            logger.warning("Invalid cookie format: no signature")
            return None

        expected_signature = hmac.new(
            self.secret_key, data.encode(), digestmod="sha256"
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid cookie signature")
            return None

        return data

    def _encode_session(self, session: Session) -> str | None:
        """Encode session to signed cookie value."""
        try:
            # Convert to dict and serialize
            session_dict = session.to_dict()
            json_bytes = msgspec.json.encode(session_dict)

            # Base64 encode
            b64_data = base64.b64encode(json_bytes).decode()

            # Sign the data
            signed_data = self._sign_data(b64_data)

            # Check size limit
            if len(signed_data) > self.max_cookie_size:
                logger.error(
                    f"Session too large for cookie: {len(signed_data)} > {self.max_cookie_size}"
                )
                return None

            return signed_data

        except Exception as e:
            logger.error(f"Error encoding session: {e}")
            return None

    def _decode_session(self, cookie_value: str) -> Session | None:
        """Decode session from signed cookie value."""
        from zenith.sessions.manager import Session

        try:
            # Verify signature and get data
            b64_data = self._unsign_data(cookie_value)
            if not b64_data:
                return None

            # Base64 decode
            json_data = base64.b64decode(b64_data).decode()

            # Parse JSON
            session_dict = msgspec.json.decode(json_data.encode())

            # Create session object
            return Session.from_dict(session_dict)

        except Exception as e:
            logger.error(f"Error decoding session cookie: {e}")
            return None

    async def load(self, session_id: str) -> Session | None:
        """
        Load session from cookie data.

        Note: For cookie sessions, the session_id is actually the cookie value.
        This is a bit of an abstraction leak, but necessary for the interface.
        """
        if not session_id:
            return None

        session = self._decode_session(session_id)

        if not session:
            return None

        # Check if expired
        if session.is_expired():
            return None

        return session

    async def save(self, session: Session) -> None:
        """
        Save session to cookie format.

        This doesn't actually persist anything - the encoded cookie
        value needs to be set by the middleware.
        """
        # For cookie sessions, we don't save here
        # The middleware will call _encode_session to get the cookie value
        pass

    async def delete(self, session_id: str) -> None:
        """Delete session (clear cookie)."""
        # For cookie sessions, deletion happens by clearing the cookie
        # This is handled by the middleware
        pass

    async def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        # Cookie sessions don't need cleanup - they expire on the client
        return 0

    def get_cookie_value(self, session: Session) -> str | None:
        """Get cookie value for a session."""
        return self._encode_session(session)

    def session_from_cookie(self, cookie_value: str) -> Session | None:
        """Create session from cookie value."""
        return self._decode_session(cookie_value)

    async def health_check(self) -> dict:
        """Get cookie session store health information."""
        return {
            "status": "healthy",
            "backend": "cookie",
            "max_cookie_size": self.max_cookie_size,
            "signed": True,
        }
