"""
Example Zenith application: Blog API

Demonstrates:
- FastAPI-style routing with type-based dependency injection
- Pydantic models for request/response validation
- Phoenix-style contexts for business logic
- Authentication and authorization

Run with: python examples/blog_api/main.py
"""

from typing import List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import String, Integer, Boolean, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from zenith import Zenith, Router, Context, Auth
from zenith.core.context import Context as BaseContext
from zenith.auth import configure_auth
from zenith.db import Base


# Application-specific models (not part of framework)
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class User(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole = UserRole.USER
    created_at: datetime
    is_active: bool = True


# Application-specific database model
class UserTable(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# Application-specific context (business logic)
class Users(BaseContext):
    async def get_user(self, user_id: int) -> Optional[User]:
        pass  # Implementation would use database

    async def create_user(self, user_data: UserCreate) -> User:
        pass  # Implementation would use database

    async def list_users(self, page: int = 1, per_page: int = 20) -> List[User]:
        pass  # Implementation would use database


# Create application
app = Zenith(debug=True)

# Configure authentication
configure_auth(app, secret_key="your-secret-key-here-use-env-var-in-production")

# Register application context
app.register_context("users", Users)

# Create router
api_router = Router(prefix="/api")


# Routes
@api_router.get("/users/{user_id}")
async def get_user(
    user_id: int, users: Users = Context(), current_user=Auth(required=True)
) -> User:
    user = await users.get_user(user_id)
    if not user:
        from starlette.responses import JSONResponse

        return JSONResponse({"error": "User not found"}, status_code=404)
    return user


@api_router.post("/users")
async def create_user(
    user_data: UserCreate,
    users: Users = Context(),
    current_user=Auth(required=True, scopes=["admin"]),
) -> User:
    return await users.create_user(user_data)


@api_router.get("/users")
async def list_users(
    page: int = 1, per_page: int = 20, users: Users = Context()
) -> List[User]:
    return await users.list_users(page=page, per_page=per_page)


# Public health check
@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "blog-api"}


# Include routes
app.include_router(api_router)

# Add documentation
app.add_docs(
    title="Blog API", description="Example blog API built with Zenith framework"
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)
