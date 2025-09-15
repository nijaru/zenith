"""
Authentication system for Zenith applications.

Provides JWT token generation/validation, password hashing,
and authentication middleware for secure API access.
"""

from .config import auth_required, configure_auth, optional_auth
from .dependencies import get_current_user, require_auth, require_roles
from .jwt import (
    JWTManager,
    configure_jwt,
    create_access_token,
    extract_user_from_token,
    verify_access_token,
)
from .password import PasswordManager, hash_password, verify_password

__all__ = [
    # JWT utilities
    "JWTManager",
    # Password utilities
    "PasswordManager",
    # Decorators
    "auth_required",
    # Easy setup
    "configure_auth",
    "configure_jwt",
    "create_access_token",
    # Dependency injection
    "extract_user_from_token",
    "get_current_user",
    "hash_password",
    "optional_auth",
    "require_auth",
    "require_roles",
    "verify_access_token",
    "verify_password",
]
