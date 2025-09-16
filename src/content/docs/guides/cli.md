---
title: CLI Tools
description: Zenith's command-line interface for development and deployment
---

# Zenith CLI Tools

The `zen` command provides essential tools for developing, testing, and deploying Zenith applications. All commands are designed to be reliable, fast, and provide excellent developer experience.

## Quick Reference

```bash
zen dev                    # Start development server (hot reload)
zen serve                  # Start production server
zen routes                 # Show all registered routes
zen shell                  # Interactive Python shell with app context
zen test                   # Run application tests
zen info                   # Show application information
zen version                # Show Zenith version
zen new <path>             # Create new Zenith application
```

## Development Commands

### `zen dev` - Development Server

Start a development server with hot reload enabled:

```bash
zen dev                              # Start on 127.0.0.1:8000
zen dev --host 0.0.0.0              # Bind to all interfaces
zen dev --port 3000                 # Use custom port
zen dev --open                      # Open browser automatically
```

**Features:**
- **Hot reload** - Automatically restarts on file changes
- **File watching** - Watches `.py`, `.html`, `.css`, `.js` files
- **Interactive logs** - Real-time request logging
- **Health endpoints** - `/health` and `/health/detailed` available
- **API documentation** - Automatic `/docs` endpoint

**Shortcut:** `zen d` (alias for `zen dev`)

**Auto-detection:** Looks for app files in this order:
1. `app.py`
2. `main.py`
3. `application.py`

### `zen shell` - Interactive Shell

Start an interactive Python shell with your application context loaded:

```bash
zen shell                           # Use IPython if available
zen shell --no-ipython             # Force standard Python shell
zen shell --app main.app           # Specify app import path
```

**Features:**
- **App context** - Your application is automatically imported
- **IPython support** - Enhanced shell with syntax highlighting
- **Database access** - Pre-configured database connections
- **Service access** - All services are available for testing

**Example session:**
```python
>>> # App is automatically loaded
>>> app
<zenith.core.application.Zenith object>

>>> # Test services directly
>>> from myapp.services import UserService
>>> users = UserService()
>>> await users.get_all()
```

## Production Commands

### `zen serve` - Production Server

Start a production-ready server with multiple workers:

```bash
zen serve                           # Start with 4 workers on 0.0.0.0:8000
zen serve --workers 8              # Use 8 worker processes
zen serve --host 127.0.0.1         # Bind to localhost only
zen serve --port 80                 # Use port 80
zen serve --reload                  # Enable reload (development)
```

**Features:**
- **Multi-process** - Automatic worker scaling
- **Production logging** - Structured logs with access logs
- **Performance optimized** - Optimized for high throughput
- **Health checks** - Built-in health monitoring
- **Graceful shutdown** - Proper signal handling

**Shortcut:** `zen s` (alias for `zen serve`)

**Production Example:**
```bash
# Production deployment
zen serve --host 0.0.0.0 --port 8000 --workers 4

# Behind reverse proxy
zen serve --host 127.0.0.1 --port 8000 --workers 8
```

## Inspection Commands

### `zen routes` - Route Inspection

Display all registered routes in your application:

```bash
zen routes
```

**Output example:**
```
📍 Registered Routes:
────────────────────────────────────────────────────────────
GET, HEAD    /                              homepage
POST         /users                         create_user
GET          /users/{user_id}               get_user
PUT          /users/{user_id}               update_user
DELETE       /users/{user_id}               delete_user
GET          /health                        health_check
GET          /docs                          swagger_ui
```

**Features:**
- **Method display** - Shows all HTTP methods
- **Path patterns** - Includes path parameters
- **Route names** - Function or endpoint names
- **Auto-discovery** - Finds routes from your app automatically

### `zen info` - Application Information

Show comprehensive application information:

```bash
zen info
```

**Output example:**
```
🔍 Zenith Application Information:
────────────────────────────────────────
Zenith version: 0.2.6
Python version: 3.12.0
Working directory: /Users/dev/my-zenith-app
App files found: app.py
Config files: pyproject.toml, .env
```

**Features:**
- **Environment details** - Python and Zenith versions
- **File detection** - Shows discovered app and config files
- **Directory info** - Current working directory
- **Health status** - Basic application health

