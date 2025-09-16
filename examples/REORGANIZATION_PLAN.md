# Examples Reorganization Plan

## Current Issues
- Duplicate numbers (multiple 16-, 17-, 18-, 19- examples)
- Poor learning progression
- Framework name-dropping throughout
- Confusing naming conventions

## Proposed Structure

### Fundamentals (00-09)
00. hello-world.py - Minimal example
01. basic-routing.py - Routes and HTTP methods
02. request-response.py - Request data and responses
03. dependency-injection.py - Session, Auth shortcuts
04. database-models.py - ZenithModel basics
05. file-upload.py - File handling
06. middleware.py - CORS, security, rate limiting
07. background-tasks.py - Simple async tasks
08. websockets.py - Real-time communication
09. testing.py - Testing patterns

### Intermediate (10-19)
10. authentication.py - JWT auth system
11. advanced-database.py - Complex queries, relationships
12. job-queue.py - Persistent job processing
13. api-documentation.py - OpenAPI, validation
14. caching.py - Redis integration
15. error-handling.py - Custom exceptions
16. performance.py - Optimization techniques
17. deployment.py - Production setup
18. monitoring.py - Logging, metrics
19. advanced-features.py - Full framework showcase

### Real-World Applications (20-29)
20. blog-api.py - Complete CRUD API
21. e-commerce-api.py - Business logic example
22. chat-application.py - Real-time features
23. file-sharing.py - Upload/download service
24. user-management.py - Auth + admin features
25. microservice.py - Service communication
26. full-stack-spa.py - Frontend integration

## Action Items
1. Remove framework name-dropping from ALL examples
2. Consolidate duplicate examples
3. Renumber following logical progression
4. Update documentation references
5. Test all examples work correctly