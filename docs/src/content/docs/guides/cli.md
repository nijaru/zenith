---
title: CLI Tools
description: Zenith's streamlined command-line interface for development and deployment
---

# Zenith CLI Tools

The `zen` command provides essential tools for developing and deploying Zenith applications. The CLI has been streamlined to focus on the most valuable, reliable commands that developers use daily.

## Quick Reference

```bash
zen new <path>             # Create new Zenith application with secure defaults
zen keygen                 # Generate secure SECRET_KEY
zen dev                    # Start development server (hot reload)
zen serve                  # Start production server
zen --version              # Show Zenith version
```

## Project Creation

### `zen new` - Create New Application

Create a new Zenith application:

```bash
zen new my-app                      # Create in ./my-app/
zen new .                          # Create in current directory
zen new /path/to/app --name MyAPI  # Specify name explicitly
```

**Generated structure:**
```
my-app/
├── app.py                    # Application entry point with sample endpoints
├── .env                     # Environment variables (with generated secret key)
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # Quick start documentation
```

**Generated app.py includes:**
- Basic Zenith application setup
- Sample API endpoints (`/` and `/health`)
- Production-ready configuration examples
- Clear documentation and next steps

## Security Commands

### `zen keygen` - Generate Secure Keys

Generate cryptographically secure SECRET_KEY values for your application:

```bash
zen keygen                          # Print key to stdout
zen keygen --output .env            # Write to .env file
zen keygen --output .env --force    # Overwrite existing key
zen keygen --length 32              # Generate 32-byte key (default: 64)
```

**Use cases:**
- **Key rotation** - Generate new keys for production rotation
- **Environment setup** - Add keys to existing .env files
- **CI/CD pipelines** - Generate keys for automated deployments

**Note:** The `zen new` command automatically generates a secure SECRET_KEY, so you typically only need `zen keygen` for key rotation or adding keys to existing projects.

**Automatic .env Loading:** Zenith automatically loads `.env` and `.env.local` files from your project directory, so keys generated with `zen keygen --output .env` work immediately without additional configuration.

## Development Commands

### `zen dev` - Development Server

Start a development server with hot reload enabled:

```bash
zen dev                              # Start on 127.0.0.1:8000
zen dev --host 0.0.0.0              # Bind to all interfaces
zen dev --port 3000                 # Use custom port
zen dev --open                      # Open browser automatically
zen dev --app src.api.app:app       # Specify app import path
zen dev --testing                   # Enable testing mode
```

**Features:**
- **Development environment** - Automatically sets `ZENITH_ENV=development`
- **Hot reload** - Automatically restarts on file changes
- **File watching** - Watches `.py`, `.html`, `.css`, `.js` files
- **Intelligent app discovery** - Finds your app automatically
- **Testing mode** - Disables rate limiting for test suites
- **Interactive logs** - Real-time request logging
- **Health endpoints** - `/health` and `/docs` available automatically

### Testing Mode

The `--testing` flag is crucial for test suites that make multiple rapid requests:

```bash
# Development with testing mode (disables rate limiting)
zen dev --testing

# For test scripts and CI/CD
ZENITH_ENV=test zen dev
```

**Why testing mode?**
- Disables rate limiting middleware that can cause `429 Too Many Requests` errors in tests
- Automatically enabled when `ZENITH_ENV=test` environment variable is set
- Safe for production (only affects rate limiting, not security features)

### App Discovery

The CLI automatically discovers your application:

**Search strategy:**
1. **Explicit app path** (if provided): `--app src.api.app:app`
2. **Common app files**: `app.py`, `main.py`, `application.py`
3. **Nested structures**: `src/app.py`, `src/api/app.py`, `app/main.py`

**Error messages:**
```bash
❌ No Zenith app found

🔍 Searched for:
   • app.py, main.py, application.py (with 'app' variable)
   • src/app.py, src/api/app.py, src/main.py
   • app/main.py, api/app.py

 Quick solutions:
   1. Specify explicitly: zen dev --app=my_module:app
   2. Create main.py: from src.api.app import app
   3. Generate new app: zen new .

 For testing: zen dev --testing --app=your.module:app

 Current directory contents:
   • main.py
   • config.py
   Subdirectories with Python files:
   • src/ (5 .py files)
```

## Production Commands

### `zen serve` - Production Server

Start a production-ready server with multiple workers:

```bash
zen serve                           # Start with 4 workers on 0.0.0.0:8000
zen serve --workers 8              # Use 8 worker processes
zen serve --host 127.0.0.1         # Bind to localhost only
zen serve --port 80                 # Use port 80
zen serve --reload                  # Enable reload (development mode)
```

