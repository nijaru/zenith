---
title: Dependency Injection
description: Request-scoped dependencies and Service architecture for clean, testable code
---

# Dependency Injection

Zenith provides powerful dependency injection with request-scoped resources and Service-based architecture for clean, testable applications.

## 🚨 Critical: Request-Scoped Dependencies

**Avoid async crashes** with proper request-scoped dependencies for database sessions and other resources.

### The Problem (DON'T DO THIS)

```python
# ❌ DANGEROUS - Will crash with "Future attached to different loop"
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Module-level engine binds to wrong event loop
engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession)

@app.get("/users")
async def get_users():
    # ❌ This crashes under concurrent requests
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        return result.scalars().all()
```

### The Solution (DO THIS)

```python
# ✅ Request-scoped database sessions
from zenith import DatabaseSession, Depends, Service, Inject
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Factory function for request-scoped sessions
async def get_db():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession)
    async with SessionLocal() as session:
        yield session

class UserService(Service):
    async def get_users(self, db: AsyncSession):
        result = await db.execute(select(User))
        return result.scalars().all()

# Both patterns work (FastAPI-compatible)
@app.get("/users")
async def get_users_zenith(
    db: AsyncSession = DatabaseSession(get_db),  # Zenith style
    users: UserService = Inject()                 # Service injection
):
    return await users.get_users(db)

@app.get("/users-fastapi")
async def get_users_fastapi(
    db: AsyncSession = Depends(get_db)            # FastAPI style
):
    # Direct database access
    result = await db.execute(select(User))
    return result.scalars().all()
```

## Service Architecture

Organize business logic in Service classes for clean, testable architecture.

### Basic Service

```python
from zenith import Service, Inject

class UserService(Service):
    """Business logic for user operations."""

    async def create_user(self, user_data: UserCreate) -> User:
        # Validation, business rules, etc.
        if await self.user_exists(user_data.email):
            raise ValueError("User already exists")

        user = User(**user_data.model_dump())
        # Save to database, send emails, etc.
        return user

    async def user_exists(self, email: str) -> bool:
        # Business logic here
        return False

# Usage in routes (automatic dependency injection)
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    users: UserService = Inject()  # Auto-injected
) -> User:
    return await users.create_user(user_data)
```

### Service with Dependencies

```python
class UserService(Service):
    async def get_users(self, db: AsyncSession) -> list[User]:
        # Use injected database session
        result = await db.execute(select(User))
        return result.scalars().all()

    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> User:
        user = User(**user_data.model_dump())
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

@app.get("/users")
async def get_users(
    db: AsyncSession = DatabaseSession(get_db),
    users: UserService = Inject()
):
    return await users.get_users(db)

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = DatabaseSession(get_db),
    users: UserService = Inject()
):
    return await users.create_user(user_data, db)
```

## Request-Scoped Dependencies

For any resource that needs to be created fresh per request:

### Custom Request-Scoped Resource

```python
from zenith import RequestScoped

async def get_redis():
    # Fresh Redis connection per request
    redis = await aioredis.create_redis_pool("redis://localhost")
    try:
        yield redis
    finally:
        redis.close()
        await redis.wait_closed()

async def get_s3_client():
    # Fresh S3 client per request
    session = aiobotocore.get_session()
    async with session.create_client('s3') as s3:
        yield s3

@app.get("/data")
async def get_data(
    redis = RequestScoped(get_redis),
    s3 = RequestScoped(get_s3_client)
):
    # Each request gets fresh connections
    cached = await redis.get("key")
    if not cached:
        data = await s3.get_object(Bucket="my-bucket", Key="data.json")
        await redis.set("key", data)
    return cached
```

## FastAPI Compatibility

Zenith is fully compatible with FastAPI patterns:

```python
from zenith import Depends  # Same as FastAPI's Depends

# FastAPI-style dependency injection
def get_current_user(token: str = Header(...)):
    # Authentication logic
    return User(id=1, name="John")

@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {"user": user.name}

# Mix and match with Zenith patterns
@app.get("/dashboard")
async def dashboard(
    user: User = Depends(get_current_user),      # FastAPI style
    db: AsyncSession = DatabaseSession(get_db), # Zenith style
    users: UserService = Inject()               # Service injection
):
    return await users.get_user_dashboard(db, user.id)
```

## Testing Dependencies

Override dependencies for testing:

```python
from zenith.testing import TestClient

# Mock database for testing
async def get_test_db():
    # In-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    SessionLocal = sessionmaker(engine, class_=AsyncSession)
    async with SessionLocal() as session:
        yield session

# Test with dependency override
async def test_create_user():
    app.dependency_overrides[get_db] = get_test_db

    async with TestClient(app) as client:
        response = await client.post("/users", json={
            "name": "Test User",
            "email": "test@example.com"
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Test User"
```

## Best Practices

### ✅ Do

- Use `DatabaseSession` or `Depends` for async resources
- Organize business logic in Service classes
- Keep route handlers thin - delegate to services
- Use request-scoped dependencies for connections
- Test services independently of HTTP layer

### ❌ Don't

- Create global database connections at module level
- Put business logic directly in route handlers
- Share mutable state between requests
- Forget to yield resources that need cleanup
- Mix HTTP concerns with business logic

## Migration from FastAPI

Zenith is designed for easy migration from FastAPI:

```python
# FastAPI code works unchanged:
from fastapi import Depends  # or from zenith import Depends

@app.get("/items")
async def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()

# Enhance with Zenith patterns:
class ItemService(Service):
    async def get_items(self, db: Session) -> list[Item]:
        return db.query(Item).all()

@app.get("/items")
async def get_items(
    db: Session = Depends(get_db),        # Keep existing
    items: ItemService = Inject()         # Add service layer
):
    return await items.get_items(db)
```

The `Depends` import works exactly the same - your FastAPI code will run unchanged in Zenith!