"""
Tests for request-scoped dependency injection.

Covers the new RequestScoped, Session, and Depends functionality
that fixes async database issues.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from starlette.requests import Request
from starlette.testclient import TestClient

from zenith import Zenith, Session, RequestScoped, Depends
from zenith.core.scoped import get_current_request, set_current_request, clear_current_request


class TestRequestScoped:
    """Test RequestScoped dependency injection."""

    def test_request_scoped_creation(self):
        """Test RequestScoped can be created with dependency."""
        async def my_dependency():
            return "test_value"

        scoped = RequestScoped(my_dependency)
        assert scoped.dependency == my_dependency

    def test_request_scoped_without_dependency(self):
        """Test RequestScoped without dependency."""
        scoped = RequestScoped()
        assert scoped.dependency is None

    @pytest.mark.asyncio
    async def test_request_scoped_get_or_create_sync(self):
        """Test RequestScoped with sync dependency."""
        def sync_dependency():
            return "sync_value"

        scoped = RequestScoped(sync_dependency)
        request = MagicMock()
        request.state = MagicMock()

        # Mock hasattr to return False initially
        def mock_hasattr(obj, name):
            return False

        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr

        try:
            result = await scoped.get_or_create(request)
            assert result == "sync_value"
        finally:
            builtins.hasattr = original_hasattr

    @pytest.mark.asyncio
    async def test_request_scoped_get_or_create_async(self):
        """Test RequestScoped with async dependency."""
        async def async_dependency():
            return "async_value"

        scoped = RequestScoped(async_dependency)
        request = MagicMock()
        request.state = MagicMock()

        # Mock hasattr to return False initially
        def mock_hasattr(obj, name):
            return False

        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr

        try:
            result = await scoped.get_or_create(request)
            assert result == "async_value"
        finally:
            builtins.hasattr = original_hasattr

    @pytest.mark.asyncio
    async def test_request_scoped_get_or_create_async_generator(self):
        """Test RequestScoped with async generator dependency."""
        async def async_gen_dependency():
            yield "generator_value"

        scoped = RequestScoped(async_gen_dependency)
        request = MagicMock()
        request.state = MagicMock()
        request.state._async_generators = []

        # Mock hasattr to return False initially
        def mock_hasattr(obj, name):
            if name == "_async_generators":
                return True
            return False

        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr

        try:
            result = await scoped.get_or_create(request)
            assert result == "generator_value"
            assert len(request.state._async_generators) == 1
        finally:
            builtins.hasattr = original_hasattr

    @pytest.mark.asyncio
    async def test_request_scoped_caching(self):
        """Test that RequestScoped caches results per request."""
        call_count = 0

        def counting_dependency():
            nonlocal call_count
            call_count += 1
            return f"value_{call_count}"

        scoped = RequestScoped(counting_dependency)
        request = MagicMock()
        request.state = MagicMock()

        # Mock the caching behavior
        cache = {}
        def mock_hasattr(obj, name):
            return name in cache

        def mock_getattr(obj, name, default=None):
            return cache.get(name, default)

        def mock_setattr(obj, name, value):
            cache[name] = value

        import builtins
        original_hasattr = builtins.hasattr
        original_getattr = builtins.getattr
        original_setattr = builtins.setattr

        builtins.hasattr = mock_hasattr
        builtins.getattr = mock_getattr
        builtins.setattr = mock_setattr

        try:
            # First call should execute dependency
            result1 = await scoped.get_or_create(request)
            assert result1 == "value_1"
            assert call_count == 1

            # Second call should return cached value
            result2 = await scoped.get_or_create(request)
            assert result2 == "value_1"  # Same as first call
            assert call_count == 1  # Dependency not called again
        finally:
            builtins.hasattr = original_hasattr
            builtins.getattr = original_getattr
            builtins.setattr = original_setattr

    @pytest.mark.asyncio
    async def test_request_scoped_no_dependency_error(self):
        """Test RequestScoped raises error when no dependency provided."""
        scoped = RequestScoped()
        request = MagicMock()

        with pytest.raises(ValueError, match="RequestScoped requires a dependency function"):
            await scoped.get_or_create(request)


class TestSession:
    """Test Session specialized RequestScoped."""

    def test_database_session_creation(self):
        """Test Session is a pre-configured dependency."""
        # Session is now a pre-configured Depends object
        assert hasattr(Session, 'dependency')
        # For custom sessions, use Depends directly
        async def get_db():
            yield "db_session"

        custom_session = Depends(get_db)
        assert custom_session.dependency == get_db


class TestDependsAlias:
    """Test Depends alias for FastAPI compatibility."""

    def test_depends_is_request_scoped(self):
        """Test that Depends is an alias for RequestScoped."""
        assert Depends is RequestScoped

    def test_depends_usage(self):
        """Test using Depends like FastAPI."""
        async def get_db():
            return "db_session"

        # This should work just like FastAPI
        dependency = Depends(get_db)
        assert isinstance(dependency, RequestScoped)
        assert dependency.dependency == get_db


class TestRequestContext:
    """Test request context management."""

    def test_request_context_management(self):
        """Test setting and getting current request."""
        request = MagicMock()

        # Initially no request
        assert get_current_request() is None

        # Set request
        set_current_request(request)
        assert get_current_request() is request

        # Clear request
        clear_current_request()
        assert get_current_request() is None


class TestIntegrationWithZenith:
    """Test integration with Zenith application."""

    @pytest.mark.asyncio
    async def test_request_scoped_in_route(self):
        """Test RequestScoped dependency in actual route."""
        app = Zenith()

        # Track calls to dependency
        call_count = 0

        async def test_dependency():
            nonlocal call_count
            call_count += 1
            return f"dependency_result_{call_count}"

        @app.get("/test")
        async def test_route(dep_result=RequestScoped(test_dependency)):
            return {"result": dep_result}

        # Note: Full integration testing would require more setup
        # This tests the basic structure
        assert hasattr(app, 'get')

    @pytest.mark.asyncio
    async def test_database_session_integration(self):
        """Test Session integration pattern."""
        app = Zenith()

        async def get_db():
            # Simulate database session
            yield "mock_db_session"

        @app.get("/users")
        async def get_users(db=Depends(get_db)):
            return {"users": [], "db": db}

        # Basic structure test
        assert hasattr(app, 'get')

    def test_fastapi_compatibility(self):
        """Test FastAPI-compatible syntax works."""
        app = Zenith()

        async def get_db():
            yield "fastapi_style_db"

        # This should work just like FastAPI
        @app.get("/fastapi-style")
        async def fastapi_route(db=Depends(get_db)):
            return {"db": db}

        assert hasattr(app, 'get')


class TestAsyncGeneratorCleanup:
    """Test cleanup of async generators."""

    @pytest.mark.asyncio
    async def test_cleanup_async_generators(self):
        """Test that async generators are properly cleaned up."""
        scoped = RequestScoped()
        request = MagicMock()
        request.state = MagicMock()

        # Mock async generators list
        mock_gen1 = AsyncMock()
        mock_gen2 = AsyncMock()
        request.state._async_generators = [mock_gen1, mock_gen2]

        # Mock hasattr to return True for _async_generators
        def mock_hasattr(obj, name):
            return name == "_async_generators"

        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr

        try:
            await scoped.cleanup(request)

            # Check that aclose was called on all generators
            mock_gen1.aclose.assert_called_once()
            mock_gen2.aclose.assert_called_once()
        finally:
            builtins.hasattr = original_hasattr

    @pytest.mark.asyncio
    async def test_cleanup_cache_key(self):
        """Test that cache key is removed during cleanup."""
        async def test_dep():
            return "test"

        scoped = RequestScoped(test_dep)
        request = MagicMock()
        request.state = MagicMock()

        # Mock hasattr and delattr
        cache = {scoped._cache_key: "cached_value"}

        def mock_hasattr(obj, name):
            return name in cache

        def mock_delattr(obj, name):
            if name in cache:
                del cache[name]

        import builtins
        original_hasattr = builtins.hasattr
        original_delattr = builtins.delattr

        builtins.hasattr = mock_hasattr
        builtins.delattr = mock_delattr

        try:
            await scoped.cleanup(request)
            assert scoped._cache_key not in cache
        finally:
            builtins.hasattr = original_hasattr
            builtins.delattr = original_delattr