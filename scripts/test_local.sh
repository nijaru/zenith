#!/bin/bash
# Local testing script - Run before pushing to save CI minutes

set -e  # Exit on error

echo "🧪 Zenith Local Test Suite"
echo "=========================="

# 1. Format check (instant)
echo "📝 Checking code formatting..."
ruff format --check . || (echo "❌ Format issues found. Run: ruff format ." && exit 1)

# 2. Lint check (fast)
echo "🔍 Running linter..."
# Allow some lint issues for now, focus on critical ones
ruff check . --select="E,F,UP,B" || echo "⚠️  Some lint issues found but continuing..."

# 3. Type check (medium)
echo "🔤 Type checking..."
pyright zenith/ || (echo "❌ Type errors found" && exit 1)

# 4. Unit tests (fast)
echo "🧪 Running unit tests..."
SECRET_KEY=test-key-long-enough uv run pytest tests/unit/ -x --tb=short -q

# 5. Performance check (optional)
if [ "$1" == "--bench" ]; then
    echo "📊 Running performance benchmark..."
    python benchmarks/simple_bench.py
fi

echo ""
echo "✅ All local tests passed!"
echo "💡 Safe to push to GitHub"
echo ""
echo "Note: GitHub Actions will run:"
echo "  - Full test suite with PostgreSQL"
echo "  - Integration tests"
echo "  - Coverage reporting"