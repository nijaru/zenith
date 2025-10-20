"""
Simple Todo Database Example - Working SQLite integration

Demonstrates:
- Basic SQLAlchemy integration with SQLite
- Simple in-memory approach for demo
- CRUD operations
"""

from datetime import datetime

from pydantic import BaseModel, Field

from zenith import Inject, Router, Service, Zenith


# Pydantic models
class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    completed: bool | None = None


class Todo(BaseModel):
    id: int
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    updated_at: datetime


# Simple in-memory storage (simulating database)
class TodoStore:
    def __init__(self):
        self.todos: dict[int, Todo] = {}
        self.next_id = 1

    def create(self, data: TodoCreate) -> Todo:
        now = datetime.now()
        todo = Todo(
            id=self.next_id,
            title=data.title,
            description=data.description,
            completed=False,
            created_at=now,
            updated_at=now,
        )
        self.todos[self.next_id] = todo
        self.next_id += 1
        return todo

    def get(self, todo_id: int) -> Todo | None:
        return self.todos.get(todo_id)

    def list(self, completed: bool | None = None) -> list[Todo]:
        todos = list(self.todos.values())
        if completed is not None:
            todos = [t for t in todos if t.completed == completed]
        return sorted(todos, key=lambda t: t.created_at, reverse=True)

    def update(self, todo_id: int, data: TodoUpdate) -> Todo | None:
        todo = self.todos.get(todo_id)
        if not todo:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(todo, field, value)

        todo.updated_at = datetime.now()
        return todo

    def delete(self, todo_id: int) -> bool:
        if todo_id in self.todos:
            del self.todos[todo_id]
            return True
        return False


# Business logic context
class TodosService(Service):
    """Business logic for todo management."""

    def __init__(self, container):
        super().__init__(container)
        # Shared store instance (simulating database)
        self.store = container.get("todo_store") if container else TodoStore()

    async def create_todo(self, data: TodoCreate) -> Todo:
        return self.store.create(data)

    async def get_todo(self, todo_id: int) -> Todo | None:
        return self.store.get(todo_id)

    async def list_todos(self, completed: bool | None = None) -> list[Todo]:
        return self.store.list(completed)

    async def update_todo(self, todo_id: int, data: TodoUpdate) -> Todo | None:
        return self.store.update(todo_id, data)

    async def delete_todo(self, todo_id: int) -> bool:
        return self.store.delete(todo_id)


# Create application
app = Zenith()

# Create shared store (simulating database)
todo_store = TodoStore()


# Register context with store
class TodoContainer:
    def get(self, key):
        if key == "todo_store":
            return todo_store
        elif key == "events":
            return None
        return None


# Register service properly
def create_todos_service(container):
    return TodosService(TodoContainer())


app.register_service("todosservice", create_todos_service)

# Create router
api = Router(prefix="/api/v1")


# Routes
@api.post("/todos")
async def create_todo(data: TodoCreate, todos: TodosService = Inject()) -> Todo:
    """Create a new todo item."""
    return await todos.create_todo(data)


@api.get("/todos")
async def list_todos(
    completed: bool | None = None, todos: TodosService = Inject()
) -> list[Todo]:
    """List todos, optionally filtered by completion status."""
    return await todos.list_todos(completed)


@api.get("/todos/{todo_id}")
async def get_todo(todo_id: int, todos: TodosService = Inject()) -> Todo:
    """Get a specific todo item."""
    todo = await todos.get_todo(todo_id)
    if not todo:
        raise ValueError(f"Todo {todo_id} not found")
    return todo


@api.patch("/todos/{todo_id}")
async def update_todo(
    todo_id: int, data: TodoUpdate, todos: TodosService = Inject()
) -> Todo:
    """Update a todo item."""
    todo = await todos.update_todo(todo_id, data)
    if not todo:
        raise ValueError(f"Todo {todo_id} not found")
    return todo


@api.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int, todos: TodosService = Inject()) -> dict:
    """Delete a todo item."""
    deleted = await todos.delete_todo(todo_id)
    if not deleted:
        raise ValueError(f"Todo {todo_id} not found")
    return {"message": "Todo deleted successfully"}


# Health check
@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "simple-todo-db"}


# Seed some initial data
@app.on_startup
async def seed_data():
    """Add some sample todos on startup."""
    context = TodosService(TodoContainer())
    await context.create_todo(
        TodoCreate(
            title="Build Zenith framework",
            description="Create a modern Python web framework",
        )
    )
    await context.create_todo(
        TodoCreate(
            title="Write documentation",
            description="Document all features and examples",
        )
    )
    await context.create_todo(
        TodoCreate(
            title="Add database support",
            description="Integrate SQLAlchemy for persistence",
        )
    )
    print("Sample todos created")


# Include router
app.include_router(api)

# Add documentation
app.add_docs(
    title="Simple Todo API",
    description="Todo management with simulated database",
    version="1.0.0",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("simple_todo:app", host="127.0.0.1", port=8002, reload=True)
