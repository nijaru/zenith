# Zenith v0.1.4 Roadmap - Critical Fixes

## High Priority - Event Loop Fixes

### Middleware Conversion to Pure ASGI
**Why**: BaseHTTPMiddleware causes event loop conflicts with AsyncPG

**Convert these middleware** (priority order):
1. ✅ RequestIDMiddleware (done in v0.1.3-alpha)
2. 🔴 ExceptionHandlerMiddleware - Critical for error handling
3. 🔴 AuthenticationMiddleware - Security critical
4. 🟡 CORSMiddleware - Common usage
5. 🟡 SecurityHeadersMiddleware - Common usage
6. 🟢 RateLimitMiddleware
7. 🟢 LoggingMiddleware  
8. 🟢 CompressionMiddleware
9. 🟢 CacheMiddleware
10. 🟢 CSRFMiddleware

### Testing Requirements
- AsyncPG integration tests with full middleware stack
- Concurrent request handling tests
- Background task execution tests
- Memory leak tests with long-running connections

## Medium Priority

### Performance
- Benchmark all middleware conversions
- Profile memory usage improvements
- Document performance characteristics

### Documentation
- Update examples to show pure ASGI patterns
- Add AsyncPG integration examples
- Document middleware conversion patterns

## Release Criteria
- All critical middleware converted (1-5)
- AsyncPG tests passing
- No event loop conflicts
- Performance regression tests passing

## Timeline
- Target: 1-2 weeks for full conversion
- Alpha release after critical middleware
- Stable release after all testing