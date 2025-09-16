"""
Seamless Integration Example - ZenithModel + Zenith App Integration

This example demonstrates that ZenithModel works seamlessly within Zenith app
web requests without any manual session management required.

Key features:
- ZenithModel automatically uses request-scoped database sessions
- No manual set_current_db_session() calls needed in route handlers
- Seamless Rails-like experience with zero boilerplate
"""

import os
from datetime import datetime
from typing import Optional

from sqlmodel import Field

from zenith import Zenith
from zenith import Session
from zenith.db import ZenithModel

# Set up environment
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///seamless_integration.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-demo-only")

# 🚀 Zero-config app setup
app = Zenith()

# 📋 Define models - they'll automatically work with app's database sessions
class User(ZenithModel, table=True):
    """User model with seamless database integration."""

    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Post(ZenithModel, table=True):
    """Post model with seamless database integration."""

    id: Optional[int] = Field(primary_key=True)
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)


# 🎯 Routes that demonstrate seamless ZenithModel integration
# Notice: NO manual session management needed!

@app.get("/")
async def home():
    """Homepage showing seamless integration capabilities."""
    return {
        "message": "Seamless ZenithModel Integration Demo",
        "features": [
            "ZenithModel automatically uses app's request-scoped sessions",
            "No manual session management in route handlers",
            "Rails-like convenience with zero boilerplate"
        ],
        "try_these": [
            "GET /users - List all users (seamless database access)",
            "POST /users - Create user (seamless saving)",
            "GET /users/{id} - Get user (seamless querying)",
            "DELETE /users/{id} - Delete user (seamless deletion)",
            "GET /stats - Database statistics (seamless counting)"
        ]
    }


@app.get("/users")
async def list_users():
    """
    List users - ZenithModel seamlessly uses app's database session.
    No manual session management required!
    """
    # This just works! ZenithModel automatically uses the request-scoped session
    users = await User.where(active=True).order_by('-created_at').all()
    return {"users": [user.to_dict() for user in users]}


@app.post("/users")
async def create_user(user_data: dict):
    """
    Create user - seamless database integration.
    No session management boilerplate!
    """
    # This just works! No session.add() or session.commit() needed
    user = await User.create(**user_data)
    return {"user": user.to_dict(), "message": "User created seamlessly!"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """
    Get user with automatic 404 handling.
    Seamless database access without any session setup.
    """
    # This just works! Automatic session management + 404 handling
    user = await User.find_or_404(user_id)
    return {"user": user.to_dict()}


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """
    Delete user - seamless destruction.
    No manual transaction management needed.
    """
    user = await User.find_or_404(user_id)
    await user.destroy()  # Seamlessly handles session and commit
    return {"message": f"User {user_id} deleted successfully"}


@app.get("/posts")
async def list_posts():
    """List posts with complex queries - all seamless."""
    published_posts = await Post.where(published=True).order_by('-created_at').limit(5)
    return {
        "posts": [post.to_dict() for post in published_posts],
        "message": "Complex queries work seamlessly!"
    }


@app.get("/stats")
async def get_stats():
    """
    Database statistics using seamless Rails-like methods.
    All database operations just work without session management.
    """
    # Multiple database operations in one request - all seamless!
    total_users = await User.count()
    active_users = await User.where(active=True).count()
    total_posts = await Post.count()
    published_posts = await Post.where(published=True).count()

    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "posts": {
            "total": total_posts,
            "published": published_posts
        },
        "message": "All database operations completed seamlessly!"
    }


# 🛠️ Database setup (creates tables)
@app.on_event("startup")
async def setup_database():
    """Create database tables."""
    from zenith.db import Database

    db_url = os.getenv("DATABASE_URL")
    db = Database(db_url)
    await db.create_all()

    print("✅ Database setup complete")
    print("🎯 ZenithModel seamless integration ready!")


if __name__ == "__main__":
    print("🚀 Starting Seamless Integration Demo")
    print("📍 Server will start at: http://localhost:8018")
    print()
    print("✨ Key Benefits Demonstrated:")
    print("   🔗 ZenithModel automatically uses app's database sessions")
    print("   🚫 NO manual session management in route handlers")
    print("   🎯 Rails-like convenience with zero boilerplate")
    print("   ⚡ Request-scoped session reuse for better performance")
    print()
    print("🔗 Try these endpoints:")
    print("   GET /users      - List users (seamless querying)")
    print("   POST /users     - Create user (seamless saving)")
    print("   GET /users/1    - Get user (seamless find + 404)")
    print("   DELETE /users/1 - Delete user (seamless destruction)")
    print("   GET /stats      - Database stats (seamless counting)")

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8018)