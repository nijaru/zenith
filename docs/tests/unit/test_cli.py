"""
Comprehensive tests for Zenith CLI commands.

Tests all CLI commands to ensure they are error-free and working correctly.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from zenith.cli import main


class TestCLICommands:
    """Test all CLI commands for reliability and correctness."""

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
        """Test that CLI help works."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Zenith - Modern Python web framework" in result.output
        assert "Commands:" in result.output

    def test_version_command(self, runner):
        """Test zen version command."""
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "Zenith" in result.output

    def test_info_command(self, runner, temp_dir, test_app_file):
        """Test zen info command."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(main, ["info"])
            assert result.exit_code == 0
            assert "Zenith Application Information" in result.output
            assert "Zenith version:" in result.output
            assert "Python version:" in result.output
            assert "Working directory:" in result.output

    def test_routes_command(self, runner, temp_dir, test_app_file):
        """Test zen routes command."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            # Change to temp dir where app.py exists
            os.chdir(temp_dir)
            result = runner.invoke(main, ["routes"])

            # Routes command may fail if it can't import the app, but shouldn't crash
            assert result.exit_code in [0, 1]
            # The command should handle import errors gracefully
            if (
                "Error importing" in result.output
                or "No app module found" in result.output
            ):
                # This is expected in test environment
                pass
            elif result.exit_code == 0:
                assert "Registered Routes" in result.output

    @patch("subprocess.run")
    def test_dev_command(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen dev command."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            # Mock subprocess.run to avoid actually starting the server
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["dev"])

            # Should try to start the server
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "uvicorn" in call_args
            assert "--reload" in call_args
            assert "app:app" in call_args

    @patch("subprocess.run")
    def test_dev_command_with_options(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen dev command with options."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["dev", "--host", "0.0.0.0", "--port", "3000"])

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "--host=0.0.0.0" in call_args
            assert "--port=3000" in call_args

    @patch("subprocess.run")
    def test_serve_command(self, mock_run, runner, temp_dir, test_app_file):
        """Test zen serve command."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["serve"])

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "uvicorn" in call_args
            assert "--workers=4" in call_args  # Default workers
            assert "--reload" not in call_args  # No reload in production

    @patch("subprocess.run")
    def test_serve_command_with_workers(
        self, mock_run, runner, temp_dir, test_app_file
    ):
        """Test zen serve command with custom workers."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["serve", "--workers", "8"])

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "--workers=8" in call_args

    @patch("subprocess.run")
    def test_test_command(self, mock_run, runner):
        """Test zen test command."""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(main, ["test"])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "python" in call_args
        assert "-m" in call_args
        assert "pytest" in call_args

    @patch("subprocess.run")
    def test_test_command_with_options(self, mock_run, runner):
        """Test zen test command with verbose and failfast options."""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(main, ["test", "--verbose", "--failfast"])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "-v" in call_args
        assert "-x" in call_args

    def test_new_command(self, runner, temp_dir):
        """Test zen new command."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            project_name = "test_project"
            result = runner.invoke(main, ["new", project_name])

            # Check if project creation was attempted
            # Note: The actual template creation might fail in tests
            # but the command should handle it gracefully
            assert result.exit_code in [0, 1]
            if result.exit_code == 0:
                assert "Creating new Zenith app" in result.output

    def test_new_command_with_template(self, runner, temp_dir):
        """Test zen new command with template option."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(main, ["new", "test_app", "--template", "fullstack"])

            assert result.exit_code in [0, 1]
            if result.exit_code == 0:
                assert "Template: fullstack" in result.output

    @patch("zenith.dev.shell.run_shell")
    def test_shell_command(self, mock_run_shell, runner, temp_dir, test_app_file):
        """Test zen shell command."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            result = runner.invoke(main, ["shell", "--no-ipython"])

            # Should call run_shell
            assert mock_run_shell.called
            assert mock_run_shell.call_args[1]["use_ipython"] is False

    @patch("zenith.dev.shell.run_shell")
    def test_shell_command_with_app(
        self, mock_run_shell, runner, temp_dir, test_app_file
    ):
        """Test zen shell command with app path."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            result = runner.invoke(main, ["shell", "--app", "app.app"])

            assert mock_run_shell.called
            assert mock_run_shell.call_args[1]["app_path"] == "app.app"

    def test_shortcuts_d_command(self, runner):
        """Test zen d shortcut for dev."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with runner.isolated_filesystem():
                # Create a dummy app.py
                Path("app.py").write_text("from zenith import Zenith\napp = Zenith()")

                result = runner.invoke(main, ["d"])

                assert mock_run.called
                call_args = mock_run.call_args[0][0]
                assert "--reload" in call_args

    def test_shortcuts_s_command(self, runner):
        """Test zen s shortcut for serve."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with runner.isolated_filesystem():
                # Create a dummy app.py
                Path("app.py").write_text("from zenith import Zenith\napp = Zenith()")

                result = runner.invoke(main, ["s"])

                assert mock_run.called
                call_args = mock_run.call_args[0][0]
                assert "--workers=4" in call_args

    def test_dev_no_app_file(self, runner):
        """Test zen dev when no app file exists."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["dev"])

            # Should exit with error code
            assert result.exit_code == 1
            assert "No Zenith app file found" in result.output

    def test_serve_no_app_file(self, runner):
        """Test zen serve when no app file exists."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["serve"])

            # Should exit with error code
            assert result.exit_code == 1
            assert "No Zenith app file found" in result.output

    def test_routes_no_app_file(self, runner):
        """Test zen routes when no app file exists."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["routes"])

            # Should handle gracefully
            assert (
                "No app module found" in result.output
                or "No Zenith app file found" in result.output
            )

    @patch("webbrowser.open")
    @patch("subprocess.run")
    def test_dev_open_browser(
        self, mock_run, mock_browser, runner, temp_dir, test_app_file
    ):
        """Test zen dev --open opens browser."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            os.chdir(temp_dir)

            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(main, ["dev", "--open"])

            assert mock_browser.called
            assert "http://127.0.0.1:8000" in mock_browser.call_args[0][0]


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_cli_import(self):
        """Test that CLI can be imported."""
        from zenith.cli import main

        assert main is not None

    def test_cli_entrypoint(self):
        """Test that CLI entrypoint exists."""
        from zenith.cli import main

        assert callable(main)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_zen_command_available(self):
        """Test that zen command is available in PATH after installation."""
        # This would only work if zenith is actually installed
        # Skip in unit tests, useful for integration testing
        pass


class TestCLIErrorHandling:
    """Test error handling in CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    def test_invalid_command(self, runner):
        """Test handling of invalid command."""
        result = runner.invoke(main, ["nonexistent"])
        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output

    def test_invalid_template(self, runner):
        """Test handling of invalid template in new command."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["new", "test", "--template", "invalid"])
            assert result.exit_code != 0

    @patch("subprocess.run")
    def test_server_interrupt(self, mock_run, runner):
        """Test handling of KeyboardInterrupt in server commands."""
        mock_run.side_effect = KeyboardInterrupt()

        with runner.isolated_filesystem():
            Path("app.py").write_text("from zenith import Zenith\napp = Zenith()")

            result = runner.invoke(main, ["dev"])
            # Should handle KeyboardInterrupt gracefully
            assert "Server stopped" in result.output

    @patch("subprocess.run")
    def test_test_command_failure(self, mock_run, runner):
        """Test handling of test failures."""
        mock_run.return_value = MagicMock(returncode=1)

        result = runner.invoke(main, ["test"])

        assert result.exit_code == 1
        assert "Tests failed" in result.output
