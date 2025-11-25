#!/usr/bin/env python3
"""
Request-scoped async database session example.

This example demonstrates how to properly handle async database sessions
with request-scoped dependency injection to avoid event loop binding issues.

Run:
    python examples/16-async-database-scoped.py

Then test:
    curl http://localhost:8016/users
    curl -X POST http://localhost:8016/users -H "Content-Type: application/json" -d '{"name":"Alice","email":"alice@example.com"}'
"""

import asyncio
from collections.abc import AsyncGenerator

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from zenith import RequestScoped, Zenith
from zenith.exceptions import NotFoundError

# SQLAlchemy models
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)


# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


# Database setup - This can be at module level!
# The engine binding to event loop happens here, but sessions are created per-request
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Session factory for request-scoped injection
async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Create a new database session for each request.

    This ensures the session is created in the correct async context
    and properly cleaned up after the request.
    """
    async with async_session_maker() as session:
        yield session


# Create the app
app = Zenith(
    title="Async Database Example",
    version="1.0.0",
    # Auto-detects environment from ZENITH_ENV
)


@app.on_startup
async def startup():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")


@app.on_shutdown
async def shutdown():
    """Clean up database connections on shutdown."""
    await engine.dispose()
    print("✅ Database connections closed")


@app.get("/users", response_model=list[User])
async def get_users(db: AsyncSession = RequestScoped(get_db)):
    """
    Get all users.

    The database session is properly scoped to this request,
    avoiding event loop binding issues.
    """
    result = await db.execute(select(UserModel))
    users = result.scalars().all()
    return [User.model_validate(u) for u in users]


@app.post("/users", response_model=User)
async def create_user(user_data: UserCreate, db: AsyncSession = RequestScoped(get_db)):
    """
    Create a new user.

    Each request gets its own database session created in the
    correct async context.
    """
    user = UserModel(name=user_data.name, email=user_data.email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return User.model_validate(user)


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int, db: AsyncSession = RequestScoped(get_db)):
    """
    Get a specific user by ID.

    Demonstrates that each endpoint gets its own properly scoped session.
    """
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return User.model_validate(user)


# Alternative: Using RequestScoped directly
@app.get("/users/alt/list", response_model=list[User])
async def get_users_alt(db: AsyncSession = RequestScoped(get_db)):
    """
    Alternative syntax using RequestScoped directly.

    RequestScoped ensures proper async context handling for database sessions.
    """
    result = await db.execute(select(UserModel))
    users = result.scalars().all()
    return [User.model_validate(u) for u in users]


# Test concurrent requests
async def test_concurrent_requests():
    """Test that concurrent requests work without event loop issues."""
    from httpx import AsyncClient

    async with AsyncClient(base_url="http://localhost:8016") as client:
        # Create users concurrently
        tasks = [
            client.post(
                "/users", json={"name": f"User{i}", "email": f"user{i}@example.com"}
            )
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        for r in results:
            assert r.status_code == 200, f"Failed: {r.text}"

        # Get users concurrently
        tasks = [client.get("/users") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        for r in results:
            assert r.status_code == 200, f"Failed: {r.text}"
            assert len(r.json()) == 5, "Should have 5 users"

        print("✅ Concurrent request test passed!")


if __name__ == "__main__":
    print("🚀 Starting Async Database Example with Request-Scoped Sessions")
    print("📍 Server will start at: http://localhost:8016")
    print("\n📖 This example demonstrates:")
    print("   • Request-scoped database sessions")
    print("   • Proper async context isolation")
    print("   • No event loop binding issues")
    print("   • Safe concurrent request handling")
    print("\n🔗 Try these endpoints:")
    print("   GET  /users           - List all users")
    print("   POST /users           - Create a user")
    print("   GET  /users/{id}      - Get specific user")
    print("   GET  /users/alt/list  - Alternative syntax example")

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8016)
