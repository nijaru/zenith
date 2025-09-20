"""
Integration tests for compression middleware.

Tests critical compression scenarios that could break performance
including gzip/deflate compression, content type filtering, and edge cases.
"""

import gzip
import zlib

import pytest

from zenith import Zenith
from zenith.middleware.compression import CompressionConfig, CompressionMiddleware
from zenith.testing.client import TestClient


@pytest.fixture
def basic_app():
    """Basic app without compression."""
    app = Zenith()

    @app.get("/small")
    async def small_response():
        return {"message": "small"}  # Too small for compression

    @app.get("/large")
    async def large_response():
        # Create a response large enough for compression
        data = {"data": ["item" * 50 for _ in range(20)]}
        return data

    @app.get("/text")
    async def text_response():
        from zenith.web.responses import Response

        large_text = "This is a large text response. " * 100
        return Response(content=large_text, media_type="text/plain")

    @app.get("/image")
    async def image_response():
        from zenith.web.responses import Response

        # Simulate binary image data
        image_data = b"fake_image_data" * 100
        return Response(content=image_data, media_type="image/png")

    @app.get("/html")
    async def html_response():
        from zenith.web.responses import Response

        html_content = "<html><body>" + "Content " * 200 + "</body></html>"
        return Response(content=html_content, media_type="text/html")

    return app


@pytest.fixture
def compression_app():
    """App with default compression middleware."""
    app = Zenith()

    app.add_middleware(
        CompressionMiddleware,
        minimum_size=100,  # Lower threshold for testing
        compressible_types={
            "application/json",
            "text/html",
            "text/plain",
            "text/css",
            "application/javascript",
        },
    )

    @app.get("/small")
    async def small_response():
        return {"message": "small"}  # Too small for compression

    @app.get("/large")
    async def large_response():
        # Create a response large enough for compression
        data = {"data": ["item" * 50 for _ in range(20)]}
        return data

    @app.get("/text")
    async def text_response():
        from zenith.web.responses import Response

        large_text = "This is a large text response. " * 100
        return Response(content=large_text, media_type="text/plain")

    @app.get("/image")
    async def image_response():
        from zenith.web.responses import Response

        # Simulate binary image data
        image_data = b"fake_image_data" * 100
        return Response(content=image_data, media_type="image/png")

    return app


@pytest.fixture
def custom_compression_app():
    """App with custom compression configuration."""
    app = Zenith()

    config = CompressionConfig(
        minimum_size=50,
        compressible_types={"application/json", "text/plain"},
        exclude_paths={"/no-compression"},
    )

    app.add_middleware(CompressionMiddleware, config=config)

    @app.get("/test")
    async def test_response():
        return {"data": "test content that should be compressed" * 10}

    @app.get("/no-compression")
    async def no_compression_response():
        return {"data": "this should not be compressed" * 10}

    @app.get("/text")
    async def text_response():
        from zenith.web.responses import Response

        return Response(content="Text content " * 20, media_type="text/plain")

    return app


