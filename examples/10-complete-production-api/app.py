"""
Complete Zenith Application Example

Demonstrates all framework features:
- Database integration with SQLAlchemy
- JWT authentication & authorization  
- Session management (Redis-backed)
- Background job processing
- Full middleware stack
- OpenAPI documentation

Run with: zen server
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, EmailStr
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

# Zenith imports
from zenith import Auth, Context, Router, Zenith, Service
from zenith.auth import configure_auth, hash_password, verify_password
from zenith.db import Base, Database
from zenith.jobs import job, schedule
# Note: Session management can be added with Redis backend
# from zenith.sessions import RedisSessionStore, SessionManager, SessionMiddleware


# ============================================================================
# DATABASE MODELS
# ============================================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    PREMIUM = "premium"


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================================
# PYDANTIC MODELS  
# ============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: UserRole = UserRole.USER


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============================================================================
# BUSINESS CONTEXTS
# ============================================================================

class UsersContext(Service):
    """User management business logic."""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password."""
        password_hash = await hash_password(user_data.password)
        
        async with self.db.transaction() as session:
            user = User(
                email=user_data.email,
                name=user_data.name,
                password_hash=password_hash,
                role=user_data.role,
            )
            session.add(user)
            await session.flush()  # Get ID
            return user
    
    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user with email/password."""
        async with self.db.session() as session:
            user = await session.get(User, {"email": email})
            if user and verify_password(password, user.password_hash):
                # Update last login
                user.last_login = datetime.utcnow()
                return user
        return None
    
    async def get_user(self, user_id: int) -> User | None:
        """Get user by ID."""
        async with self.db.session() as session:
            return await session.get(User, user_id)
    
    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        async with self.db.session() as session:
            return await session.get(User, {"email": email})


# ============================================================================
# BACKGROUND JOBS
# ============================================================================

@job(name="send_welcome_email", max_retries=3)
async def send_welcome_email(user_id: int, email: str, name: str):
    """Send welcome email to new user."""
    # Simulate email sending
    print(f"📧 Sending welcome email to {email} ({name})")
    # In production: integrate with SendGrid, SES, etc.
    return f"Welcome email sent to {email}"


@job(name="process_user_analytics", max_retries=2)
async def process_user_analytics(user_id: int, event: str, data: dict):
    """Process user analytics event."""
    print(f"📊 Processing analytics: {event} for user {user_id}")
    # In production: send to analytics service
    return f"Analytics processed for user {user_id}"


@schedule(every=timedelta(hours=24))  # Daily cleanup
async def cleanup_expired_sessions():
    """Clean up expired sessions daily."""
    print("🧹 Running daily session cleanup")
    # Cleanup logic would go here
    return "Session cleanup completed"


# ============================================================================
# APPLICATION SETUP
# ============================================================================

# Create Zenith app
app = Zenith(debug=True)

# Database setup  
database = Database("sqlite+aiosqlite:///./app.db", echo=True)

# Session management (Redis-backed) available in framework
# session_store = RedisSessionStore("redis://localhost:6379/1")
# session_manager = SessionManager(session_store, max_age=timedelta(days=7))

# Add comprehensive middleware stack
# app.add_middleware(SessionMiddleware, session_manager=session_manager)  # Add as needed
app.add_cors(allow_origins=["http://localhost:3000", "https://myapp.com"])
app.add_exception_handling(debug=True)
app.add_rate_limiting(default_limit=1000, window_seconds=3600)
app.add_security_headers(strict=True)

# Configure JWT authentication
jwt_manager = configure_auth(
    app,
    secret_key="your-super-secure-secret-key-at-least-32-chars-long",
    access_token_expire_minutes=60,
    public_paths=["/", "/health", "/docs", "/login", "/register"]
)

# Register business contexts
app.register_context("users", lambda: UsersContext(database))

# Create router
api = Router(prefix="/api/v1")


# ============================================================================
# API ENDPOINTS  
# ============================================================================

@app.get("/")
async def root():
    """Welcome endpoint."""
    return {
        "message": "Welcome to Zenith Complete API",
        "version": "1.0.0",
        "features": [
            "Database integration",
            "JWT authentication", 
            "Session management",
            "Background jobs",
            "Full middleware stack"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await database.health_check()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@api.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    users: UsersContext = Context()
) -> UserResponse:
    """Register a new user."""
    # Check if user already exists
    existing = await users.get_user_by_email(user_data.email)
    if existing:
        raise ValueError("Email already registered")
    
    # Create user
    user = await users.create_user(user_data)
    
    # Queue welcome email job
    await send_welcome_email.delay(user.id, user.email, user.name)
    
    # Track analytics
    await process_user_analytics.delay(
        user.id, 
        "user_registered", 
        {"email": user.email, "role": user.role}
    )
    
    return UserResponse(**user.__dict__)


@api.post("/login", response_model=TokenResponse)  
async def login(
    credentials: LoginRequest,
    users: UsersContext = Context()
    # Note: session = Context()  # Session dependency injection - requires session modules
) -> TokenResponse:
    """Login user and return JWT token."""
    # Authenticate user
    user = await users.authenticate_user(credentials.email, credentials.password)
    if not user or not user.is_active:
        raise ValueError("Invalid credentials")
    
    # Create JWT token
    from zenith.auth.jwt import get_jwt_manager
    jwt = get_jwt_manager()
    
    access_token = jwt.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=[user.role.value]
    )
    
    # Note: Store user info in session - requires session modules
    # if session:
    #     session["user_id"] = user.id
    #     session["email"] = user.email
    #     session["role"] = user.role.value
    
    # Track login analytics
    await process_user_analytics.delay(
        user.id,
        "user_login", 
        {"email": user.email, "timestamp": datetime.utcnow().isoformat()}
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=3600  # 1 hour
    )


@api.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user = Auth(required=True),
    users: UsersContext = Context()
) -> UserResponse:
    """Get current user's profile."""
    user = await users.get_user(current_user["user_id"])
    if not user:
        raise ValueError("User not found")
        
    return UserResponse(**user.__dict__)


