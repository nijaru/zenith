---
title: Service Architecture
description: Organize business logic in Service classes for clean, testable applications
---

# Service Architecture

Services organize your business logic outside of route handlers, creating clean, testable, and maintainable applications.

## Why Services?

Services solve common problems in web applications:

- **Thin controllers** - Route handlers focus on HTTP concerns
- **Testable logic** - Business rules tested independently
- **Reusable code** - Logic shared across endpoints
- **Clear separation** - Domain logic separate from web layer

## Basic Service

```python
from zenith import Service, Inject

class UserService(Service):
    """Business logic for user operations."""

    def __init__(self):
        self.users = {}  # Demo storage

    async def create_user(self, user_data: UserCreate) -> User:
        # Business validation
        if user_data.age < 13:
            raise ValueError("Users must be at least 13 years old")

        if user_data.email in self.users:
            raise ValueError("Email already registered")

        # Create user
        user = User(
            id=len(self.users) + 1,
            **user_data.model_dump()
        )
        self.users[user.email] = user
        return user

    async def get_user(self, user_id: int) -> User | None:
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    async def list_users(self) -> list[User]:
        return list(self.users.values())

# Usage in routes
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    users: UserService = Inject()  # Auto-injected
) -> User:
    return await users.create_user(user_data)

@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    users: UserService = Inject()
) -> User:
    user = await users.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

## Service with Database

```python
from zenith import Service, Inject, DatabaseSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserService(Service):
    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> User:
        # Check for existing user
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Create new user
        user = User(**user_data.model_dump())
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_user(self, user_id: int, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
        result = await db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

# Database connection factory
async def get_db():
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession)
    async with SessionLocal() as session:
        yield session

# Routes with database injection
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = DatabaseSession(get_db),
    users: UserService = Inject()
) -> User:
    return await users.create_user(user_data, db)

@app.get("/users", response_model=list[User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = DatabaseSession(get_db),
    users: UserService = Inject()
) -> list[User]:
    return await users.list_users(db, skip, limit)
```

## Service Dependencies

Services can depend on other services:

```python
class EmailService(Service):
    async def send_welcome_email(self, user: User):
        # Send email logic
        print(f"Sending welcome email to {user.email}")

class NotificationService(Service):
    async def notify_admin(self, message: str):
        # Admin notification logic
        print(f"Admin notification: {message}")

class UserService(Service):
    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession,
        email: EmailService = Inject(),
        notifications: NotificationService = Inject()
    ) -> User:
        # Create user
        user = User(**user_data.model_dump())
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Send welcome email
        await email.send_welcome_email(user)

        # Notify admin
        await notifications.notify_admin(f"New user registered: {user.email}")

        return user

# Route handler stays clean
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = DatabaseSession(get_db),
    users: UserService = Inject()
) -> User:
    return await users.create_user(user_data, db)
```

## Service Configuration

Configure services with initialization:

```python
class PaymentService(Service):
    def __init__(self):
        self.stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if not self.stripe_key:
            raise ValueError("STRIPE_SECRET_KEY required")

    async def process_payment(self, amount: int, customer_id: str) -> dict:
        # Payment processing logic
        return {"status": "success", "charge_id": "ch_123"}

class UserService(Service):
    def __init__(self):
        self.max_users = int(os.getenv("MAX_USERS", "1000"))

    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession,
        payments: PaymentService = Inject()
    ) -> User:
        # Check user limit
        user_count = await db.scalar(select(func.count(User.id)))
        if user_count >= self.max_users:
            raise ValueError("User limit reached")

        # Create user logic...
        user = User(**user_data.model_dump())

        # Process initial payment if needed
        if user_data.payment_token:
            result = await payments.process_payment(999, user.id)
            user.payment_status = result["status"]

        db.add(user)
        await db.commit()
        return user
```

## Testing Services

Test services independently of HTTP layer:

```python
import pytest
from zenith.testing import TestContext

class TestUserService:
    @pytest.mark.asyncio
    async def test_create_user_success(self):
        # Test service directly
        async with TestContext(UserService) as users:
            user_data = UserCreate(
                name="Test User",
                email="test@example.com",
                age=25
            )

            user = await users.create_user(user_data)

            assert user.name == "Test User"
            assert user.email == "test@example.com"
            assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_user_underage(self):
        async with TestContext(UserService) as users:
            user_data = UserCreate(
                name="Kid",
                email="kid@example.com",
                age=12  # Under 13
            )

            with pytest.raises(ValueError, match="must be at least 13"):
                await users.create_user(user_data)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self):
        async with TestContext(UserService) as users:
            user_data = UserCreate(
                name="User One",
                email="same@example.com",
                age=25
            )

            # Create first user
            await users.create_user(user_data)

            # Try to create duplicate
            duplicate_data = UserCreate(
                name="User Two",
                email="same@example.com",  # Same email
                age=30
            )

            with pytest.raises(ValueError, match="already registered"):
                await users.create_user(duplicate_data)
```

## Advanced Patterns

### Repository Pattern

```python
class UserRepository(Service):
    async def create(self, user: User, db: AsyncSession) -> User:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_by_id(self, user_id: int, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

class UserService(Service):
    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession,
        repo: UserRepository = Inject()
    ) -> User:
        # Check if user exists
        existing = await repo.get_by_email(user_data.email, db)
        if existing:
            raise ValueError("Email already registered")

        # Create new user
        user = User(**user_data.model_dump())
        return await repo.create(user, db)
```

### Event-Driven Services

```python
class EventService(Service):
    def __init__(self):
        self.listeners = {}

    def on(self, event: str, handler):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(handler)

    async def emit(self, event: str, data):
        if event in self.listeners:
            for handler in self.listeners[event]:
                await handler(data)

class UserService(Service):
    async def create_user(
        self,
        user_data: UserCreate,
        db: AsyncSession,
        events: EventService = Inject()
    ) -> User:
        user = User(**user_data.model_dump())
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Emit event for other services to handle
        await events.emit("user.created", user)

        return user

# Register event handlers
@app.on_event("startup")
async def setup_events():
    events = EventService()

    async def send_welcome_email(user: User):
        print(f"Sending welcome email to {user.email}")

    async def update_analytics(user: User):
        print(f"Recording new user: {user.id}")

    events.on("user.created", send_welcome_email)
    events.on("user.created", update_analytics)
```

## Best Practices

### ✅ Do

- Keep business logic in services, not route handlers
- Use dependency injection for service dependencies
- Test services independently
- Use descriptive service and method names
- Handle errors appropriately with clear messages
- Use type hints for better IDE support

### ❌ Don't

- Put HTTP concerns in services (request/response objects)
- Share mutable state between requests
- Make services too large (split into smaller services)
- Skip error handling and validation
- Test through HTTP layer only

### Service Organization

```
your_app/
├── services/
│   ├── __init__.py
│   ├── user_service.py      # User business logic
│   ├── payment_service.py   # Payment processing
│   ├── email_service.py     # Email sending
│   └── analytics_service.py # Analytics tracking
├── models/
│   ├── __init__.py
│   └── user.py             # Pydantic models
├── routes/
│   ├── __init__.py
│   └── users.py            # HTTP route handlers
└── main.py                 # Application setup
```

Services make your application more maintainable, testable, and easier to understand!