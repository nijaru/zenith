# API Reference

> Complete reference for Zenith framework classes and functions

## Core Classes

### `Zenith`

Main application class for creating Zenith web applications.

```python
from zenith import Zenith

app = Zenith(debug=False, config=None, middleware=None)
```

**Parameters:**
- `debug` (bool): Enable debug mode with detailed error messages
- `config` (Config, optional): Custom configuration object
- `middleware` (List[Middleware], optional): Custom middleware stack

**Methods:**

#### Route Decorators

```python
@app.get(path: str, **kwargs)
@app.post(path: str, **kwargs) 
@app.put(path: str, **kwargs)
@app.patch(path: str, **kwargs)
@app.delete(path: str, **kwargs)
@app.options(path: str, **kwargs)
@app.head(path: str, **kwargs)
```

Define HTTP route handlers with automatic dependency injection.

**Example:**
```python
@app.get("/users/{user_id}")
async def get_user(user_id: int) -> dict:
    return {"user_id": user_id}

@app.post("/users")  
async def create_user(user: UserCreate) -> User:
    # Automatic Pydantic validation
    return User(**user.dict())
```

#### Middleware Configuration

```python
app.add_cors(
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False
)

app.add_security_headers(strict=False)

app.add_exception_handling(debug=False)

app.add_rate_limiting(default_limit=100, window_seconds=60)
```

#### Context Registration

```python
app.register_context(ContextClass)
```

Register a Context class for dependency injection.

#### Database Setup

```python  
app.setup_database(database_url: str, **kwargs)
```

Configure database connection with SQLAlchemy.

#### Application Lifecycle

```python
@app.on_event("startup")
async def startup():
    print("App starting up...")

@app.on_event("shutdown")
async def shutdown():
    print("App shutting down...")

# Run the application
app.run(host="0.0.0.0", port=8000, reload=False)
```

---

## Dependency Injection

### `Context()`

Dependency marker for injecting Context instances into route handlers.

```python
from zenith.core.routing import Context

@app.get("/users")
async def list_users(users: UsersContext = Context()) -> List[User]:
    return await users.get_all_users()
```

### `Auth()`

Dependency marker for injecting authenticated user information.

```python
from zenith.core.routing import Auth

@app.get("/profile")
async def get_profile(current_user = Auth(required=True)) -> User:
    return current_user

@app.get("/public")
async def public_endpoint(current_user = Auth(required=False)) -> dict:
    if current_user:
        return {"message": f"Hello {current_user['email']}"}
    return {"message": "Hello anonymous user"}

@app.get("/admin-only")
async def admin_only(current_user = Auth(required=True, scopes=["admin"])) -> dict:
    return {"message": "Admin access granted"}
```

### `File()`

Dependency marker for handling file uploads.

```python
from zenith.core.routing import File
from zenith.web.files import FileUploadConfig

config = FileUploadConfig(
    max_file_size=10 * 1024 * 1024,  # 10MB
    allowed_extensions=[".jpg", ".png", ".gif"],
    upload_dir="./uploads"
)

@app.post("/upload")
async def upload_file(file = File("image", config)) -> dict:
    return {
        "filename": file.filename,
        "size": file.size,
        "path": str(file.path)
    }
```

---

## Context System

### `Context`

Base class for organizing business logic and domain operations.

```python
from zenith.core.context import Context
from zenith.core.container import DIContainer

class UsersContext(Context):
    def __init__(self, container: DIContainer):
        super().__init__(container)
        # Initialize services, database connections, etc.
        
    async def create_user(self, user_data: dict) -> User:
        # Business logic for user creation
        pass
    
    async def get_user(self, user_id: int) -> User:
        # Business logic for user retrieval  
        pass
    
    async def delete_user(self, user_id: int) -> bool:
        # Business logic for user deletion
        pass
```

**Key Methods:**
- `emit(event: str, data: Any)` - Emit domain event
- `subscribe(event: str, callback)` - Subscribe to domain event
- `transaction()` - Database transaction context manager

---

## Authentication

### `configure_auth()`

Configure JWT-based authentication for your application.

```python
from zenith.auth import configure_auth

configure_auth(
    app,
    secret_key="your-secret-key",  # Must be 32+ characters
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)
```

### JWT Functions

```python
from zenith.auth.jwt import create_access_token, verify_access_token

# Create token
token = create_access_token(
    user_id=123,
    email="user@example.com", 
    role="user",
    scopes=["read", "write"]
)

# Verify token
user_data = verify_access_token(token)
# Returns: {"id": 123, "email": "user@example.com", "role": "user", "scopes": [...]}
```

### Password Functions

```python
from zenith.auth.password import hash_password, verify_password

# Hash password
hashed = hash_password("plaintext_password")

# Verify password
is_valid = verify_password("plaintext_password", hashed)
```

