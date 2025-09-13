"""
Unit tests for web components.

Tests file uploads, health checks, static files, and response utilities.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from zenith import Auth, File, Zenith
from zenith.auth import configure_auth
from zenith.testing import TestClient
from zenith.web.files import (
    FileUploadConfig,
    FileUploader,
)
from zenith.monitoring.health import (
    HealthManager,
    HealthStatus,
    add_health_routes,
)
from zenith.web.responses import (
    error_response,
    file_download_response,
    paginated_response,
    redirect_response,
    success_response,
)
from zenith.web.static import StaticFileConfig, create_static_route


class TestFileUploads:
    """Test file upload functionality."""

    @pytest.mark.asyncio
    async def test_file_upload_basic(self):
        """Test basic file upload functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir) / "uploads"
            upload_dir.mkdir()

            config = FileUploadConfig(
                upload_dir=upload_dir,
                max_file_size_bytes=1024,  # 1KB
                allowed_extensions=[".txt", ".json"],
                preserve_filename=False,
            )

            app = Zenith(debug=True)
            configure_auth(app, secret_key="test-secret-key-that-is-long-enough")
            app.add_exception_handling(debug=True)

            @app.post("/api/upload")
            async def upload_file(
                file=File("file", config), current_user=Auth(required=True)
            ):
                # Ensure we're working with the right object
                if not hasattr(file, "size_bytes"):
                    # Debug: what did we actually get?
                    print(f"DEBUG: file type = {type(file)}, file = {file}")
                    # If it's an UploadedFile, access the right fields

                return {
                    "filename": file.filename,
                    "original": file.original_filename,
                    "size": file.size_bytes,
                    "type": file.content_type,
                    # Don't include path in response - it's not needed and causes serialization issues
                }

            async with TestClient(app) as client:
                client.set_auth_token("test@example.com", user_id=123)

                # Test successful upload
                files = {"file": ("test.txt", "Hello World!", "text/plain")}
                response = await client.post("/api/upload", files=files)

                if response.status_code != 200:
                    print(f"Response status: {response.status_code}")
                    print(f"Response body: {response.text}")

                assert response.status_code == 200
                data = response.json()
                assert data["original"] == "test.txt"
                assert data["size"] == len("Hello World!")
                assert data["type"] == "text/plain"
                assert data["filename"].endswith(".txt")
                assert data["filename"] != "test.txt"  # Should be UUID-based

    @pytest.mark.asyncio
    async def test_file_upload_validation(self):
        """Test file upload validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir) / "uploads"
            upload_dir.mkdir()

            config = FileUploadConfig(
                upload_dir=upload_dir,
                max_file_size_bytes=10,  # Very small limit
                allowed_extensions=[".txt"],
                allowed_mime_types=["text/plain"],
            )

            app = Zenith(debug=True)
            configure_auth(app, secret_key="test-secret-key-that-is-long-enough")
            app.add_exception_handling(debug=True)

            @app.post("/api/upload")
            async def upload_file(
                file=File("file", config), current_user=Auth(required=True)
            ):
                return {"success": True}

            async with TestClient(app) as client:
                client.set_auth_token("test@example.com", user_id=123)

                # Test file too large
                large_content = "x" * 100  # Exceeds 10 byte limit
                files = {"file": ("large.txt", large_content, "text/plain")}
                response = await client.post("/api/upload", files=files)
                assert (
                    response.status_code == 500
                )  # Should be caught as FileUploadError

                # Test wrong extension
                files = {"file": ("test.jpg", "fake image", "image/jpeg")}
                response = await client.post("/api/upload", files=files)
                assert (
                    response.status_code == 500
                )  # Should be caught as FileUploadError

                # Test wrong MIME type
                files = {"file": ("test.txt", "text content", "application/json")}
                response = await client.post("/api/upload", files=files)
                assert (
                    response.status_code == 500
                )  # Should be caught as FileUploadError

    def test_file_uploader_direct(self):
        """Test FileUploader class directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir) / "uploads"

            config = FileUploadConfig(
                upload_dir=upload_dir,
                max_file_size_bytes=1024,
                allowed_extensions=[".txt"],
                preserve_filename=True,
            )

            uploader = FileUploader(config)

            # Test filename generation
            safe_name = uploader.generate_filename("test file!@#$.txt")
            assert safe_name.endswith(".txt")
            assert "!" not in safe_name
            assert "@" not in safe_name

            # Test path generation
            upload_path = uploader.get_upload_path("test.txt")
            assert upload_path.name == "test.txt"
            if config.create_subdirs:
                assert str(upload_path).count("/") >= 4  # Should have date subdirs

    def test_file_upload_config(self):
        """Test file upload configuration."""
        # Test default config
        config = FileUploadConfig()
        assert config.max_file_size_bytes == 10 * 1024 * 1024  # 10MB
        assert config.allowed_extensions == []  # Allow all
        assert not config.preserve_filename
        assert config.create_subdirs

        # Test custom config
        custom_config = FileUploadConfig(
            max_file_size_bytes=5 * 1024 * 1024,
            allowed_extensions=[".jpg", ".png"],
            preserve_filename=True,
            create_subdirs=False,
        )
        assert custom_config.max_file_size_bytes == 5 * 1024 * 1024
        assert custom_config.allowed_extensions == [".jpg", ".png"]
        assert custom_config.preserve_filename
        assert not custom_config.create_subdirs


