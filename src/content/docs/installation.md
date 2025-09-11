---
title: Installation
description: Get Zenith installed and set up your development environment
---

import { Tabs, TabItem, Code } from '@astrojs/starlight/components';

## Requirements

Before installing Zenith, ensure you have:

- **Python 3.11 or higher** (3.12+ recommended for best performance)
- **pip** or **uv** package manager
- **PostgreSQL** or **SQLite** for database (optional)
- **Redis** for caching and background tasks (optional)

## Installation Methods

<Tabs>
  <TabItem label="pip">
    ```bash
    # Install Zenith
    pip install zenith-web
    
    # Install with all extras
    pip install "zenith-web[all]"
    
    # Install specific extras
    pip install "zenith-web[redis,postgres]"
    ```
  </TabItem>
  <TabItem label="uv (Recommended)">
    ```bash
    # Install uv if you haven't
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Install Zenith
    uv add zenith-web
    
    # Install with extras
    uv add "zenith-web[all]"
    ```
  </TabItem>
  <TabItem label="Poetry">
    ```bash
    # Add to your project
    poetry add zenith-web
    
    # With extras
    poetry add "zenith-web[redis,postgres]"
    ```
  </TabItem>
</Tabs>

## Available Extras

Zenith provides optional extras for additional functionality:

| Extra | Description | Packages Included |
|-------|-------------|-------------------|
| `redis` | Redis support for caching and queues | `redis`, `hiredis` |
| `postgres` | PostgreSQL database support | `asyncpg`, `psycopg2-binary` |
| `mysql` | MySQL database support | `aiomysql`, `pymysql` |
| `testing` | Testing utilities | `pytest`, `pytest-asyncio`, `httpx` |
| `dev` | Development tools | `black`, `ruff`, `mypy`, `pre-commit` |
| `all` | Everything included | All of the above |

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

<Tabs>
  <TabItem label="venv">
    ```bash
    # Create virtual environment
    python -m venv venv
    
    # Activate it
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    
    # Install Zenith with dev extras
    pip install "zenith-web[dev]"
    ```
  </TabItem>
  <TabItem label="uv">
    ```bash
    # uv manages virtual environments automatically
    uv init my-project
    cd my-project
    
    # Add Zenith with dev extras
    uv add "zenith-web[dev]"
    
    # Run commands
    uv run zen --version
    ```
  </TabItem>
</Tabs>

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