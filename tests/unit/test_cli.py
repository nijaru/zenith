"""
Legacy CLI tests - DEPRECATED

This file contains tests for the old CLI structure.
New CLI tests are in test_cli_new.py.

This file is kept for reference during the transition but should be removed
once the new CLI tests are proven stable.
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


class TestDeprecatedCLICommands:
    """Test old CLI commands - these should now fail gracefully."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    def test_removed_commands_return_error(self, runner):
        """Test that removed commands return appropriate errors."""
        removed_commands = ["version", "info", "routes", "test", "shell", "d", "s"]

        for cmd in removed_commands:
            result = runner.invoke(main, [cmd])
            assert result.exit_code != 0
            assert "No such command" in result.output or "Error" in result.output

    def test_basic_cli_still_works(self, runner):
        """Test that basic CLI functionality still works."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Zenith" in result.output

    def test_version_flag_works(self, runner):
        """Test that --version flag still works."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "Zenith" in result.output


# Keep some legacy test structure for reference
class TestLegacyCLIStructure:
    """Documentation of what the old CLI structure looked like."""

    def test_old_command_structure_documented(self):
        """Document what commands were removed and why."""
        removed_commands = {
            "version": "Use --version flag instead",
            "info": "Removed - use standard Python tools",
            "routes": "Removed - use /docs endpoint in browser",
            "test": "Removed - use pytest directly",
            "shell": "Removed - use standard Python REPL",
            "d": "Removed shortcut - use 'zen dev'",
            "s": "Removed shortcut - use 'zen serve'",
        }

        # This serves as documentation of the migration
        assert len(removed_commands) == 7
        assert "version" in removed_commands
        assert "shell" in removed_commands

    def test_remaining_commands_documented(self):
        """Document what commands remain in the simplified CLI."""
        remaining_commands = {
            "new": "Create new Zenith application",
            "dev": "Start development server with hot reload",
            "serve": "Start production server",
        }

        assert len(remaining_commands) == 3
        assert "new" in remaining_commands
        assert "dev" in remaining_commands
        assert "serve" in remaining_commands
