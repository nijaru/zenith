# Zenith Framework - Complete Project Specification (2025)

> **Zenith** is a modern Python web framework designed for building real-time APIs with exceptional developer experience and Phoenix-inspired architecture.

**CLI:** `zen` | **Package:** `zenith` | **Import:** `from zenith import ...`

---

## Vision & Goals (Updated)

**Primary Mission:** Create the most productive API-first framework for Python, combining Rails' developer happiness with Phoenix's real-time capabilities and modern performance.

**Core Goals:**
- **Real-time First**: Built-in LiveView-style server-rendered interactivity
- **Context-Driven Architecture**: Phoenix-inspired domain organization  
- **Contract-First Development**: OpenAPI as source of truth
- **Zero-Config Production**: Security, observability, scaling built-in
- **Progressive Enhancement**: Start simple, scale to enterprise
- **Mojo Acceleration Path**: Optional performance boosts without complexity

---

## Modern Framework Architecture (2025)

### Framework Kernel
```python
# Core systems that power everything
- Router: RESTful + real-time routes, async-first with pipelines
- Context System: Domain-driven organization (not vertical slices)
- LiveView Engine: Server-side rendering with WebSocket sync
- PubSub System: Built-in message passing and channels
- DI Container: Dependency injection with lifecycle management
- Pipeline Architecture: Composable middleware system
- Supervisor System: Fault tolerance and process management
```

### Context-Based Organization (Phoenix-Inspired)
```
app/
├── contexts/
│   ├── accounts/              # Complete accounts domain
│   │   ├── __init__.py       # Context interface/API
│   │   ├── models.py         # Data models
│   │   ├── queries.py        # Database queries/repository
│   │   ├── commands.py       # Write operations/business logic
│   │   ├── events.py         # Domain events
│   │   ├── policies.py       # Authorization rules
│   │   ├── channels.py       # Real-time channels
│   │   └── tests/
│   ├── catalog/              # Product catalog domain
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── ...
│   └── billing/              # Billing/payments domain
├── web/
│   ├── controllers/          # HTTP endpoints
│   │   ├── api/
│   │   └── live/            # LiveView controllers
│   ├── live/                # Real-time components
│   │   ├── user_dashboard.py
│   │   └── chat_room.py
│   ├── channels/            # WebSocket channels
│   ├── middleware/          # Request pipeline
│   └── templates/           # HTML templates (optional)
├── workers/                 # Background job workers
├── config/
│   ├── settings.py
│   ├── database.py
│   ├── channels.py          # PubSub/channel config
│   └── pipelines.py         # Middleware pipelines
└── lib/                     # Shared utilities
    ├── auth/
    ├── cache/
    └── observability/
```

### Revolutionary Features

#### 1. LiveView-Style Real-Time Components
```python
# live/user_dashboard.py
from zenith.live import LiveView, live_component
from zenith.events import subscribe, broadcast
from contexts.accounts import Accounts

class UserDashboard(LiveView):
    def mount(self, params, session, socket):
        user = Accounts.get_user(session["user_id"])
        
        # Subscribe to user-specific events
        subscribe(f"user:{user.id}")
        subscribe("global_announcements")
        
        socket.assign(
            user=user,
            notifications=[],
            active_sessions=Accounts.get_active_sessions(user.id)
        )
        return socket
    
    def handle_event("mark_notification_read", data, socket):
        notification_id = data["id"]
        Accounts.mark_notification_read(notification_id)
        
        # Update UI instantly
        notifications = [n for n in socket.assigns.notifications 
                        if n.id != notification_id]
        socket.assign(notifications=notifications)
        return socket
    
    def handle_info("new_notification", notification, socket):
        # Real-time notification from PubSub
        notifications = [notification] + socket.assigns.notifications
        socket.assign(notifications=notifications)
        return socket
    
    def render(self, assigns):
        return """
        <div class="dashboard">
            <h1>Welcome, {{ user.name }}</h1>
            
            <div class="notifications">
                {% for notification in notifications %}
                <div class="notification" 
                     zen-click="mark_notification_read" 
                     zen-value-id="{{ notification.id }}">
                    {{ notification.message }}
                </div>
                {% endfor %}
            </div>
            
            <!-- Real-time active sessions -->
            <live-component name="session_list" 
                            sessions="{{ active_sessions }}" />
        </div>
        """

# Usage in route
@live_route("/dashboard")
class DashboardRoute:
    component = UserDashboard
    auth_required = True
```

