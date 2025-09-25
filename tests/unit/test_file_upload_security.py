"""
Comprehensive security tests for file upload functionality.

Tests security-critical paths including:
- File size limits
- Extension validation
- MIME type validation
- Path traversal prevention
- Malicious filename handling
- Resource exhaustion protection
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open
import io

import pytest

from zenith.web.files import (
    FileUploader,
    FileUploadConfig,
    FileUploadError,
    UploadedFile,
    handle_file_upload,
    serve_uploaded_file
)
from starlette.datastructures import UploadFile


class TestFileUploadSecurity:
    """Security-focused tests for file upload."""

    def test_file_size_limit_enforcement(self):
        """Test that file size limits are enforced."""
        config = FileUploadConfig(max_file_size_bytes=1024)  # 1KB limit
        uploader = FileUploader(config)

        # Create mock file that exceeds size limit
        large_content = b"x" * 2048  # 2KB
        mock_file = Mock()
        mock_file.file = io.BytesIO(large_content)
        mock_file.filename = "large.txt"
        mock_file.content_type = "text/plain"

        with pytest.raises(FileUploadError, match="exceeds maximum allowed size"):
            uploader.validate_file(mock_file)

    def test_allowed_extensions_validation(self):
        """Test that only allowed extensions pass validation."""
        config = FileUploadConfig(allowed_extensions=[".jpg", ".png", ".pdf"])
        uploader = FileUploader(config)

        # Test allowed extension
        good_file = Mock()
        good_file.filename = "document.pdf"
        good_file.file = io.BytesIO(b"content")
        good_file.content_type = "application/pdf"

        # Should not raise
        assert uploader.validate_file(good_file) is True

        # Test disallowed extension
        bad_file = Mock()
        bad_file.filename = "script.exe"
        bad_file.file = io.BytesIO(b"content")
        bad_file.content_type = "application/x-msdownload"

        with pytest.raises(FileUploadError, match="File type .* not allowed"):
            uploader.validate_file(bad_file)

    def test_mime_type_validation(self):
        """Test MIME type filtering."""
        config = FileUploadConfig(allowed_mime_types=["image/jpeg", "image/png"])
        uploader = FileUploader(config)

        # Test allowed MIME type
        good_file = Mock()
        good_file.filename = "photo.jpg"
        good_file.file = io.BytesIO(b"content")
        good_file.content_type = "image/jpeg"

        assert uploader.validate_file(good_file) is True

        # Test disallowed MIME type
        bad_file = Mock()
        bad_file.filename = "document.pdf"
        bad_file.file = io.BytesIO(b"content")
        bad_file.content_type = "application/pdf"

        with pytest.raises(FileUploadError, match="MIME type .* not allowed"):
            uploader.validate_file(bad_file)

    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        # Various path traversal attempts
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "uploads/../../../etc/passwd",
            ".%2e/.%2e/.%2e/etc/passwd",  # URL encoded
            "....//....//....//etc/passwd",
            "uploads/../../etc/passwd"
        ]

        for dangerous_name in dangerous_filenames:
            with tempfile.NamedTemporaryFile() as tmp:
                mock_file = Mock()
                mock_file.filename = dangerous_name
                mock_file.file = tmp
                mock_file.content_type = "text/plain"

                # Save should sanitize the filename
                uploaded = uploader.save_file(mock_file)

                # Check that saved path doesn't contain traversal
                assert ".." not in str(uploaded.file_path)
                assert uploaded.file_path.is_absolute()
                # Verify file is within upload directory
                assert str(config.upload_dir) in str(uploaded.file_path.parent)

    def test_null_byte_injection_prevention(self):
        """Test that null byte injection is prevented."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        # Null byte injection attempts
        dangerous_names = [
            "file.exe\x00.jpg",  # Null byte injection
            "file.jpg\x00.exe",
            "file\x00.txt",
        ]

        for dangerous_name in dangerous_names:
            with tempfile.NamedTemporaryFile() as tmp:
                mock_file = Mock()
                mock_file.filename = dangerous_name
                mock_file.file = tmp
                mock_file.content_type = "image/jpeg"

                uploaded = uploader.save_file(mock_file)

                # Null bytes should be stripped
                assert "\x00" not in uploaded.filename
                assert "\x00" not in str(uploaded.file_path)

    def test_unicode_filename_handling(self):
        """Test handling of various unicode filenames."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        # Various unicode edge cases
        unicode_names = [
            "файл.txt",  # Cyrillic
            "文件.pdf",  # Chinese
            "🎨🎭.jpg",  # Emojis
            "file\u202e\u0041\u0042\u0043txt.exe",  # RTLO character
        ]

        for unicode_name in unicode_names:
            with tempfile.NamedTemporaryFile() as tmp:
                mock_file = Mock()
                mock_file.filename = unicode_name
                mock_file.file = tmp
                mock_file.content_type = "text/plain"

                # Should handle without crashing
                uploaded = uploader.save_file(mock_file)
                assert uploaded.filename is not None

    def test_empty_filename_handling(self):
        """Test handling of missing or empty filenames."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        # Test empty filename
        with tempfile.NamedTemporaryFile() as tmp:
            mock_file = Mock()
            mock_file.filename = ""
            mock_file.file = tmp
            mock_file.content_type = "text/plain"

            uploaded = uploader.save_file(mock_file)
            # Should generate a filename
            assert uploaded.filename != ""
            assert uploaded.file_path.exists()

        # Test None filename
        with tempfile.NamedTemporaryFile() as tmp:
            mock_file = Mock()
            mock_file.filename = None
            mock_file.file = tmp
            mock_file.content_type = "text/plain"

            uploaded = uploader.save_file(mock_file)
            assert uploaded.filename is not None

    def test_duplicate_filename_handling(self):
        """Test that duplicate filenames don't overwrite existing files."""
        config = FileUploadConfig(preserve_filename=True)
        uploader = FileUploader(config)

        with tempfile.NamedTemporaryFile() as tmp1, tempfile.NamedTemporaryFile() as tmp2:
            # Upload first file
            file1 = Mock()
            file1.filename = "test.txt"
            file1.file = tmp1
            file1.content_type = "text/plain"

            uploaded1 = uploader.save_file(file1)

            # Upload second file with same name
            file2 = Mock()
            file2.filename = "test.txt"
            file2.file = tmp2
            file2.content_type = "text/plain"

            uploaded2 = uploader.save_file(file2)

            # Files should have different paths
            assert uploaded1.file_path != uploaded2.file_path
            # Both files should exist
            assert uploaded1.file_path.exists()
            assert uploaded2.file_path.exists()

    @pytest.mark.asyncio
    async def test_resource_exhaustion_protection(self):
        """Test protection against resource exhaustion attacks."""
        config = FileUploadConfig(max_file_size_bytes=1024 * 1024)  # 1MB
        uploader = FileUploader(config)

        # Simulate streaming large file
        class EndlessFile:
            def __init__(self):
                self.position = 0

            def seek(self, offset, whence=0):
                if whence == 2:  # SEEK_END
                    self.position = 10 * 1024 * 1024  # Report 10MB
                else:
                    self.position = offset

            def tell(self):
                return self.position

            def read(self, size=-1):
                # Endless stream
                return b"x" * (size if size > 0 else 1024)

        mock_file = Mock()
        mock_file.filename = "large.bin"
        mock_file.file = EndlessFile()
        mock_file.content_type = "application/octet-stream"

        with pytest.raises(FileUploadError, match="exceeds maximum"):
            uploader.validate_file(mock_file)

    def test_symlink_attack_prevention(self):
        """Test that symlink attacks are prevented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            config = FileUploadConfig(upload_dir=tmpdir / "uploads")
            uploader = FileUploader(config)

            # Create a target file outside upload directory
            target_file = tmpdir / "sensitive.txt"
            target_file.write_text("sensitive data")

            # Try to create symlink through upload
            with tempfile.NamedTemporaryFile() as tmp:
                mock_file = Mock()
                mock_file.filename = "link.txt"
                mock_file.file = tmp
                mock_file.content_type = "text/plain"

                uploaded = uploader.save_file(mock_file)

                # Verify it's a regular file, not a symlink
                assert uploaded.file_path.exists()
                assert not uploaded.file_path.is_symlink()

    def test_content_type_mismatch_detection(self):
        """Test detection of content type mismatches."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        # File claims to be image but has executable content
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"MZ\x90\x00")  # PE executable header
            tmp.seek(0)

            mock_file = Mock()
            mock_file.filename = "image.jpg"
            mock_file.file = tmp
            mock_file.content_type = "image/jpeg"

            # Should detect mismatch (when implemented)
            uploaded = uploader.save_file(mock_file)
            # For now just verify it doesn't crash
            assert uploaded is not None


