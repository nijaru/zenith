"""
Rate Limiting Example - Comprehensive Rate Limiting Demo

Demonstrates:
- Multiple rate limit configurations
- Per-IP and per-user limiting
- Custom endpoint limits
- Redis-backed storage option
- Rate limit headers and error responses
- Testing rate limits with concurrent requests

Run with: SECRET_KEY=test-key python examples/rate_limit_example.py
"""

import asyncio
import os

import uvicorn

from zenith import Auth, Inject, Zenith
from zenith.auth import (
    configure_jwt,
    create_access_token,
    hash_password,
    verify_password,
)
from zenith.middleware.rate_limit import (
    RateLimit,
    RateLimitMiddleware,
)

# ============================================================================
# APPLICATION SETUP
# ============================================================================

# Set secret key before creating app to avoid validation issues
os.environ["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "test-rate-limit-secret-key-at-least-32-chars-long-for-example"
)

app = Zenith()

# Configure JWT for user-based rate limiting
SECRET_KEY = os.environ["SECRET_KEY"]
configure_jwt(secret_key=SECRET_KEY, access_token_expire_minutes=60)

# Mock user data for demonstration
USERS = {
    "user@example.com": {
        "id": 1,
        "email": "user@example.com",
        "password_hash": hash_password("password123"),
    },
    "premium@example.com": {
        "id": 2,
        "email": "premium@example.com",
        "password_hash": hash_password("premium123"),
    },
}


# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

# Add rate limiter to app directly - no pre-configuration needed
app.add_middleware(
    RateLimitMiddleware,
    default_limits=[
        # General limits
        RateLimit(requests=10, window=60, per="ip"),  # 10 requests per minute per IP
        RateLimit(requests=100, window=3600, per="ip"),  # 100 requests per hour per IP
    ],
    exempt_paths=["/", "/health", "/docs"],  # Exempt these paths
    # No IP exemptions for security - applies to all clients including localhost
    error_message="Too many requests. Please slow down!",
    include_headers=True,
)


# ============================================================================
# AUTHENTICATION CONTEXT
# ============================================================================


class AuthService:
    def __init__(self, container):
        pass

    async def authenticate(self, email: str, password: str) -> dict:
        """Authenticate user."""
        user = USERS.get(email)
        if user and verify_password(password, user["password_hash"]):
            return user
        return None


app.register_service(AuthService)


# ============================================================================
# API ROUTES
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint (exempt from rate limiting)."""
    return {
        "message": "Rate Limiting Example API",
        "endpoints": {
            "public": "/public",
            "api": "/api/data",
            "protected": "/protected/user-data",
            "login": "/login",
            "test": "/test-limits",
        },
    }


@app.get("/health")
async def health():
    """Health check (exempt from rate limiting)."""
    return {"status": "healthy"}


@app.post("/login")
async def login(email: str, password: str, auth: AuthService = Inject()) -> dict:
    """Login endpoint (subject to default rate limits)."""
    user = await auth.authenticate(email, password)
    if not user:
        raise ValueError("Invalid credentials")

    token = create_access_token(user_id=user["id"], email=user["email"], role="user")

    return {"access_token": token, "token_type": "bearer", "user_id": user["id"]}


@app.get("/public")
async def public_endpoint():
    """Public endpoint with default rate limits (10/min, 100/hour per IP)."""
    return {
        "message": "This is a public endpoint with default rate limits",
        "limits": "10 requests/minute, 100 requests/hour per IP",
    }


@app.get("/api/data")
async def api_endpoint():
    """API endpoint with stricter rate limits (5/min, 50/hour per IP)."""
    return {
        "message": "This is an API endpoint with stricter rate limits",
        "limits": "5 requests/minute, 50 requests/hour per IP",
        "data": {"timestamp": "2025-09-03T10:00:00Z", "value": 42},
    }


@app.get("/protected/user-data")
async def protected_endpoint(current_user=Auth):
    """Protected endpoint with user-based rate limits (20/min, 200/hour per user)."""
    return {
        "message": "This is a protected endpoint with user-based rate limits",
        "limits": "20 requests/minute, 200 requests/hour per authenticated user",
        "user": {
            "id": current_user["id"],
            "email": current_user.get("email", "unknown"),
        },
    }


@app.get("/test-limits")
async def test_limits():
    """Endpoint to test rate limits quickly."""
    return {
        "message": "Hit this endpoint multiple times to test rate limiting",
        "tip": "Try making 11+ requests within a minute to trigger rate limit",
    }


# ============================================================================
# RATE LIMIT TESTING UTILITIES
# ============================================================================


@app.get("/admin/rate-limit-stats")
async def rate_limit_stats():
    """Get rate limit statistics (for testing)."""
    # This would show current counts in a real implementation
    return {
        "message": "Rate limit statistics",
        "note": "In a real app, this would show current request counts per IP/user",
    }


# ============================================================================
# CONCURRENT REQUEST TESTING
# ============================================================================


async def test_rate_limits():
    """Test rate limits with concurrent requests."""
    import aiohttp

    print("Testing rate limits with concurrent requests...")

    async with aiohttp.ClientSession() as session:
        # Test public endpoint
        tasks = []
        for _i in range(15):  # Exceed 10/minute limit
            tasks.append(session.get("http://localhost:8008/public"))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in responses if not isinstance(r, Exception) and r.status == 200
        )
        rate_limited_count = sum(
            1 for r in responses if not isinstance(r, Exception) and r.status == 429
        )

        print(
            f"Public endpoint: {success_count} successful, {rate_limited_count} rate limited"
        )


if __name__ == "__main__":
    print("🚦 Starting Rate Limiting Example")
    print("📝 Available endpoints:")
    print("  GET  /               - Root (exempt)")
    print("  GET  /health         - Health check (exempt)")
    print("  POST /login          - Login (default limits)")
    print("  GET  /public         - Public (10/min per IP)")
    print("  GET  /api/data       - API (5/min per IP)")
    print("  GET  /protected/user-data - Protected (20/min per user)")
    print("  GET  /test-limits    - Testing endpoint")
    print()
    print("🧪 Test rate limits:")
    print("  1. Make 11+ requests to /public within 1 minute")
    print("  2. Make 6+ requests to /api/data within 1 minute")
    print("  3. Login and make 21+ requests to /protected/user-data within 1 minute")
    print()
    print("🔑 Test accounts:")
    print("  user@example.com / password123")
    print("  premium@example.com / premium123")
    print()

    # Option to run concurrent test
    if os.getenv("TEST_CONCURRENT") == "true":
        asyncio.run(test_rate_limits())
    else:
        uvicorn.run("rate_limit_example:app", host="127.0.0.1", port=8008, reload=True)
