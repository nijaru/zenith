# System Design

## Overview

Modern Python web framework for building APIs with minimal boilerplate, high performance, async-first architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Zenith Application                    │
├─────────────────────────────────────────────────────────┤
│  Mixins: Routing | Services | Docs | Middleware | HTTP  │
├─────────────────────────────────────────────────────────┤
│                   Middleware Stack                       │
│  Auth | CORS | CSRF | RateLimit | Security | Logging    │
├─────────────────────────────────────────────────────────┤
│                    Core Router                           │
│  Executor → DependencyResolver → ResponseProcessor       │
├─────────────────────────────────────────────────────────┤
│                   Service Layer                          │
│  DIContainer | ServiceRegistry | EventBus                │
├─────────────────────────────────────────────────────────┤
│                   Data Layer                             │
│  ZenithModel | AsyncSession | SQLModel | Migrations      │
├─────────────────────────────────────────────────────────┤
│                    Starlette                             │
└─────────────────────────────────────────────────────────┘
```

## Components

| Component        | Purpose                           | Status                       |
| ---------------- | --------------------------------- | ---------------------------- |
| Core Application | ASGI lifecycle, mixin composition | Stable                       |
| Routing          | Route registration, execution, DI | Stable                       |
| Middleware       | Auth, CORS, CSRF, rate limiting   | Needs security fixes         |
| Services         | DI container, service base class  | Stable (needs consolidation) |
| Database         | Async SQLAlchemy, ZenithModel ORM | Stable                       |
| Sessions         | Cookie/Redis session management   | Stable                       |
| WebSockets       | Connection manager, broadcast     | Stable                       |
| SSE              | Streaming with backpressure       | Has bugs (see TODO)          |
| Jobs             | Background tasks, Redis queue     | Stable                       |
| Monitoring       | Health checks, Prometheus metrics | Incomplete                   |
| OpenAPI          | Auto-generation, Swagger/ReDoc    | Stable                       |

## Key Design Decisions

→ See DECISIONS.md

## Data Flow

1. Request → ASGI → Middleware stack
2. Router matches path → Executor runs handler
3. DependencyResolver injects: Session, Auth, Inject(), custom
4. Handler returns → ResponseProcessor formats JSON/HTML
5. Response → Middleware stack (reverse) → Client

## AI Module Architecture (zenith.ai) - OPTIONAL

**Philosophy:** Zenith is a general-purpose web framework first. AI features are optional extras.

### Installation

```bash
pip install zenith          # Core framework (no AI deps)
pip install zenith[ai]      # + openai, anthropic, httpx-sse
pip install zenith[mcp]     # + mcp SDK
pip install zenith[all]     # Everything
```

### Module Structure

```
zenith/ai/
├── __init__.py          # Lazy imports, graceful failure if deps missing
├── streaming.py         # stream_llm(), StreamingLLMResponse
├── tools.py             # @tool decorator, ToolRouter, schema generation
├── mcp/
│   ├── server.py        # MCPServer mixin
│   └── transport.py     # Stdio + HTTP/SSE transports
└── _deps.py             # Dependency checks, helpful error messages
```

### Import Pattern

```python
# Core framework - always works
from zenith import Zenith, get, post, Session, Auth

# AI features - optional, fails gracefully
try:
    from zenith.ai import stream_llm, tool
except ImportError:
    # pip install zenith[ai] for AI features
    pass
```

### Feature Prioritization

| Phase | Feature           | Purpose                                    | Status  |
| ----- | ----------------- | ------------------------------------------ | ------- |
| 1     | `stream_llm()`    | SSE wrapper for LLM token streaming        | Planned |
| 1     | `@tool` decorator | Auto-generate OpenAI function schemas      | Planned |
| 1     | `ToolRouter`      | HTTP endpoints with schema generation      | Planned |
| 2     | `MCPServer`       | Model Context Protocol server (stdio+HTTP) | Planned |
| 3     | Pydantic AI       | Native integration examples                | Planned |
| 4     | `A2AHandler`      | Google's agent-to-agent protocol           | Future  |

### Agent Framework Support

| Framework         | Integration Approach                            |
| ----------------- | ----------------------------------------------- |
| Pydantic AI       | Primary target - same Pydantic philosophy       |
| OpenAI Agents SDK | Export tool schemas in their format             |
| LangGraph         | HTTP endpoints for agent state                  |
| CrewAI            | Deployment target (Zenith serves CrewAI agents) |

### Protocol Support

| Protocol     | Status                                        |
| ------------ | --------------------------------------------- |
| OpenAI Tools | HIGH - de facto standard for function calling |
| MCP          | HIGH - adopted by OpenAI, Google, Microsoft   |
| A2A          | MEDIUM - newer but 50+ enterprise partners    |

→ Details: ai/research/2025-12-ai-strategy.md