#### 2. Phoenix-Style Channels System
```python
# channels/user_channel.py
from zenith.channels import Channel
from zenith.auth import channel_auth

class UserChannel(Channel):
    @channel_auth
    def join(self, topic, params, socket):
        # topic format: "user:123"
        user_id = topic.split(":")[1]
        if socket.current_user.id == int(user_id):
            return {"ok": socket}
        else:
            return {"error": "unauthorized"}
    
    def handle_in("typing_start", params, socket):
        # Broadcast to other users that user is typing
        broadcast_from(socket, "typing_start", {
            "user": socket.current_user.name
        })
        return socket
    
    def handle_in("send_message", params, socket):
        message = ChatMessages.create_message({
            "user_id": socket.current_user.id,
            "content": params["message"],
            "room_id": params["room_id"]
        })
        
        # Broadcast new message to all room members
        broadcast(f"room:{params['room_id']}", "new_message", {
            "message": message.serialize(),
            "user": socket.current_user.serialize()
        })
        return socket

# Frontend JavaScript (auto-generated)
const socket = new ZenithSocket("/ws")
const channel = socket.channel("user:123")

channel.join()
    .receive("ok", () => console.log("Connected"))
    .receive("error", () => console.log("Failed to connect"))

channel.push("send_message", {message: "Hello!", room_id: 456})
channel.on("new_message", (payload) => {
    addMessageToUI(payload.message)
})
```

#### 3. Context API with Domain Events
```python
# contexts/accounts/__init__.py
from zenith.context import Context
from zenith.events import event_bus
from .models import User, Account
from .queries import UserQueries
from .commands import UserCommands

class Accounts(Context):
    """
    The Accounts context manages users, authentication, and account lifecycle.
    
    This is the public API that other contexts and web layers should use.
    All database access and business logic is encapsulated here.
    """
    
    # Queries (read operations)
    def get_user(self, user_id: int) -> User | None:
        return UserQueries.get_by_id(user_id)
    
    def list_users(self, filters: dict) -> list[User]:
        return UserQueries.list_with_filters(filters)
    
    def authenticate_user(self, email: str, password: str) -> User | None:
        return UserQueries.authenticate(email, password)
    
    # Commands (write operations)
    def create_user(self, attrs: dict) -> User:
        user = UserCommands.create(attrs)
        
        # Emit domain event
        event_bus.emit("user.created", {
            "user_id": user.id,
            "email": user.email,
            "timestamp": user.created_at
        })
        
        return user
    
    def update_user(self, user_id: int, attrs: dict) -> User:
        user = UserCommands.update(user_id, attrs)
        event_bus.emit("user.updated", {"user_id": user.id, "changes": attrs})
        return user
    
    def delete_user(self, user_id: int) -> bool:
        success = UserCommands.delete(user_id)
        if success:
            event_bus.emit("user.deleted", {"user_id": user_id})
        return success

# contexts/accounts/commands.py  
from zenith.database import transaction
from .models import User
from .events import UserCreated, UserUpdated

class UserCommands:
    @transaction
    def create(self, attrs: dict) -> User:
        # Validation, password hashing, etc.
        user = User.create(attrs)
        
        # Domain events for other contexts to react to
        UserCreated.emit(user)
        
        return user
    
    @transaction
    def update(self, user_id: int, attrs: dict) -> User:
        user = User.find(user_id)
        old_values = user.to_dict()
        user.update(attrs)
        
        UserUpdated.emit(user, old_values)
        return user

# Other contexts can listen to account events
# contexts/notifications/__init__.py
from zenith.events import event_listener
from .commands import NotificationCommands

class Notifications(Context):
    @event_listener("user.created")
    def send_welcome_email(self, event_data):
        user_id = event_data["user_id"]
        NotificationCommands.send_welcome_email(user_id)
    
    @event_listener("user.updated") 
    def log_profile_change(self, event_data):
        # Audit logging
        NotificationCommands.log_user_change(event_data)
```

