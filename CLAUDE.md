# Zenith - AI Assistant Context
*Comprehensive context for AI assistants working with the Zenith Python web framework*

## Release Strategy
**Dual Release Approach** (following Python framework conventions):

### PyPI Release (Primary - for users)
**IMPORTANT**: Use `twine` for PyPI uploads, not `uv publish`:
```bash
# Build and upload to PyPI
uv build
twine upload dist/zenithweb-{version}*
```

### GitHub Release (Secondary - for developers/changelog)
```bash
# Create GitHub release with detailed changelog
gh release create v{version} --title "v{version}: Brief Description" \
  --notes "## What's New
- Feature descriptions
- Bug fixes
- Breaking changes (if any)

Full changelog at https://github.com/nijaru/zenith/compare/v{prev-version}...v{version}"
```

**Release Decision Matrix:**
- ✅ **Major/minor releases** (0.x.0, x.0.0): Always both PyPI + GitHub
- ✅ **Critical patches**: Both (for maximum visibility)
- ⚖️ **Regular patches**: PyPI required, GitHub optional (developer judgment)

**Purpose split:**
- **PyPI**: User installation (`pip install zenithweb`)
- **GitHub**: Developer communication, changelog, contributor recognition

## Release Gotchas
**Quick sanity checks before release:**
- Dependencies updated: `uv run pip list --outdated` (check for updates)
- Security scan: `uv run pip-audit` (no vulnerabilities?)
- Run tests: `uv run pytest` (all passing?)
- Version bump: `pyproject.toml` updated?
- Examples work: `uv run python examples/00-hello-world.py`
- Docs updated: Removed references to deleted features?
- No temp files: `ZENITH_BUGS_*.md`, test outputs cleaned up?

**IMPORTANT - RELEASE PROCESS:**
- **NEVER release without explicit approval** - "prep release" means prepare only, not publish
- When asked to "prep release": build packages, update CHANGELOG.md, stage everything - but STOP
- Only release to PyPI/GitHub when explicitly told "release it" or "go ahead and release"

