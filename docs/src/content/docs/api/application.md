---
title: Application API
description: Complete reference for the Zenith application class, routing, and dependency injection
---

## Zenith Application

The `Zenith` class is your application's foundation. It provides everything you need to build production-ready APIs with minimal configuration.

### Why Zenith?

Traditional frameworks require extensive setup code for basic features. Zenith provides intelligent defaults that work for most applications, while still allowing complete customization when needed.

## Creating an Application

### Zero-Configuration Setup (v0.1.0+)

The simplest way to create a Zenith application - automatic configuration based on your environment:

```python
from zenith import Zenith

# Zero-config: Zenith detects your environment and configures everything
app = Zenith()

# What this gives you automatically:
# - SQLite database in development, PostgreSQL/MySQL in production
# - Permissive CORS in development, secure CORS in production
# - Auto-generated secret key in development, requires SECRET_KEY in production
# - Debug mode in development, optimized mode in production
# - Hot reload in development, multi-worker in production
```

### Customized Setup

For applications that need specific configuration:

```python
from zenith import Zenith

app = Zenith(
    # Basic metadata - shown in API documentation
    title="My API",              # API name in docs (default: "Zenith API")
    version="2.0.0",            # API version (default: "1.0.0")
    description="Production API", # Detailed description (default: None)

    # Development settings
    debug=False,                # Disable debug mode for production (default: False)

    # Startup/shutdown hooks for resource management
    on_startup=[init_database],    # Functions to run on startup
    on_shutdown=[cleanup_resources] # Functions to run on shutdown
)
```

### Chain Features with Convenience Methods

Zenith v0.1.0+ provides chainable methods to add common features with one line:

```python
# Each method returns the app, allowing chaining
app = (Zenith()
    .add_auth()           # Adds JWT auth + /auth/login, /auth/register endpoints
    .add_admin()          # Adds admin dashboard at /admin
    .add_api("My API", "1.0.0", "API description"))  # Adds /docs and /redoc

# What each method adds:
# .add_auth() provides:
#   - POST /auth/register - User registration
#   - POST /auth/login - User login with JWT token
#   - POST /auth/refresh - Token refresh
#   - Auth dependency for protected routes

# .add_admin() provides:
#   - GET /admin - Admin dashboard
#   - Health monitoring
#   - Request metrics
#   - System information

# .add_api() provides:
#   - GET /docs - Swagger UI documentation
#   - GET /redoc - ReDoc documentation
#   - GET /openapi.json - OpenAPI schema
```

## Route Decorators

Route decorators define your API endpoints. Each HTTP method has its own decorator with sensible defaults.

### GET Requests

```python
@app.get(
    "/items",                    # URL path (required)
    response_model=List[Item],   # Response type for validation/docs (optional)
    status_code=200,            # HTTP status code (default: 200)
    tags=["items"],             # API documentation grouping (optional)
    summary="List items",        # Short description for docs (optional)
    description="Get all items", # Detailed description (optional)
)
async def get_items(
    # Query parameters are automatically parsed from URL
    skip: int = 0,              # ?skip=10 becomes skip=10
    limit: int = 100,           # ?limit=50 becomes limit=50
    search: str | None = None   # Optional query parameter
):
    """
    Function docstring becomes description if not provided above.
    Type hints are used for validation and documentation.
    """
    return []  # Return value is validated against response_model
```

### POST Requests

```python
from pydantic import BaseModel

class ItemCreate(BaseModel):
    """Request body model - validated automatically."""
    name: str
    price: float
    tax: float | None = None

@app.post(
    "/items",
    response_model=Item,        # Response validation
    status_code=201,            # 201 Created is default for POST
)
async def create_item(
    item: ItemCreate,           # Request body is parsed and validated
    user=Auth,                  # Current authenticated user (if using auth)
    db=DB                       # Database session (if configured)
):
    """
    POST endpoints typically:
    1. Validate input data (automatic via Pydantic)
    2. Process/save data
    3. Return created resource with 201 status
    """
    # item is already validated ItemCreate instance
    return {"id": 1, **item.model_dump()}
```

### Path Parameters

