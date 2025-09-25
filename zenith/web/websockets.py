"""
WebSocket support for Zenith applications.

Provides WebSocket endpoints with clean integration into the Zenith framework.
Built on Starlette's WebSocket implementation.
"""

import json
from typing import Any

from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketDisconnect


class WebSocket:
    """
    WebSocket connection wrapper for Zenith.

    Provides a clean interface for WebSocket communication with
    automatic JSON encoding/decoding and error handling.

    Usage:
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json({"type": "connected"})

            try:
                while True:
                    data = await websocket.receive_json()
                    await websocket.send_json({"echo": data})
            except WebSocketDisconnect:
                # Client disconnected - handle cleanup if needed
                pass
    """

    __slots__ = ("_websocket", "client_id", "metadata", "user_id")

    def __init__(self, websocket: StarletteWebSocket):
        """Initialize WebSocket wrapper."""
        self._websocket = websocket
        self.client_id: str | None = None
        self.user_id: int | None = None
        self.metadata: dict[str, Any] = {}

    async def accept(self, subprotocol: str | None = None) -> None:
        """Accept the WebSocket connection."""
        await self._websocket.accept(subprotocol=subprotocol)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        """Close the WebSocket connection."""
        await self._websocket.close(code=code, reason=reason)

    async def send_text(self, data: str) -> None:
        """Send text message."""
        await self._websocket.send_text(data)

    async def send_bytes(self, data: bytes) -> None:
        """Send binary message."""
        await self._websocket.send_bytes(data)

    async def send_json(self, data: Any) -> None:
        """Send JSON message."""
        await self._websocket.send_json(data)

    async def receive_text(self) -> str:
        """Receive text message."""
        return await self._websocket.receive_text()

    async def receive_bytes(self) -> bytes:
        """Receive binary message."""
        return await self._websocket.receive_bytes()

    async def receive_json(self) -> Any:
        """Receive and parse JSON message."""
        return await self._websocket.receive_json()

    async def receive(self) -> dict[str, Any]:
        """Receive raw message."""
        return await self._websocket.receive()

    @property
    def client(self) -> Any:
        """Get client information."""
        return self._websocket.client

    @property
    def url(self) -> Any:
        """Get WebSocket URL."""
        return self._websocket.url

    @property
    def headers(self) -> Any:
        """Get WebSocket headers."""
        return self._websocket.headers

    @property
    def query_params(self) -> Any:
        """Get query parameters."""
        return self._websocket.query_params

    @property
    def path_params(self) -> Any:
        """Get path parameters."""
        return self._websocket.path_params


