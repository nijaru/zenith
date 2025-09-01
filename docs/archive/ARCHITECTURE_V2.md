# Zenith Framework Architecture V2
*The optimal blend of Python, Rails, and Phoenix*

## Design Philosophy

### 🐍 Modern Python First
- **Type safety everywhere** - Full type hints, Pydantic models
- **Async/await native** - Built on asyncio, structured concurrency  
- **Decorator-based APIs** - Clean, familiar Python patterns
- **Explicit over implicit** - Clear behavior, good error messages

### 🛤️ Rails Developer Experience
- **Convention over configuration** - Smart defaults, minimal setup
- **Code generators** - `zen generate` for scaffolding
- **Database migrations** - Version control for schema changes
- **Interactive development** - Hot reloading, console, debugging

### ⚡ Phoenix Real-time Innovation  
- **LiveView engine** - Server-rendered interactive UIs
- **Channels system** - WebSocket communication
- **Context boundaries** - Clean business logic separation
- **Event-driven** - Decoupled components via PubSub

## Architecture Overview

```python
# Modern Python: Type-safe, decorator-based
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    accounts: Accounts = Context(),
    current_user: User = Auth()
) -> UserResponse:
    user = await accounts.get_user(user_id)
    return UserResponse.model_validate(user)

# Rails DX: Convention-based file structure
app/
├── contexts/          # Business logic (Phoenix contexts)
│   ├── accounts.py    # User management
│   └── billing.py     # Payment processing
├── controllers/       # HTTP endpoints (Rails controllers)
│   ├── api/
│   └── web/
├── live/             # Real-time UIs (Phoenix LiveView)
│   ├── dashboard.py
│   └── chat.py
├── channels/         # WebSocket handlers (Phoenix channels)
├── models/           # Pydantic data models
└── templates/        # HTML templates

# Phoenix Real-time: LiveView without JavaScript
class DashboardLive(LiveView):
    async def mount(self, params: dict, session: dict, socket: Socket):
        socket.assign(count=0, user_id=session["user_id"])
        return socket
    
    async def handle_event(self, "increment", _payload, socket):
        socket.assign(count=socket.assigns.count + 1)
        return socket
    
    def render(self, assigns: dict) -> str:
        return '''
        <div>
            <h1>Count: {{ assigns.count }}</h1>
            <button zen-click="increment">+</button>
        </div>
        '''
```

## Key Design Decisions

### 1. Type-Based Dependency Injection

**Problem:** FastAPI's `Depends()` is powerful but verbose
**Solution:** Context managers with type hints

```python
# Clean, type-safe context injection
async def create_user(
    data: UserCreate,
    accounts: Accounts = Context(),  # Auto-injected
    db: Database = Database(),       # Type-based DI
    current_user: User = Auth()      # Authentication
) -> User:
    return await accounts.create_user(data, created_by=current_user)
```

### 2. Pydantic Everywhere

**Problem:** Mix of validation libraries creates inconsistency  
**Solution:** Single source of truth for all data

```python
# Configuration
class Config(BaseSettings):
    database_url: PostgresDsn
    redis_url: RedisDsn
    secret_key: SecretStr

# Request/Response models  
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)

class User(BaseModel):
    id: int
    email: str
    created_at: datetime

# Database models (with Pydantic validation)
class UserTable(Table):
    id: int = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. Convention-Driven File Discovery

**Problem:** Manual registration is tedious
**Solution:** Automatic discovery with conventions

```python
# Auto-discovers and registers:
app/contexts/accounts.py     → AccountsContext
app/controllers/api/users.py → UsersController  
app/live/dashboard.py        → DashboardLive
app/channels/chat.py         → ChatChannel

# With type-safe imports
from app.contexts import Accounts  # Type checking works
```

### 4. Simplified Supervision

**Problem:** Phoenix supervision is overkill for most Python apps
**Solution:** Optional supervision with sensible defaults

```python
# Simple mode (default) - just async tasks
app = Zenith()

# Supervised mode (for production systems)
app = Zenith(supervisor=True)

# Custom supervision (for complex apps)  
app = Zenith(supervisor=SupervisorConfig(
    max_restarts=5,
    restart_policy="one_for_one"
))
```

### 5. Rails-Style Generators

**Problem:** Boilerplate setup is tedious
**Solution:** Intelligent code generation

```bash
# Generates complete CRUD setup
zen generate resource User email:str name:str --live
# Creates:
# - app/models/user.py (Pydantic model)  
# - app/contexts/users.py (business logic)
# - app/controllers/users.py (HTTP endpoints)
# - app/live/users/ (LiveView CRUD interface)
# - tests/ (comprehensive test suite)
# - migrations/ (database schema)

zen generate liveview Chat --channel
# Creates LiveView + Channel for real-time features
```

### 6. Modern Python Features Integration

```python
# Python 3.11+ Structured Concurrency
async with asyncio.TaskGroup() as tg:
    user_task = tg.create_task(fetch_user(user_id))
    perms_task = tg.create_task(fetch_permissions(user_id))
    
# Python 3.10+ Pattern Matching for Events
match event:
    case {"type": "user.created", "data": user_data}:
        await send_welcome_email(user_data)
    case {"type": "payment.completed", "data": payment_data}:  
        await update_subscription(payment_data)

# Context managers everywhere
async with app.lifespan():
    async with db.transaction():
        user = await accounts.create_user(data)
        await billing.setup_trial(user)
```

## Framework Comparison

| Feature | FastAPI | Rails | Phoenix | **Zenith** |
|---------|---------|--------|---------|------------|
| Type Safety | ✅ | ❌ | ⚠️ | ✅ |
| Real-time UI | ❌ | ❌ | ✅ | ✅ |  
| Code Gen | ❌ | ✅ | ✅ | ✅ |
| DX/Magic | ⚠️ | ✅ | ✅ | ✅ |
| Async Native | ✅ | ❌ | ✅ | ✅ |
| Fault Tolerance | ❌ | ❌ | ✅ | ⚠️ |

## Development Workflow

```bash
# Create new app (Rails-style)
zen new my_app
cd my_app

# Generate resources (Rails-style)  
zen generate context Accounts User email:str
zen generate liveview Dashboard
zen generate controller API::Users

# Database operations (Rails-style)
zen db create
zen db migrate
zen db seed

# Development server (with hot reload)
zen server --reload

# Interactive console (Rails-style)
zen console
>>> user = await Accounts().create_user({"email": "test@example.com"})

# Testing
zen test
zen test --coverage
```

## Migration Path

### Phase 1: Enhanced Routing (ZEN-2)
- FastAPI-style decorators
- Type-based dependency injection  
- Pydantic request/response models

### Phase 2: LiveView Engine (ZEN-4)
- Server-rendered interactive UIs
- WebSocket integration
- Template engine

### Phase 3: Rails DX Features  
- Code generators
- Database migrations
- Interactive console

### Phase 4: Production Features
- Simplified supervision  
- PubSub system
- Deployment tooling

---
*Zenith: The best of Python, Rails, and Phoenix in one framework*