**RELEASE DOCUMENTATION:**
- Maintain `/CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com) format
- Use GitHub Releases for rich formatting and notifications
- Categories: Added, Changed, Fixed, Removed, Deprecated, Security
- Always update `[Unreleased]` section during development
- Move unreleased changes to versioned section before release

## Quick Facts
- **Product**: Modern Python API framework with exceptional developer experience and performance
- **Language**: Python 3.12+ (leveraging TaskGroups, generics, pattern matching)
- **Status**: v0.0.1 - Early release with zero-config setup and intuitive patterns
- **Performance**: 9,600+ req/s with optimized middleware stack and database session reuse
- **Test Coverage**: 100% integration tests (857 tests passing)
- **CLI**: `zen` command for development tools
- **Memory**: Zero memory leaks with bounded caches and automatic cleanup
- **DX**: 85% boilerplate reduction with intuitive patterns

## Framework Philosophy & Design

### Core Principles
1. **Clean Architecture** - Business logic in Contexts, separated from web concerns
2. **Type Safety** - Full type hints, Pydantic validation, minimal runtime errors
3. **Performance First** - Minimal overhead, efficient request handling, comprehensive benchmarks
4. **Developer Experience** - Intuitive APIs, excellent tooling, zero-configuration defaults
5. **Production Ready** - Security, monitoring, scalability, and reliability built-in
6. **Automation Over Validation** - Eliminate manual steps rather than trying to predict deployment success

### Key Differentiators
- **Intuitive Database Models**: `User.where(active=True).limit(10)` instead of raw SQLAlchemy
- **One-liner Setup**: `app.add_auth()`, `app.add_admin()`, `app.add_api()` for instant features
- **Zero-Configuration**: `app = Zenith()` auto-detects environment and configures everything
- **Seamless Database Integration**: ZenithModel automatically uses request-scoped sessions
- **Enhanced DI Shortcuts**: `db=DB`, `Auth`, `Cache` instead of verbose `Depends()` patterns
- **Context System**: Organizes business logic outside route handlers
- **Performance**: Exceptional performance with intelligent session reuse
- **Testing Framework**: Built-in TestClient with auth helpers and context testing
- **Comprehensive Middleware**: Production-ready CORS, security, rate limiting, logging

## Framework Excellence Standards

### Developer Experience (DX) Principles
1. **Fail Fast with Clear Messages** - Errors should guide developers to solutions
2. **Intuitive API Design** - Most common patterns should be simplest to express
3. **Progressive Disclosure** - Simple things simple, complex things possible
4. **Hot Reload by Default** - Changes visible immediately in development
5. **Type Safety Throughout** - IDE support, autocomplete, early error detection

### Performance Principles
1. **Zero-Cost Abstractions** - Conveniences shouldn't impact performance
2. **Lazy Loading** - Only load what's needed when it's needed
3. **Connection Pooling** - Reuse expensive resources efficiently
4. **Caching at Every Layer** - Memory, Redis, HTTP caching built-in
5. **Async-First Design** - Non-blocking I/O for maximum concurrency

### Production Readiness
1. **Secure by Default** - CSRF, XSS, SQL injection protection out of the box
2. **Observable** - Metrics, tracing, logging structured and available
3. **Resilient** - Circuit breakers, retries, timeouts, graceful degradation
4. **Scalable** - Horizontal scaling, stateless design, efficient resource use
5. **Documented** - Every feature with examples, migration guides, best practices

### API Design Guidelines
1. **Consistency** - Similar operations should have similar APIs
2. **Predictability** - Developers should be able to guess how things work
3. **Composability** - Components should work well together
4. **Backwards Compatibility** - Breaking changes only in major versions
5. **Error Recovery** - Always provide a way to handle errors gracefully

### Implementation Best Practices
1. **Test Everything** - 100% coverage for core functionality
2. **Benchmark Critical Paths** - Measure performance impact of changes
3. **Memory Efficiency** - Bounded caches, weak references, cleanup tasks
4. **Dependency Injection** - Loose coupling, testability, flexibility
5. **Clean Architecture** - Separate concerns, business logic from framework

## Project Structure & Architecture
```
zenith/                      # Framework source code
├── core/                   # Framework kernel
│   ├── application.py     # Main Zenith class - app creation and configuration
│   ├── service.py         # Service system for business logic organization
│   ├── routing/           # Modular routing system (router, executor, resolvers)
│   ├── config.py          # Application configuration management
│   └── container.py       # Dependency injection container
├── web/                   # Web-specific components
│   ├── responses.py       # Response handling and serialization
│   ├── health.py          # Health check endpoints (/health, /health/detailed)
│   ├── metrics.py         # Prometheus metrics (/metrics)
│   ├── files.py           # File upload/download handling
│   └── static.py          # Static file serving
├── middleware/            # Production-ready middleware stack
│   ├── auth.py           # Authentication middleware
│   ├── cors.py           # CORS with flexible configuration
│   ├── csrf.py           # CSRF protection
│   ├── security.py       # Security headers (HSTS, CSP, frame protection)
│   ├── rate_limit.py     # Rate limiting (memory/Redis backends)
│   ├── compression.py    # Gzip/Brotli compression
│   ├── logging.py        # Structured request logging
│   └── request_id.py     # Request correlation IDs
├── auth/                 # Authentication system
│   ├── jwt.py           # JWT token handling
│   ├── password.py      # Password hashing (bcrypt)
│   ├── config.py        # Auth configuration
│   └── dependencies.py  # Auth dependency injection
├── db/                  # Database integration
│   └── migrations.py    # Alembic integration with async support
├── sessions/            # Session management
│   ├── manager.py       # Session lifecycle management
│   ├── store.py         # Storage backends (cookie, Redis, database)
│   └── middleware.py    # Session middleware
├── background.py        # Background task processing (BackgroundTasks, TaskQueue)
├── websockets.py        # WebSocket support with connection management
├── performance.py       # Performance monitoring and profiling decorators
├── testing/            # Testing framework
│   ├── client.py       # Async TestClient implementation
│   ├── auth.py         # Authentication testing helpers  
│   ├── context.py      # Context testing utilities
│   └── fixtures.py     # Common test fixtures
└── cli.py             # Command-line interface

