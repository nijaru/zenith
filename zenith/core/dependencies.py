"""
Enhanced dependency injection patterns for better developer experience.

Provides convenient shortcuts for common dependencies like database sessions,
authentication, caching, and other services.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any, TypeVar

try:
    from fastapi import Depends, UploadFile
except ImportError:
    # FastAPI not available, create a dummy Depends for type compatibility
    class Depends:
        def __init__(self, dependency: Callable[..., Any]):
            self.dependency = dependency

    # Mock UploadFile for environments without FastAPI
    class UploadFile:
        def __init__(self, filename=None, content_type=None):
            self.filename = filename
            self.content_type = content_type


from sqlalchemy.ext.asyncio import AsyncSession

from .container import get_db_session, set_current_db_session
from .scoped import get_current_request

__all__ = [
    "ARCHIVE_TYPES",
    "AUDIO_TYPES",
    "DOCUMENT_TYPES",
    "GB",
    # File upload constants for better DX
    "IMAGE_TYPES",
    "KB",
    "MB",
    "VIDEO_TYPES",
    "Auth",
    "CurrentUser",
    "File",
    "Inject",
    "Request",
    "Session",
]

T = TypeVar("T")

KB = 1024
MB = 1024 * 1024
GB = 1024 * 1024 * 1024

IMAGE_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/svg+xml",
]

DOCUMENT_TYPES = [
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]

AUDIO_TYPES = [
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/ogg",
    "audio/aac",
    "audio/flac",
    "audio/m4a",
]

VIDEO_TYPES = [
    "video/mp4",
    "video/mpeg",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/ogg",
    "video/x-flv",
]

ARCHIVE_TYPES = [
    "application/zip",
    "application/x-rar-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-7z-compressed",
]


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency for FastAPI routes.

    Usage:
        @app.get("/users")
        async def get_users(session: AsyncSession = Session):
            users = await User.all()
            return users
    """
    session = await get_db_session()
    set_current_db_session(session)
    try:
        yield session
    finally:
        set_current_db_session(None)


async def get_auth_user() -> Any:
    """
    Get authenticated user dependency.

    Returns the current authenticated user from the request context,
    or None if no user is authenticated.
    """
    from zenith.auth.dependencies import get_current_user

    request = get_current_request()
    if request:
        return get_current_user(request)
    return None


async def get_current_request_dependency() -> Any:
    """
    Get current HTTP request object from context.

    Returns the current request object, or None if not in request context.
    """
    from .scoped import get_current_request as get_request

    return get_request()


def _parse_size(size: str | int | None) -> int | None:
    """Parse size string like '10MB' into bytes."""
    if size is None or isinstance(size, int):
        return size

    if not isinstance(size, str):
        raise ValueError(
            f"Size must be string like '10MB' or integer, got {type(size)}"
        )

    size = size.upper().strip()

    if size.endswith("KB"):
        return int(float(size[:-2]) * KB)
    elif size.endswith("MB"):
        return int(float(size[:-2]) * MB)
    elif size.endswith("GB"):
        return int(float(size[:-2]) * GB)
    elif size.isdigit():
        return int(size)  # Assume bytes if just a number
    else:
        raise ValueError(
            f"Invalid size format: {size}. Use '10MB', '512KB', '1GB', or bytes as integer"
        )


def get_validated_file(
    max_size: int | None = None,
    allowed_types: list[str] | None = None,
    allowed_extensions: list[str] | None = None,
    field_name: str = "file",
) -> Any:
    """
    Get validated file upload dependency.

    Returns the uploaded file after validation, or raises HTTPException
    if validation fails.

    Args:
        max_size: Maximum file size in bytes
        allowed_types: List of allowed MIME types (use IMAGE_TYPES, etc.)
        allowed_extensions: List of allowed file extensions ['.jpg', '.png']
        field_name: Form field name (default: "file")
    """
    from starlette.datastructures import UploadFile as StarletteUploadFile

    from zenith.exceptions import ValidationException

    # This function will be called during request handling
    # We need to return a dependency function that gets the request from context
    async def validate_file_upload() -> StarletteUploadFile:
        # Get the request from the current context
        request = get_current_request()
        if not request:
            raise ValueError("No request context available")
        # Get the file from the request form data
        form = await request.form()
        file_field = form.get(field_name)

        if not file_field or not isinstance(file_field, StarletteUploadFile):
            raise ValidationException(f"No file uploaded in field '{field_name}'")

        file: StarletteUploadFile = file_field

        # Validate file size
        if max_size is not None:
            # Read file size (we need to read the file to check size)
            contents = await file.read()
            file_size = len(contents)
            # Reset file position so it can be read again
            await file.seek(0)

            if file_size > max_size:
                size_mb = max_size / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                raise ValidationException(
                    f"File size ({actual_mb:.2f}MB) exceeds maximum allowed size ({size_mb:.2f}MB)"
                )

        # Validate MIME type
        if allowed_types and file.content_type:
            if file.content_type not in allowed_types:
                raise ValidationException(
                    f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(allowed_types)}"
                )

        # Validate file extension
        if allowed_extensions and file.filename:
            from pathlib import Path

            ext = Path(file.filename).suffix.lower()
            if ext not in [e.lower() for e in allowed_extensions]:
                raise ValidationException(
                    f"File extension '{ext}' not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
                )

        return file

    return validate_file_upload


