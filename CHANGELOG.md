# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-09-24

### 🎉 Initial Release of `zenithweb`

Complete rebrand from `zenith-web` to `zenithweb` - a fresh start with a cleaner, more modern package name.

### Added
- **Zero-Configuration Setup**: `app = Zenith()` with intelligent defaults
- **ZenithModel**: Enhanced SQLModel with intuitive query methods
- **One-Liner Features**: `app.add_auth()`, `app.add_admin()`, `app.add_api()`
- **Type-Safe Dependency Injection**: Clean shortcuts like `db=DB`, `user=Auth`
- **Production Middleware**: CORS, CSRF, compression, rate limiting, security headers
- **JWT Authentication**: Complete auth system with one line
- **Admin Dashboard**: System monitoring and health checks
- **Interactive Documentation**: Auto-generated Swagger UI and ReDoc
- **WebSocket Support**: Real-time communication with connection management
- **Background Tasks**: Async task processing with TaskGroups
- **Testing Framework**: Comprehensive TestClient with auth helpers
- **CLI Tools**: `zen` command for development and project management

### Performance
- **9,600+ req/s**: High-performance async request handling
- **Minimal Overhead**: <5% per middleware component
- **Memory Efficient**: Bounded caches and automatic cleanup
- **Full Async Support**: Python 3.12+ with TaskGroups optimization

### Changed
- **Package Name**: From `zenith-web` to `zenithweb` for cleaner installation
- **Version Reset**: Starting fresh at v0.1.0 for the new package
- **Documentation**: Complete rewrite focusing on features without defensive comparisons

## [0.3.1] - 2025-09-19 (as `zenith-web`, deprecated)

### Added
- **Automated Version Management**: `scripts/version_manager.py` and `scripts/bump_version.sh` for consistent version updates
- **Auto-Generated Documentation**: GitHub API integration for automatically generating website example pages
- **Documentation Standards**: `DOC_PATTERNS.md` for AI agent and human developer documentation organization

### Fixed
- **Example Import Consistency**: All examples now use `ZenithModel as Model` with enhanced methods
- **Documentation Accuracy**: Removed misleading `session=Session` parameters from all documentation
- **Database File Management**: Examples now create databases in `examples/` directory instead of project root
- **Repository Organization**: Cleaned up test artifacts, cache files, and temporary directories

### Changed
- **Enhanced Release Process**: Automated version management across 20+ files
- **Improved Repository Structure**: Better organization following documentation standards
- **Website Maintenance**: Reduced maintenance overhead through auto-generation from examples

### Performance
- **Repository Cleanup**: Eliminated accumulation of database files and test artifacts
- **Documentation Sync**: Zero-maintenance documentation that stays synchronized with code

## [0.3.0] - 2025-09-18

### Added
- **Modern Developer Experience**: Zero-config setup with `app = Zenith()`
- **One-liner Features**: `app.add_auth()`, `app.add_admin()`, `app.add_api()` convenience methods
- **Server-Sent Events (SSE)**: Complete SSE implementation with backpressure handling and adaptive throttling
- **ZenithModel**: Intuitive database patterns with `User.all()`, `User.find()`, `User.create()`, `User.where()`
- **Enhanced Dependency Injection**: Clean shortcuts like `db=DB`, `user=Auth`, `service=Inject()`
- **Comprehensive SSE Testing**: 39 unit tests and 18 integration tests for SSE functionality
- **Automatic Admin Dashboard**: `/admin` endpoint with health checks and statistics
- **Built-in API Documentation**: Automatic OpenAPI docs at `/docs` and `/redoc`

### Changed
- **Enhanced TestClient**: Now supports both Zenith and Starlette applications
- **Improved Example Organization**: Fixed duplicate numbering, now examples 00-23
- **Updated Documentation**: Comprehensive docs refresh with v0.3.1 patterns
- **Modernized Import Patterns**: Cleaner imports with `from zenith.core import DB, Auth`

### Fixed
- **SSE Throttling Logic**: Fixed to only throttle after first event sent
- **TestClient Compatibility**: Resolved startup/shutdown issues with Starlette apps
- **SSE Integration Tests**: Fixed timing issues with rate limiting
- **Example Syntax**: All examples now compile and run correctly
- **Documentation Imports**: Updated all docs to use new v0.3.1 import patterns

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