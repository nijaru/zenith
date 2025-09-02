# Zenith Framework

[![PyPI version](https://badge.fury.io/py/zenith-framework.svg)](https://badge.fury.io/py/zenith-framework)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/nijaru/zenith/workflows/Test%20Suite/badge.svg)](https://github.com/nijaru/zenith/actions)
[![Documentation](https://img.shields.io/badge/docs-passing-brightgreen.svg)](https://nijaru.github.io/zenith/)

A modern Python API framework that prioritizes clean architecture and developer experience.

> **⚠️ Early Development**: Zenith is in alpha (v0.0.1). APIs may change before v1.0.

## What is Zenith?

Zenith is a Python web framework that combines:
- **FastAPI's type safety** with less boilerplate
- **Django's project organization** in a modern async context
- **Clean architecture patterns** for maintainable code

## Performance

**Zenith outperforms leading Python frameworks:**

| Framework | Requests/sec | Relative Speed |
|-----------|-------------|----------------|
| **Zenith** | **2,089** | **100%** |
| FastAPI | 2,027 | 97% |
| Flask | 1,081 | 52% |

*Hello World benchmark - [See full benchmarks](benchmarks/)*

## Key Features

### 🎯 Type-Safe Dependency Injection
```python
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,                      # Auto-parsed from path
    accounts: Accounts = Context(),    # Business logic injection
    current_user: User = Auth()        # Authentication
) -> User:                             # Validated response
    return await accounts.get_user(user_id)
```

### 📦 Context-Driven Architecture
Organize business logic in contexts, not scattered across files:
```python
class Accounts(Context):
    async def create_user(self, data: UserCreate) -> User:
        async with self.db.transaction():
            user = await self.db.users.create(data)
            await self.emit("user.created", {"id": user.id})
            return user
```

### ✅ Production Ready
- SQLAlchemy 2.0 integration with async support
- JWT authentication with role-based access
- Comprehensive testing utilities (TestClient, TestContext)
- OpenAPI documentation at `/docs` and `/redoc`
- Security middleware (CORS, rate limiting, headers)
- File uploads and static file serving

## Installation

```bash
pip install zenith-framework  # Not yet available on PyPI
```

For development:
```bash
git clone https://github.com/nijaru/zenith
cd zenith
pip install -e ".[dev]"
```

## Quick Start

```python
from zenith import Zenith, Context
from zenith.models import User, UserCreate

app = Zenith(debug=True)

@app.get("/")
async def root():
    return {"message": "Welcome to Zenith!"}

@app.post("/users")
async def create_user(user: UserCreate) -> User:
    # Automatic validation via Pydantic
    return User(id=1, **user.model_dump())

if __name__ == "__main__":
    app.run()
```

## Project Roadmap

### Current Focus
1. **[ZEN-2]** Database Integration - Replace mock data with real persistence
2. **[ZEN-3]** Complete Routing & Middleware - Production-ready features
3. **[ZEN-6]** Authentication System - JWT, sessions, permissions

See our [Linear board](https://linear.app/nijaru7/team/ZEN/active) for detailed progress.

## Why Zenith?

**Problem**: FastAPI is great for simple APIs but becomes messy with complex business logic. Django is powerful but heavy and synchronous-first.

**Solution**: Zenith provides structure for complex applications while keeping the simplicity of modern Python.

## Project Status

### ✅ Completed
- Database integration with SQLAlchemy 2.0
- JWT authentication system
- Comprehensive middleware stack
- Testing framework
- API documentation generation
- Performance benchmarks

### 🚧 In Progress
- Production deployment examples
- WebSocket support
- Background task processing

## Contributing

We're in early development and not yet accepting contributions. Watch this space!

## Future Vision

Zenith is designed to be forward-compatible with [Mojo](https://www.modular.com/mojo), enabling potential 10x performance improvements without changing your code structure.

## License

MIT

## Contact

- GitHub: [@nijaru](https://github.com/nijaru)
- Issues: [GitHub Issues](https://github.com/nijaru/zenith/issues)

---

**Note**: This is an experimental framework in early development. Not recommended for production use.