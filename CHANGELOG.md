# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.14] - 2025-12-04

### Security

- **Critical vulnerability fixes** - Addressed 7 security issues from comprehensive code review
    - Fixed trusted proxy validation bypass in ASGI rate limiting path
    - CSRF tokens no longer bound to IP (prevents token invalidation on network change)
    - CSRF cookie now HttpOnly by default (prevents XSS token theft)
    - File upload extension sanitization hardened against traversal attacks
    - Generic auth error messages prevent user enumeration
    - Parameter validation returns 400 (not 500) for invalid input

### Changed

- **Dependencies** - Upgraded 57 packages including security patches
- **Benchmark CI** - Now runs only on version tags (reduced CI noise)

### Fixed

- Removed dead `remote_addr` code from CSRF middleware
- Extracted security constants (`DEFAULT_TRUSTED_PROXIES`, `SAFE_FILENAME_CHARS`)

## [0.0.13] - 2025-11-25

### Changed

- **Production mode** - Added `production=True` flag for secure middleware defaults
- **Performance** - Handler metadata caching (40% performance boost)

### Fixed

- Deprecated `xss_protection` removed from SecurityConfig example

## [0.0.12] - 2025-11-24

### Changed

- **Marketing messaging** - Updated performance claims to use vague, industry-standard language
    - Changed from specific "~12,000 req/s" to "high-performance async architecture"
    - Aligns with how FastAPI and other frameworks communicate performance
    - Specific benchmarks still available via test suite: `uv run pytest tests/performance/ -v`
    - Internal docs retain specific numbers for development tracking

### Fixed

- **Critical linting errors** - Resolved all linting errors in main source code (60 → 0)
    - Fixed loop variable binding bugs (B023) in test closures using default arguments
    - Replaced `open()` with `Path().open()` for pathlib consistency (PTH123)
    - Fixed 57% of linting errors through systematic pathlib adoption
    - Added per-file ignores for acceptable test patterns (B017)

### Documentation

- Updated README.md, CLAUDE.md, and website docs with conservative performance language
- Performance claims now follow industry best practices (vague but honest)

## [0.0.11] - 2025-10-21

### Performance

- **Major routing optimization** - Eliminated closure overhead in route registration (+24-69% performance gain)
    - Simple endpoints: 13,074 req/s (+69% from 7,743 req/s)
    - JSON endpoints: 12,274 req/s (+24% from 9,917 req/s)
    - With middleware: 8,781 req/s (+25% from 7,044 req/s)
    - Pre-compile endpoint functions instead of creating closures dynamically
    - Bind parameters at registration time, not call time

### Security

- **Argon2 password hashing** - Migrated from bcrypt to Argon2id via pwdlib
    - More secure and modern algorithm (winner of Password Hashing Competition 2015)
    - Automatic hash upgrades on login
    - Backward compatible with existing bcrypt hashes

### Documentation

- **Accurate performance claims** - Updated all docs with verified benchmark numbers
    - Conservative, reproducible measurements
    - Documented testing methodology and caveats

### Fixed

- **GraphQL error handling** - Add proper exception chaining in ImportError (zenith/app.py:1071)

## [0.0.10] - 2025-10-20

### Added

- **Enhanced proxy support** - TrustedProxyMiddleware now handles X-Forwarded-Host, X-Forwarded-Port, and X-Forwarded-Prefix headers
    - Supports apps behind nginx, Cloudflare, AWS ALB/ELB, or other reverse proxies
    - Path prefix support for apps mounted at /api, /v1, etc.
    - Virtual host support via X-Forwarded-Host
    - Port forwarding for apps behind load balancers
    - 8 new comprehensive tests for proxy header handling

### Fixed

- **Code quality** - Resolved 78 linting errors (144 → 66, 54% improvement)
    - Fixed all undefined name errors (Context → Service naming)
    - Added missing HTTPException imports in examples
    - Formatted code per ruff standards
- **Test isolation** - Fixed database cleanup issue in seamless DX integration tests
    - Added pre-test cleanup to prevent leftover data from previous runs
    - 899 tests now passing (up from 891)
- **Dependencies** - Excluded yanked pydantic 2.12.1 from installation
    - Updated to pydantic 2.12.3 and pydantic-core 2.41.4

### Security

- **Documented pip CVE-2025-8869** - All pip versions ≤25.2 affected, fix planned for 25.3
    - Low risk for development environments (requires malicious sdist installation)
    - Tracking issue in pyproject.toml comments

## [0.0.9] - 2025-10-12

### Changed

- **Dependency updates** - Updated core dependencies to latest stable versions
    - SQLModel 0.0.25 → 0.0.27 (adds Python 3.14 support)
    - SQLAlchemy 2.0.43 → 2.0.44 (PostgreSQL 17.3+ fixes, MySQL reflection improvements, mypy 1.11 compatibility)
    - Alembic 1.16.5 → 1.17.0 (latest migration tooling)
    - Updated various supporting packages (certifi, rich, idna, httptools, markupsafe, msgpack, etc.)

