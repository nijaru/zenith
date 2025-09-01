# Zenith Tutorial

> Build a complete REST API with authentication, file uploads, and database integration

In this tutorial, we'll build a **Blog API** that demonstrates all of Zenith's key features:

- User authentication with JWT tokens
- Database integration with SQLAlchemy  
- File uploads for blog images
- Context-driven architecture
- Comprehensive testing

## What We're Building

A blog API with these endpoints:

```
POST   /auth/register     - User registration
POST   /auth/login        - User login  
GET    /auth/me          - Get current user

GET    /posts            - List blog posts
POST   /posts            - Create blog post  
GET    /posts/{id}       - Get specific post
PUT    /posts/{id}       - Update post
DELETE /posts/{id}       - Delete post

POST   /posts/{id}/image - Upload post image
GET    /uploads/{file}   - Serve uploaded files

GET    /health           - Health check
```

## Prerequisites

- Python 3.11+
- Basic knowledge of async/await
- Familiarity with REST APIs

## Tutorial Steps

### [Step 1: Project Setup](01-setup.md)
Set up your project structure, dependencies, and basic configuration.

### [Step 2: Database Models](02-database.md) 
Define User and Post models with SQLAlchemy relationships.

### [Step 3: Authentication Context](03-authentication.md)
Build user registration, login, and JWT token handling.

### [Step 4: Posts Context](04-posts-context.md)
Create business logic for managing blog posts.

### [Step 5: HTTP Routes](05-routes.md)
Wire up HTTP endpoints with type-safe routing.

### [Step 6: File Uploads](06-file-uploads.md)
Add image upload functionality with validation.

### [Step 7: Testing](07-testing.md)
Write comprehensive tests for all functionality.

### [Step 8: Production Deployment](08-deployment.md)
Deploy your API to production with Docker.

---

**Let's get started!** → [Step 1: Project Setup](01-setup.md)