@pytest.mark.asyncio
class TestHealthChecks:
    """Test health check functionality."""

    async def test_health_manager_basic(self):
        """Test basic health manager functionality."""
        manager = HealthManager(version="1.0.0")

        # Add a simple check
        async def test_check():
            return True

        manager.add_simple_check("test", test_check, timeout_secs=1.0)

        # Run checks
        health = await manager.run_checks()

        assert health.status == HealthStatus.HEALTHY
        assert health.version == "1.0.0"
        assert len(health.checks) == 1
        assert health.checks[0].name == "test"
        assert health.checks[0].status == HealthStatus.HEALTHY
        assert health.checks[0].duration_ms is not None

    async def test_health_check_failure(self):
        """Test health check failure handling."""
        manager = HealthManager()

        # Add failing check
        async def failing_check():
            return False

        manager.add_simple_check("failing", failing_check, critical=True)

        # Run checks
        health = await manager.run_checks()

        assert health.status == HealthStatus.UNHEALTHY
        assert len(health.checks) == 1
        assert health.checks[0].status == HealthStatus.UNHEALTHY
        assert "Check failed" in health.checks[0].message

    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        manager = HealthManager()

        # Add slow check
        async def slow_check():
            await asyncio.sleep(0.2)  # 200ms
            return True

        manager.add_simple_check("slow", slow_check, timeout_secs=0.1, critical=True)

        # Run checks
        health = await manager.run_checks()

        assert health.status == HealthStatus.UNHEALTHY
        assert len(health.checks) == 1
        assert health.checks[0].status == HealthStatus.UNHEALTHY
        assert "Timeout" in health.checks[0].message

    async def test_health_check_exception(self):
        """Test health check exception handling."""
        manager = HealthManager()

        # Add check that raises exception
        async def error_check():
            raise ValueError("Test error")

        manager.add_simple_check("error", error_check, critical=False)

        # Run checks
        health = await manager.run_checks()

        # Non-critical failure should result in degraded status
        assert health.status == HealthStatus.DEGRADED
        assert health.checks[0].status == HealthStatus.UNHEALTHY
        assert "Test error" in health.checks[0].message

    async def test_health_endpoints_integration(self):
        """Test health endpoints integration."""
        app = Zenith(debug=True)

        # Set up health manager with checks
        from zenith.monitoring.health import health_manager

        health_manager.add_uptime_check(min_uptime=0.0)  # Immediate

        # Add health routes
        add_health_routes(app)

        async with TestClient(app) as client:
            # Test full health endpoint
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "checks" in data
            assert len(data["checks"]) > 0

            # Test readiness endpoint
            response = await client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

            # Test liveness endpoint
            response = await client.get("/live")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"


