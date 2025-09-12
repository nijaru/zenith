---
title: Installation
description: Get Zenith installed and set up your development environment
---

## Requirements

Before installing Zenith, ensure you have:

- **Python 3.12 or higher** (required for Zenith framework)
- **pip** or **uv** package manager
- **PostgreSQL** or **SQLite** for database (optional)
- **Redis** for caching and background tasks (optional)

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

## What's Included

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

# Security
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

## Troubleshooting

### Import Errors

If you get import errors, ensure:
- Python 3.11+ is being used
- Virtual environment is activated
- Zenith is installed in the current environment

### Command Not Found

If `zen` command is not found:
- Check if it's in your PATH
- Try `python -m zenith.cli` instead
- Reinstall with `pip install --force-reinstall zenith-web`

## Next Steps

Now that Zenith is installed, you're ready to:

- [Create your first application](/quick-start)
- [Understand the project structure](/project-structure)
- [Learn about the Context system](/concepts/contexts)