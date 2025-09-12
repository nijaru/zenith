---
title: Hello World Example
description: Your first Zenith application
---


## Minimal Zenith Application

The simplest possible Zenith application demonstrates the core concepts:

```python
from zenith import Zenith

# Create the main application instance
app = Zenith()

# Define a route handler using the @app.get() decorator
@app.get("/")
async def hello():
    """
    Route handler function - automatically converted to JSON response.
    The return value is serialized and sent with proper HTTP headers.
    """
    return {"message": "Hello, World!"}
```

**What's happening here:**
- `Zenith()` creates your application instance with sensible defaults
- `@app.get("/")` decorates the function to handle GET requests to the root path
- Return values are automatically serialized to JSON with proper content-type headers
- All route handlers are `async` functions for better performance

## Run the Application

```bash
# Save as app.py
# Run with:
uvicorn app:app --reload

# Or use the Zenith CLI:
zen server --reload
```

Visit `http://localhost:8000` to see your API in action!

## Interactive Documentation

Zenith can generate interactive API documentation. Add `app.add_docs()` to enable:

```python
from zenith import Zenith

app = Zenith()
app.add_docs()  # Enable documentation endpoints

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}
```

Then visit:
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/redoc` - ReDoc

## Adding More Routes

Zenith makes it easy to add multiple endpoints with different patterns:

```python
from zenith import Zenith
from datetime import datetime

app = Zenith()

@app.get("/")
async def hello():
    """Static endpoint - always returns the same response."""
    return {"message": "Hello, World!"}

@app.get("/time")
async def current_time():
    """Dynamic endpoint - returns server's current time."""
    return {"time": datetime.utcnow()}

@app.get("/greet/{name}")
async def greet(name: str):
    """
    Path parameter endpoint - {name} is extracted from URL.
    Zenith automatically validates and converts the parameter.
    """
    return {"message": f"Hello, {name}!"}
```

**Route patterns explained:**
- `/` - Static route, no parameters
- `/time` - Static route that returns dynamic data
- `/greet/{name}` - Path parameter route where `{name}` becomes a function argument
- Parameters are automatically type-validated based on function signatures

## With Configuration

```python
from zenith import Zenith

app = Zenith(
    title="My First API",
    version="1.0.0",
    description="Learning Zenith Framework"
)

@app.get("/", tags=["General"])
async def hello():
    """
    Say hello to the world.
    
    This endpoint returns a simple greeting message.
    """
    return {"message": "Hello, World!"}

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Check if the service is healthy."""
    return {"status": "healthy"}
```

## Complete Example

Find the complete example at:
[github.com/nijaru/zenith/examples/00-hello-world.py](https://github.com/nijaru/zenith/tree/main/examples/00-hello-world.py)