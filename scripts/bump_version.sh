#!/bin/bash
# Zenith Version Bump Helper Script
# Provides convenient wrapper around version_manager.py

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    error "Not in a git repository"
fi

# Check if working directory is clean
if [[ -n $(git status --porcelain) ]]; then
    warning "Working directory has uncommitted changes"
    echo -e "${YELLOW}Uncommitted files:${NC}"
    git status --porcelain
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Aborting due to uncommitted changes"
    fi
fi

# Parse command line arguments
case "${1:-}" in
    "current"|"c")
        info "Current version:"
        python scripts/version_manager.py current
        ;;
    "patch"|"p")
        info "Bumping patch version..."
        python scripts/version_manager.py increment patch
        success "Patch version bumped"
        ;;
    "minor"|"m")
        info "Bumping minor version..."
        python scripts/version_manager.py increment minor
        success "Minor version bumped"
        ;;
    "major"|"M")
        info "Bumping major version..."
        python scripts/version_manager.py increment major
        success "Major version bumped"
        ;;
    "")
        # Interactive mode
        current_version=$(python scripts/version_manager.py current)
        info "Current version: $current_version"
        echo
        echo "Choose version bump type:"
        echo "  1) Patch (bug fixes)         - e.g., 0.3.1 → 0.3.2"
        echo "  2) Minor (new features)      - e.g., 0.3.1 → 0.4.0"
        echo "  3) Major (breaking changes)  - e.g., 0.3.1 → 1.0.0"
        echo "  4) Custom version"
        echo "  5) Cancel"
        echo
        read -p "Enter choice (1-5): " -n 1 -r choice
        echo
        echo

        case $choice in
            1)
                info "Bumping patch version..."
                python scripts/version_manager.py increment patch
                ;;
            2)
                info "Bumping minor version..."
                python scripts/version_manager.py increment minor
                ;;
            3)
                info "Bumping major version..."
                python scripts/version_manager.py increment major
                ;;
            4)
                read -p "Enter new version (e.g., 0.3.2): " new_version
                if [[ ! $new_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                    error "Invalid version format. Use semantic versioning (e.g., 0.3.2)"
                fi
                info "Setting version to $new_version..."
                python scripts/version_manager.py update "$new_version"
                ;;
            5|*)
                info "Cancelled"
                exit 0
                ;;
        esac
        ;;
    *)
        # Custom version provided
        if [[ ! $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            error "Invalid version format: $1. Use semantic versioning (e.g., 0.3.2)"
        fi
        info "Setting version to $1..."
        python scripts/version_manager.py update "$1"
        ;;
esac

# Get new version
new_version=$(python scripts/version_manager.py current)
success "Version is now: $new_version"

# Offer to commit changes
echo
read -p "Commit version changes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add -A
    git commit -m "bump: version to $new_version

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
    success "Version changes committed"

    # Offer to create tag
    echo
    read -p "Create git tag v$new_version? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag "v$new_version" -m "Release v$new_version"
        success "Git tag v$new_version created"

        echo
        info "Next steps:"
        echo "  - Push changes: git push origin main"
        echo "  - Push tags: git push origin --tags"
        echo "  - Build package: uv build"
        echo "  - Upload to PyPI: twine upload dist/zenith-web-$new_version*"
    fi
fi

echo
info "Version update complete!"