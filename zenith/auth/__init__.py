"""
Authentication system for Zenith applications.

Provides JWT token generation/validation, password hashing,
and authentication middleware for secure API access.
"""

from .jwt import JWTManager, create_access_token, verify_access_token, configure_jwt
from .password import PasswordManager, hash_password, verify_password
from .dependencies import get_current_user, require_auth, require_roles
from .config import configure_auth, auth_required, optional_auth

__all__ = [
    # Easy setup
    "configure_auth",
    
    # JWT utilities
    "JWTManager",
    "create_access_token", 
    "verify_access_token",
    "configure_jwt",
    
    # Password utilities
    "PasswordManager", 
    "hash_password",
    "verify_password",
    
    # Dependency injection
    "get_current_user",
    "require_auth",
    "require_roles",
    
    # Decorators
    "auth_required",
    "optional_auth",
]