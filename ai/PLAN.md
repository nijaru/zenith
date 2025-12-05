# Roadmap

## Current: v0.0.14 (Released 2025-12-04)

Security hardening release. All P1 bugs closed.

## Phase 1: v0.1.0 - AI Module

**Goal:** Core AI features that differentiate Zenith from FastAPI.

| Feature           | Description                           | Bead       |
| ----------------- | ------------------------------------- | ---------- |
| `stream_llm()`    | SSE wrapper for LLM token streaming   | zenith-8gy |
| `@tool` decorator | Auto-generate OpenAI function schemas | zenith-8gy |
| `ToolRouter`      | HTTP endpoints with schema generation | zenith-8gy |

**Dependencies:**

- Optional: `zenith[ai]` → openai, anthropic, httpx-sse

**Exit Criteria:**

- [ ] Working stream_llm() with OpenAI/Anthropic
- [ ] @tool decorator generates valid OpenAI schemas
- [ ] Example app demonstrating AI features
- [ ] Tests passing, docs updated

## Phase 2: v0.2.0 - Protocols & Auth

**Goal:** MCP server support and OAuth2/OIDC.

| Feature        | Description                         | Bead       |
| -------------- | ----------------------------------- | ---------- |
| MCPServer      | Model Context Protocol server mixin | TBD        |
| MCP transports | Stdio + HTTP/SSE                    | TBD        |
| OAuth2/OIDC    | Standard auth providers             | zenith-z02 |

**Dependencies:**

- Optional: `zenith[mcp]` → mcp SDK
- Core: OAuth2 providers

**Exit Criteria:**

- [ ] Zenith routes exposed as MCP tools
- [ ] OAuth2 flows working (Google, GitHub)
- [ ] Pydantic AI integration example

## Phase 3: v1.0.0 - Production Ready

**Goal:** Stable API, comprehensive docs, proven in production.

| Task             | Description                             |
| ---------------- | --------------------------------------- |
| DI consolidation | Unify Container/ServiceRegistry/Inject  |
| Monitoring       | Complete Prometheus/OpenTelemetry       |
| A2A protocol     | Google's agent-to-agent (if stabilized) |
| Security audit   | OWASP session review                    |

**Exit Criteria:**

- [ ] API stability commitment (semantic versioning)
- [ ] Full documentation site
- [ ] Performance benchmarks published
- [ ] At least one production deployment

## Future (Post-1.0)

- A2A protocol support
- LangGraph HTTP state endpoints
- CrewAI deployment target
- Admin dashboard improvements

---

> **Task tracking:** Use `bd list` / `bd ready` for individual work items.
> **Decisions:** See DECISIONS.md for architectural choices.
> **Research:** See ai/research/ for background analysis.
