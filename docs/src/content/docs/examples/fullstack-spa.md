---
title: Full-Stack SPA Example  
description: Build a complete full-stack application with Zenith serving both API endpoints and a React/Vue/Angular SPA
---

# Full-Stack SPA Example

This example demonstrates how to build a complete full-stack application using Zenith to serve both your API backend and frontend SPA (React, Vue, Angular, etc.) from a single server.

## Code Example

```python
from zenith import Zenith
from zenith.web.static import StaticFiles
from zenith.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json

app = Zenith(
    title="Full-Stack Todo App",
    description="Complete SPA application with Zenith backend"
)

# Add CORS for development
app.add_middleware(CORSMiddleware, {
    "allow_origins": ["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["*"]
})

# Data models
class TodoItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    user_id: int

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class User(BaseModel):
    id: int
    username: str
    email: str

# In-memory data store (replace with database in production)
todos_db: List[TodoItem] = []
users_db: List[User] = [
    User(id=1, username="alice", email="alice@example.com"),
    User(id=2, username="bob", email="bob@example.com")
]
next_todo_id = 1

# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint for the API"""
    return {"status": "healthy", "service": "todo-api"}

@app.get("/api/users", response_model=List[User])
async def get_users():
    """Get all users"""
    return users_db

@app.get("/api/users/{user_id}/todos", response_model=List[TodoItem])
async def get_user_todos(user_id: int):
    """Get todos for a specific user"""
    user_todos = [todo for todo in todos_db if todo.user_id == user_id]
    return user_todos

@app.post("/api/users/{user_id}/todos", response_model=TodoItem)
async def create_todo(user_id: int, todo: TodoCreate):
    """Create a new todo for a user"""
    global next_todo_id
    
    # Verify user exists
    user = next((u for u in users_db if u.id == user_id), None)
    if not user:
        return {"error": "User not found"}, 404
    
    new_todo = TodoItem(
        id=next_todo_id,
        title=todo.title,
        description=todo.description,
        user_id=user_id
    )
    
    todos_db.append(new_todo)
    next_todo_id += 1
    
    return new_todo

@app.get("/api/todos/{todo_id}", response_model=TodoItem)
async def get_todo(todo_id: int):
    """Get a specific todo by ID"""
    todo = next((t for t in todos_db if t.id == todo_id), None)
    if not todo:
        return {"error": "Todo not found"}, 404
    return todo

@app.put("/api/todos/{todo_id}", response_model=TodoItem)
async def update_todo(todo_id: int, update: TodoUpdate):
    """Update an existing todo"""
    todo = next((t for t in todos_db if t.id == todo_id), None)
    if not todo:
        return {"error": "Todo not found"}, 404
    
    # Update fields if provided
    if update.title is not None:
        todo.title = update.title
    if update.description is not None:
        todo.description = update.description
    if update.completed is not None:
        todo.completed = update.completed
    
    return todo

@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: int):
    """Delete a todo"""
    global todos_db
    original_length = len(todos_db)
    todos_db = [t for t in todos_db if t.id != todo_id]
    
    if len(todos_db) == original_length:
        return {"error": "Todo not found"}, 404
    
    return {"message": "Todo deleted successfully"}

@app.get("/api/stats")
async def get_stats():
    """Get application statistics"""
    total_todos = len(todos_db)
    completed_todos = len([t for t in todos_db if t.completed])
    
    return {
        "total_users": len(users_db),
        "total_todos": total_todos,
        "completed_todos": completed_todos,
        "completion_rate": (completed_todos / total_todos * 100) if total_todos > 0 else 0
    }

# Static file serving for SPA
# This will serve your built React/Vue/Angular app

# For production builds
if os.path.exists("./dist"):
    # Serve built SPA (e.g., from Vite, Create React App, Angular CLI)
    app.mount("/", StaticFiles(directory="dist", html=True), name="spa")
    
elif os.path.exists("./build"):
    # Alternative build directory (Create React App default)
    app.mount("/", StaticFiles(directory="build", html=True), name="spa")
    
elif os.path.exists("./public"):
    # Development/simple static files
    app.mount("/", StaticFiles(directory="public", html=True), name="spa")
    
else:
    # Fallback: serve a simple HTML page
    @app.get("/")
    async def spa_fallback():
        """Fallback SPA interface for development"""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Todo App - Zenith Full-Stack</title>
            <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .todo-item { padding: 10px; border: 1px solid #ddd; margin: 5px 0; border-radius: 5px; }
                .completed { background-color: #f0f8f0; text-decoration: line-through; }
                .user-section { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
                input, button, select { padding: 8px; margin: 5px; }
                .stats { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div id="app">
                <h1> Full-Stack Todo App with Zenith</h1>
                
                <div class="stats">
                    <h3> Statistics</h3>
                    <p>Total Users: {{ stats.total_users }}</p>
                    <p>Total Todos: {{ stats.total_todos }}</p>
                    <p>Completed: {{ stats.completed_todos }} ({{ stats.completion_rate.toFixed(1) }}%)</p>
                </div>
                
                <div class="user-section">
                    <h3>👤 Select User</h3>
                    <select v-model="selectedUserId" @change="loadUserTodos">
                        <option value="">Choose a user...</option>
                        <option v-for="user in users" :key="user.id" :value="user.id">
                            {{ user.username }} ({{ user.email }})
                        </option>
                    </select>
                </div>
                
                <div v-if="selectedUserId" class="user-section">
                    <h3> Add New Todo</h3>
                    <input 
                        v-model="newTodo.title" 
                        placeholder="Todo title" 
                        @keyup.enter="addTodo"
                    />
                    <input 
                        v-model="newTodo.description" 
                        placeholder="Description (optional)"
                        @keyup.enter="addTodo" 
                    />
                    <button @click="addTodo">Add Todo</button>
                </div>
                
                <div v-if="selectedUserId">
                    <h3>📝 Your Todos</h3>
                    <div v-for="todo in todos" :key="todo.id" class="todo-item" :class="{ completed: todo.completed }">
                        <h4>{{ todo.title }}</h4>
                        <p v-if="todo.description">{{ todo.description }}</p>
                        <label>
                            <input 
                                type="checkbox" 
                                :checked="todo.completed" 
                                @change="toggleTodo(todo)"
                            />
                            Completed
                        </label>
                        <button @click="deleteTodo(todo.id)" style="float: right; background: #ff4444; color: white;">
                            Delete
                        </button>
                    </div>
                    <div v-if="todos.length === 0">
                        <p>No todos yet. Add one above!</p>
                    </div>
                </div>
            </div>

            <script>
                const { createApp } = Vue;

                createApp({
                    data() {
                        return {
                            users: [],
                            todos: [],
                            stats: { total_users: 0, total_todos: 0, completed_todos: 0, completion_rate: 0 },
                            selectedUserId: '',
                            newTodo: {
                                title: '',
                                description: ''
                            }
                        };
                    },
                    
                    async mounted() {
                        await this.loadUsers();
                        await this.loadStats();
                    },
                    
                    methods: {
                        async loadUsers() {
                            const response = await fetch('/api/users');
                            this.users = await response.json();
                        },
                        
                        async loadStats() {
                            const response = await fetch('/api/stats');
                            this.stats = await response.json();
                        },
                        
                        async loadUserTodos() {
                            if (!this.selectedUserId) return;
                            
                            const response = await fetch(`/api/users/${this.selectedUserId}/todos`);
                            this.todos = await response.json();
                        },
                        
                        async addTodo() {
                            if (!this.newTodo.title.trim()) return;
                            
                            const response = await fetch(`/api/users/${this.selectedUserId}/todos`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(this.newTodo)
                            });
                            
                            if (response.ok) {
                                this.newTodo = { title: '', description: '' };
                                await this.loadUserTodos();
                                await this.loadStats();
                            }
                        },
                        
                        async toggleTodo(todo) {
                            const response = await fetch(`/api/todos/${todo.id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ completed: !todo.completed })
                            });
                            
                            if (response.ok) {
                                await this.loadUserTodos();
                                await this.loadStats();
                            }
                        },
                        
                        async deleteTodo(todoId) {
                            const response = await fetch(`/api/todos/${todoId}`, {
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                await this.loadUserTodos();
                                await this.loadStats();
                            }
                        }
                    }
                }).mount('#app');
            </script>
        </body>
        </html>
        """
        return html_content

# Custom 404 handler for SPA routing
@app.exception_handler(404)
async def spa_404_handler(request, exc):
    """Handle 404s by serving the SPA for client-side routing"""
    # Only serve SPA for non-API routes
    if request.url.path.startswith('/api/'):
        return {"error": "API endpoint not found"}, 404
        
    # For all other routes, serve the SPA (index.html)
    if os.path.exists("./dist/index.html"):
        with open("./dist/index.html", "r") as f:
            return f.read()
    elif os.path.exists("./build/index.html"):
        with open("./build/index.html", "r") as f:
            return f.read()
    else:
        # Fallback to our embedded SPA
        return await spa_fallback()

if __name__ == "__main__":
    import uvicorn
    
    print(" Starting Full-Stack Todo App")
    print(" API available at: http://localhost:8000/api/")
    print(" Web app available at: http://localhost:8000/")
    print(" API docs at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Key Features Demonstrated

### Full-Stack Architecture
- **API Backend**: Complete REST API with CRUD operations
- **SPA Frontend**: Serves React/Vue/Angular apps from the same server
- **Single Port**: Everything runs on one port - no CORS issues in production
- **Development Support**: CORS enabled for frontend dev servers

### Static File Serving
- **Built Apps**: Automatically detects `dist/` or `build/` directories
- **SPA Routing**: Handles client-side routing with 404 fallback
- **Development Mode**: Embedded Vue.js app for testing
- **Flexible**: Works with any SPA framework

### Production Features
- **API Versioning**: All API routes under `/api/` prefix
- **Error Handling**: Proper 404 handling for API vs SPA routes
- **Health Checks**: `/api/health` endpoint for monitoring
- **Statistics**: Application metrics and monitoring

## Frontend Integration Examples

### React (Create React App)
```bash
# Build React app
npm run build

# Zenith will automatically serve from ./build/
python fullstack_spa.py
```

### Vue (Vite)
```bash
# Build Vue app  
npm run build

# Zenith will automatically serve from ./dist/
python fullstack_spa.py
```

### Angular
```bash
# Build Angular app
ng build

# Zenith will automatically serve from ./dist/
python fullstack_spa.py
```

## Running the Example

1. **Save the code** as `fullstack_spa.py`
2. **Install dependencies**:
   ```bash
   pip install zenithweb uvicorn
   ```
3. **Run the server**:
   ```bash
   python fullstack_spa.py
   ```
4. **Open browser** to `http://localhost:8000`

## API Testing

```bash
# Get all users
curl http://localhost:8000/api/users

# Create a todo
curl -X POST http://localhost:8000/api/users/1/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Zenith", "description": "Build full-stack apps"}'

# Get user todos
curl http://localhost:8000/api/users/1/todos

# Get statistics
curl http://localhost:8000/api/stats
```

## Deployment Ready

This example is production-ready and includes:

- **Environment Configuration**: Easy to add database connections
- **Security Middleware**: CORS properly configured
- **Error Handling**: Proper API error responses
- **Health Checks**: For load balancer monitoring
- **SPA Support**: Handles client-side routing properly

## Next Steps

- Add **[Database Models](/zenith/concepts/models/)** for data persistence
- Explore **[Authentication](/zenith/concepts/authentication/)** for user security
- Learn **[SQLModel Integration](/zenith/examples/auto-generated/16-sqlmodel-integration/)** for advanced patterns

---

**Source**: [`examples/18-fullstack-spa.py`](https://github.com/nijaru/zenith/blob/main/examples/18-fullstack-spa.py)