# Zenith Framework

[![PyPI version](https://badge.fury.io/py/zenith-framework.svg)](https://badge.fury.io/py/zenith-framework)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/nijaru/zenith/workflows/Test%20Suite/badge.svg)](https://github.com/nijaru/zenith/actions)
[![Documentation](https://img.shields.io/badge/docs-passing-brightgreen.svg)](https://nijaru.github.io/zenith/)

A modern Python API framework that prioritizes clean architecture, exceptional performance, and developer experience.

> **🚀 v0.1.4 Release**: Zenith delivers production-ready performance with comprehensive optimizations and stable APIs.

## What is Zenith?

Zenith is a modern Python API framework designed for building production-ready applications with clean architecture:

- **Type-safe by design** - Full Pydantic integration with automatic validation
- **Clean architecture** - Business logic organized in Context classes, separate from web concerns
- **Zero-configuration defaults** - Production middleware, monitoring, and security built-in
- **Performance focused** - 9,900+ req/s with async-first architecture and Python optimizations
- **Full-stack ready** - Serve APIs alongside SPAs with comprehensive middleware stack

## Quick Start

```bash
pip install zenith-web
```

```python
from zenith import Zenith, Context, Service
from pydantic import BaseModel

app = Zenith()

@app.get("/")
async def hello():
    return {"message": "Hello, Zenith!"}

# Type-safe request/response models
class UserCreate(BaseModel):
    name: str
    email: str

class User(BaseModel):
    id: int
    name: str
    email: str

# Business logic in Service classes
class UserService(Service):
    def __init__(self):
        self.users = {}
        self.next_id = 1
    
    async def create_user(self, data: UserCreate) -> User:
        user = User(id=self.next_id, name=data.name, email=data.email)
        self.users[self.next_id] = user
        self.next_id += 1
        return user
    
    async def get_user(self, user_id: int) -> User | None:
        return self.users.get(user_id)

# Clean dependency injection
@app.post("/users", response_model=User)
async def create_user(user_data: UserCreate, users: UserService = Context()):
    return await users.create_user(user_data)

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int, users: UserService = Context()):
    user = await users.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

Run with:
```bash
uvicorn main:app --reload
```

## Core Features

### 🚀 **Type-Safe Development**
- Automatic request/response validation with Pydantic
- OpenAPI 3.0 documentation generation at `/docs` and `/redoc`
- IDE autocompletion and type checking
- Zero-configuration setup

### 🏗️ **Clean Architecture**
- Business logic organized in Service classes with `Context()` injection
- Separation of web concerns from business logic
- Type-safe dependency injection without boilerplate
- Built-in support for complex application architectures

### 🔐 **Production-Ready Security**
- JWT authentication with `JWTAuth()`
- CORS, CSRF, security headers middleware
- Rate limiting with memory and Redis backends
- Automatic request correlation IDs

### ⚡ **High Performance**
- **9,900+ req/s** on modern hardware
- **24.8% middleware retention** with full production stack
- Async-first architecture with Python 3.12+ optimizations
- Comprehensive performance monitoring built-in

### 🛠️ **Developer Experience**
- Interactive CLI with code generation: `zen generate api users`
- Built-in testing framework with `TestClient`
- Hot reload development server
- Comprehensive error handling and debugging

### 🔄 **Background Processing**
- Simple background tasks with `BackgroundTasks`
- Production job queue with Redis backend
- Cron-style scheduling: `@schedule(cron="0 9 * * *")`
- Automatic retry with exponential backoff

### 📊 **Monitoring & Observability**
- Health checks: `/health` and `/health/detailed`
- Prometheus metrics: `/metrics`
- Performance profiling decorators
- Request/response logging with structured output

### 🌐 **Full-Stack Support**
- Serve SPAs (React, Vue, SolidJS) with `app.spa("dist")`
- WebSocket support with connection management
- Static file serving with caching
- Database integration with async SQLAlchemy

## Architecture

Zenith follows clean architecture principles:

```
your-app/
├── main.py           # Application entry point
├── contexts/         # Business logic (Service classes)
├── models/          # Data models (Pydantic)
├── routes/          # API endpoints (optional - can use decorators)
├── middleware/      # Custom middleware
├── migrations/      # Database migrations
└── tests/          # Test suite
```

## Performance

**Verified Benchmark Results (v0.1.4):**
- Simple endpoints: **9,897 req/s**
- JSON endpoints: **9,982 req/s**  
- With full middleware: **2,453 req/s** (24.8% retention)

Run your own benchmarks:
```bash
python run_performance_tests.py --quick
```

*Performance varies by hardware and application complexity. See [Performance Guide](docs/internal/PERFORMANCE_OPTIMIZATIONS.md) for optimization details.*

## Documentation

- **[Quick Start Guide](docs/tutorial/)** - Get up and running in 5 minutes
- **[API Reference](docs/reference/)** - Complete API documentation  
- **[Architecture Guide](docs/reference/spec/ARCHITECTURE.md)** - Framework design patterns
- **[Examples](examples/)** - Real-world usage examples
- **[Performance Guide](docs/internal/PERFORMANCE_OPTIMIZATIONS.md)** - Optimization details
- **[Contributing](docs/guides/contributing/DEVELOPER.md)** - Development guidelines

## Examples

Complete working examples in the [examples/](examples/) directory:

- [Hello World](examples/00-hello-world.py) - Basic setup
- [Context System](examples/03-context-system.py) - Business logic organization
- [Authentication](examples/02-auth-api.py) - JWT auth implementation
- [Background Jobs](examples/05-background-tasks.py) - Task processing
- [WebSocket Chat](examples/07-websocket-chat.py) - Real-time communication
- [Full Production API](examples/10-complete-production-api/) - Complete example

## CLI Tools

```bash
# Create new project
zen new my-api

# Development server with hot reload  
zen server --reload

# Interactive shell with app context
zen shell

# Code generation
zen generate api users "User UserCreate UserUpdate"
zen generate model Product "name:str price:float"

# Database migrations
zen db migrate "add users table"
zen db upgrade

# Testing
zen test --coverage
```

## Installation

```bash
# Basic installation
pip install zenith-web

# With production dependencies
pip install "zenith-web[production]"

# With development tools
pip install "zenith-web[dev]"
```

## Production Deployment

### Docker
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install "zenith-web[production]"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
```python
from zenith import Zenith
from zenith.config import Config

app = Zenith(
    config=Config(
        database_url=os.getenv("DATABASE_URL"),
        redis_url=os.getenv("REDIS_URL"), 
        secret_key=os.getenv("SECRET_KEY"),
        debug=os.getenv("DEBUG", "false").lower() == "true"
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

**Current Version**: v0.1.4 (stable release)  
**Python Support**: 3.12+  
**Test Suite**: 100% passing (309/309 tests)  
**Performance**: Production-ready with 9,900+ req/s capability  
**Architecture**: Clean separation with Context system and dependency injection  

Zenith is production-ready with comprehensive middleware, performance optimizations, and clean architecture patterns for modern Python applications.

## License

MIT License. See [LICENSE](LICENSE) for details.