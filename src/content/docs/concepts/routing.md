---
title: Routing
description: Define and organize API endpoints in Zenith
---

import { Tabs, TabItem, Aside } from '@astrojs/starlight/components';

## Route Definition

Zenith provides an intuitive decorator-based routing system with full type safety.

### Basic Routes

```python
from zenith import Zenith

app = Zenith()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/items")
async def create_item(item: dict):
    return {"created": item}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: dict):
    return {"updated": item_id, "data": item}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return {"deleted": item_id}
```

### Path Parameters

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    # Matches /files/documents/report.pdf
    return {"file": file_path}
```

### Query Parameters

```python
from typing import Optional

@app.get("/search")
async def search(
    q: str,
    limit: int = 10,
    offset: int = 0,
    sort: Optional[str] = None
):
    return {
        "query": q,
        "limit": limit,
        "offset": offset,
        "sort": sort
    }
```

## Request Bodies

### With Pydantic Models

```python
from pydantic import BaseModel
from datetime import datetime

class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = False
    tags: list[str] = []

@app.post("/posts")
async def create_post(post: PostCreate):
    # Automatic validation and parsing
    return {"created": post.model_dump()}
```

### File Uploads

```python
from zenith import UploadFile, File

@app.post("/upload")
async def upload_file(file: UploadFile = File()):
    contents = await file.read()
    return {
        "filename": file.filename,
        "size": len(contents),
        "content_type": file.content_type
    }

@app.post("/upload-multiple")
async def upload_multiple(files: list[UploadFile] = File()):
    return {
        "uploaded": [f.filename for f in files]
    }
```

## Response Models

```python
class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author: str
    created_at: datetime
    tags: list[str]

@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int) -> PostResponse:
    # Return value is automatically validated and serialized
    return PostResponse(
        id=post_id,
        title="Example Post",
        content="Content here",
        author="Alice",
        created_at=datetime.utcnow(),
        tags=["example"]
    )
```

## Router Organization

### Creating Routers

```python
# routes/users.py
from zenith import Router

router = Router(prefix="/users", tags=["Users"])

@router.get("/")
async def list_users():
    return {"users": []}

@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

@router.post("/")
async def create_user(user: dict):
    return {"created": user}
```

### Including Routers

```python
# main.py
from zenith import Zenith
from routes import users, posts, auth

app = Zenith()

# Include routers
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(auth.router, prefix="/api/auth")
```

### Nested Routers

```python
# Create parent router
api_router = Router(prefix="/api/v1")

# Create child routers
users_router = Router(prefix="/users", tags=["Users"])
posts_router = Router(prefix="/posts", tags=["Posts"])

# Include child routers in parent
api_router.include_router(users_router)
api_router.include_router(posts_router)

# Include parent in app
app.include_router(api_router)
```

## Dependency Injection

```python
from zenith import Depends

async def get_db():
    """Database dependency."""
    db = DatabaseSession()
    try:
        yield db
    finally:
        await db.close()

async def get_current_user(token: str = Header()):
    """Extract user from token."""
    user = decode_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user

@app.get("/protected")
async def protected_route(
    user = Depends(get_current_user),
    db = Depends(get_db)
):
    # Dependencies are automatically injected
    return {"user": user, "db_connected": True}
```

## Route Configuration

### Status Codes

```python
@app.post("/items", status_code=201)
async def create_item(item: dict):
    return {"created": item}

@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    # No content returned
    pass
```

### Tags and Documentation

```python
@app.get(
    "/users",
    tags=["Users"],
    summary="List all users",
    description="""
    Retrieve a paginated list of all users.
    Requires authentication.
    """,
    response_description="List of users"
)
async def list_users():
    return {"users": []}
```

### Custom Responses

```python
from zenith import JSONResponse, HTMLResponse, FileResponse

@app.get("/json")
async def json_response():
    return JSONResponse(
        content={"message": "Custom JSON"},
        status_code=200,
        headers={"X-Custom": "Header"}
    )

@app.get("/html")
async def html_response():
    return HTMLResponse(
        content="<h1>Hello World</h1>",
        status_code=200
    )

@app.get("/download")
async def download_file():
    return FileResponse(
        path="/path/to/file.pdf",
        filename="document.pdf",
        media_type="application/pdf"
    )
```

## Advanced Routing

### Route Priority

```python
# More specific routes should be defined first
@app.get("/users/me")
async def get_current_user():
    return {"user": "current"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

### Regex Patterns

```python
@app.get("/items/{item_id:^[0-9]+$}")
async def get_item_numeric(item_id: str):
    # Only matches numeric IDs
    return {"item_id": int(item_id)}

@app.get("/items/{item_id:^[a-z]+$}")
async def get_item_alpha(item_id: str):
    # Only matches alphabetic IDs
    return {"item_id": item_id}
```

### Wildcard Routes

```python
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Catches all unmatched routes
    return {"path": full_path, "message": "Not found"}
```

<Aside type="tip">
  **Best Practice**: Organize routes by feature in separate router modules. This keeps your codebase maintainable as it grows.
</Aside>

## WebSocket Routes

```python
from zenith import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

## Testing Routes

```python
from zenith.testing import TestClient

async def test_routes():
    async with TestClient(app) as client:
        # Test GET
        response = await client.get("/")
        assert response.status_code == 200
        
        # Test POST
        response = await client.post(
            "/items",
            json={"name": "Test Item"}
        )
        assert response.status_code == 201
        
        # Test with headers
        response = await client.get(
            "/protected",
            headers={"Authorization": "Bearer token"}
        )
        assert response.status_code == 200
```

## Next Steps

- Learn about [Middleware](/concepts/middleware) for request processing
- Explore [Authentication](/concepts/authentication) for securing routes
- Understand [Database](/concepts/database) integration