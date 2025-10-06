"""
Zenith CLI - Command-line interface for Zenith web applications.

Focused on reliable, high-value developer tools.
"""

import subprocess
import sys
from pathlib import Path

import click

from zenith.__version__ import __version__


@click.group()
@click.version_option(version=__version__, package_name="zenithweb", prog_name="Zenith")
def main():
    """Zenith - Modern Python web framework."""
    pass


# ============================================================================
# SECURITY AUTOMATION - Eliminate manual security steps
# ============================================================================


@main.command()
@click.option("--output", "-o", help="Output file (e.g., .env)")
@click.option(
    "--length", default=64, type=int, help="Key length in bytes (default: 64)"
)
@click.option("--force", is_flag=True, help="Overwrite existing key in file")
def keygen(output: str | None, length: int, force: bool):
    """Generate cryptographically secure SECRET_KEY.

    Examples:
      zen keygen                   # Print key to stdout
      zen keygen --output .env     # Write to .env file
      zen keygen --length 32       # Generate 32-byte key
    """
    import secrets

    # Generate cryptographically secure key
    secret_key = secrets.token_urlsafe(length)

    if output:
        output_path = Path(output)

        # Check if file exists and contains SECRET_KEY
        key_exists = False
        if output_path.exists():
            existing_content = output_path.read_text()
            key_exists = "SECRET_KEY=" in existing_content

        if key_exists and not force:
            click.echo(f"❌ SECRET_KEY already exists in {output}")
            click.echo("   Use --force to overwrite existing key")
            sys.exit(1)

        try:
            if key_exists and force:
                # Replace existing SECRET_KEY line
                lines = output_path.read_text().splitlines()
                updated_lines = []
                key_replaced = False

                for line in lines:
                    if line.startswith("SECRET_KEY=") and not key_replaced:
                        updated_lines.append(f"SECRET_KEY={secret_key}")
                        key_replaced = True
                    else:
                        updated_lines.append(line)

                output_path.write_text("\n".join(updated_lines) + "\n")
                click.echo(f"🔄 Updated SECRET_KEY in {output}")
            else:
                # Append to file or create new
                if output_path.exists():
                    with output_path.open("a") as f:
                        f.write(f"\nSECRET_KEY={secret_key}\n")
                else:
                    output_path.write_text(f"SECRET_KEY={secret_key}\n")

                click.echo(f"✅ SECRET_KEY written to {output}")

        except PermissionError:
            click.echo(f"❌ Permission denied writing to {output}")
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error writing to {output}: {e}")
            sys.exit(1)
    else:
        # Print to stdout
        click.echo(secret_key)


# ============================================================================
# DEVELOPMENT TOOLS - Reliable, high-value commands
# ============================================================================


@main.command()
@click.argument("path", default=".")
@click.option("--name", help="Application name")
def new(path: str, name: str | None):
    """Create a new Zenith application with best practices."""
    import secrets

    project_path = Path(path).resolve()

    if not name:
        name = project_path.name

    click.echo(f"🚀 Creating new Zenith app: {name}")
    click.echo(f"📁 Path: {project_path}")

    # Create project directory
    project_path.mkdir(exist_ok=True)

    # Generate cryptographically secure secret key (64 bytes for stronger entropy)
    secret_key = secrets.token_urlsafe(64)
    click.echo("🔑 Generated secure SECRET_KEY (64 bytes)")

    # Create main app.py
    app_py_content = f'''"""
{name} - Zenith API application.
"""

from dotenv import load_dotenv
from zenith import Zenith

# Load environment variables from .env file
load_dotenv()

# Create your Zenith app
app = Zenith()


@app.get("/")
async def root():
    """API root endpoint."""
    return {{"message": "Welcome to {name} API!", "status": "running"}}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "healthy", "service": "{name}"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
'''

    # Create .env file
    env_content = f"""# Environment variables for {name}
SECRET_KEY={secret_key}
DEBUG=true

# Database (uncomment and configure as needed)
# DATABASE_URL=sqlite:///./app.db

# Redis (uncomment if using caching/sessions)
# REDIS_URL=redis://localhost:6379
"""

    # Create requirements.txt with current zenith version
    requirements_content = f"""zenithweb>={__version__}
uvicorn[standard]
python-dotenv
"""

    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*.so
