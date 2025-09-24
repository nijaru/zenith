---
title: Hello World Example
description: Your first Zenith application
---


## Minimal Zenith Application

### The Problem (What You'd Write Without Zenith)
```python
# Traditional approach
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Manual response building
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"message": "Hello, World!"})
            self.wfile.write(response.encode())
        else:
            self.send_error(404)

server = HTTPServer(('localhost', 8000), MyHandler)
server.serve_forever()  # No async, no auto-reload, no docs!
```

### The Solution (Zenith Way)
```python
# With Zenith
from zenith import Zenith

# Create the application instance
# WHY: This single line gives you a production-ready app with:
#      - Automatic environment detection (dev/prod)
#      - Security headers (XSS, CSRF protection)
#      - CORS handling
#      - Error formatting
#      - Request logging
#      - JSON serialization
#      - And much more!
app = Zenith()

# Define a route using a decorator
# WHY decorators? They keep your code clean and declarative.
# The decorator tells Zenith: "When someone visits '/', run this function"
@app.get("/")        # This decorator registers the route
async def hello():   # 'async' enables handling thousands of concurrent requests
    """Your business logic - nothing else."""

    # Just return your data as a Python dict
    # Zenith automatically:
    # 1. Converts this dict to JSON
    # 2. Sets Content-Type: application/json header
    # 3. Sets status code to 200 OK
    # 4. Handles any errors gracefully
    return {"message": "Hello, World!"}

    # That's it! No manual JSON encoding, no header setting,
    # no error handling - Zenith does it all!
```

### What's Really Happening Behind the Scenes

When you write that simple code above, here's what Zenith does for you:

1. **Application Creation** (`app = Zenith()`)
   - Detects if you're in development or production
   - Configures appropriate security middleware
   - Sets up request ID tracking for debugging
   - Prepares the routing system
   - Initializes error handlers

2. **Route Registration** (`@app.get("/")`)
   - Adds your function to the routing table
   - Sets up URL pattern matching
   - Prepares request/response conversion
   - Enables automatic API documentation

3. **Request Handling** (when someone visits `/`)
   - Receives the HTTP request
   - Passes through security middleware
   - Matches the URL to your function
   - Executes your `hello()` function
   - Takes your return value
   - Serializes it to JSON
   - Sets appropriate headers
   - Sends the response

4. **Async Magic** (`async def`)
   - Uses Python's asyncio for non-blocking I/O
   - Can handle thousands of concurrent connections
   - Doesn't block on database queries or API calls
   - Scales much better than traditional threading

## Run the Application

```bash
# Save your code as app.py, then:

# Option 1: Using uvicorn directly
uvicorn app:app --reload
#       ^    ^      ^
#       |    |      └── Auto-reload when code changes (development)
#       |    └── The 'app' variable in your file
#       └── Your Python file name (without .py)

# Option 2: Using Zenith's CLI (recommended)
zen dev
# This single command:
# - Finds your app automatically
# - Enables hot reload
# - Shows pretty error pages
# - Optimizes for development

# For production:
zen serve --workers 4
#              ^
#              └── Run 4 worker processes for better performance
```

Visit `http://localhost:8000` and you'll see:
```json
{
  "message": "Hello, World!"
}
```

## Interactive Documentation

### The Problem (Without Auto-Documentation)
```python
# Traditional way - manual documentation
"""
API Documentation:

GET / - Returns hello message
  Response: {"message": "Hello, World!"}

GET /users/{id} - Get user by ID
  Parameters: id (integer) - User ID
  Response: {"id": 1, "name": "Alice"}

... pages and pages of manual docs that get outdated immediately ...
"""
```

### The Solution (Zenith Auto-Docs)
```python
# Zenith way - documentation that never gets outdated
from zenith import Zenith

app = Zenith()

# One line to enable interactive API documentation!
# WHY: Your API documentation should always match your code
app.add_docs()  # This adds /docs and /redoc endpoints

@app.get("/")
async def hello():
    """Say hello to the world."""  # This appears in the docs!
    return {"message": "Hello, World!"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):  # Type hints appear in docs too!
    """Get a user by their ID.

    Args:
        user_id: The unique identifier of the user

    Returns:
        User information including name and email
    """
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }
```