tests/                    # Comprehensive test suite
├── unit/               # Unit tests (fast, isolated)
├── performance/        # Performance benchmarks and regression tests
└── integration/        # End-to-end integration tests

docs/                    # Documentation
├── tutorial/           # Step-by-step user guides
├── api/               # Complete API reference
├── spec/              # Architecture and design specs
├── examples/          # Real-world usage examples
├── contributing/      # Contribution guidelines
├── internal/          # Internal development documentation
└── archive/           # Historical/deprecated docs

examples/               # Working example applications
├── 00-hello-world.py        # Minimal example
├── 01-basic-api.py          # Basic CRUD API
├── 02-auth-api.py           # API with authentication
├── 03-complete-api.py       # Full-featured application
├── 04-websocket-chat.py     # WebSocket example
├── 16-modern-dx.py          # Modern DX showcase
├── 17-one-liner-features.py # One-liner convenience methods
└── 18-seamless-integration.py # ZenithModel seamless integration

benchmarks/            # Performance benchmarking tools
scripts/                # Development scripts
└── run_performance_tests.py # Performance test runner
```

## Core Framework Components

### 1. Zero-Config Setup
```python
from zenith import Zenith

# Zero-config application - automatically detects environment and configures:
# - Database (SQLite for dev, requires DATABASE_URL for prod)
# - CORS (permissive for dev, secure for prod)
# - Security (dev key for dev, requires SECRET_KEY for prod)
# - Middleware (debug toolbar in dev, security headers in prod)
app = Zenith()

# One-liner convenience features
app.add_auth()           # JWT authentication + /auth/login endpoint
app.add_admin()          # Admin dashboard at /admin with health checks
app.add_api("My API")    # OpenAPI docs at /docs and /redoc

# All features chain together
app = (Zenith()
       .add_auth()
       .add_admin("/dashboard")
       .add_api("My API", "1.0.0", "API description"))
```

### 2. Enhanced Database Models
```python
from zenith.db import ZenithModel
from sqlmodel import Field

class User(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    name: str
    email: str
    active: bool = Field(default=True)

# Intuitive model operations - all seamlessly integrated with Zenith app
users = await User.all()                           # Get all users
user = await User.find(1)                         # Find by ID, returns None if not found
user = await User.find_or_404(1)                  # Find by ID, raises 404 if not found
user = await User.create(name="Alice", email="alice@example.com")  # Create and save

# Chainable queries
active_users = await User.where(active=True).order_by('-created_at').limit(10)
recent_posts = await Post.where(published=True).includes('author').all()

# No manual session management needed - ZenithModel automatically uses
# the request-scoped database session from Zenith app middleware!
```

### 3. Enhanced Dependency Injection
```python
from zenith.core import DB, Auth, Cache

# Clean dependency shortcuts instead of verbose Depends()
@app.get("/users")
async def get_users(db=DB):  # Instead of db: AsyncSession = Depends(get_session)
    users = await User.all()  # ZenithModel seamlessly uses the db session
    return {"users": [user.to_dict() for user in users]}

@app.get("/protected")
async def protected_route(user=Auth):  # Instead of user = Depends(get_current_user)
    return {"user_id": user.id}

# Enhanced Service injection
@app.get("/posts")
async def get_posts(posts_service: PostService = Inject()):
    return await posts_service.get_recent_posts()
```

### 4. Traditional Application Setup (Still Supported)
```python
# Explicit configuration for complex scenarios
app = Zenith(
    title="My API",
    version="1.0.0",
    debug=False,
    middleware=[
        SecurityHeadersMiddleware({"force_https": True}),
        CORSMiddleware({"allow_origins": ["https://mysite.com"]}),
        RateLimitMiddleware({"default_limits": ["100/minute"]})
    ]
)
```

### 5. Service System - Business Logic Organization
```python
from zenith import Service, Inject

class UserService(Service):
    """Business logic for user operations."""
    
    def __init__(self):
        self.db = get_database()  # Dependency injection
    
    async def create_user(self, data: UserCreate) -> User:
        # Business logic separated from web concerns
        user = User(**data.model_dump())
        await self.db.save(user)
        return user
    
    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.db.get_user_by_email(email)
        if user and verify_password(password, user.password_hash):
            return user
        return None

# Usage in route handlers
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    users: UserService = Inject()  # Automatic dependency injection
) -> User:
    return await users.create_user(user_data)