## Testing Commands

### `zen test` - Test Runner

Run your application's test suite:

```bash
zen test                            # Run all tests
zen test --verbose                  # Verbose output
zen test --failfast                 # Stop on first failure
```

**Features:**
- **pytest integration** - Uses pytest test runner
- **Automatic discovery** - Finds tests in standard locations
- **Coverage support** - Compatible with coverage tools
- **Parallel execution** - Supports pytest-xdist

**Test organization:**
```
your-app/
├── tests/
│   ├── test_users.py
│   ├── test_auth.py
│   └── integration/
│       └── test_api.py
├── app.py
└── pyproject.toml
```

## Project Management

### `zen new` - Create New Application

Create a new Zenith application with best practices:

```bash
zen new my-app                      # Create in ./my-app/
zen new .                          # Create in current directory
zen new /path/to/app --name MyAPI  # Specify name explicitly
zen new my-api --template api      # API-only template
zen new my-site --template fullstack # Full-stack template
```

**Templates:**
- **`api`** (default) - API-focused application
- **`fullstack`** - Complete web application with frontend

**Generated structure:**
```
my-app/
├── app.py                    # Application entry point
├── services/                 # Business logic
├── models/                   # Pydantic models
├── tests/                    # Test suite
├── pyproject.toml           # Dependencies
├── .env.example             # Environment template
└── README.md                # Documentation
```

### `zen version` - Version Information

Show the installed Zenith version:

```bash
zen version
```

## Common Workflows

### Development Workflow
```bash
# Create new project
zen new my-api
cd my-api

# Start development
zen dev --open

# In another terminal - inspect routes
zen routes

# Test your code
zen test
```

### Debugging Workflow
```bash
# Check application info
zen info

# Interactive debugging
zen shell

# View all routes
zen routes

# Run tests
zen test --verbose
```

### Production Deployment
```bash
# Test production server locally
zen serve --workers 1 --reload

# Production deployment
zen serve --host 0.0.0.0 --port 8000 --workers 4
```

## Configuration

### Environment Detection

The CLI automatically detects your application by looking for:

1. **App files** (in order): `app.py`, `main.py`, `application.py`
2. **App variable**: `app` (the Zenith application instance)
3. **Working directory**: Current directory where you run the command

### Custom App Paths

For non-standard setups, specify the app import path:

```bash
zen shell --app mypackage.application:app
zen dev --app src.main:application
```

### Configuration Files

The CLI respects these configuration files:

- **`.env`** - Environment variables
- **`pyproject.toml`** - Project configuration
- **`pytest.ini`** - Test configuration

## Troubleshooting

### Command Not Found

If `zen` command is not available:

```bash
# Check installation
pip show zenith-web

# Alternative command
python -m zenith.cli --version

# Reinstall if needed
pip install --force-reinstall zenith-web
```

### App Not Found

If CLI can't find your app:

```bash
# Check current directory has app.py, main.py, or application.py
ls *.py

# Check app variable exists
grep "app = " *.py

# Use explicit app path
zen routes --app myfile:myapp
```

### Development Server Issues

If development server won't start:

```bash
# Check for port conflicts
lsof -i :8000

# Use different port
zen dev --port 8001

# Check app file syntax
python -m py_compile app.py
```

### Shell Import Issues

If shell can't import your app:

```bash
# Check Python path
zen shell --app main.app

# Verify app file
python -c "from main import app; print(app)"
```

## Tips & Best Practices

### Performance
- Use `zen serve` for production (multiple workers)
- Use `zen dev` only for development (single worker, reload enabled)
- Monitor with `/health/detailed` endpoint

### Development
- Use `zen dev --open` to automatically open browser
- Use `zen shell` for interactive testing and debugging
- Use `zen routes` to verify your API structure

### Testing
- Run `zen test` before committing code
- Use `zen test --failfast` for quick feedback
- Combine with coverage tools: `coverage run -m pytest`

### Production
- Always use `zen serve` with multiple workers
- Set appropriate `--host` and `--port` for your environment
- Use reverse proxy (nginx) for static files and SSL