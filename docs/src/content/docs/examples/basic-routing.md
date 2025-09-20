---
title: Basic Routing Example
description: Learn Zenith's routing capabilities with path parameters, query parameters, and different HTTP methods
---

# Basic Routing Example

This example demonstrates Zenith's comprehensive routing system including path parameters, query parameters, and HTTP method handling.

## Code Example

```python
from zenith import Zenith
from pydantic import BaseModel
from typing import Optional

app = Zenith()

# Simple GET route
@app.get("/")
async def root():
    return {"message": "Welcome to Zenith!"}

# Route with path parameter
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}

# Route with multiple path parameters
@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: int, post_id: int):
    return {
        "user_id": user_id,
        "post_id": post_id,
        "title": f"Post {post_id} by User {user_id}"
    }

# Route with query parameters
@app.get("/search")
async def search_items(q: str, limit: int = 10, offset: int = 0):
    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "results": [f"Result {i}" for i in range(offset, offset + limit)]
    }

# POST route with request body
class CreateUser(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

@app.post("/users")
async def create_user(user: CreateUser):
    return {
        "message": "User created",
        "user": user.model_dump(),
        "id": 123
    }

# PUT route for updates
@app.put("/users/{user_id}")
async def update_user(user_id: int, user: CreateUser):
    return {
        "message": f"User {user_id} updated",
        "user": user.model_dump()
    }

# DELETE route
@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    return {"message": f"User {user_id} deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Key Features Demonstrated

### Path Parameters
- **Type conversion**: `user_id: int` automatically converts and validates
- **Multiple parameters**: `/users/{user_id}/posts/{post_id}`
- **Automatic validation**: Invalid types return 422 Unprocessable Entity

### Query Parameters  
- **Optional parameters**: `limit: int = 10` with default values
- **Type validation**: Automatic conversion and validation
- **Multiple parameters**: `q`, `limit`, `offset` all handled automatically

### HTTP Methods
- **GET**: Retrieve data
- **POST**: Create new resources with request body
- **PUT**: Update existing resources
- **DELETE**: Remove resources

### Request/Response Handling
- **Automatic JSON serialization**: Return dictionaries directly
- **Pydantic models**: Type-safe request body parsing
- **Error handling**: Built-in validation error responses

## Running the Example

1. **Save the code** as `basic_routing.py`
2. **Install dependencies**:
   ```bash
   pip install zenith-web uvicorn
   ```
3. **Run the server**:
   ```bash
   python basic_routing.py
   ```
4. **Test the routes**:
   ```bash
   curl http://localhost:8000/
   curl http://localhost:8000/users/123
   curl http://localhost:8000/search?q=python&limit=5
   curl -X POST http://localhost:8000/users \
     -H "Content-Type: application/json" \
     -d '{"name": "Alice", "email": "alice@example.com"}'
   ```

## Next Steps

- Explore **[Context System](/examples/context-system/)** for business logic organization
- Learn **[Pydantic Validation](/examples/pydantic-validation/)** for advanced data validation  
- See **[Middleware](/concepts/middleware/)** for request/response processing

---

**Source**: [`examples/01-basic-routing.py`](https://github.com/nijaru/zenith/blob/main/examples/01-basic-routing.py)