```python
@app.get("/items/{item_id}")
async def get_item(
    item_id: int,               # Path parameter with type validation
    # {item_id} in path must match parameter name
):
    """
    Path parameters:
    - Extracted from URL path
    - Type validated automatically
    - 422 error if validation fails
    """
    return {"item_id": item_id}

@app.put("/users/{user_id}/posts/{post_id}")
async def update_post(
    user_id: int,               # Multiple path parameters supported
    post_id: str,               # Different types allowed
    updates: dict               # Request body for PUT
):
    """Complex paths with multiple parameters."""
    return {"user": user_id, "post": post_id}
```

### DELETE Requests

```python
@app.delete(
    "/items/{item_id}",
    status_code=204,            # 204 No Content for successful deletes
)
async def delete_item(item_id: int):
    """
    DELETE typically returns:
    - 204 No Content (no body) for successful deletion
    - 404 if resource doesn't exist
    """
    # Perform deletion
    return None  # 204 responses have no body
```

## Middleware

Middleware processes every request/response, adding cross-cutting functionality like security, logging, and performance monitoring.

### Adding Middleware

```python
from zenith.middleware import (
    CORSMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)

# Method 1: Add individually with configuration
app.add_middleware(
    CORSMiddleware,
    # Configuration as keyword arguments
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True
)

# Method 2: Using config classes (recommended for complex config)
from zenith.middleware import CORSConfig

config = CORSConfig(
    allow_origins=["https://example.com"],
    allow_origin_regex=r"https://.*\.example\.com",  # Regex patterns
    max_age_secs=86400  # Cache preflight for 24 hours
)
app.add_middleware(CORSMiddleware, config=config)

# Method 3: Multiple middleware at initialization
app = Zenith(
    middleware=[
        # Order matters! Last in list executes first
        SecurityHeadersMiddleware(),  # Runs third
        RateLimitMiddleware(requests=100, per="minute"),  # Runs second
        CORSMiddleware(allow_origins=["*"])  # Runs first
    ]
)
```

### Middleware Execution Order

```python
# Middleware runs in LIFO order (Last In, First Out)
app.add_middleware(LoggingMiddleware)    # Added first, runs last
app.add_middleware(AuthMiddleware)       # Added second, runs second
app.add_middleware(SecurityMiddleware)   # Added last, runs first

# Request flow:
# Client -> SecurityMiddleware -> AuthMiddleware -> LoggingMiddleware -> Route
# Response flows back in reverse order
```

### Common Middleware Patterns

```python
# Development setup - permissive for testing
if app.debug:
    app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Production setup - restrictive for security
else:
    app.add_middleware(
        SecurityHeadersMiddleware,
        force_https=True,
        hsts_max_age=31536000  # 1 year
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://myapp.com"],
        allow_credentials=True
    )
    app.add_middleware(
        RateLimitMiddleware,
        requests=100,
        per="minute",
        # Different limits per endpoint
        routes={
            "/api/expensive": "10/hour",
            "/api/cheap": "1000/minute"
        }
    )
```

## Routers

Routers organize related endpoints into modules, keeping your code maintainable as it grows.

```python
from zenith import Router

# Create a router for user-related endpoints
users_router = Router(
    prefix="/users",     # All routes will be prefixed with /users
    tags=["users"]       # Group in API documentation
)

@users_router.get("")    # Becomes GET /users
async def list_users():
    return []

@users_router.get("/{user_id}")  # Becomes GET /users/{user_id}
async def get_user(user_id: int):
    return {"id": user_id}

@users_router.post("")   # Becomes POST /users
async def create_user(user: UserCreate):
    return user

# Include router in main app
app.include_router(users_router)

# Include multiple routers with different prefixes
app.include_router(posts_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/admin", tags=["admin"])
```

## WebSocket Support

WebSockets enable real-time, bidirectional communication for features like chat, notifications, and live updates.

```python
from zenith import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Basic WebSocket echo server."""
    # Accept the connection
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            # Send response back
            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        # Client disconnected
        print("Client disconnected")

# WebSocket with path parameters
@app.websocket("/ws/{room_id}")
async def room_websocket(
    websocket: WebSocket,
    room_id: str  # Path parameters work like regular routes
):
    await websocket.accept()
    await websocket.send_json({
        "type": "welcome",
        "room": room_id
    })
```

## Static Files and SPAs

Zenith makes it easy to serve static files and single-page applications alongside your API.

