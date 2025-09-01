# Examples

> Real-world Zenith applications demonstrating best practices and common patterns

## Example Applications

### 📝 [Blog API](https://github.com/zenith-framework/examples/tree/main/blog-api)
Complete blog platform with user authentication, post management, and file uploads.

**Features:**
- JWT authentication with refresh tokens
- CRUD operations for posts and comments  
- Image upload for post thumbnails
- User roles and permissions
- PostgreSQL with migrations
- Comprehensive test suite

**Key Concepts Demonstrated:**
- Context-driven architecture
- Database relationships with SQLAlchemy
- File upload handling
- Authentication middleware
- API testing with TestClient

### 🛒 [E-commerce API](https://github.com/zenith-framework/examples/tree/main/ecommerce-api)
Scalable e-commerce backend with products, orders, and payment processing.

**Features:**
- Product catalog with categories and variants
- Shopping cart and checkout flow
- Order management and tracking
- Payment integration (Stripe)
- Inventory tracking
- Admin dashboard API

**Key Concepts Demonstrated:**
- Complex business logic in contexts
- Event-driven architecture  
- External service integration
- Background task processing
- Performance optimization

### 💬 [Chat API](https://github.com/zenith-framework/examples/tree/main/chat-api)
Real-time chat application with WebSocket support and message history.

**Features:**
- Real-time messaging with WebSockets
- Chat rooms and direct messages
- Message history and search
- User presence tracking
- File sharing in chats
- Message encryption

**Key Concepts Demonstrated:**
- WebSocket handling
- Real-time event broadcasting
- Message queuing with Redis
- Database optimization for chat
- Security for real-time apps

### 🎯 [Task Management API](https://github.com/zenith-framework/examples/tree/main/task-api)
Project management tool with teams, projects, and task tracking.

**Features:**
- Team and project organization
- Task creation and assignment
- Progress tracking and reporting
- Time tracking
- File attachments
- Activity feeds

**Key Concepts Demonstrated:**
- Multi-tenant architecture
- Complex authorization rules
- Data aggregation and reporting
- Background job processing
- Integration testing patterns

### 🏥 [Healthcare API](https://github.com/zenith-framework/examples/tree/main/healthcare-api)
HIPAA-compliant healthcare management system.

**Features:**
- Patient and provider management
- Appointment scheduling
- Medical records with privacy controls
- Prescription management
- Audit logging
- FHIR integration

**Key Concepts Demonstrated:**
- Security and compliance patterns
- Audit trail implementation
- Data privacy controls
- External API integration
- Comprehensive error handling

### 🎮 [Gaming Leaderboard API](https://github.com/zenith-framework/examples/tree/main/gaming-api)
High-performance gaming backend with leaderboards and achievements.

**Features:**
- Player profiles and statistics
- Real-time leaderboards
- Achievement system
- Match history
- Game session tracking
- Anti-cheat measures

**Key Concepts Demonstrated:**
- High-performance data structures
- Real-time rankings
- Gaming-specific security
- Performance monitoring
- Load testing strategies

## Mini Examples

### Quick Start Templates

#### Basic API
```python
from zenith import Zenith

app = Zenith()

@app.get("/")
async def root():
    return {"message": "Hello Zenith!"}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}
```

#### With Authentication
```python
from zenith import Zenith
from zenith.auth import configure_auth
from zenith.core.routing import Auth

app = Zenith()
configure_auth(app, secret_key="your-secret-key")

@app.post("/auth/login")
async def login(credentials: LoginRequest):
    # Validate credentials
    token = create_access_token(user_id=user.id, email=user.email)
    return {"access_token": token}

@app.get("/profile")
async def get_profile(current_user = Auth(required=True)):
    return {"user": current_user}
```

#### With Database
```python
from zenith import Zenith
from zenith.core.context import Context

app = Zenith()
app.setup_database("postgresql://user:pass@localhost/db")

class UsersContext(Context):
    async def get_user(self, user_id: int):
        async with self.db.session() as session:
            return await session.get(User, user_id)

app.register_context(UsersContext)

@app.get("/users/{user_id}")
async def get_user(user_id: int, users: UsersContext = Context()):
    return await users.get_user(user_id)
```

