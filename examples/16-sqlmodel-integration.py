"""
💾 SQLModel Integration Example - Unified Models with Repository Pattern

This example demonstrates Zenith's SQLModel integration providing unified
Pydantic + SQLAlchemy models with the repository pattern for clean data access.

Key Features Demonstrated:
- Unified SQLModel models (single model for validation + database)
- Repository pattern with generic CRUD operations
- Relationship handling with eager loading
- Type-safe database operations
- Automatic validation and serialization
- Clean separation of data and business logic

Prerequisites:
    pip install sqlmodel aiosqlite

Run with: python examples/16-sqlmodel-integration.py
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, Relationship, SQLModel

from zenith import Context, Router, Service, Zenith
from zenith.db.sqlmodel import ZenithSQLModel, create_repository

# ============================================================================
# SQLMODEL UNIFIED MODELS
# ============================================================================


class UserBase(SQLModel):
    """Base user fields shared across all user models."""

    name: str = Field(min_length=1, max_length=100, description="User's full name")
    email: str = Field(unique=True, index=True, description="User's email address")
    age: int = Field(ge=0, le=150, description="User's age")
    is_active: bool = Field(default=True, description="Whether user is active")


class User(UserBase, ZenithSQLModel, table=True):
    """
    Database model for users.
    This single model handles both database operations AND API validation!
    """

    __tablename__ = "users"

    # Relationships
    posts: list["Post"] = Relationship(back_populates="author")
    comments: list["Comment"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """Model for creating new users (can customize validation)."""

    pass


class UserUpdate(SQLModel):
    """Model for updating users (all fields optional)."""

    name: str | None = None
    email: str | None = None
    age: int | None = None
    is_active: bool | None = None


class PostBase(SQLModel):
    """Base post fields."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_published: bool = Field(default=False)


class Post(PostBase, ZenithSQLModel, table=True):
    """
    Database model for blog posts.
    Demonstrates relationships with SQLModel.
    """

    __tablename__ = "posts"

    # Foreign key
    author_id: int = Field(foreign_key="users.id", description="Author's user ID")

    # Relationships
    author: User = Relationship(back_populates="posts")
    comments: list["Comment"] = Relationship(back_populates="post")
    # Note: Tags relationship will be added after Tag class is defined


class PostCreate(PostBase):
    """Model for creating posts."""

    author_id: int
    tag_ids: list[int] = []


class Comment(ZenithSQLModel, table=True):
    """Comment model demonstrating multiple relationships."""

    __tablename__ = "comments"

    content: str = Field(min_length=1, max_length=500)

    # Foreign keys
    user_id: int = Field(foreign_key="users.id")
    post_id: int = Field(foreign_key="posts.id")

    # Relationships
    user: User = Relationship(back_populates="comments")
    post: Post = Relationship(back_populates="comments")


class Tag(ZenithSQLModel, table=True):
    """Tag model for categorizing posts."""

    __tablename__ = "tags"

    name: str = Field(unique=True, index=True)

    # Note: Posts relationship will be added after PostTag class is defined


