"""
One-liner Features Example - Showcasing v0.0.3 Convenience Methods

This example demonstrates the new one-liner convenience methods:
- app.add_auth() - JWT authentication in one line
- app.add_admin() - Admin interface in one line
- app.add_api() - API documentation in one line

Compare this to traditional setup - these methods save 20-50 lines each!
"""

import os

from zenith import Zenith

# Set up environment for the example
example_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(example_dir, "oneliner_example.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-demo-only-32-chars-long")

# 🚀 Create app and add features in just 4 lines!
app = Zenith()
app.add_auth()  # Adds JWT auth + /auth/login endpoint
app.add_admin()  # Adds admin dashboard at /admin
app.add_api("Demo API", "1.0.0", "Showcase of one-liner features")


# Your regular API endpoints
@app.get("/")
async def home():
    """Homepage showing all available features."""
    return {
        "message": "One-liner Features Demo",
        "features_added": [
            "🔐 Authentication - POST /auth/login",
            "⚡ Admin Dashboard - GET /admin",
            "📚 API Documentation - GET /docs",
        ],
        "try_these": [
            "POST /auth/login - Login with any username/password",
            "GET /admin - Admin dashboard",
            "GET /admin/health - System health check",
            "GET /admin/stats - App statistics",
            "GET /api/info - API information",
            "GET /docs - Interactive API docs",
            "GET /redoc - Alternative API docs",
        ],
    }


@app.get("/protected")
async def protected_route():
    """Example protected route - requires authentication."""
    # In a real app, you'd add authentication middleware/dependencies
    return {"message": "This is a protected route"}


if __name__ == "__main__":
    print("🚀 Starting One-liner Features Demo")
    print("📍 Server will start at: http://localhost:8017")
    print()
    print("✨ Features added in just 3 lines of code:")
    print("   app.add_auth()   - JWT authentication")
    print("   app.add_admin()  - Admin dashboard")
    print("   app.add_api()    - API documentation")
    print()
    print("🔗 Try these endpoints:")
    print("   GET /            - Homepage with feature overview")
    print("   POST /auth/login - Login (any username/password works)")
    print("   GET /admin       - Admin dashboard")
    print("   GET /admin/health - System health check")
    print("   GET /docs        - Interactive API documentation")
    print("   GET /redoc       - Alternative API documentation")

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8017)
