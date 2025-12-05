# Active Tasks

## Security (Critical - Block Release)

- [ ] S1: Fix CSRF cookie HttpOnly default (csrf.py:35,81)
- [ ] S2: Add trusted proxy validation to rate limiter (rate_limit.py:285-296)
- [ ] S3: Use generic auth error messages (auth.py:113-150)
- [ ] S4: Remove IP from CSRF token signature (csrf.py:140-155)
- [ ] S5: Fix infinite recursion in require_scopes (auth/dependencies.py:82)
- [ ] C1: Fix path/query type errors returning 500 (executor.py:267-283)
- [ ] C8: Fix file upload directory traversal (files.py:182-189)
- [ ] C11: Implement actual health checks (health.py:202-209)

## High Priority Features

- [ ] OAuth2/OIDC support (`app.add_oauth2()`)
- [ ] API versioning (`app.versioned_router()`)
- [ ] LLM streaming response helper (`zenith.ai.stream_llm_response`)
- [ ] Tool calling endpoint pattern (`ToolRouter`)

## Database Fixes

- [ ] C5: Fix session race condition (db/**init**.py:154-157)
- [ ] C6: Fix SQLModelRepository transaction bypass (sqlmodel.py:97-109)
- [ ] C4: Fix session.delete() silent failure (models.py:445)

## Documentation (High Priority)

- [ ] Rewrite tutorials to use modern patterns (Auth, Session, Inject, pwdlib) - ~8400 lines across 7 files

## Medium Priority Features

- [ ] Email/SMTP utilities (`zenith.email`)
- [ ] Webhook verification helpers
- [ ] File storage backends (S3, GCS)
- [ ] MCP server support (`zenith.ai.MCPServer`)
- [ ] Consolidate DI systems

## Backlog

- [ ] GraphQL improvements
- [ ] i18n support
- [ ] API key management
- [ ] A2A protocol support
- [ ] Vector search integration
- [ ] C12: Remove SSE dead code (sse.py:234-291)
- [ ] C7: Fix SSE WeakRef bug (sse.py:502-504)

## Minor Optimizations (Low Priority)

- [ ] Module-level imports in dependency_resolver.py
- [ ] Add `__slots__` to DependencyResolver/ResponseProcessor