#### 4. Modern Pipeline Architecture
```python
# config/pipelines.py
from zenith.pipeline import Pipeline
from zenith.middleware import *

# Define reusable middleware pipelines
api_pipeline = Pipeline([
    RateLimitMiddleware(requests=1000, window=3600),
    CORSMiddleware(origins=["https://myapp.com"]),
    AuthenticationMiddleware(),
    ValidationMiddleware(),
    ObservabilityMiddleware(),
    JSONResponseMiddleware()
])

admin_pipeline = Pipeline([
    HTTPSOnlyMiddleware(),
    AdminAuthMiddleware(require_2fa=True),
    AuditLoggingMiddleware(),
    CSRFProtectionMiddleware(),
    JSONResponseMiddleware()
])

live_pipeline = Pipeline([
    AuthenticationMiddleware(),
    LiveViewMiddleware(),
    PubSubMiddleware()
])

# web/controllers/api/users.py
from zenith import Controller, get, post, put, delete
from contexts.accounts import Accounts
from ..schemas import UserSchema, CreateUserSchema

@Controller("/api/v1/users", pipeline=api_pipeline)
class UsersController:
    @get("/")
    async def index(self, params) -> list[UserSchema]:
        users = Accounts.list_users(params.filters)
        return [UserSchema.from_orm(user) for user in users]
    
    @post("/", body=CreateUserSchema)
    async def create(self, data: CreateUserSchema) -> UserSchema:
        user = Accounts.create_user(data.model_dump())
        return UserSchema.from_orm(user)
    
    @put("/{user_id}")
    async def update(self, user_id: int, data: dict) -> UserSchema:
        user = Accounts.update_user(user_id, data)
        return UserSchema.from_orm(user)
```

#### 5. Built-in Admin Interface
```python
# Auto-generated admin interface
from zenith.admin import AdminSite, ModelAdmin
from contexts.accounts.models import User, Account

class UserAdmin(ModelAdmin):
    list_display = ["id", "email", "name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["email", "name"]
    readonly_fields = ["created_at", "updated_at"]
    
    def get_queryset(self):
        return User.query.select_related("account")

class AccountAdmin(ModelAdmin):
    list_display = ["name", "subscription_status", "created_at"]
    list_filter = ["subscription_status"]

# Register with admin site
admin_site = AdminSite(url_prefix="/admin")
admin_site.register(User, UserAdmin)
admin_site.register(Account, AccountAdmin)

# Automatically creates:
# GET /admin/users/          - List users with filters/search
# GET /admin/users/123/      - User detail view  
# GET /admin/users/123/edit/ - Edit form
# POST /admin/users/         - Create user
# etc.
```

#### 6. GraphQL Support (Optional)
```python
# GraphQL schema auto-generated from contexts
from zenith.graphql import GraphQLSchema, ObjectType, Field
from contexts.accounts import Accounts

class UserType(ObjectType):
    id = Field(int)
    email = Field(str)
    name = Field(str)
    
    @Field(list["Order"])
    def orders(self, user_id):
        return Orders.get_user_orders(user_id)

class Query(ObjectType):
    @Field(UserType)
    def user(self, user_id: int):
        return Accounts.get_user(user_id)
    
    @Field(list[UserType])
    def users(self, limit: int = 20):
        return Accounts.list_users({"limit": limit})

schema = GraphQLSchema(query=Query)

# Auto-mounted at /graphql with GraphiQL interface
```

---

## CLI Commands & Workflows (Enhanced)

