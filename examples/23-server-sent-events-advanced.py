"""
Server-Sent Events (SSE) Example - Real-time Data Streaming

This example demonstrates comprehensive SSE functionality including:
- Real-time dashboard updates
- Live chat/notifications
- System monitoring streams
- Multi-channel broadcasting
- Performance monitoring
- Error handling and recovery

Key features demonstrated:
✅ Basic SSE streaming
✅ Multi-channel subscriptions
✅ Real-time performance metrics
✅ Backpressure handling
✅ Error recovery
✅ Live dashboard updates
✅ WebSocket alternative patterns
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List

from zenith import Zenith
from zenith.web.sse import ServerSentEvents, SSEEventManager, create_sse_response

# Initialize Zenith app
app = Zenith()

# Create SSE manager for advanced features
sse_manager = SSEEventManager()

# Global state for demo
dashboard_state = {
    "active_users": 0,
    "cpu_usage": 0.0,
    "memory_usage": 0.0,
    "requests_per_second": 0,
    "error_count": 0,
    "last_update": datetime.now()
}

notifications = []
chat_messages = []


# ============================================================================
# BASIC SSE ENDPOINTS
# ============================================================================

@app.get("/")
async def home():
    """SSE Demo homepage with all available endpoints."""
    return {
        "title": "Zenith Server-Sent Events Demo",
        "description": "Comprehensive SSE streaming examples",
        "endpoints": {
            "basic_stream": "/events/basic - Simple event stream",
            "dashboard_stream": "/events/dashboard - Real-time dashboard",
            "notifications": "/events/notifications - Live notifications",
            "chat": "/events/chat - Live chat stream",
            "monitoring": "/events/monitoring - System monitoring",
            "multi_channel": "/events/channel/{channel} - Channel-specific events",
            "performance": "/events/performance - Performance metrics",
            "error_demo": "/events/error-demo - Error handling demo"
        },
        "controls": {
            "trigger_notification": "POST /trigger/notification",
            "send_chat_message": "POST /trigger/chat",
            "simulate_load": "POST /trigger/load",
            "dashboard_update": "POST /trigger/dashboard"
        },
        "statistics": "/stats - SSE performance statistics"
    }


@app.get("/events/basic")
async def basic_event_stream():
    """
    Basic SSE stream - sends simple events every second.
    Perfect for getting started with SSE.
    """
    async def event_generator():
        counter = 0
        while counter < 10:  # Send 10 events then stop
            yield {
                "type": "basic_update",
                "data": {
                    "counter": counter,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Hello from SSE! Event #{counter}"
                }
            }
            counter += 1
            await asyncio.sleep(1)

        # Send completion event
        yield {
            "type": "stream_complete",
            "data": {"message": "Basic stream completed!"}
        }

    return create_sse_response(event_generator())


# ============================================================================
# REAL-TIME DASHBOARD
# ============================================================================

@app.get("/events/dashboard")
async def dashboard_stream():
    """
    Real-time dashboard stream - live system metrics and updates.
    Demonstrates high-frequency data streaming with backpressure handling.
    """
    async def dashboard_events():
        while True:
            # Simulate real-time metrics
            dashboard_state["active_users"] = random.randint(50, 200)
            dashboard_state["cpu_usage"] = round(random.uniform(10, 90), 2)
            dashboard_state["memory_usage"] = round(random.uniform(20, 80), 2)
            dashboard_state["requests_per_second"] = random.randint(100, 1000)
            dashboard_state["error_count"] = random.randint(0, 5)
            dashboard_state["last_update"] = datetime.now()

            yield {
                "type": "dashboard_update",
                "data": {
                    **dashboard_state,
                    "last_update": dashboard_state["last_update"].isoformat()
                }
            }

            await asyncio.sleep(2)  # Update every 2 seconds

    return create_sse_response(dashboard_events())


# ============================================================================
# NOTIFICATIONS SYSTEM
# ============================================================================

@app.get("/events/notifications")
async def notifications_stream():
    """
    Live notifications stream - demonstrates event-driven updates.
    Shows how to stream notifications as they occur.
    """
    async def notification_events():
        last_sent = 0

        while True:
            # Send any new notifications
            for i, notification in enumerate(notifications[last_sent:], last_sent):
                yield {
                    "type": "notification",
                    "data": notification
                }
                last_sent = i + 1

            # Send heartbeat to keep connection alive
            yield {
                "type": "heartbeat",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "pending_notifications": len(notifications) - last_sent
                }
            }

            await asyncio.sleep(3)

    return create_sse_response(notification_events())


# ============================================================================
# LIVE CHAT SYSTEM
# ============================================================================

@app.get("/events/chat")
async def chat_stream():
    """
    Live chat stream - real-time messaging.
    Demonstrates low-latency event streaming for chat applications.
    """
    async def chat_events():
        last_message_index = 0

        while True:
            # Send new chat messages
            for i, message in enumerate(chat_messages[last_message_index:], last_message_index):
                yield {
                    "type": "chat_message",
                    "data": message
                }
                last_message_index = i + 1

            # Send typing indicators (simulated)
            if random.random() < 0.2:  # 20% chance
                yield {
                    "type": "user_typing",
                    "data": {
                        "user": f"User{random.randint(1, 5)}",
                        "timestamp": datetime.now().isoformat()
                    }
                }

            await asyncio.sleep(0.5)  # Very responsive for chat

    return create_sse_response(chat_events())


# ============================================================================
# SYSTEM MONITORING
# ============================================================================

@app.get("/events/monitoring")
async def monitoring_stream():
    """
    System monitoring stream - high-frequency metrics.
    Demonstrates SSE with backpressure handling for monitoring data.
    """
    async def monitoring_events():
        while True:
            # Generate monitoring data
            metrics = {
                "cpu_cores": [
                    round(random.uniform(0, 100), 1) for _ in range(4)
                ],
                "memory": {
                    "used": round(random.uniform(2000, 8000), 1),
                    "total": 8192,
                    "cached": round(random.uniform(500, 1500), 1)
                },
                "network": {
                    "bytes_in": random.randint(1000, 50000),
                    "bytes_out": random.randint(500, 20000),
                    "packets_in": random.randint(10, 500),
                    "packets_out": random.randint(10, 500)
                },
                "disk": {
                    "read_ops": random.randint(0, 100),
                    "write_ops": random.randint(0, 50),
                    "read_bytes": random.randint(0, 1000000),
                    "write_bytes": random.randint(0, 500000)
                },
                "timestamp": datetime.now().isoformat()
            }

            yield {
                "type": "system_metrics",
                "data": metrics
            }

            await asyncio.sleep(1)  # High frequency monitoring

    return create_sse_response(monitoring_events())


# ============================================================================
# MULTI-CHANNEL STREAMING
# ============================================================================

@app.get("/events/channel/{channel}")
async def channel_stream(channel: str):
    """
    Channel-specific event stream.
    Demonstrates multi-channel broadcasting and targeted content delivery.
    """
    async def channel_events():
        event_count = 0

        while True:
            # Generate channel-specific content
            if channel == "news":
                content = {
                    "headline": f"Breaking News #{event_count + 1}",
                    "summary": "Important update from the news channel",
                    "category": "breaking",
                    "priority": random.choice(["low", "medium", "high"])
                }
            elif channel == "sports":
                content = {
                    "game": f"Game Update #{event_count + 1}",
                    "score": f"{random.randint(0, 5)}-{random.randint(0, 5)}",
                    "time": f"{random.randint(1, 90)}'",
                    "event": random.choice(["goal", "card", "substitution", "corner"])
                }
            elif channel == "stocks":
                content = {
                    "symbol": random.choice(["AAPL", "GOOGL", "MSFT", "TSLA"]),
                    "price": round(random.uniform(100, 300), 2),
                    "change": round(random.uniform(-5, 5), 2),
                    "volume": random.randint(1000000, 5000000)
                }
            else:
                content = {
                    "message": f"Generic update for channel '{channel}'",
                    "event_number": event_count + 1
                }

            yield {
                "type": f"{channel}_update",
                "data": {
                    "channel": channel,
                    "timestamp": datetime.now().isoformat(),
                    **content
                }
            }

            event_count += 1
            await asyncio.sleep(random.uniform(2, 5))  # Variable timing

    return create_sse_response(channel_events())


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

@app.get("/events/performance")
async def performance_stream():
    """
    SSE performance monitoring stream.
    Demonstrates monitoring SSE itself and optimizations.
    """
    async def performance_events():
        while True:
            # Get SSE statistics
            stats = sse_manager.get_performance_stats()

            # Add some computed metrics
            performance_metrics = {
                **stats,
                "events_per_second": stats.get("events_sent", 0) / max(time.time() - 60, 1),
                "bytes_per_second": stats.get("bytes_streamed", 0) / max(time.time() - 60, 1),
                "connection_efficiency": (
                    stats.get("active_connections", 0) /
                    max(stats.get("total_connections", 1), 1) * 100
                ),
                "timestamp": datetime.now().isoformat()
            }

            yield {
                "type": "performance_metrics",
                "data": performance_metrics
            }

            await asyncio.sleep(5)  # Every 5 seconds

    return create_sse_response(performance_events())


# ============================================================================
# ERROR HANDLING DEMO
# ============================================================================

@app.get("/events/error-demo")
async def error_demo_stream():
    """
    Error handling demonstration.
    Shows how SSE handles errors gracefully and recovers.
    """
    async def error_prone_events():
        event_count = 0

        while event_count < 20:
            try:
                # Normal events
                if event_count < 5:
                    yield {
                        "type": "normal",
                        "data": {
                            "event": event_count,
                            "status": "ok",
                            "message": "Normal operation"
                        }
                    }

                # Simulate error condition
                elif event_count == 5:
                    yield {
                        "type": "error",
                        "data": {
                            "event": event_count,
                            "status": "error",
                            "message": "Simulated error occurred!"
                        }
                    }
                    # Don't actually raise error for demo purposes

                # Recovery events
                elif event_count < 10:
                    yield {
                        "type": "recovery",
                        "data": {
                            "event": event_count,
                            "status": "recovering",
                            "message": "System recovering from error"
                        }
                    }

                # Back to normal
                else:
                    yield {
                        "type": "normal",
                        "data": {
                            "event": event_count,
                            "status": "ok",
                            "message": "Fully recovered"
                        }
                    }

                event_count += 1
                await asyncio.sleep(1)

            except Exception as e:
                yield {
                    "type": "error",
                    "data": {
                        "event": event_count,
                        "status": "exception",
                        "error": str(e)
                    }
                }
                await asyncio.sleep(2)  # Wait before continuing

        # Final completion event
        yield {
            "type": "complete",
            "data": {"message": "Error demo completed successfully"}
        }

    return create_sse_response(error_prone_events())


# ============================================================================
# CONTROL ENDPOINTS (Trigger Events)
# ============================================================================

@app.post("/trigger/notification")
async def trigger_notification(data: dict):
    """Trigger a new notification for the notifications stream."""
    notification = {
        "id": len(notifications) + 1,
        "type": data.get("type", "info"),
        "title": data.get("title", "New Notification"),
        "message": data.get("message", "Something happened!"),
        "timestamp": datetime.now().isoformat(),
        "read": False
    }

    notifications.append(notification)

    return {
        "status": "success",
        "notification": notification,
        "total_notifications": len(notifications)
    }


@app.post("/trigger/chat")
async def send_chat_message(data: dict):
    """Send a new chat message to the chat stream."""
    message = {
        "id": len(chat_messages) + 1,
        "user": data.get("user", f"User{random.randint(1, 10)}"),
        "message": data.get("message", "Hello from the chat!"),
        "timestamp": datetime.now().isoformat(),
        "type": "message"
    }

    chat_messages.append(message)

    return {
        "status": "success",
        "message": message,
        "total_messages": len(chat_messages)
    }


@app.post("/trigger/load")
async def simulate_load():
    """Simulate system load for monitoring demo."""
    # Update dashboard state with simulated high load
    dashboard_state.update({
        "active_users": random.randint(500, 1000),
        "cpu_usage": round(random.uniform(80, 95), 2),
        "memory_usage": round(random.uniform(85, 95), 2),
        "requests_per_second": random.randint(2000, 5000),
        "error_count": random.randint(10, 50),
        "last_update": datetime.now()
    })

    return {
        "status": "success",
        "message": "High load simulation activated",
        "duration": "30 seconds",
        "dashboard_state": {
            **dashboard_state,
            "last_update": dashboard_state["last_update"].isoformat()
        }
    }


@app.post("/trigger/dashboard")
async def update_dashboard(data: dict):
    """Manually update dashboard state."""
    dashboard_state.update({
        "active_users": data.get("active_users", dashboard_state["active_users"]),
        "cpu_usage": data.get("cpu_usage", dashboard_state["cpu_usage"]),
        "memory_usage": data.get("memory_usage", dashboard_state["memory_usage"]),
        "requests_per_second": data.get("requests_per_second", dashboard_state["requests_per_second"]),
        "error_count": data.get("error_count", dashboard_state["error_count"]),
        "last_update": datetime.now()
    })

    return {
        "status": "success",
        "message": "Dashboard updated",
        "dashboard_state": {
            **dashboard_state,
            "last_update": dashboard_state["last_update"].isoformat()
        }
    }


# ============================================================================
# STATISTICS AND MONITORING
# ============================================================================

@app.get("/stats")
async def sse_statistics():
    """Get comprehensive SSE performance statistics."""
    stats = sse_manager.get_performance_stats()

    return {
        "sse_statistics": stats,
        "application_state": {
            "total_notifications": len(notifications),
            "total_chat_messages": len(chat_messages),
            "dashboard_last_update": dashboard_state["last_update"].isoformat(),
            "active_streams": [
                "basic", "dashboard", "notifications", "chat",
                "monitoring", "performance", "error-demo"
            ],
            "available_channels": ["news", "sports", "stocks", "general"]
        },
        "runtime_info": {
            "uptime_seconds": time.time(),
            "memory_usage": "Dynamic based on connections",
            "performance_mode": "optimized with backpressure handling"
        }
    }


# ============================================================================
# HTML CLIENT FOR TESTING (Optional)
# ============================================================================

@app.get("/demo")
async def demo_page():
    """Simple HTML page for testing SSE endpoints."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zenith SSE Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .stream-section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; }
            .events { height: 200px; overflow-y: scroll; border: 1px solid #eee; padding: 10px; }
            button { margin: 5px; padding: 10px; }
            .event { margin: 5px 0; padding: 5px; background: #f9f9f9; }
        </style>
    </head>
    <body>
        <h1>Zenith Server-Sent Events Demo</h1>

        <div class="stream-section">
            <h3>Basic Stream</h3>
            <button onclick="startBasicStream()">Start Basic Stream</button>
            <div id="basic-events" class="events"></div>
        </div>

        <div class="stream-section">
            <h3>Dashboard Stream</h3>
            <button onclick="startDashboardStream()">Start Dashboard Stream</button>
            <div id="dashboard-events" class="events"></div>
        </div>

        <div class="stream-section">
            <h3>Notifications</h3>
            <button onclick="startNotificationStream()">Start Notifications</button>
            <button onclick="triggerNotification()">Trigger Notification</button>
            <div id="notification-events" class="events"></div>
        </div>

        <script>
            function startBasicStream() {
                const events = document.getElementById('basic-events');
                const eventSource = new EventSource('/events/basic');

                eventSource.onmessage = function(event) {
                    const div = document.createElement('div');
                    div.className = 'event';
                    div.textContent = event.data;
                    events.appendChild(div);
                    events.scrollTop = events.scrollHeight;
                };
            }

            function startDashboardStream() {
                const events = document.getElementById('dashboard-events');
                const eventSource = new EventSource('/events/dashboard');

                eventSource.onmessage = function(event) {
                    const div = document.createElement('div');
                    div.className = 'event';
                    div.textContent = event.data;
                    events.appendChild(div);
                    events.scrollTop = events.scrollHeight;
                };
            }

            function startNotificationStream() {
                const events = document.getElementById('notification-events');
                const eventSource = new EventSource('/events/notifications');

                eventSource.onmessage = function(event) {
                    const div = document.createElement('div');
                    div.className = 'event';
                    div.textContent = event.data;
                    events.appendChild(div);
                    events.scrollTop = events.scrollHeight;
                };
            }

            async function triggerNotification() {
                await fetch('/trigger/notification', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type: 'info',
                        title: 'Test Notification',
                        message: 'This is a test notification!'
                    })
                });
            }
        </script>
    </body>
    </html>
    """

    from starlette.responses import HTMLResponse
    return HTMLResponse(html_content)


# ============================================================================
# STARTUP TASKS
# ============================================================================

@app.on_startup
async def startup():
    """Initialize demo data and background tasks."""
    print("🚀 Zenith SSE Demo Starting...")
    print("📊 Initializing demo data...")

    # Add some initial notifications
    initial_notifications = [
        {
            "id": 1,
            "type": "info",
            "title": "Welcome!",
            "message": "SSE Demo is now running",
            "timestamp": datetime.now().isoformat(),
            "read": False
        },
        {
            "id": 2,
            "type": "success",
            "title": "System Ready",
            "message": "All SSE endpoints are available",
            "timestamp": datetime.now().isoformat(),
            "read": False
        }
    ]
    notifications.extend(initial_notifications)

    # Add some initial chat messages
    initial_messages = [
        {
            "id": 1,
            "user": "System",
            "message": "Chat system is online!",
            "timestamp": datetime.now().isoformat(),
            "type": "system"
        },
        {
            "id": 2,
            "user": "Demo",
            "message": "Welcome to the Zenith SSE chat demo!",
            "timestamp": datetime.now().isoformat(),
            "type": "message"
        }
    ]
    chat_messages.extend(initial_messages)

    print("✅ SSE Demo ready!")
    print()
    print("🔗 Available endpoints:")
    print("   📍 Basic Stream: /events/basic")
    print("   📊 Dashboard: /events/dashboard")
    print("   🔔 Notifications: /events/notifications")
    print("   💬 Chat: /events/chat")
    print("   📈 Monitoring: /events/monitoring")
    print("   📺 Channels: /events/channel/{news|sports|stocks}")
    print("   ⚡ Performance: /events/performance")
    print("   🚨 Error Demo: /events/error-demo")
    print()
    print("🎮 Control endpoints:")
    print("   POST /trigger/notification - Create notification")
    print("   POST /trigger/chat - Send chat message")
    print("   POST /trigger/load - Simulate high load")
    print("   POST /trigger/dashboard - Update dashboard")
    print()
    print("📈 Monitoring:")
    print("   GET /stats - SSE statistics")
    print("   GET /demo - HTML test client")


if __name__ == "__main__":
    print("🌟 Starting Zenith SSE Demo Server")
    print("🔗 Demo page: http://localhost:8020/demo")
    print("📊 Statistics: http://localhost:8020/stats")
    print()

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8020, log_level="info")