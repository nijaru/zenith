"""
Command line interface for Zenith framework.
"""

import click
import asyncio
from pathlib import Path

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


@main.command()
def test():
    """Run the test suite."""
    click.echo("🧪 Running tests...")
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest"], cwd=".")
    sys.exit(result.returncode)


@main.command()
def format():
    """Format code with black and isort."""
    click.echo("🎨 Formatting code...")
    import subprocess
    import sys

    # Run black
    subprocess.run([sys.executable, "-m", "black", "zenith/", "tests/"])

    # Run isort
    subprocess.run([sys.executable, "-m", "isort", "zenith/", "tests/"])

    click.echo("✅ Code formatted")


@main.command()
def lint():
    """Run code quality checks."""
    click.echo("🔍 Running linting...")
    import subprocess
    import sys

    # Run ruff
    result1 = subprocess.run([sys.executable, "-m", "ruff", "check", "zenith/"])

    # Run mypy
    result2 = subprocess.run([sys.executable, "-m", "mypy", "zenith/"])

    if result1.returncode == 0 and result2.returncode == 0:
        click.echo("✅ Code quality checks passed")
    else:
        click.echo("❌ Code quality issues found")
        sys.exit(1)


@main.command()
@click.option("--coverage", is_flag=True, help="Run with coverage report")
def test(coverage: bool):
    """Run tests."""
    click.echo("🧪 Running test suite...")
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "pytest"]
    if coverage:
        cmd.extend(["--cov=zenith", "--cov-report=term-missing"])

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
