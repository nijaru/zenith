"""
Unit tests for high-level decorators.

Tests caching, rate limiting, validation, and other decorator patterns.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from zenith.decorators import (
    auth_required,
    cache,
    paginate,
    rate_limit,
    returns,
    transaction,
    validate,
)
from zenith.exceptions import (
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
)


class TestCacheDecorator:
    """Test the @cache decorator."""

    async def test_cache_basic(self):
        """Test basic caching functionality."""
        call_count = 0

        @cache(ttl=1)  # 1 second TTL
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should return cached result
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different argument should execute function
        result3 = await expensive_function(3)
        assert result3 == 6
        assert call_count == 2

        # After TTL expires, function should execute again
        await asyncio.sleep(1.1)
        result4 = await expensive_function(5)
        assert result4 == 10
        assert call_count == 3

    async def test_cache_with_kwargs(self):
        """Test caching with keyword arguments."""
        call_count = 0

        @cache(ttl=60)
        async def function_with_kwargs(a: int, b: int = 10) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        result1 = await function_with_kwargs(5)
        result2 = await function_with_kwargs(5)
        assert result1 == result2 == 15
        assert call_count == 1

        # Different kwargs should create different cache entry
        result3 = await function_with_kwargs(5, b=20)
        assert result3 == 25
        assert call_count == 2

    async def test_cache_thread_safety(self):
        """Test cache is thread-safe for concurrent calls."""
        call_count = 0

        @cache(ttl=60)
        async def slow_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2

        # Run multiple concurrent calls with different arguments to avoid race condition
        tasks = [slow_function(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Each should return correct result
        assert results[0] == 0
        assert results[5] == 10
        # Each unique call should execute once
        assert call_count == 10


class TestRateLimitDecorator:
    """Test the @rate_limit decorator."""

    async def test_rate_limit_basic(self):
        """Test basic rate limiting."""

        @rate_limit("2/second")
        async def limited_function():
            return "success"

        # First two calls should succeed
        result1 = await limited_function()
        result2 = await limited_function()
        assert result1 == "success"
        assert result2 == "success"

        # Third call should fail
        with pytest.raises(RateLimitException) as exc_info:
            await limited_function()
        assert "Rate limit exceeded" in str(exc_info.value)

        # After waiting, should work again
        await asyncio.sleep(1.1)
        result3 = await limited_function()
        assert result3 == "success"

    async def test_rate_limit_different_periods(self):
        """Test rate limiting with different time periods."""

        @rate_limit("5/minute")
        async def per_minute_function():
            return "ok"

        # Should allow 5 calls
        for _ in range(5):
            result = await per_minute_function()
            assert result == "ok"

        # 6th call should fail
        with pytest.raises(RateLimitException):
            await per_minute_function()

    async def test_rate_limit_multiple_endpoints(self):
        """Test rate limiting is per-endpoint."""

        @rate_limit("1/second")
        async def endpoint_a():
            return "a"

        @rate_limit("1/second")
        async def endpoint_b():
            return "b"

        # Each endpoint should have its own limit
        result_a = await endpoint_a()
        assert result_a == "a"

        result_b = await endpoint_b()
        assert result_b == "b"

        # Second call to endpoint_a should fail
        with pytest.raises(RateLimitException):
            await endpoint_a()

        # But endpoint_b should still work once more
        with pytest.raises(RateLimitException):
            await endpoint_b()


class TestReturnsDecorator:
    """Test the @returns decorator."""

    async def test_returns_auto_404(self):
        """Test automatic 404 on None."""

        class User:
            def __init__(self, id: int, name: str):
                self.id = id
                self.name = name

        @returns(User)
        async def get_user(user_id: int):
            if user_id == 1:
                return User(1, "Alice")
            return None

        # Valid user should return
        user = await get_user(1)
        assert user.id == 1
        assert user.name == "Alice"

        # Invalid user should raise 404
        with pytest.raises(NotFoundException) as exc_info:
            await get_user(999)
        assert "User not found" in str(exc_info.value)

    async def test_returns_with_dict(self):
        """Test returns decorator with dictionary result."""

        class User:
            pass

        @returns(User)
        async def get_user_dict(user_id: int):
            if user_id == 1:
                return {"id": user_id, "name": "Test User"}
            return None

        # Should return dict for valid user
        result = await get_user_dict(1)
        assert result == {"id": 1, "name": "Test User"}

        # Should raise 404 for None
        with pytest.raises(NotFoundException):
            await get_user_dict(999)


class TestAuthRequiredDecorator:
    """Test the @auth_required decorator."""

    async def test_auth_required_basic(self):
        """Test basic authentication requirement."""

        @auth_required()
        async def protected_route(user=None):
            return f"Hello {user}"

        # Without user should fail
        with pytest.raises(UnauthorizedException):
            await protected_route()

        # With user should succeed
        result = await protected_route(user={"id": 1, "name": "Alice"})
        assert result == "Hello {'id': 1, 'name': 'Alice'}"

    async def test_auth_required_with_role(self):
        """Test role-based authorization."""

        @auth_required(role="admin")
        async def admin_route(user=None):
            return "Admin access"

        # User without role should fail
        user_obj = Mock()
        user_obj.role = "user"
        with pytest.raises(ForbiddenException):
            await admin_route(user=user_obj)

        # User with correct role should succeed
        admin_obj = Mock()
        admin_obj.role = "admin"
        result = await admin_route(user=admin_obj)
        assert result == "Admin access"

    async def test_auth_required_with_scopes(self):
        """Test scope-based authorization."""

        @auth_required(scopes=["read:users", "write:users"])
        async def scoped_route(user=None):
            return "Scoped access"

        # User without all scopes should fail
        user_obj = Mock()
        user_obj.scopes = ["read:users"]
        with pytest.raises(ForbiddenException):
            await scoped_route(user=user_obj)

        # User with all required scopes should succeed
        admin_obj = Mock()
        admin_obj.scopes = ["read:users", "write:users", "admin"]
        result = await scoped_route(user=admin_obj)
        assert result == "Scoped access"


class TestPaginateDecorator:
    """Test the @paginate decorator."""

    async def test_paginate_basic(self):
        """Test basic pagination."""

        @paginate(default_limit=10)
        async def list_items(page: int = 1, limit: int = 10, **kwargs):
            # kwargs contains injected pagination params
            offset = kwargs["_offset"]
            limit = kwargs["_limit"]

            # Simulate fetching items
            items = [f"item_{i}" for i in range(offset, offset + limit)]
            return items

        # Should return paginated response
        result = await list_items(page=1, limit=5)
        assert "items" in result
        assert len(result["items"]) == 5
        assert result["page"] == 1
        assert result["limit"] == 5

    async def test_paginate_limits(self):
        """Test pagination limit enforcement."""

        @paginate(default_limit=10, max_limit=50)
        async def list_items(page: int = 1, limit: int = 10, **kwargs):
            return list(range(kwargs["_limit"]))

        # Should enforce max limit
        result = await list_items(page=1, limit=100)
        assert result["limit"] == 50
        assert len(result["items"]) == 50

        # Should enforce min limit
        result = await list_items(page=1, limit=0)
        assert result["limit"] == 1


class TestTransactionDecorator:
    """Test the @transaction decorator."""

    async def test_transaction_basic(self):
        """Test transaction wrapper."""

        @transaction()
        async def create_user(name: str):
            # Simulate database operation
            return {"id": 1, "name": name}

        result = await create_user("Alice")
        assert result["name"] == "Alice"

    async def test_transaction_rollback(self):
        """Test transaction rollback on exception."""

        @transaction(rollback_on=(ValueError,))
        async def failing_operation():
            raise ValueError("Operation failed")

        with pytest.raises(ValueError):
            await failing_operation()


class TestValidateDecorator:
    """Test the @validate decorator."""

    async def test_validate_request(self):
        """Test request validation."""
        from pydantic import BaseModel

        class UserCreate(BaseModel):
            name: str
            email: str

        @validate(request_model=UserCreate)
        async def create_user(data: dict):
            return {"id": 1, **data}

        # Valid data should pass
        result = await create_user({"name": "Alice", "email": "alice@example.com"})
        assert result["name"] == "Alice"

    async def test_validate_response(self):
        """Test response validation."""
        from pydantic import BaseModel

        class UserResponse(BaseModel):
            id: int
            name: str

        @validate(response_model=UserResponse)
        async def get_user():
            return {"id": 1, "name": "Alice"}

        result = await get_user()
        assert result["id"] == 1
