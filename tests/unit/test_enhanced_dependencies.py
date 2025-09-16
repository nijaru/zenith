"""
Tests for enhanced dependency injection shortcuts - Rails-like DX.

Tests for:
- DB, Auth, Cache, Request shortcuts
- Service decorator and injection
- Context managers for manual resolution
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from zenith.core.dependencies import (
    DB, Auth, Cache, Request,
    Inject, Service,
    get_database_session, get_auth_user, get_cache_client, get_current_request,
    DatabaseContext, ServiceContext,
    resolve_db, resolve_auth, resolve_cache,
    DatabaseSession, AuthenticatedUser, CacheClient, HttpRequest
)
from zenith.core.container import set_current_db_session


class TestDependencyShortcuts:
    """Test Rails-like dependency shortcuts."""

    def test_db_shortcut_is_fastapi_depends(self):
        """Test DB shortcut is properly configured Depends."""
        # DB should be a Depends object wrapping get_database_session
        assert hasattr(DB, 'dependency')
        assert DB.dependency == get_database_session

    def test_auth_shortcut_is_fastapi_depends(self):
        """Test Auth shortcut is properly configured Depends."""
        assert hasattr(Auth, 'dependency')
        assert Auth.dependency == get_auth_user

    def test_cache_shortcut_is_fastapi_depends(self):
        """Test Cache shortcut is properly configured Depends."""
        assert hasattr(Cache, 'dependency')
        assert Cache.dependency == get_cache_client

    def test_request_shortcut_is_fastapi_depends(self):
        """Test Request shortcut is properly configured Depends."""
        assert hasattr(Request, 'dependency')
        assert Request.dependency == get_current_request


class TestDependencyFunctions:
    """Test dependency resolution functions."""

    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        with patch('zenith.core.dependencies.get_db_session', return_value=session):
            yield session

    async def test_get_database_session(self, mock_db_session):
        """Test database session dependency function."""
        async with get_database_session() as session:
            assert session == mock_db_session

        # Should set and clean up current session
        # This is harder to test without integration, but we can verify the pattern

    async def test_get_auth_user_mock(self):
        """Test auth user dependency function returns mock user."""
        user = await get_auth_user()

        assert isinstance(user, dict)
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert user["name"] == "Mock User"

    async def test_get_cache_client_mock(self):
        """Test cache client dependency function returns mock cache."""
        cache = await get_cache_client()

        assert isinstance(cache, dict)  # Mock implementation returns empty dict

    async def test_get_current_request_mock(self):
        """Test current request dependency function returns mock request."""
        request = await get_current_request()

        assert isinstance(request, dict)  # Mock implementation returns empty dict


class TestServiceDecorator:
    """Test Service decorator functionality."""

    def test_service_decorator_default_settings(self):
        """Test Service decorator with default settings."""
        @Service()
        class TestService:
            def __init__(self):
                self.name = "test"

        # Should add service metadata
        assert hasattr(TestService, '_zenith_service')
        assert TestService._zenith_service is True
        assert TestService._zenith_singleton is True
        assert TestService._zenith_lifecycle == "application"

    def test_service_decorator_custom_settings(self):
        """Test Service decorator with custom settings."""
        @Service(singleton=False, lifecycle="request")
        class TestService:
            def __init__(self):
                self.name = "test"

        assert TestService._zenith_service is True
        assert TestService._zenith_singleton is False
        assert TestService._zenith_lifecycle == "request"

    def test_service_decorator_returns_class(self):
        """Test Service decorator returns the original class."""
        @Service()
        class TestService:
            def test_method(self):
                return "works"

        # Should still be able to instantiate and use
        instance = TestService()
        assert instance.test_method() == "works"


class TestInjectFunction:
    """Test Inject function for service resolution."""

    def test_inject_without_service_type(self):
        """Test Inject() without explicit service type."""
        inject_result = Inject()

        # Should return a Depends object
        assert hasattr(inject_result, 'dependency')

    def test_inject_with_service_type(self):
        """Test Inject(ServiceType) with explicit service type."""
        class TestService:
            def __init__(self):
                self.name = "test"

        inject_result = Inject(TestService)

        # Should return a Depends object
        assert hasattr(inject_result, 'dependency')

    def test_inject_service_resolution(self):
        """Test that Inject can resolve services."""
        @Service()
        class TestService:
            def __init__(self):
                self.value = "injected"

        inject_result = Inject(TestService)

        # Get the resolver function
        resolver = inject_result.dependency

        # Should be able to create instance
        instance = resolver()
        assert isinstance(instance, TestService)
        assert instance.value == "injected"


class TestTypeAliases:
    """Test type aliases for better documentation."""

    def test_type_aliases_exist(self):
        """Test that type aliases are defined."""
        # These should be importable and usable for type hints
        assert DatabaseSession is not None
        assert AuthenticatedUser is not None
        assert CacheClient is not None
        assert HttpRequest is not None


class TestManualResolution:
    """Test manual dependency resolution functions."""

    async def test_resolve_db(self):
        """Test manual database session resolution."""
        mock_session = AsyncMock()

        with patch('zenith.core.dependencies.get_db_session', return_value=mock_session):
            session = await resolve_db()
            assert session == mock_session

    async def test_resolve_auth(self):
        """Test manual auth user resolution."""
        user = await resolve_auth()

        assert isinstance(user, dict)
        assert user["name"] == "Mock User"

    def test_resolve_cache(self):
        """Test manual cache client resolution."""
        cache = resolve_cache()

        assert isinstance(cache, dict)


class TestDatabaseContext:
    """Test DatabaseContext context manager."""

    async def test_database_context_manager(self):
        """Test DatabaseContext provides session management."""
        mock_session = AsyncMock()

        with patch('zenith.core.dependencies.resolve_db', return_value=mock_session):
            async with DatabaseContext() as session:
                assert session == mock_session

    async def test_database_context_sets_current_session(self):
        """Test DatabaseContext sets current session in context."""
        mock_session = AsyncMock()

        with patch('zenith.core.dependencies.resolve_db', return_value=mock_session):
            with patch('zenith.core.dependencies.set_current_db_session') as mock_set:
                async with DatabaseContext():
                    # Should set current session
                    mock_set.assert_called_with(mock_session)

    async def test_database_context_cleanup(self):
        """Test DatabaseContext cleans up properly."""
        mock_session = AsyncMock()

        with patch('zenith.core.dependencies.resolve_db', return_value=mock_session):
            with patch('zenith.core.dependencies.set_current_db_session') as mock_set:
                try:
                    async with DatabaseContext():
                        pass
                except Exception:
                    pass

                # Should clean up context even on exception
                mock_set.assert_any_call(None)


class TestServiceContext:
    """Test ServiceContext context manager."""

    async def test_service_context_manager(self):
        """Test ServiceContext manages service instances."""
        class TestService:
            def __init__(self):
                self.name = "test"

        async with ServiceContext(TestService) as ctx:
            service = ctx.get(TestService)
            assert isinstance(service, TestService)
            assert service.name == "test"

    async def test_service_context_multiple_services(self):
        """Test ServiceContext with multiple services."""
        class ServiceA:
            def __init__(self):
                self.type = "A"

        class ServiceB:
            def __init__(self):
                self.type = "B"

        async with ServiceContext(ServiceA, ServiceB) as ctx:
            service_a = ctx.get(ServiceA)
            service_b = ctx.get(ServiceB)

            assert service_a.type == "A"
            assert service_b.type == "B"

    async def test_service_context_get_nonexistent_service(self):
        """Test ServiceContext returns None for nonexistent services."""
        class TestService:
            pass

        class OtherService:
            pass

        async with ServiceContext(TestService) as ctx:
            service = ctx.get(OtherService)
            assert service is None


class TestDependencyIntegration:
    """Integration tests for dependency system."""

    def test_dependency_shortcuts_work_with_type_hints(self):
        """Test dependency shortcuts work with type annotations."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from typing import get_type_hints

        # This should work in route definitions
        async def example_route(
            db: AsyncSession = DB,
            user = Auth,
            cache = Cache
        ):
            return {"db": db, "user": user, "cache": cache}

        # Function should be properly annotated
        hints = get_type_hints(example_route)
        assert 'db' in hints
        # Note: AsyncSession hint should be preserved

    def test_service_decorator_preserves_functionality(self):
        """Test Service decorator doesn't break class functionality."""
        @Service(singleton=True)
        class UserService:
            def __init__(self):
                self.users = []

            def add_user(self, name: str):
                self.users.append(name)
                return len(self.users)

            def get_users(self):
                return self.users

        # Should work normally
        service = UserService()
        count = service.add_user("Alice")
        assert count == 1
        assert service.get_users() == ["Alice"]

        # Should have service metadata
        assert service._zenith_service is True


class TestDependencyCompatibility:
    """Test compatibility with existing systems."""

    def test_backwards_compatibility(self):
        """Test new shortcuts don't break existing Depends usage."""
        # Both old and new patterns should work
        from zenith.core.dependencies import get_database_session

        try:
            from fastapi import Depends

            # Old style should still work
            old_style = Depends(get_database_session)
            assert hasattr(old_style, 'dependency')

            # New style should work
            new_style = DB
            assert hasattr(new_style, 'dependency')

            # Should be equivalent
            assert old_style.dependency == new_style.dependency

        except ImportError:
            # FastAPI not available, that's fine for some environments
            pass

    def test_mock_depends_fallback(self):
        """Test mock Depends works when FastAPI not available."""
        # The mock Depends in dependencies.py should work
        from zenith.core.dependencies import Depends as MockDepends

        def test_func():
            return "test"

        result = MockDepends(test_func)
        # Mock version should just return the function
        assert result == test_func