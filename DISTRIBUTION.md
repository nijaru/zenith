# Zenith Framework Distribution Guide

## Overview

Zenith is distributed as a Python package through multiple channels to maximize accessibility.

## Installation Methods

### 1. PyPI (Production) - Primary Channel
```bash
pip install zenith-framework
```

### 2. Test PyPI (Pre-release) - Testing Channel  
```bash
pip install -i https://test.pypi.org/simple/ zenith-framework
```

### 3. GitHub (Development) - Edge Channel
```bash
# Latest stable
pip install git+https://github.com/nijaru/zenith

# Specific version
pip install git+https://github.com/nijaru/zenith@v0.0.1

# Development branch
pip install git+https://github.com/nijaru/zenith@develop
```

### 4. Local Development
```bash
# Clone and install in editable mode
git clone https://github.com/nijaru/zenith
cd zenith
pip install -e ".[dev]"
```

### 5. Homebrew (Future)
```bash
# macOS/Linux users
brew tap nijaru/zenith
brew install zenith
```

## User Personas & Commands

### Framework Users (Building apps WITH Zenith)

These are developers using Zenith to build their applications.

**Installation:**
```bash
pip install zenith-framework
```

**Available Commands:**
```bash
zen --help                  # Show all commands
zen version                 # Show version

# Project Management
zen new project myapp      # Create new project
zen server                 # Run development server
zen server --prod          # Run production server

# Database Operations  
zen db create              # Create database tables
zen db migrate "message"   # Create migration
zen db upgrade             # Apply migrations
```

### Framework Contributors (Developing Zenith itself)

These are developers contributing to the Zenith framework.

**Setup:**
```bash
git clone https://github.com/nijaru/zenith
cd zenith
pip install -e ".[dev]"
```

**Development Commands:**
```bash
# Code Quality
zen dev format             # Auto-format code
zen dev format --check     # Check formatting
zen dev lint               # Run linter
zen dev lint --fix         # Auto-fix linting issues
zen dev type-check         # Run type checking

# Testing
zen dev test               # Run test suite
zen dev test --coverage    # With coverage report
zen dev test -v            # Verbose output

# Distribution
zen dev build              # Build packages
zen dev publish --test     # Publish to Test PyPI
zen dev publish            # Publish to PyPI (maintainers only)
```

## Publishing Process

### For Maintainers

1. **Update Version**
   ```python
   # zenith/__version__.py
   __version__ = "0.1.0"  # Update version
   ```

2. **Build Distribution**
   ```bash
   zen dev build
   ```

3. **Test on Test PyPI**
   ```bash
   zen dev publish --test
   
   # Test installation
   pip install -i https://test.pypi.org/simple/ zenith-framework
   ```

4. **Publish to Production PyPI**
   ```bash
   zen dev publish
   ```

5. **Tag Release**
   ```bash
   git tag v0.1.0
   git push --tags
   ```

### Automated Publishing (CI/CD)

GitHub Actions automatically publishes to Test PyPI on every push to main.
Production PyPI publishing happens on tagged releases.

## Package Structure

```
zenith-framework/
├── zenith/              # Main package
│   ├── __init__.py     # Package initialization
│   ├── __version__.py  # Version management
│   ├── cli.py          # CLI commands
│   └── ...
├── pyproject.toml      # Package configuration
├── README.md           # Package description
└── LICENSE             # MIT License
```

## Version Management

- **Development**: 0.0.x (pre-release, Test PyPI)
- **Alpha**: 0.1.x (early adopters, PyPI)
- **Beta**: 0.x.x (public beta, PyPI)
- **Stable**: 1.x.x (production ready, PyPI)

## Dependencies

### Runtime Dependencies
- Python 3.11+
- Starlette (ASGI framework)
- Pydantic (validation)
- Click (CLI)
- SQLAlchemy (database)
- PyJWT (authentication)

### Development Dependencies
- pytest (testing)
- ruff (formatting/linting)
- pyright (type checking)
- build (packaging)
- twine (publishing)

## Platform Support

- **Operating Systems**: Linux, macOS, Windows
- **Python Versions**: 3.11, 3.12, 3.13
- **Architectures**: x86_64, ARM64

## Package Naming

- **PyPI Package**: `zenith-framework`
- **Import Name**: `zenith`
- **CLI Command**: `zen`

## Why Different Names?

- **zenith-framework** on PyPI to avoid conflicts
- **zenith** for imports for clean code
- **zen** for CLI for brevity

## Installation Size

- **Package Size**: ~500KB
- **With Dependencies**: ~15MB
- **Development Setup**: ~50MB

## Support Channels

- **Issues**: https://github.com/nijaru/zenith/issues
- **Discussions**: https://github.com/nijaru/zenith/discussions
- **Documentation**: https://nijaru.github.io/zenith