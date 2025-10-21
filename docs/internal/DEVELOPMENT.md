# Zenith Development Context

*Primary AI agent context for ongoing development work*

## Current Status (v0.0.10 Released)

### Framework State
- **Version**: 0.0.10 - Production-ready framework (October 2025)
- **Tests**: 900 passing on Python 3.12, 3.13 (100% success rate)
- **Performance**: 9,600+ req/s with full middleware stack
- **Python**: 3.12-3.14 supported (3.14 has known dependency issues)
- **CI**: All workflows passing, PyPI ready

### Recent Achievements
- ✅ Service-based architecture with clean DI
- ✅ Production-ready middleware stack
- ✅ Comprehensive test coverage (900 tests)
- ✅ Python 3.14 support (pending ecosystem updates)
- ✅ CI optimizations with dependency caching
- ✅ Security documentation (SECURITY.md)

## Active Development Priorities

### 1. API Stabilization for v1.0 (CURRENT)
**Status**: In progress
- API consistency review across all modules
- Documentation completeness verification
- Breaking change assessment
- Migration guide preparation

### 2. Performance Optimization (ONGOING)
**Targets**:
- Maintain 9,600+ req/s benchmark
- Memory efficiency with bounded caches
- Zero memory leaks (comprehensive cleanup)
- CI performance improvements (caching enabled)

### 3. Python 3.14 Compatibility (MONITORING)
**Status**: Pending upstream fixes
- Framework code is compatible
- SQLAlchemy/aiosqlite segfault in 3.14.0
- CI allows 3.14 tests to fail gracefully
- Will update when ecosystem stabilizes

## Code Patterns & Conventions

### Framework Architecture
```python
# Zero-config application
app = Zenith()  # Auto-detects environment, configures everything

# Enhanced models (no session management needed)
class User(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    name: str

# Route handlers (clean, no boilerplate)
@app.get("/users")
async def get_users():  # No session parameter needed!
    return await User.where(active=True).limit(10)
```

### Import Patterns (Current)
```python
# Core framework
from zenith import Zenith, Auth

# Enhanced models
from zenith.db import ZenithModel
from sqlmodel import Field

# For examples requiring enhanced methods
from zenith.db import ZenithModel as Model
```

### Testing Patterns
```python
from zenith.testing import TestClient

async with TestClient(app) as client:
    response = await client.get("/users")
    assert response.status_code == 200
```

## Current Issues & Blockers

### Known Issues
1. **Example gaps**: Missing 09, 11 (directory-based examples exist)
2. **Internal docs**: Need reorganization (this file addresses it)
3. **Website examples**: Manual duplication (needs auto-fetch system)

### Performance Monitoring
- Run `python scripts/run_performance_tests.py` for benchmarks
- Target: >9,000 req/s with middleware
- Memory: <100MB for 1000 requests
- Test pollution: Environment variable cleanup needed

## Development Workflow

### Testing
```bash
# Full test suite
uv run pytest

# Performance tests
python scripts/run_performance_tests.py --quick

# Example verification
SECRET_KEY=test-secret-key-that-is-long-enough-for-testing uv run python examples/03-modern-developer-experience.py
```

### Release Process
```bash
# Update version in pyproject.toml
# Update CHANGELOG.md with features/fixes
# Run full test suite
# Build and release to PyPI with twine
```

## AI Agent Guidelines

### When Working on Examples
- Always use `ZenithModel` for enhanced methods
- No `session=Session` parameters (ZenithModel handles automatically)
- Test examples actually run with current framework

### When Updating Documentation
- Verify code snippets match framework reality
- Remove framework comparisons (Rails, Django, FastAPI)
- Use current patterns consistently

### When Performance Optimizing
- Measure before optimizing
- Maintain backwards compatibility
- Document optimization techniques in PERFORMANCE.md

## Quick Reference

### Key Files
- `zenith/app.py`: Main Zenith class, one-liner features
- `zenith/db/models.py`: ZenithModel implementation
- `zenith/core/dependencies.py`: Session, Auth shortcuts
- `examples/03-modern-developer-experience.py`: Showcase example

### Test Commands
- `uv run pytest -xvs`: Stop on first failure
- `uv run python -m py_compile examples/*.py`: Compile check
- `SECRET_KEY=... timeout 3s uv run python examples/FILE.py`: Test run

### Performance Targets
- Simple endpoints: >9,500 req/s
- JSON endpoints: >9,600 req/s
- With middleware: >6,500 req/s (70% retention)
- Memory usage: <100MB baseline

---

*Last updated: October 2025 - v0.0.10*