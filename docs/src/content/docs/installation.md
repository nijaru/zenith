---
title: Installation
description: Get Zenith installed and set up your development environment
---

## Installation Overview

### The Problem (Traditional Python Web Development)
```bash
# What you usually have to install manually
pip install web-framework        # Core framework
pip install uvicorn              # ASGI server
pip install sqlalchemy           # Database ORM
pip install psycopg2-binary      # PostgreSQL driver
pip install redis                # Redis client
pip install python-jose          # JWT handling
pip install passlib              # Password hashing
pip install python-multipart     # File uploads
pip install bcrypt               # Password encryption
pip install alembic              # Database migrations
pip install pytest               # Testing
pip install pytest-asyncio       # Async testing
pip install aioredis             # Async Redis
# ... and 20+ more packages

# Then spend hours configuring each one:
# - Database connection strings
# - Authentication settings
# - Middleware order
# - Testing setup
# - CORS configuration
# - Security headers
# And pray they all work together! 😫
```

### The Solution (Zenith "Batteries Included" Approach)
```bash
# With Zenith - everything in one install
pip install zenith-web  # That's literally it!

# Zenith includes these dependencies:
# ✓ SQLAlchemy 2.0+ with async support
# ✓ SQLModel for type-safe models
# ✓ PostgreSQL driver (asyncpg)
# ✓ SQLite driver (aiosqlite)
# ✓ Redis client for caching
# ✓ JWT libraries (PyJWT)
# ✓ Password hashing (bcrypt + passlib)
# ✓ WebSocket support
# ✓ Alembic for migrations
# ✓ Performance monitoring (prometheus-client)
# ✓ JSON serialization (orjson, msgspec)
# ✓ File upload support (python-multipart)
# ✓ Async server (uvicorn)

# What Zenith provides on top:
# ✓ Automatic configuration
# ✓ Request-scoped database sessions
# ✓ ActiveRecord-style query methods
# ✓ Built-in authentication helpers
# ✓ Admin dashboard foundation
# ✓ Testing utilities
# ✓ CLI tools
```

**Installation Benefits:**
- **Batteries included**: Core dependencies pre-selected and tested together
- **Version compatibility**: All packages guaranteed to work together
- **Sensible defaults**: Production-ready configuration out of the box
- **Time saved**: Start building immediately instead of configuring

## Requirements

Before installing Zenith, ensure you have:

- **Python 3.12 or higher** (required for Zenith framework)
- **pip** or **uv** package manager
- **PostgreSQL** or **SQLite** for database (optional)
- **Redis** for caching and background tasks (optional)

## When to Use Each Installation Method

| Method | Best For | Why Choose This |
|--------|----------|----------------|
| **pip** | Quick start, tutorials | Universal, works everywhere |
| **uv** | Modern development | 10-100x faster installs, better dependency resolution |
| **Poetry** | Team projects | Lock files, reproducible builds |
| **Docker** | Microservices | Consistent environments |

## Installation Methods

### Method 1: pip (Most Common)
```bash
# Install Zenith with all dependencies
pip install zenith-web

# Verify installation
zen --version
# Should output: Zenith 0.3.1 (or latest version)

# Create your first project
zen new my-api
# This creates:
# - app.py (main application with examples)
# - .env (environment variables with secure secret key)
# - requirements.txt (pinned dependencies)
# - .gitignore (sensible defaults)
# - README.md (quick start guide)

# Start development server
cd my-api
zen dev
# Automatically:
# - Detects your app file
# - Enables hot reload
# - Shows pretty error pages
# - Opens browser (optional: --open flag)
```
# Redis, PostgreSQL, and other drivers are already included
```

**uv (Recommended):**
```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Zenith
uv add zenith-web

# All dependencies are included by default
```

**Poetry:**
```bash
# Add to your project
poetry add zenith-web

# All dependencies are included by default
```

## What's Included (No Extra Installs Needed!)

Zenith includes all essential dependencies out of the box:

| Component | Description | Packages Included |
|-----------|-------------|-------------------|
| **Web Framework** | ASGI server and routing | `uvicorn`, `starlette`, `websockets` |
| **Database** | Async database support | `sqlalchemy`, `alembic`, `sqlmodel`, `asyncpg`, `aiosqlite` |
| **Caching** | Redis support | `redis` |
| **Validation** | Request/response validation | `pydantic` |
| **Authentication** | JWT and password handling | `pyjwt`, `bcrypt`, `passlib` |
| **Performance** | High-performance serialization | `orjson`, `msgspec`, `uvloop` |
| **Monitoring** | Metrics and health checks | `prometheus-client`, `structlog`, `psutil` |
| **Templates** | Jinja2 templating | `jinja2` |
| **File Uploads** | Multipart form support | `python-multipart` |

Optional extras for development:

| Extra | Description | Install Command |
|-------|-------------|----------------|
| `dev` | Testing and development tools | `pip install "zenith-web[dev]"` |
| `benchmark` | Performance benchmarking tools | `pip install "zenith-web[benchmark]"` |
| `performance` | Additional performance optimizations | `pip install "zenith-web[performance]"` |
| `http3` | HTTP/3 and QUIC support | `pip install "zenith-web[http3]"` |
| `compression` | Advanced compression algorithms | `pip install "zenith-web[compression]"`

## Verify Installation

After installation, verify everything is working:

```bash
# Check Zenith CLI is available
zen --version

