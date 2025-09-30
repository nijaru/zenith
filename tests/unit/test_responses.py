"""
Comprehensive tests for response handling.

Tests all response utilities including OptimizedJSONResponse, file responses,
pagination, cookies, and content negotiation.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest
from starlette.responses import Response

from zenith.web.responses import (
    OptimizedJSONResponse,
    accepted_response,
    created_response,
    delete_cookie_response,
    error_response,
    file_download_response,
    html_response,
    inline_file_response,
    json_response,
    negotiate_response,
    no_content_response,
    paginated_response,
    permanent_redirect,
    redirect_response,
    set_cookie_response,
    streaming_response,
    success_response,
)


class TestOptimizedJSONResponse:
    """Test OptimizedJSONResponse with and without orjson."""

    def test_json_response_basic(self):
        """Test basic JSON response creation."""
        response = json_response({"message": "test"})
        assert response.status_code == 200
        assert response.media_type == "application/json"

    def test_json_response_with_status(self):
        """Test JSON response with custom status code."""
        response = json_response({"error": "not found"}, status_code=404)
        assert response.status_code == 404

    def test_json_response_with_headers(self):
        """Test JSON response with custom headers."""
        headers = {"X-Custom-Header": "value"}
        response = json_response({"data": "test"}, headers=headers)
        assert response.headers.get("x-custom-header") == "value"

    @patch("zenith.web.responses.HAS_ORJSON", False)
    def test_json_response_without_orjson(self):
        """Test JSON response falls back when orjson not available."""
        response = OptimizedJSONResponse({"message": "test"})
        assert response.status_code == 200

    def test_json_serialization_datetime(self):
        """Test JSON serialization of datetime objects."""
        now = datetime.now(UTC)
        today = date.today()

        response = OptimizedJSONResponse({"timestamp": now, "date": today})

        # Response should serialize successfully
        assert response.status_code == 200

    def test_json_serialization_decimal(self):
        """Test JSON serialization of Decimal objects."""
        response = OptimizedJSONResponse(
            {"price": Decimal("19.99"), "quantity": Decimal("100")}
        )

        assert response.status_code == 200

    def test_json_serialization_uuid(self):
        """Test JSON serialization of UUID objects."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")

        response = OptimizedJSONResponse({"id": test_uuid})

        assert response.status_code == 200

    def test_json_serialization_path(self):
        """Test JSON serialization of Path objects."""
        response = OptimizedJSONResponse(
            {"file_path": Path("/tmp/test.txt"), "directory": Path("/home/user")}
        )

        assert response.status_code == 200

    def test_json_serialization_pydantic_model(self):
        """Test JSON serialization of Pydantic models."""
        # Mock a Pydantic model
        mock_model = Mock()
        mock_model.model_dump.return_value = {"id": 1, "name": "test"}

        response = OptimizedJSONResponse({"model": mock_model})
        assert response.status_code == 200
        mock_model.model_dump.assert_called()

    def test_json_serialization_nested_objects(self):
        """Test JSON serialization of nested complex objects."""
        response = OptimizedJSONResponse(
            {
                "user": {
                    "id": UUID("12345678-1234-5678-1234-567812345678"),
                    "created": datetime.now(UTC),
                    "balance": Decimal("100.50"),
                    "profile_path": Path("/profiles/user1"),
                },
                "items": [
                    {"price": Decimal("19.99"), "date": date.today()},
                    {"price": Decimal("29.99"), "date": date.today()},
                ],
            }
        )

        assert response.status_code == 200

    def test_json_serialization_unsupported_type(self):
        """Test JSON serialization handles unsupported types gracefully."""

        # Create an object that's not serializable
        class CustomObject:
            pass

        # Should handle the error gracefully
        with pytest.raises(TypeError, match="not JSON serializable"):
            OptimizedJSONResponse({"obj": CustomObject()})


