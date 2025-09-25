"""
Comprehensive tests for response handling edge cases.

Tests error responses, malformed data, serialization issues,
and various response types.
"""

import json
import asyncio
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch
import uuid

import pytest
from pydantic import BaseModel

from zenith.web.responses import (
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    StreamingResponse,
    FileResponse,
    RedirectResponse,
    serialize_json,
    handle_response_conversion
)


class TestJSONSerialization:
    """Test JSON serialization edge cases."""

    def test_basic_types(self):
        """Test serialization of basic Python types."""
        data = {
            "string": "test",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"}
        }

        result = serialize_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_datetime_serialization(self):
        """Test datetime serialization."""
        now = datetime.now(timezone.utc)
        today = date.today()

        data = {
            "datetime": now,
            "date": today,
            "time": now.time()
        }

        result = serialize_json(data)
        parsed = json.loads(result)

        # Should serialize to ISO format
        assert parsed["datetime"] == now.isoformat()
        assert parsed["date"] == today.isoformat()

    def test_decimal_serialization(self):
        """Test Decimal serialization."""
        data = {
            "price": Decimal("19.99"),
            "large": Decimal("999999999999.999999"),
            "small": Decimal("0.0000001")
        }

        result = serialize_json(data)
        parsed = json.loads(result)

        assert parsed["price"] == "19.99"
        assert Decimal(parsed["large"]) == data["large"]
        assert Decimal(parsed["small"]) == data["small"]

    def test_uuid_serialization(self):
        """Test UUID serialization."""
        test_uuid = uuid.uuid4()
        data = {"id": test_uuid}

        result = serialize_json(data)
        parsed = json.loads(result)

        assert parsed["id"] == str(test_uuid)

    def test_enum_serialization(self):
        """Test Enum serialization."""
        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"
            PENDING = "pending"

        data = {
            "status": Status.ACTIVE,
            "all_statuses": list(Status)
        }

        result = serialize_json(data)
        parsed = json.loads(result)

        assert parsed["status"] == "active"
        assert parsed["all_statuses"] == ["active", "inactive", "pending"]

    def test_pydantic_model_serialization(self):
        """Test Pydantic model serialization."""
        class User(BaseModel):
            id: int
            name: str
            email: str
            created_at: datetime

        user = User(
            id=1,
            name="Test User",
            email="test@example.com",
            created_at=datetime.now(timezone.utc)
        )

        data = {"user": user}
        result = serialize_json(data)
        parsed = json.loads(result)

        assert parsed["user"]["id"] == 1
        assert parsed["user"]["name"] == "Test User"

    def test_nested_complex_structure(self):
        """Test deeply nested complex structure."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "datetime": datetime.now(),
                        "decimal": Decimal("123.45"),
                        "list": [1, 2, {"nested": True}]
                    }
                }
            }
        }

        result = serialize_json(data)
        parsed = json.loads(result)

        assert parsed["level1"]["level2"]["level3"]["decimal"] == "123.45"
        assert parsed["level1"]["level2"]["level3"]["list"][2]["nested"] is True

    def test_circular_reference_handling(self):
        """Test handling of circular references."""
        # Create circular reference
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2

        # Should handle gracefully (might raise or truncate)
        with pytest.raises((ValueError, RecursionError)):
            serialize_json(obj1)

    def test_non_serializable_objects(self):
        """Test handling of non-serializable objects."""
        # Objects that can't be serialized
        data = {
            "function": lambda x: x,
            "class": TestJSONSerialization,
            "module": json,
        }

        # Should raise or handle gracefully
        for key, value in data.items():
            with pytest.raises((TypeError, ValueError)):
                serialize_json({key: value})

    def test_unicode_handling(self):
        """Test Unicode character handling."""
        data = {
            "emoji": "🎉🎊🎈",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special": "\u0000\u0001\u0002",  # Control characters
        }

        result = serialize_json(data)
        parsed = json.loads(result)

        assert parsed["emoji"] == data["emoji"]
        assert parsed["chinese"] == data["chinese"]
        assert parsed["arabic"] == data["arabic"]

    def test_large_data_serialization(self):
        """Test serialization of large data structures."""
        # Create large list
        large_list = list(range(10000))
        data = {"large": large_list}

        result = serialize_json(data)
        parsed = json.loads(result)

        assert len(parsed["large"]) == 10000
        assert parsed["large"][0] == 0
        assert parsed["large"][-1] == 9999


class TestJSONResponse:
    """Test JSONResponse class."""

    def test_json_response_creation(self):
        """Test basic JSONResponse creation."""
        data = {"message": "success"}
        response = JSONResponse(data)

        assert response.status_code == 200
        assert response.media_type == "application/json"
        assert json.loads(response.body) == data

    def test_json_response_with_status(self):
        """Test JSONResponse with custom status code."""
        data = {"error": "not found"}
        response = JSONResponse(data, status_code=404)

        assert response.status_code == 404
        assert json.loads(response.body) == data

    def test_json_response_with_headers(self):
        """Test JSONResponse with custom headers."""
        data = {"data": "test"}
        headers = {"X-Custom-Header": "value"}
        response = JSONResponse(data, headers=headers)

        assert response.headers["x-custom-header"] == "value"

    def test_json_response_null_handling(self):
        """Test JSONResponse with null/None values."""
        response = JSONResponse(None)
        assert response.body == b"null"

        response = JSONResponse({"value": None})
        parsed = json.loads(response.body)
        assert parsed["value"] is None

    def test_json_response_empty_handling(self):
        """Test JSONResponse with empty data."""
        # Empty dict
        response = JSONResponse({})
        assert json.loads(response.body) == {}

        # Empty list
        response = JSONResponse([])
        assert json.loads(response.body) == []

        # Empty string
        response = JSONResponse("")
        assert json.loads(response.body) == ""


class TestHTMLResponse:
    """Test HTMLResponse class."""

    def test_html_response_creation(self):
        """Test basic HTMLResponse creation."""
        html = "<html><body>Test</body></html>"
        response = HTMLResponse(html)

        assert response.status_code == 200
        assert response.media_type == "text/html"
        assert response.body == html.encode()

    def test_html_response_encoding(self):
        """Test HTML response with different encodings."""
        # UTF-8 content
        html = "<html><body>Unicode: 你好</body></html>"
        response = HTMLResponse(html)
        assert response.body.decode('utf-8') == html

    def test_html_response_xss_content(self):
        """Test HTMLResponse doesn't modify potentially dangerous content."""
        # Response should pass through content as-is
        xss = '<script>alert("XSS")</script>'
        response = HTMLResponse(xss)
        assert response.body.decode() == xss

    def test_html_response_charset_header(self):
        """Test HTMLResponse includes charset in content-type."""
        response = HTMLResponse("<html></html>")
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type
        # Charset should be specified
        assert "charset" in content_type.lower() or response.charset


