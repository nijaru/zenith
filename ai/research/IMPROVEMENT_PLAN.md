# Zenith Improvement Plan & Architecture Analysis

**Date:** 2025-11-21
**Status:** Draft
**Focus:** Performance, Stability, and Modern Developer Experience (DX)

## Executive Summary
Zenith has a strong foundation with excellent DX ("One-line features", "Zero-config"), but it suffers from two critical issues that prevent it from matching State of the Art (SOTA) performance standards:
1.  **Critical Concurrency Bug:** The Service Dependency Injection system is not thread-safe for request context, leading to potential data leaks between users.
2.  **Routing Bottleneck:** The current O(n) list-based router significantly lags behind modern O(k) Radix Tree routers used in high-performance frameworks.

## 1. Architecture Analysis (Zenith vs. SOTA Standards)

| Feature | Zenith (Current) | Modern SOTA Standards | Impact |
|---------|------------------|-----------------------|--------|
| **Routing** | List-based (O(n)) 🔴 | Radix Tree / Trie (O(k)) 🟢 | Zenith performance degrades linearly with route count. |
| **Type Safety** | Runtime + Pydantic | End-to-End (RPC/Eden-like) 🟢 | Modern standards favor full-stack type generation. |
| **DI System** | Marker-based (Runtime) | Request-scoped / Functional | Current singleton pattern risks state leakage. |
| **Performance** | Good (Async) | Exceptional (Zero-copy/JIT) | Optimization needed to match top-tier benchmarks. |
| **DX** | "One-liners", OOP | Chaining, Functional | Current DX is strong but can be modernized. |

**Key Gaps:**
- **Routing Speed:** Zenith is mathematically slower at routing as the app grows.
- **Concurrency Safety:** The singleton service pattern implementation is currently unsafe for async contexts.

## 2. Critical Issues (Must Fix)

### 🚨 Service Context Race Condition
**Severity:** Critical (Security Vulnerability)
**Location:** `zenith/core/service.py` & `zenith/core/routing/dependency_resolver.py`
**Description:** Services are singletons, but `_inject_request(request)` sets the request object as an instance attribute (`self._request`). In concurrent scenarios, Request B will overwrite `self._request` while Request A is still processing, causing Request A to see Request B's data (user, headers, etc.).
**Fix:** Use `contextvars.ContextVar` to store the request context safely per-task.

## 3. Improvement Roadmap

### Phase 1: Stability & Security (Immediate)
- [ ] **Fix Race Condition:** Refactor `Service` to use `contextvars` for `request`, `user`, and `session` properties.
- [ ] **Fix Global Lock:** Optimize `DependencyResolver` to avoid global lock bottlenecks on every request.

### Phase 2: Core Performance (Next)
- [ ] **Radix Tree Router:** Replace the current list-based router with a specialized Radix/Trie implementation.
- [ ] **Middleware Optimization:** Review middleware chain overhead.

### Phase 3: Modern DX (Future)
- [ ] **Client Generator:** Create a script to generate typed TypeScript clients from Zenith models/routes.
- [ ] **Enhanced One-Liners:** Add `app.add_oauth()` and `app.add_job_queue()`.

### Phase 4: Python 3.14 Native (SOTA)
- [ ] **No-GIL Verification:** Audit dependencies (uvloop, asyncpg) for Python 3.14 free-threading compatibility.
- [ ] **JIT Benchmarking:** Measure performance gains with Python 3.13/3.14 JIT enabled.
- [ ] **Modern Typing:** Adopt PEP 695 `type Alias[T] = ...` syntax throughout the codebase.

## 4. Action Plan
1.  **Prove & Fix Bug:** Create a reproduction test case for the Service race condition, then implement the `contextvars` fix.
2.  **Benchmark:** Establish a baseline RPS with the current router.
3.  **Upgrade Router:** Implement Radix Tree routing.
4.  **Re-Benchmark:** Validate performance gains.
