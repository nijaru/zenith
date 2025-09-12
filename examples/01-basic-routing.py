"""
🛤️  Basic Routing - Path Parameters and Query Strings

This example demonstrates:
- Path parameters with type hints
- Query parameters and optional values
- Multiple HTTP methods
- Basic response types

Run with: python examples/01-basic-routing.py
Then visit: http://localhost:8001
"""

from zenith import Zenith

app = Zenith(debug=True)


@app.get("/")
async def root():
    """Welcome endpoint with available routes."""
    return {
        "message": "Basic Routing Example",
        "routes": [
            "GET /users/{user_id}",
            "GET /search?q=query&limit=10",
            "POST /users/{user_id}/posts",
            "GET /hello/{name}?greeting=custom",
        ],
    }


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID with path parameter."""
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
    }


@app.get("/search")
async def search(q: str, limit: int = 10, offset: int = 0):
    """Search with query parameters."""
    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "results": [f"Result {i} for '{q}'" for i in range(1, min(limit + 1, 6))],
    }


@app.post("/users/{user_id}/posts")
async def create_post(user_id: int, title: str, content: str):
    """Create post for user (form data or JSON)."""
    return {
        "post_id": 42,
        "user_id": user_id,
        "title": title,
        "content": content,
        "created": "2025-09-03T10:00:00Z",
    }


@app.get("/hello/{name}")
async def hello_custom(name: str, greeting: str | None = None):
    """Personalized greeting with optional query parameter."""
    if greeting:
        message = f"{greeting}, {name}!"
    else:
        message = f"Hello, {name}!"

    return {"message": message, "name": name, "greeting": greeting}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "example": "01-basic-routing"}


if __name__ == "__main__":
    print("🛤️  Starting Basic Routing Example")
    print("📍 Server will start at: http://localhost:8001")
    print("🔗 Try these endpoints:")
    print("   GET /users/123")
    print("   GET /search?q=python&limit=5")
    print("   POST /users/1/posts (with title & content)")
    print("   GET /hello/world?greeting=Hi")
    print()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
