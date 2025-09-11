---
title: Authentication
description: Secure your Zenith applications with JWT and custom auth
---

import { Tabs, TabItem, Code, Aside } from '@astrojs/starlight/components';

## Overview

Zenith provides a comprehensive authentication system with JWT tokens, password hashing, and flexible authorization. It includes built-in support for user registration, login, and protected routes.

## Quick Start

```python
from zenith import Zenith, Depends
from zenith.auth import Auth, create_access_token, get_current_user
from zenith.auth.password import hash_password, verify_password
from pydantic import BaseModel

app = Zenith()

# User model
class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(UserLogin):
    name: str

# Mock user store (use database in production)
users_db = {}

@app.post("/auth/register")
async def register(user: UserCreate):
    # Check if user exists
    if user.email in users_db:
        raise HTTPException(400, "Email already registered")
    
    # Create user
    users_db[user.email] = {
        "email": user.email,
        "name": user.name,
        "password_hash": hash_password(user.password)
    }
    
    # Generate token
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/login")
async def login(credentials: UserLogin):
    # Verify user
    user = users_db.get(credentials.email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    
    # Generate token
    token = create_access_token({"sub": credentials.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user['email']}!"}
```

## JWT Configuration

### Basic Setup

```python
from zenith.auth import JWTConfig
import os

jwt_config = JWTConfig(
    secret_key=os.getenv("SECRET_KEY", "your-secret-key"),
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)

app = Zenith(auth_config=jwt_config)
```

### Advanced Configuration

```python
jwt_config = JWTConfig(
    # Security
    secret_key=os.getenv("SECRET_KEY"),
    algorithm="RS256",  # RSA signature
    public_key=open("public.pem").read(),
    private_key=open("private.pem").read(),
    
    # Token settings
    access_token_expire_minutes=15,
    refresh_token_expire_days=30,
    
    # Claims
    issuer="https://api.example.com",
    audience="https://app.example.com",
    
    # Options
    verify_signature=True,
    verify_exp=True,
    verify_aud=True,
    require_exp=True
)
```

## Password Security

### Hashing Passwords

```python
from zenith.auth.password import (
    hash_password,
    verify_password,
    PasswordConfig
)

# Configure bcrypt
password_config = PasswordConfig(
    bcrypt_rounds=12,  # Higher = more secure but slower
    min_length=8,
    require_uppercase=True,
    require_lowercase=True,
    require_digits=True,
    require_special=True
)

# Hash password
hashed = hash_password("SecurePass123!", config=password_config)

# Verify password
is_valid = verify_password("SecurePass123!", hashed)
```

### Password Validation

```python
from zenith.auth.password import validate_password_strength

@app.post("/auth/register")
async def register(user: UserCreate):
    # Validate password strength
    errors = validate_password_strength(user.password)
    if errors:
        raise HTTPException(400, {"errors": errors})
    
    # Continue with registration...
```

## Token Management

### Creating Tokens

```python
from zenith.auth import create_access_token, create_refresh_token
from datetime import timedelta

# Standard access token
access_token = create_access_token(
    data={"sub": user.email, "role": user.role},
    expires_delta=timedelta(minutes=15)
)

# Refresh token
refresh_token = create_refresh_token(
    data={"sub": user.email},
    expires_delta=timedelta(days=30)
)

# Custom claims
token = create_access_token(
    data={
        "sub": user.email,
        "role": user.role,
        "permissions": user.permissions,
        "org_id": user.organization_id
    }
)
```

### Decoding Tokens

```python
from zenith.auth import decode_token

@app.get("/auth/me")
async def get_current_user_info(token: str = Header()):
    try:
        payload = decode_token(token)
        return {
            "email": payload["sub"],
            "role": payload.get("role"),
            "expires": payload["exp"]
        }
    except JWTError as e:
        raise HTTPException(401, str(e))
```

### Token Refresh

```python
@app.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    try:
        # Verify refresh token
        payload = decode_token(refresh_token, verify_exp=True)
        
        # Get user
        user = await get_user_by_email(payload["sub"])
        if not user:
            raise HTTPException(401, "User not found")
        
        # Issue new access token
        access_token = create_access_token({"sub": user.email})
        return {"access_token": access_token}
        
    except JWTError:
        raise HTTPException(401, "Invalid refresh token")
```

## Protected Routes

### Basic Protection

```python
from zenith.auth import require_auth

@app.get("/profile")
@require_auth
async def get_profile(current_user = Depends(get_current_user)):
    return current_user
```

### Role-Based Access

```python
from zenith.auth import require_role

@app.delete("/users/{user_id}")
@require_role("admin")
async def delete_user(
    user_id: int,
    current_user = Depends(get_current_user)
):
    # Only admins can delete users
    return {"deleted": user_id}

@app.get("/admin/dashboard")
@require_role(["admin", "moderator"])
async def admin_dashboard(current_user = Depends(get_current_user)):
    return {"role": current_user["role"]}
```

### Permission-Based Access

