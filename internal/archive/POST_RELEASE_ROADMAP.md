# 🗺️ Post v0.3.1 Release Roadmap

## ✅ v0.3.1 Release (Critical Fix)
**Status**: Ready for Release
- **Fix**: Async database event loop binding bug (WeakKeyDictionary per-loop engines)
- **Validated**: Production-tested in finterm/WealthScope project
- **Impact**: 99.9% performance improvement (50-100ms → 0.08ms)
- **API**: 100% backward compatible

---

## 🚀 v0.3.1 DX Improvements (Next Major Focus)

### Rails-Inspired Developer Experience
**Target**: Reduce boilerplate by 70%, zero-config database setup

#### 1. Auto-Configuration System
```python
# Current (verbose)
from zenith.db import Database
db = Database("postgresql://...")
app.configure_database(db)

# Target (zero-config)
app = Zenith()  # Reads DATABASE_URL automatically
```

#### 2. Enhanced Dependency Injection
```python
# Current
@app.get("/users")
async def get_users():
    async with db.session() as session:
        return await session.execute(select(User))

# Target (Rails ActiveRecord style)
@app.get("/users")
async def get_users(session = DB):  # Auto-injected
    return await session.execute(select(User))
```

#### 3. Smart Defaults & Convention Over Configuration
- Auto-detect database from `DATABASE_URL` environment variable
- Automatic migration discovery and running
- Smart connection pooling based on deployment environment
- Auto-configure middleware based on environment (dev/staging/prod)

---

## 🏗️ Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Create `feature/dx-improvements` branch
- [ ] Implement hidden WeakKeyDictionary pattern (cleaner internals)
- [ ] Add auto-configuration infrastructure
- [ ] Environment-based smart defaults

### Phase 2: Database Magic (Week 2)
- [ ] Global `DB` dependency injection shorthand
- [ ] Auto-discovery of `DATABASE_URL`
- [ ] Connection string validation and helpful errors
- [ ] Migration auto-discovery from `migrations/` folder

### Phase 3: Application Bootstrapping (Week 3)
- [ ] `app.setup_database()` one-liner
- [ ] Environment detection (dev/staging/production)
- [ ] Smart middleware configuration
- [ ] Health check auto-registration

### Phase 4: Testing & Polish (Week 4)
- [ ] Comprehensive test coverage for new features
- [ ] Documentation updates with new patterns
- [ ] Migration guide from v0.2.x
- [ ] Performance benchmarks (ensure no regressions)

---

## 📋 Immediate Post-Release Tasks

### 1. Release v0.3.1
```bash
# Version already bumped to 0.2.7
uv build
twine upload dist/zenith-web-0.2.7*
```

### 2. Update Dependencies
- [ ] Update finterm to use `zenith-web==0.2.7`
- [ ] Test in production environment
- [ ] Monitor for any issues

### 3. Communication
- [ ] Update CHANGELOG.md with v0.3.1 details
- [ ] GitHub release with critical fix details
- [ ] Update documentation if needed

### 4. Prepare for v0.3.1 Development
- [ ] Create feature branch: `git checkout -b feature/dx-improvements`
- [ ] Set up development environment for DX work
- [ ] Review Rails/Django patterns for inspiration

---

## 🎯 Success Metrics for v0.3.1

### Developer Experience Goals
- **Setup Time**: From 15+ lines to 3 lines for basic database app
- **Learning Curve**: New developers productive in <30 minutes
- **Boilerplate**: Reduce repetitive code by 70%
- **Error Messages**: Context-aware, actionable error messages

### Technical Goals
- **Performance**: Zero regression from convenience features
- **Backward Compatibility**: 100% compatibility with v0.2.x APIs
- **Test Coverage**: Maintain >95% coverage
- **Documentation**: Complete examples for all new patterns

---

## 🔮 Future Considerations (v0.3.1+)

### Advanced Features
- GraphQL auto-schema generation
- OpenAPI documentation generation
- Automatic API versioning
- Built-in caching strategies
- Enhanced WebSocket patterns

### Enterprise Features
- Multi-database support
- Distributed tracing integration
- Advanced monitoring and metrics
- Plugin architecture
- CLI scaffolding tools

---

*This roadmap is living document - update as priorities evolve*
*Created: 2025-09-15 | Status: Pre-v0.3.1 Release*