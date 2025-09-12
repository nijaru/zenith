"""
Todo Database Example - Full database integration with Zenith

Demonstrates:
- SQLAlchemy database integration with SQLite
- Repository pattern for data access
- Context-based business logic
- CRUD operations with real persistence
- Async database operations
"""

from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from zenith import Context, Router, Service, Zenith
from zenith.db import Base, Database


# Database models
class TodoItem(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


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

    class Config:
        from_attributes = True


# Repository pattern for data access
class TodoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: TodoCreate) -> TodoItem:
        todo = TodoItem(title=data.title, description=data.description)
        self.session.add(todo)
        await self.session.commit()
        await self.session.refresh(todo)
        return todo

    async def get(self, todo_id: int) -> TodoItem | None:
        return await self.session.get(TodoItem, todo_id)

    async def list(self, completed: bool | None = None) -> list[TodoItem]:
        query = select(TodoItem)
        if completed is not None:
            query = query.where(TodoItem.completed == completed)
        query = query.order_by(TodoItem.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, todo_id: int, data: TodoUpdate) -> TodoItem | None:
        todo = await self.get(todo_id)
        if not todo:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(todo, field, value)

        await self.session.commit()
        await self.session.refresh(todo)
        return todo

    async def delete(self, todo_id: int) -> bool:
        todo = await self.get(todo_id)
        if not todo:
            return False

        await self.session.delete(todo)
        await self.session.commit()
        return True


# Global database instance
db: Database | None = None


# Business logic context
class TodosContext(Service):
    """Business logic for todo management with database persistence."""

    def __init__(self, container):
        super().__init__(container)

    async def _get_repository(self) -> TodoRepository:
        # Get database session
        if not db:
            raise RuntimeError("Database not initialized")

        # Use async context manager for session
        # Note: In production, this would be handled differently
        # to properly manage session lifecycle
        session = db.async_session()
        return TodoRepository(session)

    async def create_todo(self, data: TodoCreate) -> Todo:
        repo = await self._get_repository()
        todo = await repo.create(data)
        return Todo.model_validate(todo)

    async def get_todo(self, todo_id: int) -> Todo | None:
        repo = await self._get_repository()
        todo = await repo.get(todo_id)
        return Todo.model_validate(todo) if todo else None

    async def list_todos(self, completed: bool | None = None) -> list[Todo]:
        repo = await self._get_repository()
        todos = await repo.list(completed)
        return [Todo.model_validate(todo) for todo in todos]

    async def update_todo(self, todo_id: int, data: TodoUpdate) -> Todo | None:
        repo = await self._get_repository()
        todo = await repo.update(todo_id, data)
        return Todo.model_validate(todo) if todo else None

    async def delete_todo(self, todo_id: int) -> bool:
        repo = await self._get_repository()
        return await repo.delete(todo_id)


# Create application
app = Zenith()

# Register context
app.register_context("todoscontext", TodosContext)

# Create router
api = Router(prefix="/api/v1")


# Routes
@api.post("/todos")
async def create_todo(data: TodoCreate, todos: TodosContext = Context()) -> Todo:
    """Create a new todo item."""
    return await todos.create_todo(data)


@api.get("/todos")
async def list_todos(
    completed: bool | None = None, todos: TodosContext = Context()
) -> list[Todo]:
    """List todos, optionally filtered by completion status."""
    return await todos.list_todos(completed)


@api.get("/todos/{todo_id}")
async def get_todo(todo_id: int, todos: TodosContext = Context()) -> Todo:
    """Get a specific todo item."""
    todo = await todos.get_todo(todo_id)
    if not todo:
        raise ValueError(f"Todo {todo_id} not found")
    return todo


@api.patch("/todos/{todo_id}")
async def update_todo(
    todo_id: int, data: TodoUpdate, todos: TodosContext = Context()
) -> Todo:
    """Update a todo item."""
    todo = await todos.update_todo(todo_id, data)
    if not todo:
        raise ValueError(f"Todo {todo_id} not found")
    return todo


@api.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int, todos: TodosContext = Context()) -> dict:
    """Delete a todo item."""
    deleted = await todos.delete_todo(todo_id)
    if not deleted:
        raise ValueError(f"Todo {todo_id} not found")
    return {"message": "Todo deleted successfully"}


# Health check
@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "todo-db"}


# Database initialization
@app.on_startup
async def init_database():
    """Initialize database on startup."""
    global db
    # Use SQLite for this example
    db = Database("sqlite+aiosqlite:///todos.db", echo=True)
    await db.create_all()
    print("Database initialized")


@app.on_shutdown
async def close_database():
    """Close database connections on shutdown."""
    global db
    if db:
        await db.close()
    print("Database connections closed")


# Include router
app.include_router(api)

# Add documentation
app.add_docs(
    title="Todo Database API",
    description="Todo management with real database persistence",
    version="1.0.0",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True)
