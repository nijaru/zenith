# Active Tasks

## High Priority
- [ ] Consider replacing custom rate limiting with slowapi
- [ ] Database query tracing / slow-query logging

## Backlog
- [ ] WebSocket middleware support (auth, logging)
- [ ] GraphQL improvements
- [ ] Brotli compression middleware
- [ ] httpx AsyncClient pooling in lifespan

## Already Implemented (in v0.0.12)
- [x] orjson responses (`OptimizedJSONResponse` in `zenith/web/responses.py`)
- [x] structlog (`zenith/logging.py` - get_logger, LoggingMiddleware, etc.)
- [x] OpenTelemetry (`add_tracing()` in `zenith/app.py`)
- [x] msgspec (in dependencies)
- [x] uvloop (in dependencies)

## Recently Completed
- [x] v0.0.12 published to PyPI
- [x] CI fixed (Python 3.14 greenlet segfault workaround)
