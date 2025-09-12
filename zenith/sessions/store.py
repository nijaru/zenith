"""
Session storage interface and base implementation.

Defines the contract for session storage backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zenith.sessions.manager import Session


class SessionStore(ABC):
    """
    Abstract base class for session storage backends.

    Defines the interface that all session stores must implement.
    """

    @abstractmethod
    async def load(self, session_id: str) -> Session | None:
        """
        Load session data by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found
        """
        pass

    @abstractmethod
    async def save(self, session: Session) -> None:
        """
        Save session data.

        Args:
            session: Session object to save
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """
        Delete session by ID.

        Args:
            session_id: Session identifier to delete
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        pass

    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        session = await self.load(session_id)
        return session is not None