**Now visit:**
- `http://localhost:8000/docs` - **Swagger UI**: Try out endpoints directly!
- `http://localhost:8000/redoc` - **ReDoc**: Beautiful API documentation

**The magic:** Zenith generates docs from your actual code:
- Function signatures → Parameter documentation
- Type hints → Input validation and docs
- Docstrings → Endpoint descriptions
- Return types → Response schemas

## Adding More Routes

### Understanding URL Patterns

```python
from zenith import Zenith
from datetime import datetime

app = Zenith()

# ROUTE TYPE 1: Static Routes
# These have fixed URLs with no variables
@app.get("/")               # Matches: GET http://localhost:8000/
async def hello():
    """API root - usually returns API info or welcome message."""
    return {
        "message": "Welcome to the API",
        "version": "1.0.0",
        "endpoints": ["/users", "/posts", "/health"]
    }

@app.get("/time")           # Matches: GET http://localhost:8000/time
async def current_time():
    """
    Returns current server time.
    Even though the URL is static, the response is dynamic!
    """
    return {
        "time": datetime.utcnow(),      # Called fresh each request
        "timezone": "UTC"
    }

# ROUTE TYPE 2: Path Parameters (variables in the URL)
# Use {variable_name} to capture parts of the URL
@app.get("/greet/{name}")   # The {name} part becomes a variable!
async def greet(
    name: str  # This parameter name MUST match {name} above!
):
    """
    Path parameters extract values from the URL itself.

    URL Examples:
    - /greet/Alice     → name="Alice"
    - /greet/Bob       → name="Bob"
    - /greet/Jane%20Doe → name="Jane Doe" (URL decoding happens automatically)
    """
    return {
        "message": f"Hello, {name}!",
        "name_length": len(name),       # We can use the parameter like any variable
        "name_upper": name.upper()
    }

# ROUTE TYPE 3: Typed Path Parameters
# Type hints provide automatic validation
@app.get("/users/{user_id}")
async def get_user(
    user_id: int  # Type hint means Zenith validates this is an integer!
):
    """
    Type hints = automatic validation.

    Valid URLs:
    - /users/1      → user_id=1
    - /users/42     → user_id=42
    - /users/999    → user_id=999

    Invalid URLs (will return 422 Validation Error):
    - /users/alice  → "alice" is not an integer!
    - /users/3.14   → "3.14" is not an integer!
    - /users/       → Missing parameter!
    """
    # At this point, user_id is GUARANTEED to be an integer
    # No need for try/except or validation - Zenith handled it!
    return {
        "user_id": user_id,
        "user_type": "premium" if user_id < 100 else "regular",
        "profile_url": f"/profiles/{user_id}"
    }

# ROUTE TYPE 4: Multiple Path Parameters
# You can have multiple variables in one URL
@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(
    user_id: int,    # Must be an integer
    post_id: int     # Also must be an integer
):
    """
    Multiple parameters are extracted in order.

    URL Pattern: /users/{user_id}/posts/{post_id}

    Examples:
    - /users/5/posts/10   → user_id=5, post_id=10 (valid)
    - /users/5/posts/abc  → Error: 'abc' not an integer (invalid)
    - /users/x/posts/10   → Error: 'x' not an integer (invalid)
    """
    return {
        "user_id": user_id,
        "post_id": post_id,
        "url": f"/users/{user_id}/posts/{post_id}",
        "edit_url": f"/users/{user_id}/posts/{post_id}/edit"
    }

# ROUTE TYPE 5: Query Parameters (after the ?)
@app.get("/search")  # No path parameters here
async def search(
    q: str,                    # Required query parameter
    limit: int = 10,          # Optional with default value
    offset: int = 0           # Optional with default value
):
    """
    Query parameters come after the ? in URLs.

    URL Examples:
    - /search?q=python           → q="python", limit=10, offset=0
    - /search?q=python&limit=5   → q="python", limit=5, offset=0
    - /search?q=python&limit=5&offset=20 → q="python", limit=5, offset=20

    Missing required parameter:
    - /search                    → Error: 'q' is required!
    - /search?limit=5            → Error: 'q' is required!
    """
    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "results": [f"Result {i} for '{q}'" for i in range(offset, offset + limit)]
    }
```

