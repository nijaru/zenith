---
title: Application API
description: Zenith application class reference and dependency injection
---

## Zenith Class

The main application class for creating Zenith applications with production-ready defaults and Service-based architecture.

### Constructor

```python
from zenith import Zenith

app = Zenith(
    title: str = "Zenith API",
    version: str = "1.0.0",
    description: str = None,
    debug: bool = False,
    middleware: List[Middleware] = None,
    exception_handlers: Dict[Type[Exception], Callable] = None,
    on_startup: List[Callable] = None,
    on_shutdown: List[Callable] = None,
)
```

#### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `title` | `str` | API title shown in docs | `"Zenith API"` |
| `version` | `str` | API version | `"1.0.0"` |
| `description` | `str` | API description | `None` |
| `debug` | `bool` | Enable debug mode | `False` |
| `middleware` | `List` | List of middleware | `None` |
| `exception_handlers` | `Dict` | Custom exception handlers | `None` |
| `on_startup` | `List` | Startup event handlers | `None` |
| `on_shutdown` | `List` | Shutdown event handlers | `None` |

### Route Decorators

#### `@app.get()`

```python
@app.get(
    path: str,
    response_model: Type = None,
    status_code: int = 200,
    tags: List[str] = None,
    summary: str = None,
    description: str = None,
    response_description: str = "Successful Response",
    responses: Dict = None,
    deprecated: bool = False,
    operation_id: str = None,
    include_in_schema: bool = True,
)
```

#### `@app.post()`

```python
@app.post(
    path: str,
    response_model: Type = None,
    status_code: int = 201,
    # ... same parameters as get()
)
```

#### `@app.put()`, `@app.patch()`, `@app.delete()`

Same parameters as `@app.get()` with appropriate default status codes.

### Methods

#### `include_router()`

Include a router with routes.

```python
from zenith import Router

router = Router(prefix="/api/v1")
app.include_router(router)
```

#### `add_middleware()`

Add middleware to the application with intelligent duplicate handling.

```python
from zenith.middleware import CORSMiddleware, RateLimitMiddleware

# Basic usage (replaces existing by default)
app.add_middleware(CORSMiddleware, {
    "allow_origins": ["*"],
    "allow_methods": ["*"],
    "allow_headers": ["*"],
})

# Advanced control
app.add_middleware(RateLimitMiddleware,
    requests=100,
    replace=False,          # Error if already exists
    allow_duplicates=True   # Allow multiple instances
)

# Middleware executes in LIFO order (last added runs first)
app.add_middleware(LoggingMiddleware)    # Runs second
app.add_middleware(SecurityMiddleware)   # Runs first
```

#### `spa()`

Serve a single-page application with enhanced configuration.

```python
# Basic usage
app.spa("dist")  # Serve from dist folder with defaults

# Enhanced configuration
app.spa(
    "dist",
    index="app.html",               # Custom index file
    exclude=["/api/*", "/admin/*"]  # Don't fallback for API routes
)

# Multiple SPA configuration
app.spa("admin-dist", path="/admin", index="admin.html")
app.spa("public-dist", path="/", exclude=["/admin/*", "/api/*"])
```

#### `static()`

Serve static files.

```python
app.static("/static", directory="static")
app.static("/media", directory="uploads", max_age=86400)
```

### Event Handlers

#### `@app.on_event()`

Register event handlers.

```python
@app.on_event("startup")
async def startup():
    print("Starting up...")

@app.on_event("shutdown")
async def shutdown():
    print("Shutting down...")
```

### WebSocket Support

#### `@app.websocket()`

Create WebSocket endpoints.

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

## Examples

### Basic Application

```python
from zenith import Zenith

app = Zenith(title="My API", version="2.0.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### With Middleware

```python
from zenith import Zenith
from zenith.middleware import (
    CORSMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)

app = Zenith(
    title="Production API",
    middleware=[
        CORSMiddleware({"allow_origins": ["https://example.com"]}),
        RateLimitMiddleware({"requests_per_minute": 60}),
        SecurityHeadersMiddleware()
    ]
)
```

### With Request-Scoped Database (Recommended)

```python
from zenith import Zenith, DatabaseSession, Service, Inject
from zenith.db import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Request-scoped database session (prevents "Future attached to loop" errors)
async def get_db():
    engine = create_async_engine("postgresql://...")
    SessionLocal = sessionmaker(engine, class_=AsyncSession)
    async with SessionLocal() as session:
        yield session

class UserService(Service):
    async def get_users(self, db: AsyncSession):
        # Business logic here
        pass

app = Zenith()

# Enhanced DI pattern with services
@app.get("/users")
async def get_users(
    users: UserService = Inject()                 # Service injection
):
    return await users.get_users()

# Traditional dependency injection also supported
@app.get("/users-alt")
async def get_users_alt(
    db: AsyncSession = Depends(get_db)            # Traditional style
):
    # Direct database access
    pass
```

## Dependency Injection API

### Service Classes

Business logic should be organized in Service classes for clean architecture:

```python
from zenith import Service, Inject

class UserService(Service):
    """Business logic for user operations."""

    async def create_user(self, user_data: dict) -> dict:
        # Auto-injected services are available
        return {"id": 1, **user_data}

    async def get_user(self, user_id: int) -> dict | None:
        # Business logic separate from web concerns
        return {"id": user_id, "name": "John"}

# Usage in routes (automatic dependency injection)
@app.post("/users")
async def create_user(
    user_data: dict,
    users: UserService = Inject()  # Auto-injected
) -> dict:
    return await users.create_user(user_data)
```

### Request-Scoped Dependencies

For async resources like database connections:

```python
from zenith import RequestScoped, DatabaseSession, Depends

# Factory function for request-scoped resources
async def get_db():
    # Fresh connection per request
    async with database.session() as session:
        yield session

# Both syntaxes work
@app.get("/data1")
async def handler1(db = RequestScoped(get_db)):  # Zenith explicit
    pass

@app.get("/data2")
async def handler2(db = DatabaseSession(get_db)):  # Database-specific
    pass

@app.get("/data3")
async def handler3(db = Depends(get_db)):  # Traditional dependency injection
    pass
```

### File Upload Enhancement

Enhanced file upload with improved UX:

```python
from zenith import File
from zenith.web.files import UploadedFile

@app.post("/upload")
async def upload_file(file: UploadedFile = File(
    max_size=5 * 1024 * 1024,  # 5MB
    allowed_types=["image/jpeg", "image/png", "application/pdf"]
)) -> dict:
    # Enhanced API with convenience methods
    if file.is_image():
        print("It's an image!")

    extension = file.get_extension()  # ".jpg"

    # Easy file operations
    final_path = await file.move_to(f"/uploads/{uuid.uuid4()}{extension}")

    # Starlette-compatible read
    content = await file.read()

    return {
        "filename": file.filename,
        "original": file.original_filename,
        "size": file.size_bytes,
        "type": file.content_type,
        "saved_to": str(final_path)
    }
```

## Type Hints

All methods and decorators are fully type-hinted for IDE support:

```python
from typing import List, Optional
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

@app.post("/items", response_model=Item)
async def create_item(item: Item) -> Item:
    return item

@app.get("/items", response_model=List[Item])
async def list_items(skip: int = 0, limit: int = 100) -> List[Item]:
    return []
```