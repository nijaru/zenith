# Internal Development Setup

## Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Git

## Environment Setup

```bash
# Clone and virtual env
git clone git@github.com:nijaru/zenith.git
cd zenith
python -m venv venv
source venv/bin/activate

# Development install
pip install -e ".[dev]"

# Database setup (Docker)
docker run -d --name zenith-postgres -e POSTGRES_PASSWORD=zenith -e POSTGRES_DB=zenith_dev -p 5432:5432 postgres:14
docker run -d --name zenith-redis -p 6379:6379 redis:6-alpine
```

## Environment Variables

Create `.env`:
```
DEBUG=true
SECRET_KEY=dev-secret-change-in-prod
DATABASE_URL=postgresql://postgres:zenith@localhost/zenith_dev
REDIS_URL=redis://localhost:6379
LOG_LEVEL=DEBUG
```

## Development Workflow

### Daily Commands
```bash
zen test                 # Run tests
zen server --reload      # Dev server
zen format              # Format code
zen lint                # Check code quality
```

### Project Structure
```
zenith/
├── zenith/             # Framework source
├── tests/              # Test suite
├── docs/internal/      # Internal docs
├── docs/spec/          # Framework spec
└── benchmarks/         # Performance tests
```

### Git Workflow
```bash
git checkout -b feat/feature-name
# Make changes
git commit -m "feat: description"
# Push and create PR when ready
```

## Testing
```bash
zen test                    # All tests
zen test tests/unit/        # Unit tests only
zen test --coverage         # With coverage
zen test -k "test_name"     # Specific test
```

## Code Quality
```bash
black zenith/ tests/        # Format
isort zenith/ tests/        # Sort imports  
mypy zenith/                # Type check
ruff check zenith/          # Lint
```

## Database Operations
```bash
zen db create               # Create database
zen db migrate             # Run migrations
zen db rollback            # Rollback migration
zen db console            # Database shell
```

## Debugging
- Add `import ipdb; ipdb.set_trace()` for breakpoints
- `DEBUG=true zen server` for debug mode
- Check logs in console output

## Performance Testing
```bash
python benchmarks/basic_benchmark.py
# Profile with: python -m cProfile script.py
```

## Troubleshooting
- **Import errors**: `pip install -e .`
- **DB connection**: Check PostgreSQL running
- **Redis errors**: Check Redis running  
- **Test failures**: Check `.env` file exists

---
*Internal setup guide - not for public consumption*