# Next Steps for Zenith Development

## ✅ Documentation & Planning Cleanup Complete

### What We Did
1. **Updated Linear Issues:**
   - ✅ ZEN-1: Marked complete (basic kernel done)
   - 🚨 ZEN-2: Renamed to "Database Integration" (URGENT)
   - ✏️ ZEN-3: Renamed to "Complete Routing & Middleware"
   - ❌ ZEN-4: Canceled (LiveView not suitable)
   - ❌ ZEN-5: Canceled (Channels overengineered)
   - ✏️ ZEN-6: Renamed to "Authentication System"
   - ➕ ZEN-7: Added "Testing Framework"
   - ➕ ZEN-8: Added "OpenAPI Documentation"
   - ➕ ZEN-9: Added "Performance Benchmarks"
   - ➕ ZEN-10: Added "Deployment Guide"

2. **Cleaned Up Documentation:**
   - Archived outdated specs to `docs/archive/`
   - Created realistic README.md
   - Created clear ROADMAP.md
   - Removed Phoenix/LiveView references

3. **Simplified Vision:**
   - **FROM**: "Phoenix LiveView for Python with Rails DX"
   - **TO**: "Clean API framework ready for Mojo performance"

## 🚨 Immediate Next Action: ZEN-2 Database Integration

### Why This Is Critical
```python
# Current (Embarrassing):
class Accounts(Context):
    def __init__(self):
        self._users = {}  # This is a dictionary!

# Needed (Real Framework):
class Accounts(Context):
    async def create_user(self, data: UserCreate) -> User:
        async with self.db.session() as session:
            user = User(**data.model_dump())
            session.add(user)
            await session.commit()
            return user
```

### Implementation Plan for ZEN-2

#### Step 1: SQLAlchemy Integration
```python
# zenith/db/__init__.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Database:
    def __init__(self, url: str):
        self.engine = create_async_engine(url)
        self.SessionLocal = sessionmaker(bind=self.engine, class_=AsyncSession)
```

#### Step 2: Update Context Base Class
```python
# zenith/core/context.py
class Context:
    def __init__(self, container: DIContainer):
        self.container = container
        self.db = container.get(Database)  # Now contexts have DB access
```

#### Step 3: Create Real Models
```python
# zenith/models/tables.py
from sqlalchemy import Column, Integer, String, DateTime
from zenith.db import Base

class UserTable(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime)
```

#### Step 4: Update Accounts Context
```python
# zenith/contexts/accounts.py
class Accounts(Context):
    async def create_user(self, data: UserCreate) -> User:
        async with self.db.session() as session:
            user = UserTable(**data.model_dump())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return User.model_validate(user)
```

## 📅 Week-by-Week Plan

### This Week (Priority: ZEN-2)
- **Monday**: SQLAlchemy integration setup
- **Tuesday**: Update Context base class with DB
- **Wednesday**: Create database models
- **Thursday**: Update Accounts to use real DB
- **Friday**: Add Alembic migrations

### Next Week (Priority: ZEN-3)
- **Monday-Tuesday**: Add middleware system
- **Wednesday**: CORS and rate limiting
- **Thursday**: Exception handling
- **Friday**: Basic OpenAPI generation

### Week 3 (Priority: ZEN-6)
- **Monday-Tuesday**: JWT implementation
- **Wednesday**: Login/logout endpoints
- **Thursday**: Fix Auth() dependency
- **Friday**: Permission system

### Week 4 (Polish & Release)
- **Monday**: Testing utilities (ZEN-7)
- **Tuesday**: Documentation (ZEN-8)
- **Wednesday**: Performance benchmarks (ZEN-9)
- **Thursday**: Docker setup (ZEN-10)
- **Friday**: Release v0.1.0

## 🎯 Definition of Success for v0.1.0

A developer can:
1. ✅ Create an API with real database persistence
2. ✅ Authenticate users with JWT tokens
3. ✅ Test their API with TestClient
4. ✅ Deploy to Docker
5. ✅ See auto-generated API docs

## ⚠️ Avoid These Temptations

1. **Don't add LiveView** - It doesn't work well in Python
2. **Don't build an ORM** - SQLAlchemy is excellent
3. **Don't over-engineer DI** - Keep it simple
4. **Don't add features** - Fix what we have first
5. **Don't refactor everything** - Incremental improvements

## 📝 Code Quality Checklist

Before committing any code:
- [ ] Tests pass
- [ ] Type hints added
- [ ] No mock data in production code
- [ ] Examples updated
- [ ] Documentation updated

## 🚀 Let's Build

The path is clear. Start with ZEN-2 (Database Integration) and work through the priorities. Ship something real that developers can actually use.

Remember: **Better to have 10 people using a simple framework than 0 people impressed by a complex one.**