class TestResponseHelpers:
    """Test response helper functions."""

    def test_success_response(self):
        """Test standardized success response."""
        response = success_response(data={"user_id": 1})
        assert response.status_code == 200

    def test_success_response_custom_message(self):
        """Test success response with custom message."""
        response = success_response(message="User created", status_code=201)
        assert response.status_code == 201

    def test_error_response(self):
        """Test standardized error response."""
        response = error_response("Not found", status_code=404)
        assert response.status_code == 404

    def test_error_response_with_code(self):
        """Test error response with error code."""
        response = error_response(
            "Invalid input", status_code=400, error_code="VALIDATION_ERROR"
        )
        assert response.status_code == 400

    def test_error_response_with_details(self):
        """Test error response with additional details."""
        details = {"field": "email", "reason": "invalid format"}
        response = error_response("Validation failed", status_code=422, details=details)
        assert response.status_code == 422

    def test_no_content_response(self):
        """Test 204 No Content response."""
        response = no_content_response()
        assert response.status_code == 204

    def test_created_response(self):
        """Test 201 Created response."""
        response = created_response(data={"id": 123})
        assert response.status_code == 201

    def test_created_response_with_location(self):
        """Test 201 Created response with location header."""
        response = created_response(data={"id": 456}, location="/api/users/456")
        assert response.status_code == 201

    def test_accepted_response(self):
        """Test 202 Accepted response."""
        response = accepted_response()
        assert response.status_code == 202

    def test_accepted_response_custom_message(self):
        """Test 202 Accepted with custom message."""
        response = accepted_response("Job queued for processing")
        assert response.status_code == 202


class TestRedirectResponses:
    """Test redirect response functions."""

    def test_redirect_response(self):
        """Test basic redirect response."""
        response = redirect_response("/new-location")
        assert response.status_code == 302
        assert response.headers["location"] == "/new-location"

    def test_redirect_response_custom_status(self):
        """Test redirect with custom status code."""
        response = redirect_response("/login", status_code=303)
        assert response.status_code == 303

    def test_permanent_redirect(self):
        """Test permanent redirect (301)."""
        response = permanent_redirect("/new-url")
        assert response.status_code == 301
        assert response.headers["location"] == "/new-url"


class TestFileResponses:
    """Test file response functions."""

    def test_file_download_response(self):
        """Test file download response."""
        with patch("pathlib.Path.exists", return_value=True):
            response = file_download_response("/tmp/test.pdf")
            assert "attachment" in response.headers.get("content-disposition", "")

    def test_file_download_custom_filename(self):
        """Test file download with custom filename."""
        with patch("pathlib.Path.exists", return_value=True):
            response = file_download_response("/tmp/uuid123.pdf", filename="report.pdf")
            assert 'filename="report.pdf"' in response.headers.get(
                "content-disposition", ""
            )

    def test_file_download_not_found(self):
        """Test file download with non-existent file."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                file_download_response("/tmp/missing.pdf")

    def test_inline_file_response(self):
        """Test inline file response."""
        with patch("pathlib.Path.exists", return_value=True):
            response = inline_file_response("/tmp/image.jpg")
            assert response.headers.get("content-disposition") == "inline"

    def test_inline_file_not_found(self):
        """Test inline file with non-existent file."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                inline_file_response("/tmp/missing.jpg")


class TestStreamingResponse:
    """Test streaming response function."""

    def test_streaming_response(self):
        """Test basic streaming response."""

        def generator():
            yield b"chunk1"
            yield b"chunk2"

        response = streaming_response(generator())
        assert response.status_code == 200
        assert response.media_type == "text/plain"

    def test_streaming_response_custom_media_type(self):
        """Test streaming with custom media type."""

        def generator():
            yield b"data"

        response = streaming_response(
            generator(), media_type="application/octet-stream"
        )
        assert response.media_type == "application/octet-stream"


class TestHTMLResponse:
    """Test HTML response function."""

    def test_html_response(self):
        """Test basic HTML response."""
        response = html_response("<h1>Hello</h1>")
        assert response.status_code == 200
        assert response.media_type == "text/html"

    def test_html_response_custom_status(self):
        """Test HTML response with custom status."""
        response = html_response("<p>Not Found</p>", status_code=404)
        assert response.status_code == 404


