"""Minimal Zenith benchmark application."""

import os

from pydantic import BaseModel

# Set required env var
os.environ["SECRET_KEY"] = "benchmark-secret-key-for-testing"

from zenith import Zenith


class CreateUserModel(BaseModel):
    name: str
    email: str


# Simple in-memory storage
users_db = {}
for i in range(100):
    users_db[i] = {
        "id": i,
        "name": f"User {i}",
        "email": f"user{i}@example.com",
        "created_at": "2025-01-01T00:00:00",
    }

# App - disable debug to avoid middleware overhead in benchmarks
app = Zenith(debug=False)


# Routes
@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id in users_db:
        return users_db[user_id]
    return {"error": "User not found"}


@app.get("/users")
async def list_users(limit: int = 100):
    return list(users_db.values())[:limit]


@app.post("/users")
async def create_user(data: CreateUserModel):
    new_id = len(users_db)
    users_db[new_id] = {
        "id": new_id,
        "name": data.name,
        "email": data.email,
        "created_at": "2025-01-01T00:00:00",
    }
    return users_db[new_id]


@app.get("/protected")
async def protected_route():
    return {"user": {"id": 1, "email": "test@example.com"}}


@app.post("/validate")
async def validate_data(data: CreateUserModel):
    return {"validated": True, "data": data.model_dump()}


@app.post("/upload")
async def upload_file():
    return {"size": 10000, "message": "File processed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100, log_level="error")