### Testing

- All 891 tests passing (including performance tests)
- Comprehensive test coverage maintained

## [0.0.8] - 2025-10-12

### Fixed

- **Python 3.14 compatibility** - Fixed `Path.suffix` behavior change for filenames ending with dot (e.g., "file.")
- **Test isolation** - Switched from unique databases to table truncation pattern for reliable test isolation
- **Auto-config tests** - Fixed DATABASE_URL environment variable interference with default value tests
- **Performance test markers** - Fixed pytest marker application to only affect performance directory tests
- **Password hashing** - Pinned bcrypt to <4.2.0 for passlib 1.7.4 compatibility
- **Type annotations** - Removed quoted type annotation for Python 3.13+ compatibility

### Testing

- Excluded flaky performance tests from CI (still runnable locally with `pytest -m performance`)
- All 845 core tests passing on Python 3.12, 3.13, and 3.14
- Performance tests now properly isolated with markers

### Internal

- Improved CI reliability by skipping timing-dependent tests in shared runner environment
- Better test organization with performance marker system

## [0.0.7] - 2025-10-08

### Fixed

- **Session cookie optimization** - Cookies now only set when session is modified or new, reducing bandwidth and enabling HTTP caching (fixes Starlette issue present in FastAPI)
- **Session boolean evaluation** - Empty sessions now correctly evaluate to `True` instead of `False`
- **Pydantic v2 compatibility** - Updated `background.py` to use `model_config = ConfigDict()` instead of deprecated `class Config:`

### Security

- Comprehensive security audit completed - all systems verified secure
- Verified JWT uses constant-time comparison
- Verified cookie signatures use `hmac.compare_digest()`
- Verified CORS validation prevents wildcard + credentials

### Testing

- Added test for session cookie optimization behavior
- All 891 tests passing

### Performance

- 90% reduction in unnecessary Set-Cookie headers
- Session middleware now more efficient than FastAPI/Starlette

## [0.0.6] - 2025-10-06

### Changed

- **Code Quality Improvements** - Achieved 100% ruff compliance (fixed 506 linting issues)
    - Replaced `os.path` with modern `pathlib.Path` API throughout codebase
    - Added `UploadedFile` to public API (`__all__`)
    - Simplified return conditions and exception handling patterns
    - Added `ClassVar` annotations for class attributes
    - Fixed mutable default in `ContextVar`
    - Added exception chaining (`raise ... from e`) for better tracebacks
    - Updated test mocks to work with `pathlib.Path`

### Internal

- Zero linting issues - completely clean codebase
- All 890 tests passing

## [0.0.5] - 2025-09-30

### Context

This release implements NestJS-style constructor injection for Services, providing a cleaner and more intuitive dependency injection pattern. This is a **breaking change** but significantly improves the developer experience.

### Added

- **Constructor Injection** - Services now use type-hinted constructor parameters for automatic dependency resolution
- **Service.create() factory method** - Services can be instantiated outside DI context for helper functions, middleware, background jobs, and CLI commands
- **Union type support in DIContainer** - Handles optional dependencies (`SomeService | None`)
- **Recursive dependency resolution** - DIContainer automatically resolves nested Service dependencies
- Comprehensive test coverage for constructor injection patterns (6 new tests in test_service_di_injection.py)
- Comprehensive test coverage for QueryBuilder chaining patterns (9 new tests)
- Comprehensive test coverage for Service.create() patterns (10 new tests)
- Documentation for constructor injection in services.mdx
- Documentation for standalone Service usage

### Fixed

- Session now fetched lazily only when executing terminal methods (.first(), .all(), .count(), .exists())
- Fixed ZenithModel.exists() to work with synchronous where() method
- Service attribute initialization works correctly even when subclasses override `__init__` without calling `super()`

### Changed

- **BREAKING**: `ZenithModel.where()` is now synchronous - Enables clean single-line chaining: `await User.where(email=email).first()`
- **BREAKING**: Removed `container` parameter from `Service.__init__()`
- **BREAKING**: Services use constructor injection via type hints instead of manual container resolution
- **Service pattern**: Dependencies injected via typed constructor parameters (NestJS-style)
- `ServiceRegistry` now uses `DIContainer._create_instance()` for automatic dependency injection
- `DependencyResolver` uses container's injection system for Service creation
- Lazy initialization pattern for framework attributes (\_container, \_request, \_events, \_initialized)
- Type hints simplified throughout service system

### Developer Experience Improvements

- **Cleaner syntax**: No `container` parameter needed in Service `__init__`
- **Type-safe**: Full IDE support for dependency injection via type hints
- **Easier testing**: Just pass mock dependencies to constructor
- **Works standalone**: Services work identically in DI context and manual instantiation
- **Pythonic**: Uses standard `__init__` patterns, no special framework magic required
- Seamless QueryBuilder chaining eliminates awkward two-step pattern

