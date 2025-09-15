---
title: Quick Start
description: Build your first Zenith API in 5 minutes
---

# Quick Start

Get a Zenith API running in 5 minutes with hot reload, automatic documentation, and production-ready defaults.

## Installation

```bash
pip install zenith-web
```

## Your First API

Create a new file `app.py`:

```python
from zenith import Zenith

app = Zenith()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}

@app.get("/hello/{name}")
async def hello_name(name: str):
    return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
```

## Run with Hot Reload

**Option 1: Using Zenith CLI (Recommended)**
```bash
zen dev
```

**Option 2: Direct uvicorn**
```bash
uvicorn app:app --reload
```

## Interactive Documentation

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for automatic OpenAPI documentation.

## Add Type-Safe Routes

```python
from pydantic import BaseModel
from zenith import Zenith

app = Zenith()

class User(BaseModel):
    name: str
    email: str
    age: int

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

# Automatic validation and serialization
@app.post("/users", response_model=User)
async def create_user(user: UserCreate) -> User:
    # user is automatically validated
    # return value is automatically serialized
    return User(
        name=user.name,
        email=user.email,
        age=user.age
    )
```

## Add Business Logic with Services

```python
from zenith import Zenith, Service, Inject

class UserService(Service):
    """Business logic for user operations."""

    def __init__(self):
        self.users = []  # In-memory store for demo

    async def create_user(self, user_data: UserCreate) -> User:
        user = User(**user_data.model_dump())
        self.users.append(user)
        return user

    async def list_users(self) -> list[User]:
        return self.users

app = Zenith()

# Automatic dependency injection
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    users: UserService = Inject()  # Auto-injected
) -> User:
    return await users.create_user(user_data)

@app.get("/users", response_model=list[User])
async def list_users(users: UserService = Inject()) -> list[User]:
    return await users.list_users()
```

## What You Get Out of the Box

✅ **Hot reload** with `zen dev`
✅ **Automatic OpenAPI docs** at `/docs`
✅ **Type-safe validation** with Pydantic
✅ **Production middleware** (CORS, security headers, rate limiting)
✅ **Dependency injection** for clean architecture
✅ **Health checks** at `/health`
✅ **Metrics** at `/metrics`

## Next Steps

- **[Service Architecture](/concepts/services/)** - Organize business logic
- **[Database Integration](/concepts/database/)** - Connect to databases safely
- **[Authentication](/concepts/authentication/)** - Secure your API
- **[CLI Tools](/guides/cli/)** - Development productivity
- **[Examples](/examples/)** - Real-world applications

## CLI Commands

```bash
zen new myapi          # Create new application
zen dev                # Development server with hot reload
zen routes             # Show all routes
zen db migrate         # Run database migrations
zen test               # Run tests
zen shell             # Interactive shell
```

Start with `zen dev` for the best development experience!