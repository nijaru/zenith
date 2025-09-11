"""
Zenith CLI - Command-line interface for Zenith web applications.

Similar to Rails, Django-admin, and Phoenix mix commands.
"""

import sys
from pathlib import Path
import secrets
import string

import click

from zenith.dev.templates import TemplateManager
from zenith.dev.templates.template_manager import TemplateContext
from zenith.__version__ import __version__


@click.group()
@click.version_option(version=__version__, package_name='zenith-web')
def main():
    """Zenith - Modern Python web framework."""
    pass


# ============================================================================
# INTERACTIVE SHELL - For debugging and development
# ============================================================================

@main.command()
@click.option('--app', default=None, help='Import path to application (e.g., main.app)')
@click.option('--no-ipython', is_flag=True, default=False, help='Use standard Python shell instead of IPython')
def shell(app: str | None, no_ipython: bool):
    """Start interactive Python shell with Zenith context."""
    from zenith.dev.shell import run_shell
    run_shell(app_path=app, use_ipython=not no_ipython)


# ============================================================================
# CORE COMMANDS - For users building apps with Zenith
# ============================================================================


@main.command()
@click.argument("path", default=".")
@click.option("--name", help="Application name")
@click.option("--web", "template", flag_value="web", help="Create full web application with templates and static files")
@click.option("--template", default="api", type=click.Choice(["api", "web"]), help="Project template")
@click.option("--db", default="sqlite", type=click.Choice(["sqlite", "postgres", "mysql"]))
def new(path: str, name: str, template: str, db: str):
    """Create a new Zenith application with state-of-the-art defaults."""
    project_path = Path(path).resolve()
    project_name = name or project_path.name

    if path == ".":
        click.echo("🚀 Initializing Zenith app in current directory...")
    else:
        click.echo(f"🚀 Creating new Zenith app '{project_name}' with {template} template...")
        project_path.mkdir(parents=True, exist_ok=True)

    # Generate secure production-ready secret key
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    secret_key = ''.join(secrets.choice(chars) for _ in range(64))

    # Initialize template system
    template_manager = TemplateManager()
    context = TemplateContext(
        project_name=project_name,
        secret_key=secret_key,
        db=db,
        template_type=template
    )

    # Get all required templates for this project type
    file_templates = template_manager.get_all_templates_for_type(template)

    # Generate all project files from templates
    click.echo("📁 Generating project files...")
    
    for file_path, template_name in file_templates.items():
        full_path = project_path / file_path
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate content from template
        try:
            content = template_manager.render_template(template_name, context)
            full_path.write_text(content)
            click.echo(f"   ✅ {file_path}")
        except (OSError, PermissionError, UnicodeError, ValueError, KeyError) as e:
            click.echo(f"   ❌ {file_path}: {e}")
            continue

    # Show completion message
    click.echo("\n✅ Project created successfully!")
    click.echo("\n🚀 Next steps:")
    if path != ".":
        click.echo(f"   cd {project_name}")
    click.echo("   zen dev")
    click.echo("\n📖 Then visit: http://localhost:8000/docs")



# ============================================================================
# DEVELOPMENT COMMANDS
# ============================================================================


