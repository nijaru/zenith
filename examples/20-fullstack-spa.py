"""
🌐 Full-Stack SPA Example - Zenith + Frontend Framework

This example demonstrates how to use Zenith as both an API server and static file
server for modern frontend frameworks (React, Vue, SolidJS, Svelte, Angular).

Key Features Demonstrated:
- API endpoints for backend logic
- SPA file serving with client-side routing support
- Automatic static asset detection and serving
- Development vs production configuration
- Hybrid API + frontend application pattern

Project Structure:
my-app/
├── frontend/         # Your SPA (React/Vue/SolidJS/etc.)
│   ├── src/
│   ├── dist/        # Built frontend files
│   └── package.json
├── backend/         # Zenith backend
│   ├── main.py      # This file
│   └── services/
└── static/          # Additional static assets

Frontend Build Commands:
- SolidJS: `npm run build` (outputs to dist/)
- React: `npm run build` (outputs to build/)
- Vue: `npm run build` (outputs to dist/)
- Svelte: `npm run build` (outputs to build/)
- Angular: `ng build` (outputs to dist/app-name/)

Run with: python examples/17-fullstack-spa.py
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from zenith import Inject, Service, Zenith
from zenith.web.static import serve_css_js, serve_images

app = Zenith(
    title="Full-Stack SPA Application",
    version="1.0.0",
    description="Modern SPA backend with Zenith",
)

# ============================================================================
# MODELS - API Data Transfer Objects
# ============================================================================


class User(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


class UserCreate(BaseModel):
    name: str
    email: str


class Task(BaseModel):
    id: int
    title: str
    description: str = ""
    completed: bool = False
    user_id: int
    created_at: datetime


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    user_id: int


# ============================================================================
# SERVICES - Business Logic
# ============================================================================


class UserService(Service):
    """User management service."""

    def __init__(self):
        # In real app: database connection
        self.users = [
            User(
                id=1, name="Alice", email="alice@example.com", created_at=datetime.now()
            ),
            User(id=2, name="Bob", email="bob@example.com", created_at=datetime.now()),
        ]
        self.next_id = 3

    async def get_all_users(self) -> list[User]:
        """Get all users."""
        return self.users

    async def get_user(self, user_id: int) -> User | None:
        """Get user by ID."""
        return next((u for u in self.users if u.id == user_id), None)

    async def create_user(self, user_data: UserCreate) -> User:
        """Create new user."""
        user = User(
            id=self.next_id,
            name=user_data.name,
            email=user_data.email,
            created_at=datetime.now(),
        )
        self.users.append(user)
        self.next_id += 1
        return user


class TaskService(Service):
    """Task management service."""

    def __init__(self):
        # In real app: database connection
        self.tasks = [
            Task(
                id=1,
                title="Learn Zenith",
                description="Build a full-stack app",
                user_id=1,
                created_at=datetime.now(),
            ),
            Task(
                id=2,
                title="Deploy to production",
                description="Set up CI/CD",
                user_id=1,
                completed=True,
                created_at=datetime.now(),
            ),
        ]
        self.next_id = 3

    async def get_user_tasks(self, user_id: int) -> list[Task]:
        """Get all tasks for a user."""
        return [t for t in self.tasks if t.user_id == user_id]

    async def create_task(self, task_data: TaskCreate) -> Task:
        """Create new task."""
        task = Task(
            id=self.next_id,
            title=task_data.title,
            description=task_data.description,
            user_id=task_data.user_id,
            created_at=datetime.now(),
        )
        self.tasks.append(task)
        self.next_id += 1
        return task

    async def update_task(self, task_id: int, completed: bool) -> Task | None:
        """Update task completion status."""
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task:
            task.completed = completed
        return task


# ============================================================================
# API ROUTES - Backend Endpoints
# ============================================================================


# Users API
@app.get("/api/users", response_model=list[User], tags=["Users"])
async def get_users(users: UserService = Inject(UserService)):
    """Get all users."""
    return await users.get_all_users()


@app.get("/api/users/{user_id}", response_model=User, tags=["Users"])
async def get_user(user_id: int, users: UserService = Inject(UserService)):
    """Get user by ID."""
    user = await users.get_user(user_id)
    if not user:
        from zenith import not_found

        raise not_found(f"User {user_id} not found")
    return user


@app.post("/api/users", response_model=User, tags=["Users"])
async def create_user(user_data: UserCreate, users: UserService = Inject(UserService)):
    """Create new user."""
    return await users.create_user(user_data)


# Tasks API
@app.get("/api/users/{user_id}/tasks", response_model=list[Task], tags=["Tasks"])
async def get_user_tasks(user_id: int, tasks: TaskService = Inject(TaskService)):
    """Get tasks for a user."""
    return await tasks.get_user_tasks(user_id)


@app.post("/api/tasks", response_model=Task, tags=["Tasks"])
async def create_task(task_data: TaskCreate, tasks: TaskService = Inject(TaskService)):
    """Create new task."""
    return await tasks.create_task(task_data)


@app.patch("/api/tasks/{task_id}", response_model=Task, tags=["Tasks"])
async def update_task(task_id: int, completed: bool, tasks: TaskService = Inject(TaskService)):
    """Update task completion status."""
    task = await tasks.update_task(task_id, completed)
    if not task:
        from zenith import not_found

        raise not_found(f"Task {task_id} not found")
    return task


# Health endpoint
@app.get("/api/health")
async def api_health():
    """API health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# STATIC FILE SERVING - Frontend Assets
