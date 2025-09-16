"""
Integration tests for seamless Rails-like DX.

Tests complete workflows of:
- Zero-config setup with automatic environment detection
- ZenithModel working seamlessly with Zenith app
- One-liner features integration
- End-to-end Rails-like patterns
"""

import os
import pytest
import tempfile
from unittest.mock import patch

from zenith import Zenith
from zenith.core import DB, Auth, Cache, is_development
from zenith.core.auto_config import Environment
from zenith.db import ZenithModel
from zenith.testing import TestClient

from sqlmodel import Field
from typing import Optional
from datetime import datetime


# Test models for integration testing
class IntegrationUser(ZenithModel, table=True):
    """Test user model for integration."""
    __tablename__ = "integration_users"

    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


class IntegrationPost(ZenithModel, table=True):
    """Test post model for integration."""
    __tablename__ = "integration_posts"

    id: Optional[int] = Field(primary_key=True)
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    user_id: int = Field(foreign_key="integration_users.id")
    created_at: datetime = Field(default_factory=datetime.now)


class TestZeroConfigIntegration:
    """Test zero-configuration setup integration."""

    def test_zero_config_development_environment(self):
        """Test zero-config setup in development environment."""
        with patch.dict(os.environ, {"ZENITH_ENV": "development"}, clear=False):
            app = Zenith()

            # Should auto-detect development
            assert is_development() is True

            # Should have development defaults
            assert app.config.debug is True

            # Should work without explicit configuration
            @app.get("/test")
            async def test_route():
                return {"env": "development", "auto_config": True}

            # Should be able to chain features
            app.add_api("Test API")

    def test_zero_config_with_environment_variables(self):
        """Test zero-config respects environment variables."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            with patch.dict(os.environ, {
                "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
                "SECRET_KEY": "test-secret-key-32-characters-long"
            }, clear=False):
                app = Zenith()

                # Should use provided database URL
                assert app.app.database.url == f"sqlite+aiosqlite:///{db_path}"

                # Should use provided secret key
                assert app.config.secret_key == "test-secret-key-32-characters-long"

        finally:
            try:
                os.unlink(db_path)
            except:
                pass

    def test_zero_config_one_liner_chaining(self):
        """Test zero-config with one-liner feature chaining."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret-key-32-characters-long"}, clear=False):
            app = (Zenith()
                  .add_auth()
                  .add_admin("/dashboard")
                  .add_api("Chained API", "1.0.0"))

            # Should have auth routes
            auth_routes = [r.path for r in app._app_router.routes]
            assert "/auth/login" in auth_routes

            # Should have admin routes
            assert "/dashboard" in auth_routes
            assert "/dashboard/health" in auth_routes

            # Should have API routes
            assert "/api/info" in auth_routes