### Route Patterns Quick Reference

| Pattern | Example URL | What It Does |
|---------|------------|-------------|
| **Static** `/users` | `/users` | Fixed URL, no variables |
| **Path Param** `/users/{id}` | `/users/123` | Extract `id=123` from URL |
| **Multiple** `/users/{uid}/posts/{pid}` | `/users/5/posts/10` | Extract both `uid=5` and `pid=10` |
| **Query** `/search` with `q: str` | `/search?q=python` | Extract `q="python"` from query string |
| **Optional Query** `/search` with `limit: int = 10` | `/search?q=python` | Use default `limit=10` if not provided |

### Common Mistakes and Solutions

```python
# MISTAKE: Parameter name doesn't match
@app.get("/users/{user_id}")
async def get_user(id: int):  # Wrong! Should be 'user_id', not 'id'
    return {"id": id}

# CORRECT: Names must match
@app.get("/users/{user_id}")
async def get_user(user_id: int):  # Matches {user_id} in path
    return {"id": user_id}

# MISTAKE: Wrong type for path parameter
@app.get("/count/{number}")
async def count(number: str):  # Should be int if you want numeric validation
    return {"double": number * 2}  # This would fail with string!

# CORRECT: Use proper type
@app.get("/count/{number}")
async def count(number: int):  # Now Zenith validates it's a number
    return {"double": number * 2}  # Works correctly

# MISTAKE: Optional path parameters aren't allowed
@app.get("/users/{user_id}")
async def get_user(user_id: int | None = None):  # Path params can't be optional!
    return {"id": user_id}

# CORRECT: Use query parameters for optional values
@app.get("/users")
async def get_users(user_id: int | None = None):  # Query param CAN be optional
    if user_id:
        return {"user": user_id}
    return {"users": "all"}
```

## With Configuration

```python
from zenith import Zenith

# You can customize your app with configuration
app = Zenith(
    # These appear in your auto-generated documentation
    title="My First API",           # API name in docs
    version="1.0.0",                # Version tracking
    description="Learning Zenith Framework",  # What your API does

    # Optional: Control behavior
    debug=True,                     # Better error messages in development
    docs_url="/api-docs",          # Custom docs URL (default: /docs)
    redoc_url="/api-redoc",        # Custom ReDoc URL (default: /redoc)
)

# Tags help organize your endpoints in documentation
@app.get("/", tags=["General"])     # This endpoint appears under 'General' in docs
async def hello():
    """
    Say hello to the world.

    This docstring becomes the endpoint description in your API docs.
    The more detail you add here, the better your auto-generated
    documentation becomes!
    """
    return {"message": "Hello, World!"}

@app.get("/health", tags=["Monitoring"])  # Different tag = different section
async def health_check():
    """
    Check if the service is healthy.

    Returns:
        dict: Status information
            - status: "healthy" or "unhealthy"
            - timestamp: Current server time
            - uptime: Seconds since startup
    """
    import time
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "uptime": time.time() - app.startup_time  # Zenith tracks this!
    }

# Pro tip: Use tags to group related endpoints
@app.post("/users", tags=["Users"])
async def create_user(name: str, email: str):
    """Create a new user."""
    return {"id": 1, "name": name, "email": email}

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: int):
    """Get user by ID."""
    return {"id": user_id, "name": f"User {user_id}"}

# Now /docs shows your endpoints organized by tags!
```

## Complete Example

Find the complete example at:
[github.com/nijaru/zenith/examples/00-hello-world.py](https://github.com/nijaru/zenith/tree/main/examples/00-hello-world.py)