```

### 6. Type-Safe Routing with Validation
```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int
    created_at: datetime

# Automatic validation and serialization
@app.post("/users", response_model=User)
async def create_user(user: UserCreate) -> User:
    # user is automatically validated
    # return value is automatically serialized
    return User(id=1, **user.model_dump(), created_at=datetime.utcnow())
```

### 7. Authentication System
```python
from zenith.auth import Auth, JWTAuth, User

# JWT Authentication
@app.get("/protected")
async def protected_route(user: Auth = JWTAuth()) -> dict:
    return {"user_id": user.id, "message": "Access granted"}

# Custom authentication
@app.get("/admin")
async def admin_route(user: Auth = JWTAuth(required_role="admin")) -> dict:
    return {"message": "Admin access granted"}
```

### 8. Background Tasks
```python
from zenith.background import BackgroundTasks, TaskQueue

@app.post("/send-email")
async def send_email(
    email_data: EmailData,
    background: BackgroundTasks
) -> dict:
    # Task runs after response is sent
    background.add_task(send_email_async, email_data.to, email_data.subject)
    return {"status": "email queued"}

# Task queue for longer-running jobs
queue = TaskQueue()

@app.post("/process-data")
async def process_data(data: ProcessingData) -> dict:
    task_id = await queue.enqueue(heavy_processing_task, data.payload)
    return {"task_id": task_id, "status": "processing"}
```

### 9. WebSocket Support
```python
from zenith.websockets import WebSocket, WebSocketManager

manager = WebSocketManager()

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast_to_room(room_id, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, room_id)
```

### 10. Performance Monitoring
```python
from zenith.monitoring.performance import track_performance, cached, profiler

@track_performance(threshold_ms=100)  # Log slow operations
@cached(ttl=300)  # Cache for 5 minutes
async def expensive_operation(data: str) -> dict:
    # Automatically tracked and cached
    return await process_complex_data(data)

# Global profiler for performance monitoring
with profiler.time_function("database_query"):
    result = await db.execute(query)
```

## Production Features

### Middleware Stack
**Built-in production middleware with intelligent defaults:**

1. **Security Headers** - HSTS, CSP, X-Frame-Options, X-Content-Type-Options
2. **CORS** - Flexible origin, method, and header configuration  
3. **Rate Limiting** - Memory and Redis backends with custom limits per endpoint
4. **CSRF Protection** - Token-based with SameSite cookie support
5. **Compression** - Gzip and Brotli with configurable minimum sizes
6. **Request Logging** - Structured logs with correlation IDs
7. **Authentication** - JWT and custom auth provider support

### Monitoring & Observability
- **Health Checks**: `/health` (basic) and `/health/detailed` (comprehensive)
- **Metrics**: Prometheus-compatible `/metrics` endpoint
- **Performance Profiling**: Built-in decorators and monitoring
- **Request Tracing**: Correlation IDs for distributed tracing
- **Error Handling**: Structured error responses with proper HTTP status codes

### Database Integration
- **Async SQLAlchemy**: Full async/await support
- **Alembic Migrations**: Automatic async-compatible migration generation
- **Connection Pooling**: Optimized connection management
- **Transaction Support**: Service managers for transaction handling

## Development & Testing

### Testing Framework
```python
from zenith.testing import TestClient, TestService

# Endpoint testing
async with TestClient(app) as client:
    response = await client.post("/users", json={"name": "Alice", "email": "alice@example.com", "age": 25})
    assert response.status_code == 201
    user = response.json()
    assert user["name"] == "Alice"

