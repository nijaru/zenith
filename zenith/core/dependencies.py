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
    "Session", "Auth", "CurrentUser", "File", "Inject", "Request",
    # File upload constants for better DX
    "IMAGE_TYPES", "DOCUMENT_TYPES", "AUDIO_TYPES", "VIDEO_TYPES", "ARCHIVE_TYPES",
    "MB", "GB", "KB"
]

T = TypeVar("T")

KB = 1024
MB = 1024 * 1024
GB = 1024 * 1024 * 1024

IMAGE_TYPES = [
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "image/webp", "image/bmp", "image/tiff", "image/svg+xml"
]

DOCUMENT_TYPES = [
    "application/pdf", "text/plain", "text/markdown",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"
]

AUDIO_TYPES = [
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg",
    "audio/aac", "audio/flac", "audio/m4a"
]

VIDEO_TYPES = [
    "video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo",
    "video/webm", "video/ogg", "video/x-flv"
]

ARCHIVE_TYPES = [
    "application/zip", "application/x-rar-compressed", "application/x-tar",
    "application/gzip", "application/x-7z-compressed"
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
        raise ValueError(f"Size must be string like '10MB' or integer, got {type(size)}")

    size = size.upper().strip()

    if size.endswith('KB'):
        return int(float(size[:-2]) * KB)
    elif size.endswith('MB'):
        return int(float(size[:-2]) * MB)
    elif size.endswith('GB'):
        return int(float(size[:-2]) * GB)
    elif size.isdigit():
        return int(size)  # Assume bytes if just a number
    else:
        raise ValueError(f"Invalid size format: {size}. Use '10MB', '512KB', '1GB', or bytes as integer")


async def get_validated_file(
    max_size: str | int | None = None,
    allowed_types: list[str] | None = None,
    allowed_extensions: list[str] | None = None,
    field_name: str = "file"
) -> Any:
    """
    Get validated file upload dependency.

    Returns the uploaded file after validation, or raises HTTPException
    if validation fails.

    Args:
        max_size: Maximum file size ('10MB', '512KB', '1GB') or bytes as int
        allowed_types: List of allowed MIME types (use IMAGE_TYPES, etc.)
        allowed_extensions: List of allowed file extensions ['.jpg', '.png']
        field_name: Form field name (default: "file")
    """
    parsed_size = _parse_size(max_size)

    # This is a placeholder - actual implementation would need to:
    # 1. Get the file from the request
    # 2. Validate size against parsed_size
    # 3. Validate MIME type against allowed_types
    # 4. Validate extension against allowed_extensions
    # 5. Return UploadFile or enhanced UploadedFile
    # For now, return None to indicate not implemented
    return None


# Convenient dependency shortcuts (Rails-like simplicity)
# These can be used directly in route parameters

# Database session dependency - the one true way
Session = Depends(get_database_session)      # Clear, concise, conventional

# Authentication shortcuts
Auth = Depends(get_auth_user)
CurrentUser = Depends(get_auth_user)  # Clearer alias for current user

# Request object shortcut
Request = Depends(get_current_request_dependency)


def File(
    max_size: str | int | None = None,
    allowed_types: list[str] | None = None,
    allowed_extensions: list[str] | None = None,
    field_name: str = "file"
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

    def create_file_validator():
        """Create a file validator with the specified constraints."""
        return lambda: get_validated_file(parsed_size, allowed_types, allowed_extensions, field_name)

    return Depends(create_file_validator())


def Inject(service_type: type[T] | None = None) -> Any:
    """
    Enhanced dependency injection for services.

    Works similar to FastAPI's Depends but with automatic service resolution.

    Usage:
        @app.get("/posts")
        async def get_posts(
            posts_service: PostService = Inject(),
            user: User = Auth,
            session: AsyncSession = Session
        ):
            return await posts_service.get_recent_posts()

    For explicit service types:
        @app.get("/posts")
        async def get_posts(posts: PostService = Inject(PostService)):
            return await posts.get_recent_posts()
    """
    if service_type is None:
        # Auto-resolve from type annotation
        def auto_resolve_service():
            # This will be resolved by FastAPI based on the parameter type annotation
            # The actual service resolution will be handled by the DI container
            pass

        return Depends(auto_resolve_service)
    else:
        # Explicit service type
        def resolve_service() -> service_type:
            # TODO: Integrate with DI container to resolve services
            # For now, return a basic implementation
            return service_type()

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
        # Initialize services
        for service_type in self.services:
            # TODO: Proper service resolution
            self.instances[service_type] = service_type()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup services if needed
        pass

    def get(self, service_type: type[T]) -> T:
        """Get a service instance."""
        return self.instances.get(service_type)
