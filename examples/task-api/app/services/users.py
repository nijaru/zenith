"""
User service for authentication and user management.
"""

from datetime import datetime

from sqlmodel import func, or_, select

from app.auth import create_access_token, hash_password, verify_password
from app.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionError,
    ValidationError,
)
from app.models import User, UserCreate, UserUpdate
from app.services import BaseService


class UserService(BaseService):
    """Handles user operations and authentication."""

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with validation."""
        # Check if email already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await self.session.exec(stmt)
        existing = result.first()
        if existing:
            raise ConflictError(f"Email {user_data.email} is already registered")

        # Validate password strength
        if len(user_data.password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        # Create user with hashed password
        user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
        )

        self.session.add(user)
        await self.commit()
        await self.session.refresh(user)

        return user

    async def get_user(self, user_id: int) -> User:
        """Get user by ID or raise NotFoundError."""
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email for authentication."""
        stmt = select(User).where(User.email == email)
        result = await self.session.exec(stmt)
        return result.first()

    async def list_users(
        self, skip: int = 0, limit: int = 100, search: str | None = None
    ) -> tuple[list[User], int]:
        """List users with pagination and search."""
        # Build base query
        query = select(User).where(User.is_active)

        # Add search filter if provided
        if search:
            query = query.where(
                or_(User.name.contains(search), User.email.contains(search))
            )

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute and return
        result = await self.session.exec(query)
        users = result.all()

        return users, total

    async def update_user(
        self, user_id: int, user_update: UserUpdate, current_user_id: int
    ) -> User:
        """Update user with permission check."""
        # Check permissions
        if user_id != current_user_id:
            raise PermissionError("You can only update your own profile")

        # Get existing user
        user = await self.get_user(user_id)

        # Update fields if provided
        update_data = user_update.model_dump(exclude_unset=True)

        # Handle password update separately
        if "password" in update_data:
            password = update_data.pop("password")
            if password and len(password) >= 8:
                user.password_hash = hash_password(password)

        # Update other fields
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()

        await self.commit()
        await self.session.refresh(user)

        return user

    async def delete_user(self, user_id: int, current_user_id: int) -> bool:
        """Soft delete a user."""
        if user_id != current_user_id:
            raise PermissionError("You can only delete your own account")

        user = await self.get_user(user_id)

        # Soft delete
        user.is_active = False
        user.deleted_at = datetime.utcnow()

        await self.commit()
        return True

    async def authenticate(self, email: str, password: str) -> dict | None:
        """Authenticate user and return tokens."""
        user = await self.get_user_by_email(email)

        if not user or not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Generate JWT token
        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

        return {"access_token": access_token, "token_type": "bearer", "user": user}
