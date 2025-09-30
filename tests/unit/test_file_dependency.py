"""
Tests for the enhanced File dependency API.

Covers the new File() dependency function, size parsing, file type constants,
and integration with the dependency injection system.
"""

import pytest
from unittest.mock import patch

from zenith.core.dependencies import (
    File,
    _parse_size,
    IMAGE_TYPES,
    DOCUMENT_TYPES,
    AUDIO_TYPES,
    VIDEO_TYPES,
    ARCHIVE_TYPES,
    KB,
    MB,
    GB,
)


class TestSizeConstants:
    """Test file size constants."""

    def test_size_constants_values(self):
        """Test size constants have correct byte values."""
        assert KB == 1024
        assert MB == 1024 * 1024
        assert GB == 1024 * 1024 * 1024

    def test_size_constants_math(self):
        """Test size constants work in mathematical expressions."""
        assert 10 * KB == 10240
        assert 5 * MB == 5242880
        assert 2 * GB == 2147483648


class TestFileTypeConstants:
    """Test file type constants."""

    def test_image_types_comprehensive(self):
        """Test IMAGE_TYPES includes common image formats."""
        assert "image/jpeg" in IMAGE_TYPES
        assert "image/png" in IMAGE_TYPES
        assert "image/gif" in IMAGE_TYPES
        assert "image/webp" in IMAGE_TYPES
        assert "image/svg+xml" in IMAGE_TYPES
        assert len(IMAGE_TYPES) >= 7  # Should have at least 7 common formats

    def test_document_types_comprehensive(self):
        """Test DOCUMENT_TYPES includes common document formats."""
        assert "application/pdf" in DOCUMENT_TYPES
        assert "text/plain" in DOCUMENT_TYPES
        assert "application/msword" in DOCUMENT_TYPES
        assert len(DOCUMENT_TYPES) >= 8

    def test_audio_types_comprehensive(self):
        """Test AUDIO_TYPES includes common audio formats."""
        assert "audio/mpeg" in AUDIO_TYPES
        assert "audio/wav" in AUDIO_TYPES
        assert "audio/mp3" in AUDIO_TYPES
        assert len(AUDIO_TYPES) >= 6

    def test_video_types_comprehensive(self):
        """Test VIDEO_TYPES includes common video formats."""
        assert "video/mp4" in VIDEO_TYPES
        assert "video/webm" in VIDEO_TYPES
        assert "video/quicktime" in VIDEO_TYPES
        assert len(VIDEO_TYPES) >= 6

    def test_archive_types_comprehensive(self):
        """Test ARCHIVE_TYPES includes common archive formats."""
        assert "application/zip" in ARCHIVE_TYPES
        assert "application/x-rar-compressed" in ARCHIVE_TYPES
        assert "application/gzip" in ARCHIVE_TYPES
        assert len(ARCHIVE_TYPES) >= 4


class TestSizeParsing:
    """Test size string parsing functionality."""

    def test_parse_size_none(self):
        """Test _parse_size handles None."""
        assert _parse_size(None) is None

    def test_parse_size_integer(self):
        """Test _parse_size handles raw integers."""
        assert _parse_size(1024) == 1024
        assert _parse_size(0) == 0

    def test_parse_size_string_kb(self):
        """Test _parse_size handles KB strings."""
        assert _parse_size("10KB") == 10 * 1024
        assert _parse_size("512kb") == 512 * 1024  # Case insensitive
        assert _parse_size(" 256 KB ") == 256 * 1024  # Whitespace handling

    def test_parse_size_string_mb(self):
        """Test _parse_size handles MB strings."""
        assert _parse_size("10MB") == 10 * 1024 * 1024
        assert _parse_size("5.5mb") == int(5.5 * 1024 * 1024)  # Floats
        assert _parse_size("1MB") == 1048576

    def test_parse_size_string_gb(self):
        """Test _parse_size handles GB strings."""
        assert _parse_size("1GB") == 1024 * 1024 * 1024
        assert _parse_size("2.5GB") == int(2.5 * 1024 * 1024 * 1024)

    def test_parse_size_raw_number_string(self):
        """Test _parse_size handles raw number strings as bytes."""
        assert _parse_size("1024") == 1024
        assert _parse_size("500000") == 500000

    def test_parse_size_invalid_format(self):
        """Test _parse_size raises ValueError for invalid formats."""
        with pytest.raises(ValueError, match="Invalid size format"):
            _parse_size("10TB")  # Unsupported unit

        with pytest.raises(ValueError, match="Invalid size format"):
            _parse_size("invalid")

        with pytest.raises(ValueError, match="Invalid size format"):
            _parse_size("10XB")

    def test_parse_size_invalid_type(self):
        """Test _parse_size raises ValueError for invalid types."""
        with pytest.raises(ValueError, match="Size must be string"):
            _parse_size(12.5)  # Float not allowed

        with pytest.raises(ValueError, match="Size must be string"):
            _parse_size([])  # List not allowed


