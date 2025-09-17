# Zenith v0.3.0 Issues & Findings Report

**Date**: 2025-09-17
**Reporter**: DJScout Production Testing
**Zenith Version**: v0.3.0 (wheel from /Users/nick/github/nijaru/zenith/dist/zenith_web-0.3.0-py3-none-any.whl)
**Test Repository**: github.com/nijaru/djscout

## Executive Summary

During comprehensive testing of Zenith v0.3.0 with the DJScout production application, we identified several issues and discrepancies between documentation, expected behavior, and actual implementation.

**Overall Compatibility**: 85% ✅
**Critical Issues**: 2
**Minor Issues**: 3
**Documentation Discrepancies**: Multiple

## 🔴 Critical Issues

### 1. Missing `/docs` Endpoint Despite CLI Advertising It

**Severity**: High
**Impact**: Developer experience, API exploration

**Description**:
The `zen dev` command output explicitly advertises:
```
📖 Docs:    http://127.0.0.1:8010/docs
```

However, accessing this endpoint returns 404:
```python
>>> requests.get('http://127.0.0.1:8010/docs')
Status: 404
```

**Expected Behavior**: Auto-generated OpenAPI documentation should be available at `/docs`

**Workaround**: None - documentation endpoint completely missing

### 2. Dependency Injection Service Registration Unclear

**Severity**: High
**Impact**: Core framework functionality

**Description**:
The v0.3.0 documentation suggests services extending `Service` base class should be auto-registered, but this doesn't work:

```python
# This pattern fails:
class UserService(Service):
    def __init__(self):
        super().__init__()  # Requires 'container' argument

# Service registration methods tried (all failed):
app.register_service(UserService)  # Method exists but doesn't work
app.contexts.register(UserService)  # AttributeError: no 'contexts'
```

**Current Workaround**: Direct instantiation without DI
```python
# Instead of: users: UserService = Inject()
# We use: users = UserService()
```

## 🟡 Minor Issues

### 3. @paginate Decorator Parameter Injection Issue

**Severity**: Medium
**Impact**: Feature functionality

**Description**:
The `@paginate` decorator injects unexpected parameters causing function signature mismatches:

```python
@paginate(default_limit=20, max_limit=100)
async def get_user_history(pagination: Paginate = Paginate()):
    # Error: get_user_history() got an unexpected keyword argument 'page'
```

### 4. ZENITH_TESTING Environment Variable Not Documented

**Severity**: Low
**Impact**: Testing workflow

**Description**:
Test documentation references `ZENITH_TESTING=true` and `zen dev --testing` but:
- `--testing` flag doesn't exist
- Effect of `ZENITH_TESTING` environment variable is unclear
- No documentation on testing mode configuration

### 5. CLI Commands Inconsistent with Documentation

**Severity**: Low
**Impact**: Developer experience

**Description**:
`TEST_ZENITH_V030.md` suggests only 3 CLI commands (new/dev/serve) but actual CLI has:
- d, dev, info, routes, s, serve, shell, test, version (10 commands)

This suggests documentation refers to unreleased `feature/dx-improvements-v0.3.0` branch.

## 📝 Documentation Discrepancies

### File Upload API Documentation Mismatch
Documentation shows:
```python
file: UploadedFile = File(...)  # UploadedFile type
```

Working implementation:
```python
file = File(...)  # No type annotation needed
```

### Service/Inject Pattern Documentation Missing
No clear documentation on:
- How to properly register services
- When to use `Service` base class vs plain classes
- Correct pattern for dependency injection with v0.3.0

### Rate Limiting Behavior Documentation
- Rate limiting is enabled but doesn't seem to enforce limits
- All 20 concurrent requests returned 400 (bad request) not 429 (too many requests)
- Documentation unclear on rate limit configuration

## ✅ Working Features

Despite issues, these v0.3.0 features work excellently:

1. **@cache decorator** - Perfect caching behavior
2. **@returns decorator** - Auto-404 working as expected
3. **Enhanced File API** - String sizes (`'50MB'`) working great
4. **CLI improvements** - `zen dev` command is excellent
5. **Server startup** - Clean, informative output

## 🎯 Recommendations

### For Zenith Team:

1. **Fix /docs endpoint** - Critical for developer experience
2. **Clarify Service/DI patterns** - Provide clear migration guide
3. **Document testing mode** - Explain ZENITH_TESTING usage
4. **Fix @paginate decorator** - Parameter injection issues
5. **Align documentation** - Clarify which branch/version features belong to

### For DJScout (Current Workarounds):

1. Continue using direct service instantiation (no DI)
2. Avoid @paginate decorator until fixed
3. Use working decorators (@cache, @returns, @rate_limit)
4. Monitor for v0.3.0 patch releases

## Test Verification

All issues verified with:
- Fresh Zenith v0.3.0 wheel installation
- Clean virtual environment
- Multiple test approaches
- Both CLI and programmatic testing

## Reproduction Steps

```bash
# 1. Install Zenith v0.3.0
uv pip install /path/to/zenith_web-0.3.0-py3-none-any.whl

# 2. Start server
zen dev --app app.main:app --port 8010

# 3. Test /docs endpoint
curl http://127.0.0.1:8010/docs  # Returns 404

# 4. Test DI pattern
# See code examples above - Service registration fails
```

## Conclusion

Zenith v0.3.0 shows great promise with excellent decorator patterns and improved developer experience. However, critical issues with documentation endpoint and dependency injection patterns need addressing for production readiness.

**Recommendation**: Continue using v0.3.0 with documented workarounds while awaiting patches for critical issues.

---

*Report generated from production testing of DJScout application*
*Test Date: 2025-09-17*
*Zenith Version: v0.3.0 (standard release, not DX improvements branch)*