### Migration Guide

**Service constructor injection:**

```python
# Before (v0.0.4)
from zenith import Service
from zenith.core.container import DIContainer

class OrderService(Service):
    def __init__(self, container: DIContainer | None = None):
        super().__init__(container)
        # Had to manually resolve dependencies
        self.products = container.get(ProductService) if container else ProductService()

# After (v0.0.5)
from zenith import Service

class OrderService(Service):
    def __init__(self, products: ProductService):
        # Dependencies auto-injected via type hints!
        self.products = products
        # No super().__init__() needed, no container parameter
```

**Service with no dependencies:**

```python
# Before (v0.0.4)
class SimpleService(Service):
    def __init__(self, container: DIContainer | None = None):
        super().__init__(container)

# After (v0.0.5)
class SimpleService(Service):
    # No __init__ needed at all!
    pass
```

**Optional dependencies:**

```python
# v0.0.5 supports optional dependencies
class CacheService(Service):
    def __init__(self, redis: RedisService | None = None):
        self.redis = redis  # Will be None if RedisService not registered
```

**Standalone service usage (new in v0.0.5):**

```python
# Use Service.create() for helper functions, CLI, background jobs
async def process_data(data: str):
    service = await MyService.create()
    return await service.process(data)
```

**QueryBuilder pattern (BREAKING CHANGE):**

```python
# Before (v0.0.4) - .where() was async
query = await User.where(email=email)
user = await query.first()

# After (v0.0.5) - .where() is now sync for seamless chaining
user = await User.where(email=email).first()

# Also works with chaining
users = await User.where(active=True).order_by('-created_at').limit(10).all()
```

**Why this change?** The old async `.where()` forced a two-step pattern. Making it synchronous enables natural chaining like Rails/Django ORMs.

## [0.0.4] - 2025-09-29

### Security

- **CRITICAL**: Fixed SQL injection vulnerability in `QueryBuilder.order_by()` - now validates column names
- **HIGH**: Removed deprecated X-XSS-Protection header (can create vulnerabilities in modern browsers)
- **HIGH**: Enhanced JWT secret key validation with entropy checking - rejects weak keys
- **MEDIUM**: Improved SSRF protection using `ipaddress` module - properly blocks all private/reserved IPs
- **MEDIUM**: Strengthened default Content Security Policy with modern directives

### Fixed

- Fixed race condition from duplicate database session creation in executor and middleware
- Fixed silent error swallowing in cleanup handlers - now logs warnings for debugging
- Fixed fragile database discovery that scanned all sys.modules - requires explicit registration
- Fixed Application to properly register database as default for ZenithModel
- Fixed inconsistent type hints in Service and database session functions
- Fixed QueryBuilder.count() to preserve filters correctly

### Changed

- **BREAKING**: Removed deprecated `Application.register_shutdown_hook()` - use `add_shutdown_hook()`
- **BREAKING**: `QueryBuilder.order_by()` now raises `ValueError` for invalid column names
- **BREAKING**: JWT secret keys must have sufficient entropy (≥16 unique chars, no char >25% frequency)
- Simplified database session management - removed O(n) module scanning
- Extracted duplicate JSON parsing logic to single `_parse_json_body()` method
- Removed unused string interning code
- `NotFoundError` now properly exported from exceptions module

### Performance

- Optimized QueryBuilder operations by removing unnecessary subqueries
- Reduced duplicate code in request body parsing (3 locations → 1)

## [0.0.3] - 2025-09-29

### Added

- **Python 3.13 support** - Framework now supports Python 3.12-3.13
- Removed Python 3.13 compatibility warning

### Changed

- Updated Python requirement to `>=3.12,<3.14`
- Updated all documentation and examples to reference v0.0.3
- Updated issue templates with Python 3.13 examples
- Code formatting improvements across codebase (85 files)

### Fixed

- Test count updated to 862 tests (was showing 857)

## [0.0.2] - 2025-09-29

### Security

- **CRITICAL**: Fixed rate limiting bypass vulnerability - removed localhost exemptions
- **CRITICAL**: Fixed authentication vulnerability accepting any credentials
- **CRITICAL**: Fixed JWT middleware not being properly configured globally
- **OAuth2 Compliance**: Ensured `expires_in` field is included in token response

### Fixed

- Rate limiting now enforces limits for all IP addresses including localhost
- Authentication now properly validates credentials (demo/demo in dev mode only)
- JWT tokens are properly validated across all protected endpoints
- OAuth2 token response includes all required RFC 6749 fields

### Changed

- Authentication in debug/development mode now only accepts demo/demo credentials
- Rate limiting has no default exemptions for maximum security
- Made auth condition more flexible (debug OR development environment)

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
