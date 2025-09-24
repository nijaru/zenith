# 📚 Zenith Examples - Learn by Doing

Welcome to the Zenith examples! These examples are organized in a **progressive learning structure**, starting from the simplest concepts and building up to production-ready applications.

**Coverage: 100% of framework features** - Complete documentation of all examples (00-14) for production applications.

## 🎯 Learning Path

### **Basics** (Start Here) 
Master the core concepts of Zenith web development:

- **[00-hello-world.py](00-hello-world.py)** - 🚀 The simplest possible Zenith app
- **[01-basic-routing.py](01-basic-routing.py)** - 🛤️ Path parameters, query strings, HTTP methods
- **[02-pydantic-validation.py](02-pydantic-validation.py)** - 🔍 Type-safe request/response with automatic validation
- **[03-context-system.py](03-context-system.py)** - 🏗️ Business logic organization with Zenith's Context system

### **Essential Features**
Learn the key middleware and features you'll use in real applications:

- **[04-cors-middleware.py](04-cors-middleware.py)** - 🌐 CORS configuration for web applications
- **[05-background-tasks.py](05-background-tasks.py)** - ⚡ Async background task processing
- **[06-file-upload.py](06-file-upload.py)** - 📁 Enhanced file upload with improved UX and Starlette compatibility

### **Advanced Features**
Build sophisticated, production-ready functionality:

- **[07-websocket-chat.py](07-websocket-chat.py)** - 💬 Real-time WebSocket chat application
- **[08-rate-limiting.py](08-rate-limiting.py)** - 🚦 Request throttling and API protection
- **[09-database-todo-api/](09-database-todo-api/)** - 🗄️ Complete SQLAlchemy integration with authentication
- **[10-complete-production-api/](10-complete-production-api/)** - 🏭 Full-featured production application

### **Production Essentials** ⭐ **NEW!**
Critical patterns for production deployment and maintenance:

- **[11-security-middleware.py](11-security-middleware.py)** - 🛡️ Complete security stack (CSRF, headers, compression)
- **[12-performance-monitoring.py](12-performance-monitoring.py)** - 📊 Health checks, metrics, profiling, observability
- **[13-testing-patterns.py](13-testing-patterns.py)** - 🧪 Comprehensive testing (API, business logic, auth, performance)

### **Advanced Patterns** ⭐ **NEW!**
Advanced production patterns for sophisticated applications:

- **[14-advanced-background-processing.py](14-advanced-background-processing.py)** - 🔄 Redis-powered job queues with retry logic, scheduling, and worker processes

### **Modern Patterns** ⭐ **NEW!**
Latest patterns for modern web development:

- **[15-router-grouping.py](15-router-grouping.py)** - 🗂️ Clean API organization with nested routers and prefixes
- **[16-async-database-scoped.py](16-async-database-scoped.py)** - 🔥 **CRITICAL**: Request-scoped async DB sessions (fixes production crashes)
- **[16-sqlmodel-integration.py](16-sqlmodel-integration.py)** - 💾 Unified Pydantic + SQLAlchemy models with repository pattern
- **[17-fullstack-spa.py](17-fullstack-spa.py)** - 🌐 Full-stack SPA serving (React, Vue, SolidJS, Angular)
- **[18-frontend-serving-dx.py](18-frontend-serving-dx.py)** - ✨ Improved developer experience for frontend serving

## 🚀 Quick Start

Each example is designed to run independently:

```bash
# Run any example
python examples/00-hello-world.py

# Most examples include interactive documentation
# Visit http://localhost:PORT/docs after starting
```

## 📖 Documentation

Each example includes:
- **📝 Clear docstrings** explaining what it demonstrates  
- **🧪 Usage instructions** with example requests
- **💡 Key concepts** highlighted in comments
- **🔗 Links to relevant docs** for deeper learning

## 🎓 Recommended Learning Order

### **For Beginners** (2-3 hours)
1. **Start with 00-03**: Learn the Zenith fundamentals
2. **Try 04-06**: Master essential middleware and features  
3. **Explore 07-08**: Build real-time and robust applications

### **For Production Teams** (1 day)
1. **Review 01-03**: Understand core concepts
2. **Focus on 09-10**: Study complete applications
3. **Master 11-13**: Production patterns (security, monitoring, testing)
4. **Advanced processing 14**: Redis job queues for scale

### **Complete Mastery** (1 week)
- **All examples (00-14)**: Comprehensive framework coverage including advanced patterns
- **Custom variations**: Adapt patterns to your use case
- **Performance tuning**: Optimize for your requirements

## 🔧 Development Examples

The `archive/` directory contains experimental and testing examples that showcase framework development concepts but aren't part of the main learning path.

## 🏗️ Architecture Highlights

**What makes Zenith different:**
- **Context-driven architecture** - Business logic organized in clean, testable contexts
- **Type-safe dependency injection** - No boilerplate, just clean `Context()` parameters  
- **Pydantic-first** - Automatic validation and serialization throughout
- **Production-ready** - Built-in middleware, authentication, and database patterns

## 🏭 Production-Ready Features

**New in this release** - Examples 11-13 demonstrate enterprise-grade patterns:

### **🛡️ Security Excellence** (Example 11)
- HSTS, CSP, X-Frame-Options security headers
- CSRF protection with SameSite cookies
- Request correlation IDs for debugging
- Gzip/Brotli compression
- Production security checklist

### **📊 Observability Stack** (Example 12)
- `/health` and `/health/detailed` endpoints
- Prometheus-compatible `/metrics`
- Performance decorators (`@cached`, `@measure_time`)
- System resource monitoring
- Custom business metrics

### **🧪 Testing Excellence** (Example 13)
- `TestClient` for API endpoint testing
- `TestService` for isolated business logic testing
- `MockAuth` for authentication testing
- Performance and load testing patterns
- Test factories and fixtures

## 🎯 Modern Development Patterns

**Latest patterns demonstrated throughout the examples:**

### **🎯 Modern SQLModel API** (Example 09)
- Unified Pydantic + SQLAlchemy models with `SQLModel`
- `ZenithSQLModel` base class with auto-configuration
- Repository pattern with `create_repository()`
- Type-safe database operations throughout
- Modern async patterns with dependency injection

### **📁 Router Organization** (Examples 09, 10)
- Clean API structure with Router grouping
- URL prefixes and nested route organization
- Middleware application at router level
- Scalable patterns for large applications
- Modern FastAPI-style route organization

### **🔄 Advanced Background Processing** (Example 14)
- Redis-powered job queues with priority and retry mechanisms
- Worker processes with supervision and fault tolerance
- Job scheduling with cron-like expressions
- Progress tracking and comprehensive result handling
- Production-ready distributed task processing

## 🤝 Contributing

Found an issue or want to improve an example? Please:
1. Check if it's already in the `archive/` directory
2. Test your changes with `python examples/your-example.py`
3. Follow the existing documentation style
4. Submit a PR with a clear description

---

**Happy coding with Zenith!** 🚀