# Zenith Framework - Development Commands
# Run 'make help' to see all available commands

.PHONY: help install format lint type-check test clean build publish

# Default target
help:
	@echo "Zenith Framework - Available Commands:"
	@echo ""
	@echo "  make install      Install development dependencies"
	@echo "  make format       Auto-format code with ruff"
	@echo "  make lint         Check code style with ruff"
	@echo "  make type-check   Run pyright type checking"
	@echo "  make test         Run test suite"
	@echo "  make test-cov     Run tests with coverage"
	@echo "  make clean        Remove build artifacts"
	@echo "  make build        Build distribution packages"
	@echo "  make publish-test Publish to Test PyPI"
	@echo "  make pre-commit   Install pre-commit hooks"
	@echo "  make ci           Run all CI checks locally"
	@echo ""

# Development setup
install:
	pip install -e ".[dev,benchmark]"
	@echo "✅ Development environment ready"

# Code formatting - automatically fixes issues
format:
	@echo "🎨 Formatting code..."
	ruff format .
	ruff check . --fix
	@echo "✅ Code formatted"

# Linting - checks without fixing
lint:
	@echo "🔍 Running linter..."
	ruff format --check .
	ruff check .
	@echo "✅ Linting passed"

# Type checking
type-check:
	@echo "🔍 Running type checker..."
	pyright
	@echo "✅ Type checking passed"

# Testing
test:
	@echo "🧪 Running tests..."
	pytest

test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest --cov=zenith --cov-report=term-missing

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned build artifacts"

# Build distribution
build: clean
	@echo "📦 Building distribution..."
	python -m build
	@echo "✅ Build complete"

# Publish to Test PyPI
publish-test: build
	@echo "📤 Publishing to Test PyPI..."
	python -m twine upload --repository testpypi dist/*
	@echo "✅ Published to Test PyPI"

# Install pre-commit hooks
pre-commit:
	@echo "🔧 Installing pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	pre-commit run --all-files
	@echo "✅ Pre-commit hooks installed"

# Run all CI checks locally
ci: format lint type-check test
	@echo "✅ All CI checks passed"

# Quick check before committing
check: format test
	@echo "✅ Ready to commit"