# Convenient dependency shortcuts (Rails-like simplicity)
# These can be used directly in route parameters

# Database session dependency - the one true way
Session = Depends(get_database_session)  # Clear, concise, conventional

# Authentication shortcuts
Auth = Depends(get_auth_user)
CurrentUser = Depends(get_auth_user)  # Clearer alias for current user

# Request object shortcut
Request = Depends(get_current_request_dependency)


def File(
    max_size: str | int | None = None,
    allowed_types: list[str] | None = None,
    allowed_extensions: list[str] | None = None,
    field_name: str = "file",
) -> Any:
    """
    File upload dependency with validation.

    Usage:
        from zenith import File, IMAGE_TYPES, MB

        @app.post("/upload")
        async def upload_file(
            file: UploadFile = File(
                max_size="10MB",
                allowed_types=IMAGE_TYPES,
                allowed_extensions=[".jpg", ".png"]
            )
        ):
            return {"filename": file.filename}

        avatar: UploadFile = File(max_size=5*MB, allowed_types=["image/jpeg"])

    Args:
        max_size: Max file size ("10MB", "512KB", "1GB") or bytes as int
        allowed_types: MIME types (use IMAGE_TYPES, DOCUMENT_TYPES, etc.)
        allowed_extensions: File extensions ['.jpg', '.png'] for extra validation
        field_name: Form field name (default: "file")
    """
    # Validate parameters at creation time for better error messages
    parsed_size = _parse_size(max_size)  # This will raise ValueError if invalid

    # Create the dependency function that will be resolved by the DI system
    file_validator = get_validated_file(
        parsed_size, allowed_types, allowed_extensions, field_name
    )

    return Depends(file_validator)


# Global service registry for singleton instances
_service_instances: dict[type, Any] = {}
_service_lock = None  # Will be initialized on first use


def _get_service_lock():
    """Get or create the async lock for thread-safe singleton creation."""
    global _service_lock
    if _service_lock is None:
        import asyncio

        _service_lock = asyncio.Lock()
    return _service_lock


def Inject[T](service_type: type[T] | None = None) -> Any:
    """
    Dependency injection for singleton services.

    Services are created once and reused across all requests (singleton pattern).
    This is ideal for services that manage connections, caches, or expensive resources.

    Usage:
        @app.get("/posts")
        async def get_posts(
            posts_service: PostService = Inject(PostService),
            user: User = Auth
        ):
            return await posts_service.get_recent_posts()

    Note: Services should be stateless or thread-safe as they're shared across requests.
    """
    if service_type is None:
        # For auto-resolution, FastAPI needs to inspect type hints
        # This requires the service to be registered or type hint to work
        async def auto_resolve_service():
            # FastAPI will provide the actual type through inspection
            # This is a placeholder that shouldn't be called directly
            raise NotImplementedError(
                "Auto-resolution requires type hints. Use Inject(ServiceClass) explicitly."
            )

        return Depends(auto_resolve_service)

    # Explicit service type - create singleton resolver
    async def resolve_service() -> service_type:
        """Get or create singleton instance of the service."""
        # Check if instance already exists
        if service_type in _service_instances:
            return _service_instances[service_type]

        # Create new instance with thread-safe lock
        async with _get_service_lock():
            # Double-check pattern - another request might have created it
            if service_type in _service_instances:
                return _service_instances[service_type]

            # Create and store singleton instance
            instance = service_type()

            # Initialize if it has an async initialize method
            if hasattr(instance, "initialize") and callable(instance.initialize):
                await instance.initialize()

            _service_instances[service_type] = instance
            return instance

    return Depends(resolve_service)


# Service decorator removed - use Service base class from zenith.core.service instead
# The @Service() decorator pattern was confusing and rarely used


# Type aliases for better documentation - these provide clear naming
# but use the same underlying dependency injection
AuthenticatedUser = Annotated[Any, Auth]
HttpRequest = Annotated[Any, Request]

# Remove redundant DatabaseSession - Session is clearer and more concise


# Convenience functions for manual dependency resolution
async def resolve_db() -> AsyncSession:
    """Manually resolve database session outside of FastAPI context."""
    return await get_db_session()


async def resolve_auth() -> Any:
    """Manually resolve authenticated user outside of FastAPI context."""
    return await get_auth_user()


# Context managers for manual session management
class DatabaseContext:
    """Context manager for database operations outside web requests."""

    def __init__(self):
        self.session = None

    async def __aenter__(self) -> AsyncSession:
        self.session = await resolve_db()
        set_current_db_session(self.session)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        set_current_db_session(None)
        if self.session:
            await self.session.close()


class ServiceContext:
    """Context manager for service operations outside web requests."""

    def __init__(self, *services: type):
        self.services = services
        self.instances = {}

    async def __aenter__(self):
        # Initialize services with simple instantiation
        # Services are expected to have zero-argument constructors
        for service_type in self.services:
            self.instances[service_type] = service_type()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup services if needed
        pass

    def get(self, service_type: type[T]) -> T:
        """Get a service instance."""
        return self.instances.get(service_type)
