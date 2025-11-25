# Active Tasks

## Backlog
- [ ] GraphQL improvements

## Already Implemented
- [x] orjson responses (`OptimizedJSONResponse` in `zenith/web/responses.py`)
- [x] structlog (`zenith/logging.py` - get_logger, LoggingMiddleware, etc.)
- [x] OpenTelemetry (`add_tracing()` in `zenith/app.py`)
- [x] Database query tracing (`zenith/db/tracing.py` - QueryTracer, slow query logging)
- [x] Rate limiting (custom impl is comprehensive, slowapi not needed)
- [x] httpx AsyncClient pooling (`zenith/http/client.py`)
- [x] Brotli compression (`zenith/middleware/compression.py`)
- [x] WebSocket auth & logging middleware (`zenith/middleware/websocket.py`)
- [x] msgspec (in dependencies)
- [x] uvloop (in dependencies)

## Recently Completed
- [x] WebSocket middleware (auth, logging)
- [x] Brotli compression support
- [x] httpx AsyncClient pooling
- [x] Database query tracing
- [x] v0.0.12 published to PyPI
