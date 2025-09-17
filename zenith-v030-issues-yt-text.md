# Zenith v0.3.0 Issues Report

## Critical Issues Found During Production Testing

### 1. Rate Limiting Not Working ❌
**Severity**: HIGH
**Description**: Rate limiting decorators are applied but not enforcing any limits
```python
@app.get("/api/endpoint")
@rate_limit("5/minute")  # Does NOT limit requests
async def endpoint():
    return {"status": "ok"}
```
**Test Result**: Made 15+ consecutive requests without receiving 429 response
**Impact**: API abuse protection completely non-functional
**Workaround**: Must implement manual rate limiting until fixed

### 2. OpenAPI Spec Generation Broken ❌
**Severity**: MEDIUM
**Error**: `TypeError: generate_openapi_spec() got an unexpected keyword argument 'routes'`
**Endpoint**: `/openapi.json` returns 400 Bad Request
**Impact**: Cannot generate OpenAPI specification for API clients
**Note**: `/docs` endpoint works but `/openapi.json` fails

### 3. Auth Decorator Syntax Issue ⚠️
**Severity**: MEDIUM
**Problem**: Documentation shows `@auth_required` but requires `@auth_required()`
```python
# Documentation shows:
@auth_required  # WRONG - causes TypeError

# Actually requires:
@auth_required()  # Correct - needs parentheses
```
**Error**: `TypeError: auth_required.<locals>.decorator() missing 1 required positional argument: 'func'`
**Impact**: Confusing migration, breaks existing code

### 4. OAuth2 Response Non-Compliant ❌
**Severity**: MEDIUM
**Issue**: Missing `expires_in` field in authentication response
**Expected**:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```
**Actual**: `expires_in` field missing
**Impact**: OAuth2 clients may fail

### 5. User Registration Returns Wrong Status Code ⚠️
**Severity**: LOW
**Issue**: POST /auth/register returns 200 instead of 201
**Expected**: 201 Created for new resource creation
**Actual**: 200 OK
**Impact**: RESTful API compliance issue

### 6. CSV Upload Returns 400 Error ❌
**Severity**: MEDIUM
**Endpoint**: POST /portfolios/import/csv
**Error**: Returns 400 Bad Request even with valid CSV
**Impact**: File upload functionality broken for certain endpoints

### 7. Rate Limit Headers Missing ❌
**Severity**: LOW
**Issue**: X-RateLimit-* headers not included in responses
**Expected Headers**:
- X-RateLimit-Limit
- X-RateLimit-Remaining
- X-RateLimit-Reset
**Impact**: Clients cannot track rate limit status

## Working Features ✅

### Caching System
- **Performance**: 421x improvement verified
- **TTL**: Respects configured time-to-live
- **Consistency**: Returns identical cached responses

### Testing Mode
- **Environment**: ZENITH_TESTING=true works
- **Effect**: Properly disables rate limiting for tests
- **Note**: Requires app restart

### API Documentation
- **Swagger UI**: /docs endpoint functional
- **Interactive**: Can test endpoints from UI

### File Size Validation
- **Working**: Rejects files exceeding size limits
- **Response**: Proper 400 error for oversized files

## Test Environment
- **Zenith Version**: 0.3.0 (installed from local path)
- **Python**: 3.12
- **Application**: WealthScope (Financial platform)
- **Database**: PostgreSQL

## Reproduction Steps

### Rate Limiting Test
```python
# This should limit to 5 requests per minute but doesn't
for i in range(15):
    response = await client.get("/performance/test")
    print(f"Request {i+1}: {response.status_code}")
    # All return 200, none return 429
```

### OpenAPI Error
```bash
curl http://localhost:8000/openapi.json
# Returns 400 with TypeError in logs
```

### Auth Decorator Issue
```python
# This fails with TypeError
@app.get("/protected")
@auth_required  # Missing parentheses
async def protected():
    pass
```

## Recommendations for Zenith Team

### Immediate Fixes Required
1. Fix rate limiting middleware initialization
2. Update generate_openapi_spec() parameters
3. Add expires_in to auth responses
4. Fix decorator documentation

### Documentation Updates Needed
1. Clarify decorator syntax (with/without parentheses)
2. Add troubleshooting guide for common issues
3. Include working examples for all decorators
4. Document rate limiting setup requirements

### Testing Improvements
1. Add integration tests for rate limiting
2. Test OAuth2 compliance
3. Verify all decorator combinations
4. Test file upload with various content types

## Impact on Production

**Can Deploy**: YES, with workarounds
**Production Ready**: 70%
**Critical Features Missing**: Rate limiting

### Required Workarounds
1. Implement manual rate limiting
2. Use /docs instead of /openapi.json
3. Add parentheses to all decorators
4. Add expires_in manually to auth responses

---
*Report Date: 2025-09-17*
*Framework: Zenith v0.3.0*
*Status: Partially functional, critical issues remain*