# Zenith Framework Roadmap

## 🎯 Vision
Build the best Python API framework for complex business logic, with clean architecture patterns that will seamlessly transition to Mojo for 10x performance gains.

## 📋 Development Phases

### Phase 1: Foundation (Current - Next 30 days)
**Goal**: Make Zenith usable for basic API development

#### Priority 1: Database Integration (ZEN-2) ✅ **COMPLETED**
- [x] SQLAlchemy 2.0 async integration
- [x] Database session management in contexts
- [x] Transaction support
- [x] Basic migrations with Alembic
- [x] Replace all mock data with real database
- [x] Password hashing utilities
- [x] Database registered in Application DI container

#### Priority 2: Routing & Middleware (ZEN-3)
- [ ] Fix routing edge cases
- [ ] CORS middleware
- [ ] Rate limiting middleware
- [ ] Exception handling
- [ ] Request/response logging

#### Priority 3: Authentication (ZEN-6)
- [ ] JWT token generation/validation
- [ ] Login/logout endpoints
- [ ] Password hashing
- [ ] Auth() dependency that works
- [ ] Basic permission checking

### Phase 2: Developer Experience (Days 31-60)
**Goal**: Make Zenith pleasant to use

#### Testing Framework (ZEN-7)
- [ ] TestClient for API testing
- [ ] TestContext for isolated testing
- [ ] Database rollback for tests
- [ ] Fixture system
- [ ] Coverage reporting

#### Documentation (ZEN-8)
- [ ] OpenAPI/Swagger generation
- [ ] Interactive API documentation
- [ ] Code examples
- [ ] Migration guide from FastAPI

### Phase 3: Production Ready (Days 61-90)
**Goal**: Make Zenith reliable for production

#### Performance (ZEN-9)
- [ ] Benchmarks vs FastAPI
- [ ] Performance optimization
- [ ] Memory profiling
- [ ] Database query optimization

#### Deployment (ZEN-10)
- [ ] Docker support
- [ ] Production configuration
- [ ] Health checks
- [ ] Monitoring integration
- [ ] Deployment guides

### Phase 4: Advanced Features (3-6 months)
**Goal**: Differentiate from FastAPI

- [ ] Background jobs
- [ ] WebSocket support (data streaming, not UI)
- [ ] GraphQL integration
- [ ] Advanced context patterns
- [ ] Plugin system

### Phase 5: Mojo Preparation (6-12 months)
**Goal**: Prepare for performance revolution

- [ ] Identify hot paths for Mojo optimization
- [ ] Create Mojo compatibility layer
- [ ] Benchmark Mojo vs Python implementation
- [ ] Python bindings for Mojo components

## 🗄️ Database Strategy
- **Current**: SQLAlchemy 2.0 with async support
- **Why**: Most mature, battle-tested, works with any database
- **Future**: Mojo direct SQL for 10-50x performance gains
- **Not using**: EdgeDB (cool but <1% adoption), custom ORM

## ❌ Explicitly Not Building
- **LiveView/Server-side UI**: Wrong runtime for Python
- **Phoenix Channels**: Overengineered for Python
- **Supervisor Trees**: Unnecessary complexity
- **Custom ORM**: Using SQLAlchemy instead
- **Message Queue**: Using existing solutions

## 📊 Success Metrics

### 30 Days
- [x] Can build a real TODO API with database
- [ ] Authentication actually works
- [ ] 10+ example applications
- [ ] Core features documented

### 90 Days
- [ ] 100+ GitHub stars
- [ ] 5+ projects using Zenith
- [ ] Performance on par with FastAPI
- [ ] Production deployment guide

### 1 Year
- [ ] 1000+ GitHub stars
- [ ] 50+ production users
- [ ] Mojo compatibility proven
- [ ] Established alternative to FastAPI

## 🚀 Getting Started

If you want to help or try Zenith:

1. **Current focus**: Routing & Middleware (ZEN-3)
2. **Most helpful**: Try building something and report issues
3. **Coming soon**: Authentication system and testing framework

## 📝 Notes

- We're being realistic about Python's strengths and limitations
- API-first approach aligns with modern architecture patterns
- Clean code architecture will make Mojo transition seamless
- Better to ship something useful than dream of perfection

---

Track progress on our [Linear board](https://linear.app/nijaru7/team/ZEN/active)