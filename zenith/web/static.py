"""
Static file serving utilities for Zenith framework.

Provides efficient static file serving with proper headers,
caching, and security features.
"""

import hashlib
import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path

from starlette.responses import FileResponse, Response
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles as StarletteStaticFiles


class StaticFileConfig:
    """Configuration for static file serving."""

    def __init__(
        self,
        directory: str,
        packages: list | None = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
        # Caching settings
        max_age: int = 3600,  # 1 hour default
        etag: bool = True,
        last_modified: bool = True,
        # Security settings
        allow_hidden: bool = False,
        allowed_extensions: list | None = None,  # None = allow all
    ):
        self.directory = directory
        self.packages = packages
        self.html = html
        self.check_dir = check_dir
        self.follow_symlink = follow_symlink
        self.max_age = max_age
        self.etag = etag
        self.last_modified = last_modified
        self.allow_hidden = allow_hidden
        self.allowed_extensions = allowed_extensions


class ZenithStaticFiles(StarletteStaticFiles):
    """Enhanced static files handler with additional features."""

    def __init__(self, config: StaticFileConfig):
        super().__init__(
            directory=config.directory,
            packages=config.packages,
            html=config.html,
            check_dir=config.check_dir,
            follow_symlink=config.follow_symlink,
        )
        self.config = config

    def file_response(
        self,
        full_path: str,
        stat_result: os.stat_result,
        scope: dict,
        status_code: int = 200,
    ) -> Response:
        """Create response for a static file with enhanced headers."""
        # Security check: don't serve hidden files unless allowed
        if not self.config.allow_hidden and Path(full_path).name.startswith("."):
            return Response(status_code=404)

        # Extension check
        if self.config.allowed_extensions:
            ext = Path(full_path).suffix.lower()
            if ext not in [
                e.lower() if e.startswith(".") else f".{e.lower()}"
                for e in self.config.allowed_extensions
            ]:
                return Response(status_code=404)

        # Get basic file response
        response = FileResponse(
            full_path, stat_result=stat_result, status_code=status_code, headers={}
        )

        # Add caching headers
        if self.config.max_age > 0:
            response.headers["cache-control"] = f"public, max-age={self.config.max_age}"

        # Add ETag if enabled
        if self.config.etag:
            # Simple ETag based on file mtime and size
            etag_data = f"{stat_result.st_mtime}-{stat_result.st_size}"
            etag = hashlib.md5(etag_data.encode()).hexdigest()
            response.headers["etag"] = f'"{etag}"'

        # Add Last-Modified if enabled
        if self.config.last_modified:
            mtime = datetime.fromtimestamp(stat_result.st_mtime, tz=UTC)
            response.headers["last-modified"] = mtime.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

        # Add security headers
        response.headers["x-content-type-options"] = "nosniff"

        # Set appropriate Content-Type
        content_type, _ = mimetypes.guess_type(full_path)
        if content_type:
            response.headers["content-type"] = content_type

        return response


def create_static_route(
    path: str, directory: str, name: str = "static", **config_kwargs
) -> Mount:
    """
    Create a static file serving route.

    Args:
        path: URL path prefix (e.g., "/static")
        directory: Local directory to serve files from
        name: Route name for URL generation
        **config_kwargs: Additional configuration options

    Returns:
        Mount route for static files

    Example:
        app.mount("/static", create_static_route(
            "/static",
            "public",
            max_age=86400,  # 1 day
            allowed_extensions=[".css", ".js", ".png", ".jpg", ".ico"]
        ))
    """
    config = StaticFileConfig(directory=directory, **config_kwargs)
    static_files = ZenithStaticFiles(config)

    return Mount(path, app=static_files, name=name)


class SPAStaticFiles(ZenithStaticFiles):
    """Static files handler with SPA fallback support."""
    
    def __init__(self, config: StaticFileConfig, fallback: str = "index.html"):
        super().__init__(config)
        self.fallback = fallback
    
    async def get_response(self, path: str, scope: dict) -> Response:
        """Get response for a path, falling back to index.html for SPAs."""
        try:
            # Try to get the actual file first
            response = await super().get_response(path, scope)
            # If we get a 404, try the fallback
            if response.status_code == 404:
                # Try to serve the fallback file (usually index.html)
                fallback_path = "" if self.fallback == "index.html" else self.fallback
                response = await super().get_response(fallback_path, scope)
            return response
        except Exception:
            # If anything fails, try to serve the fallback
            try:
                fallback_path = "" if self.fallback == "index.html" else self.fallback
                return await super().get_response(fallback_path, scope)
            except Exception:
                # If even the fallback fails, return 404
                return Response(status_code=404)


def serve_spa_files(
    directory: str = "dist", fallback: str = "index.html", **config_kwargs
) -> SPAStaticFiles:
    """
    Serve Single Page Application files with fallback support.

    Args:
        directory: Directory containing SPA files
        fallback: Fallback file for client-side routing
        **config_kwargs: Additional configuration options

    Returns:
        StaticFiles app configured for SPA

    Example:
        app.mount("/", serve_spa_files(
            "dist",
            fallback="index.html",
            max_age=300  # 5 minutes for SPA files
        ))
    """
    config = StaticFileConfig(
        directory=directory,
        html=True,  # Enable HTML file serving
        **config_kwargs,
    )

    return SPAStaticFiles(config, fallback=fallback)


# Convenience functions for common static file patterns


def serve_css_js(directory: str = "assets", path: str = "/assets") -> Mount:
    """Serve CSS and JavaScript files with long caching."""
    return create_static_route(
        path=path,
        directory=directory,
        name="assets",
        max_age=86400 * 30,  # 30 days
        allowed_extensions=[".css", ".js", ".map"],
        etag=True,
        last_modified=True,
    )


def serve_images(directory: str = "images", path: str = "/images") -> Mount:
    """Serve image files with long caching."""
    return create_static_route(
        path=path,
        directory=directory,
        name="images",
        max_age=86400 * 7,  # 7 days
        allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"],
        etag=True,
        last_modified=True,
    )


def serve_uploads(directory: str = "uploads", path: str = "/uploads") -> Mount:
    """Serve user uploaded files with moderate caching."""
    return create_static_route(
        path=path,
        directory=directory,
        name="uploads",
        max_age=3600,  # 1 hour
        etag=True,
        last_modified=True,
        allow_hidden=False,  # Security: don't serve hidden files
    )
