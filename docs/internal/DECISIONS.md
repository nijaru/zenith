# Architectural Decision Records

## ADR Format
- **Date**: When decided
- **Status**: Accepted | Superseded | Deprecated
- **Context**: Why we needed to decide
- **Decision**: What we decided
- **Consequences**: Results of the decision

---

## ADR-001: Framework Name - Zenith
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Needed unique name without tool collisions  
**Decision**: "Zenith" framework with `zen` CLI command  
**Consequences**: Clean namespace, short memorable command, peak performance metaphor

---

## ADR-002: Phoenix-Inspired Architecture  
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Python lacks real-time web framework with great DX  
**Decision**: Adopt Phoenix contexts + LiveView patterns  
**Consequences**: Clear domain boundaries, server-rendered real-time, event-driven by default

---

## ADR-003: Context-Driven Organization
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Need clear business logic boundaries  
**Decision**: Contexts as primary organizational pattern  
**Consequences**: Isolated domains, clear APIs, easier testing, more initial boilerplate

---

## ADR-004: Async-First Implementation
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Modern apps need high concurrency  
**Decision**: Build on asyncio with async/await throughout  
**Consequences**: Better I/O performance, natural WebSocket fit, requires Python 3.11+

---

## ADR-005: Type Hints Required
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Large codebases need static typing  
**Decision**: Require type hints for all public APIs  
**Consequences**: Better IDE support, early error detection, slight verbosity

---

## ADR-006: LiveView for Real-Time UI
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: JavaScript-heavy real-time is complex  
**Decision**: Phoenix LiveView pattern for server-rendered real-time  
**Consequences**: Minimal JS needed, server holds state, higher server resources

---

## ADR-007: PostgreSQL Primary Database  
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Need robust async database with advanced features  
**Decision**: PostgreSQL as primary supported database  
**Consequences**: Can use PG-specific features, LISTEN/NOTIFY, limits MySQL adoption initially

---

## ADR-008: Redis for PubSub/Caching
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Need distributed messaging and fast caching  
**Decision**: Redis for PubSub, caching, presence  
**Consequences**: Proven real-time solution, additional infrastructure dependency

---

## ADR-009: Documentation Simplification
**Date**: 2025-09-01  
**Status**: Accepted  
**Context**: Over-engineered docs for zero-code project  
**Decision**: Focus on internal docs until public release  
**Consequences**: Faster development, less maintenance, cleaner structure

---

## Decisions Pending

### Database Layer Design
- **Question**: ORM vs Query Builder vs Raw SQL
- **Options**: Custom ORM, SQLAlchemy, Databases + Raw
- **Decision**: TBD after spike

### JavaScript Client Architecture  
- **Question**: Vanilla JS vs Framework
- **Options**: Vanilla, Alpine.js, Stimulus
- **Decision**: TBD based on LiveView needs

### Plugin System Design
- **Question**: How to make framework extensible
- **Options**: Hooks, Middleware, Event system
- **Decision**: TBD after core stabilizes

### Admin Interface Approach
- **Question**: Built-in vs Separate package
- **Options**: Core feature, Optional plugin, Separate project
- **Decision**: TBD based on user feedback

### Performance Optimization Strategy
- **Question**: Python vs Native extensions
- **Options**: Pure Python, Rust extensions, Mojo integration
- **Decision**: TBD after benchmarking

---

## Decision Process

### For Reversible Decisions (Type 2)
1. Individual contributor decides
2. Document in PR description  
3. Can be changed easily later

### For Irreversible Decisions (Type 1)
1. Create discussion issue
2. Research alternatives
3. Team consensus required
4. Document in this file

### Decision Authority
- **Technical**: Core team consensus
- **Product**: Project lead with input
- **Process**: Team discussion and vote

---
*Architectural decisions for Zenith Framework*