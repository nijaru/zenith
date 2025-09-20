---
title: Introduction
description: Welcome to Zenith - A modern Python web framework
---

# Welcome to Zenith

**Zenith** is a modern Python web framework designed for building production-ready APIs with clean architecture and exceptional developer experience.

## What is Zenith?

Zenith combines the best ideas from modern web frameworks with Python's ecosystem to provide:

- **Clean Architecture** - Phoenix-inspired contexts separate business logic from web concerns
- **Type Safety** - Full type hints with Pydantic validation catch errors at development time  
- **Performance** - Built on Starlette with async-first design and modern Python 3.12+ features
- **Production Ready** - Built-in middleware for security, monitoring, and scalability

## Key Features

### 🏗️ **Context System**
Organize your business logic in contexts, keeping domain concerns separate from HTTP handling:

```python
class UserService(Service):
    async def create_user(self, data: UserCreate) -> User:
        # Business logic stays here, not in route handlers
        return await self.users.create(data)
```

### 🔒 **Type-Safe by Default**  
Leverage Python's type system for bulletproof APIs:

```python
@app.post("/users", response_model=User)
async def create_user(user: UserCreate) -> User:
    # Automatic validation and serialization
    return {"id": 1, "name": user.name}
```

### 🚀 **SQLModel Integration**
One model for everything - API, database, and documentation:

```python
class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(min_length=1)
    email: str = Field(regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

### ⚡ **Exceptional Performance**
- **9,557 req/s** for simple endpoints
- **9,602 req/s** for JSON responses
- **70% performance retained** with full middleware stack (6,694 req/s)
- Zero memory leaks with bounded caches and comprehensive optimizations

### 🛡️ **Production Features**
Built-in middleware for enterprise needs:
- Security headers (HSTS, CSP, X-Frame-Options)
- CORS with flexible configuration
- Rate limiting with Redis or memory backends
- Request logging with correlation IDs
- Health checks and Prometheus metrics

## Philosophy

Zenith is built on these core principles:

1. **Developer Experience First** - Tools should help, not hinder
2. **Type Safety Without Compromise** - Catch errors before they reach production  
3. **Clean Architecture** - Separate concerns for maintainable codebases
4. **Performance Matters** - Fast by default, optimized for Python 3.12+
5. **Production Ready** - Everything you need to ship confidently

## Who Should Use Zenith?

Zenith is great for:

- **APIs** - REST APIs, GraphQL backends, and microservices at any scale
- **Frontends** - Serve SPAs (React, Vue, Angular) and static sites seamlessly  
- **Full-Stack Applications** - Complete web applications with clean architecture
- **Production Systems** - Built for reliability, performance, and maintainability

## What Makes Zenith Different?

Unlike other Python frameworks, Zenith provides:

- **Context-Driven Architecture** - Inspired by Phoenix, Elixir's premier framework
- **Zero-Configuration Defaults** - Production middleware enabled out-of-the-box
- **Comprehensive Testing** - Built-in utilities for testing contexts and endpoints
- **Modern Python Features** - Leverages Python 3.12+ for optimal performance

## Ready to Get Started?

1. **[Install Zenith](/installation/)** - Set up your development environment
2. **[Quick Start](/quick-start/)** - Build your first API in 5 minutes  
3. **[Project Structure](/project-structure/)** - Learn recommended patterns
4. **[Examples](/examples/hello-world/)** - See real-world applications

## Community & Support

- **GitHub**: [nijaru/zenith](https://github.com/nijaru/zenith) - Source code and issues
- **Documentation**: You're already here! Comprehensive guides and API reference
- **Examples**: Production-ready example applications

---

*Zenith is actively developed and maintained. We welcome contributions, bug reports, and feature requests!*