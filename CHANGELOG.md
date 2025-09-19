# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-09-18

### Added
- **Rails-like Developer Experience**: Zero-config setup with `app = Zenith()`
- **One-liner Features**: `app.add_auth()`, `app.add_admin()`, `app.add_api()` convenience methods
- **Server-Sent Events (SSE)**: Complete SSE implementation with backpressure handling and adaptive throttling
- **ZenithModel**: Rails-like ActiveRecord patterns with `User.all()`, `User.find()`, `User.create()`, `User.where()`
- **Enhanced Dependency Injection**: Clean shortcuts like `db=DB`, `user=Auth`, `service=Inject()`
- **Comprehensive SSE Testing**: 39 unit tests and 18 integration tests for SSE functionality
- **Automatic Admin Dashboard**: `/admin` endpoint with health checks and statistics
- **Built-in API Documentation**: Automatic OpenAPI docs at `/docs` and `/redoc`

### Changed
- **Enhanced TestClient**: Now supports both Zenith and Starlette applications
- **Improved Example Organization**: Fixed duplicate numbering, now examples 00-23
- **Updated Documentation**: Comprehensive docs refresh with v0.3.0 patterns
- **Modernized Import Patterns**: Cleaner imports with `from zenith.core import DB, Auth`

### Fixed
- **SSE Throttling Logic**: Fixed to only throttle after first event sent
- **TestClient Compatibility**: Resolved startup/shutdown issues with Starlette apps
- **SSE Integration Tests**: Fixed timing issues with rate limiting
- **Example Syntax**: All examples now compile and run correctly
- **Documentation Imports**: Updated all docs to use new v0.3.0 import patterns

### Performance
- **SSE Rate Limiting**: Optimized to 10 events/second with intelligent backpressure
- **Memory Efficiency**: SSE implementation uses weak references for automatic cleanup
- **Test Suite**: Expanded from 471 to 776 tests while maintaining performance

## [0.2.6] - 2025-09-17

### Fixed
- Test pollution and environment variable cleanup
- Broken imports and dead code removal
- Critical database bug with SQLModel table creation
- Test import issues and documentation updates

### Added
- Ultra-simple SECRET_KEY automation with explicit load_dotenv()

---

For detailed release notes and migration guides, see our [GitHub Releases](https://github.com/nijaru/zenith/releases).