class TestResponseUtilities:
    """Test response utility functions."""

    def test_success_response(self):
        """Test success response generation."""
        import json

        response = success_response({"id": 123}, "User created", 201)

        assert response.status_code == 201
        body = response.body.decode()
        data = json.loads(body)
        assert data["success"]
        assert data["message"] == "User created"
        assert data["data"]["id"] == 123

    def test_error_response(self):
        """Test error response generation."""
        import json

        response = error_response(
            "Invalid input", 400, "VALIDATION_ERROR", {"field": "email"}
        )

        assert response.status_code == 400
        body = response.body.decode()
        data = json.loads(body)
        assert not data["success"]
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "Invalid input"
        assert data["details"]["field"] == "email"

    def test_paginated_response(self):
        """Test paginated response generation."""
        import json

        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = paginated_response(
            data=items,
            page=2,
            page_size=10,
            total_count=25,
            next_page="/api/items?page=3",
            prev_page="/api/items?page=1",
        )

        assert response.status_code == 200
        body = response.body.decode()
        data = json.loads(body)

        assert data["success"]
        assert len(data["data"]) == 3
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["total_pages"] == 3  # 25 items / 10 per page
        assert data["pagination"]["has_next"]
        assert data["pagination"]["has_prev"]

    def test_redirect_response(self):
        """Test redirect response generation."""
        response = redirect_response("/new-location", 302)
        assert response.status_code == 302
        assert response.headers["location"] == "/new-location"

        # Test permanent redirect
        from zenith.web.responses import permanent_redirect

        perm_response = permanent_redirect("/permanent-location")
        assert perm_response.status_code == 301
        assert perm_response.headers["location"] == "/permanent-location"

    def test_file_download_response(self):
        """Test file download response generation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test file content")
            temp_path = f.name

        try:
            response = file_download_response(temp_path, "custom-name.txt")

            assert response.status_code == 200
            assert "attachment" in response.headers["content-disposition"]
            assert "custom-name.txt" in response.headers["content-disposition"]

        finally:
            Path(temp_path).unlink()  # Cleanup

        # Test file not found
        with pytest.raises(FileNotFoundError):
            file_download_response("/nonexistent/file.txt")


class TestStaticFiles:
    """Test static file serving functionality."""

    def test_static_file_config(self):
        """Test static file configuration."""

        config = StaticFileConfig(
            directory="/static",
            max_age=3600,
            allowed_extensions=[".css", ".js"],
            allow_hidden=False,
        )

        assert config.directory == "/static"
        assert config.max_age == 3600
        assert config.allowed_extensions == [".css", ".js"]
        assert not config.allow_hidden

    def test_static_route_creation(self):
        """Test static route creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            css_file = Path(temp_dir) / "style.css"
            css_file.write_text("body { color: blue; }")

            js_file = Path(temp_dir) / "app.js"
            js_file.write_text("console.log('hello');")

            # Create static route
            route = create_static_route(
                "/static", temp_dir, max_age=3600, allowed_extensions=[".css", ".js"]
            )

            assert route.path == "/static"
            assert route.name == "static"

    def test_convenience_static_functions(self):
        """Test convenience functions for static files."""
        from zenith.web.static import serve_css_js, serve_images, serve_uploads

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test CSS/JS serving
            css_route = serve_css_js(temp_dir, "/assets")
            assert css_route.path == "/assets"
            assert css_route.name == "assets"

            # Test image serving
            img_route = serve_images(temp_dir, "/images")
            assert img_route.path == "/images"
            assert img_route.name == "images"

            # Test upload serving
            upload_route = serve_uploads(temp_dir, "/uploads")
            assert upload_route.path == "/uploads"
            assert upload_route.name == "uploads"


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
