---
title: Database Integration
description: Work with databases using SQLAlchemy and async support
---

import { Tabs, TabItem, Code, Aside } from '@astrojs/starlight/components';

## Overview

Zenith provides seamless database integration with async SQLAlchemy, automatic migrations, and connection pooling. It supports PostgreSQL, MySQL, SQLite, and other SQL databases.

## Quick Start

```python
from zenith import Zenith
from zenith.db import SQLModel, Field, create_engine, Session
from sqlmodel import select
from typing import Optional
from datetime import datetime

# Create engine
engine = create_engine("postgresql://user:pass@localhost/dbname")

app = Zenith()

# Define models
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Create tables on startup
@app.on_event("startup")
async def startup():
    SQLModel.metadata.create_all(engine)

# Use in routes
@app.post("/users")
async def create_user(user: User, session: Session = Depends(get_session)):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
```

## Database Configuration

### Connection URLs

<Tabs>
  <TabItem label="PostgreSQL">
    ```python
    # Standard
    DATABASE_URL = "postgresql://user:password@localhost/dbname"
    
    # Async with asyncpg
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
    
    # With options
    DATABASE_URL = "postgresql://user:pass@localhost/db?sslmode=require"
    ```
  </TabItem>
  <TabItem label="MySQL">
    ```python
    # Standard
    DATABASE_URL = "mysql://user:password@localhost/dbname"
    
    # Async with aiomysql
    DATABASE_URL = "mysql+aiomysql://user:password@localhost/dbname"
    
    # With charset
    DATABASE_URL = "mysql://user:pass@localhost/db?charset=utf8mb4"
    ```
  </TabItem>
  <TabItem label="SQLite">
    ```python
    # File database
    DATABASE_URL = "sqlite:///./app.db"
    
    # Async with aiosqlite
    DATABASE_URL = "sqlite+aiosqlite:///./app.db"
    
    # In-memory (testing)
    DATABASE_URL = "sqlite:///:memory:"
    ```
  </TabItem>
</Tabs>

### Connection Pooling

```python
from zenith.db import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Number of connections
    max_overflow=40,        # Maximum overflow connections
    pool_timeout=30,        # Timeout for getting connection
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Test connections before using
    echo=False              # Set True for SQL logging
)
```

## Models with SQLModel

SQLModel combines SQLAlchemy and Pydantic for type-safe database models:

### Basic Model

```python
from zenith.db import SQLModel, Field
from typing import Optional
from datetime import datetime

class Product(SQLModel, table=True):
    """Product model."""
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Required fields
    name: str = Field(index=True)
    price: float = Field(ge=0)  # Greater than or equal to 0
    
    # Optional fields
    description: Optional[str] = None
    stock: int = Field(default=0, ge=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Unique constraint
    sku: str = Field(unique=True, index=True)
```

### Relationships

```python
from sqlmodel import Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True)
    name: str
    
    # One-to-many relationship
    posts: list["Post"] = Relationship(back_populates="author")

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    
    # Foreign key
    author_id: int = Field(foreign_key="user.id")
    
    # Relationship
    author: User = Relationship(back_populates="posts")
    
    # Many-to-many through link table
    tags: list["Tag"] = Relationship(
        back_populates="posts",
        link_model="PostTag"
    )

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    
    posts: list[Post] = Relationship(
        back_populates="tags",
        link_model="PostTag"
    )

class PostTag(SQLModel, table=True):
    """Link table for many-to-many."""
    post_id: int = Field(foreign_key="post.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
```

### Model Inheritance

```python
# Base model for shared fields
class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

# Inherit from base
class Article(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str

class Comment(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    article_id: int = Field(foreign_key="article.id")
```

## Database Sessions

### Dependency Injection

```python
from zenith import Depends
from zenith.db import Session, get_session

@app.get("/users")
async def list_users(session: Session = Depends(get_session)):
    statement = select(User)
    users = session.exec(statement).all()
    return users
```

### Manual Session Management

```python
from zenith.db import SessionLocal

@app.post("/users")
async def create_user(user_data: UserCreate):
    async with SessionLocal() as session:
        user = User(**user_data.model_dump())
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
```

### Transaction Management

```python
@app.post("/transfer")
async def transfer_funds(
    from_account: int,
    to_account: int,
    amount: float,
    session: Session = Depends(get_session)
):
    async with session.begin():  # Auto-commit or rollback
        # Get accounts
        sender = session.get(Account, from_account)
        receiver = session.get(Account, to_account)
        
        # Check balance
        if sender.balance < amount:
            raise HTTPException(400, "Insufficient funds")
        
        # Transfer
        sender.balance -= amount
        receiver.balance += amount
        
        # Auto-commit on success, rollback on error
    
    return {"status": "success"}
```

