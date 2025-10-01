"""
🗄️ Modern Database Todo API - SQLModel + Router Grouping

This example demonstrates modern Zenith database patterns:
- SQLModel for unified Pydantic + SQLAlchemy models
- Repository pattern with generic CRUD operations
- Router grouping for clean API organization
- JWT authentication with protected routes
- Database migrations with async support
- Production-ready patterns

Run with: python examples/09-database-todo-api/app.py
Then visit: http://localhost:8009
"""

import os
from datetime import datetime
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from zenith import Auth, Inject, Router, Service, Zenith, not_found
from zenith.auth import (
    configure_jwt,
    create_access_token,
    hash_password,
    verify_password,
)
from zenith.db import Field, Model, SQLModel

# ============================================================================
# DATABASE SETUP
# ============================================================================

# Database URL with connection pooling
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./todos.db")
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================================
# SQLMODEL MODELS (Unified Pydantic + SQLAlchemy)
# ============================================================================


class Priority(str, Enum):
    """Todo priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Status(str, Enum):
    """Todo status options."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Base models for shared fields
class UserBase(SQLModel):
    """Base model for user fields."""

    email: str = Field(
        unique=True, index=True, max_length=255, description="User email address"
    )
    name: str = Field(max_length=100, description="User full name")


class TodoBase(SQLModel):
    """Base model for todo fields."""

    title: str = Field(max_length=200, description="Todo title")
    description: str | None = Field(default=None, description="Todo description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Todo priority")
    status: Status = Field(default=Status.PENDING, description="Todo status")
    due_date: datetime | None = Field(default=None, description="When todo is due")


# Database models (for table creation)
class User(UserBase, Model, table=True):
    """User database model."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255, description="Hashed password")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When user was created"
    )


class Todo(TodoBase, Model, table=True):
    """Todo database model."""

    __tablename__ = "todos"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(
        foreign_key="users.id", description="ID of the user who owns this todo"
    )
    completed_at: datetime | None = Field(
        default=None, description="When todo was completed"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When todo was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When todo was last updated"
    )


# API models (for request/response)
class UserCreate(UserBase):
    """Model for creating users."""

    password: str = Field(min_length=8, description="User password")


class UserLogin(SQLModel):
    """Model for user login."""

    email: str = Field(description="User email")
    password: str = Field(description="User password")


class UserPublic(UserBase):
    """Public user model for API responses."""

    id: int
    is_active: bool
    created_at: datetime


class TodoCreate(TodoBase):
    """Model for creating todos."""

    pass


class TodoUpdate(SQLModel):
    """Model for updating todos."""

    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    status: Status | None = None
    due_date: datetime | None = None


class TodoPublic(TodoBase):
    """Public todo model for API responses."""

    id: int
    user_id: int
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TokenResponse(SQLModel):
    """JWT token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


# ============================================================================
# BUSINESS LOGIC (Context Pattern with Repository)
# ============================================================================


