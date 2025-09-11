---
title: Quick Start
description: Build your first Zenith application in 5 minutes
---

import { Steps, Tabs, TabItem, Aside } from '@astrojs/starlight/components';

## Create Your First API

Let's build a simple blog API to demonstrate Zenith's core features.

<Steps>

1. **Create a new project**

   ```bash
   zen new blog-api --template api
   cd blog-api
   ```

2. **Create your application file**

   Create `app.py`:

   ```python
   from zenith import Zenith
   from pydantic import BaseModel
   from typing import List, Optional
   from datetime import datetime
   
   app = Zenith(
       title="Blog API",
       version="1.0.0",
       description="A simple blog API built with Zenith"
   )
   
   # In-memory storage for demo
   posts = []
   
   class Post(BaseModel):
       id: Optional[int] = None
       title: str
       content: str
       author: str
       created_at: Optional[datetime] = None
       updated_at: Optional[datetime] = None
   
   @app.get("/")
   async def root():
       return {
           "message": "Welcome to Blog API",
           "docs": "/docs",
           "health": "/health"
       }
   
   @app.get("/posts", response_model=List[Post])
   async def get_posts():
       """Get all blog posts."""
       return posts
   
   @app.post("/posts", response_model=Post, status_code=201)
   async def create_post(post: Post):
       """Create a new blog post."""
       post.id = len(posts) + 1
       post.created_at = datetime.utcnow()
       post.updated_at = datetime.utcnow()
       posts.append(post)
       return post
   
   @app.get("/posts/{post_id}", response_model=Post)
   async def get_post(post_id: int):
       """Get a specific blog post."""
       for post in posts:
           if post.id == post_id:
               return post
       raise HTTPException(404, "Post not found")
   
   @app.put("/posts/{post_id}", response_model=Post)
   async def update_post(post_id: int, updated_post: Post):
       """Update a blog post."""
       for i, post in enumerate(posts):
           if post.id == post_id:
               updated_post.id = post_id
               updated_post.created_at = post.created_at
               updated_post.updated_at = datetime.utcnow()
               posts[i] = updated_post
               return updated_post
       raise HTTPException(404, "Post not found")
   
   @app.delete("/posts/{post_id}")
   async def delete_post(post_id: int):
       """Delete a blog post."""
       for i, post in enumerate(posts):
           if post.id == post_id:
               posts.pop(i)
               return {"message": "Post deleted"}
       raise HTTPException(404, "Post not found")
   
   # Health check endpoint
   @app.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "timestamp": datetime.utcnow(),
           "version": app.version
       }
   ```

3. **Run the development server**

   ```bash
   zen server --reload
   # Or use uvicorn directly
   uvicorn app:app --reload
   ```

4. **Test your API**

   Your API is now running at `http://localhost:8000`

   <Tabs>
     <TabItem label="curl">
       ```bash
       # Create a post
       curl -X POST http://localhost:8000/posts \
         -H "Content-Type: application/json" \
         -d '{
           "title": "Hello Zenith",
           "content": "This is my first post!",
           "author": "Alice"
         }'
       
       # Get all posts
       curl http://localhost:8000/posts
       
       # Get a specific post
       curl http://localhost:8000/posts/1
       ```
     </TabItem>
     <TabItem label="httpie">
       ```bash
       # Create a post
       http POST localhost:8000/posts \
         title="Hello Zenith" \
         content="This is my first post!" \
         author="Alice"
       
       # Get all posts
       http localhost:8000/posts
       
       # Get a specific post
       http localhost:8000/posts/1
       ```
     </TabItem>
     <TabItem label="Python">
       ```python
       import httpx
       
       # Create a post
       response = httpx.post("http://localhost:8000/posts", json={
           "title": "Hello Zenith",
           "content": "This is my first post!",
           "author": "Alice"
       })
       print(response.json())
       
       # Get all posts
       response = httpx.get("http://localhost:8000/posts")
       print(response.json())
       ```
     </TabItem>
   </Tabs>

5. **Explore the automatic documentation**

   Visit `http://localhost:8000/docs` to see the interactive API documentation

</Steps>

## Add a Database

Let's evolve our API to use a real database with SQLModel:

```python
from zenith import Zenith
from zenith.db import SQLModel, Field, create_engine, Session
from sqlmodel import select
from typing import Optional
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///blog.db"
engine = create_engine(DATABASE_URL)

app = Zenith(title="Blog API with Database")

class Post(SQLModel, table=True):
    """Blog post model - works as both Pydantic model and database table."""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    author: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

@app.on_event("startup")
async def on_startup():
    """Create database tables on startup."""
    SQLModel.metadata.create_all(engine)

@app.get("/posts")
async def get_posts(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all posts with pagination."""
    statement = select(Post).offset(skip).limit(limit)
    posts = session.exec(statement).all()
    return posts

@app.post("/posts", response_model=Post)
async def create_post(
    post: Post,
    session: Session = Depends(get_session)
):
    """Create a new post in the database."""
    session.add(post)
    session.commit()
    session.refresh(post)
    return post
```

## Add Authentication

Protect your endpoints with JWT authentication:

```python
from zenith.auth import Auth, create_access_token, get_current_user
from zenith.auth.password import hash_password, verify_password

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    is_active: bool = Field(default=True)

@app.post("/auth/register")
async def register(
    username: str,
    email: str,
    password: str,
    session: Session = Depends(get_session)
):
    """Register a new user."""
    # Check if user exists
    existing = session.exec(
        select(User).where(User.email == email)
    ).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    
    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password)
    )
    session.add(user)
    session.commit()
    
    # Generate token
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/login")
async def login(
    email: str,
    password: str,
    session: Session = Depends(get_session)
):
    """Login and get access token."""
    user = session.exec(
        select(User).where(User.email == email)
    ).first()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# Protected endpoint
@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    """Only accessible with valid token."""
    return {"message": f"Hello {user.username}!"}
```

## Add Middleware

Enhance your API with production-ready middleware:

```python
from zenith.middleware import (
    CORSMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestIDMiddleware
)

app = Zenith(
    title="Production Blog API",
    middleware=[
        CORSMiddleware({
            "allow_origins": ["http://localhost:3000"],
            "allow_credentials": True
        }),
        RateLimitMiddleware({
            "requests_per_minute": 60
        }),
        SecurityHeadersMiddleware({
            "force_https": True
        }),
        RequestIDMiddleware()
    ]
)
```

<Aside type="tip">
  **Pro Tip**: Use environment variables for configuration:
  
  ```python
  import os
  from dotenv import load_dotenv
  
  load_dotenv()
  
  app = Zenith(
      debug=os.getenv("DEBUG", "false").lower() == "true",
      database_url=os.getenv("DATABASE_URL"),
      secret_key=os.getenv("SECRET_KEY")
  )
  ```
</Aside>

## What's Next?

Congratulations! You've built your first Zenith API. Here's what to explore next:

- **[Context System](/concepts/contexts)** - Organize business logic cleanly
- **[Background Tasks](/features/background-tasks)** - Process tasks asynchronously
- **[WebSockets](/features/websockets)** - Real-time communication
- **[Testing](/features/testing)** - Write comprehensive tests
- **[Deployment](/deployment/docker)** - Deploy to production

## Complete Example

Find the complete blog API example with all features at:
[github.com/nijaru/zenith/examples/blog-api](https://github.com/nijaru/zenith/tree/main/examples/blog-api)