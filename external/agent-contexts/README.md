# Zenith Framework v0.3.1 - Agent Context

## Framework Status
- **Version**: 0.3.0 (Rails-like DX release)
- **Test Coverage**: 100% (770+ tests passing)
- **Performance**: 9,600+ req/s
- **Python**: 3.12+ required

## Core Architecture

### 1. Zero-Config Application
```python
from zenith import Zenith

# Automatic environment detection and configuration
app = Zenith()  # Ready for development

# One-liner features
app.add_auth()    # JWT authentication
app.add_admin()   # Admin dashboard
app.add_api()     # OpenAPI docs
```

### 2. Rails-like ActiveRecord Models
```python
from zenith.db import ZenithModel

class User(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    name: str
    email: str

# Rails-style operations
users = await User.all()
user = await User.find_or_404(1)
active = await User.where(active=True).limit(10)
```

### 3. Clean Dependency Injection
```python
from zenith.core import DB, Auth, Cache

@app.get("/users")
async def get_users(db=DB):  # Clean DI
    return await User.all()

@app.get("/me")
async def get_me(user=Auth):  # Auth DI
    return {"id": user.id}
```

## Key Components

### Database (`zenith/db/`)
- **Async SQLAlchemy 2.0**: Full async/await support
- **ZenithModel**: Rails-like ActiveRecord pattern
- **Session Management**: Request-scoped automatic sessions
- **Migrations**: Alembic integration

### Authentication (`zenith/auth/`)
- **JWT**: Token-based authentication
- **Password**: Bcrypt hashing
- **Middleware**: Automatic user injection
- **Testing**: MockAuth for easy testing

### Middleware Stack (`zenith/middleware/`)
- **Security**: Headers, CSRF, XSS protection
- **CORS**: Flexible configuration
- **Rate Limiting**: Memory/Redis backends
- **Compression**: Gzip/Brotli
- **Logging**: Structured with correlation IDs

### Testing (`zenith/testing/`)
- **TestClient**: Async HTTP testing
- **SyncTestClient**: Synchronous testing
- **MockAuth**: Authentication mocking
- **Fixtures**: Common test helpers

### CLI (`zenith/cli.py`)
- `zen dev`: Development server with reload
- `zen test`: Run test suite
- `zen db`: Database migrations
- `zen keygen`: Generate secret keys

## File Organization

```
zenith/
├── core/              # Framework kernel
│   ├── application.py # Main Zenith class
│   ├── routing/       # Router system
│   ├── config.py      # Configuration
│   └── dependencies.py # DI system
├── db/                # Database layer
│   ├── __init__.py    # Database class
│   ├── models.py      # ZenithModel
│   └── migrations.py  # Alembic
├── auth/              # Authentication
├── middleware/        # Middleware stack
├── sessions/          # Session management
├── testing/           # Test utilities
└── cli.py             # CLI commands

tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
└── performance/       # Benchmarks

examples/
├── 00-hello-world.py  # Minimal example
├── 16-rails-like-dx.py # Rails patterns
└── 17-one-liner-features.py # Conveniences
```

## Recent v0.3.1 Changes

### Critical Fixes
1. **Database Metadata**: Fixed SQLModel table creation
2. **Environment Detection**: Proper dev/prod defaults
3. **File Dependencies**: Fixed async/sync mismatch
4. **Auth Endpoints**: Parameter compatibility
5. **Middleware Access**: Proper attribute handling

### New Features
1. **Zero-Config Setup**: Auto-detects environment
2. **Rails-like Models**: ActiveRecord patterns
3. **One-liner Features**: add_auth(), add_admin()
4. **Clean DI**: DB, Auth, Cache shortcuts
5. **Seamless Integration**: Request-scoped sessions

## Testing Guidelines

### Running Tests
```bash
# All tests
uv run pytest

# Specific categories
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/performance/

# With coverage
uv run pytest --cov=zenith
```

### Key Test Files
- `test_app.py`: Core application tests
- `test_testing_mode.py`: Testing mode verification
- `test_config.py`: Configuration management
- `test_auth.py`: Authentication system
- `test_db.py`: Database operations

## Performance Characteristics
- **Startup**: <100ms
- **Simple Routes**: 9,600+ req/s
- **With Middleware**: 6,700+ req/s (70% retention)
- **Memory**: <100MB for 1000 requests
- **JSON**: 25% faster with orjson

## Development Workflow

### Setup
```bash
# Clone and install
git clone https://github.com/nijaru/zenith
cd zenith
uv sync

# Run tests
uv run pytest

# Start dev server
uv run zen dev
```

### Making Changes
1. Create feature branch
2. Write tests first
3. Implement feature
4. Run tests: `uv run pytest`
5. Check types: `uv run pyright`
6. Format: `uv run ruff format`

### Release Process
1. Update version in `pyproject.toml`
2. Run full test suite
3. Build: `uv build`
4. Upload: `twine upload dist/*`
5. Create GitHub release

## Common Patterns

### Service Architecture
```python
from zenith import Service, Inject

class UserService(Service):
    async def create_user(self, data):
        return await User.create(**data)

@app.post("/users")
async def create(
    data: UserCreate,
    service: UserService = Inject()
):
    return await service.create_user(data)
```

### Error Handling
```python
from zenith.exceptions import HTTPException

@app.get("/users/{id}")
async def get_user(id: int):
    user = await User.find(id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

### Background Tasks
```python
from zenith.background import BackgroundTasks

@app.post("/email")
async def send_email(
    data: EmailData,
    tasks: BackgroundTasks
):
    tasks.add_task(send_email_async, data)
    return {"status": "queued"}
```

## Troubleshooting

### Import Errors
- Ensure Python 3.12+
- Check virtual environment
- Verify installation: `pip show zenith-web`

### Database Issues
- Check DATABASE_URL format
- Run migrations: `zen db upgrade`
- Verify with: `/health/detailed`

### Test Failures
- Clear cache: `rm -rf .pytest_cache`
- Check environment: `echo $ZENITH_ENV`
- Isolate test: `pytest -xvs tests/path/to/test.py`

## Contact & Support
- **GitHub**: https://github.com/nijaru/zenith
- **PyPI**: https://pypi.org/project/zenith-web/
- **Issues**: https://github.com/nijaru/zenith/issues

---
*Updated: September 2025 - v0.3.1 Release*