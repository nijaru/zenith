---
title: Hello World
description: Your first Zenith application
---

## Minimal Application

Create a simple API with Zenith:

```python
from zenith import Zenith

# Create application
app = Zenith()

@app.get("/")
async def hello():
    """Root endpoint."""
    return {"message": "Hello, World!"}
```

## Running the Application

Save as `app.py` and run:

```bash
# Using uvicorn
uvicorn app:app --reload

# Using Zenith CLI
zen dev

# For production
zen serve --workers 4
```

Visit `http://localhost:8000`:

```json
{
  "message": "Hello, World!"
}
```

## Adding Documentation

Enable interactive API documentation:

```python
from zenith import Zenith

app = Zenith()

# Add documentation endpoints
app.add_api("Hello API", "1.0.0")  # Adds /docs and /redoc endpoints

@app.get("/")
async def hello():
    """Say hello to the world."""
    return {"message": "Hello, World!"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
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

**Documentation endpoints:**
- `http://localhost:8000/docs` - Swagger UI (interactive testing)
- `http://localhost:8000/redoc` - ReDoc (clean documentation)

## Path Parameters

Extract values from the URL path:

```python
@app.get("/greet/{name}")
async def greet(name: str):
    """Greet someone by name.

    The name is extracted from the URL path.
    Examples:
    - /greet/Alice  → name="Alice"
    - /greet/Bob    → name="Bob"
    """
    return {"greeting": f"Hello, {name}!"}
```

## Type Validation

Type hints provide automatic validation:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID.

    Valid: /users/123
    Invalid: /users/abc (returns 422 error)
    """
    return {"user_id": user_id}

@app.get("/users/{user_id}/posts/{post_id}")
async def get_post(user_id: int, post_id: int):
    """Get specific post from specific user."""
    return {
        "user_id": user_id,
        "post_id": post_id,
        "url": f"/users/{user_id}/posts/{post_id}"
    }
```

## Query Parameters

Handle URL query parameters:

```python
@app.get("/search")
async def search(
    q: str,              # Required
    limit: int = 10,     # Optional with default
    offset: int = 0      # Optional with default
):
    """Search with query parameters.

    Examples:
    - /search?q=python
    - /search?q=python&limit=5
    - /search?q=python&limit=5&offset=10
    """
    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "results": [f"Result {i}" for i in range(offset, offset + limit)]
    }
```

## Complete Example

```python
# examples/00-hello-world.py
from zenith import Zenith

# Create application
app = Zenith()

# Enable documentation
app.add_api("Hello API", "1.0.0")  # Interactive docs at /docs

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Hello API",
        "version": "1.0.0",
        "endpoints": [
            "/",
            "/hello/{name}",
            "/users/{user_id}"
        ]
    }

@app.get("/hello/{name}")
async def hello(name: str):
    """Personalized greeting."""
    return {"message": f"Hello, {name}!"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID."""
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "active": True
    }

@app.post("/users")
async def create_user(data: dict):
    """Create a new user."""
    return {
        "message": "User created",
        "data": data,
        "id": 123
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Hello API")
    print("📚 Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run and test:

```bash
# Run the application
python examples/00-hello-world.py

# Test endpoints
curl http://localhost:8000/
curl http://localhost:8000/hello/Alice
curl http://localhost:8000/users/42

# Create a user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

## Next Steps

- Learn about [Routing](/examples/basic-routing) for more complex patterns
- Explore [Database Models](/concepts/models) for data persistence
- Add [Authentication](/concepts/authentication) to protect endpoints