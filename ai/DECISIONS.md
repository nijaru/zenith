# Architecture Decisions

## 2025-12-04 Strategic Pivot: AI-Agent Optimized Framework

**Context:**
Code review revealed Zenith has feature parity with FastAPI but no clear differentiator. AI agent frameworks (LangChain, CrewAI, OpenAI Agents SDK) are exploding in 2025. No Python web framework is purpose-built for AI agents.

**Decision:**
Add optional AI features to Zenith while keeping it a general-purpose FastAPI alternative.

**Key Principle:** Zenith is a web framework first. AI features are optional extras via `pip install zenith[ai]`.

**Key Features to Add:**

| Feature        | Purpose                                              | Priority |
| -------------- | ---------------------------------------------------- | -------- |
| `stream_llm()` | SSE wrapper for LLM token streaming                  | HIGH     |
| `ToolRouter`   | Auto-generate OpenAI function schemas from endpoints | HIGH     |
| `MCPServer`    | Model Context Protocol server for Claude             | MEDIUM   |
| A2A Protocol   | Google's agent-to-agent communication                | LOW      |

**Rationale:**

- Zenith already has SSE streaming (just needs LLM helper)
- Async-first architecture aligns with agent patterns
- High performance (37k req/s) benefits multi-call agents
- No competitor owns this space

**Tradeoffs:**

| Pro                          | Con                       |
| ---------------------------- | ------------------------- |
| Clear market position        | New features to maintain  |
| Leverages existing SSE/async | Fast-moving standards     |
| Growing AI market            | Must stay general-purpose |

**Consequences:**

- Add `zenith/ai/` module with lazy imports
- Optional deps: `zenith[ai]`, `zenith[mcp]`
- Core framework remains lightweight (no AI deps by default)
- Marketing: "Modern Python web framework" first, AI features second

---

## 2025-11-24 Library vs Custom Implementation Strategy

**Context:**
Architecture review identified multiple areas where custom implementations exist. Need clear policy on when to use libraries vs custom code.

**Decision:**
Use libraries for: routing, OpenAPI generation, rate limiting, structured logging.
Keep custom for: service layer, middleware wrappers, response optimization.

**Libraries to Use (not reinvent):**

| Component          | Use Library                    | Not Custom           |
| ------------------ | ------------------------------ | -------------------- |
| Routing            | Starlette Router               | RadixTree (deleted)  |
| OpenAPI            | Consider fastapi.openapi.utils | Current custom impl  |
| Rate limiting      | Consider slowapi/limits        | Current custom impl  |
| DI Container       | Consider dependency-injector   | Current multi-system |
| Structured logging | structlog (already dep)        | Raw logging calls    |

**Keep Custom (justified):**

| Component             | Reason                                      |
| --------------------- | ------------------------------------------- |
| Service base class    | Specific DI pattern for business logic      |
| Response optimization | orjson wrapper, specific caching needs      |
| Middleware wrappers   | Thin wrappers with Zenith-specific defaults |
| Session management    | Dirty tracking, auto-persistence features   |

**Rationale:**

- 60+ Starlette imports already - we're a layer on top, not a replacement
- Custom routing (O(k) RadixTree) adds maintenance burden for microsecond gains
- Focus effort on differentiating features (DX, service layer, zero-config)

**Consequences:**

- Deleted `zenith/core/routing/radix.py` and `radix_router.py`
- Future: consolidate DI systems, adopt structlog throughout

---

## 2025-11-24 Routing Engine

**Context:**
Implemented custom RadixTree router for O(k) path matching vs Starlette's O(n).

**Decision:**
Reverted to Starlette Router. Deleted custom implementation.

**Rationale:**

1. Starlette's compiled regex is already fast (microseconds)
2. O(k) vs O(n) only matters at 100s+ routes
3. Still wrapped Starlette catch-all anyway (worst of both worlds)
4. Maintenance burden not justified for marginal gains
5. Deep Starlette dependency throughout (60+ imports)

**Consequences:**

- Simpler codebase, less custom code
- Starlette handles edge cases and security
- Future: benchmark if needed at scale, reconsider then

---

## 2025-11-24 Known Architecture Issues (To Address)

**Critical (Before 1.0):**

1. **Multiple DI systems**: Container + ServiceRegistry + Inject() globals - consolidate
2. **OpenAPI generation**: Custom impl untested against spec - consider fastapi approach
3. **Logging**: Raw logging scattered - adopt structlog comprehensively

**Moderate (Before 2.0):**

1. Session security audit against OWASP
2. Request tracing (OpenTelemetry by default)
3. Middleware ordering documentation

---

## 2025-10-01 Password Hashing

**Context:**
Need secure password hashing defaults.

**Decision:**
Use Argon2 instead of bcrypt.

**Rationale:**
Argon2 is the modern standard and resistant to GPU/ASIC attacks.

**Consequences:**
Requires `pwdlib[argon2]`.
