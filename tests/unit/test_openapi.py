"""
Tests for OpenAPI specification generator.

Tests caching functionality, spec generation, and performance optimizations.
"""

import inspect
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from zenith.core.routing import Router
from zenith.core.routing.specs import RouteSpec
from zenith.openapi.generator import OpenAPIGenerator, generate_openapi_spec


class UserModel(BaseModel):
    """Test model for OpenAPI schema generation."""

    id: int
    name: str
    email: str


class UserCreateModel(BaseModel):
    """Test model for request body."""

    name: str
    email: str


class TestOpenAPIGenerator:
    """Test suite for OpenAPI specification generator."""

    def test_generator_initialization(self):
        """Test OpenAPI generator initialization with defaults."""
        generator = OpenAPIGenerator()

        assert generator.title == "Zenith API"
        assert generator.version == "1.0.0"
        assert generator.description == "API built with Zenith framework"
        assert generator.servers == [{"url": "/", "description": "Development server"}]
        assert generator.schemas == {}
        assert generator.components == {"schemas": generator.schemas}

    def test_generator_custom_initialization(self):
        """Test OpenAPI generator with custom configuration."""
        servers = [{"url": "https://api.example.com", "description": "Production"}]
        generator = OpenAPIGenerator(
            title="Custom API",
            version="2.0.0",
            description="Custom description",
            servers=servers,
        )

        assert generator.title == "Custom API"
        assert generator.version == "2.0.0"
        assert generator.description == "Custom description"
        assert generator.servers == servers

    def test_basic_spec_generation(self):
        """Test basic OpenAPI spec generation without caching."""
        router = Router()

        async def test_handler():
            return {"message": "test"}

        route_spec = RouteSpec(path="/test", handler=test_handler, methods=["GET"])
        router.routes = [route_spec]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        # Check basic structure
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "Zenith API"
        assert spec["info"]["version"] == "1.0.0"
        assert "/test" in spec["paths"]
        assert "get" in spec["paths"]["/test"]

    def test_cache_key_generation_consistency(self):
        """Test that cache key generation is consistent for same inputs."""
        router1 = Router()
        router2 = Router()

        async def handler1():
            pass

        async def handler2():
            pass

        # Create identical route structures
        for router in [router1, router2]:
            router.routes = [
                RouteSpec("/api/users", handler1, ["GET", "POST"]),
                RouteSpec("/api/users/{id}", handler2, ["GET"]),
            ]

        generator = OpenAPIGenerator()

        key1 = generator._get_cache_key([router1])
        key2 = generator._get_cache_key([router2])

        # Should generate identical keys for identical structures
        assert key1 == key2

    def test_cache_key_generation_differences(self):
        """Test that cache key generation differs for different inputs."""
        router1 = Router()
        router2 = Router()

        async def handler():
            pass

        router1.routes = [RouteSpec("/api/users", handler, ["GET"])]
        router2.routes = [RouteSpec("/api/posts", handler, ["GET"])]

        generator = OpenAPIGenerator()

        key1 = generator._get_cache_key([router1])
        key2 = generator._get_cache_key([router2])

        # Should generate different keys for different structures
        assert key1 != key2

    def test_cache_functionality_hit(self):
        """Test caching functionality - cache hit scenario."""
        router = Router()

        async def test_handler():
            return {"test": True}

        router.routes = [RouteSpec("/test", test_handler, ["GET"])]

        generator = OpenAPIGenerator()

        # First call - cache miss
        spec1 = generator.generate_spec([router])

        # Second call - cache hit
        spec2 = generator.generate_spec([router])

        # Should return equal but separate copies
        assert spec1 == spec2
        assert spec1 is not spec2  # Different objects due to copy()

    def test_cache_prevents_mutation(self):
        """Test that cache returns copies to prevent mutation."""
        router = Router()

        async def test_handler():
            return {"test": True}

        router.routes = [RouteSpec("/test", test_handler, ["GET"])]

        generator = OpenAPIGenerator()

        # Get spec and modify it
        spec1 = generator.generate_spec([router])
        spec1["modified"] = True

        # Get spec again - should not have modification
        spec2 = generator.generate_spec([router])

        assert "modified" not in spec2
        assert spec1 != spec2

    def test_cache_size_management(self):
        """Test that cache size is managed and bounded."""
        generator = OpenAPIGenerator()

        # Generate 51 specs to trigger cache cleanup at 50 -> 25
        for i in range(51):
            router = Router()

            # Create unique handler to ensure different cache keys
            async def handler():
                return {"id": i}

            handler.__name__ = f"handler_{i}"  # Unique name for cache key

            router.routes = [RouteSpec(f"/test/{i}", handler, ["GET"])]
            generator.generate_spec([router])

        # After 51 generations: reached 50, then cleaned to 25, then added 1 more = 26
        assert len(generator._spec_cache) == 26

    def test_multiple_routers_handling(self):
        """Test handling multiple routers in single spec generation."""
        router1 = Router()
        router2 = Router()

        async def handler1():
            return {"route": "1"}

        async def handler2():
            return {"route": "2"}

        router1.routes = [RouteSpec("/api/v1/test", handler1, ["GET"])]
        router2.routes = [RouteSpec("/api/v2/test", handler2, ["POST"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router1, router2])

        # Both routes should be in spec
        assert "/api/v1/test" in spec["paths"]
        assert "/api/v2/test" in spec["paths"]
        assert "get" in spec["paths"]["/api/v1/test"]
        assert "post" in spec["paths"]["/api/v2/test"]

    def test_pydantic_model_schema_generation(self):
        """Test Pydantic model integration and schema generation."""
        router = Router()

        async def create_user(user: UserCreateModel) -> UserModel:
            return UserModel(id=1, **user.model_dump())

        router.routes = [RouteSpec("/users", create_user, ["POST"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        # Check request body schema reference
        request_body = spec["paths"]["/users"]["post"]["requestBody"]
        assert request_body["required"] is True
        schema_ref = request_body["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/UserCreateModel"

        # Check response schema reference
        response_schema = spec["paths"]["/users"]["post"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]["$ref"]
        assert response_schema == "#/components/schemas/UserModel"

        # Check that schemas are added to components
        assert "UserCreateModel" in spec["components"]["schemas"]
        assert "UserModel" in spec["components"]["schemas"]

    def test_path_parameter_detection(self):
        """Test path parameter detection and documentation."""
        router = Router()

        async def get_user(user_id: int):
            return {"user_id": user_id}

        router.routes = [RouteSpec("/users/{user_id}", get_user, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        # Check path parameter documentation
        parameters = spec["paths"]["/users/{user_id}"]["get"]["parameters"]
        path_param = next(p for p in parameters if p["in"] == "path")

        assert path_param["name"] == "user_id"
        assert path_param["required"] is True
        assert path_param["schema"]["type"] == "integer"

    def test_query_parameter_detection(self):
        """Test query parameter detection and documentation."""
        router = Router()

        async def search_users(name: str = None, limit: int = 10):
            return {"name": name, "limit": limit}

        router.routes = [RouteSpec("/users/search", search_users, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        parameters = spec["paths"]["/users/search"]["get"]["parameters"]

        # Check optional parameter
        name_param = next(p for p in parameters if p["name"] == "name")
        assert name_param["required"] is False
        assert name_param["in"] == "query"

        # Check parameter with default
        limit_param = next(p for p in parameters if p["name"] == "limit")
        assert limit_param["required"] is False
        assert limit_param["schema"]["type"] == "integer"

    def test_operation_summary_from_docstring(self):
        """Test operation summary extraction from handler docstrings."""
        router = Router()

        async def get_users():
            """Get all users from the system."""
            return {"users": []}

        router.routes = [RouteSpec("/users", get_users, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        operation = spec["paths"]["/users"]["get"]
        assert operation["summary"] == "Get all users from the system."

    def test_operation_summary_fallback(self):
        """Test operation summary generation when no docstring."""
        router = Router()

        # Create handler with exec to ensure no docstring inheritance
        handler_code = """
async def no_docstring_handler():
    return {"users": []}
"""
        namespace = {}
        exec(handler_code, namespace)
        no_docstring_handler = namespace["no_docstring_handler"]

        # Verify handler has no docstring
        assert no_docstring_handler.__doc__ is None

        router.routes = [RouteSpec("/users", no_docstring_handler, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        operation = spec["paths"]["/users"]["get"]
        assert operation["summary"] == "GET No Docstring Handler"

    def test_generate_openapi_spec_function(self):
        """Test convenience function for OpenAPI spec generation."""
        router = Router()

        async def test_handler():
            return {"test": True}

        router.routes = [RouteSpec("/test", test_handler, ["GET"])]

        spec = generate_openapi_spec(
            routers=[router],
            title="Test API",
            version="1.2.3",
            description="Test description",
        )

        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "1.2.3"
        assert spec["info"]["description"] == "Test description"
        assert "/test" in spec["paths"]


class TestOpenAPICachePerformance:
    """Performance-focused tests for OpenAPI caching."""

    def test_cache_performance_improvement(self):
        """Test that caching provides performance improvement."""
        import time

        # Create complex router structure for measurable generation time
        routers = []
        for i in range(5):  # Multiple routers
            router = Router()
            router.routes = []

            for j in range(20):  # Multiple routes per router

                async def handler():
                    return {"data": f"route_{i}_{j}"}

                handler.__name__ = f"handler_{i}_{j}"

                router.routes.append(
                    RouteSpec(f"/api/v{i}/resource/{j}", handler, ["GET", "POST"])
                )
            routers.append(router)

        generator = OpenAPIGenerator()

        # First generation (cache miss)
        start_time = time.time()
        spec1 = generator.generate_spec(routers)
        first_gen_time = time.time() - start_time

        # Second generation (cache hit)
        start_time = time.time()
        spec2 = generator.generate_spec(routers)
        second_gen_time = time.time() - start_time

        # Cache hit should be significantly faster
        assert second_gen_time < first_gen_time / 2  # At least 2x faster
        assert spec1 == spec2

    def test_cache_memory_efficiency(self):
        """Test cache memory usage stays bounded."""
        generator = OpenAPIGenerator()
        initial_cache_size = len(generator._spec_cache)

        # Generate many different specs to trigger cleanup
        for i in range(60):  # Exceed the 50 entry limit to trigger cleanup
            router = Router()

            async def handler():
                return {"id": i}

            handler.__name__ = f"unique_handler_{i}"

            router.routes = [RouteSpec(f"/unique/{i}", handler, ["GET"])]
            generator.generate_spec([router])

        # Cache should not grow unbounded - after cleanup cycle it should be manageable
        assert len(generator._spec_cache) <= 50  # Should never exceed the trigger limit

        # Verify cache management is working (cleanup happened and cache is growing again)
        assert (
            len(generator._spec_cache) > 25
        )  # But more than 25 because it grows after cleanup

        # Should be significantly less than unbounded growth (would be 60 without management)
        assert len(generator._spec_cache) < 60
