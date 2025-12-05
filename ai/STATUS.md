# Project Status

| Metric      | Value        | Updated    |
| ----------- | ------------ | ---------- |
| Version     | v0.0.14      | 2025-12-04 |
| Python      | 3.12-3.14    | 2025-11-24 |
| Tests       | 943 passing  | 2025-12-04 |
| Performance | 37,000 req/s | 2025-11-25 |

## What Worked

- Handler metadata caching (40% perf boost)
- `production=True` for middleware defaults
- Simple optimizations over complex (reverted radix router)
- Security fixes: all 7 critical issues fixed (S1-S5, C1, C8)
- Code review fixes: trusted proxy ASGI, dead code removal, constants

## What Didn't Work

- Custom radix router: maintenance burden for microsecond gains
- Multiple DI systems: Container + ServiceRegistry + Inject globals create confusion

## Active Work

**Next:** AI module (`zenith.ai` - optional extras)

- `stream_llm()` - SSE wrapper for LLM tokens
- `@tool` decorator - auto-generate function schemas
- MCP server support

→ Details: ai/research/2025-12-ai-strategy.md

## Blockers

None.

## Recent Decisions (2025-12-04)

- **AI as optional:** `pip install zenith[ai]` - framework-first, AI-second
- **Stay Python:** Bun acquisition is about distribution, not language shift
- **Protocol priorities:** OpenAI Tools (HIGH), MCP (HIGH), A2A (MEDIUM)
- **Primary integration:** Pydantic AI (same philosophy)
