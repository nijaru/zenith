#!/usr/bin/env python3
"""
Zenith Version Management Tool

Automatically updates version across all files to maintain consistency.
Provides both CLI and programmatic interfaces for version management.
"""

import argparse
import re
import sys
from pathlib import Path


class VersionManager:
    """Manages version updates across the Zenith codebase."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.version_patterns = {
            # Python version file
            "zenith/__version__.py": [
                (r'__version__ = "[^"]*"', r'__version__ = "{version}"')
            ],
            # Documentation files
            "**/*.md": [
                (r"v0\.\d+\.\d+", r"v{version}"),
                (r"version 0\.\d+\.\d+", r"version {version}"),
                (r"Version 0\.\d+\.\d+", r"Version {version}"),
            ],
            "**/*.mdx": [
                (r"v0\.\d+\.\d+", r"v{version}"),
                (r"version 0\.\d+\.\d+", r"version {version}"),
            ],
            # Python files with version references
            "**/*.py": [
                (r"# v0\.\d+\.\d+ features", r"# v{version} features"),
                (r"# Version 0\.\d+\.\d+", r"# Version {version}"),
                (r"v0\.\d+\.\d+ - Modern", r"v{version} - Modern"),
            ],
            # Development context files
            "CLAUDE.md": [
                (r"v0\.\d+\.\d+", r"v{version}"),
                (r"Version 0\.\d+\.\d+", r"Version {version}"),
            ],
            "CHANGELOG.md": [
                # Don't auto-update CHANGELOG - it should be manually updated
            ],
        }

    def get_current_version(self) -> str:
        """Get current version from __version__.py."""
        version_file = self.root_dir / "zenith" / "__version__.py"
        if not version_file.exists():
            raise FileNotFoundError(f"Version file not found: {version_file}")

        content = version_file.read_text()
        match = re.search(r'__version__ = "([^"]*)"', content)
        if not match:
            raise ValueError("Could not parse version from __version__.py")

        return match.group(1)

    def increment_version(self, version: str, part: str = "patch") -> str:
        """Increment version number."""
        parts = version.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version}")

        major, minor, patch = map(int, parts)

        if part == "major":
            major += 1
            minor = 0
            patch = 0
        elif part == "minor":
            minor += 1
            patch = 0
        elif part == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid part: {part}. Use 'major', 'minor', or 'patch'")

        return f"{major}.{minor}.{patch}"

    def find_files_with_version(self, old_version: str) -> list[tuple[Path, int]]:
        """Find all files containing version references."""
        files_with_version = []

        # Search patterns
        patterns = [
            rf"v{re.escape(old_version)}",
            rf"version {re.escape(old_version)}",
            rf"Version {re.escape(old_version)}",
            rf'__version__ = "{re.escape(old_version)}"',
        ]

        # File extensions to search
        extensions = {".py", ".md", ".mdx", ".toml", ".json"}

        for file_path in self.root_dir.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix in extensions
                and not any(
                    skip in str(file_path)
                    for skip in [".git", "__pycache__", ".venv", "node_modules"]
                )
            ):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for pattern in patterns:
                        matches = list(re.finditer(pattern, content))
                        if matches:
                            files_with_version.append((file_path, len(matches)))
                            break
                except (UnicodeDecodeError, PermissionError):
                    continue

        return files_with_version

    def update_version_in_file(
        self, file_path: Path, old_version: str, new_version: str
    ) -> int:
        """Update version references in a specific file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content

            # Apply patterns based on file path matching
            updates = 0
            for pattern, replacement_rules in self.version_patterns.items():
                if file_path.match(pattern) or str(file_path).endswith(
                    pattern.replace("**/", "")
                ):
                    for old_pattern, new_pattern in replacement_rules:
                        new_content, count = re.subn(
                            old_pattern,
                            new_pattern.format(version=new_version),
                            content,
                        )
                        if count > 0:
                            content = new_content
                            updates += count

            # Fallback: simple version string replacement
            if updates == 0:
                replacements = [
                    (f"v{old_version}", f"v{new_version}"),
                    (f"version {old_version}", f"version {new_version}"),
                    (f"Version {old_version}", f"Version {new_version}"),
                    (
                        f'__version__ = "{old_version}"',
                        f'__version__ = "{new_version}"',
                    ),
                ]

                for old, new in replacements:
                    new_content, count = re.subn(re.escape(old), new, content)
                    if count > 0:
                        content = new_content
                        updates += count

            # Write back if changed
            if content != original_content:
                file_path.write_text(content, encoding="utf-8")
                return updates

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"Warning: Could not update {file_path}: {e}")

        return 0

    def update_all_versions(
        self, new_version: str, dry_run: bool = False
    ) -> dict[str, int]:
        """Update version across all relevant files."""
        old_version = self.get_current_version()

        if old_version == new_version:
            print(f"Version is already {new_version}")
            return {}

        files_with_version = self.find_files_with_version(old_version)
        results = {}

        print(f"Updating version from {old_version} to {new_version}")
        print(f"Found {len(files_with_version)} files with version references")

        if dry_run:
            print("\nDRY RUN - No files will be modified:")
            for file_path, count in files_with_version:
                rel_path = file_path.relative_to(self.root_dir)
                print(f"  {rel_path} ({count} matches)")
            return {}

        print("\nUpdating files:")
        for file_path, _ in files_with_version:
            updates = self.update_version_in_file(file_path, old_version, new_version)
            if updates > 0:
                rel_path = file_path.relative_to(self.root_dir)
                results[str(rel_path)] = updates
                print(f"  ✅ {rel_path} ({updates} updates)")

        print(f"\n✅ Updated {len(results)} files")
        return results


def main():
    """CLI interface for version management."""
    parser = argparse.ArgumentParser(description="Zenith Version Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Current version command
    subparsers.add_parser("current", help="Show current version")

    # Update version command
    update_parser = subparsers.add_parser("update", help="Update version")
    update_parser.add_argument("version", help="New version (e.g., 0.3.1)")
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )

    # Increment version command
    increment_parser = subparsers.add_parser("increment", help="Increment version")
    increment_parser.add_argument(
        "part",
        choices=["major", "minor", "patch"],
        default="patch",
        nargs="?",
        help="Version part to increment",
    )
    increment_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )

    # Find command
    subparsers.add_parser(
        "find", help="Find files with version references"
    )

    args = parser.parse_args()

    try:
        vm = VersionManager()

        if args.command == "current":
            print(vm.get_current_version())

        elif args.command == "update":
            vm.update_all_versions(args.version, dry_run=args.dry_run)

        elif args.command == "increment":
            current = vm.get_current_version()
            new_version = vm.increment_version(current, args.part)
            print(f"Incrementing {args.part} version: {current} → {new_version}")
            vm.update_all_versions(new_version, dry_run=args.dry_run)

        elif args.command == "find":
            current = vm.get_current_version()
            files = vm.find_files_with_version(current)
            print(f"Files containing version {current}:")
            for file_path, count in files:
                rel_path = file_path.relative_to(vm.root_dir)
                print(f"  {rel_path} ({count} matches)")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
