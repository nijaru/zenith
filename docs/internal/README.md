# Internal Documentation

*Organized development context for AI agents and human developers*

## File Structure

### 📋 Core Development Files
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Current status, priorities, code patterns for AI agents
- **[STRATEGY.md](STRATEGY.md)** - Strategic roadmap, positioning, technical direction
- **[PERFORMANCE.md](PERFORMANCE.md)** - Performance optimization techniques and benchmarks

### 📊 User Feedback
- **[feedback/djscout-migration.md](feedback/djscout-migration.md)** - DJScout project migration experience
- **[feedback/wealthscope-migration.md](feedback/wealthscope-migration.md)** - WealthScope project migration lessons

### 📦 Archive
- **[archive/](archive/)** - Historical development documents (reference only)

## Quick Navigation

### For AI Agents
1. **Start with DEVELOPMENT.md** - Current framework state and active priorities
2. **Check STRATEGY.md** - For long-term planning and roadmap context
3. **Reference PERFORMANCE.md** - For optimization work

### For Human Developers
1. **DEVELOPMENT.md** - Framework status, conventions, quick reference
2. **STRATEGY.md** - Product direction, competitive positioning
3. **feedback/** - Real-world usage experiences and migration patterns

## Key Information Summary

### Current Framework State (v0.3.1)
- ✅ 775/776 tests passing
- ✅ 9,600+ req/s performance
- ✅ Zero-config setup working
- ✅ ZenithModel with enhanced methods
- ✅ 85% boilerplate reduction achieved

### Active Priorities
1. Documentation consistency fixes (in progress)
2. Example organization and auto-generation
3. Performance optimization maintenance
4. CLI tooling development (next)

### Performance Targets
- Simple endpoints: >9,500 req/s
- JSON endpoints: >9,600 req/s
- With middleware: >6,500 req/s (70% retention)

## Development Workflow

### Testing
```bash
uv run pytest                           # Full test suite
python scripts/run_performance_tests.py # Performance benchmarks
```

### Example Verification
```bash
SECRET_KEY=test-secret-key-that-is-long-enough-for-testing uv run python examples/FILE.py
```

### Release Process
1. Update version: `./scripts/bump_version.sh` (interactive) or `./scripts/bump_version.sh patch`
2. Update `CHANGELOG.md` (manual)
3. Run full test suite: `uv run pytest`
4. Build and release: `uv build && twine upload dist/*`

---

*Documentation organized: September 2025*