"""
Authentication utilities for JWT token handling.
"""

from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from app.config import settings
from app.database import get_session
from app.models import User
from app.exceptions import AuthenticationError

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode in the token

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise AuthenticationError("Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session=Depends(get_session),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: Bearer token from request
        session: Database session

    Returns:
        Current user object

    Raises:
        AuthenticationError: If authentication fails
    """
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    email = payload.get("sub")

    if not email:
        raise AuthenticationError("Invalid token payload")

    # Get user from database
    stmt = select(User).where(User.email == email)
    user = await session.exec(stmt).first()

    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session=Depends(get_session),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that have different behavior for
    authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, session)
    except AuthenticationError:
        return None
