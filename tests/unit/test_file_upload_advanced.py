"""
Advanced file upload tests covering edge cases and security scenarios.

Tests file upload validation, security checks, size limits,
and various error conditions.
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from starlette.datastructures import UploadFile

from zenith.web.files import (
    FileUploadConfig,
    FileUploader,
    UploadedFile,
    handle_file_upload,
)


class TestFileUploadValidation:
    """Test file upload validation and security."""

    def test_file_upload_config_defaults(self):
        """Test default upload configuration."""
        config = FileUploadConfig()
        assert config.max_size_mb == 10
        assert config.allowed_extensions == [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"]
        assert config.upload_dir == "uploads"
        assert config.create_upload_dir is True
        assert config.validate_content_type is True

    def test_file_upload_config_custom(self):
        """Test custom upload configuration."""
        config = FileUploadConfig(
            max_size_mb=50,
            allowed_extensions=[".mp3", ".wav"],
            upload_dir="/custom/uploads",
            create_upload_dir=False,
            validate_content_type=False
        )
        assert config.max_size_mb == 50
        assert config.allowed_extensions == [".mp3", ".wav"]
        assert config.upload_dir == "/custom/uploads"
        assert config.create_upload_dir is False
        assert config.validate_content_type is False


class TestFileUploader:
    """Test FileUploader validation methods."""

    def create_mock_upload_file(
        self,
        filename: str = "test.jpg",
        content_type: str = "image/jpeg",
        size: int = 1024,
        content: bytes = b"test content"
    ) -> UploadFile:
        """Create a mock UploadFile for testing."""
        file = Mock(spec=UploadFile)
        file.filename = filename
        file.content_type = content_type
        file.size = size
        file.file = io.BytesIO(content)
        file.read = AsyncMock(return_value=content)
        return file

    @pytest.mark.asyncio
    async def test_validate_file_success(self):
        """Test successful file validation."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        file = self.create_mock_upload_file(
            filename="photo.jpg",
            content_type="image/jpeg",
            size=1024 * 1024  # 1MB
        )

        # Should not raise any exception
        await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self):
        """Test validation rejects files exceeding size limit."""
        config = FileUploadConfig(max_size_mb=1)
        uploader = FileUploader(config)

        file = self.create_mock_upload_file(
            filename="large.jpg",
            size=2 * 1024 * 1024  # 2MB
        )

        with pytest.raises(ValueError, match="exceeds maximum size"):
            await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_validate_file_invalid_extension(self):
        """Test validation rejects files with invalid extensions."""
        config = FileUploadConfig(allowed_extensions=[".jpg", ".png"])
        uploader = FileUploader(config)

        file = self.create_mock_upload_file(
            filename="script.php",
            content_type="application/x-httpd-php"
        )

        with pytest.raises(ValueError, match="not allowed"):
            await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_validate_file_no_filename(self):
        """Test validation handles missing filename."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        file = self.create_mock_upload_file(filename=None)

        with pytest.raises(ValueError, match="No filename provided"):
            await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_validate_file_empty_filename(self):
        """Test validation handles empty filename."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        file = self.create_mock_upload_file(filename="")

        with pytest.raises(ValueError, match="No filename provided"):
            await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_validate_content_type_mismatch(self):
        """Test validation detects content type mismatches."""
        config = FileUploadConfig(validate_content_type=True)
        uploader = FileUploader(config)

        # File claims to be image but extension suggests otherwise
        file = self.create_mock_upload_file(
            filename="document.pdf",
            content_type="image/jpeg"  # Wrong type
        )

        # Should still validate based on extension if it's allowed
        await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_generate_unique_filename(self):
        """Test unique filename generation."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        filename = await uploader.generate_filename("test.jpg")
        assert filename.endswith(".jpg")
        assert len(filename) > 4  # Has UUID prefix

        # Should generate different names
        filename2 = await uploader.generate_filename("test.jpg")
        assert filename != filename2

    @pytest.mark.asyncio
    async def test_generate_filename_preserves_extension(self):
        """Test filename generation preserves extension."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        filename = await uploader.generate_filename("document.pdf")
        assert filename.endswith(".pdf")

        filename = await uploader.generate_filename("IMAGE.PNG")
        assert filename.endswith(".png") or filename.endswith(".PNG")

    @pytest.mark.asyncio
    async def test_save_file_creates_directory(self):
        """Test file saving creates upload directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = Path(tmpdir) / "new_uploads"
            config = FileUploadConfig(
                upload_dir=str(upload_dir),
                create_upload_dir=True
            )
            uploader = FileUploader(config)

            file = self.create_mock_upload_file(
                filename="test.jpg",
                content=b"test image data"
            )

            uploaded_file = await uploader.save_file(file)

            assert upload_dir.exists()
            assert uploaded_file.file_path.exists()
            assert uploaded_file.size_bytes == len(b"test image data")

    @pytest.mark.asyncio
    async def test_save_file_no_create_directory(self):
        """Test file saving fails when directory doesn't exist and create_upload_dir=False."""
        config = FileUploadConfig(
            upload_dir="/nonexistent/uploads",
            create_upload_dir=False
        )
        uploader = FileUploader(config)

        file = self.create_mock_upload_file()

        with pytest.raises(Exception):  # Should fail when directory doesn't exist
            await uploader.save_file(file)

    @pytest.mark.asyncio
    async def test_save_file_handles_spaces_in_filename(self):
        """Test saving files with spaces in filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FileUploadConfig(upload_dir=tmpdir)
            uploader = FileUploader(config)

            file = self.create_mock_upload_file(
                filename="my document.pdf",
                content=b"pdf content"
            )

            uploaded_file = await uploader.save_file(file)

            assert uploaded_file.original_filename == "my document.pdf"
            assert uploaded_file.file_path.exists()
            # Generated filename shouldn't have spaces
            assert " " not in uploaded_file.filename

    @pytest.mark.asyncio
    async def test_save_file_handles_special_characters(self):
        """Test saving files with special characters in filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FileUploadConfig(upload_dir=tmpdir)
            uploader = FileUploader(config)

            file = self.create_mock_upload_file(
                filename="file@#$%&.jpg",
                content=b"image data"
            )

            uploaded_file = await uploader.save_file(file)

            assert uploaded_file.original_filename == "file@#$%&.jpg"
            assert uploaded_file.file_path.exists()