### Project Generation with Templates
```bash
# Create new projects with different templates
zen new myapp --template=api            # API-only template
zen new blog --template=fullstack       # With LiveView components
zen new saas --template=multi-tenant     # Multi-tenant SaaS
zen new microservice --template=minimal  # Minimal microservice

# Generate complete contexts (not just resources)
zen generate context Accounts users name:str email:str:unique
zen generate context Catalog products title:str price:decimal category:foreign
zen generate context Billing subscriptions plan:str status:enum

# Generate LiveView components
zen generate live UserDashboard --context=Accounts
zen generate live ProductCatalog --context=Catalog --auth

# Generate channels and real-time features
zen generate channel UserChannel --context=Accounts
zen generate channel ChatChannel --context=Messages

# Advanced generators
zen generate admin UserAdmin --model=User
zen generate graphql UserSchema --context=Accounts
zen generate webhook StripeWebhook --events=payment.succeeded,payment.failed
```

### Enhanced Development Tools
```bash
# Development server with multiple modes
zen server                              # Standard development server
zen server --live                       # With LiveView hot reload
zen server --admin                      # Include admin interface
zen server --graphql                    # Include GraphQL playground

# Real-time debugging and monitoring
zen console                             # Interactive console
zen channels list                       # Show active channels
zen channels broadcast user:123 "message" # Test channel broadcasting
zen live sessions                       # Show active LiveView sessions

# Database operations with migrations
zen db create                           # Create database  
zen db migrate "add user preferences"   # Create & run migration
zen db seed --context=Accounts          # Seed specific context data
zen db console                          # Database console

# Testing with real-time support  
zen test                                # Run all tests
zen test --live                         # Test LiveView components
zen test --channels                     # Test channel functionality
zen test --integration                  # Full integration tests

# Production deployment
zen deploy prepare                      # Prepare production assets
zen deploy check                        # Check deployment readiness
zen deploy migrate                      # Run pending migrations
```

### Client Generation & Documentation
```bash
# Enhanced API documentation
zen docs generate                       # Generate OpenAPI + GraphQL docs
zen docs serve                          # Interactive documentation server
zen docs export --format=postman       # Export Postman collection

# Client SDK generation with real-time support
zen client generate typescript --realtime  # Include WebSocket client
zen client generate python --async         # Async Python client
zen client generate swift --combine         # iOS SDK with GraphQL + REST
zen client generate kotlin --realtime      # Android SDK with channels

# API testing and validation
zen api test                            # Run API contract tests  
zen api validate                        # Validate OpenAPI compliance
zen api benchmark                       # Performance benchmarking
```

---

## Production Features (Enterprise-Ready)

### Built-in Observability
```python
# Automatic tracing and metrics
from zenith.observability import trace, metric, log

@trace("user.creation")
@metric.counter("users.created")
class UserCommands:
    def create(self, attrs: dict) -> User:
        with log.context(user_email=attrs["email"]):
            # Automatically traced with:
            # - Request ID correlation
            # - Database query performance  
            # - External API call latency
            # - Error tracking with stack traces
            
            user = User.create(attrs)
            
            # Custom metrics
            metric.histogram("user.registration_time", 
                           labels={"method": "email"})
            
            return user

# Health checks with dependency monitoring
@zen_health_check
def database_health():
    return Database.ping()

@zen_health_check  
def redis_health():
    return Redis.ping()

@zen_health_check
def external_api_health():
    return ExternalAPI.status()

# Automatic endpoints:
# GET /health            - Overall health
# GET /health/ready      - Readiness probe
# GET /health/live       - Liveness probe  
# GET /metrics           - Prometheus metrics
```