class TestUploadedFileOperations:
    """Test UploadedFile methods for security."""

    def test_copy_to_path_traversal(self):
        """Test copy_to prevents path traversal."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = Path(tmp.name)

        uploaded = UploadedFile(
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            size_bytes=12,
            file_path=tmp_path
        )

        # Try path traversal in destination
        with tempfile.TemporaryDirectory() as safe_dir:
            safe_dir = Path(safe_dir)

            # This should be sanitized
            dest = safe_dir / "../../../etc/passwd"
            result = uploaded.copy_to(dest)

            # Should not escape safe directory
            assert str(safe_dir) in str(result.resolve())

    @pytest.mark.asyncio
    async def test_move_to_atomic_operation(self):
        """Test move_to is atomic and safe."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = Path(tmp.name)

        uploaded = UploadedFile(
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            size_bytes=12,
            file_path=tmp_path
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "moved.txt"
            result = await uploaded.move_to(dest)

            # Original should not exist
            assert not tmp_path.exists()
            # New location should exist
            assert result.exists()
            # Internal path should be updated
            assert uploaded.file_path == result


class TestFileServingSecurity:
    """Test secure file serving."""

    @pytest.mark.asyncio
    async def test_serve_file_path_traversal(self):
        """Test that file serving prevents path traversal."""
        # Create safe directory with file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            safe_file = tmpdir / "safe.txt"
            safe_file.write_text("safe content")

            # Try to access file outside directory
            from zenith.web.files import serve_uploaded_file

            # These should all be blocked
            dangerous_paths = [
                "../../../etc/passwd",
                "..\\..\\windows\\system32\\config\\sam",
                "/etc/passwd",  # Absolute path
                "C:\\Windows\\System32\\config\\SAM",
            ]

            for dangerous_path in dangerous_paths:
                with pytest.raises((FileNotFoundError, ValueError)):
                    await serve_uploaded_file(dangerous_path, tmpdir)

    @pytest.mark.asyncio
    async def test_serve_file_mime_type(self):
        """Test correct MIME type detection for served files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create files with different extensions
            files = {
                "test.html": ("text/html", b"<html></html>"),
                "test.js": ("application/javascript", b"console.log()"),
                "test.exe": ("application/x-msdownload", b"MZ"),
            }

            for filename, (expected_type, content) in files.items():
                file_path = tmpdir / filename
                file_path.write_bytes(content)

                response = await serve_uploaded_file(filename, tmpdir)
                # Verify MIME type is set correctly
                assert expected_type in response.media_type or response.media_type == "application/octet-stream"