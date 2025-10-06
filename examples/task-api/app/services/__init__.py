"""
Service layer for business logic.
"""

from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from app.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionError,
    ValidationError,
)


class BaseService:
    """Base service with common patterns."""

    def __init__(self, session):
        self.session = session

    async def commit(self):
        """Commit changes with error handling."""
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            # Convert database errors to API errors
            if "UNIQUE constraint" in str(e):
                raise ConflictError("Resource already exists")
            raise ValidationError(f"Database constraint violation: {e}")
