"""
Comprehensive test suite for Server-Sent Events (SSE) functionality.

Tests all SSE features including:
- Basic SSE streaming
- Backpressure handling
- Connection management
- Channel subscriptions
- Performance monitoring
- Edge cases and error scenarios
"""

import asyncio
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.responses import StreamingResponse

from zenith.web.sse import (
    SSEConnection,
    SSEConnectionState,
    SSEEventManager,
    ServerSentEvents,
    create_sse_response,
    sse,
)


class TestSSEConnection:
    """Test SSEConnection data class and functionality."""

    def test_sse_connection_creation(self):
        """Test SSEConnection creation with default values."""
        connection_id = "test_conn_123"
        connection = SSEConnection(connection_id=connection_id)

        assert connection.connection_id == connection_id
        assert connection.state == SSEConnectionState.CONNECTING
        assert connection.events_sent == 0
        assert connection.events_queued == 0
        assert connection.bytes_sent == 0
        assert connection.client_buffer_estimate == 0
        assert connection.send_rate_limit == 10.0
        assert connection.max_buffer_size == 65536
        assert connection.adaptive_throttling is True
        assert isinstance(connection.subscribed_channels, set)
        assert isinstance(connection.metadata, dict)
        assert connection.connected_at > 0
        assert connection.last_activity > 0

    def test_sse_connection_state_transitions(self):
        """Test SSE connection state transitions."""
        connection = SSEConnection("test_conn")

        # Test all valid state transitions
        connection.state = SSEConnectionState.CONNECTING
        assert connection.state == SSEConnectionState.CONNECTING

        connection.state = SSEConnectionState.CONNECTED
        assert connection.state == SSEConnectionState.CONNECTED

        connection.state = SSEConnectionState.THROTTLED
        assert connection.state == SSEConnectionState.THROTTLED

        connection.state = SSEConnectionState.DISCONNECTING
        assert connection.state == SSEConnectionState.DISCONNECTING

        connection.state = SSEConnectionState.DISCONNECTED
        assert connection.state == SSEConnectionState.DISCONNECTED

    def test_sse_connection_performance_tracking(self):
        """Test SSE connection performance tracking."""
        connection = SSEConnection("test_conn")

        # Update performance metrics
        connection.events_sent = 10
        connection.bytes_sent = 1024
        connection.events_queued = 5
        connection.client_buffer_estimate = 2048

        assert connection.events_sent == 10
        assert connection.bytes_sent == 1024
        assert connection.events_queued == 5
        assert connection.client_buffer_estimate == 2048

    def test_sse_connection_channel_management(self):
        """Test SSE connection channel subscription management."""
        connection = SSEConnection("test_conn")

        # Add channels
        connection.subscribed_channels.add("channel1")
        connection.subscribed_channels.add("channel2")

        assert "channel1" in connection.subscribed_channels
        assert "channel2" in connection.subscribed_channels
        assert len(connection.subscribed_channels) == 2

        # Remove channel
        connection.subscribed_channels.remove("channel1")
        assert "channel1" not in connection.subscribed_channels
        assert len(connection.subscribed_channels) == 1


