# Zenith Framework Overview

## Vision

Build the most productive Python web framework by combining:
- **Phoenix's real-time capabilities** (LiveView, Channels)  
- **Rails' developer experience** (Conventions, generators)
- **Python's ecosystem** (Libraries, tooling, community)

## Core Principles

1. **Real-time First**: LiveView and Channels built into core
2. **Context-Driven**: Business logic organized by domain, not technical layers
3. **Type Safety**: Full type hints for better DX and fewer bugs
4. **Async Throughout**: Built on asyncio for high concurrency
5. **Progressive Enhancement**: Start simple, scale to complex

## High-Level Architecture

```
Client (Browser)
    ↓ HTTP/WebSocket
Web Layer (Controllers, LiveViews, Channels)
    ↓ Function calls
Core Layer (Contexts, Router, PubSub)
    ↓ Async queries
Data Layer (PostgreSQL, Redis)
```

## Key Components

### Application Kernel
- Supervisor tree for fault tolerance
- Dependency injection container
- Configuration management
- Lifecycle hooks

### Context System  
- Domain-driven business logic organization
- Public APIs for other layers
- Event emission for decoupling
- Built-in testing helpers

### LiveView Engine
- Server-rendered real-time UI
- Automatic DOM diffing and patching  
- Event handling without JavaScript
- Component composition

### Channels System
- WebSocket-based real-time communication
- Topic-based message routing
- Presence tracking
- Fault-tolerant connections

### Router & Pipeline
- HTTP request routing
- Composable middleware pipelines
- Parameter extraction
- Response handling

## Developer Experience

### CLI Tool (`zen`)
```bash
zen new myapp                    # Create new project
zen generate context Accounts    # Generate business logic
zen generate live Dashboard      # Generate real-time component  
zen server --reload             # Development server
zen test                        # Run test suite
```

### Simple Getting Started
```python
from zenith import Application, Context, LiveView, get

# Business logic
class Blog(Context):
    async def get_posts(self):
        return await Post.all()

# HTTP endpoint  
@get("/api/posts")
async def list_posts():
    return await Blog().get_posts()

# Real-time component
class PostsLive(LiveView):
    async def mount(self, params, session, socket):
        socket.assign(posts=await Blog().get_posts())
        return socket

app = Application()
app.start()
```

## Target Performance

- **HTTP Requests**: 50,000+ req/s
- **WebSocket Connections**: 10,000+ concurrent  
- **Startup Time**: < 1 second
- **Memory Usage**: < 100MB base

## Development Roadmap

### v0.1.0 - Foundation (Q1 2025)
Core framework with basic HTTP handling

### v0.2.0 - Real-Time (Q1 2025)  
LiveView and Channels implementation

### v0.3.0 - Database (Q2 2025)
ORM and migration system

### v1.0.0 - Production Ready (Q4 2025)
Stable API, comprehensive features

## Competitive Positioning

| Framework | Real-Time | DX | Performance | Ecosystem |
|-----------|-----------|----|-----------  |-----------|
| **Zenith** | ✅ Built-in | ✅ Excellent | ✅ High | ✅ Python |
| Django | ❌ Add-on | ✅ Good | ⚠️ Medium | ✅ Huge |  
| FastAPI | ❌ Manual | ⚠️ Good | ✅ High | ⚠️ Growing |
| Flask | ❌ Extensions | ⚠️ Basic | ⚠️ Medium | ✅ Large |
| Phoenix | ✅ Excellent | ✅ Excellent | ✅ High | ⚠️ Elixir |

## Success Metrics

### Technical Goals
- Framework performance benchmarks
- Test coverage >90%
- Documentation completeness
- API stability

### Community Goals  
- 5,000+ GitHub stars by v1.0
- 100+ production deployments
- 50+ active contributors
- Thriving plugin ecosystem

### Business Goals
- Featured at major Python conferences
- Adoption by recognizable companies
- Positive developer surveys
- Sustainable project financing

---
*High-level overview of Zenith Framework vision and goals*