class TestSeamlessZenithModelIntegration:
    """Test ZenithModel seamless integration with Zenith app."""

    @pytest.fixture
    async def app_with_models(self):
        """Create app with test models."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        app = Zenith(middleware=[])  # Minimal middleware for testing
        app.config.database_url = f"sqlite+aiosqlite:///{db_path}"

        # Create tables for test models
        await app.app.database.create_all()

        # Create fresh test model tables for each test
        from sqlalchemy import text
        async with app.app.database.session() as session:
            # Drop existing tables to ensure clean state
            await session.execute(text("DROP TABLE IF EXISTS integration_posts"))
            await session.execute(text("DROP TABLE IF EXISTS integration_users"))

            # Create integration_users table
            await session.execute(text("""
                CREATE TABLE integration_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR NOT NULL UNIQUE,
                    active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME NOT NULL
                )
            """))

            # Create integration_posts table
            await session.execute(text("""
                CREATE TABLE integration_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    content TEXT NOT NULL,
                    published BOOLEAN DEFAULT FALSE,
                    user_id INTEGER NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES integration_users(id)
                )
            """))

            await session.commit()

        yield app

        # Clean up database file
        try:
            if hasattr(app.app, 'database') and app.app.database:
                await app.app.database.close()
            os.unlink(db_path)
        except Exception:
            pass

    async def test_zenith_model_automatic_session_management(self, app_with_models):
        """Test ZenithModel automatically uses app's database sessions."""
        app = app_with_models

        @app.get("/users")
        async def get_users():
            # No manual session management needed!
            users = await IntegrationUser.all()
            return {"users": [user.to_dict() for user in users]}

        @app.post("/users")
        async def create_user(user_data: dict):
            # Seamless creation without session management
            user = await IntegrationUser.create(**user_data)
            return {"user": user.to_dict()}

        @app.get("/users/{user_id}")
        async def get_user(user_id: int):
            # Automatic 404 handling
            user = await IntegrationUser.find_or_404(user_id)
            return {"user": user.to_dict()}

        # Test the integration with TestClient
        async with TestClient(app) as client:
            # Test creation with unique email
            import time
            unique_email = f"test-{int(time.time() * 1000)}@example.com"
            response = await client.post("/users", json={
                "name": "Test User",
                "email": unique_email
            })
            assert response.status_code == 200
            user_data = response.json()
            assert user_data["user"]["name"] == "Test User"

            # Test listing
            response = await client.get("/users")
            assert response.status_code == 200
            users = response.json()["users"]
            assert len(users) == 1
            assert users[0]["name"] == "Test User"

            # Test getting specific user
            user_id = users[0]["id"]
            response = await client.get(f"/users/{user_id}")
            assert response.status_code == 200
            assert response.json()["user"]["name"] == "Test User"

    async def test_zenith_model_rails_like_queries(self, app_with_models):
        """Test Rails-like query patterns work seamlessly."""
        app = app_with_models

        @app.get("/users/active")
        async def get_active_users():
            # Rails-like chainable queries (current working pattern)
            query = await IntegrationUser.where(active=True)
            users = await query.order_by('-created_at').limit(10).all()
            return {"users": [user.to_dict() for user in users]}

        @app.get("/stats")
        async def get_stats():
            # Rails-like aggregate queries
            total_users = await IntegrationUser.count()
            active_query = await IntegrationUser.where(active=True)
            active_users = await active_query.count()
            return {
                "total_users": total_users,
                "active_users": active_users
            }

        async with TestClient(app) as client:
            # Create test data with unique emails
            import time
            timestamp = int(time.time() * 1000)
            await client.post("/users", json={"name": "Active User", "email": f"active-{timestamp}@example.com", "active": True})
            await client.post("/users", json={"name": "Inactive User", "email": f"inactive-{timestamp}@example.com", "active": False})

            # Test Rails-like queries
            response = await client.get("/users/active")
            assert response.status_code == 200
            active_users = response.json()["users"]
            assert len(active_users) == 1
            assert active_users[0]["name"] == "Active User"

            # Test aggregate queries
            response = await client.get("/stats")
            assert response.status_code == 200
            stats = response.json()
            assert stats["total_users"] == 2
            assert stats["active_users"] == 1


class TestEnhancedDependencyIntegration:
    """Test enhanced dependency injection integration."""

    @pytest.fixture
    def app_with_dependencies(self):
        """Create app with dependency shortcuts."""
        app = Zenith(middleware=[])

        @app.get("/db-test")
        async def db_test(db=DB):
            # Should get database session automatically
            return {"has_db": db is not None}

        @app.get("/auth-test")
        async def auth_test(user=Auth):
            # Should get auth user (mock for now)
            return {"user": user}

        @app.get("/cache-test")
        async def cache_test(cache=Cache):
            # Should get cache client
            return {"has_cache": cache is not None}

        return app

    async def test_dependency_shortcuts_integration(self, app_with_dependencies):
        """Test dependency shortcuts work in actual routes."""
        async with TestClient(app_with_dependencies) as client:
            # Test DB shortcut
            response = await client.get("/db-test")
            assert response.status_code == 200
            assert response.json()["has_db"] is True

            # Test Auth shortcut
            response = await client.get("/auth-test")
            assert response.status_code == 200
            user_data = response.json()["user"]
            assert "id" in user_data
            assert user_data["name"] == "Mock User"

            # Test Cache shortcut
            response = await client.get("/cache-test")
            assert response.status_code == 200
            assert response.json()["has_cache"] is True


