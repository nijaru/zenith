# Security Best Practices for Zenith

## Model Serialization Security

### ⚠️ CRITICAL: Use Explicit Response Models, Not `.model_dump()`

The `.model_dump()` method exposes **ALL** model fields, including sensitive data:

```python
# ❌ DANGEROUS - Exposes password hashes, tokens, internal IDs
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await User.find_or_404(user_id)
    return user.model_dump()  # Exposes: password_hash, reset_token, etc.
```

**Why This Is Dangerous:**
- Exposes password hashes (can be cracked offline)
- Leaks internal IDs (database primary keys)
- Reveals security tokens (password reset, email verification)
- Shows system metadata (created_at, updated_at, deleted_at)

### ✅ SAFE: Use Pydantic Response Models

Always define explicit response models:

```python
from pydantic import BaseModel

class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    # Explicitly choose what to expose

@app.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: int):
    user = await User.find_or_404(user_id)
    return user  # FastAPI/Starlette serializes based on response_model
```

### ✅ SAFE: Use `model_dump(exclude=...)`

If you must serialize directly, explicitly exclude sensitive fields:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await User.find_or_404(user_id)
    return user.model_dump(exclude={'password_hash', 'reset_token', 'api_key'})
```

### ✅ BEST: Use Pydantic `.model_validate()`

Convert database models to response models:

```python
@app.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: int):
    user = await User.find_or_404(user_id)
    return UserPublic.model_validate(user)
```

---

## SECRET_KEY Security

### ⚠️ Development vs Production

**Development (auto-generated):**
```python
# Zenith auto-generates keys for dev:
# "dev-key-not-for-production-use-only"
app = Zenith()  # Works in dev, FAILS in production
```

**Production (REQUIRED):**
```bash
# Generate secure key:
zen keygen --output .env

# Or manually:
export SECRET_KEY="your-64-char-secure-random-key"
```

**Key Requirements:**
- ✅ Minimum 32 characters (64+ recommended)
- ✅ Cryptographically random (use `secrets` module or `zen keygen`)
- ✅ Different for each environment (dev/staging/prod)
- ❌ Never commit to git
- ❌ Never share across services

---

## Database Security

### Connection Strings

**❌ BAD:**
```python
# Hardcoded credentials
DATABASE_URL = "postgresql://admin:password123@localhost/db"
```

**✅ GOOD:**
```python
# Use environment variables
import os
DATABASE_URL = os.getenv("DATABASE_URL")
```

### SQL Injection Prevention

Zenith uses SQLAlchemy's parameterized queries, which prevent SQL injection:

```python
# ✅ SAFE - Parameters are automatically escaped
users = await User.where(email=user_input).all()

# ✅ SAFE - SQLAlchemy handles escaping
query = select(User).where(User.email == user_input)
```

**❌ NEVER** use raw SQL with string interpolation:
```python
# ❌ DANGEROUS - SQL injection vulnerability
await session.execute(f"SELECT * FROM users WHERE email = '{user_input}'")
```

---

## Authentication Security

### JWT Tokens

**Best Practices:**
- Use short expiration times (15 minutes for access tokens)
- Implement refresh tokens for longer sessions
- Store tokens securely (httpOnly cookies for web, secure storage for mobile)
- Validate tokens on every request

```python
from zenith.auth import create_access_token

# ✅ GOOD - Short-lived token
token = create_access_token(
    data={"sub": user.id},
    expires_delta=timedelta(minutes=15)
)
```

### Password Hashing

Zenith uses bcrypt by default:

```python
from zenith.auth import hash_password, verify_password

# ✅ GOOD - Bcrypt with automatic salt
hashed = hash_password("user-password")
is_valid = verify_password("user-password", hashed)
```

**Don't:**
- ❌ Use MD5 or SHA1 (easily cracked)
- ❌ Implement your own hashing (use bcrypt/argon2)
- ❌ Store passwords in plain text

---

## CORS Security

### Development
```python
# Permissive for local development
app = Zenith()  # Allows localhost:3000 by default
```

### Production
```python
# Restrict to your domain(s)
from zenith.middleware import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**Never use `allow_origins=["*"]` with `allow_credentials=True` in production.**

---

## Rate Limiting

Protect against brute force and DDoS:

```python
from zenith.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    requests=100,
    window=60,  # 100 requests per minute
)
```

**Apply stricter limits to auth endpoints:**
```python
@app.post("/auth/login")
@rate_limit(requests=5, window=300)  # 5 attempts per 5 minutes
async def login(credentials: LoginCredentials):
    ...
```

---

## File Upload Security

### Validate Everything

```python
from zenith import File, UploadedFile

@app.post("/upload")
async def upload(
    file: UploadedFile = File(
        max_size="5MB",  # Limit size
        allowed_extensions=[".jpg", ".png"],  # Whitelist extensions
        allowed_types=["image/jpeg", "image/png"],  # Verify MIME types
    )
):
    # ✅ Zenith validates automatically
    # ✅ Rejects dangerous files (.exe, .sh, etc.)
    await file.save(f"/uploads/{uuid.uuid4()}{file.extension}")
```

**Don't trust filenames:**
```python
# ❌ BAD - Path traversal vulnerability
save_path = f"/uploads/{file.filename}"  # User could use "../../../etc/passwd"

# ✅ GOOD - Generate safe filenames
import uuid
safe_name = f"{uuid.uuid4()}{file.extension}"
save_path = f"/uploads/{safe_name}"
```

---

## Environment Variables

### Use `.env` Files (Development Only)

```bash
# .env (NOT committed to git)
DATABASE_URL=postgresql://localhost/mydb
SECRET_KEY=dev-key-only
```

```python
# Load with python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

### Production: Use Secrets Management

- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets
- Railway/Heroku config vars

**Never:**
- ❌ Commit `.env` files to git
- ❌ Hardcode credentials in code
- ❌ Share production credentials in Slack/email

---

## Checklist for Production

- [ ] `SECRET_KEY` set to cryptographically random value (64+ chars)
- [ ] `DATABASE_URL` uses environment variable
- [ ] All API responses use explicit Pydantic models (not `.model_dump()`)
- [ ] CORS restricted to your domain(s)
- [ ] Rate limiting enabled on auth endpoints
- [ ] File uploads validate size, type, and extension
- [ ] HTTPS enabled (via reverse proxy or CDN)
- [ ] Security headers enabled (Zenith adds automatically in production)
- [ ] Passwords hashed with bcrypt/argon2
- [ ] JWT tokens have short expiration times
- [ ] Database connections use connection pooling
- [ ] Error messages don't reveal sensitive info

---

## Reporting Security Issues

**Do not** create public GitHub issues for security vulnerabilities.

Email security concerns to: nijaru7@gmail.com

We'll respond within 48 hours and credit you in release notes (unless you prefer to remain anonymous).

---

*Last updated: 2025-10-08*
