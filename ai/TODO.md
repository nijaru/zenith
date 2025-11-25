# Active Tasks

## Backlog
- [ ] WebSocket middleware support (auth, logging)
- [ ] GraphQL improvements
- [ ] Brotli compression middleware
- [ ] httpx AsyncClient pooling in lifespan

## Already Implemented
- [x] orjson responses (`OptimizedJSONResponse` in `zenith/web/responses.py`)
- [x] structlog (`zenith/logging.py` - get_logger, LoggingMiddleware, etc.)
- [x] OpenTelemetry (`add_tracing()` in `zenith/app.py`)
- [x] Database query tracing (`zenith/db/tracing.py` - QueryTracer, slow query logging)
- [x] Rate limiting (custom impl is comprehensive, slowapi not needed)
- [x] msgspec (in dependencies)
- [x] uvloop (in dependencies)

## Recently Completed
- [x] Database query tracing with slow query logging
- [x] v0.0.12 published to PyPI
- [x] CI fixed (Python 3.14 greenlet segfault workaround)
