"""
Tests for OpenAPI specification generator.

Tests caching functionality, spec generation, and performance optimizations.
"""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

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


class UserStatus(Enum):
    """Test enum for OpenAPI schema generation."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


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

            # Create unique handler with bound variable to fix B023
            async def handler(id_val=i):
                return {"id": id_val}

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

        async def search_users(name: str | None = None, limit: int = 10):
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

                async def handler(i_val=i, j_val=j):
                    return {"data": f"route_{i_val}_{j_val}"}

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
        len(generator._spec_cache)

        # Generate many different specs to trigger cleanup
        for i in range(60):  # Exceed the 50 entry limit to trigger cleanup
            router = Router()

            async def handler(id_val=i):
                return {"id": id_val}

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


class TestRouteSpecFields:
    """Test suite for RouteSpec field support in OpenAPI generation."""

    def test_include_in_schema_false(self):
        """Test that routes with include_in_schema=False are excluded."""
        router = Router()

        async def hidden_handler():
            return {"secret": True}

        async def visible_handler():
            return {"visible": True}

        router.routes = [
            RouteSpec("/hidden", hidden_handler, ["GET"], include_in_schema=False),
            RouteSpec("/visible", visible_handler, ["GET"], include_in_schema=True),
        ]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        assert "/hidden" not in spec["paths"]
        assert "/visible" in spec["paths"]

    def test_tags_field(self):
        """Test that tags from RouteSpec are included in operation."""
        router = Router()

        async def get_users():
            return []

        router.routes = [
            RouteSpec("/users", get_users, ["GET"], tags=["users", "admin"])
        ]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        operation = spec["paths"]["/users"]["get"]
        assert operation["tags"] == ["users", "admin"]

    def test_status_code_field(self):
        """Test that status_code from RouteSpec is used."""
        router = Router()

        async def create_user():
            return {"created": True}

        router.routes = [RouteSpec("/users", create_user, ["POST"], status_code=201)]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        responses = spec["paths"]["/users"]["post"]["responses"]
        assert "201" in responses
        # 200 should not be present as the success response
        assert (
            "200" not in responses
            or responses.get("200", {}).get("description") == "Successful Response"
        )

    def test_response_description_field(self):
        """Test that response_description from RouteSpec is used."""
        router = Router()

        async def get_users():
            return []

        router.routes = [
            RouteSpec(
                "/users",
                get_users,
                ["GET"],
                response_description="List of all users",
            )
        ]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        response = spec["paths"]["/users"]["get"]["responses"]["200"]
        assert response["description"] == "List of all users"

    def test_summary_field(self):
        """Test that summary from RouteSpec takes precedence over docstring."""
        router = Router()

        async def get_users():
            """This should be overridden."""
            return []

        router.routes = [
            RouteSpec("/users", get_users, ["GET"], summary="Get All Users")
        ]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        operation = spec["paths"]["/users"]["get"]
        assert operation["summary"] == "Get All Users"

    def test_description_field(self):
        """Test that description from RouteSpec takes precedence over docstring."""
        router = Router()

        async def get_users():
            """This description should be overridden."""
            return []

        router.routes = [
            RouteSpec(
                "/users",
                get_users,
                ["GET"],
                description="Retrieves all users from the database.",
            )
        ]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        operation = spec["paths"]["/users"]["get"]
        assert operation["description"] == "Retrieves all users from the database."

    def test_response_model_field(self):
        """Test that response_model from RouteSpec overrides return type."""
        router = Router()

        async def get_user() -> dict:  # Return type is dict
            return {}

        router.routes = [
            RouteSpec(
                "/users/{id}",
                get_user,
                ["GET"],
                response_model=UserModel,  # But we want UserModel schema
            )
        ]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        response_schema = spec["paths"]["/users/{id}"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/UserModel"}
        assert "UserModel" in spec["components"]["schemas"]


class TestTypeInference:
    """Test suite for improved type inference in OpenAPI generation."""

    def test_datetime_type(self):
        """Test datetime type inference."""
        router = Router()

        async def get_timestamp(created_at: datetime):
            return {"timestamp": created_at}

        router.routes = [RouteSpec("/timestamp", get_timestamp, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        params = spec["paths"]["/timestamp"]["get"]["parameters"]
        created_param = next(p for p in params if p["name"] == "created_at")
        assert created_param["schema"]["type"] == "string"
        assert created_param["schema"]["format"] == "date-time"

    def test_date_type(self):
        """Test date type inference."""
        router = Router()

        async def get_date(birth_date: date):
            return {"date": birth_date}

        router.routes = [RouteSpec("/date", get_date, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        params = spec["paths"]["/date"]["get"]["parameters"]
        date_param = next(p for p in params if p["name"] == "birth_date")
        assert date_param["schema"]["type"] == "string"
        assert date_param["schema"]["format"] == "date"

    def test_uuid_type(self):
        """Test UUID type inference."""
        router = Router()

        async def get_by_uuid(user_id: UUID):
            return {"id": user_id}

        router.routes = [RouteSpec("/users/{user_id}", get_by_uuid, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        params = spec["paths"]["/users/{user_id}"]["get"]["parameters"]
        uuid_param = next(p for p in params if p["name"] == "user_id")
        assert uuid_param["schema"]["type"] == "string"
        assert uuid_param["schema"]["format"] == "uuid"

    def test_enum_type(self):
        """Test Enum type inference."""
        router = Router()

        async def filter_by_status(status: UserStatus):
            return {"status": status}

        router.routes = [RouteSpec("/users/filter", filter_by_status, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        params = spec["paths"]["/users/filter"]["get"]["parameters"]
        status_param = next(p for p in params if p["name"] == "status")
        assert status_param["schema"]["type"] == "string"
        assert status_param["schema"]["enum"] == ["active", "inactive", "pending"]

    def test_list_with_type_param(self):
        """Test List[T] type inference."""
        router = Router()

        async def get_users() -> list[UserModel]:
            return []

        router.routes = [RouteSpec("/users", get_users, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        response_schema = spec["paths"]["/users"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert response_schema["type"] == "array"
        assert response_schema["items"] == {"$ref": "#/components/schemas/UserModel"}

    def test_dict_with_type_params(self):
        """Test Dict[K, V] type inference."""
        router = Router()

        async def get_config() -> dict[str, int]:
            return {}

        router.routes = [RouteSpec("/config", get_config, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        response_schema = spec["paths"]["/config"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
        assert response_schema["type"] == "object"
        assert response_schema["additionalProperties"] == {"type": "integer"}

    def test_optional_type(self):
        """Test Optional[T] / T | None type inference."""
        router = Router()

        async def search(query: str | None = None):
            return {"query": query}

        router.routes = [RouteSpec("/search", search, ["GET"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        params = spec["paths"]["/search"]["get"]["parameters"]
        query_param = next(p for p in params if p["name"] == "query")
        assert query_param["schema"]["type"] == "string"
        assert query_param["schema"]["nullable"] is True

    def test_bytes_type(self):
        """Test bytes type inference."""
        router = Router()

        async def upload(data: bytes):
            return {"size": len(data)}

        router.routes = [RouteSpec("/upload", upload, ["POST"])]

        generator = OpenAPIGenerator()
        spec = generator.generate_spec([router])

        params = spec["paths"]["/upload"]["post"]["parameters"]
        data_param = next(p for p in params if p["name"] == "data")
        assert data_param["schema"]["type"] == "string"
        assert data_param["schema"]["format"] == "binary"