class TestFileDependency:
    """Test File dependency function."""

    def test_file_dependency_returns_depends(self):
        """Test File() returns a Depends object."""
        result = File()
        assert hasattr(result, "dependency")
        assert callable(result.dependency)

    def test_file_dependency_with_string_size(self):
        """Test File() accepts string sizes."""
        result = File(max_size="10MB")
        assert hasattr(result, "dependency")
        # The dependency should be callable and created without error
        assert callable(result.dependency)

    def test_file_dependency_with_integer_size(self):
        """Test File() accepts integer sizes."""
        result = File(max_size=1048576)  # 1MB in bytes
        assert hasattr(result, "dependency")

    def test_file_dependency_with_size_constants(self):
        """Test File() works with size constants."""
        result = File(max_size=10 * MB)
        assert hasattr(result, "dependency")

    def test_file_dependency_with_type_constants(self):
        """Test File() works with file type constants."""
        result = File(allowed_types=IMAGE_TYPES)
        assert hasattr(result, "dependency")

        result = File(allowed_types=DOCUMENT_TYPES + AUDIO_TYPES)
        assert hasattr(result, "dependency")

    def test_file_dependency_with_extensions(self):
        """Test File() works with allowed extensions."""
        result = File(allowed_extensions=[".jpg", ".png"])
        assert hasattr(result, "dependency")

    def test_file_dependency_all_parameters(self):
        """Test File() works with all parameters."""
        result = File(
            max_size="10MB",
            allowed_types=IMAGE_TYPES,
            allowed_extensions=[".jpg", ".png", ".gif"],
            field_name="avatar",
        )
        assert hasattr(result, "dependency")

    def test_file_dependency_invalid_size_raises_error(self):
        """Test File() with invalid size raises error during creation."""
        # The error should occur when File() is created for better UX
        with pytest.raises(ValueError, match="Invalid size format"):
            File(max_size="invalid_size")


class TestFileDependencyIntegration:
    """Test File dependency integration patterns."""

    def test_file_dependency_usage_patterns(self):
        """Test common File dependency usage patterns."""
        # Avatar upload pattern
        avatar = File(max_size="5MB", allowed_types=IMAGE_TYPES)
        assert hasattr(avatar, "dependency")

        # Document upload pattern
        docs = File(max_size="50MB", allowed_types=DOCUMENT_TYPES)
        assert hasattr(docs, "dependency")

        # Media upload pattern
        media = File(
            max_size="100MB",
            allowed_types=IMAGE_TYPES + VIDEO_TYPES,
            allowed_extensions=[".jpg", ".mp4", ".webm"],
        )
        assert hasattr(media, "dependency")

    def test_file_dependency_flexible_sizing(self):
        """Test File dependency supports flexible sizing options."""
        # String sizes
        File(max_size="10MB")
        File(max_size="512KB")
        File(max_size="2GB")

        # Constant multiplication
        File(max_size=10 * MB)
        File(max_size=500 * KB)

        # Raw bytes
        File(max_size=1048576)

        # All should work without error
        assert True  # If we get here, all patterns worked


class TestFileAPIDocumentation:
    """Test that File API is well-documented through usage examples."""

    def test_basic_usage_example(self):
        """Test basic File usage example from docstring works."""
        # This should match the pattern in the docstring
        file_dep = File(
            max_size="10MB",
            allowed_types=IMAGE_TYPES,
            allowed_extensions=[".jpg", ".png"],
        )
        assert hasattr(file_dep, "dependency")

    def test_alternative_syntax_example(self):
        """Test alternative syntax example from docstring works."""
        # This should match the alternative pattern in the docstring
        avatar = File(max_size=5 * MB, allowed_types=["image/jpeg"])
        assert hasattr(avatar, "dependency")

    def test_type_constant_combinations(self):
        """Test combining different type constants works."""
        # Combined types
        multimedia = File(
            max_size="100MB", allowed_types=IMAGE_TYPES + VIDEO_TYPES + AUDIO_TYPES
        )
        assert hasattr(multimedia, "dependency")

    def test_real_world_scenarios(self):
        """Test realistic file upload scenarios."""
        # Profile picture
        profile_pic = File(max_size="2MB", allowed_types=IMAGE_TYPES)

        # Resume upload
        resume = File(max_size="10MB", allowed_types=DOCUMENT_TYPES)

        # Media gallery
        gallery = File(max_size="50MB", allowed_types=IMAGE_TYPES + VIDEO_TYPES)

        # All should create valid dependencies
        for dep in [profile_pic, resume, gallery]:
            assert hasattr(dep, "dependency")
            assert callable(dep.dependency)
