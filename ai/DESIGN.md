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

## Proposed: AI Module (zenith.ai)

| Component    | Purpose                               | Priority |
| ------------ | ------------------------------------- | -------- |
| stream_llm() | SSE wrapper for LLM responses         | HIGH     |
| ToolRouter   | Auto-generate OpenAI function schemas | HIGH     |
| MCPServer    | Model Context Protocol server         | MEDIUM   |
| A2AHandler   | Agent-to-agent protocol               | LOW      |

→ Details: ai/research/2025-12-code-review.md (Section 5)
