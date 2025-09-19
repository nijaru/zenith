# Critical Zenith Framework Bug: Async Database Event Loop Binding

## Bug Summary
Zenith Web Framework (v0.2.6) has a critical design flaw where async database engines become permanently bound to the event loop they were created in, causing "Future attached to a different loop" errors in production applications.

## Severity: CRITICAL 🔴
This bug makes Zenith unsuitable for production use with async databases.

## Affected Versions
- Confirmed in: v0.2.2, v0.2.4, v0.2.5, v0.2.6
- Likely affects: All versions with async SQLAlchemy support

## Bug Description

### The Problem
When using SQLAlchemy's async engine with Zenith, the engine becomes bound to a specific event loop at creation time. Since Zenith creates the engine during application initialization but handles requests in different async contexts, any database operation fails with:

```
RuntimeError: Task <Task pending> got Future <Future pending> attached to a different loop
```

### Root Cause
1. Zenith initializes the async engine at startup in one event loop
2. Request handlers run in different async contexts/loops
3. The engine's connection pool is bound to the original loop
4. Any attempt to use the engine from a request handler fails

### Code That Triggers the Bug

```python
# In Zenith application initialization
from sqlalchemy.ext.asyncio import create_async_engine

# This creates an engine bound to the startup event loop
engine = create_async_engine("postgresql+asyncpg://...")

# Later in a request handler
@app.post("/api/users")
async def create_user(user_data: UserCreate):
    # This FAILS with event loop error
    async with AsyncSession(engine) as session:
        # ... database operations
```

## Impact on Applications

### What Breaks
- ❌ All async database operations from request handlers
- ❌ User registration/login with database storage
- ❌ Any CRUD operations on database models
- ❌ Portfolio management features
- ❌ Transaction history tracking
- ❌ Real-time data persistence

### What Still Works
- ✅ Application startup
- ✅ Static routes
- ✅ In-memory operations
- ✅ External API calls (non-database)

## Current Workaround (Performance Penalty)

We've implemented a per-request engine creation pattern, but this has severe drawbacks:

```python
async def database_operation():
    # Create new engine for EVERY request (huge overhead)
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession)

    try:
        async with SessionLocal() as session:
            # ... perform operation
    finally:
        # Must dispose of engine to prevent connection leaks
        await engine.dispose()
```

### Workaround Problems
- 🔴 **Performance**: Creating engine per-request is extremely expensive
- 🔴 **Connection Pool**: Loses all benefits of connection pooling
- 🔴 **Latency**: Adds 50-100ms to every database operation
- 🔴 **Scalability**: Cannot handle high request volumes
- 🔴 **Resource Usage**: Excessive connection churn to database

## Why This Is a Framework Bug

This is NOT an application implementation issue. The bug exists because:

1. **Zenith's Architecture**: The framework doesn't properly manage async contexts between initialization and request handling
2. **No Documentation**: Zenith docs don't mention this limitation or provide guidance
3. **No Built-in Solution**: Framework provides no way to properly share async engines
4. **Breaks Standard Patterns**: Standard SQLAlchemy async patterns fail in Zenith

## Attempted Solutions That Failed

### 1. Lazy Initialization
```python
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(...)
    return _engine
```
**Result**: Still fails - engine created in first request's loop, breaks in subsequent requests

### 2. Context Variables
```python
from contextvars import ContextVar

engine_context = ContextVar('engine')
```
**Result**: Doesn't solve the loop binding issue

### 3. Engine per Worker
**Result**: Zenith's worker model doesn't expose worker lifecycle hooks

## Required Framework Fix

Zenith needs to implement one of these solutions:

### Option 1: Request Context Engine
```python
# Framework should provide this
@app.request_context
async def get_db_session():
    """Called by framework for each request"""
    return create_session_for_request()
```

### Option 2: Proper Lifecycle Management
```python
# Framework should handle engine lifecycle
class ZenithApp:
    async def on_request_start(self):
        # Create request-specific engine/session

    async def on_request_end(self):
        # Cleanup connections
```

### Option 3: Built-in Database Support
```python
# Framework should provide database integration
from zenith.ext.database import DatabaseExtension

app.use_extension(DatabaseExtension(
    url="postgresql+asyncpg://...",
    pool_size=20
))
```

## Reproduction Steps

1. Create a Zenith app with async PostgreSQL:
```python
from zenith import App
from sqlalchemy.ext.asyncio import create_async_engine

app = App()
engine = create_async_engine("postgresql+asyncpg://...")

@app.post("/test")
async def test_endpoint():
    async with AsyncSession(engine) as session:
        result = await session.execute("SELECT 1")
    return {"status": "ok"}
```

2. Start the application
3. Make a request to `/test`
4. Observe the "Future attached to different loop" error

## Test Environment
- Python: 3.12
- Zenith: 0.2.6
- SQLAlchemy: 2.0.36
- asyncpg: 0.30.0
- PostgreSQL: 14+
- OS: macOS, Linux (both affected)

## Business Impact

This bug is preventing WealthScope (and likely other applications) from using Zenith in production:

- **Development Speed**: Every database operation requires complex workarounds
- **Performance**: Current workaround adds unacceptable latency
- **Reliability**: Per-request engines can exhaust database connections
- **Maintenance**: Workaround code is fragile and hard to maintain
- **Adoption**: Developers will choose other frameworks that handle this correctly

## Comparison with Other Frameworks

### FastAPI (Works Correctly)
```python
# FastAPI handles this properly
async def get_db():
    async with SessionLocal() as session:
        yield session

@app.post("/users")
async def create_user(db: Session = Depends(get_db)):
    # Works perfectly
```

### Starlette (Works Correctly)
```python
# Starlette also handles async contexts properly
async with database.transaction():
    # Works without issues
```

## Recommendation

**This bug must be fixed at the framework level**. Until then, Zenith cannot be recommended for production applications that require database access. The current workarounds are not sustainable for real-world applications.

## Priority: P0 - Critical

This completely blocks production deployment of any database-backed application using Zenith.

---

*Reported by: WealthScope Development Team*
*Date: 2025-01-15*
*Zenith Version: 0.2.6*
*Status: Unresolved*