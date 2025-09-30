"""
Database models for TaskFlow API.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from pydantic import EmailStr, validator

# ============= USER MODELS =============


class UserBase(SQLModel):
    """Base user model with shared fields."""

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(unique=True, index=True)


class UserCreate(UserBase):
    """Model for creating a new user."""

    password: str = Field(min_length=8)


class UserUpdate(SQLModel):
    """Model for updating a user."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)


class User(UserBase, table=True):
    """Database user model."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    projects: List["Project"] = Relationship(back_populates="owner")
    assigned_tasks: List["Task"] = Relationship(back_populates="assignee")


class UserResponse(UserBase):
    """User response model (no password)."""

    id: int
    is_active: bool
    created_at: datetime


# ============= PROJECT MODELS =============


class ProjectBase(SQLModel):
    """Base project model."""

    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class ProjectCreate(ProjectBase):
    """Model for creating a project."""

    pass


class ProjectUpdate(SQLModel):
    """Model for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_archived: Optional[bool] = None


class Project(ProjectBase, table=True):
    """Database project model."""

    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id")
    is_archived: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = Field(default=None)

    # Relationships
    owner: User = Relationship(back_populates="projects")
    tasks: List["Task"] = Relationship(back_populates="project")


class ProjectResponse(ProjectBase):
    """Project response model."""

    id: int
    owner: UserResponse
    is_archived: bool
    created_at: datetime
    task_count: Optional[int] = None


# ============= TASK MODELS =============


class TaskBase(SQLModel):
    """Base task model."""

    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: int = Field(default=1, ge=1, le=5)
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    """Model for creating a task."""

    project_id: int
    assignee_id: Optional[int] = None


class TaskUpdate(SQLModel):
    """Model for updating a task."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None
    is_completed: Optional[bool] = None


class Task(TaskBase, table=True):
    """Database task model."""

    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id")
    assignee_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_by: int
    is_completed: bool = Field(default=False)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Project = Relationship(back_populates="tasks")
    assignee: Optional[User] = Relationship(back_populates="assigned_tasks")


class TaskResponse(TaskBase):
    """Task response model."""

    id: int
    project: ProjectResponse
    assignee: Optional[UserResponse]
    is_completed: bool
    created_at: datetime


# ============= AUTH MODELS =============


class LoginRequest(SQLModel):
    """Login request model."""

    email: EmailStr
    password: str


class TokenResponse(SQLModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