### Security by Default
```python
# Automatic security headers and protection
SECURITY_CONFIG = {
    "rate_limiting": {
        "global": {"requests": 1000, "window": 3600},
        "per_user": {"requests": 100, "window": 3600},
        "endpoints": {
            "/api/auth/login": {"requests": 5, "window": 900}
        }
    },
    "content_security_policy": {
        "default_src": ["'self'"],
        "script_src": ["'self'", "'unsafe-inline'"],  # For LiveView
        "connect_src": ["'self'", "ws:", "wss:"]      # For WebSockets
    },
    "cors": {
        "allowed_origins": ["https://myapp.com"],
        "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_credentials": True
    }
}

# Built-in authentication with multiple strategies
from zenith.auth import JWTAuth, SessionAuth, OAuth2

auth = JWTAuth(
    secret_key=settings.JWT_SECRET,
    refresh_token_ttl=7 * 24 * 3600,  # 7 days
    access_token_ttl=3600,            # 1 hour
    auto_refresh=True
)

# OAuth2 providers
oauth = OAuth2(
    google=GoogleProvider(client_id="...", client_secret="..."),
    github=GitHubProvider(client_id="...", client_secret="..."),
    microsoft=MicrosoftProvider(client_id="...", client_secret="...")
)
```

### Multi-Tenancy Support
```python
# Built-in multi-tenancy patterns
from zenith.tenancy import TenantMiddleware, tenant_context

class TenantMiddleware:
    def process_request(self, request):
        # Extract tenant from subdomain, header, or JWT
        tenant = self.extract_tenant(request)
        tenant_context.set(tenant)

# Automatic tenant scoping in models
class User(TenantScopedModel):
    tenant_id = Column(Integer, nullable=False, index=True)
    email = Column(String, nullable=False)
    
    # Automatic tenant filtering
    __tenant_scope__ = "tenant_id"

# Context methods automatically scoped
class Accounts(Context):
    def list_users(self) -> list[User]:
        # Automatically filters by current tenant
        return UserQueries.list_all()  # Only returns current tenant's users
    
    def get_user(self, user_id: int) -> User | None:
        # Prevents cross-tenant data access
        return UserQueries.get_by_id(user_id)  # Validates tenant access
```

### Event Sourcing & CQRS (Optional)
```python
# Event sourcing for complex domains
from zenith.events import EventStore, Aggregate, Event

class UserAggregate(Aggregate):
    def __init__(self):
        self.user_id = None
        self.email = None
        self.is_active = True
    
    def create_user(self, user_id: str, email: str):
        self.apply(UserCreated(user_id=user_id, email=email))
    
    def deactivate_user(self):
        if not self.is_active:
            raise UserAlreadyDeactivated()
        self.apply(UserDeactivated(user_id=self.user_id))

# Event handlers update read models  
@event_handler("UserCreated")
def create_user_read_model(event: UserCreated):
    UserReadModel.create(
        user_id=event.user_id,
        email=event.email,
        created_at=event.timestamp
    )

# CQRS command/query separation
class UserCommands:
    def create_user(self, command: CreateUserCommand):
        aggregate = UserAggregate()
        aggregate.create_user(command.user_id, command.email)
        EventStore.save(aggregate)

class UserQueries:
    def get_user(self, user_id: str) -> UserReadModel:
        return UserReadModel.get(user_id)
```

---

## Framework Package Structure (Updated)