# Service testing (business logic)
async with TestService(UserService) as users:
    user = await users.create_user(UserCreate(name="Bob", email="bob@example.com", age=30))
    assert user.name == "Bob"

# Authentication testing
from zenith.testing.auth import MockAuth

@app.get("/protected")
async def protected(user: Auth = JWTAuth()):
    return {"user_id": user.id}

# Test with mock authentication
async with TestClient(app) as client:
    with MockAuth(user_id=123):
        response = await client.get("/protected")
        assert response.json()["user_id"] == 123
```

### Performance Testing
Comprehensive performance test suite covering:
- **Basic endpoint performance** - Simple and JSON endpoints
- **Middleware overhead** - Individual and stack performance impact
- **Memory efficiency** - Memory usage during request processing
- **Concurrency** - Performance under concurrent load
- **Background tasks** - Async task processing performance
- **WebSocket performance** - Real-time communication benchmarks

### CLI Tools
```bash
# Project creation and setup
zen new my-app                 # Create new project with secure defaults
zen keygen                     # Generate secure SECRET_KEY

# Development server
zen dev                        # Start development server with hot reload
zen serve                      # Start production server

# Performance testing
python scripts/run_performance_tests.py        # Basic performance tests
python scripts/run_performance_tests.py --slow # Include load tests
python benchmarks/simple_bench.py      # Quick benchmark
```

## Performance Characteristics

### Benchmarks (September 2025)
- **Simple endpoints**: 9,557 req/s (bare framework)
- **JSON endpoints**: 9,602 req/s (bare framework)  
- **With middleware**: 6,694 req/s (30.0% overhead, 70.0% retained performance)
- **Memory efficiency**: <100MB for 1000 requests
- **Startup time**: <100ms
- **JSON serialization**: 25% faster with orjson/msgspec
- **Background tasks**: 20-30% faster with TaskGroups

### Performance Features
- **Python 3.13 optimizations** - Free-threaded Python, JIT compiler, eager tasks
- **Zero-copy operations** - Memory-efficient buffer handling
- **Binary serialization** - 3-10x faster than JSON for internal APIs
- **Slotted classes** - 40% memory reduction for high-volume objects
- **Weak reference caching** - Automatic memory management
- **Precompiled regex** - 10-50x faster pattern matching
- **Vectorized operations** - 5-20x faster bulk data processing
- **Intelligent prefetching** - 50-70% latency reduction
- **Optimized routing** - O(1) exact matches, compiled matchers
- **Connection pooling** - 80% overhead reduction
- **Minimal middleware overhead** - each middleware <5% impact
- **Async throughout** - full async/await with TaskGroups

## API Stability & Versioning

### Current Status
- **Core APIs**: Stable, minor changes possible
- **Middleware**: Stable configuration patterns
- **Testing**: Stable API, expanding utilities
- **Performance**: Stable monitoring API
- **CLI**: Expanding command set

### Stability Guarantees
- **Breaking changes**: Documented in MIGRATION.md
- **Deprecation policy**: 2-version deprecation cycle
- **Semantic versioning**: Major.Minor.Patch
- **LTS releases**: Planned for v1.x series

## Common Patterns & Best Practices

### Project Organization
```
your-zenith-app/
├── main.py                  # Application entry point
├── contexts/               # Business logic contexts
│   ├── __init__.py
│   ├── users.py           # UserService, UserAuth, etc.
│   └── orders.py          # OrderService, PaymentService, etc.
├── models/                # Pydantic models
│   ├── __init__.py
│   ├── users.py          # User, UserCreate, UserUpdate
│   └── orders.py         # Order, OrderCreate, OrderStatus
├── middleware/           # Custom middleware
├── migrations/          # Database migrations
├── tests/              # Test suite
│   ├── test_users.py
│   └── test_orders.py
├── config.py           # Application configuration
└── requirements.txt    # Dependencies
```

### Error Handling
```python
from zenith.exceptions import ZenithException, HTTPException

class UserNotFoundError(ZenithException):
    """Raised when user is not found."""
    status_code = 404
    detail = "User not found"