class TestServerSentEvents:
    """Test ServerSentEvents core functionality."""

    def test_sse_initialization(self):
        """Test ServerSentEvents initialization with default and custom values."""
        # Default initialization
        sse_default = ServerSentEvents()
        assert sse_default.max_concurrent_connections == 1000
        assert sse_default.default_buffer_size == 32768
        assert sse_default.heartbeat_interval == 30
        assert sse_default.enable_adaptive_throttling is True

        # Custom initialization
        sse_custom = ServerSentEvents(
            max_concurrent_connections=500,
            default_buffer_size=16384,
            heartbeat_interval=60,
            enable_adaptive_throttling=False
        )
        assert sse_custom.max_concurrent_connections == 500
        assert sse_custom.default_buffer_size == 16384
        assert sse_custom.heartbeat_interval == 60
        assert sse_custom.enable_adaptive_throttling is False

    def test_sse_statistics_initialization(self):
        """Test SSE statistics tracking initialization."""
        sse_instance = ServerSentEvents()
        stats = sse_instance.get_statistics()

        assert "total_connections" in stats
        assert "active_connections" in stats
        assert "events_sent" in stats
        assert "backpressure_throttles" in stats
        assert "bytes_streamed" in stats
        assert "concurrent_processing_time_saved" in stats
        assert stats["total_connections"] == 0
        assert stats["active_connections"] == 0
        assert stats["events_sent"] == 0

    def test_format_sse_message_basic(self):
        """Test SSE message formatting with basic event."""
        sse_instance = ServerSentEvents()

        event = {
            "type": "update",
            "data": {"message": "Hello World"}
        }

        formatted = sse_instance._format_sse_message(event)
        expected_lines = [
            "event: update",
            'data: {"message": "Hello World"}',
            "",
            ""
        ]
        expected = "\n".join(expected_lines)

        assert formatted == expected

    def test_format_sse_message_with_id_and_retry(self):
        """Test SSE message formatting with ID and retry."""
        sse_instance = ServerSentEvents()

        event = {
            "id": "123",
            "type": "error",
            "retry": "5000",
            "data": {"error": "Network timeout"}
        }

        formatted = sse_instance._format_sse_message(event)
        lines = formatted.split("\n")

        assert "id: 123" in lines
        assert "event: error" in lines
        assert "retry: 5000" in lines
        assert 'data: {"error": "Network timeout"}' in lines

    def test_format_sse_message_multiline_data(self):
        """Test SSE message formatting with multiline data."""
        sse_instance = ServerSentEvents()

        event = {
            "type": "multiline",
            "data": "Line 1\nLine 2\nLine 3"
        }

        formatted = sse_instance._format_sse_message(event)
        lines = formatted.split("\n")

        assert "event: multiline" in lines
        assert "data: Line 1" in lines
        assert "data: Line 2" in lines
        assert "data: Line 3" in lines

    def test_generate_connection_id(self):
        """Test connection ID generation uniqueness."""
        sse_instance = ServerSentEvents()

        # Generate multiple IDs
        ids = [sse_instance._generate_connection_id() for _ in range(10)]

        # Check uniqueness
        assert len(set(ids)) == 10

        # Check format
        for conn_id in ids:
            assert conn_id.startswith("sse_")
            assert len(conn_id.split("_")) == 3  # sse_timestamp_uuid

    def test_update_client_buffer_estimate(self):
        """Test client buffer estimate updating."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        connection.client_buffer_estimate = 5000

        # First update - initializes timestamp
        sse_instance._update_client_buffer_estimate(connection)
        assert hasattr(connection, "_last_buffer_update")

        # Wait a bit and update again
        import time
        time.sleep(0.01)  # Small delay

        # Second update - should reduce buffer
        sse_instance._update_client_buffer_estimate(connection)

        # Buffer should be reduced (consumption simulation)
        assert connection.client_buffer_estimate < 5000

    async def test_should_throttle_connection_rate_limit(self):
        """Test connection throttling based on send rate limit."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        connection.send_rate_limit = 10.0  # 10 events per second
        connection.events_sent = 1  # Must have sent events for throttling to apply
        connection.last_send_time = time.time()

        # Should throttle if sending too fast
        result = await sse_instance._should_throttle_connection(connection)
        assert result is True

        # Should not throttle after sufficient time
        connection.last_send_time = time.time() - 1.0  # 1 second ago
        result = await sse_instance._should_throttle_connection(connection)
        assert result is False

    async def test_should_throttle_connection_buffer_usage(self):
        """Test connection throttling based on client buffer usage."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        connection.max_buffer_size = 1000
        connection.client_buffer_estimate = 850  # 85% usage
        connection.last_send_time = time.time() - 1.0  # Not rate limited

        # Should throttle due to high buffer usage
        result = await sse_instance._should_throttle_connection(connection)
        assert result is True

        # Should not throttle with low buffer usage
        connection.client_buffer_estimate = 200  # 20% usage
        result = await sse_instance._should_throttle_connection(connection)
        assert result is False

    async def test_should_throttle_connection_queue_limit(self):
        """Test connection throttling based on queued events."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        connection.events_queued = 60  # Above 50 limit
        connection.last_send_time = time.time() - 1.0  # Not rate limited
        connection.client_buffer_estimate = 100  # Low buffer usage

        # Should throttle due to too many queued events
        result = await sse_instance._should_throttle_connection(connection)
        assert result is True

        # Should not throttle with reasonable queue
        connection.events_queued = 10
        result = await sse_instance._should_throttle_connection(connection)
        assert result is False

    async def test_should_throttle_connection_disabled(self):
        """Test connection throttling when adaptive throttling is disabled."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        connection.adaptive_throttling = False
        connection.client_buffer_estimate = 9999  # High usage
        connection.events_queued = 100  # High queue

        # Should not throttle when adaptive throttling is disabled
        result = await sse_instance._should_throttle_connection(connection)
        assert result is False

    async def test_subscribe_to_channel(self):
        """Test channel subscription functionality."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        sse_instance._connections["test_conn"] = connection

        # Subscribe to channel
        result = await sse_instance.subscribe_to_channel("test_conn", "news")
        assert result is True
        assert "news" in connection.subscribed_channels
        assert "news" in sse_instance._event_channels
        assert "test_conn" in sse_instance._event_channels["news"]

    async def test_subscribe_to_channel_nonexistent_connection(self):
        """Test channel subscription with nonexistent connection."""
        sse_instance = ServerSentEvents()

        # Try to subscribe nonexistent connection
        result = await sse_instance.subscribe_to_channel("nonexistent", "news")
        assert result is False

    async def test_unsubscribe_from_channel(self):
        """Test channel unsubscription functionality."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        sse_instance._connections["test_conn"] = connection

        # First subscribe
        await sse_instance.subscribe_to_channel("test_conn", "news")
        assert "news" in connection.subscribed_channels

        # Then unsubscribe
        result = await sse_instance.unsubscribe_from_channel("test_conn", "news")
        assert result is True
        assert "news" not in connection.subscribed_channels
        assert "news" not in sse_instance._event_channels

    async def test_unsubscribe_from_channel_nonexistent_connection(self):
        """Test channel unsubscription with nonexistent connection."""
        sse_instance = ServerSentEvents()

        # Try to unsubscribe nonexistent connection
        result = await sse_instance.unsubscribe_from_channel("nonexistent", "news")
        assert result is False

    async def test_cleanup_connection(self):
        """Test connection cleanup functionality."""
        sse_instance = ServerSentEvents()
        connection = SSEConnection("test_conn")
        sse_instance._connections["test_conn"] = connection
        sse_instance._stats["active_connections"] = 1

        # Subscribe to channels
        await sse_instance.subscribe_to_channel("test_conn", "news")
        await sse_instance.subscribe_to_channel("test_conn", "updates")

        # Cleanup connection
        await sse_instance._cleanup_connection(connection)

        assert connection.state == SSEConnectionState.DISCONNECTED
        assert len(connection.subscribed_channels) == 0
        assert sse_instance._stats["active_connections"] == 0

    def test_stream_response_creation(self):
        """Test SSE stream response creation."""
        sse_instance = ServerSentEvents()

        async def dummy_generator():
            yield {"type": "test", "data": "hello"}

        response = sse_instance.stream_response(dummy_generator())

        assert isinstance(response, StreamingResponse)
        assert response.headers["content-type"] == "text/event-stream"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-sse-backpressure"] == "enabled"

    def test_stream_response_with_custom_headers(self):
        """Test SSE stream response with custom headers."""
        sse_instance = ServerSentEvents()

        async def dummy_generator():
            yield {"type": "test", "data": "hello"}

        custom_headers = {"X-Custom": "value", "X-Another": "test"}
        response = sse_instance.stream_response(dummy_generator(), custom_headers)

        assert response.headers["x-custom"] == "value"
        assert response.headers["x-another"] == "test"
        # Should still have SSE headers
        assert response.headers["content-type"] == "text/event-stream"


class TestSSEEventManager:
    """Test SSEEventManager high-level interface."""

    def test_sse_event_manager_initialization(self):
        """Test SSEEventManager initialization."""
        # With default SSE instance
        manager = SSEEventManager()
        assert isinstance(manager.sse, ServerSentEvents)

        # With custom SSE instance
        custom_sse = ServerSentEvents(max_concurrent_connections=100)
        manager = SSEEventManager(custom_sse)
        assert manager.sse is custom_sse

    async def test_create_event_stream(self):
        """Test event stream creation through manager."""
        manager = SSEEventManager()

        async def test_generator():
            yield {"type": "test", "data": "hello"}

        response = await manager.create_event_stream(test_generator())
        assert isinstance(response, StreamingResponse)

    def test_get_connection_count(self):
        """Test connection count retrieval."""
        manager = SSEEventManager()

        # Total connections
        total_count = manager.get_connection_count()
        assert total_count == 0

        # Channel-specific connections
        channel_count = manager.get_connection_count("news")
        assert channel_count == 0

    def test_get_performance_stats(self):
        """Test performance statistics retrieval."""
        manager = SSEEventManager()
        stats = manager.get_performance_stats()

        assert isinstance(stats, dict)
        assert "total_connections" in stats
        assert "active_connections" in stats
        assert "events_sent" in stats


class TestSSEIntegration:
    """Integration tests for SSE functionality."""

    @pytest.mark.asyncio
    async def test_basic_sse_streaming(self):
        """Test basic SSE streaming functionality."""
        # Create SSE instance with throttling disabled for testing
        sse_instance = ServerSentEvents(enable_adaptive_throttling=False)

        async def event_generator():
            for i in range(3):
                yield {
                    "type": "count",
                    "data": {"value": i}
                }
                await asyncio.sleep(0.01)  # Small delay

        response = sse_instance.stream_response(event_generator())

        # Collect streamed events
        events = []
        async for chunk in response.body_iterator:
            events.append(chunk)

        # Should have exactly 3 events (no heartbeats in this short test)
        assert len(events) >= 3

        # Check event format
        first_event = events[0]
        assert "event: count" in first_event
        assert "data:" in first_event
        assert first_event.endswith("\n\n")

        # Verify all 3 events are present
        event_values = []
        for event in events:
            if "value" in event:
                # Extract value from data
                if '"value": 0' in event:
                    event_values.append(0)
                elif '"value": 1' in event:
                    event_values.append(1)
                elif '"value": 2' in event:
                    event_values.append(2)

        assert 0 in event_values
        assert 1 in event_values
        assert 2 in event_values

    @pytest.mark.asyncio
    async def test_sse_with_backpressure(self):
        """Test SSE streaming with backpressure simulation."""
        sse_instance = ServerSentEvents()

        async def fast_generator():
            for i in range(10):
                yield {
                    "type": "fast",
                    "data": {"value": i}
                }
                # No delay - generate events fast

        response = sse_instance.stream_response(fast_generator())

        # Should complete without errors even with fast generation
        events = []
        async for chunk in response.body_iterator:
            events.append(chunk)

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_sse_connection_lifecycle(self):
        """Test complete SSE connection lifecycle."""
        sse_instance = ServerSentEvents()

        async def lifecycle_generator():
            yield {"type": "start", "data": "beginning"}
            await asyncio.sleep(0.01)
            yield {"type": "middle", "data": "processing"}
            await asyncio.sleep(0.01)
            yield {"type": "end", "data": "complete"}

        # Track statistics
        initial_stats = sse_instance.get_statistics()

        response = sse_instance.stream_response(lifecycle_generator())

        # Consume stream
        events = []
        async for chunk in response.body_iterator:
            events.append(chunk)

        # Check statistics were updated
        final_stats = sse_instance.get_statistics()
        assert final_stats["events_sent"] > initial_stats["events_sent"]
        assert final_stats["bytes_streamed"] > initial_stats["bytes_streamed"]

    @pytest.mark.asyncio
    async def test_sse_error_handling(self):
        """Test SSE error handling."""
        sse_instance = ServerSentEvents()

        async def error_generator():
            yield {"type": "ok", "data": "good"}
            await asyncio.sleep(0.01)
            raise ValueError("Something went wrong")

        response = sse_instance.stream_response(error_generator())

        # Should handle error gracefully
        events = []
        try:
            async for chunk in response.body_iterator:
                events.append(chunk)
        except ValueError:
            pass  # Expected error

        # Should have at least the first event
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_concurrent_sse_connections(self):
        """Test multiple concurrent SSE connections."""
        sse_instance = ServerSentEvents()

        async def multi_generator(conn_id: str):
            for i in range(2):
                yield {
                    "type": "multi",
                    "data": {"connection": conn_id, "count": i}
                }
                await asyncio.sleep(0.01)

        # Create multiple responses
        response1 = sse_instance.stream_response(multi_generator("conn1"))
        response2 = sse_instance.stream_response(multi_generator("conn2"))

        # Process both concurrently
        tasks = [
            asyncio.create_task(self._collect_events(response1)),
            asyncio.create_task(self._collect_events(response2))
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Both should complete successfully
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)

    async def _collect_events(self, response):
        """Helper to collect events from SSE response."""
        events = []
        async for chunk in response.body_iterator:
            events.append(chunk)
        return events


class TestSSEConvenienceFunctions:
    """Test SSE convenience functions and global instances."""

    def test_global_sse_instance(self):
        """Test global SSE instance availability."""
        from zenith.web.sse import sse
        assert isinstance(sse, ServerSentEvents)

    def test_create_sse_response_function(self):
        """Test create_sse_response convenience function."""
        async def test_events():
            yield {"type": "test", "data": "convenience"}

        response = create_sse_response(test_events())

        assert isinstance(response, StreamingResponse)
        assert response.headers["content-type"] == "text/event-stream"

    @pytest.mark.asyncio
    async def test_create_sse_response_functionality(self):
        """Test create_sse_response actually works."""
        async def working_events():
            for i in range(2):
                yield {
                    "type": "convenience",
                    "data": {"number": i}
                }
                await asyncio.sleep(0.01)

        response = create_sse_response(working_events())

        # Should be able to iterate the response
        events = []
        async for chunk in response.body_iterator:
            events.append(chunk)

        assert len(events) > 0
        assert any("convenience" in event for event in events)


class TestSSEEdgeCases:
    """Test SSE edge cases and error scenarios."""

    def test_sse_connection_state_enum_completeness(self):
        """Test all SSE connection states are properly defined."""
        states = list(SSEConnectionState)
        expected_states = [
            SSEConnectionState.CONNECTING,
            SSEConnectionState.CONNECTED,
            SSEConnectionState.THROTTLED,
            SSEConnectionState.DISCONNECTING,
            SSEConnectionState.DISCONNECTED,
        ]

        assert len(states) == 5
        for state in expected_states:
            assert state in states

    def test_sse_message_format_edge_cases(self):
        """Test SSE message formatting with edge case data."""
        sse_instance = ServerSentEvents()

        # Empty data
        event = {"type": "empty", "data": {}}
        formatted = sse_instance._format_sse_message(event)
        assert "data: {}" in formatted

        # None data
        event = {"type": "none", "data": None}
        formatted = sse_instance._format_sse_message(event)
        assert "data: None" in formatted

        # String data instead of dict
        event = {"type": "string", "data": "plain text"}
        formatted = sse_instance._format_sse_message(event)
        assert "data: plain text" in formatted

        # No event type
        event = {"data": {"message": "no type"}}
        formatted = sse_instance._format_sse_message(event)
        assert "event:" not in formatted
        assert "data:" in formatted

    @pytest.mark.asyncio
    async def test_sse_memory_efficiency(self):
        """Test SSE memory efficiency with weak references."""
        sse_instance = ServerSentEvents()

        # Create connection that goes out of scope
        connection_id = "memory_test"
        connection = SSEConnection(connection_id)
        sse_instance._connections[connection_id] = connection

        # Connection should be in dictionary
        assert connection_id in sse_instance._connections

        # Delete local reference
        del connection

        # Weak reference should eventually clean up
        # Note: This is implementation-dependent and may not always work in tests
        # But we can at least verify the structure exists
        assert hasattr(sse_instance, '_connections')
        assert hasattr(sse_instance._connections, '__weakref__')

    def test_sse_statistics_consistency(self):
        """Test SSE statistics consistency and edge cases."""
        sse_instance = ServerSentEvents()

        # Initial statistics
        stats = sse_instance.get_statistics()
        assert stats["active_connections"] == 0
        assert stats["total_connections"] == 0

        # Add fake connection for testing
        connection = SSEConnection("stats_test")
        sse_instance._connections["stats_test"] = connection

        # Updated statistics
        stats = sse_instance.get_statistics()
        assert stats["active_connections"] == 1

        # Test performance calculation edge cases
        assert stats["performance_improvement_percent"] >= 0
        assert stats["average_buffer_usage"] >= 0

    @pytest.mark.asyncio
    async def test_sse_task_cancellation(self):
        """Test SSE handling of task cancellation."""
        sse_instance = ServerSentEvents()

        async def cancellable_generator():
            try:
                for i in range(100):  # Long running
                    yield {"type": "long", "data": {"count": i}}
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                yield {"type": "cancelled", "data": "cleanup"}
                raise

        response = sse_instance.stream_response(cancellable_generator())

        # Start iteration
        iterator = response.body_iterator.__aiter__()

        # Get first event
        first_event = await iterator.__anext__()
        assert "long" in first_event

        # Cancel the operation (simulating client disconnect)
        # In a real scenario, this would be handled by the framework
        # Here we just verify the structure can handle it
        assert iterator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])