@main.command("dev")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--open", is_flag=True, help="Open browser after start")
def dev(host: str, port: int, open: bool):
    """Start Zenith development server with hot reload."""
    import subprocess
    import webbrowser
    import time
    from pathlib import Path

    # Find the app file
    app_file = None
    app_var = "app"

    for filename in ["app.py", "main.py", "application.py"]:
        if Path(filename).exists():
            app_file = filename.replace(".py", "")
            break

    if not app_file:
        click.echo("❌ No Zenith app file found")
        click.echo("   Looking for: app.py, main.py, or application.py")
        click.echo("   💡 Create a new app: zen new .")
        click.echo("   💡 Or ensure your app file is named correctly")
        sys.exit(1)

    # Build development server command with hot reload
    cmd = [
        "uvicorn", 
        f"{app_file}:{app_var}",
        f"--host={host}", 
        f"--port={port}",
        "--reload",
        "--reload-include=*.py",
        "--reload-include=*.html", 
        "--reload-include=*.css",
        "--reload-include=*.js",
        "--log-level=info",
    ]

    click.echo("🔧 Starting Zenith development server...")
    click.echo(f"🔄 Hot reload enabled - edit files to see changes instantly!")
    click.echo(f"🌐 Local:   http://{host}:{port}")
    click.echo(f"📖 Docs:    http://{host}:{port}/docs")
    click.echo(f"❤️ Health:  http://{host}:{port}/health")
    
    # Open browser if requested
    if open:
        def open_browser():
            """Open browser after server starts."""
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f"http://{host}:{port}")
        
        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo(f"\n👋 Development server stopped")


@main.command("serve")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--workers", "-w", default=4, type=int, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable hot reload (development mode)")
def serve(host: str, port: int, workers: int, reload: bool):
    """Start Zenith server (production or development with --reload)."""
    import subprocess
    from pathlib import Path

    # Find the app file
    app_file = None
    app_var = "app"

    for filename in ["app.py", "main.py", "application.py"]:
        if Path(filename).exists():
            app_file = filename.replace(".py", "")
            break

    if not app_file:
        click.echo("❌ No Zenith app file found")
        click.echo("   Looking for: app.py, main.py, or application.py")
        click.echo("   💡 Create a new app: zen new .")
        click.echo("   💡 Or ensure your app file is named correctly")
        sys.exit(1)

    if reload:
        click.echo("🔧 Starting Zenith development server...")
        click.echo(f"🔄 Hot reload enabled - edit files to see changes instantly!")
        cmd = [
            "uvicorn", 
            f"{app_file}:{app_var}",
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
            f"{app_file}:{app_var}",
            f"--host={host}", 
            f"--port={port}",
            f"--workers={workers}",
            "--log-level=info",
            "--access-log",
        ]
    
    click.echo(f"🌐 Server:  http://{host}:{port}")
    click.echo(f"📖 Docs:    http://{host}:{port}/docs")
    click.echo(f"❤️ Health:  http://{host}:{port}/health")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("\n👋 Production server stopped")


# Shortcuts for common commands (Rails-style)
@main.command("d")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--open", is_flag=True, help="Open browser after start")
@click.pass_context
def dev_shortcut(ctx, host: str, port: int, open: bool):
    """Shortcut for 'dev' command."""
    ctx.invoke(dev, host=host, port=port, open=open)

@main.command("s")
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--workers", "-w", default=4, type=int, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable hot reload (development mode)")
@click.pass_context
def serve_shortcut(ctx, host: str, port: int, workers: int, reload: bool):
    """Shortcut for 'serve' command."""
    ctx.invoke(serve, host=host, port=port, workers=workers, reload=reload)



@main.command()
def routes():
    """Show all registered routes in the application."""
    import importlib
    from pathlib import Path

    if not Path("app.py").exists():
        click.echo("❌ No app.py found")
        sys.exit(1)

    try:
        app_module = importlib.import_module("app")
        app = app_module.app

        click.echo("📍 Registered Routes:\n")
        click.echo(f"{'Method':<8} {'Path':<30} {'Handler'}")
        click.echo("-" * 60)

        # Get routes from the app
        if hasattr(app, "routes"):
            for route in app.routes:
                for method in route.methods:
                    click.echo(f"{method:<8} {route.path:<30} {route.endpoint.__name__}")
        else:
            click.echo("  No routes registered yet")

    except (ModuleNotFoundError, ImportError, AttributeError, SyntaxError) as e:
        click.echo("❌ Error loading app")
        click.echo(f"   Details: {e}")
        click.echo("   💡 Check that your app file:")
        click.echo("      • Defines an 'app' variable")
        click.echo("      • Has valid Python syntax")
        click.echo("      • Imports are working correctly")
        sys.exit(1)


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--failfast", "-f", is_flag=True, help="Stop on first failure")
def test(verbose: bool, failfast: bool):
    """Run application tests."""
    import subprocess

    click.echo("🧪 Running tests...")

    cmd = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    if failfast:
        cmd.append("-x")

    # Add test directory if it exists
    if Path("tests").exists():
        cmd.append("tests/")
    elif Path("test").exists():
        cmd.append("test/")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        click.echo("✅ All tests passed!")
    else:
        click.echo("❌ Tests failed")

    sys.exit(result.returncode)


