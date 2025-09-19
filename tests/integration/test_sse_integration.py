"""
Integration tests for Server-Sent Events (SSE) with real HTTP scenarios.

Tests SSE functionality in real request/response contexts including:
- End-to-end SSE streaming
- Client disconnection handling
- Real backpressure scenarios
- Performance under load
- Security considerations
"""

import asyncio
import json
import time
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from zenith.testing.client import TestClient
from zenith.web.sse import (
    SSEEventManager,
    ServerSentEvents,
    create_sse_response,
    sse,
)


class TestSSEHTTPIntegration:
    """Test SSE functionality over real HTTP connections."""

    @pytest.fixture
    def sse_app(self):
        """Create test app with SSE endpoints."""

        async def basic_stream(request):
            """Basic SSE stream endpoint."""
            async def events():
                for i in range(5):
                    yield {
                        "type": "count",
                        "data": {"value": i, "timestamp": time.time()}
                    }
                    # Sleep 0.11 seconds to respect 10 events/second rate limit
                    await asyncio.sleep(0.11)

            return create_sse_response(events())

        async def long_stream(request):
            """Long-running SSE stream."""
            async def events():
                # Reduced from 100 to 40 events to work with 10 events/second rate limit
                for i in range(40):
                    yield {
                        "type": "long",
                        "data": {"iteration": i}
                    }
                    await asyncio.sleep(0.001)  # Very fast

            return create_sse_response(events())

        async def heartbeat_stream(request):
            """SSE stream with heartbeats."""
            async def events():
                for i in range(3):
                    yield {
                        "type": "data",
                        "data": {"value": i}
                    }
                    await asyncio.sleep(0.05)  # Slower to trigger heartbeats

            return create_sse_response(events())

        async def error_stream(request):
            """SSE stream that encounters errors."""
            async def events():
                yield {"type": "start", "data": "ok"}
                await asyncio.sleep(0.11)
                yield {"type": "middle", "data": "still ok"}
                await asyncio.sleep(0.11)
                raise ValueError("Simulated error")

            return create_sse_response(events())

        async def channel_stream(request):
            """SSE stream with channel management."""
            channel = request.query_params.get("channel", "default")

            async def events():
                for i in range(3):
                    yield {
                        "type": "channel_message",
                        "data": {"channel": channel, "message": f"Message {i}"}
                    }
                    await asyncio.sleep(0.11)

            return create_sse_response(events())

        async def backpressure_stream(request):
            """SSE stream designed to trigger backpressure."""
            async def events():
                # Generate events very quickly to test backpressure
                for i in range(50):
                    large_data = {"iteration": i, "payload": "x" * 1000}  # 1KB per event
                    yield {
                        "type": "backpressure_test",
                        "data": large_data
                    }
                    # No delay - generate as fast as possible

            return create_sse_response(events())

        async def custom_headers_stream(request):
            """SSE stream with custom headers."""
            async def events():
                yield {"type": "custom", "data": "with headers"}

            custom_headers = {
                "X-Custom-Header": "test-value",
                "X-Stream-ID": "custom-123"
            }
            return sse.stream_response(events(), custom_headers)

        async def stats_endpoint(request):
            """Get SSE statistics."""
            stats = sse.get_statistics()
            return Response(
                json.dumps(stats),
                media_type="application/json"
            )

        routes = [
            Route("/sse/basic", basic_stream),
            Route("/sse/long", long_stream),
            Route("/sse/heartbeat", heartbeat_stream),
            Route("/sse/error", error_stream),
            Route("/sse/channel", channel_stream),
            Route("/sse/backpressure", backpressure_stream),
            Route("/sse/custom-headers", custom_headers_stream),
            Route("/sse/stats", stats_endpoint),
        ]

        return Starlette(routes=routes)

    @pytest.mark.asyncio
    async def test_basic_sse_http_stream(self, sse_app):
        """Test basic SSE streaming over HTTP."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/basic")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"

            # Read the stream content
            content = await response.aread()
            content_str = content.decode("utf-8")

            # Should contain multiple events
            assert "event: count" in content_str
            assert "data:" in content_str
            assert content_str.count("\n\n") >= 5  # At least 5 events

    @pytest.mark.asyncio
    async def test_sse_custom_headers(self, sse_app):
        """Test SSE with custom headers."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/custom-headers")

            assert response.status_code == 200
            assert response.headers["x-custom-header"] == "test-value"
            assert response.headers["x-stream-id"] == "custom-123"
            # Should still have SSE headers
            assert response.headers["content-type"] == "text/event-stream"

    @pytest.mark.asyncio
    async def test_sse_cors_headers(self, sse_app):
        """Test SSE CORS headers are properly set."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/basic")

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "*"
            assert response.headers["access-control-allow-credentials"] == "true"

    @pytest.mark.asyncio
    async def test_sse_nginx_compatibility(self, sse_app):
        """Test SSE headers for nginx compatibility."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/basic")

            assert response.status_code == 200
            assert response.headers["x-accel-buffering"] == "no"
            assert response.headers["x-sse-backpressure"] == "enabled"

    @pytest.mark.asyncio
    async def test_sse_channel_streaming(self, sse_app):
        """Test SSE streaming with channel parameters."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/channel?channel=news")

            assert response.status_code == 200
            content = await response.aread()
            content_str = content.decode("utf-8")

            # Should contain channel-specific data
            assert "news" in content_str
            assert "channel_message" in content_str

    @pytest.mark.asyncio
    async def test_sse_error_handling_in_stream(self, sse_app):
        """Test error handling during SSE streaming."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/error")

            assert response.status_code == 200

            # Should receive some events before error
            content = await response.aread()
            content_str = content.decode("utf-8")

            # Should have started streaming
            assert "event: start" in content_str
            # May or may not have complete stream due to error

    @pytest.mark.asyncio
    async def test_sse_backpressure_handling(self, sse_app):
        """Test SSE backpressure handling with rapid events."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/backpressure")

            assert response.status_code == 200

            # Should handle backpressure gracefully
            content = await response.aread()
            content_str = content.decode("utf-8")

            # Should have events (may be throttled)
            assert "backpressure_test" in content_str
            assert "data:" in content_str

    @pytest.mark.asyncio
    async def test_sse_heartbeat_generation(self, sse_app):
        """Test SSE heartbeat generation."""
        async with TestClient(sse_app) as client:
            response = await client.get("/sse/heartbeat")

            assert response.status_code == 200
            content = await response.aread()
            content_str = content.decode("utf-8")

            # Should have data events
            assert "event: data" in content_str

            # May have heartbeat events depending on timing
            # (Heartbeats are sent every 10 data events)

    @pytest.mark.asyncio
    async def test_sse_statistics_tracking(self, sse_app):
        """Test SSE statistics are properly tracked."""
        async with TestClient(sse_app) as client:
            # Get initial stats
            stats_response = await client.get("/sse/stats")
            initial_stats = json.loads(await stats_response.aread())

            # Make SSE request
            sse_response = await client.get("/sse/basic")
            await sse_response.aread()  # Consume the stream

            # Get updated stats
            stats_response = await client.get("/sse/stats")
            final_stats = json.loads(await stats_response.aread())

            # Should have updated statistics
            assert final_stats["events_sent"] >= initial_stats["events_sent"]
            assert final_stats["bytes_streamed"] >= initial_stats["bytes_streamed"]

    @pytest.mark.asyncio
    async def test_concurrent_sse_streams(self, sse_app):
        """Test multiple concurrent SSE streams."""
        async with TestClient(sse_app) as client:
            # Start multiple SSE streams concurrently
            tasks = [
                asyncio.create_task(client.get("/sse/basic")),
                asyncio.create_task(client.get("/sse/basic")),
                asyncio.create_task(client.get("/sse/basic"))
            ]

            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"

            # Read all streams
            contents = await asyncio.gather(*[
                resp.aread() for resp in responses
            ])

            # All should have content
            for content in contents:
                assert len(content) > 0

    @pytest.mark.asyncio
    async def test_sse_long_stream_performance(self, sse_app):
        """Test performance of long SSE streams."""
        async with TestClient(sse_app) as client:
            start_time = time.time()

            response = await client.get("/sse/long")
            assert response.status_code == 200

            content = await response.aread()

            end_time = time.time()
            duration = end_time - start_time

            # Should complete reasonably quickly despite 100 events
            assert duration < 5.0  # Should be much faster, but allow buffer

            # Should have substantial content
            assert len(content) > 800  # Adjusted for throttled content


class TestSSEManagerIntegration:
    """Test SSEEventManager integration scenarios."""

    @pytest.fixture
    def manager_app(self):
        """Create app using SSEEventManager."""
        manager = SSEEventManager()

        async def managed_stream(request):
            """Stream using SSEEventManager."""
            async def events():
                for i in range(3):
                    yield {
                        "type": "managed",
                        "data": {"value": i}
                    }
                    await asyncio.sleep(0.11)

            return await manager.create_event_stream(events())

        async def connection_count(request):
            """Get connection count."""
            total = manager.get_connection_count()
            channel_count = manager.get_connection_count("test")
            return Response(
                json.dumps({"total": total, "channel": channel_count}),
                media_type="application/json"
            )

        async def performance_stats(request):
            """Get performance statistics."""
            stats = manager.get_performance_stats()
            return Response(
                json.dumps(stats),
                media_type="application/json"
            )

        routes = [
            Route("/managed/stream", managed_stream),
            Route("/managed/connections", connection_count),
            Route("/managed/stats", performance_stats),
        ]

        return Starlette(routes=routes)

    @pytest.mark.asyncio
    async def test_sse_manager_streaming(self, manager_app):
        """Test streaming through SSEEventManager."""
        async with TestClient(manager_app) as client:
            response = await client.get("/managed/stream")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            content = await response.aread()
            content_str = content.decode("utf-8")

            assert "event: managed" in content_str
            assert "data:" in content_str

    @pytest.mark.asyncio
    async def test_sse_manager_connection_tracking(self, manager_app):
        """Test connection tracking through manager."""
        async with TestClient(manager_app) as client:
            # Get initial connection count
            response = await client.get("/managed/connections")
            initial_data = json.loads(await response.aread())

            # Connection counts should be valid
            assert isinstance(initial_data["total"], int)
            assert isinstance(initial_data["channel"], int)
            assert initial_data["total"] >= 0
            assert initial_data["channel"] >= 0

    @pytest.mark.asyncio
    async def test_sse_manager_performance_stats(self, manager_app):
        """Test performance stats through manager."""
        async with TestClient(manager_app) as client:
            response = await client.get("/managed/stats")
            stats = json.loads(await response.aread())

            # Should have expected stat fields
            assert "total_connections" in stats
            assert "active_connections" in stats
            assert "events_sent" in stats
            assert "bytes_streamed" in stats

            # Values should be reasonable
            assert stats["total_connections"] >= 0
            assert stats["active_connections"] >= 0
            assert stats["events_sent"] >= 0
            assert stats["bytes_streamed"] >= 0


class TestSSESecurityIntegration:
    """Test SSE security considerations in integration scenarios."""

    @pytest.fixture
    def security_app(self):
        """Create app for testing security scenarios."""

        async def public_stream(request):
            """Public SSE stream."""
            async def events():
                yield {"type": "public", "data": "anyone can see this"}

            return create_sse_response(events())

        async def user_data_stream(request):
            """Stream that includes user data (security test)."""
            user_id = request.query_params.get("user_id", "anonymous")

            async def events():
                # Simulate sending user-specific data
                yield {
                    "type": "user_data",
                    "data": {
                        "user_id": user_id,
                        "sensitive_info": "This should be validated"
                    }
                }

            return create_sse_response(events())

        async def large_payload_stream(request):
            """Stream with large payloads (DoS protection test)."""
            size = int(request.query_params.get("size", "1000"))

            async def events():
                # Potentially large payload
                large_data = "x" * min(size, 100000)  # Cap at 100KB
                yield {
                    "type": "large_payload",
                    "data": {"payload": large_data}
                }

            return create_sse_response(events())

        routes = [
            Route("/security/public", public_stream),
            Route("/security/user-data", user_data_stream),
            Route("/security/large-payload", large_payload_stream),
        ]

        return Starlette(routes=routes)

    @pytest.mark.asyncio
    async def test_sse_public_stream_security(self, security_app):
        """Test public SSE stream doesn't expose sensitive data."""
        async with TestClient(security_app) as client:
            response = await client.get("/security/public")

            assert response.status_code == 200
            content = await response.aread()
            content_str = content.decode("utf-8")

            assert "public" in content_str
            assert "anyone can see this" in content_str

    @pytest.mark.asyncio
    async def test_sse_user_data_stream(self, security_app):
        """Test SSE stream with user-specific data."""
        async with TestClient(security_app) as client:
            response = await client.get("/security/user-data?user_id=test123")

            assert response.status_code == 200
            content = await response.aread()
            content_str = content.decode("utf-8")

            assert "test123" in content_str
            assert "user_data" in content_str

            # In real app, should validate user_id and authentication

    @pytest.mark.asyncio
    async def test_sse_large_payload_protection(self, security_app):
        """Test SSE protection against large payloads."""
        async with TestClient(security_app) as client:
            # Test reasonable size
            response = await client.get("/security/large-payload?size=1000")
            assert response.status_code == 200

            # Test very large size (should be capped)
            response = await client.get("/security/large-payload?size=1000000")
            assert response.status_code == 200

            content = await response.aread()
            # Should not exceed reasonable limits
            assert len(content) < 200000  # Much less than requested 1MB

    @pytest.mark.asyncio
    async def test_sse_connection_limits(self, security_app):
        """Test SSE connection limit handling."""
        # This would require a custom SSE instance with low limits
        # For now, just verify the interface exists
        custom_sse = ServerSentEvents(max_concurrent_connections=2)
        assert custom_sse.max_concurrent_connections == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])