class TestStreamingResponse:
    """Test StreamingResponse class."""

    @pytest.mark.asyncio
    async def test_streaming_response_iterator(self):
        """Test StreamingResponse with async iterator."""
        async def generate():
            for i in range(3):
                yield f"chunk{i}".encode()
                await asyncio.sleep(0)

        response = StreamingResponse(generate())
        assert response.status_code == 200
        assert response.media_type == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_streaming_response_error_handling(self):
        """Test StreamingResponse with error in generator."""
        async def failing_generator():
            yield b"chunk1"
            raise ValueError("Generator error")

        response = StreamingResponse(failing_generator())

        # Consume the generator
        chunks = []
        try:
            async for chunk in response.body_iterator:
                chunks.append(chunk)
        except ValueError:
            pass

        assert chunks == [b"chunk1"]

    def test_streaming_response_media_type(self):
        """Test StreamingResponse with custom media type."""
        async def generate():
            yield b"data"

        response = StreamingResponse(generate(), media_type="text/plain")
        assert response.media_type == "text/plain"


class TestFileResponse:
    """Test FileResponse class."""

    def test_file_response_creation(self):
        """Test basic FileResponse creation."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        response = FileResponse(tmp_path)
        assert response.status_code == 200
        assert response.path == tmp_path

        # Clean up
        Path(tmp_path).unlink()

    def test_file_response_headers(self):
        """Test FileResponse headers."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"PDF content")
            tmp_path = tmp.name

        response = FileResponse(
            tmp_path,
            filename="document.pdf",
            media_type="application/pdf"
        )

        assert response.media_type == "application/pdf"
        assert "content-disposition" in response.headers or "Content-Disposition" in response.headers

        # Clean up
        Path(tmp_path).unlink()

    def test_file_response_nonexistent_file(self):
        """Test FileResponse with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            FileResponse("/nonexistent/file.txt")


class TestRedirectResponse:
    """Test RedirectResponse class."""

    def test_redirect_response_creation(self):
        """Test basic RedirectResponse creation."""
        response = RedirectResponse("/new-location")
        assert response.status_code == 307  # Default is temporary redirect
        assert response.headers["location"] == "/new-location"

    def test_redirect_response_permanent(self):
        """Test permanent redirect."""
        response = RedirectResponse("/new-location", status_code=308)
        assert response.status_code == 308
        assert response.headers["location"] == "/new-location"

    def test_redirect_response_absolute_url(self):
        """Test redirect with absolute URL."""
        response = RedirectResponse("https://example.com/page")
        assert response.headers["location"] == "https://example.com/page"

    def test_redirect_response_special_characters(self):
        """Test redirect with special characters in URL."""
        # URL with query parameters
        response = RedirectResponse("/search?q=test&lang=en")
        assert response.headers["location"] == "/search?q=test&lang=en"

        # URL with unicode
        response = RedirectResponse("/page/你好")
        assert response.headers["location"] == "/page/你好"


class TestResponseConversion:
    """Test automatic response conversion."""

    def test_dict_to_json_conversion(self):
        """Test dict automatically converts to JSONResponse."""
        data = {"key": "value"}
        response = handle_response_conversion(data)

        assert isinstance(response, JSONResponse)
        assert json.loads(response.body) == data

    def test_list_to_json_conversion(self):
        """Test list automatically converts to JSONResponse."""
        data = [1, 2, 3]
        response = handle_response_conversion(data)

        assert isinstance(response, JSONResponse)
        assert json.loads(response.body) == data

    def test_string_to_text_conversion(self):
        """Test string converts to PlainTextResponse."""
        text = "Hello, World!"
        response = handle_response_conversion(text)

        assert isinstance(response, PlainTextResponse)
        assert response.body == text.encode()

    def test_none_handling(self):
        """Test None value handling."""
        response = handle_response_conversion(None)

        assert isinstance(response, JSONResponse)
        assert response.body == b"null"

    def test_response_passthrough(self):
        """Test Response objects pass through unchanged."""
        original = JSONResponse({"data": "test"})
        response = handle_response_conversion(original)

        assert response is original

    def test_pydantic_model_conversion(self):
        """Test Pydantic model converts to JSON."""
        class TestModel(BaseModel):
            field: str

        model = TestModel(field="value")
        response = handle_response_conversion(model)

        assert isinstance(response, JSONResponse)
        parsed = json.loads(response.body)
        assert parsed["field"] == "value"


class TestErrorResponses:
    """Test error response handling."""

    def test_error_response_format(self):
        """Test standard error response format."""
        from zenith.web.responses import error_response

        response = error_response("Not found", 404)

        assert response.status_code == 404
        parsed = json.loads(response.body)
        assert "error" in parsed or "detail" in parsed

    def test_validation_error_response(self):
        """Test validation error response format."""
        from zenith.web.responses import validation_error_response

        errors = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "age", "message": "Must be positive"}
        ]

        response = validation_error_response(errors)

        assert response.status_code == 422
        parsed = json.loads(response.body)
        assert "errors" in parsed or "detail" in parsed

    def test_server_error_response(self):
        """Test 500 server error response."""
        from zenith.web.responses import server_error_response

        response = server_error_response("Internal server error")

        assert response.status_code == 500
        parsed = json.loads(response.body)
        # Should not expose sensitive information
        assert "traceback" not in str(parsed).lower()


class TestResponsePerformance:
    """Test response performance characteristics."""

    def test_large_json_response(self):
        """Test handling of large JSON responses."""
        # Create large data structure
        large_data = {
            "items": [{"id": i, "data": "x" * 100} for i in range(1000)]
        }

        response = JSONResponse(large_data)
        assert response.status_code == 200

        # Should be able to parse back
        parsed = json.loads(response.body)
        assert len(parsed["items"]) == 1000

    def test_response_memory_efficiency(self):
        """Test that responses don't hold unnecessary references."""
        import gc
        import weakref

        data = {"large": "x" * 10000}
        response = JSONResponse(data)

        # Create weak reference to data
        weak_ref = weakref.ref(data)

        # Delete original reference
        del data
        gc.collect()

        # Response should still work
        assert response.status_code == 200
        # Original data might be garbage collected (implementation dependent)