"""
WebSocket Chat Example - Real-time chat application

Demonstrates:
- WebSocket connections with Zenith
- Real-time messaging between clients
- Chat room management
- Connection tracking and broadcasting
"""

from datetime import datetime

from zenith import WebSocket, WebSocketDisconnect, WebSocketManager, Zenith

# Create app
app = Zenith()

# Global chat manager
chat_manager = WebSocketManager()

# Store chat history (in production, use database)
chat_history: dict[str, list] = {"general": []}


@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for chat rooms."""
    room_id = websocket.path_params.get("room_id", "general")
    user_name = websocket.query_params.get("name", "Anonymous")

    # Store user info on websocket
    websocket.user_name = user_name
    websocket.room_id = room_id

    # Initialize room history if needed
    if room_id not in chat_history:
        chat_history[room_id] = []

    try:
        # Connect user to room
        await chat_manager.connect(websocket, room_id)

        # Send welcome message and recent history
        await websocket.send_json(
            {
                "type": "system",
                "message": f"Welcome to room '{room_id}', {user_name}!",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Send recent chat history (last 10 messages)
        for message in chat_history[room_id][-10:]:
            await websocket.send_json(message)

        # Listen for messages
        while True:
            data = await websocket.receive_json()

            # Process different message types
            if data.get("type") == "chat":
                # Create chat message
                message = {
                    "type": "chat",
                    "user": user_name,
                    "message": data.get("message", ""),
                    "room": room_id,
                    "timestamp": datetime.now().isoformat(),
                }

                # Store in history
                chat_history[room_id].append(message)

                # Broadcast to all users in room
                await chat_manager.broadcast_to_room(room_id, message)

            elif data.get("type") == "typing":
                # Broadcast typing indicator (don't store in history)
                typing_message = {
                    "type": "typing",
                    "user": user_name,
                    "room": room_id,
                    "typing": data.get("typing", False),
                }
                await chat_manager.broadcast_to_room(
                    room_id, typing_message, exclude=websocket
                )

    except WebSocketDisconnect:
        # User disconnected
        await chat_manager.disconnect(websocket, room_id)

        # Notify room
        leave_message = {
            "type": "system",
            "message": f"{user_name} left the room",
            "timestamp": datetime.now().isoformat(),
        }
        await chat_manager.broadcast_to_room(room_id, leave_message)


@app.get("/")
async def chat_home():
    """Serve chat client HTML."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Zenith WebSocket Chat</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #chat { height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
        .message { margin: 5px 0; }
        .system { color: #666; font-style: italic; }
        .chat { color: #000; }
        .typing { color: #999; font-style: italic; }
        input, button { padding: 8px; margin: 5px; }
        #messageInput { width: 300px; }
    </style>
</head>
<body>
    <h1>🚀 Zenith WebSocket Chat</h1>

    <div>
        <input type="text" id="nameInput" placeholder="Your name" value="User">
        <input type="text" id="roomInput" placeholder="Room name" value="general">
        <button onclick="connect()">Connect</button>
        <button onclick="disconnect()">Disconnect</button>
    </div>

    <div id="status">Disconnected</div>
    <div id="chat"></div>

    <div>
        <input type="text" id="messageInput" placeholder="Type a message..." disabled>
        <button onclick="sendMessage()" disabled id="sendBtn">Send</button>
    </div>

    <div style="margin-top: 20px;">
        <h3>Instructions:</h3>
        <ul>
            <li>Enter your name and room</li>
            <li>Click Connect to join</li>
            <li>Type messages and press Enter or click Send</li>
            <li>Open multiple tabs to test real-time chat</li>
        </ul>
    </div>

<script>
let ws = null;
let connected = false;

function connect() {
    if (connected) return;

    const name = document.getElementById('nameInput').value || 'Anonymous';
    const room = document.getElementById('roomInput').value || 'general';

    ws = new WebSocket(`ws://localhost:8007/ws/${room}?name=${encodeURIComponent(name)}`);

    ws.onopen = function() {
        connected = true;
        document.getElementById('status').textContent = `Connected to room: ${room}`;
        document.getElementById('messageInput').disabled = false;
        document.getElementById('sendBtn').disabled = false;
    };

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        displayMessage(data);
    };

    ws.onclose = function() {
        connected = false;
        document.getElementById('status').textContent = 'Disconnected';
        document.getElementById('messageInput').disabled = true;
        document.getElementById('sendBtn').disabled = true;
    };

    ws.onerror = function(error) {
        console.log('WebSocket error:', error);
    };
}

function disconnect() {
    if (ws) {
        ws.close();
    }
}

function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (message && connected) {
        ws.send(JSON.stringify({
            type: 'chat',
            message: message
        }));
        messageInput.value = '';
    }
}

function displayMessage(data) {
    const chat = document.getElementById('chat');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${data.type}`;

    const time = new Date(data.timestamp).toLocaleTimeString();

    if (data.type === 'chat') {
        messageDiv.innerHTML = `<strong>${data.user}:</strong> ${data.message} <small>(${time})</small>`;
    } else if (data.type === 'system') {
        messageDiv.innerHTML = `<em>${data.message}</em> <small>(${time})</small>`;
    } else if (data.type === 'typing') {
        messageDiv.innerHTML = `<em>${data.user} is typing...</em>`;
        // Remove typing messages after 3 seconds
        setTimeout(() => messageDiv.remove(), 3000);
    }

    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;
}

// Send message on Enter key
document.getElementById('messageInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Auto-connect on page load
window.onload = function() {
    // Don't auto-connect, let user choose
};
</script>
</body>
</html>
    """


@app.get("/api/rooms")
async def get_rooms():
    """Get list of active chat rooms."""
    rooms = chat_manager.get_rooms()
    room_info = []

    for room in rooms:
        room_info.append(
            {
                "name": room,
                "connections": chat_manager.get_room_connections(room),
                "messages": len(chat_history.get(room, [])),
            }
        )

    return {
        "rooms": room_info,
        "total_connections": chat_manager.get_total_connections(),
    }


@app.get("/api/history/{room_id}")
async def get_room_history(room_id: str, limit: int = 50):
    """Get chat history for a room."""
    messages = chat_history.get(room_id, [])
    return {"room": room_id, "messages": messages[-limit:], "total": len(messages)}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "websocket-chat",
        "active_rooms": len(chat_manager.get_rooms()),
        "total_connections": chat_manager.get_total_connections(),
    }


if __name__ == "__main__":
    import uvicorn

    print("🚀 WebSocket Chat Server")
    print("Open your browser to: http://localhost:8007")
    print("API endpoints:")
    print("  GET /api/rooms - List active rooms")
    print("  GET /api/history/{room} - Get room history")
    print("  WebSocket: ws://localhost:8007/ws/{room}?name={username}")
    uvicorn.run("websocket_chat_example:app", host="127.0.0.1", port=8007, reload=True)