# ============================================================================
# DATABASE COMMANDS
# ============================================================================


@main.group(name='g')
def generate():
    """Generate code for your application."""
    pass


@generate.command()
@click.argument('name')
@click.option('--fields', '-f', help='Field definitions (e.g., "name:str email:str age:int")')
def model(name: str, fields: str):
    """Generate a SQLModel model."""
    from zenith.dev.generators import generate_code, write_generated_files, parse_field_spec
    
    field_dict = parse_field_spec(fields) if fields else {}
    files = generate_code('model', name, fields=field_dict)
    
    click.echo(f"🏗️  Generating model: {name}")
    created = write_generated_files(files)
    if created:
        click.echo(f"✅ Generated {len(created)} file(s)")


@generate.command()
@click.argument('name')
@click.option('--model', '-m', help='Associated model name')
def context(name: str, model: str | None):
    """Generate a business logic context."""
    from zenith.dev.generators import generate_code, write_generated_files
    
    options = {'model': model} if model else {}
    files = generate_code('context', name, **options)
    
    click.echo(f"🏗️  Generating context: {name}")
    created = write_generated_files(files)
    if created:
        click.echo(f"✅ Generated {len(created)} file(s)")


@generate.command()
@click.argument('name')
@click.option('--model', '-m', help='Associated model name')
@click.option('--crud', is_flag=True, help='Generate full CRUD operations')
def api(name: str, model: str | None, crud: bool):
    """Generate API routes."""
    from zenith.dev.generators import generate_code, write_generated_files
    
    options = {'model': model} if model else {}
    if crud:
        options['crud'] = True
    
    files = generate_code('api', name, **options)
    
    click.echo(f"🏗️  Generating API routes: {name}")
    created = write_generated_files(files)
    if created:
        click.echo(f"✅ Generated {len(created)} file(s)")


# ============================================================================
# UTILITY COMMANDS
# ============================================================================


@main.command()
def version():
    """Show Zenith version."""
    from zenith import __version__
    click.echo(f"Zenith v{__version__}")


@main.command()
def info():
    """Show application information."""
    from pathlib import Path

    click.echo("📊 Application Information\n")

    # Check project structure
    if Path("app.py").exists():
        click.echo("  ✓ app.py found")
    else:
        click.echo("  ✗ app.py not found")

    if Path(".env").exists():
        click.echo("  ✓ .env found")

    if Path("requirements.txt").exists():
        click.echo("  ✓ requirements.txt found")

    if Path("tests").exists():
        click.echo("  ✓ tests/ directory found")

    click.echo("\nAvailable commands:")
    click.echo("  zen new my-app      # Create new API project")
    click.echo("  zen dev             # Run development server")
    click.echo("  zen serve           # Run production server")
    click.echo("  zen d               # Shortcut for dev")
    click.echo("  zen test            # Run tests")
    click.echo("  zen routes          # Show routes")
    click.echo("  zen db upgrade      # Apply migrations")


# ============================================================================
# DATABASE MIGRATION COMMANDS
# ============================================================================

@main.group()
def db():
    """Database migration commands."""
    pass


