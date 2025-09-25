# Rate Limiting Security Best Practices

## Default Behavior (v0.0.2+)

**No default exemptions** - All endpoints are rate limited by default for maximum security.

## Operational Endpoints

For production deployments, consider these patterns:

### 1. Separate Rate Limits (Recommended)
```python
# Higher limits for operational endpoints, not exemptions
from zenith.middleware.rate_limit import RateLimit, RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, default_limits=[
    RateLimit(requests=100, window=60, per="ip")  # Regular endpoints
])

# Add endpoint-specific higher limits
rate_limit_middleware = app.middleware[-1]  # Get the rate limit middleware
rate_limit_middleware.add_endpoint_limit("/health", [
    RateLimit(requests=1000, window=60, per="ip")  # Higher limit, not exempt
])
```

### 2. Environment-Specific Configuration
```python
# Only exempt in development, never in production
exempt_paths = []
if app.environment == "development":
    exempt_paths = ["/health", "/docs"]

app.add_middleware(RateLimitMiddleware,
    default_limits=[RateLimit(requests=100, window=60, per="ip")],
    exempt_paths=exempt_paths
)
```

### 3. Authentication for Sensitive Ops
```python
# Require authentication for sensitive operational endpoints
@app.get("/metrics")
async def metrics(user: Auth = require_admin):  # Admin only
    return prometheus_metrics()
```

## Security Considerations

### ❌ **Never Exempt These in Production:**
- `/metrics` - Reveals system internals
- `/admin/*` - Administrative functions
- `/health/detailed` - May expose sensitive system state

### ✅ **Safe to Higher-Limit (not exempt):**
- `/health` - Basic health checks (with higher limits, not exemptions)
- `/docs` - OpenAPI documentation (cached, lower resource impact)

### 🔒 **Production Recommendations:**
1. **No blanket exemptions** - Use higher limits instead
2. **Monitor operational endpoints** - Watch for abuse patterns
3. **Authentication for sensitive ops** - Protect `/metrics`, `/admin`
4. **Load balancer health checks** - Configure external health checking
5. **Separate rate limit tiers** - Different limits for different endpoint types

## Migration from v0.0.1

If upgrading from v0.0.1, operational endpoints will now be rate limited. To maintain compatibility:

```python
# Temporary migration - add higher limits, not exemptions
rate_middleware.add_endpoint_limit("/health", [
    RateLimit(requests=1000, window=60, per="ip")
])
```

**Recommendation**: Review your operational endpoint usage and implement proper rate limiting strategy rather than exemptions.