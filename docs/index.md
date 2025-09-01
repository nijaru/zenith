# Zenith Framework

> Modern Python web framework with clean architecture

Zenith combines the best of FastAPI's type safety, Rails' developer experience, and Phoenix's architectural patterns into a cohesive, productive Python web framework.

## Quick Start

```bash
pip install zenith-web
```

```python
from zenith import Zenith, Context

app = Zenith()

@app.get("/")
async def hello():
    return {"message": "Hello, Zenith!"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}
```

## Core Features

### 🚀 **FastAPI-Style API Development**
- Type-safe routing with automatic validation
- Dependency injection without boilerplate
- OpenAPI/Swagger documentation generation
- Async/await throughout

### 🏗️ **Context-Driven Architecture** 
- Organize business logic in Contexts (inspired by Phoenix)
- Clean separation of concerns
- Testable, mockable components
- Event-driven communication between contexts

### 🔒 **Built-in Security**
- JWT authentication with bcrypt password hashing
- CORS, CSRF, and security headers middleware
- Input validation and sanitization
- Rate limiting and request throttling

### 📁 **File Handling & Storage**
- Secure file uploads with validation
- Configurable storage backends
- Image processing and thumbnails
- Static file serving with caching

### 🏥 **Production-Ready Features**
- Health checks with liveness/readiness probes  
- Structured logging and metrics
- Database connection pooling
- Graceful shutdown handling

### 🧪 **Testing Excellence**
- Built-in test client with authentication
- Context testing utilities
- Database transaction rollback
- Comprehensive test coverage

## Architecture Overview

Zenith applications are structured around three core concepts:

```python
# 1. Application - The main entry point
app = Zenith()

# 2. Contexts - Business logic containers  
class UsersContext(Context):
    async def create_user(self, data): ...
    async def get_user(self, id): ...

# 3. Routes - HTTP endpoints with dependency injection
@app.post("/users")
async def create_user(user: UserCreate, users: UsersContext = Context()) -> User:
    return await users.create_user(user)
```

This architecture provides:
- **Clear boundaries** between HTTP layer and business logic
- **Testable components** that can be mocked and isolated
- **Type safety** with full IntelliSense and validation
- **Scalable structure** that grows with your application

## Getting Started

### Installation

```bash
# Install Zenith
pip install zenith-web

# Or with all optional dependencies
pip install "zenith-web[all]"
```

### Your First App

Create `main.py`:

```python
from zenith import Zenith

app = Zenith()

@app.get("/")
async def root():
    return {"message": "Welcome to Zenith!"}

@app.get("/health") 
async def health():
    return {"status": "healthy", "framework": "zenith"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

Run your app:

```bash
python main.py
# or 
uvicorn main:app --reload
```

Your API is now running at `http://localhost:8000`

- **API**: http://localhost:8000/
- **Health**: http://localhost:8000/health
- **Docs**: http://localhost:8000/docs (coming soon)

## Next Steps

- [**Tutorial**](tutorial/index.md) - Build a complete application step-by-step
- [**API Reference**](api/index.md) - Complete API documentation
- [**Examples**](examples/index.md) - Real-world application examples
- [**Deployment**](deployment/index.md) - Production deployment guides

## Why Zenith?

### vs FastAPI
- **Better Organization**: Context system prevents "god files" 
- **Less Boilerplate**: Simpler dependency injection
- **More Batteries**: File uploads, auth, security built-in

### vs Django
- **Modern Async**: Built for async/await from the ground up
- **Type Safety**: Full type hints and validation 
- **API First**: Designed for building APIs, not templated websites

### vs Flask
- **Type Safety**: Automatic request/response validation
- **Modern Features**: Built-in async, dependency injection, testing
- **Production Ready**: Security, health checks, metrics included

---

**Ready to get started?** Check out the [Tutorial →](tutorial/index.md)