# ============================================================================


def setup_frontend_serving():
    """Configure frontend serving based on environment and available directories."""

    # Common frontend build directories to check
    frontend_dirs = [
        ("frontend/dist", "SolidJS/Vue build output"),
        ("frontend/build", "React build output"),
        ("build", "Svelte build output"),
        ("dist", "General dist directory"),
        ("public", "Static public files"),
    ]

    # Find first available frontend directory
    frontend_dir = None
    for dir_path, description in frontend_dirs:
        if Path(dir_path).exists() and Path(dir_path).is_dir():
            # Check if directory has files
            if any(Path(dir_path).iterdir()):
                frontend_dir = dir_path
                print(f"📁 Found frontend files: {dir_path} ({description})")
                break

    if frontend_dir:
        # Production vs development caching
        cache_time = 60 if app.config.debug else 86400  # 1 min dev, 1 day prod

        # Mount the SPA with client-side routing support (new clean API)
        app.spa(frontend_dir, max_age=cache_time)
        print(f"🌐 SPA serving: / -> {frontend_dir}")
        print(
            f"⚡ Cache policy: {cache_time}s ({'development' if app.config.debug else 'production'})"
        )
    else:
        # No frontend found, serve a simple HTML page
        from starlette.responses import HTMLResponse

        @app.get("/")
        async def frontend_placeholder():
            """Placeholder when no frontend build is found."""
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Zenith Full-Stack App</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                           max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }
                    .api-example { background: #f5f5f5; padding: 1rem; border-radius: 8px; }
                    code { background: #e1e1e1; padding: 0.2em 0.4em; border-radius: 3px; }
                </style>
            </head>
            <body>
                <h1>🚀 Zenith Full-Stack Application</h1>
                <p>Your Zenith API is running! Build your frontend and place it in one of these directories:</p>
                <ul>
                    <li><code>frontend/dist/</code> - SolidJS, Vue</li>
                    <li><code>frontend/build/</code> - React</li>
                    <li><code>dist/</code> - General build output</li>
                    <li><code>public/</code> - Static files</li>
                </ul>

                <h2>API Endpoints</h2>
                <div class="api-example">
                    <p><strong>Users:</strong></p>
                    <p>GET <a href="/api/users">/api/users</a> - List all users</p>
                    <p>GET <a href="/api/users/1">/api/users/1</a> - Get user by ID</p>
                    <p>POST /api/users - Create user</p>

                    <p><strong>Tasks:</strong></p>
                    <p>GET <a href="/api/users/1/tasks">/api/users/1/tasks</a> - User's tasks</p>
                    <p>POST /api/tasks - Create task</p>
                    <p>PATCH /api/tasks/1 - Update task</p>

                    <p><strong>Documentation:</strong></p>
                    <p><a href="/docs">📖 API Documentation</a></p>
                </div>

                <h2>Frontend Examples</h2>
                <p>Here are fetch examples for your frontend:</p>
                <div class="api-example">
                    <pre><code>// Fetch users
const users = await fetch('/api/users').then(r => r.json());

// Create user
const newUser = await fetch('/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'John', email: 'john@example.com' })
}).then(r => r.json());

// Fetch user's tasks
const tasks = await fetch('/api/users/1/tasks').then(r => r.json());</code></pre>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(html)

        print("📄 No frontend build found - serving API documentation page")


# Additional static asset serving
def setup_static_assets():
    """Set up additional static asset serving."""

    # Serve additional assets with appropriate caching
    static_configs = [
        ("assets", serve_css_js, 86400 * 30),  # CSS/JS: 30 days
        ("images", serve_images, 86400 * 7),  # Images: 7 days
        ("uploads", "serve_uploads", 3600),  # Uploads: 1 hour
    ]

    for dir_name, _serve_func, max_age in static_configs:
        if Path(dir_name).exists():
            # Use Zenith's clean static serving API
            app.mount_static(f"/{dir_name}", dir_name, max_age=max_age)
            print(f"📂 Static assets: /{dir_name} -> {dir_name}/")


# ============================================================================
# APPLICATION SETUP
# ============================================================================

if __name__ == "__main__":
    print("🌐 Starting Zenith Full-Stack Application")
    print("=" * 50)

    # Configure frontend and static asset serving
    setup_frontend_serving()
    setup_static_assets()

    # Show configuration
    print(f"🔧 Environment: {'Development' if app.config.debug else 'Production'}")
    print("📍 Server: http://localhost:8017")
    print("📖 API Docs: http://localhost:8017/docs")
    print("🏥 Health: http://localhost:8017/api/health")

    print("\n💡 Frontend Framework Support:")
    print("   • SolidJS: Place build output in frontend/dist/")
    print("   • React: Place build output in frontend/build/")
    print("   • Vue: Place build output in frontend/dist/")
    print("   • Svelte: Place build output in build/")
    print("   • Angular: Place build output in dist/app-name/")

    print("\n🚀 Starting server...")

    app.run(
        host="127.0.0.1",
        port=8017,
        reload=app.config.debug,  # Auto-reload in development
    )
