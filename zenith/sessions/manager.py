"""
Session manager for handling user sessions.

Provides a high-level API for session operations with pluggable storage backends.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from zenith.sessions.store import SessionStore


class Session:
    """
    User session data container.

    Provides dict-like access to session data with automatic
    dirty tracking and expiration handling.
    """

    def __init__(
        self,
        session_id: str,
        data: dict | None = None,
        created_at: datetime | None = None,
        expires_at: datetime | None = None,
        is_new: bool = True,
    ):
        """
        Initialize session.

        Args:
            session_id: Unique session identifier
            data: Session data dictionary
            created_at: Session creation timestamp
            expires_at: Session expiration timestamp
            is_new: Whether this is a newly created session
        """
        self.session_id = session_id
        self._data = data or {}
        self.created_at = created_at or datetime.now(UTC)
        self.expires_at = expires_at
        self._dirty = False
        self._new = is_new

    def get(self, key: str, default: Any = None) -> Any:
        """Get session value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set session value."""
        self._data[key] = value
        self._dirty = True

    def delete(self, key: str) -> None:
        """Delete session key."""
        if key in self._data:
            del self._data[key]
            self._dirty = True

    def clear(self) -> None:
        """Clear all session data."""
        self._data.clear()
        self._dirty = True

    def is_expired(self) -> bool:
        """Check if session is expired."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    def refresh_expiry(self, max_age: timedelta) -> None:
        """Refresh session expiration time."""
        self.expires_at = datetime.now(UTC) + max_age
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        """Check if session data has been modified."""
        return self._dirty

    @property
    def is_new(self) -> bool:
        """Check if this is a new session."""
        return self._new

    def mark_clean(self) -> None:
        """Mark session as clean (saved)."""
        self._dirty = False
        self._new = False

    def to_dict(self) -> dict:
        """Convert session to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "data": self._data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        """Create session from dictionary."""
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])

        return cls(
            session_id=data["session_id"],
            data=data.get("data", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=expires_at,
            is_new=False,  # Loaded sessions are not new
        )

    # Dict-like interface
    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        """Sessions are always truthy, even when empty."""
        return True

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class SessionManager:
    """
    Session manager with pluggable storage backends.

    Features:
    - Multiple storage backends (cookie, Redis, database)
    - Automatic session expiration
    - Security features (secure cookies, CSRF protection)
    - Session regeneration
    """

    def __init__(
        self,
        store: SessionStore,
        cookie_name: str = "session_id",
        max_age: timedelta | int = timedelta(days=30),
        is_secure: bool = True,
        is_http_only: bool = True,
        same_site: str = "lax",
        domain: str | None = None,
        path: str = "/",
    ):
        """
        Initialize session manager.

        Args:
            store: Session storage backend
            cookie_name: Name of session cookie
            max_age: Session expiration time (timedelta or seconds as int)
            is_secure: Use secure cookies (HTTPS only)
            is_http_only: HTTP-only cookies (no JS access)
            same_site: SameSite cookie attribute
            domain: Cookie domain
            path: Cookie path
        """
        self.store = store
        self.cookie_name = cookie_name
        # Convert int seconds to timedelta for consistency
        if isinstance(max_age, int):
            self.max_age = timedelta(seconds=max_age)
        else:
            self.max_age = max_age
        self.secure = is_secure
        self.http_only = is_http_only
        self.same_site = same_site
        self.domain = domain
        self.path = path

    def generate_session_id(self) -> str:
        """Generate a secure session ID."""
        # Use cryptographically secure random string
        return secrets.token_urlsafe(32)

    async def create_session(self, data: dict | None = None) -> Session:
        """Create a new session."""
        session_id = self.generate_session_id()
        expires_at = datetime.now(UTC) + self.max_age

        session = Session(
            session_id=session_id,
            data=data,  # Keep None to mark as new
            expires_at=expires_at,
        )

        await self.store.save(session)
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get session by ID."""
        session = await self.store.load(session_id)

        if not session:
            return None

        # Check if expired
        if session.is_expired():
            await self.destroy_session(session_id)
            return None

        return session

    async def save_session(self, session: Session) -> None:
        """Save session if dirty."""
        if session.is_dirty:
            await self.store.save(session)
            session.mark_clean()

    async def destroy_session(self, session_id: str) -> None:
        """Destroy a session."""
        await self.store.delete(session_id)

    async def regenerate_session_id(self, session: Session) -> Session:
        """
        Regenerate session ID for security.

        This should be called after login to prevent session fixation attacks.
        """
        old_session_id = session.session_id

        # Create new session with same data
        new_session = await self.create_session(session._data.copy())

        # Delete old session
        await self.destroy_session(old_session_id)

        return new_session

    async def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        return await self.store.cleanup_expired()

    def get_cookie_config(self) -> dict:
        """Get cookie configuration for middleware."""
        config = {
            "key": self.cookie_name,
            "max_age": int(self.max_age.total_seconds()),
            "path": self.path,
            "httponly": self.http_only,
            "samesite": self.same_site,
        }

        if self.secure:
            config["secure"] = True

        if self.domain:
            config["domain"] = self.domain

        return config