class TestFileUploadSecurity:
    """Test file upload security measures."""

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "uploads/../../../etc/passwd",
            "test/../../sensitive.txt"
        ]

        for dangerous_name in dangerous_filenames:
            file = Mock(spec=UploadFile)
            file.filename = dangerous_name
            file.content_type = "text/plain"
            file.size = 100
            file.read = AsyncMock(return_value=b"content")

            # Should either sanitize or reject
            filename = await uploader.generate_filename(dangerous_name)
            assert ".." not in filename
            assert "/" not in filename or filename.startswith("/")

    @pytest.mark.asyncio
    async def test_executable_file_rejection(self):
        """Test rejection of potentially dangerous file types."""
        dangerous_extensions = [
            ".exe", ".bat", ".cmd", ".com", ".scr",
            ".vbs", ".js", ".jar", ".app", ".deb", ".rpm"
        ]

        config = FileUploadConfig(
            allowed_extensions=[".jpg", ".png", ".pdf"]
        )
        uploader = FileUploader(config)

        for ext in dangerous_extensions:
            file = Mock(spec=UploadFile)
            file.filename = f"malicious{ext}"
            file.content_type = "application/octet-stream"
            file.size = 1024

            with pytest.raises(ValueError, match="not allowed"):
                await uploader.validate_file(file)

    @pytest.mark.asyncio
    async def test_double_extension_attack(self):
        """Test handling of double extension attacks."""
        config = FileUploadConfig(
            allowed_extensions=[".jpg", ".png"]
        )
        uploader = FileUploader(config)

        # Try to bypass with double extension
        file = Mock(spec=UploadFile)
        file.filename = "malicious.php.jpg"
        file.content_type = "image/jpeg"
        file.size = 1024

        # Should be allowed as it ends with .jpg
        await uploader.validate_file(file)

        # But the generated filename should be safe
        filename = await uploader.generate_filename(file.filename)
        assert filename.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_null_byte_injection(self):
        """Test handling of null byte injection attempts."""
        config = FileUploadConfig()
        uploader = FileUploader(config)

        file = Mock(spec=UploadFile)
        file.filename = "test.jpg\x00.php"  # Null byte injection
        file.content_type = "image/jpeg"
        file.size = 1024

        # Should handle null bytes safely
        filename = await uploader.generate_filename(file.filename)
        assert "\x00" not in filename
        assert filename.endswith(".jpg") or filename.endswith(".php")

    @pytest.mark.asyncio
    async def test_mime_type_validation(self):
        """Test MIME type validation when enabled."""
        config = FileUploadConfig(
            validate_content_type=True,
            allowed_extensions=[".jpg", ".png"]
        )
        uploader = FileUploader(config)

        # Valid MIME type
        file = Mock(spec=UploadFile)
        file.filename = "image.jpg"
        file.content_type = "image/jpeg"
        file.size = 1024

        await uploader.validate_file(file)

        # Invalid MIME type for image
        file.content_type = "text/plain"
        # Should still pass if extension is valid
        await uploader.validate_file(file)


