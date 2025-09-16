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
@click.version_option(version=__version__, package_name="zenith-web")
def main():
    """Zenith - Modern Python web framework."""
    pass


# ============================================================================
# DEVELOPMENT TOOLS - Reliable, high-value commands
# ============================================================================


@main.command()
@click.option("--app", default=None, help="Import path to application (e.g., main.app)")
@click.option(
    "--no-ipython",
    is_flag=True,
    default=False,
    help="Use standard Python shell instead of IPython",
)
def shell(app: str | None, no_ipython: bool):
    """Start interactive Python shell with Zenith context."""
    from zenith.dev.shell import run_shell

    run_shell(app_path=app, use_ipython=not no_ipython)


@main.command()
@click.argument("path", default=".")
@click.option("--name", help="Application name")
@click.option(
    "--template",
    type=click.Choice(["api", "fullstack"], case_sensitive=False),
    default="api",
    help="Project template",
)
def new(path: str, name: str | None, template: str):
    """Create a new Zenith application with best practices."""
    from zenith.dev.templates import TemplateManager

    manager = TemplateManager()
    project_path = Path(path).resolve()

    if not name:
        name = project_path.name

    click.echo(f"🚀 Creating new Zenith app: {name}")
    click.echo(f"📁 Path: {project_path}")
    click.echo(f"📋 Template: {template}")

    manager.create_project(
        project_path=project_path,
        project_name=name,
        template_name=template,
    )

    click.echo("\n✅ Project created successfully!")
    click.echo("\nNext steps:")
    click.echo(f"  cd {project_path.name}")
    click.echo("  zen dev                 # Start development server")
    click.echo("  zen routes              # View available routes")


@main.command("dev")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--app", default=None, help="Import path to app (e.g., src.api.app:app)")
@click.option("--open", is_flag=True, help="Open browser after start")
def dev(host: str, port: int, app: str | None, open: bool):
    """Start development server with hot reload."""
    _run_server(host, port, reload=True, workers=1, open_browser=open, app_path=app)


@main.command("serve")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--workers", "-w", default=4, type=int, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable reload (development)")
def serve(host: str, port: int, workers: int, reload: bool):
    """Start production server."""
    _run_server(host, port, reload=reload, workers=workers)


# Shortcuts
@main.command("d")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--open", is_flag=True, help="Open browser after start")
def d(host: str, port: int, open: bool):
    """Shortcut for 'dev' command."""
    _run_server(host, port, reload=True, workers=1, open_browser=open)


@main.command("s")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--workers", "-w", default=4, type=int, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable reload (development)")
def s(host: str, port: int, workers: int, reload: bool):
    """Shortcut for 'serve' command."""
    _run_server(host, port, reload=reload, workers=workers)


def _run_server(host: str, port: int, reload: bool = False, workers: int = 1, open_browser: bool = False, app_path: str | None = None):
    """Internal function to run uvicorn server."""
    from pathlib import Path
    import importlib.util
    import os

    # Enhanced app discovery
    app_module = None
    app_var = "app"

    # Strategy 0: Use explicit app path if provided
    if app_path:
        if ':' in app_path:
            app_module, app_var = app_path.split(':', 1)
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
                            if hasattr(attr, '__class__') and 'Zenith' in str(type(attr)):
                                app_module = module_name
                                app_var = var_name
                                break
                            # Also try to find any Zenith app in the module
                            for attr_name in dir(module):
                                if not attr_name.startswith('_'):
                                    attr = getattr(module, attr_name)
                                    if hasattr(attr, '__class__') and 'Zenith' in str(type(attr)):
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
            "api/app.py"
        ]

        for path_str in common_paths:
            path = Path(path_str)
            if path.exists():
                try:
                    # Convert path to module notation: src/api/app.py -> src.api.app
                    module_path = str(path.with_suffix('')).replace('/', '.')
                    spec = importlib.util.spec_from_file_location(module_path.split('.')[-1], path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        # Add the parent directory to sys.path temporarily
                        parent_dir = str(path.parent.parent.absolute()) if len(path.parts) > 1 else str(Path.cwd())
                        if parent_dir not in sys.path:
                            sys.path.insert(0, parent_dir)

                        spec.loader.exec_module(module)

                        if hasattr(module, 'app'):
                            attr = getattr(module, 'app')
                            if hasattr(attr, '__class__') and 'Zenith' in str(type(attr)):
                                app_module = module_path
                                app_var = 'app'
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
        click.echo("💡 Solutions:")
        click.echo("   1. Create main.py with: from src.api.app import app")
        click.echo("   2. Use zen dev --app=src.api.app:app")
        click.echo("   3. Create new app: zen new .")
        click.echo("")
        click.echo("📖 See: https://zenith-python.org/cli#app-discovery")
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


@main.command()
def routes():
    """Show all registered routes in the application."""
    import importlib
    from pathlib import Path

    # Find and import the app
    app_module = None
    for filename in ["app.py", "main.py", "application.py"]:
        if Path(filename).exists():
            module_name = filename.replace(".py", "")
            try:
                app_module = importlib.import_module(module_name)
                break
            except ImportError as e:
                click.echo(f"❌ Error importing {module_name}: {e}")

    if not app_module:
        click.echo("❌ No app module found or importable")
        return

    # Get the app instance
    app = getattr(app_module, "app", None)
    if not app:
        click.echo("❌ No 'app' variable found in module")
        return

    # Display routes
    click.echo("\n📍 Registered Routes:")
    click.echo("─" * 60)

    if hasattr(app, "routes"):
        for route in app.routes:
            methods = ", ".join(route.methods) if hasattr(route, "methods") else "N/A"
            path = route.path if hasattr(route, "path") else "N/A"
            name = route.name if hasattr(route, "name") else "unnamed"
            click.echo(f"{methods:<10} {path:<30} {name}")
    else:
        click.echo("❌ Cannot access routes from app object")


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--failfast", "-f", is_flag=True, help="Stop on first failure")
def test(verbose: bool, failfast: bool):
    """Run application tests."""
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")
    if failfast:
        cmd.append("-x")

    click.echo("🧪 Running tests...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        click.echo("✅ All tests passed!")
    else:
        click.echo("❌ Tests failed")

    sys.exit(result.returncode)


@main.command()
def version():
    """Show Zenith version."""
    from zenith import __version__
    click.echo(f"Zenith {__version__}")


@main.command()
def info():
    """Show application information."""
    import sys
    from pathlib import Path

    click.echo("🔍 Zenith Application Information:")
    click.echo("─" * 40)
    click.echo(f"Zenith version: {__version__}")
    click.echo(f"Python version: {sys.version.split()[0]}")
    click.echo(f"Working directory: {Path.cwd()}")

    # Check for app files
    app_files = []
    for filename in ["app.py", "main.py", "application.py"]:
        if Path(filename).exists():
            app_files.append(filename)

    if app_files:
        click.echo(f"App files found: {', '.join(app_files)}")
    else:
        click.echo("❌ No app files found (app.py, main.py, application.py)")

    # Check for common config files
    config_files = []
    for filename in ["pyproject.toml", "requirements.txt", ".env"]:
        if Path(filename).exists():
            config_files.append(filename)

    if config_files:
        click.echo(f"Config files: {', '.join(config_files)}")


if __name__ == "__main__":
    main()
