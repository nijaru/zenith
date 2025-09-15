---
title: CLI Tools
description: Zenith command-line tools for development productivity
---

# CLI Tools

Zenith provides a comprehensive CLI for development productivity, inspired by Rails, Django, and Phoenix.

## Installation

The `zen` command is available after installing Zenith:

```bash
pip install zenith-web
zen --help
```

## Development Server

### `zen dev` - Hot Reload Development Server

**The best way to develop** - automatic reloading when files change:

```bash
zen dev                    # Start with hot reload
zen dev --port 3000        # Custom port
zen dev --host 0.0.0.0     # Bind to all interfaces
zen dev --open             # Open browser automatically
```

**Features:**
- ✅ **Hot reload** - Automatic restarts on file changes
- ✅ **Fast startup** - Optimized development mode
- ✅ **Error display** - Clear error messages in terminal
- ✅ **Auto-discovery** - Finds your app automatically

### `zen serve` - Production Server

For production or when you don't need hot reload:

```bash
zen serve                  # Production mode
zen serve --reload         # Development mode (same as zen dev)
zen serve --workers 4      # Multiple workers
```

## Project Creation

### `zen new` - Create New Application

Scaffold a new Zenith application with best practices:

```bash
zen new myapi              # Create new project
zen new myapi --template api   # API-only template
zen new myapi --template fullstack  # Full-stack template
```

**Generated structure:**
```
myapi/
├── app/
│   ├── __init__.py
│   ├── main.py           # Application setup
│   ├── models/           # Pydantic models
│   ├── services/         # Business logic
│   └── routes/           # Route handlers
├── tests/                # Test suite
├── requirements.txt      # Dependencies
├── .env.example          # Environment variables
└── README.md             # Documentation
```

## Code Generation

### `zen g` - Generate Code

Generate boilerplate code following best practices:

```bash
zen g service User         # Generate UserService
zen g model User           # Generate User model
zen g routes users         # Generate user routes
zen g test UserService     # Generate service tests
```

**Service generation:**
```bash
zen g service User
```
Creates `app/services/user_service.py`:
```python
from zenith import Service, Inject

class UserService(Service):
    """Business logic for user operations."""

    async def create_user(self, user_data: dict) -> dict:
        # TODO: Implement user creation
        pass

    async def get_user(self, user_id: int) -> dict | None:
        # TODO: Implement user retrieval
        pass
```

## Database Management

### `zen db` - Database Operations

Manage database migrations and schema:

```bash
zen db init                # Initialize migrations
zen db migrate "add users" # Create new migration
zen db upgrade             # Apply pending migrations
zen db downgrade           # Rollback last migration
zen db current             # Show current revision
zen db history             # Show migration history
zen db stamp head          # Mark as up to date
```

**Example migration workflow:**
```bash
# Initial setup
zen db init

# Create migration for users table
zen db migrate "add users table"

# Apply the migration
zen db upgrade

# Check status
zen db current
```

## Debugging & Inspection

### `zen routes` - Show All Routes

View all registered routes in your application:

```bash
zen routes                 # Show all routes
zen routes --format table  # Table format
zen routes --format json   # JSON output
```

**Output:**
```
Method  Path              Handler              Name
GET     /                 main.hello_world     hello_world
POST    /users            users.create_user    create_user
GET     /users/{id}       users.get_user       get_user
PUT     /users/{id}       users.update_user    update_user
DELETE  /users/{id}       users.delete_user    delete_user
```

### `zen info` - Application Information

Show application configuration and environment:

```bash
zen info                   # Basic info
zen info --detailed        # Detailed configuration
zen info --env             # Environment variables
```

### `zen shell` - Interactive Shell

Start Python shell with application context loaded:

```bash
zen shell                  # Start interactive shell
```

**In the shell:**
```python
>>> app  # Your Zenith application
>>> from app.services import UserService
>>> users = UserService()
>>> # Test your code interactively
```

## Testing

### `zen test` - Run Tests

Run your application tests:

```bash
zen test                   # Run all tests
zen test tests/test_user.py  # Run specific file
zen test -v                # Verbose output
zen test --coverage        # With coverage report
zen test --parallel        # Parallel execution
```

## Utilities

### `zen version` - Version Information

```bash
zen version                # Show Zenith version
zen --version              # Same as above
```

### Shortcuts

Common commands have short aliases:

```bash
zen d                      # Same as zen dev
zen s                      # Same as zen serve
zen g                      # Same as zen generate
```

## Configuration

### Project Configuration

Zenith looks for configuration in these files:
- `zenith.toml` - Project configuration
- `.env` - Environment variables
- `pyproject.toml` - Python project settings

**Example `zenith.toml`:**
```toml
[zenith]
app = "app.main:app"       # Application location
debug = true               # Development mode
port = 8000               # Default port

[zenith.database]
url = "postgresql://..."   # Database URL
auto_migrate = true       # Auto-apply migrations

[zenith.testing]
parallel = true           # Run tests in parallel
coverage = true           # Generate coverage
```

## Development Workflow

### Recommended Development Flow

1. **Create project:**
   ```bash
   zen new myapi
   cd myapi
   ```

2. **Start development server:**
   ```bash
   zen dev
   ```

3. **Generate code as needed:**
   ```bash
   zen g service User
   zen g model User
   zen g routes users
   ```

4. **Set up database:**
   ```bash
   zen db init
   zen db migrate "initial schema"
   zen db upgrade
   ```

5. **Check routes:**
   ```bash
   zen routes
   ```

6. **Run tests:**
   ```bash
   zen test
   ```

### Hot Reload Tips

**What triggers hot reload:**
- ✅ Python file changes (`.py`)
- ✅ Configuration changes (`zenith.toml`, `.env`)
- ✅ Template changes (if using templates)

**What doesn't trigger reload:**
- ❌ Static file changes (use separate static server)
- ❌ Database schema changes (run migrations manually)

**Best practices:**
- Use `zen dev` for all development
- Keep terminal visible to see errors
- Save files to trigger reload
- Check logs for startup errors

## Productivity Tips

### 1. Use Aliases

Add to your shell profile:
```bash
alias zd="zen dev"
alias zr="zen routes"
alias zt="zen test"
alias zs="zen shell"
```

### 2. Auto-completion

Enable shell completion:
```bash
# For bash
eval "$(zen --completion bash)"

# For zsh
eval "$(zen --completion zsh)"

# For fish
zen --completion fish | source
```

### 3. Environment Management

Use `.env` files for configuration:
```bash
# .env.development
DEBUG=true
DATABASE_URL=sqlite:///dev.db
SECRET_KEY=dev-secret

# .env.production
DEBUG=false
DATABASE_URL=postgresql://...
SECRET_KEY=prod-secret
```

Load with:
```bash
zen dev --env .env.development
zen serve --env .env.production
```

The Zenith CLI provides everything you need for productive development!