class PostTag(SQLModel, table=True):
    """Join table for many-to-many relationship between posts and tags."""

    __tablename__ = "post_tags"

    post_id: int = Field(foreign_key="posts.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)


# Add many-to-many relationships after all classes are defined
Post.tags = Relationship(back_populates="posts", link_model=PostTag)
Tag.posts = Relationship(back_populates="tags", link_model=PostTag)


# ============================================================================
# REPOSITORY PATTERN WITH SQLMODEL
# ============================================================================


class BlogContext(Service):
    """
    Business logic context using repository pattern for data access.
    Clean separation of business logic from data access.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        # Create repositories for each model
        self.users = create_repository(session, User)
        self.posts = create_repository(session, Post)
        self.comments = create_repository(session, Comment)
        self.tags = create_repository(session, Tag)

    # User operations
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(**user_data.model_dump())
        return await self.users.create(user)

    async def get_user(self, user_id: int, include_posts: bool = False) -> User | None:
        """Get user by ID with optional posts."""
        if include_posts:
            return await self.users.get(user_id, with_relations=["posts"])
        return await self.users.get(user_id)

    async def list_users(self, skip: int = 0, limit: int = 10) -> list[User]:
        """List users with pagination."""
        return await self.users.list(offset=skip, limit=limit)

    async def update_user(self, user_id: int, updates: UserUpdate) -> User | None:
        """Update user fields."""
        update_data = updates.model_dump(exclude_unset=True)
        return await self.users.update(user_id, **update_data)

    async def search_users(self, email_contains: str) -> list[User]:
        """Search users by email (custom query)."""
        return await self.users.filter(User.email.contains(email_contains))

    # Post operations
    async def create_post(self, post_data: PostCreate) -> Post:
        """Create a new post with tags."""
        # Extract tag IDs
        tag_ids = post_data.tag_ids
        post_dict = post_data.model_dump(exclude={"tag_ids"})

        # Create post
        post = Post(**post_dict)
        created_post = await self.posts.create(post)

        # Add tags if provided
        if tag_ids:
            # In a real app, you'd add the tags through the relationship
            pass

        return created_post

    async def get_post_with_author(self, post_id: int) -> Post | None:
        """Get post with author information."""
        return await self.posts.get(post_id, with_relations=["author"])

    async def get_post_full(self, post_id: int) -> Post | None:
        """Get post with all relationships loaded."""
        return await self.posts.get(
            post_id, with_relations=["author", "comments", "tags"]
        )

    async def list_published_posts(self) -> list[Post]:
        """List only published posts."""
        return await self.posts.filter(is_published=True)

    async def list_posts_by_author(self, author_id: int) -> list[Post]:
        """List posts by a specific author."""
        return await self.posts.filter(author_id=author_id)

    # Comment operations
    async def add_comment(self, post_id: int, user_id: int, content: str) -> Comment:
        """Add a comment to a post."""
        comment = Comment(post_id=post_id, user_id=user_id, content=content)
        return await self.comments.create(comment)

    async def get_post_comments(self, post_id: int) -> list[Comment]:
        """Get all comments for a post."""
        return await self.comments.filter(post_id=post_id)

    # Tag operations
    async def create_tag(self, name: str) -> Tag:
        """Create a new tag."""
        tag = Tag(name=name)
        return await self.tags.create(tag)

    async def get_or_create_tag(self, name: str) -> Tag:
        """Get existing tag or create new one."""
        existing = await self.tags.get_by(name=name)
        if existing:
            return existing
        return await self.create_tag(name)

    # Complex queries
    async def get_user_activity(self, user_id: int) -> dict:
        """Get comprehensive user activity."""
        user = await self.users.get(user_id, with_relations=["posts", "comments"])
        if not user:
            return {}

        return {
            "user": user.model_dump(exclude={"posts", "comments"}),
            "post_count": len(user.posts),
            "comment_count": len(user.comments),
            "recent_posts": [p.model_dump() for p in user.posts[:5]],
        }


# ============================================================================
# API ROUTES
# ============================================================================

# Create the application
app = Zenith()

# Create router for API organization
api = Router(prefix="/api")


@api.post("/users", response_model=User)
async def create_user(user_data: UserCreate, blog: BlogContext = Context()) -> User:
    """Create a new user."""
    return await blog.create_user(user_data)


@api.get("/users", response_model=list[User])
async def list_users(
    skip: int = 0, limit: int = 10, blog: BlogContext = Context()
) -> list[User]:
    """List users with pagination."""
    return await blog.list_users(skip, limit)


@api.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int, include_posts: bool = False, blog: BlogContext = Context()
) -> User:
    """Get user by ID."""
    user = await blog.get_user(user_id, include_posts)
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user


@api.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int, updates: UserUpdate, blog: BlogContext = Context()
) -> User:
    """Update user information."""
    user = await blog.update_user(user_id, updates)
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user


@api.get("/users/{user_id}/activity")
async def get_user_activity(user_id: int, blog: BlogContext = Context()) -> dict:
    """Get user activity summary."""
    return await blog.get_user_activity(user_id)


@api.post("/posts", response_model=Post)
async def create_post(post_data: PostCreate, blog: BlogContext = Context()) -> Post:
    """Create a new blog post."""
    return await blog.create_post(post_data)


@api.get("/posts", response_model=list[Post])
async def list_posts(
    published_only: bool = True,
    author_id: int | None = None,
    blog: BlogContext = Context(),
) -> list[Post]:
    """List blog posts with filters."""
    if author_id:
        return await blog.list_posts_by_author(author_id)
    elif published_only:
        return await blog.list_published_posts()
    else:
        return await blog.posts.list()


@api.get("/posts/{post_id}", response_model=Post)
async def get_post(
    post_id: int, include_all: bool = False, blog: BlogContext = Context()
) -> Post:
    """Get post by ID with optional relationships."""
    if include_all:
        post = await blog.get_post_full(post_id)
    else:
        post = await blog.get_post_with_author(post_id)

    if not post:
        raise ValueError(f"Post {post_id} not found")
    return post


@api.post("/posts/{post_id}/comments", response_model=Comment)
async def add_comment(
    post_id: int, user_id: int, content: str, blog: BlogContext = Context()
) -> Comment:
    """Add a comment to a post."""
    return await blog.add_comment(post_id, user_id, content)


@api.get("/posts/{post_id}/comments", response_model=list[Comment])
async def get_post_comments(
    post_id: int, blog: BlogContext = Context()
) -> list[Comment]:
    """Get all comments for a post."""
    return await blog.get_post_comments(post_id)


# Include the API router
app.include_router(api)


# Root endpoint
@app.get("/")
async def root() -> dict:
    """API root endpoint."""
    return {
        "name": "Blog API with SQLModel",
        "message": "Unified models with repository pattern",
        "features": [
            "Single model for database + validation",
            "Repository pattern for clean data access",
            "Relationship handling with eager loading",
            "Type-safe database operations",
            "Automatic serialization",
        ],
        "docs": "/docs",
    }


# ============================================================================
# DATABASE SETUP AND MAIN
# ============================================================================


async def init_db():
    """Initialize database and create tables."""
    # Create async engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///./blog.db", echo=False, future=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # In a real app, you'd set up the session in the app's dependency injection
    # For this demo, we'll use a global session factory
    global session_factory
    session_factory = async_session

    # Create some sample data
    async with async_session() as session:
        blog = BlogContext(session)

        # Check if we already have data
        users = await blog.list_users()
        if not users:
            print("📝 Creating sample data...")

            # Create users
            alice = await blog.create_user(
                UserCreate(name="Alice Smith", email="alice@example.com", age=30)
            )
            bob = await blog.create_user(
                UserCreate(name="Bob Jones", email="bob@example.com", age=25)
            )

            # Create posts
            post1 = await blog.create_post(
                PostCreate(
                    title="Introduction to SQLModel",
                    content="SQLModel combines Pydantic and SQLAlchemy...",
                    author_id=alice.id,
                    is_published=True,
                )
            )

            post2 = await blog.create_post(
                PostCreate(
                    title="Repository Pattern in Python",
                    content="The repository pattern provides clean data access...",
                    author_id=alice.id,
                    is_published=True,
                )
            )

            # Add comments
            await blog.add_comment(post1.id, bob.id, "Great article!")
            await blog.add_comment(post1.id, alice.id, "Thanks Bob!")

            await session.commit()
            print("✅ Sample data created")

    return async_session


async def main():
    """Run the application."""
    print("💾 SQLModel Integration Example")
    print("=" * 60)

    # Initialize database
    await init_db()

    print("\n📍 Server starting at: http://localhost:8016")
    print("\n🔗 Available endpoints:")
    print("\n  Users:")
    print("    POST   /api/users           - Create user")
    print("    GET    /api/users           - List users")
    print("    GET    /api/users/{id}      - Get user")
    print("    PUT    /api/users/{id}      - Update user")
    print("    GET    /api/users/{id}/activity - User activity")
    print("\n  Posts:")
    print("    POST   /api/posts           - Create post")
    print("    GET    /api/posts           - List posts")
    print("    GET    /api/posts/{id}      - Get post")
    print("\n  Comments:")
    print("    POST   /api/posts/{id}/comments - Add comment")
    print("    GET    /api/posts/{id}/comments - Get comments")
    print("\n📖 Interactive docs: http://localhost:8016/docs")
    print("\n✨ SQLModel Benefits:")
    print("  • Single model for DB + validation")
    print("  • Type safety throughout")
    print("  • Automatic migrations")
    print("  • Clean repository pattern")
    print("  • Relationship handling")

    # Note: In a real deployment, use uvicorn directly
    # For this example, we'll just show the setup
    print("\n⚠️  Note: This example shows the setup.")
    print("    Run with: uvicorn examples.16-sqlmodel-integration:app --reload")


if __name__ == "__main__":
    # For demonstration, just show the setup
    asyncio.run(main())

    # In production, the app would be run with:
    # app.run(host="127.0.0.1", port=8016, reload=True)
