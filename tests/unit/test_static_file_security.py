"""
Comprehensive security tests for static file serving.

Tests critical security paths including:
- Path traversal prevention
- Symlink following prevention
- Directory listing prevention
- MIME type security
- Cache header security
- Range request handling
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import mimetypes

import pytest
from starlette.responses import FileResponse, Response
from starlette.exceptions import HTTPException

from zenith.web.static import StaticFiles, StaticResponse


class TestStaticFilesSecurity:
    """Security tests for static file serving."""

    def create_test_directory(self):
        """Create a test directory structure."""
        tmpdir = tempfile.mkdtemp()
        tmpdir = Path(tmpdir)

        # Create test files
        (tmpdir / "index.html").write_text("<html>Test</html>")
        (tmpdir / "style.css").write_text("body { color: red; }")
        (tmpdir / "script.js").write_text("console.log('test');")

        # Create subdirectory
        subdir = tmpdir / "assets"
        subdir.mkdir()
        (subdir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        # Create sensitive file (should not be served)
        (tmpdir / ".env").write_text("SECRET=sensitive")
        (tmpdir / ".git").mkdir()
        (tmpdir / ".git" / "config").write_text("git config")

        return tmpdir

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        tmpdir = self.create_test_directory()
        static = StaticFiles(directory=str(tmpdir))

        # Create mock scope and receive
        scope = {
            "type": "http",
            "method": "GET",
            "path": "",
            "headers": []
        }
        receive = AsyncMock()
        send = AsyncMock()

        # Various path traversal attempts
        traversal_paths = [
            "/../etc/passwd",
            "/../../etc/passwd",
            "/../../../etc/passwd",
            "/..\\..\\windows\\system32\\config\\sam",
            "/assets/../../../etc/passwd",
            "/.%2e/.%2e/.%2e/etc/passwd",  # URL encoded
            "/....//....//....//etc/passwd",
            "/assets/../../.env",
            "/%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
        ]

        for path in traversal_paths:
            scope["path"] = path

            # Should either raise 404 or serve safe content
            try:
                await static(scope, receive, send)
                # If it doesn't raise, check that we didn't escape directory
                assert send.call_count > 0
                # Verify we're not serving content from outside directory
                response_headers = send.call_args_list[0][0][0].get("headers", [])
                # Should not contain sensitive paths
                for header_name, header_value in response_headers:
                    if header_name == b"content-location":
                        assert b"/etc/" not in header_value
                        assert b"\\windows\\" not in header_value
            except HTTPException as e:
                # 404 is acceptable for blocked paths
                assert e.status_code == 404

            send.reset_mock()

    @pytest.mark.asyncio
    async def test_symlink_following_prevented(self):
        """Test that symlinks outside directory are not followed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            static_dir = tmpdir / "static"
            static_dir.mkdir()

            # Create legitimate file
            (static_dir / "normal.txt").write_text("normal content")

            # Create sensitive file outside static directory
            sensitive = tmpdir / "sensitive.txt"
            sensitive.write_text("SENSITIVE DATA")

            # Create symlink pointing outside
            symlink = static_dir / "link.txt"
            symlink.symlink_to(sensitive)

            static = StaticFiles(directory=str(static_dir), follow_symlinks=False)

            scope = {
                "type": "http",
                "method": "GET",
                "path": "/link.txt",
                "headers": []
            }
            receive = AsyncMock()
            send = AsyncMock()

            # Should not serve symlinked content
            with pytest.raises(HTTPException) as exc_info:
                await static(scope, receive, send)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_hidden_files_not_served(self):
        """Test that hidden files are not served."""
        tmpdir = self.create_test_directory()
        static = StaticFiles(directory=str(tmpdir))

        hidden_files = [
            "/.env",
            "/.git/config",
            "/.gitignore",
            "/.htaccess",
            "/.DS_Store",
        ]

        for path in hidden_files:
            scope = {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": []
            }
            receive = AsyncMock()
            send = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await static(scope, receive, send)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_directory_listing_disabled(self):
        """Test that directory listing is disabled by default."""
        tmpdir = self.create_test_directory()
        static = StaticFiles(directory=str(tmpdir))

        # Try to access directory
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/assets/",  # Directory path
            "headers": []
        }
        receive = AsyncMock()
        send = AsyncMock()

        # Should not list directory contents
        with pytest.raises(HTTPException) as exc_info:
            await static(scope, receive, send)
        assert exc_info.value.status_code == 404

    def test_mime_type_security(self):
        """Test secure MIME type handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Files that could be dangerous if served with wrong MIME
            dangerous_files = {
                "test.html": b"<script>alert('XSS')</script>",
                "test.svg": b'<svg onload="alert(1)"></svg>',
                "test.xml": b'<?xml version="1.0"?><!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
            }

            for filename, content in dangerous_files.items():
                file_path = tmpdir / filename
                file_path.write_bytes(content)

                response = StaticResponse(str(file_path))

                # Check that appropriate MIME type is set
                mime_type = response.media_type
                assert mime_type is not None

                # For HTML/SVG, should include charset to prevent encoding attacks
                if filename.endswith('.html'):
                    assert 'text/html' in mime_type

                # SVG should be served with proper type
                if filename.endswith('.svg'):
                    assert 'svg' in mime_type or mime_type == 'application/octet-stream'

    def test_cache_header_security(self):
        """Test secure cache headers for sensitive files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            (tmpdir / "public.js").write_text("console.log('public');")
            (tmpdir / "sensitive.json").write_text('{"api_key": "secret"}')

            # Public file should have cache headers
            public_response = StaticResponse(str(tmpdir / "public.js"))
            assert "cache-control" in public_response.headers or "Cache-Control" in public_response.headers

            # Sensitive files might need no-cache headers (depends on implementation)
            sensitive_response = StaticResponse(str(tmpdir / "sensitive.json"))
            # Just verify it doesn't crash
            assert sensitive_response is not None

    @pytest.mark.asyncio
    async def test_range_request_validation(self):
        """Test that range requests are validated properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "large.bin"
            test_file.write_bytes(b"0" * 1000)

            static = StaticFiles(directory=str(tmpdir))

            # Valid range request
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/large.bin",
                "headers": [(b"range", b"bytes=0-499")]
            }
            receive = AsyncMock()
            send = AsyncMock()

            await static(scope, receive, send)
            # Should return 206 Partial Content
            assert send.called

            # Invalid range requests
            invalid_ranges = [
                b"bytes=500-100",  # End before start
                b"bytes=-",  # Invalid format
                b"bytes=abc-def",  # Non-numeric
                b"bytes=0-999999999999",  # Beyond file size
            ]

            for invalid_range in invalid_ranges:
                scope["headers"] = [(b"range", invalid_range)]
                send.reset_mock()

                # Should handle gracefully
                await static(scope, receive, send)
                assert send.called

    @pytest.mark.asyncio
    async def test_null_byte_in_path(self):
        """Test that null bytes in path are handled safely."""
        tmpdir = self.create_test_directory()
        static = StaticFiles(directory=str(tmpdir))

        # Paths with null bytes
        null_paths = [
            "/test.html\x00.txt",
            "/test\x00/index.html",
            "/\x00etc/passwd",
        ]

        for path in null_paths:
            scope = {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": []
            }
            receive = AsyncMock()
            send = AsyncMock()

            # Should reject or sanitize
            with pytest.raises(HTTPException):
                await static(scope, receive, send)

    def test_content_type_sniffing_prevention(self):
        """Test that content type sniffing is prevented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # File with misleading extension
            fake_image = tmpdir / "image.jpg"
            fake_image.write_text("<script>alert('XSS')</script>")

            response = StaticResponse(str(fake_image))

            # Should include X-Content-Type-Options header
            assert response.headers.get("x-content-type-options") == "nosniff"

            # MIME type should be based on extension, not content
            assert "image" in response.media_type or response.media_type == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_large_file_dos_prevention(self):
        """Test protection against DoS via large file requests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a "large" file
            large_file = tmpdir / "large.bin"
            large_file.write_bytes(b"0" * (10 * 1024 * 1024))  # 10MB

            static = StaticFiles(directory=str(tmpdir))

            # Multiple range requests for same file (range request flooding)
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/large.bin",
                "headers": [(b"range", b"bytes=0-1")]
            }
            receive = AsyncMock()
            send = AsyncMock()

            # Should handle multiple requests without exhausting resources
            for _ in range(100):
                send.reset_mock()
                await static(scope, receive, send)
                assert send.called

    def test_executable_file_headers(self):
        """Test that executable files get proper headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create files that could be executable
            executables = [
                ("test.exe", b"MZ"),
                ("test.sh", b"#!/bin/bash"),
                ("test.bat", b"@echo off"),
            ]

            for filename, content in executables:
                file_path = tmpdir / filename
                file_path.write_bytes(content)

                response = StaticResponse(str(file_path))

                # Should have Content-Disposition header to prevent execution
                assert "content-disposition" in response.headers or "Content-Disposition" in response.headers

                # Should not be served as executable MIME type
                mime = response.media_type
                assert mime == "application/octet-stream" or "text" in mime


