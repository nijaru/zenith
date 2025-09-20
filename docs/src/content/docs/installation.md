---
title: Installation
description: Get Zenith installed and set up your development environment
---

## Installation Overview

Typical Python web frameworks require multiple separate installations:
- Installing the core framework
- Adding database drivers separately
- Installing Redis clients
- Adding authentication libraries
- Finding compatible middleware packages
- Configuring each component manually

## Batteries Included Approach

Zenith includes **everything** you need in one install:
```bash
pip install zenith-web  # That's it!
```

All database drivers, Redis support, authentication, and middleware are included and pre-configured.

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
| **uv** | Modern development | 10x faster, better dependency resolution |
| **Poetry** | Team projects | Lock files, reproducible builds |
| **Docker** | Microservices | Consistent environments |

## Installation Methods

**pip:**
```bash
# Install Zenith
pip install zenith-web

# All dependencies are included by default
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

### From FastAPI
```bash
# FastAPI requires multiple installs
pip install fastapi uvicorn[standard] sqlalchemy redis pyjwt

# Zenith includes everything
pip install zenith-web  # Done!
```

### From Flask
```bash
# Flask requires many extensions
pip install flask flask-sqlalchemy flask-cors flask-jwt-extended

# Zenith is batteries-included
pip install zenith-web  # Everything included!
```

### From Django
```bash
# Django + async support + API tools
pip install django djangorestframework django-cors-headers channels

# Zenith is async-first with API focus
pip install zenith-web  # Simpler, faster, async
```

## Best Practices

###  DO
- Use virtual environments (venv, uv, poetry)
- Pin versions in production (`zenith-web==0.3.1`)
- Use `.env` files for configuration
- Keep `requirements.txt` updated
- Use `uv` for faster installs

### ❌ DON'T
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