class TestPaginationResponse:
    """Test paginated response function."""

    def test_paginated_response_first_page(self):
        """Test paginated response for first page."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = paginated_response(data=data, page=1, page_size=10, total_count=25)
        assert response.status_code == 200

    def test_paginated_response_middle_page(self):
        """Test paginated response for middle page."""
        data = [{"id": 11}, {"id": 12}, {"id": 13}]
        response = paginated_response(
            data=data,
            page=2,
            page_size=10,
            total_count=30,
            next_page="/api/items?page=3",
            prev_page="/api/items?page=1",
        )
        assert response.status_code == 200

    def test_paginated_response_last_page(self):
        """Test paginated response for last page."""
        data = [{"id": 21}, {"id": 22}]
        response = paginated_response(data=data, page=3, page_size=10, total_count=22)
        assert response.status_code == 200


class TestCookieUtilities:
    """Test cookie utility functions."""

    def test_set_cookie_response(self):
        """Test setting a cookie on response."""
        response = Response()
        set_cookie_response(response, key="session_id", value="abc123")
        # Cookie should be set with secure defaults

    def test_set_cookie_custom_options(self):
        """Test setting cookie with custom options."""
        response = Response()
        set_cookie_response(
            response,
            key="preferences",
            value="theme=dark",
            max_age=3600,
            path="/app",
            secure=False,  # For testing only
            httponly=False,
            samesite="strict",
        )

    def test_delete_cookie_response(self):
        """Test deleting a cookie from response."""
        response = Response()
        delete_cookie_response(response, key="session_id")

    def test_delete_cookie_with_path(self):
        """Test deleting cookie with specific path."""
        response = Response()
        delete_cookie_response(response, key="app_cookie", path="/app")


class TestContentNegotiation:
    """Test content negotiation helper."""

    def test_negotiate_json_response(self):
        """Test negotiation returns JSON for JSON accept header."""
        data = {"message": "test"}
        response = negotiate_response(data, accept_header="application/json")
        assert response.media_type == "application/json"

    def test_negotiate_html_response(self):
        """Test negotiation returns HTML for HTML accept header."""
        data = {"message": "test"}
        response = negotiate_response(data, accept_header="text/html")
        assert response.media_type == "text/html"

    def test_negotiate_text_response(self):
        """Test negotiation returns text for text accept header."""
        data = {"message": "test"}
        response = negotiate_response(data, accept_header="text/plain")
        assert response.media_type == "text/plain"

    def test_negotiate_default_to_json(self):
        """Test negotiation defaults to JSON for unknown accept header."""
        data = {"message": "test"}
        response = negotiate_response(data, accept_header="application/xml")
        assert response.media_type == "application/json"

    def test_negotiate_with_string_data(self):
        """Test negotiation with string data."""
        response = negotiate_response("Hello World", accept_header="text/plain")
        assert response.media_type == "text/plain"

    def test_negotiate_with_list_data(self):
        """Test negotiation with list data."""
        data = [1, 2, 3, 4, 5]
        response = negotiate_response(data, accept_header="application/json")
        assert response.media_type == "application/json"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_json_response(self):
        """Test JSON response with empty data."""
        response = json_response({})
        assert response.status_code == 200

    def test_null_json_response(self):
        """Test JSON response with None."""
        response = json_response(None)
        assert response.status_code == 200

    def test_large_json_response(self):
        """Test JSON response with large data."""
        large_data = [{"id": i, "data": "x" * 100} for i in range(1000)]
        response = json_response(large_data)
        assert response.status_code == 200

    def test_unicode_json_response(self):
        """Test JSON response with Unicode characters."""
        response = json_response({"message": "Hello 世界 🌍", "emoji": "😀🎉🚀"})
        assert response.status_code == 200

    def test_nested_error_details(self):
        """Test error response with nested details."""
        details = {
            "validation_errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "age", "message": "Must be positive"},
            ],
            "request_id": "abc-123",
        }
        response = error_response("Validation failed", status_code=422, details=details)
        assert response.status_code == 422
