---
title: Hello World Example
description: Your first Zenith application
---


## Minimal Zenith Application

The simplest possible Zenith application demonstrates the core concepts. Unlike traditional frameworks that require extensive boilerplate, Zenith provides intelligent defaults so you can start building immediately:

```python
from zenith import Zenith

# Create the application instance - automatically configures:
# - Development/production settings based on environment
# - Security middleware (CORS, headers, etc.)
# - Error handling and logging
app = Zenith()

# Route decorator: Maps HTTP GET requests to this function
# The "/" path responds to: http://localhost:8000/
@app.get("/")
async def hello():
    """
    Route handler function - Zenith handles the complexity for you:
    - Accepts the HTTP request
    - Calls your function
    - Converts the return value to JSON
    - Sets proper Content-Type headers
    - Sends the HTTP response
    """
    return {"message": "Hello, World!"}
    # Behind the scenes: This dict becomes JSON with status 200
```

**What's happening here:**
- `Zenith()` creates your application with production-ready defaults (security, logging, error handling)
- `@app.get("/")` registers this function to handle GET requests to the root URL
- Return any Python dict/list - Zenith automatically converts to JSON and sets headers
- `async def` enables high-performance async I/O (handles thousands of concurrent requests)

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

Zenith makes it easy to add multiple endpoints with different URL patterns. Each pattern serves a different purpose in your API:

```python
from zenith import Zenith
from datetime import datetime

app = Zenith()

@app.get("/")
async def hello():
    """Root endpoint - typically used for API information."""
    return {"message": "Hello, World!"}

@app.get("/time")
async def current_time():
    """
    Dynamic data endpoint - returns different data each call.
    No parameters needed, but the response changes.
    """
    # datetime.utcnow() is called fresh each request
    return {"time": datetime.utcnow()}

@app.get("/greet/{name}")
async def greet(name: str):  # 'name' matches {name} in the path
    """
    Path parameter endpoint - extracts data from the URL itself.

    Examples of URLs that match:
    - /greet/Alice -> name="Alice"
    - /greet/Bob   -> name="Bob"
    - /greet/123   -> name="123" (converted to string)
    """
    # The 'name' parameter is automatically extracted and type-validated
    return {"message": f"Hello, {name}!"}

@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: int, post_id: int):
    """
    Multiple path parameters - Zenith extracts both values.
    Type hints ensure user_id and post_id are valid integers.

    /users/abc/posts/123 -> 422 Error (abc is not an integer)
    /users/5/posts/10    -> user_id=5, post_id=10
    """
    return {
        "user_id": user_id,  # Guaranteed to be an int
        "post_id": post_id   # Also guaranteed to be an int
    }
```

**Route patterns explained:**
- **Static routes** (`/`, `/time`) - Fixed paths, may return dynamic data
- **Path parameters** (`{name}`) - Extract values from the URL path itself
- **Type validation** - Function type hints (`str`, `int`) automatically validate inputs
- **Multiple parameters** - Combine multiple path segments for complex URLs

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