# Active Tasks

## High Priority
- [ ] Add request tracing support (OpenTelemetry)
- [ ] orjson responses (2-3x faster JSON, ~10 lines)
- [ ] structlog for structured logging

## Moderate
- [ ] Consider replacing custom rate limiting with slowapi
- [ ] Add database query tracing / slow-query logging

## Backlog
- [ ] WebSocket middleware support (auth, logging)
- [ ] GraphQL improvements
- [ ] Brotli compression middleware
- [ ] httpx AsyncClient pooling in lifespan
- [ ] msgspec for high-throughput validation (alternative to Pydantic)
- [ ] uvloop event loop (Linux, 2-4x faster)

## Recently Completed
- [x] v0.0.12 published to PyPI
- [x] CI fixed (Python 3.14 greenlet segfault workaround)
- [x] Docs package-lock.json regenerated
- [x] Docs updated to match v0.0.12 API (Argon2, Session imports)
- [x] Repository cleanup (34K lines removed)
- [x] Examples cleaned (emojis removed, version updated)
- [x] SQLAlchemy GC warnings fixed in tests
- [x] v0.0.12 released to GitHub
