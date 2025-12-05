# Project Status

| Metric      | Value        | Updated    |
| ----------- | ------------ | ---------- |
| Version     | v0.0.14      | 2025-12-04 |
| Python      | 3.12-3.14    | 2025-11-24 |
| Tests       | 943 passing  | 2025-12-04 |
| Performance | 37,000 req/s | 2025-11-25 |

## Current Phase

**Phase 1: v0.1.0 - AI Module** (see PLAN.md)

Bead: `zenith-8gy`

| Feature           | Status      |
| ----------------- | ----------- |
| `stream_llm()`    | Not started |
| `@tool` decorator | Not started |
| `ToolRouter`      | Not started |

## What Worked

- Handler metadata caching (40% perf boost)
- `production=True` for middleware defaults
- Simple optimizations over complex (reverted radix router)
- Security fixes: all 7 critical issues fixed (v0.0.14)
- Code review fixes: trusted proxy ASGI, constants extraction

## What Didn't Work

- Custom radix router: maintenance burden for microsecond gains
- Multiple DI systems: Container + ServiceRegistry + Inject globals create confusion

## Blockers

None.

## Key Decisions (2025-12-04)

- **AI as optional:** `pip install zenith[ai]` - framework-first, AI-second
- **Stay Python:** Bun acquisition is about distribution, not language shift
- **Protocol priorities:** OpenAI Tools (HIGH), MCP (HIGH), A2A (MEDIUM)
- **Primary integration:** Pydantic AI (same philosophy)

→ Full roadmap: ai/PLAN.md
→ Research: ai/research/2025-12-ai-strategy.md
