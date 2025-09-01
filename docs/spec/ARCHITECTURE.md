# System Architecture

## Core Architecture

```
┌─────────────────────────────────────────────────┐
│                 Client Layer                     │  
│  Browser (HTML/JS) ←→ WebSocket ←→ HTTP          │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│                 Web Layer                        │
│  ┌─────────┐ ┌──────────┐ ┌─────────────────┐   │
│  │LiveViews│ │Controllers│ │    Channels     │   │
│  └─────────┘ └──────────┘ └─────────────────┘   │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│                Core Layer                        │
│  ┌─────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │
│  │Contexts │ │ Router │ │ PubSub │ │Pipeline │  │
│  └─────────┘ └────────┘ └────────┘ └─────────┘  │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│                Data Layer                        │
│  ┌──────────────┐ ┌─────────────────────────┐   │
│  │ PostgreSQL   │ │        Redis            │   │
│  │ (Persistence)│ │ (PubSub, Cache, Session)│   │
│  └──────────────┘ └─────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Component Details

### Application Kernel

**Responsibilities:**
- Process supervision and fault tolerance
- Dependency injection container
- Configuration management
- Application lifecycle

```python
class Application:
    def __init__(self, config: Config):
        self.supervisor = Supervisor()      # Fault tolerance
        self.container = DIContainer()      # Dependencies  
        self.contexts = ContextRegistry()   # Business logic
        self.router = Router()              # Request routing
        self.pubsub = PubSub()             # Internal messaging
        
    async def start(self):
        await self.supervisor.start_tree()
```

### Context System

**Purpose:** Domain-driven business logic organization

```python
class Context:
    """Base class for business contexts."""
    
    def __init__(self, container: DIContainer):
        self.repo = container.get(Repository)
        self.events = container.get(EventBus)
    
    async def emit(self, event: str, data: Any):
        """Emit domain event for other contexts."""
        await self.events.emit(event, data)
```

**Context Boundaries:**
- Each context owns a specific domain
- Contexts communicate via events, not direct calls
- Public API explicitly defined
- Private implementation details hidden

### Router & Pipeline

**Request Flow:**
```
Request → Middleware Pipeline → Route Handler → Response
```

**Pipeline Composition:**
```python
api_pipeline = Pipeline([
    RateLimitMiddleware(1000, 3600),  # Rate limiting
    AuthMiddleware(),                 # Authentication  
    ValidationMiddleware(),           # Input validation
    LoggingMiddleware()               # Request logging
])
```

### LiveView Engine

**Real-time UI without JavaScript:**

```python
class CounterLive(LiveView):
    async def mount(self, params, session, socket):
        socket.assign(count=0)
        return socket
    
    async def handle_event(self, "increment", payload, socket):
        socket.assign(count=socket.assigns.count + 1)
        return socket  # Auto-renders and sends diff
```

**Lifecycle:**
1. HTTP request → Full page render
2. WebSocket upgrade
3. User interaction → Server event
4. State update → DOM diff → Client patch

### Channels System

**WebSocket Communication:**

```python
class ChatChannel(Channel):
    async def join(self, topic, params, socket):
        # Authorize user for topic
        if self.can_join(socket.user, topic):
            return {"ok": True}
        return {"error": "unauthorized"}
    
    async def handle_in(self, "new_message", payload, socket):
        # Process incoming message
        message = await self.create_message(payload)
        # Broadcast to all subscribers
        await self.broadcast("message", message)
```

### PubSub System

**Internal Event Bus:**

```python
# Context emits event
await self.emit("user.created", {"user_id": user.id})

# Other contexts listen
@event_listener("user.created")
async def send_welcome_email(event_data):
    user_id = event_data["user_id"]
    await EmailService.send_welcome(user_id)
```

## Data Flow Patterns

### Synchronous Request/Response

```
1. HTTP Request
2. Router matches route  
3. Pipeline processes middleware
4. Controller calls Context
5. Context performs business logic
6. Context returns data
7. Controller formats response
8. Pipeline post-processes
9. Response sent
```

### Asynchronous Real-time (LiveView)

```
1. Initial HTTP request
2. Full page render + WebSocket upgrade
3. User interaction → WebSocket event
4. LiveView processes event
5. State update triggers re-render
6. DOM diff calculated
7. Minimal patch sent to client
8. Client applies DOM changes
```

### Event-Driven (Context Communication)

```
1. Context A performs operation
2. Context A emits domain event
3. Event bus routes to subscribers  
4. Context B receives event
5. Context B reacts accordingly
6. UI components updated via PubSub
```

## Scalability Patterns

### Horizontal Scaling

```
    Load Balancer
         │
   ┌─────┼─────┐
   │     │     │
Server1 Server2 Server3
   │     │     │  
   └─────┼─────┘
         │
    Redis Cluster
  (Shared PubSub)
```

**Considerations:**
- Sticky sessions for WebSockets
- Redis PubSub for cross-server communication
- Stateless HTTP handlers
- Database connection pooling

### Performance Optimizations

1. **Connection Pooling**: Database and Redis connections
2. **Query Batching**: Avoid N+1 queries  
3. **Caching Layers**: Memory → Redis → Database
4. **Async I/O**: Non-blocking operations throughout
5. **Message Queuing**: Background job processing

## Security Architecture

### Defense Layers

```
Internet → CDN → WAF → Load Balancer → App Server
                                           ↓
                                    Security Middleware
                                           ↓  
                                     Application Logic
```

### Built-in Protections

- **CSRF**: Automatic token validation
- **XSS**: Template auto-escaping
- **SQL Injection**: Parameterized queries only
- **Rate Limiting**: Per-endpoint and per-user
- **Secure Headers**: Automatic security headers
- **Input Validation**: Schema-based validation

## Deployment Architecture

### Container-Based Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["zen", "server", "--prod"]
```

### Environment Configuration

```python
# All config from environment
DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]  
SECRET_KEY = os.environ["SECRET_KEY"]

# Health checks
@health_check
async def database_ready():
    return await db.ping()
```

### Observability

```python
# Built-in tracing and metrics
@trace("user.creation")
@metric("users.created")  
async def create_user(data):
    with log_context(email=data["email"]):
        user = await User.create(data)
        return user
```

## Extension Points

### Custom Middleware

```python
class CustomMiddleware:
    async def __call__(self, request, next):
        # Pre-processing
        start_time = time.time()
        response = await next(request)  
        # Post-processing
        response.headers["X-Response-Time"] = str(time.time() - start_time)
        return response
```

### Context Mixins

```python
class CacheableMixin:
    @cache(ttl=300)
    async def cached_operation(self, key):
        return await self.expensive_operation(key)

class UserContext(Context, CacheableMixin):
    ...
```

### LiveView Components

```python
@live_component  
class SearchBox:
    async def update(self, assigns, socket):
        results = await self.search(assigns["query"])
        socket.assign(results=results)
        return socket
```

---
*Detailed system architecture for Zenith Framework*