# Zenith v0.3.0 Remaining Issues Report

**Reporter**: DJScout Production Testing
**Date**: 2025-09-17
**Zenith Version**: v0.3.0 (fixed release)
**Test Environment**: macOS, Python 3.13, DJScout Cloud Application

## Executive Summary

After applying the fixes documented in TEST_V030_FIXES.md, most critical issues are resolved. However, several issues remain that affect framework usability.

## 🟡 Partially Fixed Issues

### 1. OpenAPI Schema Generation Error
**Severity**: Medium
**Status**: Partially Fixed - /docs works but /openapi.json fails

**Error**:
```
GET /openapi.json returns 400 Bad Request
Error: generate_openapi_spec() got an unexpected keyword argument 'routes'
```

**Expected**: Should return valid OpenAPI JSON schema
**Actual**: Returns 400 error despite /docs endpoint working

**Impact**:
- Third-party API clients cannot fetch schema programmatically
- API documentation tools cannot import schema

### 2. Rate Limit Headers Missing
**Severity**: Low
**Status**: Not Fixed

**Issue**: Rate limiting works but headers are missing
**Missing Headers**:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

**Current Headers on 429**:
```
retry-after: 60
```

**Expected Headers**:
```
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1234567890
retry-after: 60
```

## 🔴 New Issues Found

### 3. @paginate Decorator Parameter Conflicts
**Severity**: Medium
**Status**: Partially Working

**Issue**: The @paginate decorator doesn't handle query parameters correctly when used with Paginate model

**Error Case**:
```python
@app.get("/api/items")
@paginate(default_limit=10)
async def get_items(pagination: Paginate = Paginate()):
    # Fails with 400 when ?page=2&limit=5 provided
```

**Workaround**: Manual pagination without decorator

### 4. SimplifiedService Missing Documentation
**Severity**: Low
**Status**: Documentation Gap

**Issue**: SimplifiedService is the recommended pattern but lacks documentation
- No migration guide from Service to SimplifiedService
- No examples in official docs
- Constructor signature differences not explained

## 📊 Test Results Summary

| Feature | Expected | Actual | Status |
|---------|----------|---------|---------|
| /docs endpoint | 200 OK | 200 OK | ✅ Fixed |
| /openapi.json | 200 OK | 400 Bad Request | ❌ Broken |
| Rate limiting (429) | Works | Works | ✅ Fixed |
| Rate limit headers | Present | Missing | ❌ Not Fixed |
| Service DI | Works | Works | ✅ Fixed |
| @cache decorator | Works | Works | ✅ Fixed |
| @paginate decorator | Works | Partial | ⚠️ Partial |
| OAuth2 expires_in | Present | Present | ✅ Fixed |

## Recommendations for Zenith Team

### High Priority
1. Fix OpenAPI schema generation (`/openapi.json` endpoint)
2. Add comprehensive SimplifiedService documentation
3. Fix @paginate decorator parameter handling

### Medium Priority
4. Add X-RateLimit-* headers to rate limited responses
5. Provide migration guide for Service → SimplifiedService
6. Improve error messages for DI failures

### Low Priority
7. Add type hints for decorator return types
8. Document testing mode behavior (ZENITH_TESTING)

## Reproduction Steps

### OpenAPI Schema Error:
```bash
curl http://localhost:8000/openapi.json
# Returns 400 with error about 'routes' parameter
```

### Missing Rate Limit Headers:
```bash
# Hit rate limited endpoint multiple times
for i in {1..5}; do
  curl -i http://localhost:8000/api/rate-test
done
# Check headers on 429 response - X-RateLimit-* missing
```

### Paginate Decorator Issue:
```bash
curl "http://localhost:8000/api/user/demo/history?page=2&limit=5"
# Returns 400 Bad Request
```

## Working Examples (For Documentation)

### SimplifiedService Pattern:
```python
from zenith import SimplifiedService, Inject

class MyService(SimplifiedService):
    def __init__(self):
        super().__init__()  # No container needed

    async def get_data(self):
        return {"data": "example"}

# Register with app
app.register_service(MyService)

# Use with DI
@app.get("/data")
async def get_data(service: MyService = Inject()):
    return await service.get_data()
```

## Conclusion

Zenith v0.3.0 fixes have resolved the critical issues (DI, basic rate limiting, caching). The remaining issues are mostly edge cases and missing features that don't block production use but would improve developer experience.

**Overall Score**: 85/100 ✅
**Production Ready**: Yes, with workarounds

---
*Generated from production testing with DJScout application*
*Test Date: 2025-09-17*