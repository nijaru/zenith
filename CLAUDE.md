# Zenith - AI Assistant Context

*Framework-specific context for the Zenith Python web framework*

## Release Strategy

**Dual Release Approach**: PyPI (primary) + GitHub (secondary)

### PyPI Release
```bash
uv build
twine upload dist/zenithweb-{version}*  # Use twine, not uv publish
```

### GitHub Release
```bash
gh release create v{version} --title "v{version}: Brief Description" \
  --notes "## What's New..."
```

**Decision Matrix:**
- Major/minor (0.x.0, x.0.0): Both PyPI + GitHub
- Critical patches: Both
- Regular patches: PyPI required, GitHub optional

**Pre-Release Checklist:**
- `uv run ruff check .` (linting - must be 0 errors)
- `uv format --check` (formatting - must pass)
- `uv run pip-audit` (security scan)
- `uv run pytest` (all tests passing)
- Examples work: `uv run python examples/00-hello-world.py`
- Clean temp files: `ZENITH_BUGS_*.md`, test outputs
- CHANGELOG.md updated

**CRITICAL**: Never release without explicit approval. "Prep release" = prepare only, STOP before publishing.

## Quick Facts
- **Status**: v0.0.6 - Production-ready framework
- **Performance**: 9,600+ req/s with middleware stack
- **Python**: 3.12-3.14 (TaskGroups, PEP 695 generics, pattern matching)
- **CLI**: `zen` command for development tools

## Code Quality Tools

**Run before every commit:**
```bash
# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv format

# Run tests
uv run pytest
```

**Run before releases:**
```bash
# Linting (must be 0 errors)
uv run ruff check .

# Formatting (must pass)
uv format --check

# Dead code detection
uvx vulture . --min-confidence 80

# Security audit
uv run pip-audit

# Type checking (when ty is stable - currently pre-alpha)
# uvx ty check .

# Full test suite
uv run pytest --cov=zenith
```

## Framework Philosophy

**Core Principle**: Service-based architecture - business logic in Service classes, thin route handlers

**Key Differentiators**:
- **Intuitive Models**: `User.where(active=True).limit(10)` vs raw SQLAlchemy
- **One-liner Features**: `app.add_auth()`, `app.add_admin()`, `app.add_api()`
- **Zero-Config**: `app = Zenith()` auto-detects environment
- **Seamless DB Integration**: ZenithModel uses request-scoped sessions automatically
- **Enhanced DI**: `Session`, `Auth` vs verbose `Depends()` patterns

## Project Structure

**Framework layout:**
```
zenith/
├── core/          # Application, Service, routing, DI container
├── middleware/    # CORS, CSRF, security, rate limiting, compression
├── auth/          # JWT, password hashing, dependencies
├── db/            # Migrations, async SQLAlchemy
├── testing/       # TestClient, auth helpers, fixtures
└── cli.py         # zen command

tests/             # unit/, performance/, integration/
docs/              # tutorial/, api/, spec/, examples/
examples/          # Working applications (00-18)
```

## Core API Patterns

### Zero-Config Setup
```python
app = Zenith()  # Auto-detects environment (dev/prod)
app.add_auth()  # JWT + /auth/login (demo/demo in dev)
app.add_admin() # Admin dashboard at /admin
app.add_api("My API")  # OpenAPI docs at /docs

# Chainable
app = Zenith().add_auth().add_admin().add_api("My API")
```

### ZenithModel (Enhanced Database Models)
```python
from zenith.db import ZenithModel

class User(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    name: str
    active: bool = True

# Intuitive queries - automatic session management
users = await User.all()
user = await User.find(1)  # None if not found
user = await User.find_or_404(1)  # Raises 404
user = await User.create(name="Alice")

# Chainable
active_users = await User.where(active=True).order_by('-created_at').limit(10)
```

### Service System (Business Logic)
```python
from zenith import Service, Inject

class UserService(Service):
    async def create_user(self, data: UserCreate) -> User:
        # Business logic here
        return await User.create(**data.model_dump())

# Route handler
@app.post("/users")
async def create_user(
    user_data: UserCreate,
    users: UserService = Inject()  # Auto-injected
):
    return await users.create_user(user_data)
```

### Enhanced DI Shortcuts
```python
@app.get("/users")
async def get_users(session: AsyncSession = Session):  # vs Depends()
    return await User.all()

@app.get("/protected")
async def protected(user=Auth):  # vs Depends(get_current_user)
    return {"user_id": user.id}
```

## Built-in Features

**Middleware**: Security headers, CORS, rate limiting, CSRF, compression, logging
**Monitoring**: `/health`, `/health/detailed`, `/metrics` (Prometheus)
**Database**: Async SQLAlchemy, Alembic migrations, connection pooling
**Testing**: `TestClient`, `TestService`, `MockAuth` helpers

### CLI Tools
```bash
zen new my-app      # Create project
zen keygen          # Generate SECRET_KEY
zen dev             # Development server with hot reload
zen serve           # Production server

# Performance testing
python scripts/run_performance_tests.py
```

## Performance

**Benchmarks (September 2025)**:
- 9,600+ req/s with middleware (6,694 req/s baseline)
- <100MB memory for 1000 requests
- <100ms startup time

**Optimizations**:
- Python 3.13 (free-threaded, JIT)
- TaskGroups for async operations
- Connection pooling (80% overhead reduction)
- Slotted classes (40% memory reduction)
- See `docs/internal/PERFORMANCE_OPTIMIZATIONS.md`

## Testing Patterns

```python
from zenith.testing import TestClient, TestService, MockAuth

# Endpoint testing
async with TestClient(app) as client:
    response = await client.post("/users", json={"name": "Alice"})
    assert response.status_code == 201

# Service testing
async with TestService(UserService) as users:
    user = await users.create_user(UserCreate(name="Bob"))

# Mock auth
with MockAuth(user_id=123):
    response = await client.get("/protected")
```

## Recommended App Structure

```
your-app/
├── main.py           # Entry point
├── contexts/         # Service classes (UserService, OrderService)
├── models/           # Pydantic models (User, UserCreate, UserUpdate)
├── migrations/       # Alembic migrations
└── tests/            # Test suite
```

## Key Development Notes

**Architecture**: Service classes contain business logic, routes stay thin
**Testing**: Use TestClient for endpoints, TestService for business logic
**Performance**: Profile with `@track_performance()`, monitor `/metrics`
**Changes**: Update docs/, examples/, tests/, CHANGELOG.md when modifying API

**Current Focus**: API stabilization for v1.0, performance optimization, documentation

*Updated October 2025 - v0.0.6 with Python 3.14 support and code quality improvements*