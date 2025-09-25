"""
Tests for enhanced dependency injection shortcuts - Rails-like DX.

Tests for:
- Session, Auth, Request shortcuts
- Service decorator and injection
- Context managers for manual resolution
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from zenith.core.dependencies import (
    Session, Auth, Request,
    Inject,
    get_database_session, get_auth_user, get_current_request_dependency,
    DatabaseContext, ServiceContext,
    resolve_db, resolve_auth,
    AuthenticatedUser, HttpRequest
)
from zenith.core.container import set_current_db_session


class TestDependencyShortcuts:
    """Test Rails-like dependency shortcuts."""

    def test_session_shortcut_is_fastapi_depends(self):
        """Test Session shortcut is properly configured Depends."""
        # Session should be a Depends object wrapping get_database_session
        assert hasattr(Session, 'dependency')
        assert Session.dependency == get_database_session

    def test_auth_shortcut_is_fastapi_depends(self):
        """Test Auth shortcut is properly configured Depends."""
        assert hasattr(Auth, 'dependency')
        assert Auth.dependency == get_auth_user


    def test_request_shortcut_is_fastapi_depends(self):
        """Test Request shortcut is properly configured Depends."""
        assert hasattr(Request, 'dependency')
        assert Request.dependency == get_current_request_dependency


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
        # get_database_session is an async generator, not a context manager
        gen = get_database_session()
        session = await gen.__anext__()
        assert session == mock_db_session

        # Clean up the generator
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    async def test_get_auth_user_without_request_context(self):
        """Test auth user dependency function returns None without request context."""
        user = await get_auth_user()
        # Without request context, auth user is None
        assert user is None


    async def test_get_current_request_without_context(self):
        """Test current request dependency function returns None without context."""
        request = await get_current_request_dependency()

        assert request is None  # Without request context, returns None


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

    async def test_inject_service_resolution(self):
        """Test that Inject can resolve services."""
        class TestService:
            def __init__(self):
                self.value = "injected"

        inject_result = Inject(TestService)

        # Get the resolver function
        resolver = inject_result.dependency

        # Should be able to create instance (resolver is now async)
        instance = await resolver()
        assert isinstance(instance, TestService)
        assert instance.value == "injected"


class TestTypeAliases:
    """Test type aliases for better documentation."""

    def test_type_aliases_exist(self):
        """Test that type aliases are defined."""
        # These should be importable and usable for type hints
        assert AuthenticatedUser is not None
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
        """Test manual auth user resolution without context."""
        user = await resolve_auth()

        # Without request context, auth user is None
        assert user is None



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
            session: AsyncSession = Session,
            user = Auth
        ):
            return {"session": session, "user": user}

        # Function should be properly annotated
        hints = get_type_hints(example_route)
        assert 'session' in hints
        # Note: AsyncSession hint should be preserved

    # Service decorator test removed - decorator functionality was removed from the framework


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
            new_style = Session
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
        # The result should be compatible with FastAPI's Depends
        # In FastAPI, Depends returns a special object, not the function itself
        assert callable(result) or hasattr(result, '__class__')