# Zenith Development Context

*Primary AI agent context for ongoing development work*

## Current Status (v0.3.1 Released)

### Framework State
- **Version**: 0.3.0 - Modern DX release (September 2025)
- **Tests**: 775/776 passing (99.9% success rate)
- **Performance**: 9,600+ req/s with full middleware stack
- **Python**: 3.12+ required (uses TaskGroups, modern generics)

### Recent Achievements
- ✅ Zero-config setup: `app = Zenith()` works automatically
- ✅ ZenithModel with intuitive methods: `User.where().find().create()`
- ✅ One-liner features: `app.add_auth().add_admin().add_api()`
- ✅ No manual session management needed
- ✅ 85% boilerplate reduction vs traditional FastAPI

## Active Development Priorities

### 1. Documentation Consistency (CURRENT)
**Status**: In progress
- Fixed examples to use `ZenithModel` instead of `Model`
- Removed misleading `session=Session` parameters
- Updated all docs to match v0.3.1 reality

### 2. Performance Optimization (NEXT)
**Targets**:
- Maintain 9,600+ req/s benchmark
- Memory efficiency with bounded caches
- Zero memory leaks (WeakKeyDictionary patterns)

### 3. Production Readiness (ONGOING)
- Comprehensive middleware stack (security, CORS, rate limiting)
- Built-in monitoring (`/health`, `/metrics`)
- Error handling and logging

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

### Import Patterns (v0.3.1)
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
- Use v0.3.1 patterns consistently

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

*Last updated: September 2025 - Post v0.3.1 release*