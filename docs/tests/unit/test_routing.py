"""
Unit tests for the core routing system.

Tests the Router class, dependency injection, and route handling.
"""

import pytest
from pydantic import BaseModel

from zenith import Zenith
from zenith.auth import configure_auth
from zenith.core.routing import (
    Auth,
    AuthDependency,
    File,
    FileDependency,
    Inject,
    InjectDependency,
    Router,
)
from zenith.testing import TestClient


class MockTestUser(BaseModel):
    name: str
    email: str
    age: int


class TestRouter:
    """Test suite for Router functionality."""

    def test_router_creation(self):
        """Test basic router creation."""
        router = Router()
        assert router.prefix == ""
        assert len(router.routes) == 0
        assert len(router.middleware) == 0

    def test_router_with_prefix(self):
        """Test router with prefix."""
        router = Router(prefix="/api/v1")
        assert router.prefix == "/api/v1"

    def test_route_decorators(self):
        """Test HTTP method decorators."""
        router = Router()

        @router.get("/users")
        async def get_users():
            return {"users": []}

        @router.post("/users")
        async def create_user():
            return {"created": True}

        @router.put("/users/{id}")
        async def update_user(id: int):
            return {"id": id, "updated": True}

        @router.delete("/users/{id}")
        async def delete_user(id: int):
            return {"id": id, "deleted": True}

        assert len(router.routes) == 4

        # Check route specifications
        get_route = router.routes[0]
        assert get_route.path == "/users"
        assert get_route.methods == ["GET"]
        assert get_route.handler == get_users

        post_route = router.routes[1]
        assert post_route.path == "/users"
        assert post_route.methods == ["POST"]

        put_route = router.routes[2]
        assert put_route.path == "/users/{id}"
        assert put_route.methods == ["PUT"]

        delete_route = router.routes[3]
        assert delete_route.path == "/users/{id}"
        assert delete_route.methods == ["DELETE"]

    def test_route_with_prefix(self):
        """Test route path prefixing."""
        router = Router(prefix="/api/v1")

        @router.get("/users")
        async def get_users():
            return {"users": []}

        route = router.routes[0]
        assert route.path == "/api/v1/users"

    def test_dependency_markers(self):
        """Test dependency injection markers."""
        # Context dependency
        ctx_dep = Inject()
        assert isinstance(ctx_dep, InjectDependency)

        # Auth dependency
        auth_dep = Auth()
        assert isinstance(auth_dep, AuthDependency)
        assert auth_dep.required
        assert auth_dep.scopes == []

        auth_optional = Auth(required=False, scopes=["admin"])
        assert not auth_optional.required
        assert auth_optional.scopes == ["admin"]

        # File dependency
        file_dep = File("upload")
        assert isinstance(file_dep, FileDependency)
        assert file_dep.field_name == "upload"


