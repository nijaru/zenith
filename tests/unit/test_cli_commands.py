"""
Tests for Zenith CLI commands.
"""

from zenith.dev.generators import (
    APIGenerator,
    ModelGenerator,
    ServiceGenerator,
    generate_code,
    parse_field_spec,
)

# Shell functionality removed - no longer part of CLI


# Shell tests removed - shell functionality was removed from CLI
# These tests were for non-existent features


class TestCodeGenerators:
    """Test code generation functionality."""

    def test_model_generator(self):
        """Test model code generation."""
        generator = ModelGenerator(
            "user_profile",
            fields={"name": "str", "email": "str", "age": "int", "active": "bool?"},
        )

        files = generator.generate()
        assert "models/user_profile.py" in files

        code = files["models/user_profile.py"]
        assert "class UserProfile(SQLModel" in code
        assert '__tablename__ = "user_profiles"' in code
        assert "name: str" in code
        assert "age: int" in code
        assert "active: bool | None" in code
        assert "created_at: datetime" in code

    def test_service_generator(self):
        """Test service code generation."""
        generator = ServiceGenerator("user", model="User")

        files = generator.generate()
        assert "services/user_service.py" in files

        code = files["services/user_service.py"]
        assert "class UserService(Service):" in code
        assert "async def get_all(" in code
        assert "async def get_by_id(" in code
        assert "async def create(" in code
        assert "async def update(" in code
        assert "async def delete(" in code

    def test_api_generator(self):
        """Test API route generation."""
        generator = APIGenerator("product", model="Product")

        files = generator.generate()
        assert "routes/product_api.py" in files

        code = files["routes/product_api.py"]
        assert 'router = Router(prefix="/products")' in code
        assert '@router.get("/"' in code
        assert '@router.post("/"' in code
        assert '@router.patch("/{product_id}"' in code
        assert '@router.delete("/{product_id}"' in code
        assert "ProductCreate(BaseModel):" in code
        assert "ProductUpdate(BaseModel):" in code

    def test_parse_field_spec(self):
        """Test field specification parsing."""
        fields = parse_field_spec("name:str email:str age:int active:bool?")

        assert fields == {
            "name": "str",
            "email": "str",
            "age": "int",
            "active": "bool?",
        }

    def test_generate_code_model(self):
        """Test generate_code function for models."""
        files = generate_code(
            "model",
            "article",
            fields={"title": "str", "content": "text", "published": "bool"},
        )

        assert "models/article.py" in files
        code = files["models/article.py"]
        assert "class Article(SQLModel" in code

    def test_name_conversions(self):
        """Test name conversion methods."""
        generator = ModelGenerator("user_profile")

        assert generator.class_name == "UserProfile"
        assert generator.variable_name == "user_profile"
        assert generator.table_name == "user_profiles"

        # Test with different patterns
        generator2 = ModelGenerator("category")
        assert generator2.table_name == "categories"

        generator3 = ModelGenerator("class")
        assert generator3.table_name == "classes"
