"""
Comprehensive tests for the new simplified Zenith CLI.

Tests the streamlined CLI with only zen new/dev/serve commands,
including the new --testing flag functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from zenith.cli import main


class TestSimplifiedCLI:
    """Test the simplified CLI with only essential commands."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def test_app_file(self, temp_dir):
        """Create a test app.py file."""
        app_file = temp_dir / "app.py"
        app_file.write_text("""
from zenith import Zenith

app = Zenith()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}

@app.get("/health")
async def health():
    return {"status": "ok"}
""")
        return app_file

    def test_cli_help(self, runner):
        """Test that CLI help shows only simplified commands."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Zenith - Modern Python web framework" in result.output

        # Should only show the four main commands
        assert "new" in result.output
        assert "dev" in result.output
        assert "serve" in result.output
        assert "keygen" in result.output

        # Should NOT show removed commands as top-level commands
        # (Note: "routes" may appear in generate command description, which is fine)
        assert "  shell " not in result.output
        assert "  test " not in result.output
        assert "  info " not in result.output
        # Note: --version flag is still present and that's correct

    def test_version_flag(self, runner):
        """Test --version flag works."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        # The actual output format includes version number
        assert "version" in result.output

    def test_new_command(self, runner, temp_dir):
        """Test zen new command creates project structure."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            project_name = "test_project"
            result = runner.invoke(main, ["new", project_name])

            assert result.exit_code == 0
            assert "Creating new Zenith app" in result.output

            # Check that the project directory and files were created
            project_path = Path(project_name)
            assert project_path.exists()
            assert (project_path / "app.py").exists()
            assert (project_path / ".env").exists()
            assert (project_path / "requirements.txt").exists()
            assert (project_path / "README.md").exists()
            assert (project_path / ".gitignore").exists()

            # Check app.py contains basic Zenith app
            app_content = (project_path / "app.py").read_text()
            assert "from zenith import Zenith" in app_content
            assert "app = Zenith()" in app_content

            # Check .env has SECRET_KEY
            env_content = (project_path / ".env").read_text()
            assert "SECRET_KEY=" in env_content

    def test_new_command_current_directory(self, runner, temp_dir):
        """Test zen new . creates project in current directory."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(main, ["new", "."])

            assert result.exit_code == 0
            assert "Creating new Zenith app" in result.output

            # Files should be created in current directory
            assert Path("app.py").exists()
            assert Path(".env").exists()
            assert Path("requirements.txt").exists()

    @patch("subprocess.run")
    def test_dev_command_basic(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen dev command starts development server."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["dev"])

            assert result.exit_code == 0
            assert mock_run.called

            call_args = mock_run.call_args[0][0]
            assert "uvicorn" in call_args
            assert "--reload" in call_args
            assert "app:app" in call_args

    @patch("subprocess.run")
    def test_dev_command_with_testing_flag(
        self, mock_run, runner, temp_dir, test_app_file
    ):
        """Test zen dev --testing sets testing mode environment variable."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["dev", "--testing"])

            assert result.exit_code == 0
            assert "🧪 Testing mode enabled" in result.output
            assert (
                "rate limiting and other test-interfering middleware disabled"
                in result.output
            )

            # Check that ZENITH_ENV environment variable was set
            assert os.environ.get("ZENITH_ENV") == "test"

            # Clean up
            if "ZENITH_ENV" in os.environ:
                del os.environ["ZENITH_ENV"]

    @patch("subprocess.run")
    def test_dev_command_with_options(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen dev command with host, port, and app options."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(
                main,
                [
                    "dev",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "3000",
                    "--app",
                    "myapp:application",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_run.call_args[0][0]
            assert "--host=0.0.0.0" in call_args
            assert "--port=3000" in call_args
            assert "myapp:application" in call_args

    @patch("webbrowser.open")
    @patch("subprocess.run")
    def test_dev_command_open_browser(
        self, mock_run, mock_browser, runner, temp_dir, test_app_file
    ):
        """Test zen dev --open opens browser."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["dev", "--open"])

            assert result.exit_code == 0
            assert mock_browser.called
            assert "http://127.0.0.1:8000" in mock_browser.call_args[0][0]

    @patch("subprocess.run")
    def test_serve_command_basic(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen serve command starts production server."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["serve"])

            assert result.exit_code == 0
            assert mock_run.called

            call_args = mock_run.call_args[0][0]
            assert "uvicorn" in call_args
            assert "--workers=4" in call_args  # Default workers
            assert "--reload" not in call_args  # No reload in production

    @patch("subprocess.run")
    def test_serve_command_with_options(
        self, mock_run, runner, temp_dir, test_app_file
    ):
        """Test zen serve command with custom options."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(
                main, ["serve", "--host", "127.0.0.1", "--port", "80", "--workers", "8"]
            )

            assert result.exit_code == 0
            call_args = mock_run.call_args[0][0]
            assert "--host=127.0.0.1" in call_args
            assert "--port=80" in call_args
            assert "--workers=8" in call_args

    def test_keygen_command_basic(self, runner):
        """Test zen keygen command generates a key."""
        result = runner.invoke(main, ["keygen"])
        assert result.exit_code == 0
        # Check that output looks like a secure key (base64url format)
        output = result.output.strip()
        assert len(output) >= 32  # Should be a reasonably long key
        assert all(
            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for c in output
        )

    def test_keygen_command_to_file(self, runner, temp_dir):
        """Test zen keygen --output writes to file."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            env_file = "test.env"
            result = runner.invoke(main, ["keygen", "--output", env_file])
            assert result.exit_code == 0
            assert "✅ SECRET_KEY written to" in result.output

            # Verify file was created and contains SECRET_KEY
            assert Path(env_file).exists()
            content = Path(env_file).read_text()
            assert "SECRET_KEY=" in content

    def test_keygen_command_force_overwrite(self, runner, temp_dir):
        """Test zen keygen --force overwrites existing key."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            env_file = "test.env"

            # Create initial file with SECRET_KEY
            Path(env_file).write_text("SECRET_KEY=old_key\nOTHER_VAR=value")

            # Try without --force (should fail)
            result = runner.invoke(main, ["keygen", "--output", env_file])
            assert result.exit_code != 0
            assert "already exists" in result.output

            # Try with --force (should succeed)
            result = runner.invoke(main, ["keygen", "--output", env_file, "--force"])
            assert result.exit_code == 0
            assert "Updated SECRET_KEY" in result.output

            # Verify OTHER_VAR is still there
            content = Path(env_file).read_text()
            assert "OTHER_VAR=value" in content
            assert "SECRET_KEY=old_key" not in content  # Old key replaced

    @patch("subprocess.run")
    def test_serve_command_with_reload(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen serve --reload enables reload for development testing."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["serve", "--reload"])

            assert result.exit_code == 0
            call_args = mock_run.call_args[0][0]
            assert "--reload" in call_args

    def test_dev_no_app_file(self, runner):
        """Test zen dev with enhanced error message when no app file exists."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["dev"])

            assert result.exit_code == 1
            assert "❌ No Zenith app found" in result.output
            assert "🔍 Searched for:" in result.output
            assert "💡 Quick solutions:" in result.output
            assert "zen dev --app=my_module:app" in result.output
            assert "zen new ." in result.output

    def test_serve_no_app_file(self, runner):
        """Test zen serve with enhanced error message when no app file exists."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["serve"])

            assert result.exit_code == 1
            assert "❌ No Zenith app found" in result.output

    @patch("subprocess.run")
    def test_dev_keyboard_interrupt(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen dev handles KeyboardInterrupt gracefully."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.side_effect = KeyboardInterrupt()

            result = runner.invoke(main, ["dev"])

            assert "Server stopped" in result.output

    @patch("subprocess.run")
    def test_serve_keyboard_interrupt(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen serve handles KeyboardInterrupt gracefully."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.side_effect = KeyboardInterrupt()

            result = runner.invoke(main, ["serve"])

            assert "Server stopped" in result.output

    def test_removed_commands_not_available(self, runner):
        """Test that removed commands are no longer available."""
        removed_commands = ["shell", "test", "routes", "info", "d", "s"]

        for cmd in removed_commands:
            result = runner.invoke(main, [cmd])
            assert result.exit_code != 0
            assert "No such command" in result.output or "Error" in result.output


class TestCLIAppDiscovery:
    """Test the enhanced app discovery functionality."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_app_discovery_app_py(self, runner):
        """Test app discovery finds app.py."""
        with runner.isolated_filesystem():
            Path("app.py").write_text("from zenith import Zenith\napp = Zenith()")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(main, ["dev"])

                assert result.exit_code == 0
                call_args = mock_run.call_args[0][0]
                assert "app:app" in call_args

    def test_app_discovery_main_py(self, runner):
        """Test app discovery finds main.py."""
        with runner.isolated_filesystem():
            Path("main.py").write_text("from zenith import Zenith\napp = Zenith()")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(main, ["dev"])

                assert result.exit_code == 0
                call_args = mock_run.call_args[0][0]
                assert "main:app" in call_args

    def test_app_discovery_explicit_app_path(self, runner):
        """Test explicit app path overrides discovery."""
        with runner.isolated_filesystem():
            Path("myfile.py").write_text(
                "from zenith import Zenith\napplication = Zenith()"
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(main, ["dev", "--app", "myfile:application"])

                assert result.exit_code == 0
                call_args = mock_run.call_args[0][0]
                assert "myfile:application" in call_args

    def test_app_discovery_nested_structure(self, runner):
        """Test app discovery in nested directories."""
        with runner.isolated_filesystem():
            # Create nested structure
            src_dir = Path("src")
            src_dir.mkdir()
            (src_dir / "app.py").write_text("from zenith import Zenith\napp = Zenith()")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(main, ["dev"])

                assert result.exit_code == 0
                call_args = mock_run.call_args[0][0]
                assert "src.app:app" in call_args

    def test_enhanced_error_message_content(self, runner):
        """Test that enhanced error message contains helpful information."""
        with runner.isolated_filesystem():
            # Create some files to show in directory listing
            Path("config.py").write_text("# config file")
            Path("utils.py").write_text("# utils file")
            sub_dir = Path("src")
            sub_dir.mkdir()
            (sub_dir / "models.py").write_text("# models")
            (sub_dir / "views.py").write_text("# views")

            result = runner.invoke(main, ["dev"])

            assert result.exit_code == 1
            assert "❌ No Zenith app found" in result.output
            assert "🔍 Searched for:" in result.output
            assert "app.py, main.py, application.py" in result.output
            assert "💡 Quick solutions:" in result.output
            assert "zen dev --app=my_module:app" in result.output
            assert "zen new ." in result.output
            assert "🧪 For testing: zen dev --testing" in result.output
            assert "📁 Current directory contents:" in result.output
            assert "config.py" in result.output
            assert "utils.py" in result.output
            assert "src/ (2 .py files)" in result.output


class TestTestingModeIntegration:
    """Test testing mode functionality integration."""

    def test_testing_mode_explicit_parameter(self):
        """Test that explicit testing parameter works."""
        from zenith import Zenith

        # Test without testing mode
        app1 = Zenith()
        assert app1.testing is False

        # Test with explicit testing=True
        app2 = Zenith(testing=True)
        assert app2.testing is True

    def test_testing_mode_zenith_env_variable(self):
        """Test that ZENITH_ENV=test environment variable enables testing mode."""
        from zenith import Zenith

        # Test without testing mode
        app1 = Zenith()
        assert app1.testing is False

        # Test with new ZENITH_ENV environment variable
        os.environ["ZENITH_ENV"] = "test"
        try:
            app2 = Zenith()
            assert app2.testing is True
        finally:
            del os.environ["ZENITH_ENV"]

    def test_testing_mode_parameter(self):
        """Test that testing parameter works."""
        from zenith import Zenith

        app = Zenith(testing=True)
        assert app.testing is True

    def test_testing_mode_disables_rate_limiting(self):
        """Test that testing mode disables rate limiting middleware."""
        from zenith import Zenith

        # Create app in testing mode
        app = Zenith(testing=True)

        # Check that rate limiting middleware is not added
        middleware_classes = [m.cls.__name__ for m in app.middleware]

        # Should not contain rate limiting middleware
        assert "RateLimitMiddleware" not in middleware_classes

    def test_testing_mode_preserves_other_middleware(self):
        """Test that testing mode only disables rate limiting, not other middleware."""
        from zenith import Zenith

        app = Zenith(testing=True)
        middleware_classes = [m.cls.__name__ for m in app.middleware]

        # Should still have other essential middleware
        assert "SecurityHeadersMiddleware" in middleware_classes
        assert "RequestLoggingMiddleware" in middleware_classes


class TestCLIProjectGeneration:
    """Test the project generation functionality."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_generated_app_structure(self, runner):
        """Test that generated app has correct structure and content."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["new", "testapp"])

            assert result.exit_code == 0

            # Check app.py content
            app_content = Path("testapp/app.py").read_text()
            assert "from zenith import Zenith" in app_content
            assert "app = Zenith()" in app_content
            assert '@app.get("/")' in app_content
            assert '@app.get("/health")' in app_content

            # Check requirements.txt
            reqs_content = Path("testapp/requirements.txt").read_text()
            assert "zenithweb" in reqs_content

            # Check README.md
            readme_content = Path("testapp/README.md").read_text()
            assert "Zenith" in readme_content
            assert "zen dev" in readme_content

            # Check .gitignore
            gitignore_content = Path("testapp/.gitignore").read_text()
            assert "__pycache__/" in gitignore_content
            assert ".env" in gitignore_content

    def test_generated_secret_key_strength(self, runner):
        """Test that generated SECRET_KEY is strong enough."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["new", "testapp"])

            assert result.exit_code == 0

            env_content = Path("testapp/.env").read_text()

            # Extract SECRET_KEY value
            secret_key = None
            for line in env_content.split("\n"):
                if line.startswith("SECRET_KEY="):
                    secret_key = line.split("=", 1)[1]
                    break

            assert secret_key is not None
            assert len(secret_key) >= 32  # Must be at least 32 characters for JWT

    def test_project_name_with_directory_creation(self, runner):
        """Test project creation with various name patterns."""
        with runner.isolated_filesystem():
            # Test with hyphenated name
            result = runner.invoke(main, ["new", "my-cool-app"])
            assert result.exit_code == 0
            assert Path("my-cool-app").exists()
            assert Path("my-cool-app/app.py").exists()

            # Test with underscore name
            result = runner.invoke(main, ["new", "my_app"])
            assert result.exit_code == 0
            assert Path("my_app").exists()
            assert Path("my_app/app.py").exists()
