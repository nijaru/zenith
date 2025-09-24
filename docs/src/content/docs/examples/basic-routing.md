---
title: Basic Routing
description: Routing with path parameters, query parameters, and different HTTP methods
---

# Basic Routing

This example demonstrates Zenith's routing system, including path parameters, query parameters, and different HTTP methods.

## Simple Routes

Create basic endpoints with the route decorators:

```python
from zenith import Zenith

app = Zenith()

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Zenith!"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "api"
    }
```

## Path Parameters

Extract values from the URL path with type annotations:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get a specific user by ID.

    The user_id is extracted from the URL and automatically
    converted to an integer. Invalid values return 422.
    """
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }

@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: int, post_id: int):
    """Get a specific post from a specific user.

    Multiple path parameters are supported.
    """
    return {
        "user_id": user_id,
        "post_id": post_id,
        "title": f"Post {post_id} by User {user_id}"
    }
```

## Query Parameters

Handle URL query parameters with function parameters:

```python
@app.get("/search")
async def search_items(
    q: str,                    # Required query parameter
    limit: int = 10,          # Optional with default
    offset: int = 0           # Optional with default
):
    """Search with query parameters.

    Example URLs:
    - /search?q=python
    - /search?q=python&limit=5
    - /search?q=python&limit=5&offset=20
    """
    results = [f"Result {i} for '{q}'" for i in range(offset, offset + limit)]

    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "results": results,
        "total": 100
    }
```

## Request Body

Handle JSON request bodies with Pydantic models:

```python
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    """Model for user creation."""
    name: str
    email: str
    age: Optional[int] = None

@app.post("/users")
async def create_user(user: UserCreate):
    """Create a new user.

    Expects JSON body:
    {
        "name": "Alice",
        "email": "alice@example.com",
        "age": 30  // optional
    }
    """
    return {
        "message": "User created successfully",
        "user": user.model_dump(),
        "id": 123  # Would be from database
    }
```

## HTTP Methods

Zenith supports all standard HTTP methods:

```python
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    """Retrieve an item."""
    return {"item_id": item_id, "name": f"Item {item_id}"}

@app.post("/items")
async def create_item(data: dict):
    """Create a new item."""
    return {"message": "Item created", "data": data}

@app.put("/items/{item_id}")
async def update_item(item_id: int, data: dict):
    """Update an existing item."""
    return {"message": f"Item {item_id} updated", "data": data}

@app.patch("/items/{item_id}")
async def patch_item(item_id: int, data: dict):
    """Partially update an item."""
    return {"message": f"Item {item_id} patched", "data": data}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item."""
    return {"message": f"Item {item_id} deleted"}
```

## Response Models

Use response models for type-safe responses:

```python
class User(BaseModel):
    """User response model."""
    id: int
    name: str
    email: str
    created_at: datetime

@app.get("/users/{user_id}", response_model=User)
async def get_user_detailed(user_id: int) -> User:
    """Get user with validated response."""
    # Return value is validated against User model
    return User(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com",
        created_at=datetime.now()
    )
```

## Status Codes

Control response status codes:

```python
from zenith import status

@app.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item_with_status(item: dict):
    """Create item returns 201 Created."""
    return {"id": 123, "item": item}

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_no_content(item_id: int):
    """Delete returns 204 No Content."""
    # Perform deletion
    return None  # No content
```

## Complete Example

Here's a complete working example:

```python
# examples/01-basic-routing.py
from zenith import Zenith
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = Zenith()

# Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 1

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: int
    completed: bool
    created_at: datetime

# In-memory storage for demo
tasks = {}
task_counter = 0

@app.get("/")
async def root():
    """API root."""
    return {
        "name": "Task API",
        "version": "1.0.0",
        "endpoints": {
            "tasks": "/tasks",
            "task": "/tasks/{id}",
            "search": "/search?q=query"
        }
    }

@app.get("/tasks")
async def list_tasks(
    completed: Optional[bool] = None,
    limit: int = 10
):
    """List tasks with optional filtering."""
    result = []
    for task in tasks.values():
        if completed is None or task["completed"] == completed:
            result.append(task)

    return {
        "tasks": result[:limit],
        "total": len(result),
        "limit": limit
    }

@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    """Get a specific task."""
    if task_id not in tasks:
        return {"error": "Task not found"}, 404

    return tasks[task_id]

@app.post("/tasks", response_model=Task)
async def create_task(task: TaskCreate) -> Task:
    """Create a new task."""
    global task_counter
    task_counter += 1

    new_task = Task(
        id=task_counter,
        title=task.title,
        description=task.description,
        priority=task.priority,
        completed=False,
        created_at=datetime.now()
    )

    tasks[task_counter] = new_task.model_dump()
    return new_task

@app.put("/tasks/{task_id}")
async def update_task(task_id: int, task: TaskCreate):
    """Update a task."""
    if task_id not in tasks:
        return {"error": "Task not found"}, 404

    tasks[task_id].update(task.model_dump())
    return tasks[task_id]

@app.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    """Mark a task as completed."""
    if task_id not in tasks:
        return {"error": "Task not found"}, 404

    tasks[task_id]["completed"] = True
    return tasks[task_id]

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """Delete a task."""
    if task_id not in tasks:
        return {"error": "Task not found"}, 404

    deleted = tasks.pop(task_id)
    return {"message": "Task deleted", "task": deleted}

@app.get("/search")
async def search_tasks(q: str):
    """Search tasks by title."""
    results = []
    for task in tasks.values():
        if q.lower() in task["title"].lower():
            results.append(task)

    return {
        "query": q,
        "results": results,
        "count": len(results)
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Task API Running")
    print("📚 Docs at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

## Running the Example

```bash
# Install Zenith
pip install zenith-web

# Run the example
python examples/01-basic-routing.py

# Test with curl
curl http://localhost:8000/
curl http://localhost:8000/tasks
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Zenith", "priority": 5}'

# Or visit the auto-generated docs
open http://localhost:8000/docs
```

## Key Concepts

### Type Validation
- Path and query parameters are automatically validated
- Invalid types return 422 Unprocessable Entity
- Pydantic models provide request/response validation

### Automatic Documentation
- All endpoints appear in `/docs` (Swagger UI)
- Alternative docs at `/redoc`
- OpenAPI schema at `/openapi.json`

### Async Support
- All route handlers are async by default
- Enables handling thousands of concurrent requests
- Non-blocking I/O for database and external API calls

## Next Steps

- Explore [Authentication](/concepts/authentication) for protected routes
- Learn about [Database Models](/concepts/models) for data persistence
- See [Middleware](/concepts/middleware) for request processing