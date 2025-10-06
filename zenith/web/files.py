"""
File upload handling utilities for Zenith framework.

Provides secure file upload handling with validation, storage options,
and integration with the routing system.
"""

import mimetypes
import tempfile
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.datastructures import UploadFile
from starlette.requests import Request


class FileUploadConfig(BaseModel):
    """Configuration for file uploads."""

    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB default
    allowed_extensions: list[str] = []  # Empty = allow all
    allowed_mime_types: list[str] = []  # Empty = allow all
    upload_dir: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "uploads"
    )
    preserve_filename: bool = False  # If False, generate UUIDs
    create_subdirs: bool = True  # Create subdirectories by date

    @field_validator("upload_dir")
    @classmethod
    def ensure_upload_dir_exists(cls, v):
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v


class UploadedFile(BaseModel):
    """
    Represents an uploaded file with enhanced UX methods.

    Provides both compatibility with existing code and convenient helpers
    commonly needed in real applications.
    """

    filename: str
    original_filename: str
    content_type: str | None
    size_bytes: int
    file_path: Path
    url: str | None = None  # URL to access the file

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Starlette-compatible methods for easier migration
    async def read(self) -> bytes:
        """Read the entire file content (Starlette UploadFile compatible)."""
        with self.file_path.open("rb") as f:
            return f.read()

    # Convenience methods for common patterns
    def get_extension(self) -> str:
        """Get file extension including the dot (e.g., '.pdf', '.jpg')."""
        return Path(self.filename).suffix

    def is_image(self) -> bool:
        """Check if file is an image based on content type."""
        return self.content_type.startswith("image/") if self.content_type else False

    def is_audio(self) -> bool:
        """Check if file is audio based on content type."""
        return self.content_type.startswith("audio/") if self.content_type else False

    def is_video(self) -> bool:
        """Check if file is video based on content type."""
        return self.content_type.startswith("video/") if self.content_type else False

    def is_pdf(self) -> bool:
        """Check if file is a PDF."""
        return self.content_type == "application/pdf"

    async def copy_to(self, destination: str | Path) -> Path:
        """
        Copy file to a new location.

        Args:
            destination: Target path for the copy

        Returns:
            Path object of the copied file

        Example:
            backup_path = await uploaded_file.copy_to("/backups/file.pdf")
        """
        import shutil

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.file_path, destination)
        return destination

    async def move_to(self, destination: str | Path) -> Path:
        """
        Move file to a new location.

        Args:
            destination: Target path for the move

        Returns:
            Path object of the moved file

        Example:
            final_path = await uploaded_file.move_to("/final/location.pdf")
        """
        import shutil

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.file_path, destination)

        # Update our internal path
        self.file_path = destination
        return destination

    def __repr__(self) -> str:
        return f"UploadedFile(filename={self.filename!r}, size={self.size_bytes}, type={self.content_type!r})"


class FileUploadError(Exception):
    """Raised when file upload fails validation."""

    pass


class FileUploader:
    """Handles file upload operations."""

    def __init__(self, config: FileUploadConfig = None):
        self.config = config or FileUploadConfig()

    def validate_file(self, file: UploadFile) -> bool:
        """Validate uploaded file against configuration."""
        # Check file size
        if hasattr(file.file, "seek") and hasattr(file.file, "tell"):
            # Get file size
            file.file.seek(0, 2)  # Seek to end
            size = file.file.tell()
            file.file.seek(0)  # Reset to start

            if size > self.config.max_file_size_bytes:
                raise FileUploadError(
                    f"File size ({size} bytes) exceeds maximum allowed size "
                    f"({self.config.max_file_size_bytes} bytes)"
                )

        # Check file extension
        if self.config.allowed_extensions:
            file_ext = Path(file.filename or "").suffix.lower()
            if file_ext not in [
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in self.config.allowed_extensions
            ]:
                raise FileUploadError(
                    f"File extension '{file_ext}' not allowed. "
                    f"Allowed extensions: {self.config.allowed_extensions}"
                )

        # Check MIME type
        if self.config.allowed_mime_types:
            if file.content_type not in self.config.allowed_mime_types:
                raise FileUploadError(
                    f"MIME type '{file.content_type}' not allowed. "
                    f"Allowed types: {self.config.allowed_mime_types}"
                )

        return True

    def generate_filename(self, original_filename: str) -> str:
        """Generate a safe filename for storage."""
        if self.config.preserve_filename:
            # Sanitize the original filename
            filename = Path(original_filename).name
            # Remove potentially dangerous characters
            safe_chars = (
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
            )
            filename = "".join(c for c in filename if c in safe_chars)
            return filename or f"{uuid.uuid4().hex}.bin"
        else:
            # Generate UUID-based filename with original extension
            ext = Path(original_filename).suffix if original_filename else ""
            return f"{uuid.uuid4().hex}{ext}"

    def get_upload_path(self, filename: str) -> Path:
        """Get the full path where file should be stored."""
        base_path = self.config.upload_dir

        if self.config.create_subdirs:
            from datetime import datetime

            date_dir = datetime.now().strftime("%Y/%m/%d")
            base_path = base_path / date_dir
            base_path.mkdir(parents=True, exist_ok=True)

        return base_path / filename

    async def save_file(self, file: UploadFile) -> UploadedFile:
        """Save uploaded file to storage."""
        # Validate the file
        self.validate_file(file)

        # Generate safe filename
        safe_filename = self.generate_filename(file.filename or "unnamed")
        file_path = self.get_upload_path(safe_filename)

        # Ensure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file content
        with Path(file_path).open("wb") as f:
            # Read file in chunks to handle large files
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break
                f.write(chunk)

        # Reset file pointer for potential reuse
        await file.seek(0)

        # Get file size
        file_size = file_path.stat().st_size

        # Detect content type if not provided
        content_type = file.content_type
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or "application/octet-stream"

        return UploadedFile(
            filename=safe_filename,
            original_filename=file.filename or "unnamed",
            content_type=content_type,
            size_bytes=file_size,
            file_path=file_path,
        )

    async def save_multiple_files(self, files: list[UploadFile]) -> list[UploadedFile]:
        """Save multiple uploaded files."""
        uploaded_files = []
        for file in files:
            uploaded_file = await self.save_file(file)
            uploaded_files.append(uploaded_file)
        return uploaded_files


# Default uploader instance
default_uploader = FileUploader()


async def handle_file_upload(
    request: Request, field_name: str = "file", config: FileUploadConfig = None
) -> UploadedFile | list[UploadedFile]:
    """
    Handle file upload from request.

    Args:
        request: The incoming request
        field_name: Form field name containing the file(s)
        config: Upload configuration

    Returns:
        UploadedFile or list of UploadedFiles
    """
    uploader = FileUploader(config) if config else default_uploader

    # Get form data
    form = await request.form()

    # Handle single or multiple files
    files = form.getlist(field_name)
    if not files:
        raise FileUploadError(f"No files found in field '{field_name}'")

    # Filter out empty files
    upload_files = [f for f in files if isinstance(f, UploadFile) and f.filename]

    if not upload_files:
        raise FileUploadError("No valid files to upload")

    if len(upload_files) == 1:
        return await uploader.save_file(upload_files[0])
    else:
        return await uploader.save_multiple_files(upload_files)


# Dependency injection helper for file uploads
class FileUpload:
    """Dependency marker for file upload handling."""

    def __init__(self, field_name: str = "file", config: FileUploadConfig = None):
        self.field_name = field_name
        self.config = config