---

## File Handling

### `FileUploadConfig`

Configuration for file upload validation and processing.

```python
from zenith.web.files import FileUploadConfig

config = FileUploadConfig(
    upload_dir="./uploads",           # Where to store files
    max_file_size=10 * 1024 * 1024,  # 10MB max size
    allowed_extensions=[".jpg", ".png", ".gif"],  # Allowed file types
    allowed_mime_types=["image/jpeg", "image/png"],  # Allowed MIME types
    preserve_filename=False,          # Use UUID names instead
    create_subdirs=True,             # Organize by date subdirs
)
```

### `UploadedFile`

Represents an uploaded file with metadata.

```python
# Properties available on File() dependency injected parameter
file.filename          # Original filename
file.content_type      # MIME type
file.size             # File size in bytes  
file.path             # Path where file was saved
file.original_filename # Original uploaded filename
```

---

## Response Utilities

### Standard Responses

```python
from zenith.web.responses import (
    success_response,
    error_response, 
    paginated_response,
    redirect_response,
    file_download_response
)

# Success response
return success_response(
    data={"user_id": 123}, 
    message="User created successfully",
    status_code=201
)

# Error response  
return error_response(
    message="User not found",
    status_code=404,
    error_code="USER_NOT_FOUND",
    details={"user_id": user_id}
)

# Paginated response
return paginated_response(
    data=users,
    page=1,
    page_size=20,
    total_count=100,
    next_page="/users?page=2",
    prev_page=None
)

# File download
return file_download_response(
    file_path="/uploads/document.pdf",
    download_name="my_document.pdf"
)
```

---

## Health Checks

### Built-in Health System

```python
from zenith.web.health import health_manager, add_health_routes

# Add health endpoints to your app
add_health_routes(app)

# Add custom health checks
async def database_check():
    # Check database connectivity
    return True

health_manager.add_simple_check(
    name="database",
    check_function=database_check,
    timeout=5.0,
    critical=True
)

# Built-in checks
health_manager.add_database_check(database_url)
health_manager.add_redis_check(redis_url) 
health_manager.add_uptime_check(min_uptime=30.0)
```

**Endpoints:**
- `GET /health` - Full health check with all details
- `GET /ready` - Readiness check (critical checks only)
- `GET /live` - Liveness check (basic app health)

---

## Testing

### `TestClient`

Async HTTP client for testing Zenith applications.

```python
import pytest
from zenith.testing import TestClient

@pytest.mark.asyncio
async def test_api_endpoint():
    async with TestClient(app) as client:
        # Set authentication
        client.set_auth_token("user@example.com", user_id=123, role="admin")
        
        # Make requests
        response = await client.get("/users")
        assert response.status_code == 200
        
        response = await client.post("/users", json={"name": "John"})
        assert response.status_code == 201
```

### `TestContext`

Utility for testing Context classes in isolation.

```python
from zenith.testing import TestContext

@pytest.mark.asyncio
async def test_users_context():
    async with TestContext(UsersContext) as users:
        # Test context methods
        user = await users.create_user({"name": "John", "email": "john@example.com"})
        assert user.name == "John"
        
        retrieved = await users.get_user(user.id)  
        assert retrieved.email == "john@example.com"
```

### Test Utilities

```python
from zenith.testing import create_test_token

# Create JWT token for testing
token = create_test_token(
    email="test@example.com",
    user_id=123,
    role="admin", 
    scopes=["read", "write", "admin"]
)
```

---

## Configuration

### Environment Variables

Zenith reads configuration from environment variables:

```bash
# Required
SECRET_KEY=your-secret-key-that-is-at-least-32-characters-long

# Optional  
DEBUG=true                    # Enable debug mode
DATABASE_URL=postgresql://... # Database connection
CORS_ORIGINS=*               # CORS allowed origins
UPLOAD_DIR=./uploads         # File upload directory
MAX_FILE_SIZE=10485760       # Max upload size (bytes)

# JWT Configuration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256
```

### Custom Configuration

```python
from zenith.core.config import Config

config = Config(
    debug=True,
    secret_key="custom-secret-key",
    database_url="sqlite:///./test.db"
)

app = Zenith(config=config)
```

---

## CLI Commands

Zenith provides a CLI for common development tasks:

```bash
# Start development server  
zen serve --reload --port 8000

# Run tests
zen test

# Database migrations
zen db migrate "Add users table"
zen db upgrade

# Generate API docs
zen docs build

# Format code
zen format

# Type checking
zen typecheck
```

---

This covers the core Zenith API. For more examples and advanced usage, see:

- [Tutorial](../tutorial/index.md) - Step-by-step application building
- [Examples](../examples/index.md) - Real-world application examples  
- [Deployment](../deployment/index.md) - Production deployment guides