#!/usr/bin/env python
"""
Example showcasing Zenith's improved developer experience features.

Demonstrates the new high-level decorators and utilities that reduce
boilerplate and improve code clarity.
"""

from zenith import (
    Zenith,
    CurrentUser,
    DB,
    Paginate,
    PaginatedResponse,
    cache,
    rate_limit,
    returns,
    auth_required,
    paginate as paginate_decorator,
)
from zenith.db import ZenithModel
from sqlmodel import Field
from datetime import datetime


# Define models with Rails-like functionality
class User(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    name: str
    email: str
    role: str = Field(default="user")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Post(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    title: str
    content: str
    author_id: int = Field(foreign_key="user.id")
    published: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Create application with zero configuration
app = Zenith()


@app.get("/")
async def home():
    """Home endpoint showing available features."""
    return {
        "message": "Zenith Improved DX Demo",
        "features": [
            "CurrentUser dependency for cleaner auth",
            "Pagination with Paginate dependency",
            "@cache decorator for response caching",
            "@rate_limit decorator for rate limiting",
            "@returns decorator for auto-404s",
            "@auth_required decorator for protected routes",
        ],
        "endpoints": {
            "GET /users": "Paginated user list",
            "GET /users/{id}": "Get user (auto-404)",
            "GET /posts": "Cached post list",
            "POST /admin/clear-cache": "Admin-only endpoint",
            "GET /stats": "Rate-limited statistics",
        },
    }


# Clean pagination with Paginate dependency
@app.get("/users")
async def list_users(page: Paginate = Paginate(), db=DB):
    """List users with automatic pagination."""
    # Get paginated results
    query = User.select().offset(page.offset).limit(page.limit)
    users = await db.execute(query)
    users_list = users.scalars().all()

    # Get total count
    count_query = User.count()
    total = await db.scalar(count_query)

    return PaginatedResponse.create(
        items=[u.to_dict() for u in users_list],
        page=page.page,
        limit=page.limit,
        total=total
    )


# Auto-404 with @returns decorator
@app.get("/users/{user_id}")
@returns(User)
async def get_user(user_id: int):
    """Get user by ID with automatic 404 if not found."""
    return await User.find(user_id)


# Response caching with @cache decorator
@app.get("/posts")
@cache(ttl=60)  # Cache for 60 seconds
async def list_posts():
    """List published posts with caching."""
    posts = await Post.where(published=True).order_by("-created_at").limit(10)
    return {"posts": [p.to_dict() for p in posts]}


# Rate limiting with @rate_limit decorator
@app.get("/stats")
@rate_limit("10/minute")  # 10 requests per minute
@cache(ttl=30)  # Also cache for 30 seconds
async def get_statistics():
    """Get system statistics with rate limiting and caching."""
    user_count = await User.count()
    post_count = await Post.count()

    return {
        "users": user_count,
        "posts": post_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Clean auth with CurrentUser dependency
@app.get("/me")
async def get_current_user(user: User = CurrentUser):
    """Get current authenticated user profile."""
    if not user:
        return {"message": "Not authenticated"}
    return {"user": user.to_dict()}


# Role-based access with @auth_required decorator
@app.post("/admin/clear-cache")
@auth_required(role="admin")
async def clear_cache(user=CurrentUser):
    """Admin-only endpoint to clear cache."""
    # In production, would clear actual cache
    return {
        "message": "Cache cleared",
        "admin": user.name if hasattr(user, 'name') else "Admin",
    }


# Paginated decorator for simpler pagination
@app.get("/products")
@paginate_decorator(default_limit=10)
async def list_products(page: int = 1, limit: int = 10, **kwargs):
    """List products with decorator-based pagination."""
    # kwargs contains _page, _limit, _offset injected by decorator
    return [
        {"id": i, "name": f"Product {i}"}
        for i in range(kwargs["_offset"], kwargs["_offset"] + kwargs["_limit"])
    ]


# Startup event to create tables
@app.on_startup
async def setup_database():
    """Create database tables on startup."""
    # In production, use proper migrations
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    engine = create_engine("sqlite:///example.db")
    SQLModel.metadata.create_all(engine)

    print("✅ Database tables created")
    print("🚀 Improved DX features are ready!")


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Zenith Improved DX Example")
    print("📍 Server will start at: http://localhost:8019")
    print("🔗 Try these endpoints:")
    print("   GET /           - Feature overview")
    print("   GET /users      - Paginated users (?page=1&limit=5)")
    print("   GET /users/1    - Get specific user (auto-404)")
    print("   GET /posts      - Cached post list")
    print("   GET /stats      - Rate-limited statistics")
    print("   GET /me         - Current user profile")
    print("   GET /products   - Decorator-based pagination")
    print("📖 Interactive docs: http://localhost:8019/docs")
    print()
    print("✨ New DX improvements:")
    print("   • CurrentUser - Cleaner auth dependency")
    print("   • Paginate - Built-in pagination support")
    print("   • @cache - Response caching decorator")
    print("   • @rate_limit - Per-endpoint rate limiting")
    print("   • @returns - Auto-404 for None results")
    print("   • @auth_required - Role-based access control")

    uvicorn.run(app, host="0.0.0.0", port=8019, reload=True)