"""
Response compression middleware for reducing bandwidth usage.

Provides gzip and deflate compression for responses based on client
Accept-Encoding headers and configurable content types.
"""

import gzip
import zlib
from io import BytesIO
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse


class CompressionConfig:
    """Configuration for compression middleware."""
    
    def __init__(
        self,
        minimum_size: int = 500,
        compressible_types: set[str] | None = None,
        exclude_paths: set[str] | None = None,
    ):
        self.minimum_size = minimum_size
        self.exclude_paths = exclude_paths or set()
        
        # Default compressible types
        self.compressible_types = compressible_types or {
            "application/json",
            "application/javascript", 
            "application/xml",
            "text/html",
            "text/css",
            "text/javascript",
            "text/plain",
            "text/xml",
            "image/svg+xml",
        }


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that compresses responses based on client capabilities.
    
    Supports gzip and deflate compression with configurable minimum size
    and content type filtering.
    """
    
    def __init__(
        self,
        app: Any,
        config: CompressionConfig | None = None,
        # Individual parameters (for backward compatibility)
        minimum_size: int = 500,
        compressible_types: set[str] | None = None,
        exclude_paths: set[str] | None = None,
    ):
        """
        Initialize the compression middleware.
        
        Args:
            app: The ASGI application
            config: Compression configuration object
            minimum_size: Minimum response size in bytes before compression
            compressible_types: Set of content types to compress
            exclude_paths: Set of paths to exclude from compression
        """
        super().__init__(app)
        
        # Use config object if provided, otherwise use individual parameters
        if config is not None:
            self.minimum_size = config.minimum_size
            self.exclude_paths = config.exclude_paths
            self.compressible_types = config.compressible_types
        else:
            self.minimum_size = minimum_size
            self.exclude_paths = exclude_paths or set()
            
            # Default compressible types
            self.compressible_types = compressible_types or {
                "application/json",
                "application/javascript", 
                "application/xml",
                "text/html",
                "text/css",
                "text/javascript",
                "text/plain",
                "text/xml",
                "image/svg+xml",
            }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and compress response if appropriate."""
        # Skip compression for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get client's accepted encodings
        accept_encoding = request.headers.get("accept-encoding", "")
        
        # Skip if client doesn't support compression
        if not ("gzip" in accept_encoding or "deflate" in accept_encoding):
            return await call_next(request)
        
        response = await call_next(request)
        
        # Skip compression for certain response types
        if (
            response.status_code < 200 
            or response.status_code >= 300
            or response.headers.get("content-encoding")
            or response.headers.get("cache-control", "").startswith("no-transform")
        ):
            return response
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        content_type_main = content_type.split(";")[0].strip()
        
        if content_type_main not in self.compressible_types:
            return response
        
        # Get response body
        body = b""
        if hasattr(response, "body"):
            body = response.body
        elif isinstance(response, StreamingResponse):
            # Handle streaming responses by collecting body
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
            body = b"".join(chunks)
        
        # Skip compression if body is too small
        if len(body) < self.minimum_size:
            return response
        
        # Choose compression algorithm
        if "gzip" in accept_encoding:
            compressed_body = self._gzip_compress(body)
            encoding = "gzip"
        elif "deflate" in accept_encoding:
            compressed_body = self._deflate_compress(body)
            encoding = "deflate"
        else:
            return response
        
        # Only compress if it actually reduces size
        if len(compressed_body) >= len(body):
            return response
        
        # Create compressed response
        compressed_response = Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        
        # Update headers
        compressed_response.headers["content-encoding"] = encoding
        compressed_response.headers["content-length"] = str(len(compressed_body))
        compressed_response.headers["vary"] = "Accept-Encoding"
        
        return compressed_response
    
    def _gzip_compress(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as f:
            f.write(data)
        return buffer.getvalue()
    
    def _deflate_compress(self, data: bytes) -> bytes:
        """Compress data using deflate."""
        return zlib.compress(data)


def create_compression_middleware(
    minimum_size: int = 500,
    compressible_types: set[str] | None = None,
    exclude_paths: set[str] | None = None,
) -> type[CompressionMiddleware]:
    """
    Factory function to create a configured compression middleware.
    
    Args:
        minimum_size: Minimum response size in bytes before compression
        compressible_types: Set of content types to compress
        exclude_paths: Set of paths to exclude from compression
        
    Returns:
        Configured CompressionMiddleware class
    """
    def middleware_factory(app):
        return CompressionMiddleware(
            app=app,
            minimum_size=minimum_size,
            compressible_types=compressible_types,
            exclude_paths=exclude_paths,
        )
    
    return middleware_factory