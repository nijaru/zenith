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

### Current Framework State (v0.0.10)
- ✅ 900 tests passing (Python 3.12, 3.13)
- ✅ ~10,000 req/s JSON endpoints, ~7,000 req/s with middleware
- ✅ Zero-config setup working
- ✅ Service-based architecture with DI
- ✅ Production-ready middleware stack

### Active Priorities
1. API stabilization for v1.0
2. Performance optimization maintenance
3. Documentation enhancement
4. Python 3.14 ecosystem compatibility (SQLAlchemy segfault pending upstream fix)

### Performance Achievements
- Simple endpoints: ~8,000 req/s (7,743 req/s measured)
- JSON endpoints: ~10,000 req/s (9,917 req/s measured)
- With middleware: ~7,000 req/s (71% retention, 29% overhead)

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

*Documentation updated: October 2025 (v0.0.10)*