### Static Files

```python
# Serve static files from a directory
app.mount_static(
    "/static",           # URL prefix
    directory="static",  # Directory path
    max_age=3600        # Cache for 1 hour
)

# Now /static/logo.png serves ./static/logo.png
```

### Single-Page Applications (SPAs)

```python
# Method 1: Auto-detect common build directories
app.spa()  # Looks for dist/, build/, or public/

# Method 2: Specify framework for smart defaults
app.spa("react")     # Looks for build/ (Create React App default)
app.spa("vue")       # Looks for dist/ (Vue CLI default)
app.spa("solidjs")   # Looks for dist/ (SolidJS default)

# Method 3: Custom directory with options
app.spa(
    directory="frontend/dist",
    index="app.html",           # Custom index file
    max_age=86400,              # Cache static assets for 24 hours
    exclude=["/api/*", "/ws/*"] # Don't serve SPA for these paths
)

# The SPA middleware:
# 1. Serves static files from the directory
# 2. Falls back to index.html for client-side routing
# 3. Excludes API routes to prevent interference
```

## Dependency Injection

Dependency injection provides clean, testable code by automatically supplying required dependencies to your route handlers.

### Basic Injection

```python
from zenith.core import DB, Auth, Cache

@app.get("/profile")
async def get_profile(
    user=Auth,      # Current authenticated user (replaces Depends(get_current_user))
    db=DB,          # Database session (replaces Depends(get_db))
    cache=Cache     # Cache client (replaces Depends(get_cache))
):
    """
    Zenith's shortcuts make code cleaner:
    - Auth: Current user or 401 if not authenticated
    - DB: Request-scoped database session
    - Cache: Redis or memory cache client
    """
    profile = await db.get(User, user.id)
    return profile
```

### Service Injection

Services organize business logic separate from web concerns:

```python
from zenith import Service, Inject

class EmailService(Service):
    """Business logic for sending emails."""

    def __init__(self, config: EmailConfig):
        self.smtp = SMTPClient(config)

    async def send_welcome_email(self, user: User):
        """Send welcome email to new user."""
        await self.smtp.send(
            to=user.email,
            subject="Welcome!",
            body=render_template("welcome.html", user=user)
        )

class UserService(Service):
    """Business logic for user operations."""

    def __init__(self, email: EmailService):
        # Services can depend on other services
        self.email = email

    async def create_user(self, data: UserCreate) -> User:
        """Create user and send welcome email."""
        user = await User.create(**data.model_dump())
        await self.email.send_welcome_email(user)
        return user

# Use in routes
@app.post("/users")
async def create_user(
    data: UserCreate,
    users: UserService = Inject()  # Automatically injected with dependencies
):
    """
    Inject() automatically:
    1. Creates EmailService with config
    2. Creates UserService with EmailService
    3. Provides it to your route
    """
    user = await users.create_user(data)
    return {"user": user.to_dict()}
```

### Custom Dependencies

Create your own injectable dependencies:

```python
from zenith import Depends

# Dependency function
async def get_current_company(
    user=Auth,  # Dependencies can use other dependencies
    db=DB
) -> Company:
    """Get the current user's company."""
    return await Company.find(user.company_id)

# Use in routes
@app.get("/company/stats")
async def company_stats(
    company: Company = Depends(get_current_company)
):
    """Routes can depend on complex logic."""
    return await company.get_statistics()

# Parameterized dependencies
def require_role(role: str):
    """Factory for role-checking dependencies."""
    async def check_role(user=Auth):
        if role not in user.roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check_role

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin = Depends(require_role("admin"))  # Only admins can delete
):
    """Protected endpoint requiring admin role."""
    await User.delete(user_id)
    return {"deleted": user_id}
```

## Event Handlers

Event handlers run code at specific application lifecycle points:

```python
@app.on_event("startup")
async def startup_handler():
    """
    Runs once when application starts.
    Use for:
    - Database connections
    - Cache warming
    - Background task initialization
    """
    app.state.db = await create_database_pool()
    app.state.redis = await aioredis.create_redis_pool()
    print("Application started!")

@app.on_event("shutdown")
async def shutdown_handler():
    """
    Runs once when application shuts down.
    Use for:
    - Closing database connections
    - Flushing caches
    - Cleanup tasks
    """
    await app.state.db.close()
    await app.state.redis.close()
    print("Application stopped!")

# Alternative: Use context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Startup
    db = await setup_database()
    yield
    # Shutdown
    await db.close()

app = Zenith(lifespan=lifespan)
```

