# Zenith v0.2.6 Migration Guide

This guide helps you migrate from previous versions of Zenith to v0.2.6, which includes critical fixes for async database operations and enhanced dependency injection.

## 🚨 Critical Fixes (Action Required)

### 1. Async Database Session Handling

**Issue**: Applications were crashing with "Future attached to different loop" errors in production.

**❌ Broken Pattern (Remove This)**:
```python
# DON'T DO THIS - Will crash in production
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# ❌ Module-level engine creation binds to wrong event loop
engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession)

@app.get("/users")
async def get_users():
    # ❌ This will crash with concurrent requests
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        return result.scalars().all()
```

**✅ Fixed Pattern (Use This)**:
```python
# ✅ Request-scoped database sessions
from zenith import DatabaseSession, Depends  # FastAPI-compatible!
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# ✅ Factory function for request-scoped sessions
async def get_db():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

# ✅ Both syntaxes work:
@app.get("/users")
async def get_users(db: AsyncSession = DatabaseSession(get_db)):  # Zenith style
    result = await db.execute(select(User))
    return result.scalars().all()

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):  # FastAPI style
    result = await db.execute(select(User))
    return result.scalars().all()
```

### 2. Service Dependency Injection

**Issue**: Service injection with `Inject()` was failing with "Service not registered" errors.

**✅ Now Works Automatically**:
```python
from zenith import Service, Inject

class UserService(Service):
    async def get_user(self, user_id: str):
        return {"id": user_id}

# ✅ This now works automatically (auto-registration)
@app.get("/users/{user_id}")
async def get_user(user_id: str, users: UserService = Inject()):
    return await users.get_user(user_id)
```

**If you have manual registration code, you can remove it**:
```python
# ❌ Remove manual registration (no longer needed)
# app.register_service(UserService)  # Delete this line

# ✅ Auto-registration works now
@app.get("/users/{user_id}")
async def get_user(user_id: str, users: UserService = Inject()):
    return await users.get_user(user_id)
```

## 🆕 New Features You Can Use

### 1. FastAPI-Compatible Dependency Injection

You can now use `Depends()` just like in FastAPI:

```python
from zenith import Depends  # FastAPI-compatible import

# ✅ FastAPI code works unchanged:
@app.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    return await db.execute(select(Item))

# ✅ Mix and match with Zenith patterns:
@app.get("/items")
async def get_items(
    db: AsyncSession = Depends(get_db),        # FastAPI style
    service: ItemService = Inject(),           # Zenith style
):
    return await service.get_items(db)
```

### 2. Enhanced File Upload UX

**New UploadedFile API** with convenient methods:

```python
from zenith import File
from zenith.web.files import UploadedFile

# ✅ Enhanced file upload with automatic validation
@app.post("/upload")
async def upload_file(file: UploadedFile = File(
    max_size=5 * 1024 * 1024,  # 5MB
    allowed_types=["image/jpeg", "image/png", "application/pdf"]
)):
    # ✅ Convenient methods available
    if file.is_image():
        print("It's an image!")

    extension = file.get_extension()  # ".jpg"

    # ✅ Easy file operations
    final_path = await file.move_to(f"/uploads/{uuid.uuid4()}{extension}")

    # ✅ Starlette-compatible read() method
    content = await file.read()

    return {"saved_to": str(final_path)}
```

### 3. Enhanced SPA Configuration

```python
# ✅ Before (basic):
app.spa("dist")

# ✅ After (powerful):
app.spa(
    "dist",
    index="app.html",               # Custom index file
    exclude=["/api/*", "/admin/*"]  # Don't fallback for API routes
)
```

### 4. Intelligent Middleware Management

```python
# ✅ Duplicate prevention (default behavior):
app.add_middleware(RateLimitMiddleware, requests=100)
app.add_middleware(RateLimitMiddleware, requests=200)  # Replaces previous

# ✅ Explicit control when needed:
app.add_middleware(RateLimitMiddleware, replace=False)        # Raises error if exists
app.add_middleware(RateLimitMiddleware, allow_duplicates=True) # Allows duplicates
```

## 📋 Step-by-Step Migration

### Step 1: Update Database Patterns

1. **Find** module-level database engine creation:
   ```bash
   grep -r "create_async_engine" . --include="*.py"
   ```

2. **Replace** with request-scoped factories:
   ```python
   # Move engine creation into a function
   async def get_db():
       engine = create_async_engine(DATABASE_URL)
       SessionLocal = sessionmaker(engine, class_=AsyncSession)
       async with SessionLocal() as session:
           yield session
   ```

3. **Update** route handlers:
   ```python
   # Change from global session to injected session
   @app.get("/users")
   async def get_users(db: AsyncSession = DatabaseSession(get_db)):
       # Use db parameter instead of global session
   ```

### Step 2: Update Service Injection

1. **Remove** manual service registration:
   ```python
   # Delete these lines if you have them:
   # app.register_service(UserService)
   # app.contexts.register("users", UserService)
   ```

2. **Verify** services extend `Service`:
   ```python
   from zenith import Service

   class UserService(Service):  # ✅ Must extend Service
       pass
   ```

### Step 3: Test Concurrent Requests

After migration, test with concurrent requests to ensure no crashes:

```python
import asyncio
import httpx

async def test_concurrent():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Test 10 concurrent database requests
        tasks = [client.get("/users") for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        for r in responses:
            assert r.status_code == 200

        print("✅ Concurrent requests work!")

# Run this test after migration
asyncio.run(test_concurrent())
```

## 🔧 Troubleshooting

### "Future attached to different loop" errors

- Check for module-level `create_async_engine()` calls
- Move engine creation inside request-scoped functions
- Use `DatabaseSession()` or `Depends()` for injection

### "Service not registered" errors

- Ensure service classes extend `zenith.Service`
- Remove manual registration code
- Check import statements are correct

### File upload compatibility issues

- Update to new `UploadedFile` type hints
- Use enhanced API methods like `file.move_to()`
- Check file validation configuration

### Middleware duplication issues

- Remove duplicate `add_middleware()` calls
- Use `replace=True` (default) to replace existing middleware
- Use `allow_duplicates=True` only when intentional

## ✅ Validation Checklist

After migration, verify:

- [ ] No more "Future attached to different loop" crashes
- [ ] Service injection works without manual registration
- [ ] File uploads work with enhanced API
- [ ] Concurrent requests handled properly
- [ ] No duplicate middleware warnings
- [ ] All tests pass
- [ ] Performance maintained or improved

## 🆘 Need Help?

If you encounter issues during migration:

1. **Check examples**: See `examples/16-async-database-scoped.py`
2. **Review tests**: Look at the test suite for patterns
3. **File issues**: Report problems on GitHub

---

**Migration Timeline**: Allow 30-60 minutes for small applications, 2-4 hours for larger codebases.

The critical database fixes make this migration essential for production stability.