---
title: Installation
description: Get Zenith installed and set up your development environment
---

## Installation

Zenith is a batteries-included Python web framework that comes with everything you need to build production APIs.

### Quick Install

```bash
pip install zenithweb

# Verify installation
zen --version
```

## What's Included

Zenith bundles commonly needed dependencies so you can start building immediately:

**Database & ORM**
- SQLAlchemy 2.0+ with async support
- SQLModel for type-safe models
- PostgreSQL driver (asyncpg)
- SQLite driver (aiosqlite)
- Alembic for migrations

**Authentication & Security**
- JWT libraries (PyJWT)
- Password hashing (bcrypt + passlib)
- Security headers middleware

**Performance & Caching**
- Redis client for caching
- JSON serialization (orjson, msgspec)
- Performance monitoring (prometheus-client)
- Async server (uvicorn)

**Development Tools**
- WebSocket support
- File upload support (python-multipart)
- Testing utilities
- CLI tools

## Requirements

- **Python 3.12 or higher**
- **pip** or **uv** package manager
- **PostgreSQL** or **SQLite** for database (optional)
- **Redis** for caching and background tasks (optional)

## Installation Methods

### Using pip

The standard Python package manager:

```bash
# Install Zenith
pip install zenithweb

# Create your first project
zen new my-api
cd my-api

# Start development server
zen dev
```

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast, modern Python package manager:

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Zenith
uv add zenithweb

# Run with uv
uv run zen dev
```

### Using Poetry

For projects that use Poetry for dependency management:

```bash
# Add to your project
poetry add zenithweb

# Run commands
poetry run zen dev
```

### Installation Options

| Method | Best For | Key Benefit |
|--------|----------|-------------|
| **pip** | Quick start, tutorials | Universal, works everywhere |
| **uv** | Modern development | 10-100x faster installs |
| **Poetry** | Team projects | Lock files, reproducible builds |
| **Docker** | Microservices | Consistent environments |

## Optional Extras

Install additional features as needed:

```bash
# Development tools (testing, linting)
pip install "zenithweb[dev]"

# Performance benchmarking
pip install "zenithweb[benchmark]"

# Additional performance optimizations
pip install "zenithweb[performance]"

# HTTP/3 support
pip install "zenithweb[http3]"

# Advanced compression
pip install "zenithweb[compression]"
```

## Environment Setup

### Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Zenith
pip install zenithweb
```

### Environment Variables

Create a `.env` file for your configuration:

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

## Docker Setup

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

## Verify Installation

After installation, verify everything works:

```bash
# Check CLI
zen --version

# Check Python import
python -c "import zenith; print(zenith.__version__)"

# Create test project
zen new test-project
cd test-project

# Run development server
zen dev

# Visit http://localhost:8000
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

## Production Setup

```bash
# Install with production optimizations
pip install "zenithweb[performance]"

# Set production environment variables
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...
export SECRET_KEY=$(zen keygen)
export DEBUG=false

# Run with production server
zen serve --workers 4
```

## Troubleshooting

### Import Errors
- Ensure Python 3.12+ is being used
- Check virtual environment is activated
- Reinstall: `pip install --force-reinstall zenithweb`

### Command Not Found
- Check if `zen` is in your PATH
- Try `python -m zenith.cli` instead
- Ensure virtual environment is activated

### Port Already in Use
- Stop other processes: `lsof -i :8000`
- Use different port: `zen dev --port 8001`

## Next Steps

- [Quick Start Guide](/quick-start) - Build your first API
- [Project Structure](/project-structure) - Understand the layout
- [Tutorial](/tutorial/01-getting-started) - Step-by-step learning