## Complete Examples

### Production API with All Features

```python
from zenith import Zenith
from zenith.db import ZenithModel
from zenith.core import Auth, DB, Inject
from sqlmodel import Field
from datetime import datetime

# Create application with chained features
app = (Zenith()
    .add_auth()      # Authentication system
    .add_admin()     # Admin dashboard
    .add_api("Production API", "1.0.0"))  # Adds /docs and /redoc endpoints

# Database model using ZenithModel for enhanced functionality
class Article(ZenithModel, table=True):
    """Article model with automatic CRUD operations."""
    id: int | None = Field(primary_key=True)
    title: str = Field(max_length=200)
    content: str
    author_id: int = Field(foreign_key="user.id")
    published: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Service layer for business logic
class ArticleService(Service):
    """Business logic separated from web layer."""

    async def create_article(self, data: dict, author_id: int) -> Article:
        """Create article with author."""
        return await Article.create(
            **data,
            author_id=author_id
        )

    async def publish_article(self, article_id: int) -> Article:
        """Publish an article."""
        article = await Article.find_or_404(article_id)
        article.published = True
        await article.save()
        return article

# Public endpoints
@app.get("/articles")
async def list_articles(
    published: bool = True,
    limit: int = 20
):
    """List articles - public endpoint."""
    query = Article.where(published=published) if published else Article
    articles = await query.order_by("-created_at").limit(limit).all()
    return {"articles": [a.to_dict() for a in articles]}

# Protected endpoints requiring authentication
@app.post("/articles")
async def create_article(
    data: dict,
    user=Auth,  # Requires authenticated user
    articles: ArticleService = Inject()
):
    """Create article - requires authentication."""
    article = await articles.create_article(data, user.id)
    return {"article": article.to_dict()}

@app.put("/articles/{article_id}/publish")
async def publish_article(
    article_id: int,
    user=Auth,
    articles: ArticleService = Inject()
):
    """Publish article - requires authentication."""
    article = await articles.publish_article(article_id)
    return {"article": article.to_dict()}

# Admin endpoints
@app.delete("/admin/articles/{article_id}")
async def delete_article(
    article_id: int,
    admin = Depends(require_role("admin"))
):
    """Delete article - requires admin role."""
    article = await Article.find_or_404(article_id)
    await article.delete()
    return {"deleted": article_id}

# WebSocket for real-time updates
@app.websocket("/ws/articles")
async def article_updates(websocket: WebSocket):
    """Stream real-time article updates."""
    await websocket.accept()
    # In production, integrate with message queue
    while True:
        # Send updates when articles change
        await websocket.send_json({
            "type": "article_published",
            "id": 123,
            "title": "New Article"
        })
        await asyncio.sleep(10)

if __name__ == "__main__":
    # Development
    app.run(debug=True)

    # Production (use zen serve or uvicorn)
    # uvicorn main:app --workers 4
```

## Testing Your Application

```python
from zenith.testing import TestClient
import pytest

@pytest.fixture
async def client():
    """Test client fixture."""
    async with TestClient(app) as client:
        yield client

async def test_create_article(client):
    """Test article creation."""
    response = await client.post("/articles", json={
        "title": "Test Article",
        "content": "Test content"
    })
    assert response.status_code == 201
    assert response.json()["article"]["title"] == "Test Article"

async def test_protected_endpoint(client):
    """Test authentication requirement."""
    response = await client.get("/profile")
    assert response.status_code == 401  # Unauthorized

    # With authentication
    client.set_auth_token("valid-token")
    response = await client.get("/profile")
    assert response.status_code == 200
```

## Next Steps

- [Routing](../concepts/routing) - Advanced routing patterns
- [Models](../concepts/models) - Database models with ZenithModel
- [Services](../concepts/services) - Organizing business logic
- [Middleware](../concepts/middleware) - Creating custom middleware
- [Testing](./testing) - Testing strategies and patterns

---

*For more examples, see the [complete tutorial](../tutorial/01-getting-started) or explore [example applications](../examples/).*