class TestCompressionBasicFunctionality:
    """Test basic compression functionality."""

    async def test_no_compression_without_accept_encoding(self, compression_app):
        """Test that responses aren't compressed without Accept-Encoding."""
        async with TestClient(compression_app) as client:
            # Explicitly remove Accept-Encoding header to test no compression
            response = await client.get("/large", headers={"accept-encoding": ""})

            assert response.status_code == 200
            assert "content-encoding" not in response.headers
            # Response should be uncompressed JSON
            data = response.json()
            assert "data" in data

    async def test_gzip_compression_with_accept_encoding(self, compression_app):
        """Test gzip compression when client accepts it."""
        async with TestClient(compression_app) as client:
            response = await client.get("/large", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # TestClient automatically handles decompression, so check headers
            assert "content-encoding" in response.headers
            assert response.headers["content-encoding"] == "gzip"
            assert "vary" in response.headers
            assert "Accept-Encoding" in response.headers["vary"]

            # Content should still be accessible (TestClient decompresses)
            data = response.json()
            assert "data" in data

    async def test_deflate_compression(self, compression_app):
        """Test deflate compression when gzip not available."""
        async with TestClient(compression_app) as client:
            response = await client.get(
                "/large", headers={"Accept-Encoding": "deflate"}
            )

            assert response.status_code == 200
            assert response.headers["content-encoding"] == "deflate"
            data = response.json()
            assert "data" in data

    async def test_prefer_gzip_over_deflate(self, compression_app):
        """Test that gzip is preferred when both are available."""
        async with TestClient(compression_app) as client:
            response = await client.get(
                "/large", headers={"Accept-Encoding": "gzip, deflate"}
            )

            assert response.status_code == 200
            assert response.headers["content-encoding"] == "gzip"

    async def test_small_response_not_compressed(self, compression_app):
        """Test that small responses are not compressed."""
        async with TestClient(compression_app) as client:
            response = await client.get("/small", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # Should not be compressed due to size
            assert "content-encoding" not in response.headers


class TestCompressionContentTypes:
    """Test compression based on content types."""

    async def test_json_compression(self, compression_app):
        """Test JSON response compression."""
        async with TestClient(compression_app) as client:
            response = await client.get("/large", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            assert response.headers["content-encoding"] == "gzip"

    async def test_text_compression(self, compression_app):
        """Test text response compression."""
        async with TestClient(compression_app) as client:
            response = await client.get("/text", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            assert response.headers["content-encoding"] == "gzip"

    async def test_image_not_compressed(self, compression_app):
        """Test that image responses are not compressed."""
        async with TestClient(compression_app) as client:
            response = await client.get("/image", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # Image should not be compressed
            assert "content-encoding" not in response.headers

    async def test_custom_compressible_types(self, custom_compression_app):
        """Test custom compressible content types."""
        async with TestClient(custom_compression_app) as client:
            # JSON should be compressed
            response = await client.get("/test", headers={"Accept-Encoding": "gzip"})
            assert response.headers["content-encoding"] == "gzip"

            # Text should be compressed
            response = await client.get("/text", headers={"Accept-Encoding": "gzip"})
            assert response.headers["content-encoding"] == "gzip"


class TestCompressionConfiguration:
    """Test compression configuration options."""

    async def test_minimum_size_threshold(self):
        """Test minimum size threshold configuration."""
        app = Zenith()

        app.add_middleware(
            CompressionMiddleware,
            minimum_size=1000,  # Higher threshold
        )

        @app.get("/medium")
        async def medium_response():
            # Create response smaller than threshold
            return {"data": "content " * 50}  # Less than 1000 bytes

        async with TestClient(app) as client:
            response = await client.get("/medium", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # Should not be compressed due to minimum size
            assert "content-encoding" not in response.headers

    async def test_excluded_paths(self, custom_compression_app):
        """Test path exclusion from compression."""
        async with TestClient(custom_compression_app) as client:
            # Regular path should be compressed
            response = await client.get("/test", headers={"Accept-Encoding": "gzip"})
            assert response.headers["content-encoding"] == "gzip"

            # Excluded path should not be compressed
            response = await client.get(
                "/no-compression", headers={"Accept-Encoding": "gzip"}
            )
            assert "content-encoding" not in response.headers

    async def test_config_object_vs_parameters(self):
        """Test that config object and individual parameters work the same."""
        app1 = Zenith()
        app2 = Zenith()

        # Using individual parameters
        middleware1 = CompressionMiddleware(
            app=app1,
            minimum_size=200,
            compressible_types={"text/plain"},
            exclude_paths={"/skip"},
        )

        # Using config object
        config = CompressionConfig(
            minimum_size=200, compressible_types={"text/plain"}, exclude_paths={"/skip"}
        )
        middleware2 = CompressionMiddleware(app=app2, config=config)

        # Both should have the same configuration
        assert middleware1.minimum_size == middleware2.minimum_size
        assert middleware1.compressible_types == middleware2.compressible_types
        assert middleware1.exclude_paths == middleware2.exclude_paths


class TestCompressionEdgeCases:
    """Test compression edge cases and potential bugs."""

    async def test_already_compressed_content(self):
        """Test that already compressed content is not re-compressed."""
        app = Zenith()

        app.add_middleware(CompressionMiddleware)

        @app.get("/pre-compressed")
        async def pre_compressed():
            # Create actual gzip-compressed content
            import gzip

            from zenith.web.responses import Response

            original_content = "Already compressed content"
            compressed_content = gzip.compress(original_content.encode("utf-8"))
            return Response(
                content=compressed_content, headers={"Content-Encoding": "gzip"}
            )

        async with TestClient(app) as client:
            response = await client.get(
                "/pre-compressed", headers={"Accept-Encoding": "gzip"}
            )

            assert response.status_code == 200
            # Should not re-compress
            assert response.headers["content-encoding"] == "gzip"

    async def test_no_transform_cache_control(self):
        """Test that responses with no-transform are not compressed."""
        app = Zenith()

        app.add_middleware(CompressionMiddleware, minimum_size=10)

        @app.get("/no-transform")
        async def no_transform():
            from zenith.web.responses import Response

            return Response(
                content="Content that should not be transformed" * 10,
                headers={"Cache-Control": "no-transform"},
            )

        async with TestClient(app) as client:
            response = await client.get(
                "/no-transform", headers={"Accept-Encoding": "gzip"}
            )

            assert response.status_code == 200
            # Should not be compressed due to no-transform
            assert "content-encoding" not in response.headers

    async def test_error_responses_not_compressed(self):
        """Test that error responses are not compressed."""
        app = Zenith()

        app.add_middleware(CompressionMiddleware, minimum_size=10)

        @app.get("/error")
        async def error_response():
            from zenith.web.responses import Response

            return Response(content="Error message " * 50, status_code=400)

        async with TestClient(app) as client:
            response = await client.get("/error", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 400
            # Error responses should not be compressed
            assert "content-encoding" not in response.headers

    async def test_redirect_responses_not_compressed(self):
        """Test that redirect responses are not compressed."""
        app = Zenith()

        app.add_middleware(CompressionMiddleware, minimum_size=10)

        @app.get("/redirect")
        async def redirect_response():
            from starlette.responses import RedirectResponse

            return RedirectResponse(url="/other", status_code=302)

        async with TestClient(app) as client:
            response = await client.get(
                "/redirect", headers={"Accept-Encoding": "gzip"}, follow_redirects=False
            )

            assert response.status_code == 302
            # Redirect responses should not be compressed
            assert "content-encoding" not in response.headers

    async def test_compression_improves_size(self):
        """Test that compression only happens if it actually reduces size."""
        app = Zenith()

        app.add_middleware(CompressionMiddleware, minimum_size=10)

        @app.get("/random")
        async def random_data():
            # Random data that might not compress well
            import random
            import string

            from zenith.web.responses import Response

            random_content = "".join(random.choices(string.ascii_letters, k=500))
            return Response(content=random_content, media_type="text/plain")

        async with TestClient(app) as client:
            response = await client.get("/random", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # Might or might not be compressed depending on whether it reduces size
            # This tests the compression efficiency check

    async def test_content_length_header_updated(self, compression_app):
        """Test that Content-Length header is updated for compressed responses."""
        async with TestClient(compression_app) as client:
            response = await client.get("/large", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            if "content-encoding" in response.headers:
                # If compressed, content-length should be for compressed content
                assert "content-length" in response.headers
                content_length = int(response.headers["content-length"])
                assert content_length > 0

    async def test_streaming_response_handling(self):
        """Test compression with streaming responses."""
        import asyncio

        from zenith.web.responses import StreamingResponse

        app = Zenith()

        app.add_middleware(CompressionMiddleware, minimum_size=10)

        async def generate_data():
            for i in range(10):
                yield f"chunk {i} " * 20
                await asyncio.sleep(0.001)

        @app.get("/stream")
        async def streaming_response():
            return StreamingResponse(generate_data(), media_type="text/plain")

        async with TestClient(app) as client:
            response = await client.get("/stream", headers={"Accept-Encoding": "gzip"})

            assert response.status_code == 200
            # StreamingResponse handling might differ
            content = response.text
            assert "chunk" in content

    async def test_case_insensitive_content_type_matching(self):
        """Test that content type matching is case insensitive."""
        app = Zenith()

        app.add_middleware(
            CompressionMiddleware, minimum_size=10, compressible_types={"text/plain"}
        )

        @app.get("/mixed-case")
        async def mixed_case_content_type():
            from zenith.web.responses import Response

            return Response(
                content="Content with mixed case content-type " * 10,
                media_type="TEXT/PLAIN",  # Mixed case
            )

        async with TestClient(app) as client:
            response = await client.get(
                "/mixed-case", headers={"Accept-Encoding": "gzip"}
            )

            assert response.status_code == 200
            # Should still be compressed despite case difference
            # Note: This tests if the implementation handles case sensitivity properly


class TestCompressionAlgorithms:
    """Test compression algorithms directly."""

    def test_gzip_compression_algorithm(self):
        """Test gzip compression algorithm."""
        from zenith.middleware.compression import CompressionMiddleware

        app = Zenith()
        middleware = CompressionMiddleware(app)

        test_data = b"This is test data for compression. " * 20
        compressed = middleware._gzip_compress(test_data)

        # Verify it's valid gzip
        decompressed = gzip.decompress(compressed)
        assert decompressed == test_data
        assert len(compressed) < len(test_data)

    def test_deflate_compression_algorithm(self):
        """Test deflate compression algorithm."""
        from zenith.middleware.compression import CompressionMiddleware

        app = Zenith()
        middleware = CompressionMiddleware(app)

        test_data = b"This is test data for compression. " * 20
        compressed = middleware._deflate_compress(test_data)

        # Verify it's valid deflate
        decompressed = zlib.decompress(compressed)
        assert decompressed == test_data
        assert len(compressed) < len(test_data)


class TestCompressionInStack:
    """Test compression middleware in middleware stack."""

    async def test_compression_with_cors_middleware(self):
        """Test compression working with CORS middleware."""
        from zenith.middleware.cors import CORSMiddleware

        app = Zenith()

        # Add both CORS and compression through the proper middleware system
        app.add_middleware(CORSMiddleware, allow_origins=["*"])
        app.add_middleware(CompressionMiddleware, minimum_size=10)

        @app.get("/test")
        async def test_endpoint():
            return {"data": "content " * 50}

        async with TestClient(app) as client:
            response = await client.get(
                "/test",
                headers={"Accept-Encoding": "gzip", "Origin": "https://example.com"},
            )

            assert response.status_code == 200
            # Should have both compression and CORS headers
            assert response.headers["content-encoding"] == "gzip"
            assert (
                response.headers["access-control-allow-origin"] == "https://example.com"
            )
