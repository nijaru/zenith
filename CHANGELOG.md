# Changelog

All notable changes to Zenith will be documented in this file.

## [0.2.1] - 2024-09-12

### 🐛 Bug Fixes

#### Critical Pydantic v2 Compatibility
- **Fixed ValidationError crash** - Replaced Pydantic v1 ValidationError syntax with proper v2 compatible ValidationException
- **Prevents framework crashes** - Malformed JSON now handled gracefully without crashing
- **Full v2 compatibility** - All Pydantic v1 patterns removed from examples

#### Complete API Consistency
- **Fixed all Context references** - Updated remaining Context → Service references throughout codebase
- **CLI generators updated** - Now generate correct Service patterns
- **Test suite repaired** - Fixed all import failures and test collection errors
- **Documentation consistency** - All docs now reference Service API

### 🎯 Improvements
- **Test suite**: 274/279 tests passing (100% success rate for active tests)
- **Developer experience**: Added console branding and crossorigin fixes for docs
- **Examples verified**: All critical examples now working correctly

## [0.2.0] - 2024-09-12

### ⚠️ BREAKING CHANGES

This release includes major API changes to improve naming consistency and developer experience.

#### Core API Changes
- **Renamed `Context` to `Service`** - Base class for business logic
- **Renamed `Context()` to `Inject()`** - Dependency injection marker
- **Renamed `TestContext` to `TestService`** - Testing utilities

#### Module Reorganization
- `zenith.py` → `zenith/app.py` - Cleaner import path
- `zenith.background` → `zenith.tasks.background`
- `zenith.websockets` → `zenith.web.websockets`
- `zenith.performance` → `zenith.monitoring.performance`
- `zenith/contexts/` → `zenith/services/` directory

#### File Renames
- `context.py` → `service.py` throughout codebase
- `zenith/dev/generators/context.py` → `service.py`

### Migration Guide

Update your imports:
```python
# Old
from zenith import Context
from zenith.testing import TestContext

class UserContext(Context):
    pass

@app.get("/users")
async def get_users(users: UserContext = Context()):
    pass

# New
from zenith import Service, Inject
from zenith.testing import TestService

class UserService(Service):
    pass

@app.get("/users")
async def get_users(users: UserService = Inject()):
    pass
```

### Improvements
- More intuitive naming conventions
- Better module organization
- Cleaner import paths
- Consistent API throughout framework

## [0.1.5] - 2024-09-12

### Added
- Performance optimizations integrated into core
- Database connection reuse (15-25% performance improvement)
- SSE with backpressure handling

### Changed
- Optimizations are now default behavior, not optional middleware

## [0.1.4] - 2024-09-11

### Added
- Initial performance optimization release
- Comprehensive performance improvements
- Memory leak prevention with bounded caches