**Features:**
- **Production environment** - Automatically sets `ZENITH_ENV=production`
- **Multi-process** - Automatic worker scaling based on CPU cores
- **Production logging** - Structured logs with access logs
- **Performance optimized** - Optimized for high throughput
- **Health checks** - Built-in health monitoring
- **Graceful shutdown** - Proper signal handling

**Production Example:**
```bash
# Production deployment
zen serve --host 0.0.0.0 --port 8000 --workers 4

# Behind reverse proxy
zen serve --host 127.0.0.1 --port 8000 --workers 8

# Container deployment
zen serve --host 0.0.0.0 --port 8000 --workers 2
```

## Common Workflows

### New Project Workflow
```bash
# Create new project
zen new my-api
cd my-api

# Install dependencies
pip install -r requirements.txt

# Start development
zen dev --open

# The generated app includes:
# - GET / (API root with welcome message)
# - GET /health (health check)
# - GET /docs (automatic OpenAPI documentation)
```

### Development Workflow
```bash
# Start development server
zen dev

# For rapid testing (disables rate limiting)
zen dev --testing

# Custom configuration
zen dev --host 0.0.0.0 --port 3000 --app src.main:app
```

### Testing Workflow
```bash
# Enable testing mode for test suites
ZENITH_ENV=test python -m pytest

# Or in development server
zen dev --testing

# Testing mode prevents these common errors:
# - 429 Too Many Requests from rate limiting
# - Middleware interference with test isolation
```

### Production Deployment
```bash
# Test production server locally
zen serve --workers 1 --reload

# Production deployment
zen serve --host 0.0.0.0 --port 8000 --workers 4

# With environment variables
SECRET_KEY=your-secret zen serve --workers 4
```

## Configuration

### Environment Variables

The CLI respects these environment variables:

- **`ZENITH_ENV=test`** - Enables testing mode (disables rate limiting)
- **`SECRET_KEY`** - Application secret key
- **`DATABASE_URL`** - Database connection string
- **`DEBUG`** - Enable debug mode

### App Path Resolution

For non-standard setups, use explicit app paths:

```bash
# Module notation
zen dev --app mypackage.application:app
zen dev --app src.main:application

# For complex structures
zen dev --app project.apps.api:create_app
```

### Configuration Files

The CLI respects these configuration files:

- **`.env`** - Environment variables (automatically generated by `zen new`)
- **`requirements.txt`** - Python dependencies
- **`pyproject.toml`** - Project configuration

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

### App Discovery Issues

If CLI can't find your app:

```bash
# Use explicit app path
zen dev --app myfile:myapp

# Check app variable exists
grep "app = " *.py

# Verify app file syntax
python -m py_compile app.py

# Create main.py wrapper for complex structures
echo "from src.api.app import app" > main.py
```

### Testing Issues

If tests fail with rate limiting errors:

```bash
# Enable testing mode
zen dev --testing

# Or set environment variable
export ZENITH_ENV=test
zen dev

# In pytest configuration (conftest.py)
import os
os.environ["ZENITH_ENV"] = "test"
```

### Development Server Issues

If development server won't start:

```bash
# Check for port conflicts
lsof -i :8000

# Use different port
zen dev --port 8001

# Check app file imports
python -c "from app import app; print(' App loads successfully')"
```

## Migration from Previous Versions

If upgrading from earlier Zenith versions, note that these commands have been removed for simplicity:

- `zen routes` → Use `/docs` endpoint in your browser
- `zen shell` → Use standard Python REPL or IPython
- `zen test` → Use `pytest` directly
- `zen info` → Use `zen --version` and standard Python tools
- `zen d` / `zen s` → Use full command names for clarity

**Why simplified?**
- Focus on high-value commands used daily
- Reduce maintenance burden and potential bugs
- Clearer, more predictable CLI interface
- Better error messages and app discovery

## Tips & Best Practices

### Development
- Use `zen dev --testing` when running test suites
- Use `zen dev --open` to automatically open browser
- Set up `.env` file for consistent local configuration

### Testing
- Always enable testing mode: `ZENITH_ENV=test`
- Use explicit app paths in CI/CD: `zen dev --app src.main:app`
- Create wrapper files for complex app structures

### Production
- Always use `zen serve` with multiple workers
- Set appropriate `--host` and `--port` for your environment
- Use environment variables for secrets, not command-line arguments
- Use reverse proxy (nginx/traefik) for static files and SSL

### Performance
- Use `zen serve` for production (multiple workers)
- Use `zen dev` only for development (single worker, reload enabled)
- Monitor with `/health` endpoint
- Consider container orchestration for scaling