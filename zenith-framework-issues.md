# Zenith Framework Issues - Found During WealthScope Migration

## Overview
During the migration of WealthScope from Zenith v0.2.7 to v0.3.0, several framework issues and unclear patterns were discovered. These impact developer experience and migration efficiency.

## High Priority Issues

### 1. **Unclear File Upload Patterns**
**Issue**: Migration guide shows new file upload syntax but actual implementation unclear.

**Migration Guide Shows**:
```python
from zenith import File, UploadedFile, IMAGE_TYPES

file: UploadedFile = File(
    max_size="10MB",
    allowed_types=IMAGE_TYPES
)
```

**Problems Encountered**:
- `File()` constructor parameters not documented
- `max_size` string format unclear ("10MB", "5MB" - what formats are valid?)
- `allowed_extensions` parameter not mentioned in guide
- Interaction with `@validate` decorator unclear

**Actual Working Pattern**:
```python
file: UploadedFile = File(max_size="5MB", allowed_extensions=[".csv"])
```

### 2. **@validate Decorator Usage Unclear**
**Issue**: Migration guide mentions `@validate` but doesn't show proper usage patterns.

**Questions**:
- How to validate Pydantic models with `@validate`?
- What should the parameter be? `@validate(UserCreate)` or `@validate(None)`?
- How does it interact with existing Pydantic model injection?

**Current Workaround**:
```python
@validate(PortfolioCreate)  # Guessing based on model
# or
@validate(None)  # For file uploads?
```

### 3. **CurrentUser Dependency Injection Documentation**
**Issue**: `CurrentUser` pattern works but lacks comprehensive documentation.

**Working Pattern**:
```python
@auth_required
async def endpoint(user=CurrentUser):
    # user is automatically injected
    return user.id
```

**Missing Documentation**:
- What attributes does `CurrentUser` provide? (id, email, etc.)
- How to handle authentication failures?
- How to access user roles/permissions?
- Relationship with existing auth functions

### 4. **Rate Limiting Syntax Questions**
**Issue**: Rate limiting works but optimal patterns unclear.

**Working Examples**:
```python
@rate_limit("100/minute")  # Works
@rate_limit("20/hour")     # Works
@rate_limit("1000/hour")   # Works
```

**Questions**:
- What time units are supported? (second, minute, hour, day?)
- How to set different limits per user role?
- How to handle rate limit exceeded responses?
- Per-endpoint vs global limits?

## Medium Priority Issues

### 5. **Transaction Decorator Behavior**
**Issue**: `@transaction` decorator added but behavior not documented.

**Questions**:
- Does it automatically rollback on exceptions?
- Can it be nested with manual transaction handling?
- Performance impact on simple operations?

### 6. **Cache Decorator Advanced Usage**
**Issue**: Basic caching works but advanced patterns unclear.

**Working**:
```python
@cache(ttl=300)  # 5 minutes
```

**Missing**:
- Cache key customization
- Cache invalidation patterns
- Memory usage concerns
- Cache backends (Redis, memory, etc.)

### 7. **Pagination Response Format**
**Issue**: `PaginatedResponse.create()` works but format not documented.

**Current Usage**:
```python
return PaginatedResponse.create(
    items=paginated_items,
    page=pagination.page,
    limit=pagination.limit,
    total=len(items)
)
```

**Questions**:
- What's the exact response JSON format?
- How to add metadata (next_page, prev_page urls)?
- Custom pagination parameters?

## Low Priority Issues

### 8. **@returns Decorator Edge Cases**
**Issue**: `@returns(Model)` auto-404 works but edge cases unclear.

**Questions**:
- What happens with List[Model] when list is empty?
- Custom 404 messages?
- Other HTTP status codes (403, 500)?

### 9. **Decorator Order Requirements**
**Issue**: Multiple decorators work but optimal order not documented.

**Current Working Order**:
```python
@app.get("/endpoint")
@auth_required
@cache(ttl=60)
@rate_limit("100/hour")
@paginate()
@returns(Model)
async def endpoint():
    pass
```

**Questions**:
- Is decorator order important?
- Performance implications of different orders?
- Required vs optional decorator combinations?

## Migration Process Issues

### 10. **Bulk Pattern Replacement**
**Issue**: Migrating large codebases requires manual endpoint updates.

**Current Process**:
- 32+ endpoints need `user_id: int = 1` → `user=CurrentUser` replacement
- 40+ endpoints need decorator additions
- Manual testing required for each

**Suggestion**:
- CLI tool for pattern detection/replacement
- Migration validation command
- Automated testing helpers

## Framework Strengths Observed

### What Works Well
1. **Decorator Performance**: No noticeable performance regression
2. **Type Safety**: Pydantic integration seamless
3. **Error Messages**: Better than v0.2.x in most cases
4. **Async Support**: Excellent async/await throughout
5. **Development Experience**: Overall improvement when patterns are clear

## Recommendations for Framework Team

### Immediate (Next Release)
1. **Comprehensive Migration Examples**: Real-world endpoint examples
2. **File Upload Documentation**: Complete parameter reference
3. **@validate Decorator Guide**: Clear usage patterns
4. **CurrentUser Documentation**: Complete API reference

### Short Term
1. **CLI Migration Tool**: Automated pattern detection/replacement
2. **Decorator Reference**: Complete decorator interaction guide
3. **Rate Limiting Guide**: Advanced configuration options
4. **Performance Tuning Guide**: Cache/rate limit optimization

### Long Term
1. **Interactive Migration Tool**: Step-by-step guidance
2. **Framework Testing Helpers**: Automated migration validation
3. **Plugin System**: Custom decorator development

## Testing Status

### Successful Patterns
- ✅ Basic decorators (@cache, @rate_limit, @auth_required)
- ✅ CurrentUser dependency injection
- ✅ Pagination with PaginatedResponse
- ✅ File uploads with basic parameters
- ✅ Error handling with returns decorator

### Needs More Testing
- ❓ Complex file upload validations
- ❓ Nested transaction handling
- ❓ Advanced caching patterns
- ❓ Rate limiting edge cases
- ❓ Performance under load

## Impact on Migration

### Current Status
- **Migration Progress**: ~30% complete (slowed by unclear patterns)
- **Time Impact**: 2-3x longer than expected due to documentation gaps
- **Developer Experience**: Good when patterns work, frustrating when unclear

### Completion Estimate
- **With Current Documentation**: 6-8 hours remaining
- **With Improved Documentation**: 2-3 hours remaining
- **With CLI Tool**: 1 hour remaining

---
*Reported by: WealthScope Migration Team*
*Date: 2025-09-16*
*Zenith Version: 0.3.0*
*Migration Context: Production application with 50+ endpoints*