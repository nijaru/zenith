"""
Pagination utilities for Zenith applications.

Provides clean, reusable pagination patterns for list endpoints.
"""

from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class PaginatedResponse[T](BaseModel):
    """Standard paginated response format."""

    items: list[T]
    page: int
    limit: int
    total: int
    pages: int

    @classmethod
    def create(
        cls, items: list[T], page: int, limit: int, total: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        pages = (total + limit - 1) // limit  # Ceiling division
        return cls(items=items, page=page, limit=limit, total=total, pages=pages)


class Paginate:
    """
    Dependency for pagination parameters.

    Example:
        @app.get("/users")
        async def list_users(pagination: Paginate = Paginate()):
            users = await User.query.offset(pagination.offset).limit(pagination.limit).all()
            total = await User.query.count()
            return PaginatedResponse.create(users, pagination.page, pagination.limit, total)

    Or with the ZenithModel integration:
        @app.get("/users")
        async def list_users(pagination: Paginate = Paginate()):
            return await User.paginate(pagination)
    """

    def __init__(
        self,
        default_limit: int = 20,
        max_limit: int = 100,
        min_limit: int = 1,
    ):
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.min_limit = min_limit
        self._page = 1
        self._limit = default_limit

    def __call__(self, page: int = 1, limit: int | None = None) -> "Paginate":
        """Called by the framework to inject query parameters."""
        self._page = max(1, page)

        if limit is None:
            limit = self.default_limit

        self._limit = max(self.min_limit, min(limit, self.max_limit))
        return self

    @property
    def page(self) -> int:
        """Current page number."""
        return self._page

    @property
    def limit(self) -> int:
        """Items per page."""
        return self._limit

    @property
    def offset(self) -> int:
        """Database offset."""
        return (self._page - 1) * self._limit

    def to_params(self) -> PaginationParams:
        """Convert to PaginationParams model."""
        return PaginationParams(page=self._page, limit=self._limit)


class CursorPagination:
    """
    Cursor-based pagination for large datasets.

    More efficient than offset-based for large datasets.

    Example:
        @app.get("/events")
        async def list_events(cursor: CursorPagination = CursorPagination()):
            query = Event.query.order_by(Event.id)
            if cursor.after:
                query = query.where(Event.id > cursor.after)
            events = await query.limit(cursor.limit).all()

            next_cursor = events[-1].id if events else None
            return {
                "items": events,
                "cursor": {"next": next_cursor}
            }
    """

    def __init__(self, default_limit: int = 20, max_limit: int = 100):
        self.default_limit = default_limit
        self.max_limit = max_limit
        self._after = None
        self._before = None
        self._limit = default_limit

    def __call__(
        self,
        after: str | None = None,
        before: str | None = None,
        limit: int | None = None,
    ) -> "CursorPagination":
        """Called by the framework to inject query parameters."""
        self._after = after
        self._before = before

        if limit is None:
            limit = self.default_limit

        self._limit = max(1, min(limit, self.max_limit))
        return self

    @property
    def after(self) -> str | None:
        """Cursor after which to fetch results."""
        return self._after

    @property
    def before(self) -> str | None:
        """Cursor before which to fetch results."""
        return self._before

    @property
    def limit(self) -> int:
        """Maximum items to return."""
        return self._limit


# Export pagination utilities
__all__ = [
    "CursorPagination",
    "Paginate",
    "PaginatedResponse",
    "PaginationParams",
]
