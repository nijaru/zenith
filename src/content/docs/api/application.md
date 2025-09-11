---
title: Application API
description: Zenith application class reference
---

## Zenith Class

The main application class for creating Zenith applications.

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

Add middleware to the application.

```python
from zenith.middleware import CORSMiddleware

app.add_middleware(CORSMiddleware, {
    "allow_origins": ["*"],
    "allow_methods": ["*"],
    "allow_headers": ["*"],
})
```

#### `spa()`

Serve a single-page application.

```python
app.spa("dist")  # Serve SPA from dist folder
app.spa("build", fallback="index.html")  # Custom fallback
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

### With Database

```python
from zenith import Zenith
from zenith.db import create_engine

app = Zenith()

@app.on_event("startup")
async def startup():
    app.db = create_engine("postgresql://...")
    
@app.on_event("shutdown")
async def shutdown():
    await app.db.dispose()
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