class UserService(Service):
    """User management business logic with repository pattern."""

    def __init__(self):
        # For demo, create session directly
        # In real apps, inject database session as dependency
        self.session_factory = SessionLocal

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        async with self.session_factory() as session:
            # Check if user already exists
            from sqlalchemy import select

            result = await session.execute(
                select(User).where(User.email == user_data.email)
            )
            if result.scalar_one_or_none():
                raise ValueError(f"User with email {user_data.email} already exists")

            # Create user with hashed password
            user = User(
                **user_data.model_dump(exclude={"password"}),
                password_hash=hash_password(user_data.password),
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user with email/password."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user and verify_password(password, user.password_hash):
                return user
            return None

    async def get_user(self, user_id: int) -> User | None:
        """Get user by ID."""
        async with self.session_factory() as session:
            return await session.get(User, user_id)


class TodoService(Service):
    """Todo management business logic with repository pattern."""

    def __init__(self):
        # For demo, create session directly
        # In real apps, inject database session as dependency
        self.session_factory = SessionLocal

    async def create_todo(self, user_id: int, todo_data: TodoCreate) -> Todo:
        """Create a new todo."""
        async with self.session_factory() as session:
            todo = Todo(
                **todo_data.model_dump(),
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            session.add(todo)
            await session.commit()
            await session.refresh(todo)
            return todo

    async def get_todo(self, todo_id: int, user_id: int) -> Todo | None:
        """Get todo by ID for specific user."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def list_todos(
        self,
        user_id: int,
        status: Status | None = None,
        priority: Priority | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Todo]:
        """List todos for user with optional filtering."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            query = select(Todo).where(Todo.user_id == user_id)

            if status:
                query = query.where(Todo.status == status)
            if priority:
                query = query.where(Todo.priority == priority)

            query = query.order_by(Todo.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def update_todo(
        self, todo_id: int, user_id: int, updates: TodoUpdate
    ) -> Todo | None:
        """Update todo."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
            )
            todo = result.scalar_one_or_none()

            if not todo:
                return None

            # Update fields
            update_data = updates.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(todo, field, value)

            # Update timestamp
            todo.updated_at = datetime.utcnow()

            # Set completion timestamp
            if updates.status == Status.COMPLETED and not todo.completed_at:
                todo.completed_at = datetime.utcnow()
            elif updates.status and updates.status != Status.COMPLETED:
                todo.completed_at = None

            await session.commit()
            await session.refresh(todo)
            return todo

    async def delete_todo(self, todo_id: int, user_id: int) -> bool:
        """Delete todo."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
            )
            todo = result.scalar_one_or_none()

            if todo:
                await session.delete(todo)
                await session.commit()
                return True
            return False


# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = Zenith()

# Configure JWT
SECRET_KEY = os.getenv(
    "SECRET_KEY", "your-super-secure-secret-key-at-least-32-characters-long"
)
configure_jwt(secret_key=SECRET_KEY, access_token_expire_minutes=60)

# Register services for dependency injection
app.register_context("users", UserService)
app.register_context("todos", TodoService)

# ============================================================================
# ROUTER GROUPING FOR CLEAN API ORGANIZATION
# ============================================================================

# API v1 router
api_v1 = Router(prefix="/api/v1")

# Authentication router
auth_router = Router(prefix="/auth")

# Todos router (protected)
todos_router = Router(prefix="/todos")


# ============================================================================
# DATABASE LIFECYCLE
# ============================================================================


@app.on_startup
async def startup():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ Database tables created")


@app.on_shutdown
async def shutdown():
    """Close database connections."""
    await engine.dispose()
    print("✅ Database connections closed")


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================


@auth_router.post("/register", response_model=UserPublic)
async def register(user_data: UserCreate, users: UserService = Inject()) -> UserPublic:
    """Register a new user."""
    user = await users.create_user(user_data)
    return UserPublic.model_validate(user)


@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, users: UserService = Inject()) -> TokenResponse:
    """Login and get access token."""
    user = await users.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise ValueError("Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email, role="user")

    return TokenResponse(access_token=token)


# ============================================================================
# Todo Management Routes (Protected)
# ============================================================================


@todos_router.post("/", response_model=TodoPublic)
async def create_todo(
    todo_data: TodoCreate,
    todos: TodoService = Inject(),
    current_user=Auth,
) -> TodoPublic:
    """Create a new todo."""
    user_id = current_user["id"]
    todo = await todos.create_todo(user_id, todo_data)
    return TodoPublic.model_validate(todo)


@todos_router.get("/", response_model=list[TodoPublic])
async def list_todos(
    status: Status | None = None,
    priority: Priority | None = None,
    limit: int = 100,
    offset: int = 0,
    todos: TodoService = Inject(),
    current_user=Auth,
) -> list[TodoPublic]:
    """List todos for current user with optional filtering and pagination."""
    user_id = current_user["id"]
    todo_list = await todos.list_todos(user_id, status, priority, limit, offset)
    return [TodoPublic.model_validate(todo) for todo in todo_list]


@todos_router.get("/{todo_id}", response_model=TodoPublic)
async def get_todo(
    todo_id: int, todos: TodoService = Inject(), current_user=Auth
) -> TodoPublic:
    """Get specific todo by ID."""
    user_id = current_user["id"]
    todo = await todos.get_todo(todo_id, user_id)
    if not todo:
        not_found(f"Todo {todo_id} not found")
    return TodoPublic.model_validate(todo)


@todos_router.patch("/{todo_id}", response_model=TodoPublic)
async def update_todo(
    todo_id: int,
    updates: TodoUpdate,
    todos: TodoService = Inject(),
    current_user=Auth,
) -> TodoPublic:
    """Update todo with partial data."""
    user_id = current_user["id"]
    todo = await todos.update_todo(todo_id, user_id, updates)
    if not todo:
        not_found(f"Todo {todo_id} not found")
    return TodoPublic.model_validate(todo)


@todos_router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int, todos: TodoService = Inject(), current_user=Auth
) -> dict:
    """Delete todo by ID."""
    user_id = current_user["id"]
    deleted = await todos.delete_todo(todo_id, user_id)
    if not deleted:
        not_found(f"Todo {todo_id} not found")
    return {"message": "Todo deleted successfully"}


# ============================================================================
# UTILITY ROUTES
# ============================================================================


@app.get("/")
async def root():
    """API information and available endpoints."""
    return {
        "message": "Modern Database Todo API 🗄️",
        "version": "1.0.0",
        "features": [
            "SQLModel unified models",
            "Router grouping",
            "Repository pattern",
            "JWT authentication",
            "CRUD operations",
            "Type safety",
        ],
        "endpoints": {
            "auth": "/api/v1/auth",
            "todos": "/api/v1/todos",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    """Health check with database connectivity."""
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e!s}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# INCLUDE ROUTERS WITH GROUPING
# ============================================================================

# Include auth and todos in API v1
api_v1.include_router(auth_router)
api_v1.include_router(todos_router)

# Include API v1 in main app
app.include_router(api_v1)


if __name__ == "__main__":
    print("🗄️ Starting Modern Database Todo API Example")
    print("📍 Server will start at: http://localhost:8009")
    print("🔗 Try these endpoints:")
    print("   GET  /                         - API information")
    print("   POST /api/v1/auth/register     - Register new user")
    print("   POST /api/v1/auth/login        - Login and get JWT token")
    print("   GET  /api/v1/todos             - List todos (requires auth)")
    print("   POST /api/v1/todos             - Create todo (requires auth)")
    print("   GET  /api/v1/todos/{id}        - Get specific todo (requires auth)")
    print("   PATCH /api/v1/todos/{id}       - Update todo (requires auth)")
    print("   DELETE /api/v1/todos/{id}      - Delete todo (requires auth)")
    print("   GET  /health                   - Health check")
    print("📖 Interactive docs: http://localhost:8009/docs")
    print()
    print("🎨 Modern patterns demonstrated:")
    print("   ✨ SQLModel - unified Pydantic + SQLAlchemy models")
    print("   🗂️  Router grouping - clean API organization")
    print("   🏗️  Repository pattern - clean data access")
    print("   🔐 JWT Authentication - secure token-based auth")
    print("   🔒 Type safety - throughout the application")
    print()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8009)
