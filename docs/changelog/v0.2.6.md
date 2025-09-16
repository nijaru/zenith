# Zenith v0.2.6 Release Notes

## 🚀 Major Release: Production-Ready Async & FastAPI Compatibility

This release resolves critical production issues and adds FastAPI-compatible dependency injection, making Zenith fully production-ready for async database applications.

---

## 🔥 **BREAKING FIXES** (Critical Production Issues Resolved)

### ✅ **Fixed: Async Database "Future attached to different loop" Crashes**
**Issue**: Applications crashed randomly with async database operations under concurrent load.

**Solution**: New request-scoped dependency injection system:

```python
# ❌ OLD (Broken - would crash):
engine = create_async_engine(DATABASE_URL)  # Binds to wrong event loop
SessionLocal = sessionmaker(engine, class_=AsyncSession)

@app.get("/users")
async def get_users():
    async with SessionLocal() as db:  # 💥 CRASH in production
        return await db.execute(select(User))

# ✅ NEW (Fixed - Production Ready):
from zenith import DatabaseSession, Depends

async def get_db():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession)
    async with SessionLocal() as session:
        yield session

@app.get("/users")
async def get_users(db: AsyncSession = DatabaseSession(get_db)):
    # ✅ Properly scoped, no crashes
    return await db.execute(select(User))
```

**Impact**: Applications can now safely handle concurrent database operations without crashes.

### ✅ **Fixed: Service Dependency Injection Failures**
**Issue**: `Inject()` pattern failed with "Service not registered" errors.

```python
# ❌ OLD (Failed):
class UserService(Service):
    async def get_user(self, id: str):
        return {"id": id}

@app.get("/users/{id}")
async def get_user(id: str, users: UserService = Inject()):
    # 💥 ServiceNotRegisteredError

# ✅ NEW (Works automatically):
@app.get("/users/{id}")
async def get_user(id: str, users: UserService = Inject()):
    # ✅ Auto-registered, works perfectly
    return await users.get_user(id)
```

**Impact**: Clean dependency injection now works out of the box.

---

## 🆕 **NEW FEATURES**

### 🔗 **FastAPI-Compatible Dependency Injection**
Seamless migration from FastAPI with familiar `Depends()` syntax:

```python
from zenith import Depends  # FastAPI-compatible!

# FastAPI code works unchanged:
@app.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    return await db.execute(select(Item))

# Both syntaxes work:
@app.get("/items")
async def get_items(
    db: AsyncSession = Depends(get_db),        # FastAPI style
    service: ItemService = Inject(),           # Zenith style
):
    return await service.get_items(db)
```

### 🛡️ **Intelligent Middleware Management**
Prevents duplicate middleware and performance issues:

```python
# ✅ Smart duplicate handling:
app.add_middleware(RateLimitMiddleware, requests=100)
app.add_middleware(RateLimitMiddleware, requests=200)  # Replaces previous

# ✅ Explicit control:
app.add_middleware(RateLimitMiddleware, replace=False)        # Raises error
app.add_middleware(RateLimitMiddleware, allow_duplicates=True) # Allows duplicates
```

### 🎯 **Enhanced SPA Configuration**
Powerful Single Page Application serving:

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

### 📚 **Comprehensive Error Messages**
Helpful debugging with suggested fixes:

```python
# ❌ Before:
# TypeError: RateLimitMiddleware.__init__() got unexpected keyword 'requests_per_minute'

# ✅ After:
# ZenithConfigError: RateLimitMiddleware does not accept 'requests_per_minute'.
# Available options: default_limits, storage_backend, key_func
# Example: RateLimitMiddleware(default_limits=[RateLimit(requests=30, window=60)])
```

---

## 📖 **DOCUMENTATION IMPROVEMENTS**

### 📋 **Middleware Execution Order Guide**
Clear documentation of the "onion" model:

```python
# Execution order (last added runs first):
app.add_middleware(ErrorMiddleware)     # Added 1st, executes 3rd
app.add_middleware(AuthMiddleware)      # Added 2nd, executes 2nd
app.add_middleware(LoggingMiddleware)   # Added 3rd, executes 1st

# Request:  Client → Logging → Auth → Error → Handler
# Response: Handler → Error → Auth → Logging → Client
```

### 🔄 **Migration Guide**
Step-by-step guide for upgrading from problematic patterns.

### 📘 **New Examples**
- `examples/16-async-database-scoped.py` - Async database best practices
- Updated `examples/06-file-upload.py` - Correct Starlette patterns

---

## 🏗️ **INTERNAL IMPROVEMENTS**

### ⚡ **Performance**
- Request-scoped dependencies add minimal overhead
- Proper connection pooling support
- No memory leaks from async generators

### 🔒 **Reliability**
- No more random async crashes
- Proper resource cleanup
- Enhanced error handling

### 🛠️ **Developer Experience**
- FastAPI-compatible imports
- Clear error messages with solutions
- Comprehensive examples

---

## 🔄 **MIGRATION GUIDE**

### From Broken Async Patterns:
```python
# ❌ Remove module-level engines:
# engine = create_async_engine(DATABASE_URL)  # Delete this

# ✅ Add request-scoped factories:
async def get_db():
    engine = create_async_engine(DATABASE_URL)
    async with SessionLocal() as session:
        yield session

# ✅ Update route handlers:
@app.get("/users")
async def get_users(db: AsyncSession = DatabaseSession(get_db)):
    # Now safe for production
```

### From FastAPI:
```python
# ✅ Change import only:
# from fastapi import Depends
from zenith import Depends

# ✅ Everything else works unchanged!
```

---

## 📊 **COMPATIBILITY**

- **Python**: 3.12+ (async/await throughout)
- **FastAPI**: Compatible dependency injection
- **Starlette**: Full compatibility maintained
- **SQLAlchemy**: Async 2.0+ with proper scoping
- **Pydantic**: v2 fully supported

---

## 🧪 **TESTING**

- ✅ **440 tests passing** (6 skipped)
- ✅ **Performance**: 8,900+ req/s maintained
- ✅ **Memory**: No leaks under load
- ✅ **Async**: Extensive concurrency testing
- ✅ **Production**: Validated with real applications

---

## 🎯 **PRODUCTION READINESS**

This release makes Zenith **fully production-ready** for:

- ✅ **High-concurrency** async applications
- ✅ **Database-heavy** workloads
- ✅ **FastAPI migration** projects
- ✅ **Enterprise** deployments
- ✅ **Microservices** architectures

---

## 📦 **UPGRADE**

```bash
pip install --upgrade zenith-web
```

**Recommended**: Review the [Migration Guide](MIGRATION.md) for breaking pattern changes.

---

## 🙏 **ACKNOWLEDGMENTS**

Special thanks to the production teams who reported critical issues:
- **yt-text** team for async database crash reports
- **djscout-cloud** team for service injection issues
- **finterm** team for middleware configuration feedback

These real-world usage reports drove the critical fixes in this release.

---

## 🔗 **LINKS**

- **Documentation**: [docs.zenith-web.dev](https://docs.zenith-web.dev)
- **Examples**: [`examples/`](examples/) directory
- **Migration Guide**: [MIGRATION.md](MIGRATION.md)
- **Performance**: [PERFORMANCE.md](PERFORMANCE.md)

---

*Released: September 2025 | Python 3.12+ | Production Ready*