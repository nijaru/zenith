"""
🔍 Pydantic Validation - Type-Safe Request and Response Models

This example demonstrates:
- Pydantic models for request validation
- Automatic JSON parsing and validation
- Type-safe response models
- Error handling for invalid data

Run with: python examples/02-pydantic-validation.py
Then visit: http://localhost:8002/docs for interactive API
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from zenith import Zenith

app = Zenith(debug=True)


# Request Models
class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    age: int
    bio: str | None = None

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("Age must be positive")
        if v > 150:
            raise ValueError("Age must be realistic")
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UpdateUserRequest(BaseModel):
    name: str | None = None
    age: int | None = None
    bio: str | None = None


# Response Models
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int
    bio: str | None
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict | None = None


# Mock database
users_db = []
next_id = 1


@app.get("/", response_model=dict)
async def root():
    """API overview with available endpoints."""
    return {
        "message": "Pydantic Validation Example",
        "features": [
            "Automatic request validation",
            "Type-safe response models",
            "Email validation",
            "Custom field validators",
            "Comprehensive error handling",
        ],
        "endpoints": {
            "users": "GET /users - List all users",
            "create": "POST /users - Create new user",
            "get": "GET /users/{user_id} - Get user by ID",
            "update": "PATCH /users/{user_id} - Update user",
            "delete": "DELETE /users/{user_id} - Delete user",
        },
    }


@app.get("/users", response_model=list[UserResponse])
async def list_users():
    """Get all users."""
    return users_db


@app.post("/users", response_model=UserResponse)
async def create_user(user_data: CreateUserRequest) -> UserResponse:
    """Create a new user with validation."""
    global next_id

    # Check for duplicate email
    if any(u["email"] == user_data.email for u in users_db):
        raise ValueError(f"User with email {user_data.email} already exists")

    now = datetime.utcnow()
    new_user = {
        "id": next_id,
        "name": user_data.name,
        "email": user_data.email,
        "age": user_data.age,
        "bio": user_data.bio,
        "created_at": now,
        "updated_at": now,
    }

    users_db.append(new_user)
    next_id += 1

    return UserResponse(**new_user)


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """Get user by ID."""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    return UserResponse(**user)


@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, updates: UpdateUserRequest) -> UserResponse:
    """Update user with partial data."""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    # Apply updates (only set fields)
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        user[field] = value

    user["updated_at"] = datetime.utcnow()

    return UserResponse(**user)


@app.delete("/users/{user_id}")
async def delete_user(user_id: int) -> dict:
    """Delete user by ID."""
    global users_db
    original_length = len(users_db)
    users_db = [u for u in users_db if u["id"] != user_id]

    if len(users_db) == original_length:
        raise ValueError(f"User with ID {user_id} not found")

    return {"message": f"User {user_id} deleted successfully"}


@app.get("/health")
async def health():
    """Health check with current stats."""
    return {
        "status": "healthy",
        "example": "02-pydantic-validation",
        "users_count": len(users_db),
        "next_id": next_id,
    }


if __name__ == "__main__":
    print("🔍 Starting Pydantic Validation Example")
    print("📍 Server will start at: http://localhost:8002")
    print("📖 Interactive docs at: http://localhost:8002/docs")
    print()
    print("🧪 Try these requests:")
    print('   POST /users {"name": "Alice", "email": "alice@example.com", "age": 25}')
    print(
        '   POST /users {"name": "", "email": "invalid", "age": -5}  # Will fail validation'
    )
    print("   GET /users")
    print('   PATCH /users/1 {"age": 26}')
    print()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
