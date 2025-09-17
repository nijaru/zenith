# Zenith v0.3.0 Production Testing Guide

## Quick Test Commands

Test the key improvements from v0.3.0 in your production repository:

```bash
# 1. Update to latest Zenith (from nijaru/zenith directory)
cd ../nijaru/zenith
git checkout feature/dx-improvements-v0.3.0

# 2. Install in your project (from your project directory)
pip install -e ../nijaru/zenith

# 3. Test the new CLI commands
zen --version  # Should show version
zen --help     # Should only show new/dev/serve commands

# 4. Test zen dev with testing mode
ZENITH_TESTING=true zen dev  # Should disable rate limiting
zen dev --testing            # Alternative: use flag

# 5. Test enhanced app discovery
zen dev  # Should show better error messages if no app found
```

## Critical Changes to Test

### 1. Testing Mode (Prevents 429 Errors)
```python
# In your test setup (conftest.py or test files)
import os
os.environ["ZENITH_TESTING"] = "true"

# Or when creating app
from zenith import Zenith
app = Zenith(testing=True)  # Disables rate limiting
```

### 2. Model Changes (ZenithSQLModel → Model)
```python
# OLD (will break)
from zenith.db import ZenithSQLModel
class User(ZenithSQLModel, table=True):
    pass

# NEW (correct)
from zenith import Model
from sqlmodel import Field

class User(Model, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
```

### 3. Simplified Auth Dependency
```python
# OLD (will break)
from zenith import Auth
@app.get("/protected")
async def protected(user=Auth(required=True)):
    pass

# NEW (correct)
from zenith import Auth
@app.get("/protected")
async def protected(user=Auth):  # Simple, no parentheses
    pass
```

### 4. Removed CLI Commands
These commands NO LONGER EXIST:
- ❌ `zen version` → Use `zen --version`
- ❌ `zen info` → Removed
- ❌ `zen routes` → Use `/docs` endpoint
- ❌ `zen test` → Use `pytest` directly
- ❌ `zen shell` → Use standard Python REPL
- ❌ `zen d` → Use `zen dev`
- ❌ `zen s` → Use `zen serve`

### 5. File Upload API Changes
```python
from zenith import File, UploadedFile, IMAGE_TYPES, MB

@app.post("/upload")
async def upload_file(
    file: UploadedFile = File(
        max_size="10MB",  # String sizes now supported
        allowed_types=IMAGE_TYPES  # Predefined constants
    )
):
    return {"filename": file.filename}
```

## Test Scenarios

### Scenario 1: Run Existing Tests
```bash
# This should work WITHOUT 429 errors
ZENITH_TESTING=true pytest -v

# Or set in your test file
import os
os.environ["ZENITH_TESTING"] = "true"
```

### Scenario 2: Development Server
```bash
# Test new app discovery
zen dev  # Better error messages if no app

# Test with testing flag
zen dev --testing  # For running tests

# Test explicit app path
zen dev --app mymodule:app
```

### Scenario 3: Create New Project
```bash
# Test simplified project generation
zen new testapp
cd testapp
zen dev  # Should start immediately
```

## Expected Results

✅ **PASS**: Tests run without 429 Too Many Requests errors
✅ **PASS**: `zen dev --testing` disables rate limiting
✅ **PASS**: Better error messages when app not found
✅ **PASS**: Only 3 CLI commands (new, dev, serve)
✅ **PASS**: Model imports work with new syntax

❌ **FAIL**: Using ZenithSQLModel (removed)
❌ **FAIL**: Using Auth(required=True) (simplified)
❌ **FAIL**: Using old CLI commands (removed)

## Migration Checklist

- [ ] Update imports: `ZenithSQLModel` → `Model`
- [ ] Update Auth usage: Remove parentheses
- [ ] Add primary keys to Model classes
- [ ] Set `ZENITH_TESTING=true` for test suites
- [ ] Update CLI usage to new commands only
- [ ] Remove references to deleted CLI commands

## Rollback if Needed

```bash
# If issues occur, rollback to previous version
cd ../nijaru/zenith
git checkout main
pip install -e ../nijaru/zenith
```

## Report Results

After testing, note any issues:

1. **DJScout Results**:
   - [ ] Tests pass with ZENITH_TESTING=true
   - [ ] zen dev --testing works
   - [ ] No import errors

2. **finterm Results**:
   - [ ] Tests pass with ZENITH_TESTING=true
   - [ ] zen dev --testing works
   - [ ] No import errors

3. **yt-text Results**:
   - [ ] Tests pass with ZENITH_TESTING=true
   - [ ] zen dev --testing works
   - [ ] No import errors

---

**Testing Date**: $(date)
**Zenith Version**: v0.3.0 (feature/dx-improvements-v0.3.0)
**Tester**: Production validation