@pytest.mark.asyncio
class TestRouterIntegration:
    """Integration tests for router with full app."""

    async def test_path_parameters(self):
        """Test path parameter extraction and type conversion."""
        app = Zenith(debug=True)

        @app.get("/users/{user_id}")
        async def get_user(user_id: int):
            return {"user_id": user_id, "type": type(user_id).__name__}

        @app.get("/posts/{post_id}/comments/{comment_id}")
        async def get_comment(post_id: int, comment_id: str):
            return {
                "post_id": post_id,
                "comment_id": comment_id,
                "post_type": type(post_id).__name__,
                "comment_type": type(comment_id).__name__,
            }

        async with TestClient(app) as client:
            # Test integer conversion
            response = await client.get("/users/123")
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == 123
            assert data["type"] == "int"

            # Test mixed types
            response = await client.get("/posts/456/comments/abc123")
            assert response.status_code == 200
            data = response.json()
            assert data["post_id"] == 456
            assert data["comment_id"] == "abc123"
            assert data["post_type"] == "int"
            assert data["comment_type"] == "str"

    async def test_query_parameters(self):
        """Test query parameter extraction and type conversion."""
        app = Zenith(debug=True)

        @app.get("/search")
        async def search(
            q: str, limit: int = 10, sort: str = "name", active: bool = True
        ):
            return {
                "query": q,
                "limit": limit,
                "sort": sort,
                "active": active,
                "types": {
                    "limit": type(limit).__name__,
                    "active": type(active).__name__,
                },
            }

        async with TestClient(app) as client:
            # Test required and optional params
            response = await client.get("/search?q=python")
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "python"
            assert data["limit"] == 10  # default
            assert data["sort"] == "name"  # default
            assert data["active"]  # default

            # Test type conversion
            response = await client.get("/search?q=test&limit=5&active=false&sort=date")
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 5
            assert not data["active"]
            assert data["sort"] == "date"
            assert data["types"]["limit"] == "int"
            assert data["types"]["active"] == "bool"

    async def test_pydantic_validation(self):
        """Test Pydantic model validation."""
        app = Zenith(debug=True)

        @app.post("/api/users")
        async def create_user(user: MockTestUser):
            return {
                "name": user.name,
                "email": user.email,
                "age": user.age,
                "created": True,
            }

        async with TestClient(app) as client:
            # Test valid data
            user_data = {"name": "John", "email": "john@test.com", "age": 30}
            response = await client.post("/api/users", json=user_data)
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "John"
            assert data["created"]

            # Test validation errors
            invalid_data = {"name": "John"}  # Missing required fields
            response = await client.post("/api/users", json=invalid_data)
            assert response.status_code == 422
            data = response.json()
            assert data["error"] == "Validation failed"
            assert "details" in data

    async def test_authentication_dependency(self):
        """Test authentication dependency injection."""
        app = Zenith(debug=True)
        configure_auth(
            app, secret_key="test-secret-key-that-is-long-enough-for-jwt-signing"
        )
        app.add_exception_handling(debug=True)

        @app.get("/public")
        async def public_endpoint(current_user=Auth(required=False)):
            return {
                "message": "public",
                "authenticated": current_user is not None,
                "user": current_user,
            }

        @app.get("/protected")
        async def protected_endpoint(current_user=Auth(required=True)):
            return {"message": "protected", "user": current_user}

        async with TestClient(app) as client:
            # Test public endpoint without auth
            response = await client.get("/public")
            assert response.status_code == 200
            data = response.json()
            assert not data["authenticated"]
            assert data["user"] is None

            # Test public endpoint with auth
            client.set_auth_token("test@example.com", user_id=123, role="user")
            response = await client.get("/public")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"]
            assert data["user"]["id"] == 123

            # Test protected endpoint with auth
            response = await client.get("/protected")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == "test@example.com"

            # Test protected endpoint without auth
            client.clear_auth()
            response = await client.get("/protected")
            assert response.status_code == 401

    async def test_response_types(self):
        """Test different response types and validation."""
        app = Zenith(debug=True)

        @app.get("/dict")
        async def return_dict():
            return {"type": "dict", "data": [1, 2, 3]}

        @app.get("/list")
        async def return_list():
            return [{"id": 1}, {"id": 2}]

        @app.get("/model")
        async def return_model() -> MockTestUser:
            return MockTestUser(name="John", email="john@test.com", age=30)

        @app.get("/none")
        async def return_none():
            return None

        @app.get("/string")
        async def return_string():
            return "Hello World"

        async with TestClient(app) as client:
            # Test dict response
            response = await client.get("/dict")
            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "dict"
            assert data["data"] == [1, 2, 3]

            # Test list response
            response = await client.get("/list")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["id"] == 1

            # Test Pydantic model response
            response = await client.get("/model")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "John"
            assert data["email"] == "john@test.com"
            assert data["age"] == 30

            # Test None response
            response = await client.get("/none")
            assert response.status_code == 200
            data = response.json()
            assert data["result"] is None

            # Test string response
            response = await client.get("/string")
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "Hello World"

    async def test_error_handling(self):
        """Test error handling and exception conversion."""
        app = Zenith(debug=True)
        app.add_exception_handling(debug=True)

        @app.get("/value-error")
        async def value_error():
            raise ValueError("Test value error")

        @app.get("/type-error")
        async def type_error():
            raise TypeError("Test type error")

        @app.get("/custom-error")
        async def custom_error():
            from zenith.exceptions import NotFoundException

            raise NotFoundException("Resource not found")

        async with TestClient(app) as client:
            # Test ValueError handling
            response = await client.get("/value-error")
            assert response.status_code == 400
            data = response.json()
            assert "error" in data

            # Test TypeError handling
            response = await client.get("/type-error")
            assert response.status_code == 400
            data = response.json()
            assert "error" in data

            # Test custom exception
            response = await client.get("/custom-error")
            assert response.status_code == 404
            data = response.json()
            assert "Resource not found" in data["detail"]

    async def test_malformed_json_handling(self):
        """Test handling of malformed JSON in request bodies."""
        app = Zenith(debug=True)
        app.add_exception_handling(debug=True)

        class TestModel(BaseModel):
            name: str
            value: int

        @app.post("/test-json")
        async def test_endpoint(data: TestModel):
            return {"received": data.model_dump()}

        async with TestClient(app) as client:
            # Test invalid JSON syntax
            response = await client.post(
                "/test-json",
                headers={"Content-Type": "application/json"},
                content=b'{"name": "test", invalid}',
            )
            assert response.status_code == 422
            data = response.json()
            assert "Invalid JSON in request body" in data["detail"]

            # Test invalid UTF-8 encoding
            response = await client.post(
                "/test-json",
                headers={"Content-Type": "application/json"},
                content=b'\xff\xfe{"name": "test"}',
            )
            assert response.status_code == 422
            data = response.json()
            assert "Invalid JSON in request body" in data["detail"]

            # Test valid JSON for comparison
            response = await client.post(
                "/test-json", json={"name": "test", "value": 123}
            )
            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