@app.get("/users/{user_id}")
async def get_user(user_id: int, users: UserService = Inject()) -> User:
    user = await users.get_by_id(user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    return user
```

### Configuration Management
```python
from zenith.config import Config
import os

config = Config(
    database_url=os.getenv("DATABASE_URL", "sqlite:///app.db"),
    redis_url=os.getenv("REDIS_URL"),
    secret_key=os.getenv("SECRET_KEY"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
    cors_origins=os.getenv("CORS_ORIGINS", "*").split(",")
)

app = Zenith(config=config)
```

## Migration from Other Frameworks

### Migration Guide
- **Routes**: Minimal changes, same decorator patterns
- **Dependencies**: Replace `Depends()` with `Inject()` for business logic
- **Middleware**: Enhanced built-in middleware, less configuration needed
- **Testing**: More comprehensive testing utilities
- **Performance**: Immediate performance improvements

### Architecture Benefits
- **Async support**: Full async/await throughout
- **Type safety**: Automatic request/response validation
- **Architecture**: Service system for better organization
- **Production features**: Built-in middleware, monitoring, health checks

## Development Status & Roadmap

### Completed
- ✅ Core framework architecture
- ✅ Service system for business logic  
- ✅ Type-safe routing and dependency injection
- ✅ Production-ready middleware stack
- ✅ JWT authentication system
- ✅ Background task processing with TaskGroups
- ✅ WebSocket support with connection management
- ✅ Database integration with async SQLAlchemy
- ✅ Session management system
- ✅ Comprehensive testing framework
- ✅ Performance monitoring and profiling
- ✅ Health checks and metrics endpoints
- ✅ CLI development tools
- ✅ Complete test coverage (328/332 tests, 4 skipped)
- ✅ Performance benchmarking (9,600+ req/s with optimizations)
- ✅ Python 3.12 optimizations (generics, pattern matching)
- ✅ Memory leak prevention (bounded caches, cleanup tasks)
- ✅ Modern type hints (388 modernized)

### Stabilizing for v1.0
- 🔄 API consistency review
- 🔄 Documentation completeness
- 🔄 Plugin architecture design
- 🔄 Enhanced CLI features
- 🔄 Production deployment guides

### Future Features (v1.x+)
- 📋 GraphQL integration
- 📋 Advanced caching strategies
- 📋 Distributed tracing
- 📋 Admin interface
- 📋 Plugin ecosystem

## Troubleshooting & Common Issues

### Import Errors
- Ensure Python 3.11+ is used
- Install with `pip install zenithweb`
- Check virtual environment activation

### Performance Issues
- Run performance tests: `python scripts/run_performance_tests.py`
- Check middleware configuration  
- Profile with `@track_performance()` decorator
- Monitor `/metrics` endpoint
- **Reference:** Complete optimization guide at `docs/internal/PERFORMANCE_OPTIMIZATIONS.md`

### Database Issues
- Verify async database URL format
- Test connection with health checks: `/health/detailed`

### Authentication Problems
- Verify JWT secret key configuration
- Check token expiration and format
- Use `/health` endpoint to verify auth middleware

---

## For AI Assistants: Key Context

**When helping with Zenith development:**

1. **Architecture**: Use Service classes for business logic, keep routes thin
2. **Type Safety**: Always use type hints, Pydantic models for validation
3. **Testing**: Include both endpoint tests (TestClient) and business logic tests (TestService)
4. **Performance**: Consider performance impact, use profiling decorators, follow optimization patterns in `docs/internal/PERFORMANCE_OPTIMIZATIONS.md`
5. **Standards**: Follow existing patterns in codebase, maintain consistency
6. **Documentation**: Update docs for any API changes or new features

**Framework Strengths to Leverage:**
- Service system for clean architecture
- Built-in production features
- Comprehensive testing utilities
- Performance monitoring capabilities
- Type-safe dependency injection

**Current Focus Areas:**
- API stabilization for v1.0 release
- Performance optimization and benchmarking
- Documentation enhancement
- Developer experience improvements

*Updated September 2025 - Reflects current production status with full Pydantic v2 compatibility and modern Service-based architecture*