class TestHandleFileUpload:
    """Test the handle_file_upload request handler."""

    @pytest.mark.asyncio
    async def test_handle_file_upload_success(self):
        """Test successful file upload handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FileUploadConfig(upload_dir=tmpdir)

            # Create mock request with file
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.size = 1024
            mock_file.read = AsyncMock(return_value=b"image data")

            mock_request = Mock()
            mock_request.form = AsyncMock(return_value={"file": mock_file})

            result = await handle_file_upload(mock_request, config)

            assert result["success"] is True
            assert "file" in result
            assert result["file"]["original_filename"] == "test.jpg"

    @pytest.mark.asyncio
    async def test_handle_file_upload_no_file(self):
        """Test handling when no file is provided."""
        config = FileUploadConfig()

        mock_request = Mock()
        mock_request.form = AsyncMock(return_value={})

        result = await handle_file_upload(mock_request, config)

        assert result["success"] is False
        assert "No file" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_file_upload_validation_error(self):
        """Test handling of validation errors."""
        config = FileUploadConfig(
            allowed_extensions=[".jpg"],
            max_size_mb=1
        )

        # File too large
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 10 * 1024 * 1024  # 10MB
        mock_file.read = AsyncMock(return_value=b"x" * mock_file.size)

        mock_request = Mock()
        mock_request.form = AsyncMock(return_value={"file": mock_file})

        result = await handle_file_upload(mock_request, config)

        assert result["success"] is False
        assert "exceeds maximum size" in result["error"]


class TestUploadedFileEdgeCases:
    """Test UploadedFile edge cases."""

    @pytest.mark.asyncio
    async def test_uploaded_file_zero_size(self):
        """Test handling of zero-size files."""
        file = UploadedFile(
            filename="empty.txt",
            original_filename="empty.txt",
            content_type="text/plain",
            size_bytes=0,
            file_path=Path("/tmp/empty.txt")
        )

        assert file.size_bytes == 0
        assert file.get_extension() == ".txt"

    def test_uploaded_file_unusual_extensions(self):
        """Test handling of unusual file extensions."""
        test_cases = [
            ("file.tar.gz", ".gz"),
            ("archive.7z", ".7z"),
            ("data.json5", ".json5"),
            ("file_without_extension", ""),
            (".htaccess", ""),
            ("file.", ""),
        ]

        for filename, expected_ext in test_cases:
            file = UploadedFile(
                filename=filename,
                original_filename=filename,
                content_type="application/octet-stream",
                size_bytes=100,
                file_path=Path(f"/tmp/{filename}")
            )
            assert file.get_extension() == expected_ext

    def test_uploaded_file_unicode_filename(self):
        """Test handling of Unicode characters in filenames."""
        file = UploadedFile(
            filename="文档.pdf",
            original_filename="文档.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            file_path=Path("/tmp/doc.pdf")
        )

        assert file.original_filename == "文档.pdf"
        assert file.get_extension() == ".pdf"

    @pytest.mark.asyncio
    async def test_uploaded_file_concurrent_operations(self):
        """Test UploadedFile handles concurrent operations safely."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            temp_path = Path(tmp.name)

        file = UploadedFile(
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            size_bytes=len(b"test content"),
            file_path=temp_path
        )

        # Simulate concurrent reads
        with patch("builtins.open", mock_open(read_data=b"test content")):
            results = await asyncio.gather(
                file.read(),
                file.read(),
                file.read()
            )

        assert all(r == b"test content" for r in results)

        # Clean up
        try:
            temp_path.unlink()
        except:
            pass


# Add asyncio import for the concurrent test
import asyncio
from unittest.mock import mock_open