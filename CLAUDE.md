# Zenith - AI Assistant Context
*Token-efficient overview for AI assistants*

## Quick Facts
- **Product**: Modern Python API framework with clean architecture
- **Language**: Python 3.11+
- **Focus**: API development with better organization than FastAPI
- **Status**: Early development (v0.0.1-dev)
- **CLI**: `zen` command

## Core Concepts

### 1. Context System (Business Logic Organization)
```python
# Business logic in contexts, not scattered in routes
class Accounts(Context):
    async def create_user(self, data): ...
    async def get_user(self, id): ...
```

### 2. Type-Safe Dependency Injection
```python
# Clean DI without verbose Depends()
@app.get("/users/{id}")
async def get_user(id: int, accounts: Accounts = Context()):
    return await accounts.get_user(id)
```

### 3. Pydantic Integration
```python
# Automatic validation and serialization
@app.post("/users")
async def create_user(user: UserCreate) -> User:
    # Validated input, typed output
```

## Project Structure
```
zenith/
├── zenith/          # Framework source
│   ├── core/       # App kernel, contexts, router
│   ├── web/        # Controllers, middleware
│   ├── live/       # LiveView engine
│   └── channels/   # Real-time channels
├── tests/          # Test suite
├── docs/           # Documentation
└── examples/       # Example apps
```

## Development Status

**Completed**:
- Core application kernel (needs simplification)
- Basic routing with type-safe DI
- Context system foundation
- Pydantic integration

**Current Focus (CRITICAL)**:
- **ZEN-2**: Database integration (SQLAlchemy)
- **ZEN-3**: Complete routing & middleware
- **ZEN-6**: Authentication system

**Explicitly NOT Building**:
- LiveView (not suitable for Python)
- Phoenix Channels (overengineered)
- Supervisor trees (unnecessary)

## Key Files
```
README.md                 # Project overview
ROADMAP.md               # Development priorities
docs/NEXT_STEPS.md       # Immediate action items
docs/archive/            # Outdated specs (archived)
```

## Development Commands
```bash
# Install dev environment
pip install -e ".[dev]"

# Run tests
zen test

# Start dev server  
zen server --reload

# Format code
black zenith/ tests/

# Type check
mypy zenith/
```

## Design Principles
1. **API-first** - Focus on building excellent APIs
2. **Context-driven** - Clean business logic organization
3. **Type-safe** - Full type hints and validation
4. **Async throughout** - Modern Python async/await
5. **Pragmatic** - Ship useful features, not complexity

## Common Tasks

### Adding a Feature
1. Check ROADMAP.md for planned features
2. Write tests first (TDD)
3. Implement in appropriate module
4. Update documentation
5. Run full test suite

### Key Patterns
- Contexts for business logic
- Clean separation of concerns
- Type hints for everything
- Dependency injection without boilerplate
- Events for decoupling components

## Testing
```python
# API testing
async with TestClient(app) as client:
    response = await client.post("/users", json={...})
    assert response.status_code == 201

# Context testing  
async with TestContext(Accounts) as accounts:
    user = await accounts.create_user(...)
    assert user.id
```

## Performance Goals
- Match or exceed FastAPI performance
- Efficient database connection pooling
- <1 second startup time
- <100MB base memory usage
- Ready for Mojo optimization paths

## Architecture Notes
- Context-driven business logic organization
- Type-safe dependency injection
- Event-driven architecture for decoupling
- Middleware pipeline for cross-cutting concerns
- Database integration with SQLAlchemy (in progress)

---
*Optimized for AI assistants - see docs/ for details*