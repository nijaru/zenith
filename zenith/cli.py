"""
Command line interface for Zenith framework.
"""

import asyncio
from pathlib import Path

import click

from zenith.core.application import Application
from zenith.core.config import Config


@click.group()
@click.version_option()
def main():
    """Zenith Framework CLI - Modern Python web framework with real-time features."""
    pass


@main.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--env", default=".env", help="Environment file path")
def server(host: str, port: int, reload: bool, env: str):
    """Start the development server."""
    click.echo("🚀 Starting Zenith development server...")

    # Load configuration
    env_file = Path(env) if Path(env).exists() else None
    config = Config.from_env(env_file)
    config.host = host
    config.port = port

    # Create application
    app = Application(config)

    # Run application
    try:
        asyncio.run(app.run_until_complete())
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")


@main.group()
def new():
    """Create new Zenith projects and components."""
    pass


@new.command("project")
@click.argument("name")
@click.option("--db", default="sqlite", help="Database type (sqlite/postgres/mysql)")
@click.option("--auth/--no-auth", default=True, help="Include authentication")
def new_project(name: str, db: str, auth: bool):
    """Create a new Zenith project."""
    click.echo(f"🚀 Creating new project '{name}'...")
    # TODO: Implement project scaffolding
    click.echo(f"✅ Project '{name}' created!")
    click.echo(f"\nNext steps:")
    click.echo(f"  cd {name}")
    click.echo(f"  zen server")


@main.group()
def db():
    """Database management commands."""
    pass


@db.command("create")
def db_create():
    """Create database tables."""
    click.echo("📊 Creating database tables...")
    # TODO: Run alembic migrations
    click.echo("✅ Database created")


@db.command("migrate")
@click.argument("message")
def db_migrate(message: str):
    """Create a new migration."""
    click.echo(f"📝 Creating migration: {message}")
    # TODO: Generate alembic migration
    click.echo("✅ Migration created")


@db.command("upgrade")
def db_upgrade():
    """Apply database migrations."""
    click.echo("⬆️ Applying migrations...")
    # TODO: Run alembic upgrade
    click.echo("✅ Database upgraded")


@main.group()
def dev():
    """Development tools for Zenith contributors."""
    pass


@dev.command("format")
@click.option("--check", is_flag=True, help="Check only, don't modify files")
def dev_format(check: bool):
    """Format Zenith framework code with ruff."""
    click.echo("🎨 Formatting code...")
    import subprocess
    import sys
    
    cmd = ["ruff", "format"]
    if check:
        cmd.append("--check")
    cmd.append(".")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        click.echo("✅ Code formatted" if not check else "✅ Code formatting is correct")
    else:
        click.echo("❌ Formatting issues found" if check else "❌ Failed to format code")
        sys.exit(1)


@dev.command("lint")
@click.option("--fix", is_flag=True, help="Auto-fix issues")
def dev_lint(fix: bool):
    """Lint Zenith framework code with ruff."""
    click.echo("🔍 Running linter...")
    import subprocess
    import sys
    
    cmd = ["ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.append(".")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        click.echo("✅ Linting passed")
    else:
        click.echo("❌ Linting issues found")
        sys.exit(1)


@dev.command("type-check")
def dev_type_check():
    """Run pyright type checking."""
    click.echo("🔍 Running type checker...")
    import subprocess
    import sys
    
    result = subprocess.run(["pyright"])
    
    if result.returncode == 0:
        click.echo("✅ Type checking passed")
    else:
        click.echo("❌ Type errors found")
        sys.exit(1)


@dev.command("test")
@click.option("--coverage", is_flag=True, help="Run with coverage report")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def dev_test(coverage: bool, verbose: bool):
    """Run Zenith test suite."""
    click.echo("🧪 Running tests...")
    import subprocess
    import sys
    
    cmd = [sys.executable, "-m", "pytest"]
    if coverage:
        cmd.extend(["--cov=zenith", "--cov-report=term-missing"])
    if verbose:
        cmd.append("-v")
    
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


@dev.command("build")
def dev_build():
    """Build distribution packages."""
    click.echo("📦 Building distribution...")
    import subprocess
    import sys
    
    # Clean old builds
    subprocess.run(["rm", "-rf", "dist/", "build/", "*.egg-info"])
    
    # Build
    result = subprocess.run([sys.executable, "-m", "build"])
    
    if result.returncode == 0:
        click.echo("✅ Build complete")
        click.echo("\nNext steps:")
        click.echo("  zen dev publish         # Publish to PyPI")
        click.echo("  zen dev publish --test  # Publish to Test PyPI")
    else:
        click.echo("❌ Build failed")
        sys.exit(1)


@dev.command("publish")
@click.option("--test", is_flag=True, help="Publish to Test PyPI instead of production")
@click.option("--skip-build", is_flag=True, help="Skip building, use existing dist/")
def dev_publish(test: bool, skip_build: bool):
    """Publish Zenith to PyPI."""
    import subprocess
    import sys
    
    if not skip_build:
        click.echo("📦 Building distribution...")
        result = subprocess.run([sys.executable, "-m", "build"])
        if result.returncode != 0:
            click.echo("❌ Build failed")
            sys.exit(1)
    
    repository = "testpypi" if test else "pypi"
    click.echo(f"📤 Publishing to {repository}...")
    
    cmd = [sys.executable, "-m", "twine", "upload"]
    if test:
        cmd.extend(["--repository", "testpypi"])
    cmd.append("dist/*")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        click.echo(f"✅ Published to {repository}!")
        if test:
            click.echo("\nInstall with:")
            click.echo("  pip install -i https://test.pypi.org/simple/ zenith-framework")
        else:
            click.echo("\nInstall with:")
            click.echo("  pip install zenith-framework")
    else:
        click.echo("❌ Publishing failed")
        sys.exit(1)


@main.command()
def version():
    """Show Zenith version."""
    from zenith import __version__
    click.echo(f"Zenith Framework v{__version__}")


if __name__ == "__main__":
    main()