class WebSocketManager:
    """
    WebSocket connection manager for handling multiple connections.

    Useful for chat rooms, notifications, real-time updates, etc.

    Usage:
        manager = WebSocketManager()

        @app.websocket("/ws/{room_id}")
        async def websocket_endpoint(websocket: WebSocket, room_id: str):
            await manager.connect(websocket, room_id)
            try:
                while True:
                    data = await websocket.receive_json()
                    await manager.broadcast_to_room(room_id, data)
            except WebSocketDisconnect:
                await manager.disconnect(websocket, room_id)
    """

    # Note: __slots__ removed to allow mock patching in tests
    # Memory optimization less critical for WebSocketManager (typically singleton)

    def __init__(self):
        """Initialize WebSocket manager."""
        self.connections: dict[str, list[WebSocket]] = {}
        self.connection_metadata: dict[WebSocket, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, room_id: str = "default") -> None:
        """Add a WebSocket connection to a room."""
        await websocket.accept()

        if room_id not in self.connections:
            self.connections[room_id] = []

        self.connections[room_id].append(websocket)
        self.connection_metadata[websocket] = {
            "room_id": room_id,
            "connected_at": json.dumps({"timestamp": "now"}),  # Would use datetime
            "user_id": getattr(websocket, "user_id", None),
        }

        # Notify room about new connection
        await self.broadcast_to_room(
            room_id,
            {
                "type": "user_joined",
                "room_id": room_id,
                "connections": len(self.connections[room_id]),
            },
            exclude=websocket,
        )

    async def disconnect(self, websocket: WebSocket, room_id: str = "default") -> None:
        """Remove a WebSocket connection from a room."""
        if room_id in self.connections:
            if websocket in self.connections[room_id]:
                self.connections[room_id].remove(websocket)

                # Clean up empty rooms
                if not self.connections[room_id]:
                    del self.connections[room_id]

        # Clean up metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        # Notify room about disconnection
        if room_id in self.connections:
            await self.broadcast_to_room(
                room_id,
                {
                    "type": "user_left",
                    "room_id": room_id,
                    "connections": len(self.connections[room_id]),
                },
            )

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict[str, Any] | str,
        exclude: WebSocket | None = None,
    ) -> None:
        """Broadcast message to all connections in a room."""
        if room_id not in self.connections:
            return

        # Remove disconnected connections while preserving excluded ones
        active_connections = []
        dead_connections = []

        for websocket in self.connections[room_id]:
            if websocket == exclude:
                # Keep excluded websockets in the room (just don't send to them)
                active_connections.append(websocket)
            else:
                try:
                    if isinstance(message, dict):
                        await websocket.send_json(message)
                    else:
                        await websocket.send_text(message)
                    active_connections.append(websocket)
                except Exception:
                    # Connection is dead, track for cleanup
                    dead_connections.append(websocket)

        # Update active connections
        self.connections[room_id] = active_connections

        # Clean up metadata for dead connections
        for dead_ws in dead_connections:
            self.connection_metadata.pop(dead_ws, None)

    async def send_to_user(self, user_id: int, message: dict[str, Any] | str) -> bool:
        """Send message to a specific user across all rooms.

        Returns True if user was found (message delivery was attempted),
        False if user was not found.
        """
        user_found = False
        for room_connections in self.connections.values():
            for websocket in room_connections:
                if getattr(websocket, "user_id", None) == user_id:
                    user_found = True
                    try:
                        if isinstance(message, dict):
                            await websocket.send_json(message)
                        else:
                            await websocket.send_text(message)
                    except Exception:
                        # Connection failed but user was found
                        pass
        return user_found

    async def broadcast_global(self, message: dict[str, Any] | str) -> None:
        """Broadcast message to all connected clients."""
        for room_id in self.connections:
            await self.broadcast_to_room(room_id, message)

    def get_room_connections(self, room_id: str) -> int:
        """Get number of connections in a room."""
        return len(self.connections.get(room_id, []))

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.connections.values())

    def get_rooms(self) -> list[str]:
        """Get list of active rooms."""
        return list(self.connections.keys())

    def cleanup_dead_connections(self) -> int:
        """
        Clean up dead connections and their metadata.

        Returns the number of connections cleaned up.
        """
        cleaned_count = 0

        # Check for connections that exist in metadata but not in any room
        active_connections = set()
        for room_connections in self.connections.values():
            active_connections.update(room_connections)

        # Remove metadata for connections not in any room
        dead_metadata_keys = []
        for ws in self.connection_metadata:
            if ws not in active_connections:
                dead_metadata_keys.append(ws)

        for ws in dead_metadata_keys:
            self.connection_metadata.pop(ws, None)
            cleaned_count += 1

        return cleaned_count

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory usage statistics for monitoring."""
        active_connections = set()
        for room_connections in self.connections.values():
            active_connections.update(room_connections)

        return {
            "total_rooms": len(self.connections),
            "total_connections": len(active_connections),
            "metadata_entries": len(self.connection_metadata),
            "orphaned_metadata": len(self.connection_metadata)
            - len(active_connections),
            "largest_room": max(
                (len(connections) for connections in self.connections.values()),
                default=0,
            ),
        }


# Export WebSocketDisconnect for convenience
__all__ = ["WebSocket", "WebSocketDisconnect", "WebSocketManager"]