#### File Upload
```python
from zenith import Zenith
from zenith.core.routing import File
from zenith.web.files import FileUploadConfig

app = Zenith()

upload_config = FileUploadConfig(
    max_file_size=5 * 1024 * 1024,  # 5MB
    allowed_extensions=[".jpg", ".png"],
    upload_dir="./uploads"
)

@app.post("/upload")
async def upload_file(file = File("image", upload_config)):
    return {
        "filename": file.filename,
        "size": file.size,
        "url": f"/uploads/{file.filename}"
    }
```

## Code Patterns

### Error Handling
```python
from zenith.middleware.exceptions import NotFoundException, ValidationException

class PostsContext(Context):
    async def get_post(self, post_id: int):
        post = await self.db.get(Post, post_id)
        if not post:
            raise NotFoundException(f"Post {post_id} not found")
        return post
    
    async def create_post(self, post_data: dict):
        if not post_data.get("title"):
            raise ValidationException("Title is required")
        return await self.db.create(Post, post_data)
```

### Background Tasks
```python
import asyncio
from zenith.tasks import BackgroundTasks

app = Zenith()

async def send_email(to: str, subject: str, body: str):
    # Send email logic
    await email_service.send(to, subject, body)

@app.post("/users")
async def create_user(user: UserCreate, background_tasks: BackgroundTasks):
    new_user = await users.create_user(user)
    
    # Send welcome email in background
    background_tasks.add_task(
        send_email,
        new_user.email,
        "Welcome!",
        "Thanks for joining!"
    )
    
    return new_user
```

### Caching
```python
from zenith.cache import cache, cache_key

class PostsContext(Context):
    @cache(expire=300)  # 5 minutes
    async def get_popular_posts(self):
        return await self.db.query(Post).order_by(Post.views.desc()).limit(10)
    
    async def update_post(self, post_id: int, data: dict):
        post = await self.db.update(Post, post_id, data)
        
        # Invalidate related cache
        await cache.delete(cache_key("popular_posts"))
        await cache.delete(cache_key(f"post_{post_id}"))
        
        return post
```

### Testing Patterns
```python
import pytest
from zenith.testing import TestClient, TestContext

@pytest.fixture
async def app():
    app = Zenith(debug=True)
    app.setup_database("sqlite:///:memory:")
    return app

@pytest.fixture
async def client(app):
    async with TestClient(app) as c:
        yield c

@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post("/users", json={
        "name": "John Doe",
        "email": "john@example.com"
    })
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "John Doe"
    assert "id" in data

@pytest.mark.asyncio  
async def test_users_context():
    async with TestContext(UsersContext) as users:
        user = await users.create_user({
            "name": "Jane",
            "email": "jane@example.com"
        })
        assert user.name == "Jane"
```

## Project Templates

### Microservice Template
```
my-service/
├── src/
│   └── my_service/
│       ├── __init__.py
│       ├── main.py
│       ├── contexts/
│       │   ├── __init__.py
│       │   └── users.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── user.py
│       └── routes/
│           ├── __init__.py
│           └── users.py
├── tests/
├── alembic/
├── docker-compose.yml
└── pyproject.toml
```

### Monolith Template  
```
my-app/
├── src/
│   └── my_app/
│       ├── __init__.py
│       ├── main.py
│       ├── contexts/
│       │   ├── auth.py
│       │   ├── users.py
│       │   ├── posts.py
│       │   └── comments.py
│       ├── models/
│       ├── middleware/
│       ├── utils/
│       └── static/
├── tests/
├── migrations/
├── uploads/
└── docs/
```

## Contributing Examples

We welcome community-contributed examples! To add your example:

1. Fork the [examples repository](https://github.com/zenith-framework/examples)
2. Create your example in a new directory
3. Include comprehensive README with setup instructions
4. Add tests demonstrating the key functionality  
5. Submit a pull request

### Example Requirements

- **Complete**: Runnable application, not just code snippets
- **Documented**: Clear README with setup and usage instructions
- **Tested**: Include tests covering main functionality
- **Modern**: Use current Python and Zenith best practices
- **Educational**: Focus on demonstrating specific concepts

---

**Need help with your Zenith application?** Join our [Discord community](https://discord.gg/zenith) or [discussions](https://github.com/zenith-framework/zenith/discussions)!