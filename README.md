# Zenith Framework

[![PyPI version](https://badge.fury.io/py/zenithweb.svg)](https://badge.fury.io/py/zenithweb)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/nijaru/zenith/workflows/Test%20Suite/badge.svg)](https://github.com/nijaru/zenith/actions)
[![Documentation](https://img.shields.io/badge/docs-passing-brightgreen.svg)](https://nijaru.github.io/zenith/)

A modern Python web framework with **intuitive developer experience** and exceptional performance.

> **🎯 Modern DX**: Zero-config setup, database models with chainable queries, one-liner features, and clean architecture patterns - making Python web development incredibly productive.

## What is Zenith?

Zenith brings together **exceptional productivity**, **outstanding performance**, and **full type safety**:

- **🚀 Zero-config setup** - `app = Zenith()` just works with intelligent defaults
- **🏗️ Intuitive models** - `User.where(active=True).order_by('-created_at').limit(10)`
- **⚡ One-liner features** - `app.add_auth()`, `app.add_admin()`, `app.add_api()`
- **🎯 Enhanced DX** - No session management, ZenithModel handles it automatically
- **🏎️ Exceptional performance** - 9,600+ req/s with full async support
- **🛡️ Production-ready** - Security, monitoring, and middleware built-in

## 🚀 Zero-Config Quick Start

```bash
pip install zenithweb
```

```python
from zenith import Zenith
from zenith import Session  # Database session dependency
from zenith.db import ZenithModel  # Modern database models
from sqlmodel import Field
from pydantic import BaseModel
from typing import Optional

# 🎯 Zero-config setup - just works!
app = Zenith()

# ⚡ Add features in one line each
app.add_auth()    # JWT authentication + /auth/login
app.add_admin()   # Admin dashboard at /admin
app.add_api("My API", "1.0.0")  # API docs at /docs

# 🏗️ Modern models with chainable query patterns
class User(ZenithModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
    active: bool = Field(default=True)

class UserCreate(BaseModel):
    name: str
    email: str
    active: bool = True

# 🎨 Clean routes with enhanced DX
@app.get("/")
async def home():
    return {"message": "Modern DX in Python!"}

@app.get("/users")
async def list_users():  # ✨ No session management needed!
    # Clean chaining: User.where().order_by().limit()
    users = await User.where(active=True).order_by('-id').limit(10).all()
    return {"users": [user.model_dump() for user in users]}

@app.post("/users")
async def create_user(user_data: UserCreate):
    # Clean API: User.create() - no session management!
    user = await User.create(**user_data.model_dump())
    return {"user": user.model_dump()}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Automatic 404 handling
    user = await User.find_or_404(user_id)
    return {"user": user.model_dump()}

# 🏃‍♂️ Run it
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Run with:
```bash
uvicorn main:app --reload
```

## 🎯 Modern DX Features

### 🚀 **Zero-Config Setup (for Development)**
```python
app = Zenith()  # Just works! No complex configuration needed
```
- **Intelligent defaults** - Development uses SQLite, auto-generated dev keys
- **Production ready** - Set `DATABASE_URL` and `SECRET_KEY` env vars for production
- **Automatic middleware** - Security, CORS, logging configured automatically
- **Environment-aware** - Uses `ZENITH_ENV` or intelligent detection

### 🏗️ **Intuitive Database Models**
```python
# Intuitive database operations - seamless chaining!
users = await User.where(active=True).order_by('-created_at').limit(10).all()
user = await User.find_or_404(123)  # Automatic 404 handling
user = await User.create(name="Alice", email="alice@example.com")
```
- **ZenithModel** - Modern ORM with chainable queries
- **Automatic sessions** - No manual database session management
- **Type-safe queries** - Full async support with SQLModel integration

### ⚡ **One-Liner Features**
```python
app.add_auth()     # JWT authentication + /auth/login endpoint
app.add_admin()    # Admin dashboard at /admin with health checks
app.add_api()      # API documentation at /docs and /redoc
```
- **Instant features** - Complex functionality in single lines
- **Production-ready** - Each feature includes monitoring and security
- **Configurable** - Sensible defaults with full customization options

### 🎯 **Clean Dependency Injection**
```python
@app.get("/users")
async def get_users(session: AsyncSession = Session):
    # Simple database session injection
    users = await User.all()  # ZenithModel uses the session automatically
    return users
```
- **Simple patterns** - `Session` for database, `Auth` for current user
- **Service injection** - `Inject(ServiceClass)` for business logic
- **Type-safe** - Full IDE support and autocompletion

### 🏎️ **Exceptional Performance**
- **9,600+ req/s** - Exceptional performance with modern features
- **No performance penalty** - Zero overhead from convenience features
- **Async-first** - Full async/await with Python 3.12+ optimizations
- **Production tested** - 70% middleware retention with full feature stack

### 🛡️ **Production-Ready**
- **Security by default** - CSRF, CORS, security headers automatic
- **Built-in monitoring** - `/health`, `/metrics`, request tracing
- **Error handling** - Structured errors with proper HTTP status codes
- **Testing framework** - Comprehensive testing utilities included

### 🌐 **Full-Stack Support**
- Serve SPAs (React, Vue, SolidJS) with `app.spa("dist")`
- WebSocket support with connection management
- Static file serving with caching
- Database integration with async SQLAlchemy

## 📁 Project Structure

Clean organization with zero configuration:

```
your-app/
├── main.py         # app = Zenith() + routes
├── models.py       # ZenithModel classes
├── services.py     # Business logic (optional)
├── migrations/     # Database migrations (auto-generated)
└── tests/          # Testing with built-in TestClient
```

**Or traditional clean architecture:**
```
your-app/
├── main.py         # Application entry point
├── models/         # ZenithModel classes
├── services/       # Service classes with @Service decorator
├── routes/         # Route modules (optional)
├── middleware/     # Custom middleware
└── tests/          # Comprehensive test suite
```

## Performance

**Verified Benchmark Results:**
- Simple endpoints: **9,557 req/s**
- JSON endpoints: **9,602 req/s**
- With full middleware: **6,694 req/s** (70% retention)

*Tested on Apple M3 Max, Python 3.13, uvloop enabled*

Run your own benchmarks:
```bash
python scripts/run_performance_tests.py --quick
```

*Performance varies by hardware and application complexity.*

## Documentation

- **[Quick Start Guide](docs/tutorial/)** - Get up and running in 5 minutes
- **[API Reference](docs/reference/)** - Complete API documentation  
- **[Architecture Guide](docs/reference/spec/ARCHITECTURE.md)** - Framework design patterns
- **[Examples](examples/)** - Real-world usage examples
- **[Contributing](docs/guides/contributing/DEVELOPER.md)** - Development guidelines

## 📚 Examples

**🔥 Modern DX Examples:**
- **[Modern Developer Experience](examples/03-modern-developer-experience.py)** - Complete modern patterns showcase
- **[One-Liner Features](examples/04-one-liner-features.py)** - Convenience methods demonstration
- **[One-liner Features](examples/17-one-liner-features.py)** - `app.add_auth()`, `app.add_admin()`, `app.add_api()`
- **[Zero-config Setup](examples/18-seamless-integration.py)** - Automatic environment detection

**🚀 Complete Examples:**
- [Hello World](examples/00-hello-world.py) - Simple setup (`app = Zenith()`)
- [Basic API](examples/01-basic-routing.py) - Routing and validation
- [Authentication](examples/02-auth-api.py) - JWT authentication
- [WebSocket Chat](examples/07-websocket-chat.py) - Real-time communication
- [Background Jobs](examples/05-background-tasks.py) - Task processing
- [Security Middleware](examples/11-security-middleware.py) - Production security

## CLI Tools

```bash
# Create new project with secure defaults
zen new my-api

# Generate secure SECRET_KEY
zen keygen

# Development server with hot reload
zen dev

# Production server
zen serve --workers 4
```

## Installation

```bash
# Basic installation
pip install zenithweb

# With production dependencies
pip install "zenithweb[production]"

# With development tools
pip install "zenithweb[dev]"
```

## Production Deployment

### Docker
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install "zenithweb[production]"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
```python
from zenith import Zenith

app = Zenith()

# Environment-specific behavior:
# development (or dev): Enhanced error reporting, auto-generated secrets
# production (or prod): Optimized for deployment, requires SECRET_KEY
# test: Testing mode with rate limiting disabled
# staging: Production-like with enhanced monitoring

# Manual configuration if needed
from zenith.config import Config
app = Zenith(
    config=Config(
        database_url=os.getenv("DATABASE_URL"),
        redis_url=os.getenv("REDIS_URL"),
        secret_key=os.getenv("SECRET_KEY")
        # debug automatically set based on ZENITH_ENV
    )
)
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/guides/contributing/DEVELOPER.md).

```bash
git clone https://github.com/nijaru/zenith.git
cd zenith
pip install -e ".[dev]"
pytest  # Run tests
```

## Status

**Latest Version**: v0.0.3
**Python Support**: 3.12-3.14
**Test Suite**: 100% passing (862 tests)
**Performance**: Production-ready with 9,600+ req/s capability  
**Architecture**: Clean separation with Service system and simple dependency patterns  

Zenith is production-ready with comprehensive middleware, performance optimizations, and clean architecture patterns for modern Python applications.

## License

MIT License. See [LICENSE](LICENSE) for details.
