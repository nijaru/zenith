"""
Unit tests for the Context system and dependency injection.

Tests context creation, registration, dependency resolution, and lifecycle.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from zenith import Service, Zenith
from zenith.core.container import DIContainer
from zenith.core.service import Service as BaseContext
from zenith.core.service import EventBus
from zenith.core.routing import Context


class UserService:
    """Mock service for testing dependency injection."""

    def __init__(self, database_url: str = "mock://"):
        self.database_url = database_url
        self.users = [
            {"id": 1, "name": "John", "email": "john@test.com"},
            {"id": 2, "name": "Jane", "email": "jane@test.com"},
        ]

    async def get_user(self, user_id: int):
        return next((u for u in self.users if u["id"] == user_id), None)

    async def create_user(self, name: str, email: str):
        new_id = max(u["id"] for u in self.users) + 1
        user = {"id": new_id, "name": name, "email": email}
        self.users.append(user)
        return user

    async def list_users(self, limit: int = 10):
        return self.users[:limit]


class UserService(Service):
    """Example context for testing."""

    def __init__(self, container: DIContainer, user_service: UserService = None):
        super().__init__(container)
        self.user_service = user_service or UserService()

    async def get_user(self, user_id: int):
        """Get user by ID."""
        return await self.user_service.get_user(user_id)

    async def create_user(self, name: str, email: str):
        """Create new user."""
        return await self.user_service.create_user(name, email)

    async def list_users(self, limit: int = 10):
        """List users with pagination."""
        return await self.user_service.list_users(limit)

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        return "@" in email and "." in email


class NotificationService(Service):
    """Another context for testing inter-context dependencies."""

    def __init__(self, container: DIContainer, user_context: UserContext = None):
        super().__init__(container)
        self.user_context = user_context

    async def send_welcome_email(self, user_id: int):
        """Send welcome email to user."""
        if self.user_context:
            user = await self.user_context.get_user(user_id)
            if user:
                return {"sent": True, "to": user["email"]}
        return {"sent": False}


class TestContextBasics:
    """Test basic context functionality."""

    def test_context_creation(self):
        """Test basic context creation and inheritance."""
        container = DIContainer()
        container.register("events", EventBus())
        ctx = UserContext(container)

        assert isinstance(ctx, BaseContext)
        assert hasattr(ctx, "user_service")
        assert hasattr(ctx, "get_user")
        assert hasattr(ctx, "container")
        assert hasattr(ctx, "events")

    def test_context_dependency_injection(self):
        """Test context with injected dependencies."""
        container = DIContainer()
        container.register("events", EventBus())

        mock_service = Mock()
        mock_service.get_user = AsyncMock(return_value={"id": 1, "name": "Test"})

        ctx = UserContext(container, user_service=mock_service)
        assert ctx.user_service is mock_service

    def test_context_methods(self):
        """Test context method definitions."""
        container = DIContainer()
        container.register("events", EventBus())
        ctx = UserContext(container)

        # Check methods are callable
        assert callable(ctx.get_user)
        assert callable(ctx.create_user)
        assert callable(ctx.list_users)
        assert callable(ctx.validate_email)

        # Test sync method
        assert ctx.validate_email("test@example.com")
        assert not ctx.validate_email("invalid-email")


@pytest.mark.asyncio
class TestContextExecution:
    """Test context method execution."""

    async def test_get_user(self):
        """Test getting user from context."""
        container = DIContainer()
        container.register("events", EventBus())
        ctx = UserContext(container)

        user = await ctx.get_user(1)
        assert user is not None
        assert user["id"] == 1
        assert user["name"] == "John"

        # Test non-existent user
        user = await ctx.get_user(999)
        assert user is None

    async def test_create_user(self):
        """Test creating user through context."""
        container = DIContainer()
        container.register("events", EventBus())
        ctx = UserContext(container)

        new_user = await ctx.create_user("Test User", "test@example.com")
        assert new_user["name"] == "Test User"
        assert new_user["email"] == "test@example.com"
        assert new_user["id"] > 0

        # Verify user was added
        retrieved = await ctx.get_user(new_user["id"])
        assert retrieved == new_user

    async def test_list_users(self):
        """Test listing users with pagination."""
        container = DIContainer()
        container.register("events", EventBus())
        ctx = UserContext(container)

        # Default limit
        users = await ctx.list_users()
        assert len(users) >= 2

        # Custom limit
        users = await ctx.list_users(limit=1)
        assert len(users) == 1

    async def test_inter_context_dependencies(self):
        """Test contexts that depend on other contexts."""
        container = DIContainer()
        container.register("events", EventBus())

        user_ctx = UserContext(container)
        notif_ctx = NotificationContext(container, user_context=user_ctx)

        # Send welcome email to existing user
        result = await notif_ctx.send_welcome_email(1)
        assert result["sent"]
        assert result["to"] == "john@test.com"

        # Try with non-existent user
        result = await notif_ctx.send_welcome_email(999)
        assert not result["sent"]


class TestDependencyContainer:
    """Test the dependency injection container."""

    def test_container_creation(self):
        """Test creating dependency container."""
        container = DIContainer()
        assert hasattr(container, "_services")

    def test_service_registration(self):
        """Test registering services in container."""
        container = DIContainer()

        # Register services
        container.register("user_service", UserService())
        container.register("events", EventBus())

        assert container.get("user_service") is not None
        assert container.get("events") is not None

    def test_service_resolution(self):
        """Test resolving services from container."""
        container = DIContainer()
        container.register("events", EventBus())
        container.register(UserService)
        container.register(UserContext)

        # Resolve context
        ctx = container.get(UserContext)
        assert isinstance(ctx, UserContext)

        # Should return same instance (singleton)
        ctx2 = container.get(UserContext)
        assert ctx is ctx2

        # Resolve service
        service = container.get(UserService)
        assert isinstance(service, UserService)

    def test_dependency_injection_resolution(self):
        """Test automatic dependency resolution."""
        container = DIContainer()
        container.register("events", EventBus())

        # Register services with dependency injection
        container.register(UserService)

        # Resolve service
        service = container.get(UserService)
        assert isinstance(service, UserService)

    def test_circular_dependency_detection(self):
        """Test circular dependency detection and handling."""
        container = DIContainer()

        class ServiceA:
            def __init__(self):
                pass

        class ServiceB:
            def __init__(self, service_a: ServiceA = None):
                self.service_a = service_a

        container.register(ServiceA)
        container.register(ServiceB)

        # Should handle dependencies
        service_a = container.get(ServiceA)
        assert isinstance(service_a, ServiceA)

        service_b = container.get(ServiceB)
        assert isinstance(service_b, ServiceB)


@pytest.mark.asyncio
class TestContextIntegrationWithApp:
    """Test context integration with Zenith application."""

    async def test_context_registration_in_app(self):
        """Test registering contexts in Zenith app."""
        app = Zenith(debug=True)
        app.register_context("users", UserContext)
        app.register_context("notifications", NotificationContext)

        # Should be registered in context registry
        contexts = app.app.contexts
        assert "users" in contexts._context_classes
        assert contexts._context_classes["users"] == UserContext
        assert "notifications" in contexts._context_classes
        assert contexts._context_classes["notifications"] == NotificationContext

    async def test_context_injection_in_routes(self):
        """Test context injection in route handlers."""
        app = Zenith(debug=True)
        app.register_context("users", UserContext)

        @app.get("/users/{user_id}")
        async def get_user(user_id: int, ctx: UserContext = Inject()):
            return await ctx.get_user(user_id)

        @app.post("/users")
        async def create_user(name: str, email: str, ctx: UserContext = Inject()):
            return await ctx.create_user(name, email)

        from zenith.testing import TestClient

        async with TestClient(app) as client:
            # Test get user
            response = await client.get("/users/1")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "John"

            # Test create user
            response = await client.post(
                "/users", params={"name": "New User", "email": "new@test.com"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "New User"


class TestContextTesting:
    """Test the TestContext utility for testing contexts."""

    @pytest.mark.asyncio
    async def test_test_context_basic(self):
        """Test basic TestContext functionality."""
        # Note: TestContext utility may need implementation or we create manually
        container = DIContainer()
        container.register("events", EventBus())

        ctx = UserContext(container)
        assert isinstance(ctx, UserContext)

        # Test context methods
        user = await ctx.get_user(1)
        assert user["name"] == "John"

    @pytest.mark.asyncio
    async def test_test_context_with_mocks(self):
        """Test TestContext with mocked dependencies."""
        container = DIContainer()
        container.register("events", EventBus())

        mock_service = Mock()
        mock_service.get_user = AsyncMock(return_value={"id": 1, "name": "Mocked"})

        ctx = UserContext(container, user_service=mock_service)
        user = await ctx.get_user(1)
        assert user["name"] == "Mocked"
        mock_service.get_user.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_test_context_isolation(self):
        """Test that TestContext provides isolated instances."""
        # First context
        container1 = DIContainer()
        container1.register("events", EventBus())
        ctx1 = UserContext(container1)
        await ctx1.create_user("User1", "user1@test.com")
        await ctx1.list_users()

        # Second context should be isolated
        container2 = DIContainer()
        container2.register("events", EventBus())
        ctx2 = UserContext(container2)
        users2 = await ctx2.list_users()

        # Should have different instances with original data
        assert len(users2) == 2  # Original mock data
        assert not any(u["name"] == "User1" for u in users2)


class TestContextErrorHandling:
    """Test error handling in contexts."""

    @pytest.mark.asyncio
    async def test_context_method_errors(self):
        """Test error handling in context methods."""

        class ErrorService(Service):
            def __init__(self, container: DIContainer):
                super().__init__(container)

            async def failing_method(self):
                raise ValueError("Test error")

            async def db_error_method(self):
                raise ConnectionError("Database connection failed")

        container = DIContainer()
        container.register("events", EventBus())
        ctx = ErrorContext(container)

        # Test ValueError
        with pytest.raises(ValueError, match="Test error"):
            await ctx.failing_method()

        # Test ConnectionError
        with pytest.raises(ConnectionError, match="Database connection failed"):
            await ctx.db_error_method()

    @pytest.mark.asyncio
    async def test_context_dependency_errors(self):
        """Test error handling with dependency injection."""
        container = DIContainer()
        container.register("events", EventBus())

        mock_service = Mock()
        mock_service.get_user = AsyncMock(side_effect=Exception("Service error"))

        ctx = UserContext(container, user_service=mock_service)

        with pytest.raises(Exception, match="Service error"):
            await ctx.get_user(1)


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
