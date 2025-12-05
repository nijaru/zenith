# Project Status

| Metric      | Value        | Updated    |
| ----------- | ------------ | ---------- |
| Version     | v0.0.13      | 2025-11-25 |
| Python      | 3.12-3.14    | 2025-11-24 |
| Tests       | 943 passing  | 2025-12-04 |
| Performance | 37,000 req/s | 2025-11-25 |

## What Worked

- Handler metadata caching (40% perf boost)
- `production=True` for middleware defaults
- Simple optimizations over complex (reverted radix router)

## What Didn't Work

- Custom radix router: maintenance burden for microsecond gains
- Multiple DI systems: Container + ServiceRegistry + Inject globals create confusion

## Active Work

**Phase 1:** Security fixes (5 vulnerabilities, 3 code issues)
**Phase 2:** AI module (`zenith.ai` - LLM streaming, tool calling)

→ Details: ai/research/2025-12-code-review.md

## Blockers

None. Strategic pivot decided: AI-optimized framework (see DECISIONS.md)

## Recent Learnings (2025-12-04)

- Package upgrades: redis 7.x, pytest 9.x, starlette 0.50 - all tests pass
- Security audit identified 5 HIGH vulnerabilities (CSRF, rate limiting, auth)
- Feature gaps vs FastAPI: OAuth2/OIDC, API versioning
- AI opportunity: LLM streaming, MCP support, tool calling patterns
