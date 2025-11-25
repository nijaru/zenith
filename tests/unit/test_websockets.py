"""Tests for WebSocket functionality."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from zenith.web.websockets import WebSocket, WebSocketManager

# Skip on Python 3.14 due to segfault in greenlet/mock interaction during GC
# See: https://github.com/python-greenlet/greenlet/issues/391
pytestmark = pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="Python 3.14 segfaults in mock/greenlet GC interaction",
)


class TestWebSocket:
    """Test WebSocket wrapper functionality."""

    @pytest.fixture
    def mock_starlette_websocket(self):
        """Mock Starlette WebSocket."""
        websocket = AsyncMock()
        websocket.client = ("127.0.0.1", 12345)
        websocket.url = MagicMock()
        websocket.url.path = "/ws"
        websocket.headers = {"user-agent": "test"}
        websocket.query_params = {"token": "abc123"}
        websocket.path_params = {"room": "general"}
        return websocket

    @pytest.fixture
    def websocket(self, mock_starlette_websocket):
        """Create WebSocket instance."""
        return WebSocket(mock_starlette_websocket)

    def test_websocket_init(self, mock_starlette_websocket):
        """Test WebSocket initialization."""
        ws = WebSocket(mock_starlette_websocket)

        assert ws._websocket == mock_starlette_websocket
        assert ws.client_id is None
        assert ws.user_id is None
        assert ws.metadata == {}

    @pytest.mark.asyncio
    async def test_websocket_accept(self, websocket, mock_starlette_websocket):
        """Test WebSocket accept."""
        await websocket.accept()

        mock_starlette_websocket.accept.assert_called_once_with(subprotocol=None)

    @pytest.mark.asyncio
    async def test_websocket_accept_with_subprotocol(
        self, websocket, mock_starlette_websocket
    ):
        """Test WebSocket accept with subprotocol."""
        await websocket.accept("chat")

        mock_starlette_websocket.accept.assert_called_once_with(subprotocol="chat")

    @pytest.mark.asyncio
    async def test_websocket_close(self, websocket, mock_starlette_websocket):
        """Test WebSocket close."""
        await websocket.close()

        mock_starlette_websocket.close.assert_called_once_with(code=1000, reason=None)

    @pytest.mark.asyncio
    async def test_websocket_close_with_code_reason(
        self, websocket, mock_starlette_websocket
    ):
        """Test WebSocket close with code and reason."""
        await websocket.close(1001, "Going away")

        mock_starlette_websocket.close.assert_called_once_with(
            code=1001, reason="Going away"
        )

    @pytest.mark.asyncio
    async def test_websocket_send_text(self, websocket, mock_starlette_websocket):
        """Test sending text message."""
        await websocket.send_text("Hello, World!")

        mock_starlette_websocket.send_text.assert_called_once_with("Hello, World!")

    @pytest.mark.asyncio
    async def test_websocket_send_bytes(self, websocket, mock_starlette_websocket):
        """Test sending binary message."""
        data = b"binary data"
        await websocket.send_bytes(data)

        mock_starlette_websocket.send_bytes.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_websocket_send_json(self, websocket, mock_starlette_websocket):
        """Test sending JSON message."""
        data = {"type": "message", "content": "Hello"}
        await websocket.send_json(data)

        mock_starlette_websocket.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_websocket_receive_text(self, websocket, mock_starlette_websocket):
        """Test receiving text message."""
        mock_starlette_websocket.receive_text.return_value = "Hello from client"

        message = await websocket.receive_text()

        assert message == "Hello from client"
        mock_starlette_websocket.receive_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_receive_bytes(self, websocket, mock_starlette_websocket):
        """Test receiving binary message."""
        test_data = b"binary from client"
        mock_starlette_websocket.receive_bytes.return_value = test_data

        message = await websocket.receive_bytes()

        assert message == test_data
        mock_starlette_websocket.receive_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_receive_json(self, websocket, mock_starlette_websocket):
        """Test receiving JSON message."""
        test_data = {"type": "client_message", "data": "test"}
        mock_starlette_websocket.receive_json.return_value = test_data

        message = await websocket.receive_json()

        assert message == test_data
        mock_starlette_websocket.receive_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_receive_raw(self, websocket, mock_starlette_websocket):
        """Test receiving raw message."""
        test_data = {"type": "websocket.receive", "text": "raw message"}
        mock_starlette_websocket.receive.return_value = test_data

        message = await websocket.receive()

        assert message == test_data
        mock_starlette_websocket.receive.assert_called_once()

    def test_websocket_properties(self, websocket, mock_starlette_websocket):
        """Test WebSocket property access."""
        assert websocket.client == mock_starlette_websocket.client
        assert websocket.url == mock_starlette_websocket.url
        assert websocket.headers == mock_starlette_websocket.headers
        assert websocket.query_params == mock_starlette_websocket.query_params
        assert websocket.path_params == mock_starlette_websocket.path_params


class TestWebSocketManager:
    """Test WebSocketManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create WebSocketManager instance."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket instance."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.user_id = None
        return websocket

    @pytest.mark.asyncio
    async def test_manager_init(self, manager):
        """Test WebSocketManager initialization."""
        assert manager.connections == {}
        assert manager.connection_metadata == {}

    @pytest.mark.asyncio
    async def test_connect_to_default_room(self, manager, mock_websocket):
        """Test connecting to default room."""
        # Mock the broadcast method to avoid recursion
        with patch.object(manager, "broadcast_to_room") as mock_broadcast:
            await manager.connect(mock_websocket)

            mock_websocket.accept.assert_called_once()
            assert "default" in manager.connections
            assert mock_websocket in manager.connections["default"]
            assert mock_websocket in manager.connection_metadata

            # Should call broadcast with join message
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]
            assert call_args[0] == "default"
            assert call_args[1]["type"] == "user_joined"

    @pytest.mark.asyncio
    async def test_connect_to_specific_room(self, manager, mock_websocket):
        """Test connecting to specific room."""
        with patch.object(manager, "broadcast_to_room"):
            await manager.connect(mock_websocket, "chat_room")

            assert "chat_room" in manager.connections
            assert mock_websocket in manager.connections["chat_room"]
            assert manager.connection_metadata[mock_websocket]["room_id"] == "chat_room"

    @pytest.mark.asyncio
    async def test_connect_user_with_id(self, manager):
        """Test connecting user with user_id."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.user_id = 123

        await manager.connect(mock_websocket, "user_room")

        metadata = manager.connection_metadata[mock_websocket]
        assert metadata["user_id"] == 123

    @pytest.mark.asyncio
    async def test_disconnect_from_room(self, manager, mock_websocket):
        """Test disconnecting from room."""
        # First connect (mock broadcast to avoid issues)
        with patch.object(manager, "broadcast_to_room"):
            await manager.connect(mock_websocket, "test_room")

        # Then disconnect
        with patch.object(manager, "broadcast_to_room"):
            await manager.disconnect(mock_websocket, "test_room")

        # Should be removed from connections
        assert "test_room" not in manager.connections  # Empty room cleaned up
        assert mock_websocket not in manager.connection_metadata

    @pytest.mark.asyncio
    async def test_disconnect_with_other_users_in_room(self, manager):
        """Test disconnecting when other users remain in room."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        # Connect both users
        await manager.connect(mock_ws1, "shared_room")
        await manager.connect(mock_ws2, "shared_room")

        # Reset mocks
        mock_ws1.reset_mock()
        mock_ws2.reset_mock()

        # Disconnect first user
        await manager.disconnect(mock_ws1, "shared_room")

        # Room should still exist with second user
        assert "shared_room" in manager.connections
        assert len(manager.connections["shared_room"]) == 1
        assert mock_ws2 in manager.connections["shared_room"]
        assert mock_ws1 not in manager.connection_metadata

        # Should broadcast leave message to remaining user
        mock_ws2.send_json.assert_called_once()
        call_args = mock_ws2.send_json.call_args[0][0]
        assert call_args["type"] == "user_left"

    @pytest.mark.asyncio
    async def test_broadcast_to_room_json(self, manager):
        """Test broadcasting JSON message to room."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        # Connect users to room
        await manager.connect(mock_ws1, "broadcast_room")
        await manager.connect(mock_ws2, "broadcast_room")

        # Reset mocks
        mock_ws1.reset_mock()
        mock_ws2.reset_mock()

        # Broadcast message
        message = {"type": "announcement", "text": "Hello everyone"}
        await manager.broadcast_to_room("broadcast_room", message)

        # Both should receive message
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_room_text(self, manager):
        """Test broadcasting text message to room."""
        mock_websocket = AsyncMock(spec=WebSocket)

        await manager.connect(mock_websocket, "text_room")
        mock_websocket.reset_mock()

        # Broadcast text message
        await manager.broadcast_to_room("text_room", "Hello, room!")

        mock_websocket.send_text.assert_called_once_with("Hello, room!")

    @pytest.mark.asyncio
    async def test_broadcast_to_room_with_exclude(self, manager):
        """Test broadcasting with excluded websocket."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        await manager.connect(mock_ws1, "exclude_room")
        await manager.connect(mock_ws2, "exclude_room")

        mock_ws1.reset_mock()
        mock_ws2.reset_mock()

        # Broadcast excluding first websocket
        message = {"type": "message", "from": "ws1"}
        await manager.broadcast_to_room("exclude_room", message, exclude=mock_ws1)

        # Only second websocket should receive message
        mock_ws1.send_json.assert_not_called()
        mock_ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_room_handles_disconnected(self, manager):
        """Test that broadcasting handles disconnected websockets."""
        mock_ws_good = AsyncMock(spec=WebSocket)
        mock_ws_bad = AsyncMock(spec=WebSocket)
        mock_ws_bad.send_json.side_effect = Exception("Connection closed")

        await manager.connect(mock_ws_good, "mixed_room")
        await manager.connect(mock_ws_bad, "mixed_room")

        mock_ws_good.reset_mock()
        mock_ws_bad.reset_mock()

        # Broadcast message
        message = {"type": "test"}
        await manager.broadcast_to_room("mixed_room", message)

        # Good websocket should receive, bad one should be removed
        mock_ws_good.send_json.assert_called_once_with(message)
        mock_ws_bad.send_json.assert_called_once_with(message)

        # Bad connection should be removed from active connections
        assert mock_ws_good in manager.connections["mixed_room"]
        assert len(manager.connections["mixed_room"]) == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_room(self, manager):
        """Test broadcasting to room that doesn't exist."""
        # Should not raise exception
        await manager.broadcast_to_room("nonexistent", {"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager):
        """Test sending message to specific user."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws1.user_id = 123
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws2.user_id = 456

        await manager.connect(mock_ws1, "room1")
        await manager.connect(mock_ws2, "room2")

        mock_ws1.reset_mock()
        mock_ws2.reset_mock()

        # Send to specific user
        message = {"type": "private", "content": "Hello user 123"}
        result = await manager.send_to_user(123, message)

        assert result is True
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user(self, manager):
        """Test sending message to user that doesn't exist."""
        result = await manager.send_to_user(999, {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_user_handles_errors(self, manager):
        """Test sending to user handles connection errors."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.user_id = 123
        mock_websocket.send_json.side_effect = Exception("Connection error")

        await manager.connect(mock_websocket, "error_room")
        mock_websocket.reset_mock()

        # Should still return True even if send fails
        result = await manager.send_to_user(123, {"type": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_broadcast_global(self, manager):
        """Test broadcasting to all rooms."""
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws3 = AsyncMock(spec=WebSocket)

        await manager.connect(mock_ws1, "room1")
        await manager.connect(mock_ws2, "room2")
        await manager.connect(mock_ws3, "room2")

        # Reset mocks
        for ws in [mock_ws1, mock_ws2, mock_ws3]:
            ws.reset_mock()

        # Global broadcast
        message = {"type": "global", "content": "Server announcement"}
        await manager.broadcast_global(message)

        # All websockets should receive message
        for ws in [mock_ws1, mock_ws2, mock_ws3]:
            ws.send_json.assert_called_once_with(message)

    def test_get_room_connections(self, manager):
        """Test getting connection count for room."""
        # Empty manager
        assert manager.get_room_connections("empty") == 0

        # Add mock connections directly
        manager.connections["test_room"] = [AsyncMock(), AsyncMock(), AsyncMock()]

        assert manager.get_room_connections("test_room") == 3

    def test_get_total_connections(self, manager):
        """Test getting total connection count."""
        assert manager.get_total_connections() == 0

        # Add mock connections
        manager.connections["room1"] = [AsyncMock(), AsyncMock()]
        manager.connections["room2"] = [AsyncMock()]

        assert manager.get_total_connections() == 3

    def test_get_rooms(self, manager):
        """Test getting list of active rooms."""
        assert manager.get_rooms() == []

        # Add rooms
        manager.connections["room1"] = [AsyncMock()]
        manager.connections["room2"] = [AsyncMock()]

        rooms = manager.get_rooms()
        assert len(rooms) == 2
        assert "room1" in rooms
        assert "room2" in rooms


class TestWebSocketIntegration:
    """Test WebSocket integration scenarios."""

    @pytest.mark.asyncio
    async def test_websocket_chat_room_simulation(self):
        """Test simulated chat room scenario."""
        manager = WebSocketManager()

        # Create mock users
        user1_ws = AsyncMock(spec=WebSocket)
        user1_ws.user_id = 1
        user2_ws = AsyncMock(spec=WebSocket)
        user2_ws.user_id = 2

        # Users join room
        await manager.connect(user1_ws, "chat")
        await manager.connect(user2_ws, "chat")

        # Reset mocks after connection messages
        user1_ws.reset_mock()
        user2_ws.reset_mock()

        # User 1 sends message
        chat_message = {
            "type": "chat_message",
            "user_id": 1,
            "message": "Hello everyone!",
        }
        await manager.broadcast_to_room("chat", chat_message, exclude=user1_ws)

        # Only user 2 should receive the message
        user1_ws.send_json.assert_not_called()
        user2_ws.send_json.assert_called_once_with(chat_message)

        # User 2 leaves
        await manager.disconnect(user2_ws, "chat")

        # Room should still exist with user 1
        assert manager.get_room_connections("chat") == 1
        assert len(manager.connections["chat"]) == 1

    @pytest.mark.asyncio
    async def test_websocket_private_messaging(self):
        """Test private messaging between users."""
        manager = WebSocketManager()

        user1_ws = AsyncMock(spec=WebSocket)
        user1_ws.user_id = 1
        user2_ws = AsyncMock(spec=WebSocket)
        user2_ws.user_id = 2
        user3_ws = AsyncMock(spec=WebSocket)
        user3_ws.user_id = 3

        # All users connect to different rooms
        await manager.connect(user1_ws, "lobby")
        await manager.connect(user2_ws, "game")
        await manager.connect(user3_ws, "lobby")

        # Clear connection messages
        for ws in [user1_ws, user2_ws, user3_ws]:
            ws.reset_mock()

        # Send private message to user 2
        private_msg = {
            "type": "private_message",
            "from": 1,
            "message": "Hey, want to play?",
        }
        result = await manager.send_to_user(2, private_msg)

        assert result is True
        user1_ws.send_json.assert_not_called()
        user2_ws.send_json.assert_called_once_with(private_msg)
        user3_ws.send_json.assert_not_called()

    def test_websocket_disconnect_import(self):
        """Test WebSocketDisconnect is properly exported."""
        from zenith.web.websockets import WebSocketDisconnect as ImportedDisconnect

        # Should be the same as Starlette's WebSocketDisconnect
        assert ImportedDisconnect == WebSocketDisconnect
