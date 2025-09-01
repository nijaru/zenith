# Internal Code & Documentation Standards

## Code Standards

### Python Style
- **Formatting**: Black (line length 88)
- **Import sorting**: isort
- **Linting**: Ruff
- **Type checking**: mypy

### Naming Conventions
```python
# Files
my_module.py                # snake_case

# Classes  
class MyClass:              # PascalCase

# Functions/variables
def my_function():          # snake_case
my_variable = 1

# Constants
MY_CONSTANT = "value"       # UPPER_SNAKE_CASE

# Private
def _private_function():    # _leading_underscore
```

### Type Hints (Required)
```python
from typing import Optional, List, Dict, Any

async def process_data(
    items: List[Dict[str, Any]], 
    timeout: Optional[float] = None
) -> Dict[str, int]:
    ...
```

### Error Handling
```python
# Custom exceptions
class ZenithError(Exception):
    pass

class ValidationError(ZenithError):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

# Usage
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Async Patterns
```python
# Use async/await for I/O
async def fetch_data() -> Dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Connection management
async with db.transaction():
    await db.execute(query1)
    await db.execute(query2)
```

## Testing Standards

### Test Structure
```python
class TestUserContext:
    """Test user context operations."""
    
    @pytest.fixture
    async def context(self):
        async with create_test_context() as ctx:
            yield ctx
    
    async def test_create_user_success(self, context):
        """Test successful user creation."""
        # Arrange
        data = {"email": "test@example.com"}
        
        # Act  
        user = await context.accounts.create_user(data)
        
        # Assert
        assert user.email == "test@example.com"
```

### Test Categories
- **Unit**: Single function/class
- **Integration**: Multiple components
- **E2E**: Full application flow

### Coverage Requirements
- Overall: >90%
- New code: 100%
- Critical paths: 100%

## Documentation Standards

### Docstrings (Required for Public APIs)
```python
async def process_batch(
    items: List[Dict],
    batch_size: int = 100
) -> List[Result]:
    """Process items in batches.
    
    Args:
        items: List of items to process
        batch_size: Items per batch (default: 100)
    
    Returns:
        List of processed results
        
    Raises:
        ValidationError: If items invalid
        
    Example:
        >>> results = await process_batch([{"id": 1}])
    """
```

### Comments (Explain WHY, not WHAT)
```python
# ❌ BAD: What
counter += 1  # Increment counter

# ✅ GOOD: Why  
delay = 2 ** attempt  # Exponential backoff for retry
```

### Internal Documentation
- Use `.md` files in `docs/internal/`
- Keep concise and actionable
- Update with code changes
- No public-facing content here

## Framework Patterns

### Context Pattern
```python
class Accounts(Context):
    """Business logic for user accounts."""
    
    # Queries (reads)
    async def get_user(self, user_id: str) -> Optional[User]:
        return await self.repo.find_by_id(user_id)
    
    # Commands (writes)
    async def create_user(self, data: CreateUserSchema) -> User:
        user = await self.repo.create(data)
        await self.emit("user.created", user)
        return user
```

### LiveView Pattern
```python
class DashboardLive(LiveView):
    async def mount(self, params, session, socket):
        socket.assign(user=session["user"], stats=await self.load_stats())
        return socket
    
    async def handle_event(self, event, payload, socket):
        if event == "refresh":
            socket.assign(stats=await self.load_stats())
        return socket
```

## Performance Guidelines

### Database
```python
# ✅ Batch operations
users = await User.filter(id__in=user_ids).all()

# ❌ N+1 queries
for user_id in user_ids:
    user = await User.get(id=user_id)
```

### Memory Management
```python
# ✅ Use generators for large datasets
def process_large_file():
    with open("large.txt") as f:
        for line in f:
            yield process_line(line)

# ❌ Load everything into memory
with open("large.txt") as f:
    lines = f.readlines()  # Loads entire file
```

### Caching
```python
@cache(ttl=300)  # 5 minutes
async def expensive_operation(param):
    return await complex_computation(param)
```

## Security Guidelines

### Input Validation
```python
# Always validate inputs
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    email: str
    age: int
    
    @validator('email')
    def validate_email(cls, v):
        if not v or "@" not in v:
            raise ValueError("Invalid email")
        return v
```

### SQL Injection Prevention
```python
# ✅ Parameterized queries
await db.fetch("SELECT * FROM users WHERE id = $1", user_id)

# ❌ String interpolation
query = f"SELECT * FROM users WHERE id = {user_id}"  # NEVER
```

### Secret Management
```python
# ✅ Environment variables
SECRET_KEY = os.environ["SECRET_KEY"]

# ❌ Hardcoded secrets
SECRET_KEY = "my-secret-key"  # NEVER
```

## Git Standards

### Commit Messages
```
type: Brief description

Longer explanation if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

### Branch Names
```
feat/add-live-view-support
fix/websocket-disconnect
docs/update-api-reference
```

### PR Requirements
- [ ] Tests pass
- [ ] Code formatted
- [ ] Type checks pass
- [ ] No debug code
- [ ] Documentation updated

## Tool Configuration

### VS Code Settings
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true
}
```

### Pre-commit Hooks
```yaml
repos:
  - repo: https://github.com/psf/black
    hooks: [black]
  - repo: https://github.com/pycqa/isort  
    hooks: [isort]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks: [ruff]
```

## Quick Reference

### Common Commands
```bash
# Development
zen server --reload
zen test --watch

# Code quality  
black . && isort . && mypy zenith/

# Database
zen db migrate
zen db console

# Performance
python benchmarks/load_test.py
```

### File Locations
- Source: `zenith/`
- Tests: `tests/`
- Internal docs: `docs/internal/`
- Config: `pyproject.toml`

---
*Internal standards - for core team only*