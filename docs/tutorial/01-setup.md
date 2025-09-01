# Step 1: Project Setup

> Set up your Zenith project with proper structure and dependencies

## Create Project Structure

First, let's create a well-organized project structure:

```bash
mkdir blog-api
cd blog-api

# Create directory structure
mkdir -p {src/blog_api,tests,uploads,docs}
touch src/blog_api/__init__.py
```

Your project should look like this:

```
blog-api/
├── src/
│   └── blog_api/
│       └── __init__.py
├── tests/
├── uploads/
├── docs/
├── pyproject.toml     # We'll create this
├── README.md         # We'll create this  
└── .env              # We'll create this
```

## Dependencies

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "blog-api"
version = "0.1.0"
description = "Blog API built with Zenith"
authors = [{name = "Your Name", email = "you@example.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"

dependencies = [
    "zenith-web>=0.1.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "asyncpg>=0.28.0",     # PostgreSQL driver
    "python-multipart>=0.0.6",  # File uploads
    "pillow>=10.0.0",      # Image processing
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",         # Linting & formatting
    "pyright>=1.1.0",     # Type checking
    "httpx>=0.24.0",       # Testing HTTP client
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "S", "B", "C4"]
ignore = ["E501", "S101", "S608"]

[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "strict"
```

## Environment Configuration

Create `.env` for development settings:

```bash
# Development environment settings
SECRET_KEY=your-super-secret-key-that-is-at-least-32-characters-long
DATABASE_URL=postgresql+asyncpg://user:password@localhost/blog_api_dev
DEBUG=true

# File upload settings  
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB

# JWT settings
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

> **Important**: Never commit `.env` to version control. Add it to `.gitignore`.

## Install Dependencies

```bash
# Install the package in development mode
pip install -e ".[dev]"

# Or if using pip-tools
pip install pip-tools
pip-compile pyproject.toml
pip install -r requirements.txt
```

## Basic Application Structure

Create `src/blog_api/main.py`:

```python
"""
Blog API - Main application entry point.
"""
import os
from pathlib import Path

from zenith import Zenith
from zenith.auth import configure_auth

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Create Zenith app
app = Zenith(debug=os.getenv("DEBUG", "false").lower() == "true")

# Configure authentication
configure_auth(
    app,
    secret_key=os.getenv("SECRET_KEY"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
)

# Configure database
database_url = os.getenv("DATABASE_URL")
if database_url:
    app.setup_database(database_url)

# Add middleware
app.add_cors(allow_origins=["*"])  # Configure properly for production
app.add_security_headers()
app.add_exception_handling(debug=app.config.debug)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "blog-api", 
        "version": "0.1.0"
    }

# We'll add more routes in the next steps
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Blog API!",
        "docs": "/docs",  # Will add OpenAPI docs later
        "health": "/health"
    }

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=app.config.debug
    )
```

Create `src/blog_api/__init__.py`:

```python
"""Blog API - A modern blog API built with Zenith."""

__version__ = "0.1.0"
```

## Test Your Setup

Let's verify everything works:

```bash
# Run the app
cd src
python -m blog_api.main

# Or with uvicorn
uvicorn blog_api.main:app --reload
```

Visit http://localhost:8000 - you should see:

```json
{
  "message": "Welcome to the Blog API!",
  "docs": "/docs",
  "health": "/health"
}
```

Test the health endpoint at http://localhost:8000/health:

```json
{
  "status": "healthy",
  "service": "blog-api",
  "version": "0.1.0"
}
```

## Basic Testing Setup

Create `tests/test_setup.py` to verify everything works:

```python
"""Test basic application setup."""
import pytest
from httpx import AsyncClient

from blog_api.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns welcome message."""
    from zenith.testing import TestClient
    
    async with TestClient(app) as client:
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Welcome to the Blog API!"
        assert "docs" in data
        assert "health" in data


@pytest.mark.asyncio 
async def test_health_endpoint():
    """Test health check endpoint."""
    from zenith.testing import TestClient
    
    async with TestClient(app) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "blog-api"
        assert data["version"] == "0.1.0"
```

Run the tests:

```bash
pytest tests/test_setup.py -v
```

You should see:

```
tests/test_setup.py::test_root_endpoint PASSED
tests/test_setup.py::test_health_endpoint PASSED
```

## Project Documentation

Create `README.md`:

```markdown
# Blog API

A modern blog API built with [Zenith](https://github.com/zenith-framework/zenith).

## Features

- User authentication with JWT
- CRUD operations for blog posts
- File upload for post images
- PostgreSQL database integration  
- Comprehensive test coverage
- Production-ready deployment

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start the server
python -m blog_api.main
```

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /posts` - List posts
- `POST /posts` - Create post

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=blog_api

# Format code
ruff format .

# Type checking
pyright
```
```

## Git Setup

Initialize git and create `.gitignore`:

```bash
git init

cat > .gitignore << 'EOF'
# Environment
.env
.env.local

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
build/
dist/

# Database
*.db
*.sqlite3

# Uploads
uploads/
*.jpg
*.png
*.gif

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
EOF

git add .
git commit -m "Initial project setup"
```

## What We've Built

✅ **Project Structure** - Clean, scalable directory layout
✅ **Dependencies** - Modern Python tooling with Zenith
✅ **Configuration** - Environment-based config with `.env`  
✅ **Basic App** - Working Zenith application with health checks
✅ **Testing** - Test setup with async support
✅ **Documentation** - README and project docs

## Next Steps

Your project foundation is ready! In the next step, we'll:

- Set up the database with SQLAlchemy models
- Create User and Post tables with relationships
- Add database migrations with Alembic

---

**Continue to:** [Step 2: Database Models →](02-database.md)