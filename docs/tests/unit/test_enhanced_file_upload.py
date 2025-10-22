"""
Tests for enhanced file upload functionality.

Covers the improved UploadedFile API with convenience methods
and better UX based on production feedback.
"""

import contextlib
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from zenith.web.files import UploadedFile


class TestUploadedFile:
    """Test enhanced UploadedFile functionality."""

    def create_test_uploaded_file(
        self,
        filename: str = "test.pdf",
        content_type: str = "application/pdf",
        size: int = 1024,
    ) -> UploadedFile:
        """Create a test UploadedFile instance."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            temp_path = Path(tmp.name)

        return UploadedFile(
            filename=filename,
            original_filename=filename,
            content_type=content_type,
            size_bytes=size,
            file_path=temp_path,
        )

    def test_uploaded_file_creation(self):
        """Test UploadedFile can be created with required fields."""
        file = self.create_test_uploaded_file()
        assert file.filename == "test.pdf"
        assert file.original_filename == "test.pdf"
        assert file.content_type == "application/pdf"
        assert file.size_bytes == 1024

    @pytest.mark.asyncio
    async def test_read_method(self):
        """Test Starlette-compatible read() method."""
        file = self.create_test_uploaded_file()

        # Mock file content
        with patch("builtins.open", mock_open(read_data=b"test file content")):
            content = await file.read()
            assert content == b"test file content"

    def test_get_extension(self):
        """Test get_extension method."""
        file = self.create_test_uploaded_file("document.pdf")
        assert file.get_extension() == ".pdf"

        file = self.create_test_uploaded_file("image.jpg")
        assert file.get_extension() == ".jpg"

        file = self.create_test_uploaded_file("no_extension")
        assert file.get_extension() == ""

    def test_is_image(self):
        """Test is_image method."""
        # Test image types
        image_file = self.create_test_uploaded_file("pic.jpg", "image/jpeg")
        assert image_file.is_image() is True

        png_file = self.create_test_uploaded_file("pic.png", "image/png")
        assert png_file.is_image() is True

        # Test non-image type
        pdf_file = self.create_test_uploaded_file("doc.pdf", "application/pdf")
        assert pdf_file.is_image() is False

        # Test None content type
        no_type_file = self.create_test_uploaded_file("file", None)
        assert no_type_file.is_image() is False

    def test_is_audio(self):
        """Test is_audio method."""
        audio_file = self.create_test_uploaded_file("song.mp3", "audio/mpeg")
        assert audio_file.is_audio() is True

        wav_file = self.create_test_uploaded_file("sound.wav", "audio/wav")
        assert wav_file.is_audio() is True

        pdf_file = self.create_test_uploaded_file("doc.pdf", "application/pdf")
        assert pdf_file.is_audio() is False

    def test_is_video(self):
        """Test is_video method."""
        video_file = self.create_test_uploaded_file("movie.mp4", "video/mp4")
        assert video_file.is_video() is True

        self.create_test_uploaded_file("clip.webm", "video/webm")
        assert video_file.is_video() is True

        pdf_file = self.create_test_uploaded_file("doc.pdf", "application/pdf")
        assert pdf_file.is_video() is False

    def test_is_pdf(self):
        """Test is_pdf method."""
        pdf_file = self.create_test_uploaded_file("doc.pdf", "application/pdf")
        assert pdf_file.is_pdf() is True

        image_file = self.create_test_uploaded_file("pic.jpg", "image/jpeg")
        assert image_file.is_pdf() is False

    @pytest.mark.asyncio
    async def test_copy_to(self):
        """Test copy_to method."""
        file = self.create_test_uploaded_file()

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "copied_file.pdf"

            with patch("shutil.copy2") as mock_copy:
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    result = await file.copy_to(destination)

                    assert result == destination
                    mock_copy.assert_called_once_with(file.file_path, destination)
                    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_move_to(self):
        """Test move_to method."""
        file = self.create_test_uploaded_file()
        original_path = file.file_path

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "moved_file.pdf"

            with patch("shutil.move") as mock_move:
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    result = await file.move_to(destination)

                    assert result == destination
                    assert file.file_path == destination  # Path should be updated
                    mock_move.assert_called_once_with(original_path, destination)
                    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_repr(self):
        """Test string representation."""
        file = self.create_test_uploaded_file()
        repr_str = repr(file)

        assert "UploadedFile" in repr_str
        assert "test.pdf" in repr_str
        assert "1024" in repr_str
        assert "application/pdf" in repr_str

    def teardown_method(self):
        """Clean up temporary files after each test."""
        # Clean up any temporary files created during tests

        temp_files = list(Path("/tmp").glob("tmp*"))
        for temp_file in temp_files:
            with contextlib.suppress(OSError, FileNotFoundError):
                Path(temp_file).unlink()


class TestFileTypeDetection:
    """Test file type detection across different scenarios."""

    def test_image_detection_variants(self):
        """Test image detection with various MIME types."""
        test_cases = [
            ("image/jpeg", True),
            ("image/png", True),
            ("image/gif", True),
            ("image/webp", True),
            ("image/svg+xml", True),
            ("application/pdf", False),
            ("audio/mpeg", False),
            ("video/mp4", False),
            ("text/plain", False),
            (None, False),
        ]

        for content_type, expected in test_cases:
            file = UploadedFile(
                filename="test.file",
                original_filename="test.file",
                content_type=content_type,
                size_bytes=100,
                file_path=Path("/tmp/test"),
            )
            assert file.is_image() == expected, f"Failed for {content_type}"

    def test_audio_detection_variants(self):
        """Test audio detection with various MIME types."""
        test_cases = [
            ("audio/mpeg", True),
            ("audio/wav", True),
            ("audio/ogg", True),
            ("audio/flac", True),
            ("audio/aac", True),
            ("image/jpeg", False),
            ("video/mp4", False),
            ("application/pdf", False),
            (None, False),
        ]

        for content_type, expected in test_cases:
            file = UploadedFile(
                filename="test.file",
                original_filename="test.file",
                content_type=content_type,
                size_bytes=100,
                file_path=Path("/tmp/test"),
            )
            assert file.is_audio() == expected, f"Failed for {content_type}"

    def test_extension_detection_edge_cases(self):
        """Test extension detection with edge cases."""
        test_cases = [
            ("file.pdf", ".pdf"),
            ("file.jpeg", ".jpeg"),
            ("file.tar.gz", ".gz"),
            ("file", ""),
            ("file.", ""),
            (".hidden", ""),
            (".hidden.txt", ".txt"),
            ("", ""),
        ]

        for filename, expected_ext in test_cases:
            file = UploadedFile(
                filename=filename,
                original_filename=filename,
                content_type="application/octet-stream",
                size_bytes=100,
                file_path=Path("/tmp/test"),
            )
            assert file.get_extension() == expected_ext, f"Failed for {filename}"


class TestEnhancedFileUploadUX:
    """Test UX improvements based on production app feedback."""

    @pytest.mark.asyncio
    async def test_production_file_handling_pattern(self):
        """Test the improved pattern that addresses real app pain points."""
        # This pattern was problematic in djscout-cloud app
        file = UploadedFile(
            filename="22cbcac08f654faba7e0d539c1840c2d.wav",
            original_filename="my_song.wav",
            content_type="audio/wav",
            size_bytes=5 * 1024 * 1024,  # 5MB
            file_path=Path("/tmp/uploaded_file"),
        )

        # ✅ Now works with enhanced API
        assert file.is_audio()
        assert file.get_extension() == ".wav"

        # ✅ Easy file operations
        with patch("shutil.move") as mock_move:
            with patch("pathlib.Path.mkdir"):
                await file.move_to("/storage/audio/final_location.wav")
                mock_move.assert_called_once()

        # ✅ Starlette-compatible read
        with patch("builtins.open", mock_open(read_data=b"audio data")):
            content = await file.read()
            assert content == b"audio data"

    def test_uuid_filename_compatibility(self):
        """Test handling of UUID-based filenames (common production pattern)."""
        uuid_filename = "a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3"

        file = UploadedFile(
            filename=uuid_filename,
            original_filename="My Song.mp3",  # Original had spaces
            content_type="audio/mpeg",
            size_bytes=8 * 1024 * 1024,
            file_path=Path(f"/uploads/{uuid_filename}"),
        )

        assert file.get_extension() == ".mp3"
        assert file.is_audio()
        assert file.original_filename == "My Song.mp3"  # Original preserved
        assert file.filename == uuid_filename  # UUID version used

    def test_mixed_content_type_detection(self):
        """Test content type detection when filename and MIME type differ."""
        # Common case: file uploaded with wrong/missing MIME type
        file = UploadedFile(
            filename="document.pdf",
            original_filename="document.pdf",
            content_type="application/octet-stream",  # Generic type
            size_bytes=1024,
            file_path=Path("/tmp/document.pdf"),
        )

        # Extension-based detection would help here
        assert file.get_extension() == ".pdf"
        # is_pdf() relies on content_type, so this would be False
        assert file.is_pdf() is False

        # But with correct content type:
        file.content_type = "application/pdf"
        assert file.is_pdf() is True
