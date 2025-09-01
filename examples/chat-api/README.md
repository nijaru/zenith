# Chat API

> Real-time messaging application with WebSocket support and message history

## Features

- Real-time messaging with WebSockets
- Chat rooms and direct messages  
- Message history with pagination
- User presence tracking
- File sharing in chats
- Message reactions and threads
- Push notifications

## Key Endpoints

```
GET    /rooms              - List user's chat rooms
POST   /rooms              - Create chat room
GET    /rooms/{id}/messages - Get message history
POST   /rooms/{id}/messages - Send message
WS     /ws/rooms/{id}      - Real-time room connection
GET    /users/presence     - User presence status
```

## Architecture

Demonstrates WebSocket handling, real-time event broadcasting, message queuing with Redis, and optimized database queries for chat history.

```python
# Real-time message broadcasting
class ChatWebSocket(WebSocketEndpoint):
    async def on_message(self, websocket, data):
        message = await self.chat.send_message(
            room_id=data["room_id"],
            user_id=data["user_id"], 
            content=data["content"]
        )
        
        # Broadcast to all room members
        await self.broadcast_to_room(data["room_id"], {
            "type": "new_message",
            "message": message.dict()
        })
```