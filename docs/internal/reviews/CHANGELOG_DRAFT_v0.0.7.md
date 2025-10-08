# Changelog Draft for v0.0.7

## [0.0.7] - 2025-10-08

### Added
- **Python 3.14 Support** - Updated `requires-python` to `>=3.12,<3.15`
  - Added Python 3.14 classifier to pyproject.toml
  - Framework fully compatible with Python 3.14 features
  - Documentation updated to reflect 3.12-3.14 support

- **Security Documentation** - Added comprehensive `docs/security/SECURITY_BEST_PRACTICES.md`
  - Critical warning about `.to_dict()` security risks
  - SECRET_KEY generation and management guide
  - Database security best practices
  - JWT authentication security guidelines
  - CORS configuration for production
  - File upload security patterns
  - Production deployment checklist

### Removed
- **BREAKING**: Removed `.to_dict()` and `.from_dict()` from ZenithModel (security risk)
  - Use `.model_dump()` instead (Pydantic standard method)
  - Recommended: Use explicit Pydantic response models
  - See "Breaking Changes" section below for migration guide

### Changed
- **README Improvements**
  - Fixed example code to use Pydantic models instead of `dict` type hints
  - Added hardware specifications to performance benchmarks (M3 Max, 128GB RAM, Python 3.13)
  - Clarified "zero-config" as "zero-config for development" with production requirements
  - Added `UserCreate` Pydantic model to quick start example

- **Code Quality - Examples**
  - Migrated from `os.path` to `pathlib.Path` throughout examples (31 → 0 errors)
  - Removed deprecated `typing.List/Optional` in favor of built-in `list` and `T | None`
  - Added exception chaining (`raise ... from e`) in 3 locations
  - Fixed all F401 (unused imports) warnings
  - All examples now pass ruff checks with 0 errors

### Updated
- **Dependencies**
  - Upgraded Pydantic from 2.11.9 → 2.12.0
  - Upgraded pydantic-core from 2.33.2 → 2.41.1
  - Upgraded typing-inspection to 0.4.2

- **Documentation**
  - Updated CLAUDE.md with code quality checklist
  - Added pre-release checklist items for linting and formatting
  - Updated Python version references throughout docs

### Quality Metrics
- **Core Framework**: 0 ruff errors ✅
- **Examples**: 0 ruff errors (down from 31)
- **Tests**: 890 passing, 1 skipped ✅
- **Formatting**: 368 files formatted ✅

### Breaking Changes

**BREAKING: Removed `.to_dict()` from ZenithModel**

`.to_dict()` was a security risk - it exposed ALL model fields by default, including passwords, tokens, and other sensitive data.

**Migration:**
```python
# Before (v0.0.6 and earlier)
user = await User.find(123)
return {"user": user.to_dict()}

# After (v0.0.7+) - Use Pydantic's model_dump()
user = await User.find(123)
return {"user": user.model_dump()}

# Better (recommended) - Use explicit response models
from pydantic import BaseModel

class UserPublic(BaseModel):
    id: int
    name: str
    email: str

@app.get("/users/{id}", response_model=UserPublic)
async def get_user(id: int):
    return await User.find_or_404(id)
```

**Why this change:**
- `.to_dict()` exposed all fields by default (security risk)
- Required manual `exclude=` for every call
- Easy to forget and leak sensitive data
- `.model_dump()` is Pydantic's standard method
- Explicit response models force security by design

### Migration Guide

**1. Replace `.to_dict()` with `.model_dump()`:**
```bash
# Find all usages in your codebase:
grep -r "\.to_dict()" .

# Replace with sed (backup first!):
find . -type f -name "*.py" -exec sed -i '' 's/\.to_dict()/.model_dump()/g' {} \;
```

**2. Update dependencies:**
```bash
uv sync  # or pip install --upgrade zenithweb
```

**3. Run tests to verify:**
```bash
pytest
```

### Notes
- Python 3.14 free-threading (no-GIL) is supported but not required or recommended (10% overhead)
- See `ZENITH_ANALYSIS_2025-10-08.md` for detailed Python 3.14 analysis
- Security best practices document addresses concerns from code review

---

## Files Modified in This Release

**Core:**
- `pyproject.toml` - Python 3.14 support, Pydantic 2.12.0
- `README.md` - Example fixes, benchmark specs, clarity improvements
- `CLAUDE.md` - Tool checklist, version updates

**Documentation:**
- `docs/security/SECURITY_BEST_PRACTICES.md` (new)
- `ZENITH_ANALYSIS_2025-10-08.md` (new)

**Examples (pathlib migration):**
- `examples/03-modern-developer-experience.py`
- `examples/04-one-liner-features.py`
- `examples/06-file-upload.py` (5 fixes)
- `examples/09-database-todo-api/alembic/env.py`
- `examples/18-database-sessions.py`
- `examples/19-seamless-integration.py`
- `examples/20-fullstack-spa.py`
- `examples/task-api/app/auth.py`
- `examples/task-api/app/models/__init__.py`
- `examples/task-api/app/services/__init__.py`

**Total Changes:**
- 20 files modified
- 3 files created
- 31 code quality issues fixed
- 1 breaking change (`.to_dict()` removed)