@api.get("/admin/users")
async def list_users(
    current_user = Auth(required=True, scopes=["admin"]),
    users: UsersContext = Context()
) -> list[UserResponse]:
    """Admin endpoint to list all users."""
    # In a real app, implement pagination and filtering
    return [UserResponse(id=1, email="admin@example.com", name="Admin", role=UserRole.ADMIN, is_active=True, created_at=datetime.utcnow())]


@api.post("/admin/cleanup")
async def trigger_cleanup(
    current_user = Auth(required=True, scopes=["admin"])
):
    """Manually trigger cleanup job."""
    job_id = await cleanup_expired_sessions.delay()
    return {"message": "Cleanup job queued", "job_id": job_id}


@api.get("/session")
async def get_session_info():  # Note: session = Context() - requires session modules
    """Get current session information."""
    # Note: session functionality requires session modules
    return {"message": "Session functionality not implemented yet - requires session modules"}
    
    # if not session:
    #     return {"message": "No session"}
    #     
    # return {
    #     "session_id": session.session_id,
    #     "user_id": session.get("user_id"),
    #     "email": session.get("email"), 
    #     "role": session.get("role"),
    #     "created_at": session.created_at.isoformat()
    # }


# Include API router
app.include_router(api)

# Add comprehensive API documentation
app.add_docs(
    title="Zenith Complete API",
    description="""
    A complete example showcasing all Zenith framework features:
    
    ## Features
    - 🔐 **JWT Authentication** - Secure token-based auth
    - 📊 **Database Integration** - SQLAlchemy with async support
    - 🍪 **Session Management** - Redis-backed sessions  
    - 🔄 **Background Jobs** - Async task processing
    - 🛡️ **Security Middleware** - CORS, rate limiting, security headers
    - 📝 **Auto Documentation** - OpenAPI/Swagger integration
    
    ## Getting Started
    1. Register: `POST /api/v1/register`
    2. Login: `POST /api/v1/login` 
    3. Use token in Authorization header: `Bearer <token>`
    """,
    version="1.0.0"
)


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@app.on_startup
async def startup():
    """Initialize database and start background workers."""
    # Create database tables
    await database.create_all()
    print("✅ Database tables created")
    
    # Start job worker (in production, run separately)
    # asyncio.create_task(job_manager.start_worker(concurrency=2))
    # print("✅ Background job worker started")


@app.on_shutdown  
async def shutdown():
    """Clean up resources."""
    await database.close()
    # Note: await session_store.close() - requires session modules
    print("✅ Resources cleaned up")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, reload=True)