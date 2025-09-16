# Zenith v0.3.0 Migration Guide

## Overview
Zenith v0.3.0 introduces Rails-like developer experience improvements with breaking changes to create a cleaner, more intuitive API.

## Breaking Changes

### 1. Removed Redundant Aliases
The following exports have been removed from `zenith` package. Use the recommended alternatives:

| Removed | Use Instead | Example |
|---------|------------|---------|
| `ServiceDecorator` | `Service` base class | `class MyService(Service):` |
| `AuthDependency` | `Auth` | `user=Auth` |
| `FileDependency` | `File` | `upload=File("file")` |
| `ServiceInject` | `Inject` | `service: MyService = Inject()` |

### 2. Import Changes

**Before (v0.2.x):**
```python
from zenith import ServiceDecorator, AuthDependency, FileDependency, ServiceInject

@ServiceDecorator()
class UserService:
    pass

@app.get("/protected")
async def protected(user=AuthDependency()):
    pass
```

**After (v0.3.0):**
```python
from zenith import Service, Auth, File, Inject

class UserService(Service):
    pass

@app.get("/protected")
async def protected(user=Auth):
    pass
```

## New Features in v0.3.0

### 1. High-Level Decorators
New decorators for common patterns:
```python
from zenith import cache, rate_limit, auth_required, paginate, returns, validate, transaction

@app.get("/users")
@cache(ttl=300)  # Cache for 5 minutes
@rate_limit("10/minute")
@paginate(default_limit=20)
async def list_users():
    return await User.all()

@app.get("/users/{id}")
@returns(User)  # Auto-404 if None
async def get_user(id: int):
    return await User.find(id)
```

### 2. Enhanced Dependency Injection
Cleaner shortcuts for common dependencies:
```python
from zenith import DB, CurrentUser, Cache, Request

@app.get("/profile")
async def get_profile(user=CurrentUser):  # Instead of Depends(get_current_user)
    return user

@app.get("/data")
async def get_data(db=DB):  # Instead of Depends(get_session)
    return await db.query(Data).all()
```

### 3. Pagination Utilities
Built-in pagination support:
```python
from zenith import Paginate, PaginatedResponse

@app.get("/posts")
async def list_posts(pagination: Paginate = Paginate()):
    posts = await Post.paginate(pagination.page, pagination.limit)
    return PaginatedResponse.create(
        items=posts,
        page=pagination.page,
        limit=pagination.limit,
        total=await Post.count()
    )
```

## Migration Steps

### Step 1: Update Imports
Search and replace deprecated imports:
```bash
# Find all uses of deprecated imports
rg "ServiceDecorator|AuthDependency|FileDependency|ServiceInject"

# Update imports in your code:
# ServiceDecorator -> Service
# AuthDependency -> Auth
# FileDependency -> File
# ServiceInject -> Inject
```

### Step 2: Update Service Classes
Change from decorator pattern to inheritance:

**Before:**
```python
@ServiceDecorator()
class UserService:
    def __init__(self):
        pass
```

**After:**
```python
from zenith import Service

class UserService(Service):
    def __init__(self):
        super().__init__()
```

### Step 3: Update Dependency Injection

**Before:**
```python
from zenith import AuthDependency, ServiceInject

@app.get("/protected")
async def protected(user=AuthDependency(), service: UserService = ServiceInject()):
    pass
```

**After:**
```python
from zenith import Auth, Inject

@app.get("/protected")
async def protected(user=Auth, service: UserService = Inject()):
    pass
```

### Step 4: Take Advantage of New Features
Consider adopting the new high-level decorators for cleaner code:

```python
# Add caching to expensive operations
@cache(ttl=300)
async def expensive_operation():
    pass

# Add rate limiting to protect endpoints
@rate_limit("100/hour")
async def api_endpoint():
    pass

# Simplify authentication
@auth_required(role="admin")
async def admin_endpoint():
    pass
```

## Testing Your Migration

1. **Run your test suite** after making changes
2. **Check import errors** - ensure no references to removed exports
3. **Verify dependency injection** still works correctly
4. **Test authentication** flows if using Auth changes

## Need Help?

- Check the [examples](examples/) directory for v0.3.0 patterns
- Review the [API documentation](docs/api/) for detailed information
- Open an issue on [GitHub](https://github.com/nijaru/zenith/issues) for migration problems

## Benefits of Upgrading

1. **Cleaner API** - No confusing duplicate exports
2. **Better DX** - More intuitive naming and patterns
3. **New Features** - High-level decorators, pagination, enhanced DI
4. **Performance** - Thread-safe caching and optimizations
5. **Future-proof** - Aligned with v1.0 API direction