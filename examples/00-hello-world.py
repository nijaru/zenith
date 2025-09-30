"""
🚀 Zenith Hello World - The Simplest Possible Example

This is your first Zenith application. It demonstrates:
- Creating a Zenith app
- Defining routes
- Running the server

Run with: python examples/00-hello-world.py
Then visit: http://localhost:8000
"""

from zenith import Zenith

app = Zenith()


# Define a simple route
@app.get("/")
async def hello_world():
    """Simple hello world endpoint."""
    return {
        "message": "Hello, World! 🚀",
        "framework": "Zenith",
        "version": "0.0.2",
        "docs": "/docs",
    }


@app.get("/hello/{name}")
async def hello_name(name: str):
    """Personalized greeting with path parameter."""
    return {
        "message": f"Hello, {name}! 👋",
        "framework": "Zenith",
        "timestamp": "2025-09-09T00:00:00Z",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Zenith is running perfectly! ✅",
        "framework": "Zenith",
        "example": "00-hello-world",
    }


if __name__ == "__main__":
    print("🚀 Starting Zenith Hello World Example")
    print("📍 Server will start at: http://localhost:8001")
    print("🔗 Try these endpoints:")
    print("   GET /           - Hello World with framework info")
    print("   GET /hello/you  - Personalized greeting with path param")
    print("   GET /health     - Health check endpoint")
    print("📖 Interactive docs: http://localhost:8001/docs")
    print()
    print("🎨 This example demonstrates:")
    print("   • Basic Zenith application setup")
    print("   • Route definition with decorators")
    print("   • Path parameters and type hints")
    print("   • JSON response handling")
    print("   • Automatic API documentation")
    print()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
