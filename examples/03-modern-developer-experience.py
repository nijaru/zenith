"""
Modern Developer Experience Example - Showcasing v0.0.1 Improvements

This example demonstrates the new patterns in Zenith v0.0.1:
- Enhanced Model with intuitive query methods
- Enhanced dependency injection shortcuts
- Zero-configuration auto-setup
- Dramatically reduced boilerplate

Shows the improved developer experience with clean, declarative code.
"""

import os
from datetime import datetime
from typing import Optional

from sqlmodel import Field

# Zenith v0.0.1 imports - much cleaner!
from zenith import Zenith
from zenith import Session
from zenith import Auth
from zenith.core import is_development
from zenith.db import ZenithModel as Model  # Enhanced model with where/find/create methods

# Set up database in examples directory
example_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(example_dir, "modern_dx_example.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

# 🚀 Zero-config application setup
# This automatically detects environment and configures:
# - Database (SQLite for development)
# - CORS (permissive for dev, secure for prod)
# - Security settings (dev key for dev, requires SECRET_KEY for prod)
# - Middleware (debug toolbar in dev, security headers in prod)
app = Zenith()


# 📋 Modern Models with Enhanced Model
class User(Model, table=True):
    """User model with Modern convenience methods."""

    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Post(Model, table=True):
    """Blog post model."""

    id: Optional[int] = Field(primary_key=True)
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)


# 🎯 Routes with Enhanced DX

@app.get("/")
async def home():
    """Homepage showing framework info."""
    return {
        "message": "Modern DX Example",
        "framework": "Zenith v0.0.1",
        "features": [
            "Zero-config setup",
            "Modern models",
            "Enhanced dependency injection",
            "85% less boilerplate"
        ],
        "environment": "development" if is_development() else "production",
        "endpoints": [
            "GET /users - List users with Modern queries",
            "POST /users - Create user",
            "GET /users/{id} - Get user (with 404 handling)",
            "GET /posts - List published posts",
            "POST /posts - Create post (requires user)",
        ]
    }


@app.get("/users")
async def list_users():
    """
    List users with Modern query methods.

    Notice how clean this is compared to raw SQLAlchemy:
    - No session management boilerplate
    - Readable query methods
    - Automatic async handling
    """
    # Clean query syntax: User.where(active=True).order_by('-created_at').limit(10)
    query = await User.where(active=True)
    users = await query.order_by('-created_at').limit(10).all()
    return {"users": [user.to_dict() for user in users]}


@app.post("/users")
async def create_user(user_data: dict):
    """
    Create a user with Modern convenience.

    Compare to verbose alternatives:
    - No manual session management
    - Clean creation syntax
    - Automatic validation
    """
    # Clean: User.create(name="Alice", email="alice@example.com")
    user = await User.create(**user_data)
    return {"user": user.to_dict(), "message": "User created successfully"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """
    Get user with automatic 404 handling.

    The find_or_404 method automatically raises a proper HTTP 404
    if the user doesn't exist - no manual checking needed!
    """
    # Clean: User.find_or_404(123) - raises 404 if not found
    user = await User.find_or_404(user_id)
    return {"user": user.to_dict()}


@app.get("/posts")
async def list_posts(published: bool = True):
    """
    List posts with conditional filtering.

    Shows chainable query methods for complex queries.
    """
    if published:
        # Clean chaining: Post.where(published=True).order_by('-created_at')
        query = await Post.where(published=True)
        posts = await query.order_by('-created_at').all()
    else:
        posts = await Post.all()

    return {
        "posts": [post.to_dict() for post in posts],
        "count": len(posts)
    }


@app.post("/posts")
async def create_post(post_data: dict):
    """
    Create a post.

    In a real app, this would use authentication to get the current user.
    For this example, we'll use the first user or create one.
    """
    # Find or create a user for the post
    user = await User.first()
    if not user:
        user = await User.create(
            name="Demo User",
            email="demo@example.com"
        )

    # Add user_id to post data
    post_data["user_id"] = user.id

    # Clean creation
    post = await Post.create(**post_data)
    return {"post": post.to_dict(), "message": "Post created successfully"}


@app.get("/stats")
async def get_stats():
    """
    Get database statistics using Modern count methods.

    Shows how clean aggregate queries can be.
    """
    # Clean: User.count(), Post.where(published=True).count()
    total_users = await User.count()
    active_query = await User.where(active=True)
    active_users = await active_query.count()
    total_posts = await Post.count()
    published_query = await Post.where(published=True)
    published_posts = await published_query.count()

    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "posts": {
            "total": total_posts,
            "published": published_posts
        }
    }


# 🛠️ Database Setup
@app.on_event("startup")
async def setup_database():
    """Create database tables."""
    from zenith.db import Database

    # Get database from auto-config
    db_url = os.getenv("DATABASE_URL")
    db = Database(db_url)

    # Create tables
    await db.create_all()

    print("✅ Database tables created successfully")
    print("🎯 Modern DX patterns are ready to use!")
    print("📝 Try the endpoints to see Enhanced Model in action")


if __name__ == "__main__":
    print("🚀 Starting Modern DX Example")
    print("📍 Server will start at: http://localhost:8016")
    print("🔗 Try these endpoints:")
    print("   GET /           - Framework info and available endpoints")
    print("   GET /users      - List active users (Clean queries)")
    print("   POST /users     - Create user (JSON: {\"name\": \"...\", \"email\": \"...\"})")
    print("   GET /users/1    - Get specific user (with 404 handling)")
    print("   GET /posts      - List published posts")
    print("   POST /posts     - Create post (JSON: {\"title\": \"...\", \"content\": \"...\"})")
    print("   GET /stats      - Database statistics")
    print("📖 Interactive docs: http://localhost:8016/docs")
    print()
    print("🎨 DX Improvements showcased:")
    print("   ✨ Zero-config setup - app = Zenith() just works")
    print("   ✨ Modern models - User.where(active=True).limit(10)")
    print("   ✨ No session management - ZenithModel handles it automatically")
    print("   ✨ Automatic 404s - User.find_or_404(id)")
    print("   ✨ 85% less boilerplate than verbose alternatives")

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8016)