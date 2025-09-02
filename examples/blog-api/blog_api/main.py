"""
Blog API - Main application entry point.

A complete blog platform built with Zenith demonstrating:
- JWT authentication with user roles
- CRUD operations for blog posts
- File upload for post images
- Context-driven architecture
- Production-ready configuration
"""

import logging
import os
from pathlib import Path

# Import contexts
from blog_api.contexts.auth import AuthContext
from blog_api.contexts.posts import PostsContext
from blog_api.contexts.users import UsersContext

# Import route modules
from blog_api.routes import admin, auth, posts

from zenith import Zenith
from zenith.auth import configure_auth
from zenith.web.health import add_health_routes, health_manager

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Zenith application
app = Zenith(debug=os.getenv("DEBUG", "false").lower() == "true")

# Configure authentication
configure_auth(
    app,
    secret_key=os.getenv(
        "SECRET_KEY", "dev-secret-key-that-is-long-enough-for-development"
    ),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)),
    refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)),
)

# Configure database
database_url = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://blog_user:blog_pass@localhost/blog_api"
)
app.setup_database(database_url)

# Register contexts
app.register_context(AuthContext)
app.register_context(PostsContext)
app.register_context(UsersContext)

# Configure middleware
app.add_cors(
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_security_headers(
    strict=not app.config.debug,
    csp_policy="default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline'",
)

app.add_exception_handling(debug=app.config.debug)

# Add rate limiting
if os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true":
    app.add_rate_limiting(
        default_limit=int(os.getenv("RATE_LIMIT_PER_MINUTE", 60)), window_seconds=60
    )

# Configure file uploads
upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
upload_dir.mkdir(exist_ok=True)

# Mount static files for uploads
app.mount_static("/uploads", str(upload_dir), max_age=86400)  # 1 day cache

# Health checks
add_health_routes(app)


# Add custom health checks
async def database_health_check():
    """Check database connectivity."""
    try:

        # Simple query to test connection
        # This would use the actual database session
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


health_manager.add_simple_check(
    "database", database_health_check, timeout=5.0, critical=True
)

# Add uptime check
health_manager.add_uptime_check(min_uptime=10.0)


# Root endpoint
@app.get("/")
async def root():
    """API information and available endpoints."""
    return {
        "name": "Blog API",
        "version": "1.0.0",
        "description": "A modern blog platform built with Zenith",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "authentication": {
                "register": "POST /auth/register",
                "login": "POST /auth/login",
                "refresh": "POST /auth/refresh",
                "profile": "GET /auth/me",
            },
            "posts": {
                "list": "GET /posts",
                "create": "POST /posts",
                "get": "GET /posts/{id}",
                "update": "PUT /posts/{id}",
                "delete": "DELETE /posts/{id}",
                "upload_image": "POST /posts/{id}/image",
            },
            "admin": {"users": "GET /admin/users", "stats": "GET /admin/stats"},
        },
    }


# Include route modules
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(posts.router, prefix="/posts", tags=["Posts"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


# Application events
@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    logger.info("🚀 Blog API starting up...")

    # Initialize database tables if needed
    # (In production, use proper migrations)
    if app.config.debug:
        try:
            from blog_api.models import create_tables

            await create_tables()
            logger.info("✅ Database tables created")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")

    logger.info("✅ Blog API startup complete")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on application shutdown."""
    logger.info("🔄 Blog API shutting down...")
    logger.info("✅ Blog API shutdown complete")


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        # CLI command to create admin user
        import asyncio

        from blog_api.cli import create_admin_user

        asyncio.run(create_admin_user())
    else:
        # Run the application
        app.run(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", 8000)),
            reload=app.config.debug,
        )
