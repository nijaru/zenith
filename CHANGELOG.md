# Changelog

All notable changes to the Zenith framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-09-11

### Added
- 🚀 **Core Framework**: Complete async web framework with type-safe routing
- 🏗️ **Context System**: Clean architecture for organizing business logic
- 🔒 **Security Stack**: JWT auth, CSRF protection, security headers, rate limiting
- 📊 **Performance Monitoring**: Built-in metrics, health checks, profiling decorators
- 💾 **Database Integration**: Async SQLAlchemy with Alembic migrations
- 🔄 **Background Jobs**: Task queues with Redis backend and scheduling
- 🌐 **WebSocket Support**: Real-time communication with connection management  
- 🧪 **Testing Framework**: Comprehensive test client with auth helpers
- ⚡ **High Performance**: 7,700+ req/s bare endpoints, 850+ req/s with full middleware
- 📚 **Complete Examples**: 16 progressive examples from hello-world to production
- 🛠️ **CLI Tools**: Project generation, dev server, database migrations
- 📖 **Documentation**: Comprehensive guides and API reference

### Features
- **Router Grouping**: Organize routes with nested routers and middleware
- **SQLModel Integration**: Type-safe database models with relationships
- **File Upload Handling**: Validation, storage, and processing
- **CORS Middleware**: Flexible cross-origin resource sharing
- **Compression**: Brotli and gzip with configurable settings
- **Session Management**: Cookie, Redis, and database backends
- **Request Logging**: Structured logging with correlation IDs
- **Static File Serving**: Efficient static asset delivery
- **Input Validation**: Automatic Pydantic validation for all endpoints

### Performance
- 7,743 req/s for simple endpoints (bare framework)
- 7,834 req/s for JSON endpoints (bare framework)
- 856 req/s with full middleware stack (88.9% overhead)
- Memory efficient: <100MB for 1000 requests
- Startup time: <100ms

### Security
- JWT authentication with secure defaults
- bcrypt password hashing (12 rounds default)
- CSRF protection with time-based tokens
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Rate limiting with memory/Redis storage
- Input sanitization and validation
- Secure cookie handling with SameSite

### Quality
- 100% test coverage (293 tests passing, 2 skipped)
- Type hints throughout
- Comprehensive error handling  
- Production-ready defaults
- Zero-configuration development setup
- Hot reload development server

### Documentation
- 📚 Progressive learning examples (00-16)
- 🔧 Production deployment guides
- 📋 API reference documentation
- 🧪 Testing patterns and best practices
- 🏗️ Architecture guides
- 🚀 Quick start tutorials

### Developer Experience
- Modern Python 3.12+ support
- Intuitive decorator-based routing
- Automatic API documentation generation
- Built-in development server with hot reload
- Comprehensive CLI tools (`zen` command)
- Rich error messages and debugging

### Breaking Changes
None (initial release)

### Security Updates
- All dependencies use secure, up-to-date versions
- No known security vulnerabilities
- Secure configuration defaults

---

**Full Changelog**: https://github.com/nijaru/zenith/commits/v0.1.0