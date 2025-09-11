"""
Advanced compression middleware with Brotli support.

Provides superior compression compared to standard gzip with 20-30% better ratios.
"""

import asyncio
import gzip
import io
import zlib
from typing import Literal

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Try to import Brotli
try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    brotli = None

# Try to import zstandard
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    zstd = None


class AdvancedCompressionMiddleware(BaseHTTPMiddleware):
    """
    Advanced compression middleware with multiple algorithm support.
    
    Features:
    - Brotli compression (best compression ratio)
    - Zstandard compression (best speed/ratio balance)
    - Gzip fallback (universal compatibility)
    - Content-type aware compression
    - Minimum size threshold
    - Quality level configuration
    
    Performance:
    - Brotli: 20-30% better than gzip
    - Zstandard: 10-15% better than gzip, faster
    - Smart algorithm selection based on Accept-Encoding
    """
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        brotli_quality: int = 4,  # 0-11, 4 is good balance
        gzip_level: int = 6,  # 1-9
        zstd_level: int = 3,  # 1-22, 3 is default
        exclude_paths: list[str] | None = None,
        exclude_mediatype: list[str] | None = None,
    ):
        """
        Initialize compression middleware.
        
        Args:
            app: ASGI application
            minimum_size: Minimum response size to compress (bytes)
            brotli_quality: Brotli compression quality (0-11)
            gzip_level: Gzip compression level (1-9)
            zstd_level: Zstandard compression level (1-22)
            exclude_paths: Paths to exclude from compression
            exclude_mediatype: Media types to exclude
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.brotli_quality = brotli_quality
        self.gzip_level = gzip_level
        self.zstd_level = zstd_level
        self.exclude_paths = set(exclude_paths or [])
        
        # Media types that shouldn't be compressed (already compressed)
        self.exclude_mediatype = set(exclude_mediatype or [
            "image/jpeg",
            "image/png", 
            "image/gif",
            "image/webp",
            "image/avif",
            "video/mp4",
            "video/webm",
            "audio/mpeg",
            "audio/ogg",
            "application/zip",
            "application/pdf",
            "application/octet-stream",
        ])
        
        # Media types that benefit from compression
        self.compressible_types = {
            "text/html",
            "text/css",
            "text/xml",
            "text/plain",
            "text/javascript",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/rss+xml",
            "application/atom+xml",
            "application/ld+json",
            "application/manifest+json",
            "image/svg+xml",
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply compression to response."""
        # Check if path should be excluded
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get response
        response = await call_next(request)
        
        # Check if we should compress
        if not self._should_compress(request, response):
            return response
        
        # Determine best encoding
        encoding = self._select_encoding(request.headers.get("accept-encoding", ""))
        if not encoding:
            return response
        
        # Compress response
        return await self._compress_response(response, encoding)
    
    def _should_compress(self, request: Request, response: Response) -> bool:
        """Determine if response should be compressed."""
        # Check response status
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        # Check if already compressed
        if "content-encoding" in response.headers:
            return False
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        if content_type:
            # Extract base type without charset
            base_type = content_type.split(";")[0].strip().lower()
            
            # Skip if excluded type
            if base_type in self.exclude_mediatype:
                return False
            
            # Only compress known compressible types
            if base_type not in self.compressible_types:
                # Check if it's a text type
                if not base_type.startswith("text/"):
                    return False
        
        return True
    
    def _select_encoding(self, accept_encoding: str) -> str | None:
        """
        Select best encoding based on Accept-Encoding header.
        
        Priority: br (Brotli) > zstd > gzip > deflate
        """
        if not accept_encoding:
            return None
        
        accept_encoding = accept_encoding.lower()
        encodings = [e.strip() for e in accept_encoding.split(",")]
        
        # Parse encodings with quality values
        encoding_prefs = {}
        for encoding in encodings:
            parts = encoding.split(";")
            name = parts[0].strip()
            
            # Parse quality value
            quality = 1.0
            if len(parts) > 1:
                for param in parts[1:]:
                    if param.strip().startswith("q="):
                        try:
                            quality = float(param.split("=")[1])
                        except ValueError:
                            quality = 1.0
            
            encoding_prefs[name] = quality
        
        # Select best available encoding
        if BROTLI_AVAILABLE and "br" in encoding_prefs and encoding_prefs["br"] > 0:
            return "br"
        
        if ZSTD_AVAILABLE and "zstd" in encoding_prefs and encoding_prefs["zstd"] > 0:
            return "zstd"
        
        if "gzip" in encoding_prefs and encoding_prefs["gzip"] > 0:
            return "gzip"
        
        if "deflate" in encoding_prefs and encoding_prefs["deflate"] > 0:
            return "deflate"
        
        # Check for wildcard
        if "*" in encoding_prefs and encoding_prefs["*"] > 0:
            # Prefer Brotli if available
            if BROTLI_AVAILABLE:
                return "br"
            return "gzip"
        
        return None
    
    async def _compress_response(self, response: Response, encoding: str) -> Response:
        """Compress response body with selected encoding."""
        # Handle streaming responses
        if isinstance(response, StreamingResponse):
            return await self._compress_streaming(response, encoding)
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Check minimum size
        if len(body) < self.minimum_size:
            # Return original response
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        # Compress body
        compressed = self._compress_data(body, encoding)
        
        # Create new response with compressed body
        headers = MutableHeaders(response.headers)
        headers["content-encoding"] = encoding
        headers["content-length"] = str(len(compressed))
        
        # Add Vary header for caching
        vary = headers.get("vary", "")
        if vary:
            if "accept-encoding" not in vary.lower():
                headers["vary"] = f"{vary}, Accept-Encoding"
        else:
            headers["vary"] = "Accept-Encoding"
        
        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=dict(headers),
            media_type=response.media_type,
        )
    
    async def _compress_streaming(
        self,
        response: StreamingResponse,
        encoding: str
    ) -> StreamingResponse:
        """Compress streaming response."""
        
        async def compressed_stream():
            """Generate compressed chunks."""
            compressor = self._create_compressor(encoding)
            
            async for chunk in response.body_iterator:
                if chunk:
                    compressed = self._compress_chunk(compressor, chunk, encoding)
                    if compressed:
                        yield compressed
            
            # Flush final data
            final = self._finalize_compression(compressor, encoding)
            if final:
                yield final
        
        # Create new streaming response
        headers = MutableHeaders(response.headers)
        headers["content-encoding"] = encoding
        headers.pop("content-length", None)  # Can't know compressed size
        
        # Add Vary header
        vary = headers.get("vary", "")
        if vary:
            if "accept-encoding" not in vary.lower():
                headers["vary"] = f"{vary}, Accept-Encoding"
        else:
            headers["vary"] = "Accept-Encoding"
        
        return StreamingResponse(
            compressed_stream(),
            status_code=response.status_code,
            headers=dict(headers),
            media_type=response.media_type,
        )
    
    def _compress_data(self, data: bytes, encoding: str) -> bytes:
        """Compress data with specified encoding."""
        if encoding == "br" and BROTLI_AVAILABLE:
            return brotli.compress(data, quality=self.brotli_quality)
        
        elif encoding == "zstd" and ZSTD_AVAILABLE:
            cctx = zstd.ZstdCompressor(level=self.zstd_level)
            return cctx.compress(data)
        
        elif encoding == "gzip":
            return gzip.compress(data, compresslevel=self.gzip_level)
        
        elif encoding == "deflate":
            return zlib.compress(data, level=self.gzip_level)
        
        return data
    
    def _create_compressor(self, encoding: str):
        """Create streaming compressor."""
        if encoding == "br" and BROTLI_AVAILABLE:
            return brotli.Compressor(quality=self.brotli_quality)
        
        elif encoding == "zstd" and ZSTD_AVAILABLE:
            return zstd.ZstdCompressor(level=self.zstd_level)
        
        elif encoding == "gzip":
            return zlib.compressobj(
                level=self.gzip_level,
                wbits=16 + zlib.MAX_WBITS,  # Gzip format
            )
        
        elif encoding == "deflate":
            return zlib.compressobj(level=self.gzip_level)
        
        return None
    
    def _compress_chunk(self, compressor, chunk: bytes, encoding: str) -> bytes:
        """Compress a single chunk."""
        if not compressor:
            return chunk
        
        if encoding == "br" and BROTLI_AVAILABLE:
            return compressor.process(chunk)
        
        elif encoding == "zstd" and ZSTD_AVAILABLE:
            return compressor.compress(chunk)
        
        else:  # gzip or deflate
            return compressor.compress(chunk)
    
    def _finalize_compression(self, compressor, encoding: str) -> bytes:
        """Finalize compression and get remaining data."""
        if not compressor:
            return b""
        
        if encoding == "br" and BROTLI_AVAILABLE:
            return compressor.finish()
        
        elif encoding == "zstd" and ZSTD_AVAILABLE:
            return compressor.flush()
        
        else:  # gzip or deflate
            return compressor.flush()


def get_compression_middleware(
    algorithm: Literal["auto", "brotli", "gzip", "zstd"] = "auto",
    **kwargs
) -> AdvancedCompressionMiddleware:
    """
    Factory function to create compression middleware.
    
    Args:
        algorithm: Compression algorithm preference
        **kwargs: Additional middleware parameters
    
    Returns:
        Configured compression middleware
    """
    # Set defaults based on algorithm
    if algorithm == "brotli":
        kwargs.setdefault("brotli_quality", 4)
    elif algorithm == "zstd":
        kwargs.setdefault("zstd_level", 3)
    elif algorithm == "gzip":
        kwargs.setdefault("gzip_level", 6)
    
    return AdvancedCompressionMiddleware(**kwargs)