@db.command()
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def init(migrations_dir: str):
    """Initialize migrations directory."""
    import os
    from zenith.db import create_migration_manager
    
    # Try to get database URL from environment or config
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        manager.init_migrations()
        click.echo(f"✅ Initialized migrations in {migrations_dir}/")
    except Exception as e:
        click.echo("❌ Failed to initialize migrations")
        click.echo(f"   Error: {e}")
        click.echo("   💡 Make sure you have write permissions in this directory")
        click.echo("   💡 Check that DATABASE_URL is properly configured")


@db.command()
@click.argument("message")
@click.option("--autogenerate/--no-autogenerate", default=True, 
              help="Automatically detect model changes")
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def revision(message: str, autogenerate: bool, migrations_dir: str):
    """Create a new migration revision."""
    import os
    from zenith.db import create_migration_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        revision_id = manager.create_migration(message, autogenerate)
        if revision_id:
            click.echo(f"✅ Created migration: {message} ({revision_id})")
        else:
            click.echo("❌ Failed to create migration")
            click.echo("   💡 Check that your models are properly defined")
            click.echo("   💡 Ensure migrations directory has write permissions")
            click.echo("   💡 Try: zen db init (if migrations not initialized)")
    except Exception as e:
        click.echo("❌ Error creating migration")
        click.echo(f"   Details: {e}")
        click.echo("   💡 Common fixes:")
        click.echo("      • Check DATABASE_URL environment variable")
        click.echo("      • Ensure database is accessible")
        click.echo("      • Verify model imports are correct")


@db.command()
@click.argument("revision", default="head")
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def upgrade(revision: str, migrations_dir: str):
    """Upgrade database to revision (default: head)."""
    import os
    from zenith.db import create_migration_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        if manager.upgrade(revision):
            click.echo(f"✅ Upgraded database to {revision}")
        else:
            click.echo("❌ Upgrade failed")
    except Exception as e:
        click.echo(f"❌ Error upgrading database: {e}")


@db.command()
@click.argument("revision")
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def downgrade(revision: str, migrations_dir: str):
    """Downgrade database to revision."""
    import os
    from zenith.db import create_migration_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        if manager.downgrade(revision):
            click.echo(f"✅ Downgraded database to {revision}")
        else:
            click.echo("❌ Downgrade failed")
    except Exception as e:
        click.echo(f"❌ Error downgrading database: {e}")


@db.command()
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def current(migrations_dir: str):
    """Show current database revision."""
    import os
    from zenith.db import create_migration_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        current_rev = manager.current_revision()
        if current_rev:
            click.echo(f"Current revision: {current_rev}")
        else:
            click.echo("No migrations applied yet")
    except Exception as e:
        click.echo(f"❌ Error getting current revision: {e}")


@db.command()
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def history(migrations_dir: str):
    """Show migration history."""
    import os
    from zenith.db import create_migration_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        history = manager.migration_history()
        
        if not history:
            click.echo("No migrations found")
            return
        
        click.echo("Migration History:")
        click.echo("─" * 80)
        
        for rev in history:
            click.echo(f"{rev['revision'][:8]} | {rev['message']}")
            if rev['down_revision']:
                click.echo(f"         └─ from {rev['down_revision'][:8]}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Error getting migration history: {e}")


@db.command()
@click.option("--dir", "migrations_dir", default="migrations", help="Migrations directory")
def status(migrations_dir: str):
    """Show migration status."""
    import os
    from zenith.db import create_migration_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    
    try:
        manager = create_migration_manager(database_url, migrations_dir)
        status = manager.status()
        
        click.echo("Database Migration Status:")
        click.echo("─" * 40)
        click.echo(f"Current revision: {status['current_revision'] or 'None'}")
        click.echo(f"Total migrations: {status['total_migrations']}")
        click.echo(f"Pending migrations: {status['pending_migrations']}")
        
        if status['pending_migrations'] > 0:
            click.echo("\n⚠️  Run 'zen db upgrade' to apply pending migrations")
        else:
            click.echo("\n✅ Database is up to date")
            
    except Exception as e:
        click.echo(f"❌ Error getting migration status: {e}")


if __name__ == "__main__":
    main()
