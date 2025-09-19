# 📚 Zenith Examples - Learn by Doing

Welcome to the Zenith examples! These examples are organized in a **progressive learning structure**, starting from the simplest concepts and building up to production-ready applications.

**Coverage: 100% of framework features** - Complete documentation of all examples (00-22) for production applications.

## 🎯 Learning Path

### **Basics** (Start Here)
Master the core concepts of Zenith web development:

- **[00-hello-world.py](00-hello-world.py)** - 🚀 The simplest possible Zenith app
- **[01-basic-routing.py](01-basic-routing.py)** - 🛤️ Path parameters, query strings, HTTP methods
- **[02-pydantic-validation.py](02-pydantic-validation.py)** - 🔍 Type-safe request/response with automatic validation
- **[03-modern-developer-experience.py](03-modern-developer-experience.py)** - 🏗️ Modern patterns and enhanced DX features

### **Essential Features**
Learn the key middleware and features you'll use in real applications:

- **[04-one-liner-features.py](04-one-liner-features.py)** - ⚡ Rails-like one-liner convenience methods
- **[05-context-system.py](05-context-system.py)** - 🏗️ Business logic organization with Zenith's Context system
- **[06-file-upload.py](06-file-upload.py)** - 📁 Enhanced file upload with improved UX and Starlette compatibility
- **[07-websocket-chat.py](07-websocket-chat.py)** - 💬 Real-time WebSocket chat application
- **[08-rate-limiting.py](08-rate-limiting.py)** - 🚦 Request throttling and API protection

### **Database & API Development**
Build sophisticated, production-ready functionality:

- **[09-database-todo-api/](09-database-todo-api/)** - 🗄️ Complete SQLAlchemy integration with authentication
- **[10-cors-middleware.py](10-cors-middleware.py)** - 🌐 CORS configuration for web applications
- **[11-complete-production-api/](11-complete-production-api/)** - 🏭 Full-featured production application
- **[12-security-middleware.py](12-security-middleware.py)** - 🛡️ Complete security stack (CSRF, headers, compression)
- **[13-router-grouping.py](13-router-grouping.py)** - 🗂️ Clean API organization with nested routers and prefixes

### **Background Processing & Tasks**
Asynchronous task handling and job processing:

- **[14-background-tasks.py](14-background-tasks.py)** - ⚡ Async background task processing
- **[15-advanced-background-processing.py](15-advanced-background-processing.py)** - 🔄 Redis-powered job queues with retry logic and scheduling

### **Production Essentials** ⭐ **NEW!**
Critical patterns for production deployment and maintenance:

- **[16-testing-patterns.py](16-testing-patterns.py)** - 🧪 Comprehensive testing (API, business logic, auth, performance)
- **[17-performance-monitoring.py](17-performance-monitoring.py)** - 📊 Health checks, metrics, profiling, observability
- **[18-database-sessions.py](18-database-sessions.py)** - 🔥 **CRITICAL**: Request-scoped async DB sessions (fixes production crashes)

### **Advanced Patterns** ⭐ **NEW!**
Advanced production patterns for sophisticated applications:

- **[19-seamless-integration.py](19-seamless-integration.py)** - 💾 ZenithModel seamless integration patterns
- **[20-fullstack-spa.py](20-fullstack-spa.py)** - 🌐 Full-stack SPA serving (React, Vue, SolidJS, Angular)
- **[21-proper-middleware-architecture.py](21-proper-middleware-architecture.py)** - 🏗️ Production middleware architecture patterns
- **[22-server-sent-events.py](22-server-sent-events.py)** - 📡 Real-time event streaming with Server-Sent Events

## 📈 Example Status
- ✅ **20 examples working** - Ready to run and learn from
- ⏭️ **1 skipped** - Testing patterns (requires pytest dependency)
- 🔧 **1 incomplete** - Complete production API (needs work)

## 🎓 Recommended Learning Order

1. **Start with 00-03** to understand the basics
2. **Try 04-05** for modern DX features
3. **Explore 06-09** for essential functionality
4. **Study 10-15** for advanced features
5. **Master 16-22** for production patterns

## 🚀 Running Examples

Each example is self-contained and can be run directly:

```bash
# Set required environment variable
export SECRET_KEY="your-secret-key-at-least-32-characters-long"

# Run any example
python examples/00-hello-world.py

# Or with uv (recommended)
uv run python examples/00-hello-world.py
```

## 🔧 Prerequisites

Most examples work out of the box. Some may require additional dependencies:

- **PostgreSQL examples**: Set `DATABASE_URL` environment variable
- **Testing patterns**: Install pytest (`pip install pytest`)
- **Background processing**: Redis for advanced examples

## 📖 Documentation

Each example includes:
- **Comprehensive comments** explaining every concept
- **Real-world patterns** you can copy to your projects
- **Production considerations** and best practices
- **Performance tips** and optimization guidance

## 🤝 Contributing

Found an issue or want to improve an example? Contributions welcome!

1. Check the example works with latest Zenith
2. Ensure code follows existing patterns
3. Add comprehensive comments
4. Test with different scenarios

---

*These examples demonstrate Zenith v0.3.0 features. Check the [documentation](https://docs.zenith-python.org) for complete guides.*