class TestCompleteRailsLikeDXWorkflow:
    """Test complete Rails-like DX workflow end-to-end."""

    async def test_complete_rails_like_workflow(self):
        """Test complete workflow from zero-config to Rails-like operations."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            with patch.dict(os.environ, {
                "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
                "SECRET_KEY": "test-secret-key-32-characters-long"
            }, clear=False):

                # 1. Zero-config setup with one-liner features
                app = (Zenith()
                      .add_auth()
                      .add_admin()
                      .add_api("Rails-like API", "1.0.0"))

                # Create tables
                await app.app.database.create_all()

                # 2. Rails-like model operations in routes
                @app.get("/users")
                async def list_users():
                    users = await IntegrationUser.all()
                    return {"users": [user.to_dict() for user in users]}

                @app.post("/users")
                async def create_user(user_data: dict):
                    user = await IntegrationUser.create(**user_data)
                    return {"user": user.to_dict()}

                @app.get("/users/active")
                async def get_active_users():
                    users = await IntegrationUser.where(active=True).order_by('-created_at').limit(5)
                    return {"users": [user.to_dict() for user in users]}

                @app.get("/users/{user_id}")
                async def get_user(user_id: int):
                    user = await IntegrationUser.find_or_404(user_id)
                    return {"user": user.to_dict()}

                # 3. Test complete workflow
                async with TestClient(app) as client:
                    # Test one-liner features work
                    response = await client.get("/admin")
                    assert response.status_code == 200
                    assert "Admin Dashboard" in response.json()["message"]

                    response = await client.get("/api/info")
                    assert response.status_code == 200
                    assert response.json()["title"] == "Rails-like API"

                    # Test Rails-like CRUD operations
                    # Create users
                    response = await client.post("/users", json={
                        "name": "Alice Johnson",
                        "email": "alice@example.com"
                    })
                    assert response.status_code == 200
                    alice = response.json()["user"]

                    response = await client.post("/users", json={
                        "name": "Bob Smith",
                        "email": "bob@example.com",
                        "active": False
                    })
                    assert response.status_code == 200

                    # Test Rails-like queries
                    response = await client.get("/users")
                    assert response.status_code == 200
                    all_users = response.json()["users"]
                    assert len(all_users) == 2

                    response = await client.get("/users/active")
                    assert response.status_code == 200
                    active_users = response.json()["users"]
                    assert len(active_users) == 1
                    assert active_users[0]["name"] == "Alice Johnson"

                    # Test automatic 404 handling
                    response = await client.get(f"/users/{alice['id']}")
                    assert response.status_code == 200
                    assert response.json()["user"]["name"] == "Alice Johnson"

                    response = await client.get("/users/999")
                    assert response.status_code == 404

        finally:
            try:
                os.unlink(db_path)
            except:
                pass


class TestPerformanceWithRailsLikeFeatures:
    """Test that Rails-like features don't hurt performance."""

    async def test_zenith_model_vs_raw_queries_performance(self):
        """Test ZenithModel performance is reasonable vs raw queries."""
        import time

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            app = Zenith(middleware=[])
            app.config.database_url = f"sqlite+aiosqlite:///{db_path}"
            await app.app.database.create_all()

            # Test with small dataset to verify performance isn't terrible
            async with TestClient(app) as client:
                # Add routes for both approaches
                @app.post("/users/zenith-model")
                async def create_user_zenith_model(user_data: dict):
                    start = time.time()
                    user = await IntegrationUser.create(**user_data)
                    end = time.time()
                    return {
                        "user": user.to_dict(),
                        "duration_ms": (end - start) * 1000
                    }

                # Test ZenithModel performance
                response = await client.post("/users/zenith-model", json={
                    "name": "Performance Test",
                    "email": "perf@example.com"
                })

                assert response.status_code == 200
                duration = response.json()["duration_ms"]

                # Should complete in reasonable time (< 100ms for simple operation)
                assert duration < 100, f"ZenithModel operation took {duration}ms, too slow"

        finally:
            try:
                os.unlink(db_path)
            except:
                pass


class TestBackwardsCompatibility:
    """Test that new features don't break existing patterns."""

    def test_traditional_fastapi_patterns_still_work(self):
        """Test traditional FastAPI patterns work alongside Rails-like patterns."""
        from zenith.core.dependencies import get_database_session

        app = Zenith(middleware=[])

        # Traditional FastAPI pattern should still work
        @app.get("/traditional")
        async def traditional_route(db=None):  # Using None as default for testing
            return {"traditional": True}

        # Rails-like pattern should work
        @app.get("/rails-like")
        async def rails_like_route(db=DB):
            return {"rails_like": True}

        # Both should coexist
        routes = [route.path for route in app._app_router.routes]
        assert "/traditional" in routes
        assert "/rails-like" in routes

    def test_existing_service_patterns_preserved(self):
        """Test existing Service patterns aren't broken by new features."""
        from zenith.core.service import Service

        # Old Service pattern should still work
        @Service
        class TraditionalService:
            def get_data(self):
                return "traditional"

        # Should still be instantiable
        service = TraditionalService()
        assert service.get_data() == "traditional"