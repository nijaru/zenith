# Zenith (zenithweb)

Modern Python web framework for building APIs with minimal boilerplate, high performance, and intuitive developer experience.

## Project Structure

| Directory | Purpose |
|-----------|---------|
| zenith/ | Core framework source code |
| tests/ | Comprehensive test suite (unit, integration, performance) |
| docs/ | Documentation (tutorial, api, spec) |
| examples/ | Working application examples (00-23) |
| benchmarks/ | Performance benchmarks |
| ai/ | **AI session context** - workspace for tracking state across sessions |

### AI Context Organization

**Purpose:** AI maintains project context between sessions using ai/

**Session files** (read every session):
- ai/STATUS.md — Current state, metrics, blockers (read FIRST)
- ai/TODO.md — Active tasks only
- ai/DECISIONS.md — Architectural decisions
- ai/RESEARCH.md — Research index
- ai/PLAN.md — Strategic roadmap

**Reference files** (loaded on demand):
- ai/research/ — Detailed research
- ai/design/ — Design specs
- ai/decisions/ — Archived decisions
- ai/tmp/ — Temporary artifacts (gitignored)

**Token efficiency:** Session files = current work only. Details in subdirs.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 - 3.14 |
| Framework | Zenith (Self) |
| Package Manager | uv (preferred), pip |
| Build System | hatchling |
| Testing | pytest, coverage |
| Linting/Format | ruff |
| Database | Async SQLAlchemy, SQLModel, Alembic |

## Commands

```bash
# Build
uv build

# Test
uv run pytest
make test-cov  # With coverage

# Run (Dev)
zen dev
uvicorn main:app --reload

# Lint/Format
uv run ruff check . --fix
uv format

# Release
gh release create v{version} --title "v{version}: ..." --notes "..."
```

## Verification Steps

Commands to verify correctness (must pass):
- Build: `uv build` (zero errors)
- Tests: `uv run pytest` (all pass, currently 899 tests)
- Lint: `uv run ruff check .` (zero errors)
- Format: `uv format --check` (no changes needed)

## Code Standards

| Aspect | Standard |
|--------|----------|
| Naming | Snake_case for functions/vars, PascalCase for classes |
| Typing | 100% type hints required (Python 3.12+ style) |
| Imports | `from zenith import ...` (clean namespace) |
| Async | Async-first (all I/O must be async) |
| Models | Inherit from `ZenithModel` |
| Services | Inherit from `Service`, inject with `Inject()` |

## Examples

### Zero-Config App
```python
from zenith import Zenith
app = Zenith()
app.add_auth().add_admin().add_api()
```

### Database Model
```python
class User(ZenithModel, table=True):
    name: str
    active: bool = True

# Query
users = await User.where(active=True).limit(10).all()
```

### Service Pattern
```python
class UserService(Service):
    async def get(self, id: int) -> User:
        return await User.find_or_404(id)

@app.get("/users/{id}")
async def get_user(id: int, service: UserService = Inject()):
    return await service.get(id)
```

## Deprecated Patterns

| ❌ Don't Use | ✅ Use Instead | Why |
|-------------|---------------|-----|
| `Depends(get_db)` | `session: AsyncSession = Session` | `Session` is auto-managed by ZenithModel |
| `Depends(get_current_user)` | `user: User = Auth` | Cleaner syntax, better type inference |
| `bcrypt` | `argon2` | Superior security against GPU cracking |

## Claude Code Integration

| Feature | Details |
|---------|---------|
| Commands | None |
| MCP Servers | None |
| Hooks | None |

## Development Workflow

**Before implementing:**
1. Research best practices → ai/research/{topic}.md
2. Document decision → DECISIONS.md
3. Design if complex → ai/design/{component}.md
4. Implement → [src dir]
5. Update STATUS.md with learnings
6. Update docs/, examples/, tests/, CHANGELOG.md when modifying API

## Current Focus

See ai/STATUS.md for current state, ai/PLAN.md for roadmap.