## Queries

### Basic Queries

```python
from sqlmodel import select, col

# Get all
statement = select(User)
users = session.exec(statement).all()

# Get by ID
user = session.get(User, user_id)

# Filter
statement = select(User).where(User.age >= 18)
adult_users = session.exec(statement).all()

# Multiple conditions
statement = select(User).where(
    User.age >= 18,
    User.is_active == True
)

# OR conditions
from sqlmodel import or_
statement = select(User).where(
    or_(User.role == "admin", User.role == "moderator")
)
```

### Advanced Queries

```python
# Joins
statement = (
    select(Post, User)
    .join(User)
    .where(User.is_active == True)
)
results = session.exec(statement).all()

# Aggregations
from sqlmodel import func
statement = (
    select(func.count(User.id))
    .where(User.created_at >= datetime(2024, 1, 1))
)
user_count = session.exec(statement).one()

# Group by
statement = (
    select(User.country, func.count(User.id))
    .group_by(User.country)
    .having(func.count(User.id) > 10)
)

# Order and limit
statement = (
    select(Post)
    .order_by(Post.created_at.desc())
    .limit(10)
    .offset(20)
)
```

### Pagination

```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int

@app.get("/users", response_model=Page[User])
async def list_users(
    page: int = 1,
    per_page: int = 20,
    session: Session = Depends(get_session)
):
    # Count total
    count_statement = select(func.count(User.id))
    total = session.exec(count_statement).one()
    
    # Get page
    statement = (
        select(User)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    users = session.exec(statement).all()
    
    return Page(
        items=users,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )
```

## Migrations with Alembic

### Setup

```bash
# Initialize migrations
zen db init

# Create migration
zen db migrate -m "add users table"

# Apply migrations
zen db upgrade

# Rollback
zen db downgrade -1
```

### Configuration

```python
# alembic.ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://localhost/mydb

# migrations/env.py
from zenith.db import SQLModel
from app.models import *  # Import all models

target_metadata = SQLModel.metadata
```

### Auto-generating Migrations

```python
# After model changes
zen db migrate -m "add email field to users"

# Review generated migration
cat migrations/versions/xxx_add_email_field_to_users.py

# Apply
zen db upgrade
```

## Testing with Databases

```python
import pytest
from zenith.testing import TestClient
from zenith.db import create_engine, SQLModel

@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.mark.asyncio
async def test_create_user(test_db):
    app.state.engine = test_db
    
    async with TestClient(app) as client:
        response = await client.post("/users", json={
            "email": "test@example.com",
            "name": "Test User"
        })
        assert response.status_code == 201
        user = response.json()
        assert user["email"] == "test@example.com"
```

## Performance Optimization

### Eager Loading

```python
from sqlmodel import selectinload

# Avoid N+1 queries
statement = (
    select(User)
    .options(selectinload(User.posts))  # Load posts in one query
)
users = session.exec(statement).all()

# Multiple relationships
statement = (
    select(Post)
    .options(
        selectinload(Post.author),
        selectinload(Post.tags)
    )
)
```

### Bulk Operations

```python
# Bulk insert
users = [
    User(email=f"user{i}@example.com", name=f"User {i}")
    for i in range(1000)
]
session.bulk_insert_mappings(User, users)
await session.commit()

# Bulk update
session.bulk_update_mappings(
    User,
    [{"id": 1, "is_active": False}, {"id": 2, "is_active": False}]
)
```

### Query Optimization

```python
# Use indexes
class User(SQLModel, table=True):
    email: str = Field(index=True)  # Single column index
    
    class Config:
        # Composite index
        __table_args__ = (
            Index("ix_user_email_active", "email", "is_active"),
        )

# Only select needed columns
statement = select(User.id, User.email).where(User.is_active == True)

# Use exists for checks
from sqlmodel import exists
has_admin = session.exec(
    select(exists().where(User.role == "admin"))
).one()
```

<Aside type="tip">
  **Pro Tip**: Always use connection pooling in production and consider read replicas for scaling read-heavy workloads.
</Aside>

## Next Steps

- Implement [Authentication](/concepts/authentication) with database users
- Learn about [Testing](/api/testing) database operations
- Explore [Performance](/features/performance) optimization