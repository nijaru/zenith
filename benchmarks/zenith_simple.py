"""Simplified Zenith benchmark application."""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from zenith import Zenith


# Models
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    created_at: Mapped[datetime]


class UserModel(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


class CreateUserModel(BaseModel):
    name: str
    email: str


# Database setup
engine = create_async_engine("sqlite+aiosqlite:///:memory:")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# App
app = Zenith()


# Startup
@app.on_startup
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data
    async with AsyncSessionLocal() as session:
        for i in range(100):
            user = User(
                name=f"User {i}",
                email=f"user{i}@example.com",
                created_at=datetime.now(),
            )
            session.add(user)
        await session.commit()


# Routes
@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}


@app.get("/users/{user_id}")
async def get_user(user_id: int) -> UserModel:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return UserModel(
                id=user.id, name=user.name, email=user.email, created_at=user.created_at
            )
        return {"error": "User not found"}


@app.get("/users")
async def list_users(limit: int = 100) -> list[UserModel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(limit))
        users = result.scalars().all()
        return [
            UserModel(
                id=user.id, name=user.name, email=user.email, created_at=user.created_at
            )
            for user in users
        ]


@app.post("/users")
async def create_user(data: CreateUserModel) -> UserModel:
    async with AsyncSessionLocal() as session:
        user = User(name=data.name, email=data.email, created_at=datetime.now())
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return UserModel(
            id=user.id, name=user.name, email=user.email, created_at=user.created_at
        )


@app.get("/protected")
async def protected_route():
    # Simplified - no actual auth check for benchmark
    return {"user": {"id": 1, "email": "test@example.com"}}


@app.post("/validate")
async def validate_data(data: CreateUserModel):
    return {"validated": True, "data": data.model_dump()}


@app.post("/upload")
async def upload_file():
    # Simplified - no actual file handling
    return {"size": 10000, "message": "File processed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
