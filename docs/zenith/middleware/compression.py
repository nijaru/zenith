"""
Response compression middleware for reducing bandwidth usage.

Provides gzip and deflate compression for responses based on client
Accept-Encoding headers and configurable content types.
"""

import gzip
import zlib
from io import BytesIO

from starlette.types import ASGIApp, Receive, Scope, Send


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


class CompressionMiddleware:
    """
    Middleware that compresses responses based on client capabilities.

    Supports gzip and deflate compression with configurable minimum size
    and content type filtering.
    """

    def __init__(
        self,
        app: ASGIApp,
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
        self.app = app

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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI3 interface implementation with response compression."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip compression for excluded paths
        path = scope.get("path", "")
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Get client's accepted encodings from headers
        headers = dict(scope.get("headers", []))
        accept_encoding_bytes = headers.get(b"accept-encoding", b"")
        accept_encoding = accept_encoding_bytes.decode("latin-1")

        # Skip if client doesn't support compression
        if not ("gzip" in accept_encoding or "deflate" in accept_encoding):
            await self.app(scope, receive, send)
            return

        # Variables to capture response data
        should_compress = (
            None  # None = not decided, True = compress, False = passthrough
        )
        response_status = 200
        response_headers = {}
        response_body = b""

        # Wrap send to capture response and apply compression
        async def send_wrapper(message):
            nonlocal should_compress, response_status, response_headers, response_body

            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = dict(message.get("headers", []))

                # Skip compression for certain response types
                content_encoding = response_headers.get(
                    b"content-encoding", b""
                ).decode("latin-1")
                cache_control = response_headers.get(b"cache-control", b"").decode(
                    "latin-1"
                )

                # Determine if we should compress
                if (
                    response_status < 200
                    or response_status >= 300
                    or content_encoding
                    or cache_control.startswith("no-transform")
                ):
                    should_compress = False

                # Check content type
                if should_compress is None:
                    content_type_bytes = response_headers.get(b"content-type", b"")
                    content_type = content_type_bytes.decode("latin-1")
                    content_type_main = content_type.split(";")[0].strip()

                    if content_type_main not in self.compressible_types:
                        should_compress = False
                    else:
                        should_compress = True

                # If not compressing, forward the start message immediately
                if not should_compress:
                    await send(message)
                # If compressing, don't send start yet, wait for complete body

            elif message["type"] == "http.response.body":
                if should_compress:
                    # Collect body for compression
                    body_bytes = message.get("body", b"")
                    if isinstance(body_bytes, bytes):
                        response_body += body_bytes

                    # Check if this is the last body message
                    more_body = message.get("more_body", False)
                    if not more_body:
                        # This is the end of the response, now we can compress and send
                        await self._compress_and_send_response(
                            send,
                            response_status,
                            response_headers,
                            response_body,
                            accept_encoding,
                        )
                else:
                    # Not compressing, forward body message as-is
                    await send(message)
            else:
                # Forward other message types as-is
                await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _compress_and_send_response(
        self,
        send: Send,
        status: int,
        headers: dict[bytes, bytes],
        body: bytes,
        accept_encoding: str,
    ):
        """Compress response body and send the complete response."""
        # Skip compression if body is too small
        if len(body) < self.minimum_size:
            # Send original response
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": list(headers.items()),
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )
            return

        # Choose compression algorithm
        compressed_body = None
        encoding = None

        if "gzip" in accept_encoding:
            compressed_body = self._gzip_compress(body)
            encoding = "gzip"
        elif "deflate" in accept_encoding:
            compressed_body = self._deflate_compress(body)
            encoding = "deflate"

        # Only compress if it actually reduces size
        if not compressed_body or len(compressed_body) >= len(body):
            # Send original response
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": list(headers.items()),
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )
            return

        # Update headers for compressed response
        updated_headers = dict(headers)
        updated_headers[b"content-encoding"] = encoding.encode("latin-1")
        updated_headers[b"content-length"] = str(len(compressed_body)).encode("latin-1")
        updated_headers[b"vary"] = b"Accept-Encoding"

        # Send compressed response
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": list(updated_headers.items()),
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": compressed_body,
            }
        )

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
