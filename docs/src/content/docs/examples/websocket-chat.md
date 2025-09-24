---
title: WebSocket Chat Example
description: Build a real-time chat application using Zenith's WebSocket support with connection management and message broadcasting
---

# WebSocket Chat Example

This example demonstrates building a real-time chat application using Zenith's WebSocket capabilities, including connection management, room-based messaging, and user presence.

## Code Example

```python
from zenith import Zenith
from zenith.websockets import WebSocket, WebSocketManager
from pydantic import BaseModel
from typing import Dict, Set
import json
import asyncio

app = Zenith()

# WebSocket connection manager
class ChatManager(WebSocketManager):
    def __init__(self):
        super().__init__()
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.user_names: Dict[WebSocket, str] = {}
        
    async def connect_to_room(self, websocket: WebSocket, room: str, username: str):
        """Connect user to a chat room"""
        await self.connect(websocket)
        
        if room not in self.rooms:
            self.rooms[room] = set()
            
        self.rooms[room].add(websocket)
        self.user_names[websocket] = username
        
        # Notify room about new user
        await self.broadcast_to_room(room, {
            "type": "user_joined",
            "username": username,
            "message": f"{username} joined the room"
        })
        
        # Send current users list
        users_in_room = [
            self.user_names[ws] for ws in self.rooms[room] 
            if ws in self.user_names
        ]
        await websocket.send_json({
            "type": "users_list", 
            "users": users_in_room
        })
    
    async def disconnect_from_room(self, websocket: WebSocket, room: str):
        """Disconnect user from a chat room"""
        if websocket in self.user_names:
            username = self.user_names[websocket]
            
            # Remove from room
            if room in self.rooms:
                self.rooms[room].discard(websocket)
                
                # Notify room about user leaving
                await self.broadcast_to_room(room, {
                    "type": "user_left",
                    "username": username,
                    "message": f"{username} left the room"
                })
                
                # Clean up empty rooms
                if not self.rooms[room]:
                    del self.rooms[room]
            
            # Clean up user data
            del self.user_names[websocket]
            
        await self.disconnect(websocket)
    
    async def broadcast_to_room(self, room: str, message: dict):
        """Broadcast message to all users in a room"""
        if room not in self.rooms:
            return
            
        message_json = json.dumps(message)
        disconnected = []
        
        for websocket in self.rooms[room].copy():
            try:
                await websocket.send_text(message_json)
            except:
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.rooms[room].discard(ws)
            if ws in self.user_names:
                del self.user_names[ws]

# Global chat manager
chat_manager = ChatManager()

# Message models
class ChatMessage(BaseModel):
    type: str = "message"
    username: str
    message: str
    room: str

class JoinRoom(BaseModel):
    type: str = "join"
    username: str
    room: str

# WebSocket endpoint
@app.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for chat rooms"""
    username = None
    
    try:
        await websocket.accept()
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data["type"] == "join":
                # User joining room
                join_data = JoinRoom(**data)
                username = join_data.username
                await chat_manager.connect_to_room(websocket, room_id, username)
                
            elif data["type"] == "message":
                # Chat message
                if username:  # Only if user has joined
                    message = ChatMessage(**data, room=room_id, username=username)
                    await chat_manager.broadcast_to_room(room_id, {
                        "type": "message",
                        "username": message.username,
                        "message": message.message,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    
            elif data["type"] == "typing":
                # Typing indicator
                if username:
                    await chat_manager.broadcast_to_room(room_id, {
                        "type": "typing",
                        "username": username,
                        "is_typing": data.get("is_typing", False)
                    })
                    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if username:
            await chat_manager.disconnect_from_room(websocket, room_id)

# REST endpoints for chat rooms
@app.get("/api/rooms")
async def get_active_rooms():
    """Get list of active chat rooms"""
    rooms = []
    for room_id, connections in chat_manager.rooms.items():
        users = [chat_manager.user_names[ws] for ws in connections if ws in chat_manager.user_names]
        rooms.append({
            "room_id": room_id,
            "user_count": len(users),
            "users": users
        })
    return {"rooms": rooms}

@app.get("/api/rooms/{room_id}")
async def get_room_info(room_id: str):
    """Get information about a specific room"""
    if room_id not in chat_manager.rooms:
        return {"error": "Room not found"}, 404
        
    users = [
        chat_manager.user_names[ws] 
        for ws in chat_manager.rooms[room_id] 
        if ws in chat_manager.user_names
    ]
    
    return {
        "room_id": room_id,
        "user_count": len(users),
        "users": users
    }

# Serve static HTML for testing
@app.get("/")
async def chat_interface():
    """Simple HTML interface for testing the chat"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zenith Chat</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .chat-container { max-width: 600px; }
            .messages { 
                border: 1px solid #ccc; 
                height: 400px; 
                overflow-y: scroll; 
                padding: 10px; 
                margin-bottom: 10px;
            }
            .message { margin-bottom: 10px; }
            .username { font-weight: bold; color: #007bff; }
            .system-message { color: #28a745; font-style: italic; }
            input, button { padding: 8px; margin: 2px; }
            #messageInput { width: 400px; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>Zenith WebSocket Chat</h1>
            <div>
                <input type="text" id="usernameInput" placeholder="Enter username" />
                <input type="text" id="roomInput" placeholder="Room name" value="general" />
                <button onclick="joinRoom()">Join Room</button>
            </div>
            <div class="messages" id="messages"></div>
            <div>
                <input type="text" id="messageInput" placeholder="Type a message..." disabled />
                <button onclick="sendMessage()" id="sendBtn" disabled>Send</button>
            </div>
        </div>

        <script>
            let socket = null;
            let username = null;
            let currentRoom = null;

            function joinRoom() {
                username = document.getElementById('usernameInput').value.trim();
                currentRoom = document.getElementById('roomInput').value.trim();
                
                if (!username || !currentRoom) {
                    alert('Please enter username and room name');
                    return;
                }

                socket = new WebSocket(`ws://localhost:8000/ws/chat/${currentRoom}`);
                
                socket.onopen = function() {
                    socket.send(JSON.stringify({
                        type: 'join',
                        username: username,
                        room: currentRoom
                    }));
                    
                    document.getElementById('messageInput').disabled = false;
                    document.getElementById('sendBtn').disabled = false;
                    addMessage('system', `Connected to room: ${currentRoom}`);
                };
                
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'message') {
                        addMessage(data.username, data.message);
                    } else if (data.type === 'user_joined' || data.type === 'user_left') {
                        addMessage('system', data.message);
                    }
                };
                
                socket.onclose = function() {
                    addMessage('system', 'Disconnected from chat');
                    document.getElementById('messageInput').disabled = true;
                    document.getElementById('sendBtn').disabled = true;
                };
            }

            function sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const message = messageInput.value.trim();
                
                if (message && socket) {
                    socket.send(JSON.stringify({
                        type: 'message',
                        message: message
                    }));
                    messageInput.value = '';
                }
            }

            function addMessage(user, message) {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                
                if (user === 'system') {
                    messageDiv.innerHTML = `<span class="system-message">${message}</span>`;
                } else {
                    messageDiv.innerHTML = `<span class="username">${user}:</span> ${message}`;
                }
                
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            // Enter key to send message
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Key Features Demonstrated

### WebSocket Connection Management
- **Room-based chat**: Users can join different chat rooms
- **Connection tracking**: Manage active connections per room
- **Graceful disconnection**: Clean up when users leave

### Real-time Messaging
- **Broadcast messages**: Send messages to all users in a room
- **User presence**: Track who's online in each room
- **Join/leave notifications**: Notify when users enter or leave

### Message Types
- **Chat messages**: Regular user messages
- **System messages**: Join/leave notifications  
- **Typing indicators**: Show when users are typing
- **User lists**: Current users in the room

### REST API Integration
- **Room listing**: Get active rooms via REST API
- **Room information**: Get details about specific rooms
- **Hybrid approach**: WebSocket for real-time, REST for metadata

## Running the Example

1. **Save the code** as `websocket_chat.py`
2. **Install dependencies**:
   ```bash
   pip install zenithweb uvicorn
   ```
3. **Run the server**:
   ```bash
   python websocket_chat.py
   ```
4. **Open multiple browser tabs** to `http://localhost:8000`
5. **Join different rooms** and start chatting!

## Testing with curl

```bash
# Get active rooms
curl http://localhost:8000/api/rooms

# Get specific room info
curl http://localhost:8000/api/rooms/general
```

## Next Steps

- Explore **[Background Tasks](/zenith/examples/auto-generated/05-background-tasks/)** for message persistence
- Learn **[Database Models](/zenith/concepts/models/)** for persistent storage
- See **[Rate Limiting](/zenith/examples/auto-generated/08-rate-limiting/)** for message throttling

---

**Source**: [`examples/07-websocket-chat.py`](https://github.com/nijaru/zenith/blob/main/examples/07-websocket-chat.py)