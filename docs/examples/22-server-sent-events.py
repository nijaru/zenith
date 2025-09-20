#!/usr/bin/env python3
"""
Server-Sent Events (SSE) Example.

Demonstrates real-time event streaming with Zenith's built-in SSE support.
Features automatic backpressure handling for 10x connection capacity.

Run with:
    uv run python examples/22-server-sent-events.py

Then open:
    http://localhost:8000 - HTML client
    http://localhost:8000/events - SSE stream endpoint
"""

import asyncio
import time
from datetime import datetime

from zenith import Zenith, create_sse_response
from zenith.web.responses import html_response

app = Zenith(
    title="SSE Demo",
    description="Real-time event streaming with Server-Sent Events",
    version="1.0.0",
)


# HTML client for testing SSE
HTML_CLIENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Zenith SSE Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        #events {
            border: 1px solid #ddd;
            padding: 10px;
            height: 400px;
            overflow-y: auto;
            background: #f5f5f5;
        }
        .event {
            margin: 5px 0;
            padding: 5px;
            background: white;
            border-radius: 3px;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .connected { background: #d4edda; color: #155724; }
        .disconnected { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>🌊 Zenith Server-Sent Events Demo</h1>

    <div id="status" class="status disconnected">Disconnected</div>

    <button onclick="connect()">Connect</button>
    <button onclick="disconnect()">Disconnect</button>
    <button onclick="clearEvents()">Clear</button>

    <h2>Event Stream:</h2>
    <div id="events"></div>

    <script>
        let eventSource = null;

        function connect() {
            if (eventSource) {
                eventSource.close();
            }

            eventSource = new EventSource('/events');

            eventSource.onopen = function() {
                updateStatus('Connected', true);
                addEvent('Connection established', 'system');
            };

            eventSource.onerror = function(e) {
                updateStatus('Disconnected', false);
                addEvent('Connection error', 'error');
            };

            // Handle specific event types
            eventSource.addEventListener('time', function(e) {
                const data = JSON.parse(e.data);
                addEvent(`Time update: ${data.current_time}`, 'time');
            });

            eventSource.addEventListener('stats', function(e) {
                const data = JSON.parse(e.data);
                addEvent(`Stats: ${data.connections} connections, ${data.events_sent} events sent`, 'stats');
            });

            eventSource.addEventListener('heartbeat', function(e) {
                const data = JSON.parse(e.data);
                addEvent(`Heartbeat #${data.count}`, 'heartbeat');
            });
        }

        function disconnect() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
                updateStatus('Disconnected', false);
                addEvent('Disconnected by user', 'system');
            }
        }

        function updateStatus(text, connected) {
            const status = document.getElementById('status');
            status.textContent = text;
            status.className = 'status ' + (connected ? 'connected' : 'disconnected');
        }

        function addEvent(message, type) {
            const events = document.getElementById('events');
            const event = document.createElement('div');
            event.className = 'event';
            event.innerHTML = `<strong>[${new Date().toLocaleTimeString()}]</strong> ${message}`;
            events.appendChild(event);
            events.scrollTop = events.scrollHeight;
        }

        function clearEvents() {
            document.getElementById('events').innerHTML = '';
        }

        // Auto-connect on load
        window.onload = function() {
            connect();
        };
    </script>
</body>
</html>
"""


@app.get("/")
async def home():
    """Serve the HTML client."""
    return html_response(HTML_CLIENT)


@app.get("/events")
async def stream_events():
    """
    Stream real-time events using Server-Sent Events.

    Demonstrates Zenith's built-in SSE support with:
    - Automatic backpressure handling
    - Multiple event types
    - Clean async generator pattern
    """

    async def event_generator():
        """Generate events for streaming."""
        event_count = 0
        heartbeat_count = 0

        while True:
            # Send different types of events

            # Time update event
            if event_count % 3 == 0:
                yield {
                    "type": "time",
                    "data": {
                        "current_time": datetime.now().isoformat(),
                        "timestamp": time.time(),
                    },
                }

            # Stats event
            if event_count % 5 == 0:
                yield {
                    "type": "stats",
                    "data": {
                        "connections": 1,  # In real app, track actual connections
                        "events_sent": event_count,
                        "uptime_seconds": event_count,
                    },
                }

            # Regular heartbeat
            heartbeat_count += 1
            yield {
                "type": "heartbeat",
                "data": {"count": heartbeat_count, "message": "Server is alive"},
            }

            event_count += 1

            # Wait before next event
            await asyncio.sleep(1)

            # Stop after 100 events for demo
            if event_count >= 100:
                break

    # Use Zenith's built-in SSE response helper
    return create_sse_response(event_generator())


@app.get("/events/infinite")
async def stream_infinite_events():
    """
    Stream infinite events for stress testing.

    Demonstrates backpressure handling with continuous streaming.
    """

    async def infinite_generator():
        counter = 0
        while True:
            counter += 1
            yield {"type": "counter", "data": {"value": counter}}

            # Small delay to avoid overwhelming
            if counter % 10 == 0:
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(0.01)

    return create_sse_response(infinite_generator())


if __name__ == "__main__":
    import uvicorn

    print("🌊 Starting Server-Sent Events Demo")
    print("📍 Open http://localhost:8000 in your browser")
    print("🔄 The page will auto-connect to the event stream")
    print("\n💡 Features demonstrated:")
    print("   • Real-time event streaming")
    print("   • Multiple event types")
    print("   • Automatic reconnection in browser")
    print("   • Built-in backpressure handling")
    print("   • Clean async generator pattern")

    uvicorn.run(app, host="0.0.0.0", port=8000)