```python
from zenith.auth import require_permission

@app.post("/posts")
@require_permission("posts:write")
async def create_post(
    post: PostCreate,
    current_user = Depends(get_current_user)
):
    return {"created": post}

@app.put("/posts/{post_id}")
@require_permission("posts:edit")
async def edit_post(
    post_id: int,
    post: PostUpdate,
    current_user = Depends(get_current_user)
):
    return {"updated": post_id}
```

### Custom Authorization

```python
from zenith.auth import AuthorizationChecker

class OwnershipChecker(AuthorizationChecker):
    """Check if user owns the resource."""
    
    async def check(
        self,
        user: dict,
        resource_id: int,
        resource_type: str
    ) -> bool:
        # Check ownership in database
        resource = await get_resource(resource_type, resource_id)
        return resource and resource.owner_id == user["id"]

# Use in route
@app.put("/posts/{post_id}")
async def update_post(
    post_id: int,
    post: PostUpdate,
    current_user = Depends(get_current_user),
    checker: OwnershipChecker = Depends()
):
    # Check ownership
    if not await checker.check(current_user, post_id, "post"):
        raise HTTPException(403, "Not authorized")
    
    return {"updated": post_id}
```

## OAuth2 Integration

### Google OAuth

```python
from zenith.auth.oauth import GoogleOAuth

google_oauth = GoogleOAuth(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    redirect_uri="https://api.example.com/auth/google/callback"
)

@app.get("/auth/google")
async def google_login():
    return {"url": google_oauth.get_authorization_url()}

@app.get("/auth/google/callback")
async def google_callback(code: str):
    # Exchange code for token
    token = await google_oauth.get_access_token(code)
    
    # Get user info
    user_info = await google_oauth.get_user_info(token)
    
    # Create or update user
    user = await get_or_create_user(
        email=user_info["email"],
        name=user_info["name"],
        provider="google"
    )
    
    # Generate JWT
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token}
```

### GitHub OAuth

```python
from zenith.auth.oauth import GitHubOAuth

github_oauth = GitHubOAuth(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    redirect_uri="https://api.example.com/auth/github/callback"
)

@app.get("/auth/github")
async def github_login():
    return {"url": github_oauth.get_authorization_url(scope="user:email")}

@app.get("/auth/github/callback")
async def github_callback(code: str):
    # Similar to Google OAuth
    pass
```

## Session Management

### Cookie-Based Sessions

```python
from zenith.sessions import SessionMiddleware, SessionConfig

app.add_middleware(SessionMiddleware, {
    "secret_key": os.getenv("SESSION_SECRET"),
    "cookie_name": "session_id",
    "cookie_secure": True,  # HTTPS only
    "cookie_httponly": True,
    "cookie_samesite": "lax",
    "max_age": 86400  # 24 hours
})

@app.post("/auth/login")
async def login(credentials: UserLogin, request: Request):
    # Verify credentials...
    
    # Store in session
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    
    return {"status": "logged in"}

@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}
```

## Multi-Factor Authentication

```python
from zenith.auth.mfa import TOTP, generate_secret

@app.post("/auth/mfa/enable")
async def enable_mfa(current_user = Depends(get_current_user)):
    # Generate secret
    secret = generate_secret()
    
    # Save to user (encrypted)
    await save_user_mfa_secret(current_user["id"], secret)
    
    # Generate QR code URL
    totp = TOTP(secret)
    qr_url = totp.provisioning_uri(
        name=current_user["email"],
        issuer="MyApp"
    )
    
    return {"qr_url": qr_url, "secret": secret}

@app.post("/auth/mfa/verify")
async def verify_mfa(
    code: str,
    current_user = Depends(get_current_user)
):
    # Get user's secret
    secret = await get_user_mfa_secret(current_user["id"])
    
    # Verify code
    totp = TOTP(secret)
    if not totp.verify(code):
        raise HTTPException(400, "Invalid code")
    
    # Mark MFA as verified
    await mark_mfa_verified(current_user["id"])
    
    return {"status": "MFA enabled"}
```

## Testing Authentication

```python
from zenith.testing import TestClient, MockAuth

@pytest.mark.asyncio
async def test_protected_route():
    async with TestClient(app) as client:
        # Test without auth
        response = await client.get("/protected")
        assert response.status_code == 401
        
        # Test with mock auth
        with MockAuth(user={"email": "test@example.com", "role": "admin"}):
            response = await client.get("/protected")
            assert response.status_code == 200
            assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login():
    async with TestClient(app) as client:
        # Register user
        response = await client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "Test User"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Use token
        response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
```

<Aside type="caution">
  **Security Note**: Always use HTTPS in production, store passwords with bcrypt, and keep your secret keys secure. Never commit secrets to version control.
</Aside>

## Best Practices

1. **Use environment variables** for secrets
2. **Implement rate limiting** on auth endpoints
3. **Log authentication attempts** for security monitoring
4. **Use secure cookies** with HttpOnly and SameSite flags
5. **Implement token rotation** for long-lived sessions
6. **Add CAPTCHA** for registration and login after failures
7. **Email verification** for new accounts
8. **Password reset** with secure tokens

## Next Steps

- Implement [Database](/concepts/database) user storage
- Add [Middleware](/concepts/middleware) for auth
- Learn about [Testing](/api/testing) auth flows