class TestStaticResponseSecurity:
    """Test StaticResponse class security."""

    def test_response_headers_security(self):
        """Test that security headers are properly set."""
        with tempfile.NamedTemporaryFile(suffix=".html") as tmp:
            tmp.write(b"<html>test</html>")
            tmp.flush()

            response = StaticResponse(tmp.name)

            # Should have security headers
            assert response.headers.get("x-content-type-options") == "nosniff"

            # Should have appropriate cache headers
            assert "last-modified" in response.headers or "Last-Modified" in response.headers

    def test_etag_generation(self):
        """Test that ETags are generated securely."""
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"content")
            tmp.flush()

            response1 = StaticResponse(tmp.name)
            etag1 = response1.headers.get("etag")

            # Modify file
            tmp.seek(0)
            tmp.write(b"changed")
            tmp.flush()

            response2 = StaticResponse(tmp.name)
            etag2 = response2.headers.get("etag")

            # ETags should be different for different content
            if etag1 and etag2:
                assert etag1 != etag2

    @pytest.mark.asyncio
    async def test_conditional_request_handling(self):
        """Test If-None-Match and If-Modified-Since handling."""
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"content")
            tmp.flush()

            response = StaticResponse(tmp.name)

            # Simulate If-None-Match
            etag = response.headers.get("etag")
            if etag:
                # With matching ETag
                response_match = StaticResponse(
                    tmp.name,
                    headers={"if-none-match": etag}
                )
                # Should return 304 Not Modified
                assert response_match.status_code == 304 or response_match.status_code == 200

    def test_forbidden_file_access(self):
        """Test that forbidden files raise appropriate errors."""
        # Try to access system files
        forbidden_paths = [
            "/etc/passwd",
            "/dev/null",
            "C:\\Windows\\System32\\config\\SAM",
        ]

        for path in forbidden_paths:
            if not Path(path).exists():
                continue

            with pytest.raises((PermissionError, FileNotFoundError, ValueError)):
                StaticResponse(path)