.Python
.venv/
venv/
ENV/

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
"""

    # Create README.md
    readme_content = f"""# {name}

A modern API built with [Zenith](https://zenith-python.org).

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start development server:
   ```bash
   zen dev
   ```

3. Visit http://localhost:8000 to see your API!

## API Endpoints

- `GET /` - API root
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

## Project Structure

- `app.py` - Main application file
- `.env` - Environment variables (configure your secrets here)
- `requirements.txt` - Python dependencies

## Next Steps

- Add your business logic and models
- Configure database connection in `.env`
- Add authentication with `app.add_auth()`
- Deploy to production

## Learn More

- [Zenith Documentation](https://zenith-python.org)
- [API Examples](https://zenith-python.org/examples)
"""

    # Write all files
    files_to_create = [
        ("app.py", app_py_content),
        (".env", env_content),
        ("requirements.txt", requirements_content),
        (".gitignore", gitignore_content),
        ("README.md", readme_content),
    ]

    for filename, content in files_to_create:
        file_path = project_path / filename
        file_path.write_text(content.strip())
        click.echo(f"  ✓ {filename}")

    click.echo("\n✅ Project created successfully!")
    click.echo("\nNext steps:")
    click.echo(f"  cd {project_path.name}")
    click.echo("  pip install -r requirements.txt")
    click.echo("  zen dev                         # Start development server")


@main.command("dev")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--app", default=None, help="Import path to app (e.g., src.api.app:app)")
@click.option("--open", is_flag=True, help="Open browser after start")
@click.option(
    "--testing", is_flag=True, help="Enable testing mode (disables rate limiting)"
)
def dev(host: str, port: int, app: str | None, open: bool, testing: bool):
    """Start development server with hot reload."""
    import os

    if testing:
        os.environ["ZENITH_ENV"] = "test"
        click.echo(
            "🧪 Testing mode enabled - rate limiting and other test-interfering middleware disabled"
        )
    else:
        # Set development environment by default for zen dev
        os.environ.setdefault("ZENITH_ENV", "development")

    _run_server(host, port, reload=True, workers=1, open_browser=open, app_path=app)


@main.command("serve")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--workers", "-w", default=4, type=int, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable reload (development)")
def serve(host: str, port: int, workers: int, reload: bool):
    """Start production server."""
    import os

    # Set production environment by default for zen serve
    os.environ.setdefault("ZENITH_ENV", "production")

    _run_server(host, port, reload=reload, workers=workers)


def _run_server(
    host: str,
    port: int,
    reload: bool = False,
    workers: int = 1,
    open_browser: bool = False,
    app_path: str | None = None,
):
    """Internal function to run uvicorn server."""
    import importlib.util

    # Enhanced app discovery
    app_module = None
    app_var = "app"

    # Strategy 0: Use explicit app path if provided
    if app_path:
        if ":" in app_path:
            app_module, app_var = app_path.split(":", 1)
        else:
            app_module = app_path
            app_var = "app"
        click.echo(f"🎯 Using explicit app path: {app_module}:{app_var}")
    else:
        # Strategy 1: Check for common app files and discover app variable
        discovery_patterns = [
            ("app.py", "app"),
            ("main.py", "app"),
            ("application.py", "app"),
            ("application.py", "application"),
        ]

        for filename, var_name in discovery_patterns:
            if Path(filename).exists():
                # Try to discover the actual app variable by importing the module
                try:
                    module_name = filename.replace(".py", "")
                    spec = importlib.util.spec_from_file_location(module_name, filename)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Check if the expected variable exists and is a Zenith app
                        if hasattr(module, var_name):
                            attr = getattr(module, var_name)
                            if hasattr(attr, "__class__") and "Zenith" in str(
                                type(attr)
                            ):
                                app_module = module_name
                                app_var = var_name
                                break
                            # Also try to find any Zenith app in the module
                            for attr_name in dir(module):
                                if not attr_name.startswith("_"):
                                    attr = getattr(module, attr_name)
                                    if hasattr(attr, "__class__") and "Zenith" in str(
                                        type(attr)
                                    ):
                                        app_module = module_name
                                        app_var = attr_name
                                        break
                        if app_module:
                            break
                except Exception:
                    # If import fails, fall back to filename-based discovery
                    app_module = filename.replace(".py", "")
                    break

    # Strategy 2: Look for nested app structures (like src/api/app.py)
    if not app_module:
        common_paths = [
            "src/app.py",
            "src/api/app.py",
            "src/main.py",
            "app/main.py",
            "api/app.py",
        ]

        for path_str in common_paths:
            path = Path(path_str)
            if path.exists():
                try:
                    # Convert path to module notation: src/api/app.py -> src.api.app
                    module_path = str(path.with_suffix("")).replace("/", ".")
                    spec = importlib.util.spec_from_file_location(
                        module_path.split(".")[-1], path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        # Add the parent directory to sys.path temporarily
                        parent_dir = (
                            str(path.parent.parent.absolute())
                            if len(path.parts) > 1
                            else str(Path.cwd())
                        )
                        if parent_dir not in sys.path:
                            sys.path.insert(0, parent_dir)

                        spec.loader.exec_module(module)

                        if hasattr(module, "app"):
                            attr = module.app
                            if hasattr(attr, "__class__") and "Zenith" in str(
                                type(attr)
                            ):
                                app_module = module_path
                                app_var = "app"
                                break
                except Exception:
                    continue

    if not app_module:
        click.echo("❌ No Zenith app found")
        click.echo("")
        click.echo("🔍 Searched for:")
        click.echo("   • app.py, main.py, application.py (with 'app' variable)")
        click.echo("   • src/app.py, src/api/app.py, src/main.py")
        click.echo("   • app/main.py, api/app.py")
        click.echo("")
        click.echo("💡 Quick solutions:")
        click.echo("   1. Specify explicitly: zen dev --app=my_module:app")
        click.echo("   2. Create main.py: from src.api.app import app")
        click.echo("   3. Generate new app: zen new .")
        click.echo("")
        click.echo("🧪 For testing: zen dev --testing --app=your.module:app")
        click.echo("")
        click.echo("📁 Current directory contents:")
        cwd = Path.cwd()
        py_files = list(cwd.glob("*.py"))
        if py_files:
            for py_file in py_files[:5]:  # Show up to 5 Python files
                click.echo(f"   • {py_file.name}")
            if len(py_files) > 5:
                click.echo(f"   • ... and {len(py_files) - 5} more .py files")
        else:
            click.echo("   • No .py files found")

        subdirs_with_py = []
        for subdir in ["src", "app", "api"]:
            subdir_path = cwd / subdir
            if subdir_path.exists() and subdir_path.is_dir():
                py_files_in_subdir = list(subdir_path.glob("*.py"))
                if py_files_in_subdir:
                    subdirs_with_py.append(
                        f"{subdir}/ ({len(py_files_in_subdir)} .py files)"
                    )

        if subdirs_with_py:
            click.echo("   Subdirectories with Python files:")
            for subdir_info in subdirs_with_py:
                click.echo(f"   • {subdir_info}")

        sys.exit(1)

    if reload:
        click.echo("🔧 Starting Zenith development server...")
        click.echo("🔄 Hot reload enabled - edit files to see changes instantly!")
        cmd = [
            "uvicorn",
            f"{app_module}:{app_var}",
            f"--host={host}",
            f"--port={port}",
            "--reload",
            "--reload-include=*.py",
            "--reload-include=*.html",
            "--reload-include=*.css",
            "--reload-include=*.js",
            "--log-level=info",
        ]
    else:
        click.echo("🚀 Starting Zenith production server...")
        click.echo(f"👥 Workers: {workers}")
        cmd = [
            "uvicorn",
            f"{app_module}:{app_var}",
            f"--host={host}",
            f"--port={port}",
            f"--workers={workers}",
            "--log-level=info",
            "--access-log",
        ]

    click.echo(f"🌐 Server:  http://{host}:{port}")
    click.echo(f"📖 Docs:    http://{host}:{port}/docs")
    click.echo(f"❤️ Health:  http://{host}:{port}/health")

    if open_browser:
        import webbrowser

        webbrowser.open(f"http://{host}:{port}")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")


if __name__ == "__main__":
    main()
