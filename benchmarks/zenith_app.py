"""Zenith benchmark application."""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from zenith import Auth, Context, Zenith
from zenith.auth import JWTManager
from zenith.web.responses import JSONResponse


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


# Context
class UsersContext(Context):
    def __init__(self):
        super().__init__()
        self.db = None

    async def initialize(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        self.db = AsyncSessionLocal

        # Seed data
        async with self.db() as session:
            for i in range(100):
                user = User(
                    name=f"User {i}",
                    email=f"user{i}@example.com",
                    created_at=datetime.now(),
                )
                session.add(user)
            await session.commit()

    async def get_user(self, user_id: int) -> UserModel | None:
        async with self.db() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                return UserModel(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    created_at=user.created_at,
                )
            return None

    async def list_users(self, limit: int = 100) -> list[UserModel]:
        async with self.db() as session:
            result = await session.execute(select(User).limit(limit))
            users = result.scalars().all()
            return [
                UserModel(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    created_at=user.created_at,
                )
                for user in users
            ]

    async def create_user(self, data: CreateUserModel) -> UserModel:
        async with self.db() as session:
            user = User(name=data.name, email=data.email, created_at=datetime.now())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return UserModel(
                id=user.id, name=user.name, email=user.email, created_at=user.created_at
            )


# App
app = Zenith()

# Configure auth
jwt_manager = JWTManager(secret_key="benchmark-secret-key-123")
app.dependency_overrides[Auth] = lambda: jwt_manager

# Initialize context
users_context = UsersContext()


@app.on_startup
async def startup():
    await users_context.initialize()
    app.dependency_overrides[UsersContext] = lambda: users_context


# Routes
@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}


@app.get("/users/{user_id}")
async def get_user(user_id: int, users: UsersContext = Context()) -> UserModel:
    user = await users.get_user(user_id)
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return user


@app.get("/users")
async def list_users(
    limit: int = 100, users: UsersContext = Context()
) -> list[UserModel]:
    return await users.list_users(limit)


@app.post("/users")
async def create_user(
    data: CreateUserModel, users: UsersContext = Context()
) -> UserModel:
    return await users.create_user(data)


@app.get("/protected")
async def protected_route(current_user=Auth(required=True)):
    return {"user": current_user}


@app.post("/validate")
async def validate_data(data: CreateUserModel):
    return {"validated": True, "data": data.model_dump()}


@app.post("/upload")
async def upload_file(file_content: bytes):
    return {"size": len(file_content), "message": "File processed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