# Check Python import works
python -c "import zenith; print(zenith.__version__)"
```

## Development Setup

For development, we recommend setting up a virtual environment:

**venv:**
```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Zenith (production dependencies included)
pip install zenith-web

# Add development tools
pip install "zenith-web[dev]"
```

**uv:**
```bash
# uv manages virtual environments automatically
uv init my-project
cd my-project

# Add Zenith (production dependencies included)
uv add zenith-web

# Add development tools if needed
uv add "zenith-web[dev]"

# Run commands
uv run zen --version
```

## IDE Setup

### VS Code

Install recommended extensions for the best experience:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml"
  ]
}
```

### PyCharm

1. Set Python interpreter to your virtual environment
2. Enable type checking in settings
3. Configure Black as the code formatter

## Environment Variables

Create a `.env` file in your project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/zenith_dev

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Security (generate with: zen keygen --output .env)
SECRET_KEY=your-secret-key-here

# Environment
DEBUG=true
ENVIRONMENT=development
```

## Docker Setup (Optional)

For containerized development:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: zenith
      POSTGRES_PASSWORD: zenith
      POSTGRES_DB: zenith_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Start services:

```bash
docker-compose up -d
```

## Common Patterns

### Production Setup

```bash
# Install with production optimizations
pip install "zenith-web[performance]"

# Set production environment variables
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...
export SECRET_KEY=$(zen keygen)
export DEBUG=false

# Run with production server
zen serve --workers 4
```

### Development with Database

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Run migrations
zen db upgrade

# Start dev server with hot reload
zen dev --reload
```

### Testing Environment

```bash
# Install test dependencies
pip install "zenith-web[dev]"

# Run tests with coverage
zen test --coverage

# Run specific test file
zen test tests/test_api.py
```

## Performance Impact

| Installation Type | Startup Time | Memory Usage | Request/sec |
|------------------|-------------|--------------|-------------|
| Basic | <100ms | 45MB | 9,600 |
| With [performance] | <80ms | 42MB | 11,200 |
| With [dev] | <150ms | 65MB | 9,600 |
| Docker | <200ms | 50MB | 9,400 |

## Troubleshooting

### Import Errors

If you get import errors, ensure:
- Python 3.12+ is being used
- Virtual environment is activated
- Zenith is installed in the current environment

### Command Not Found

If `zen` command is not found:
- Check if it's in your PATH
- Try `python -m zenith.cli` instead
- Reinstall with `pip install --force-reinstall zenith-web`

## Verification Checklist

After installation, verify everything works:

```bash
#  CLI installed
zen --version
# Expected: zenith-cli 0.3.1 or higher

#  Python import works
python -c "import zenith; print(f'Zenith {zenith.__version__} ready!')"
# Expected: Zenith 0.3.1 ready!

#  Create test project
zen new test-project
cd test-project

#  Run development server
zen dev
# Expected: Server running on http://localhost:8000

#  Check API docs
curl http://localhost:8000/docs
# Expected: HTML response with Swagger UI
```

If all checks pass, you're ready to build!

## Migration from Other Frameworks

### Migrating from Other Frameworks

If you're coming from another Python web framework:

```bash
# Traditional approach - install core + many extensions
pip install framework-core
pip install framework-orm
pip install framework-auth
pip install framework-cors
pip install framework-validation
pip install redis
pip install celery
# ... many more packages

# With Zenith - everything included
pip install zenith-web  # All batteries included!
```

**What's different:**
- **Single package**: No need to hunt for compatible extensions
- **Pre-configured**: Sensible defaults that work immediately
- **Async-first**: Built for modern async Python from the ground up
- **Type-safe**: Full type hints and validation throughout

## Best Practices

###  DO
- Use virtual environments (venv, uv, poetry)
- Pin versions in production (`zenith-web==0.3.1`)
- Use `.env` files for configuration
- Keep `requirements.txt` updated
- Use `uv` for faster installs

### DON'T
- Don't install in system Python
- Don't mix pip and poetry in same project
- Don't forget to activate virtual environment
- Don't commit `.env` files to git
- Don't use outdated Python versions

## Next Steps

Now that Zenith is installed, you're ready to:

- [Create your first application](/quick-start)
- [Understand the project structure](/project-structure)
- [Learn about the Service system](/concepts/contexts)