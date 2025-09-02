"""FastAPI benchmark application."""

from datetime import datetime

import jwt
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


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


# Database
engine = create_async_engine("sqlite+aiosqlite:///:memory:")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Auth
security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, "benchmark-secret-key-123", algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


# App
app = FastAPI()


@app.on_event("startup")
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


@app.get("/users/{user_id}", response_model=UserModel)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserModel(
        id=user.id, name=user.name, email=user.email, created_at=user.created_at
    )


@app.get("/users", response_model=list[UserModel])
async def list_users(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).limit(limit))
    users = result.scalars().all()
    return [
        UserModel(
            id=user.id, name=user.name, email=user.email, created_at=user.created_at
        )
        for user in users
    ]


@app.post("/users", response_model=UserModel)
async def create_user(data: CreateUserModel, db: AsyncSession = Depends(get_db)):
    user = User(name=data.name, email=data.email, created_at=datetime.now())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserModel(
        id=user.id, name=user.name, email=user.email, created_at=user.created_at
    )


@app.get("/protected")
async def protected_route(current_user=Depends(verify_token)):
    return {"user": current_user}


@app.post("/validate")
async def validate_data(data: CreateUserModel):
    return {"validated": True, "data": data.model_dump()}


@app.post("/upload")
async def upload_file(file: UploadFile):
    content = await file.read()
    return {"size": len(content), "message": "File processed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
