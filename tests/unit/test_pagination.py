"""
Unit tests for pagination utilities.

Tests PaginationParams, PaginatedResponse, Paginate, and CursorPagination.
"""

import pytest
from pydantic import ValidationError

from zenith.pagination import (
    CursorPagination,
    Paginate,
    PaginatedResponse,
    PaginationParams,
)


class TestPaginationParams:
    """Test PaginationParams model."""

    def test_pagination_params_defaults(self):
        """Test default values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.limit == 20
        assert params.offset == 0

    def test_pagination_params_custom(self):
        """Test custom values."""
        params = PaginationParams(page=3, limit=50)
        assert params.page == 3
        assert params.limit == 50
        assert params.offset == 100  # (3-1) * 50

    def test_pagination_params_validation(self):
        """Test parameter validation."""
        # Page must be >= 1
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

        # Limit must be >= 1
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)

        # Limit must be <= 100
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)

    def test_offset_calculation(self):
        """Test offset calculation for different pages."""
        assert PaginationParams(page=1, limit=10).offset == 0
        assert PaginationParams(page=2, limit=10).offset == 10
        assert PaginationParams(page=5, limit=20).offset == 80


class TestPaginatedResponse:
    """Test PaginatedResponse model."""

    def test_paginated_response_create(self):
        """Test creating paginated response."""
        items = ["item1", "item2", "item3"]
        response = PaginatedResponse.create(
            items=items,
            page=2,
            limit=3,
            total=10,
        )

        assert response.items == items
        assert response.page == 2
        assert response.limit == 3
        assert response.total == 10
        assert response.pages == 4  # ceil(10/3)

    def test_pages_calculation(self):
        """Test pages calculation."""
        # Exact division
        response = PaginatedResponse.create([], 1, 10, 100)
        assert response.pages == 10

        # Needs rounding up
        response = PaginatedResponse.create([], 1, 10, 101)
        assert response.pages == 11

        # Single item
        response = PaginatedResponse.create([], 1, 10, 1)
        assert response.pages == 1

        # No items
        response = PaginatedResponse.create([], 1, 10, 0)
        assert response.pages == 0

    def test_generic_typing(self):
        """Test generic type support."""

        class User:
            def __init__(self, id: int, name: str):
                self.id = id
                self.name = name

        users = [User(1, "Alice"), User(2, "Bob")]
        response = PaginatedResponse.create(
            items=users,
            page=1,
            limit=10,
            total=2,
        )

        assert len(response.items) == 2
        assert response.items[0].name == "Alice"


class TestPaginate:
    """Test Paginate dependency."""

    def test_paginate_defaults(self):
        """Test default configuration."""
        paginate = Paginate()
        assert paginate.default_limit == 20
        assert paginate.max_limit == 100
        assert paginate.min_limit == 1
        assert paginate.page == 1
        assert paginate.limit == 20
        assert paginate.offset == 0

    def test_paginate_custom_defaults(self):
        """Test custom default configuration."""
        paginate = Paginate(default_limit=50, max_limit=200, min_limit=5)
        assert paginate.default_limit == 50
        assert paginate.max_limit == 200
        assert paginate.min_limit == 5
        assert paginate.limit == 50

    def test_paginate_call(self):
        """Test calling with query parameters."""
        paginate = Paginate()

        # Call with custom values
        result = paginate(page=3, limit=30)
        assert result.page == 3
        assert result.limit == 30
        assert result.offset == 60  # (3-1) * 30

    def test_paginate_limit_enforcement(self):
        """Test limit enforcement."""
        paginate = Paginate(default_limit=20, max_limit=50, min_limit=5)

        # Exceeds max limit
        result = paginate(page=1, limit=100)
        assert result.limit == 50  # Capped at max

        # Below min limit
        result = paginate(page=1, limit=1)
        assert result.limit == 5  # Raised to min

        # Within bounds
        result = paginate(page=1, limit=25)
        assert result.limit == 25

    def test_paginate_page_validation(self):
        """Test page number validation."""
        paginate = Paginate()

        # Negative page should become 1
        result = paginate(page=-5)
        assert result.page == 1

        # Zero page should become 1
        result = paginate(page=0)
        assert result.page == 1

        # Positive page should be preserved
        result = paginate(page=10)
        assert result.page == 10

    def test_to_params(self):
        """Test conversion to PaginationParams."""
        paginate = Paginate()
        result = paginate(page=2, limit=25)

        params = result.to_params()
        assert isinstance(params, PaginationParams)
        assert params.page == 2
        assert params.limit == 25
        assert params.offset == 25


class TestCursorPagination:
    """Test CursorPagination for large datasets."""

    def test_cursor_defaults(self):
        """Test default configuration."""
        cursor = CursorPagination()
        assert cursor.default_limit == 20
        assert cursor.max_limit == 100
        assert cursor.after is None
        assert cursor.before is None
        assert cursor.limit == 20

    def test_cursor_call(self):
        """Test calling with parameters."""
        cursor = CursorPagination()

        result = cursor(after="cursor123", limit=30)
        assert result.after == "cursor123"
        assert result.before is None
        assert result.limit == 30

        result = cursor(before="cursor456", limit=10)
        assert result.after is None
        assert result.before == "cursor456"
        assert result.limit == 10

    def test_cursor_limit_enforcement(self):
        """Test limit enforcement."""
        cursor = CursorPagination(default_limit=20, max_limit=50)

        # Exceeds max
        result = cursor(limit=100)
        assert result.limit == 50

        # Below min
        result = cursor(limit=0)
        assert result.limit == 1

        # Default when not specified
        result = cursor()
        assert result.limit == 20

    def test_cursor_both_directions(self):
        """Test using both after and before cursors."""
        cursor = CursorPagination()

        result = cursor(after="start", before="end")
        assert result.after == "start"
        assert result.before == "end"


class TestPaginationIntegration:
    """Test pagination integration scenarios."""

    async def test_paginate_with_database_query(self):
        """Test pagination with simulated database query."""

        class MockQuery:
            def __init__(self, total_items: int = 100):
                self.total_items = total_items
                self._offset = 0
                self._limit = 10

            def offset(self, value: int):
                self._offset = value
                return self

            def limit(self, value: int):
                self._limit = value
                return self

            async def all(self):
                # Simulate fetching items
                start = self._offset
                end = min(start + self._limit, self.total_items)
                return [f"item_{i}" for i in range(start, end)]

            async def count(self):
                return self.total_items

        # Simulate a paginated endpoint
        async def list_items(pagination: Paginate = Paginate()):
            query = MockQuery(total_items=55)

            items = await query.offset(pagination.offset).limit(pagination.limit).all()
            total = await query.count()

            return PaginatedResponse.create(
                items=items,
                page=pagination.page,
                limit=pagination.limit,
                total=total,
            )

        # Test first page
        pagination = Paginate()(page=1, limit=20)
        response = await list_items(pagination)
        assert len(response.items) == 20
        assert response.items[0] == "item_0"
        assert response.page == 1
        assert response.pages == 3  # ceil(55/20)

        # Test last page
        pagination = Paginate()(page=3, limit=20)
        response = await list_items(pagination)
        assert len(response.items) == 15  # 55 - 40
        assert response.items[0] == "item_40"
        assert response.page == 3

    def test_cursor_pagination_with_ids(self):
        """Test cursor pagination using IDs."""
        # Simulate data with IDs
        items = [{"id": i, "name": f"item_{i}"} for i in range(1, 101)]

        def get_page(cursor: CursorPagination):
            after_id = int(cursor.after) if cursor.after else 0
            before_id = int(cursor.before) if cursor.before else float("inf")

            # Filter based on cursors
            filtered = [item for item in items if after_id < item["id"] < before_id]

            # Apply limit
            return filtered[: cursor.limit]

        # Get first page
        cursor = CursorPagination()(limit=10)
        page = get_page(cursor)
        assert len(page) == 10
        assert page[0]["id"] == 1
        assert page[-1]["id"] == 10

        # Get next page using cursor
        cursor = CursorPagination()(after="10", limit=10)
        page = get_page(cursor)
        assert len(page) == 10
        assert page[0]["id"] == 11
        assert page[-1]["id"] == 20

        # Get page before cursor
        cursor = CursorPagination()(before="50", after="40", limit=5)
        page = get_page(cursor)
        assert len(page) == 5
        assert page[0]["id"] == 41
        assert page[-1]["id"] == 45