```
zenith/                               # Main framework package
├── core/
│   ├── __init__.py                   # Main exports (get, post, Context, LiveView)
│   ├── app.py                        # Application class with supervisor tree
│   ├── context.py                    # Context base class and registration
│   ├── pipeline.py                   # Middleware pipeline system
│   └── events.py                     # Event bus and domain events
├── web/
│   ├── routing.py                    # Router with pipeline support
│   ├── controllers.py                # Controller base classes
│   ├── middleware/                   # Built-in middleware collection
│   └── decorators.py                 # Route decorators (@get, @post, etc.)
├── live/                             # LiveView system
│   ├── view.py                       # LiveView base class
│   ├── component.py                  # LiveComponent for composition
│   ├── socket.py                     # WebSocket connection management
│   └── rendering.py                  # Template rendering with diffs
├── channels/                         # Phoenix-style channels
│   ├── channel.py                    # Channel base class
│   ├── socket.py                     # Channel socket
│   ├── presence.py                   # User presence tracking
│   └── pubsub.py                     # PubSub system (Redis backend)
├── database/
│   ├── orm.py                        # Enhanced SQLAlchemy integration
│   ├── migrations/                   # Migration system
│   ├── query.py                      # Query builder with tenant scoping
│   └── transactions.py               # Transaction management
├── auth/
│   ├── strategies/                   # JWT, session, OAuth2 strategies
│   ├── middleware.py                 # Authentication middleware
│   ├── policies.py                   # Authorization policies
│   └── channels.py                   # Channel authentication
├── admin/
│   ├── site.py                       # Admin site with auto-discovery
│   ├── views.py                      # CRUD views with customization
│   ├── forms.py                      # Auto-generated forms
│   └── templates/                    # Admin HTML templates
├── graphql/                          # GraphQL integration
│   ├── schema.py                     # Schema auto-generation
│   ├── resolvers.py                  # Resolver base classes
│   └── playground.py                 # GraphiQL interface
├── jobs/
│   ├── queue.py                      # Multi-queue job system
│   ├── scheduler.py                  # Cron scheduling with clustering
│   ├── workers.py                    # Worker process management
│   └── workflows.py                  # Multi-step job workflows
├── cache/
│   ├── backends/                     # Redis, in-memory, distributed
│   ├── decorators.py                 # Caching helpers
│   └── invalidation.py               # Smart cache invalidation
├── storage/
│   ├── backends/                     # S3, GCS, local, CDN
│   ├── uploads.py                    # File upload handling
│   └── media.py                      # Image/video processing
├── search/
│   ├── backends/                     # Elasticsearch, Solr integration
│   ├── indexing.py                   # Auto-indexing from models
│   └── queries.py                    # Search query builders
├── observability/
│   ├── tracing.py                    # OpenTelemetry integration
│   ├── metrics.py                    # Prometheus metrics
│   ├── logging.py                    # Structured logging
│   └── profiling.py                  # Performance profiling
├── security/
│   ├── rate_limiting.py              # Advanced rate limiting
│   ├── encryption.py                 # Field-level encryption
│   ├── audit.py                      # Audit logging
│   └── compliance.py                 # GDPR, SOX compliance helpers
├── tenancy/
│   ├── middleware.py                 # Multi-tenant request handling
│   ├── models.py                     # Tenant-scoped model base
│   └── isolation.py                  # Data isolation strategies
├── integrations/
│   ├── stripe.py                     # Payment processing
│   ├── sendgrid.py                   # Email services
│   ├── twilio.py                     # SMS/voice services
│   └── webhooks.py                   # Webhook handling system
├── testing/
│   ├── client.py                     # Enhanced test client
│   ├── live.py                       # LiveView testing helpers
│   ├── channels.py                   # Channel testing utilities
│   └── factories.py                  # Data factory system
├── cli/
│   ├── __main__.py                   # CLI entrypoint
│   ├── commands/                     # All CLI commands
│   │   ├── new.py                    # Project generation
│   │   ├── generate.py               # Context/component generation
│   │   ├── live.py                   # LiveView management
│   │   ├── channels.py               # Channel debugging
│   │   └── deploy.py                 # Deployment helpers
│   └── templates/                    # Enhanced code generation
└── accel/                            # Mojo integration (future)
    ├── protocol.py                   # Performance interface contracts
    ├── serializers.py                # Fast JSON/msgpack serialization
    └── compute.py                    # CPU/GPU acceleration
```

---

## Installation & Getting Started

```bash
# Install framework
pip install zenith                    # Basic framework
pip install zenith[full]              # All integrations
pip install zenith[mojo]              # With Mojo accelerators (future)

# Create new project
zen new myapp --template=fullstack
cd myapp

# Generate your first context
zen generate context Accounts users email:str name:str

# Start development server
zen server --live                      # With hot reload and LiveView
```

This updated specification incorporates modern framework patterns, addresses the naming collision, and provides a comprehensive roadmap for building a truly competitive framework in 2025. The Phoenix-inspired architecture with LiveView-style real-time capabilities and context organization will differentiate it significantly from existing Python frameworks.