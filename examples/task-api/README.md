# TaskFlow API - Complete Zenith Tutorial Example

This is the complete implementation of the TaskFlow API built throughout the Zenith tutorial series. It demonstrates production-ready patterns for building APIs with Zenith.

## Features

- User registration and authentication
- Project management with ownership
- Task creation and assignment
- Complete CRUD operations
- Pagination and filtering
- Soft deletes and archiving
- Transaction handling
- Comprehensive error handling

## Setup

1. Install dependencies:
```bash
uv add zenithweb sqlmodel alembic python-jose[cryptography] passlib[bcrypt]
# or
pip install zenithweb sqlmodel alembic python-jose[cryptography] passlib[bcrypt]
```

2. Set environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the development server:
```bash
uvicorn app.main:app --reload
# or
uv run uvicorn app.main:app --reload
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

### Users
- `GET /users` - List all users (paginated)
- `GET /users/{id}` - Get specific user
- `PATCH /users/{id}` - Update user (own profile only)
- `DELETE /users/{id}` - Soft delete user

### Projects
- `POST /projects` - Create new project
- `GET /projects` - List projects (with filters)
- `GET /projects/{id}` - Get project details
- `PATCH /projects/{id}` - Update project (owner only)
- `DELETE /projects/{id}` - Archive project

### Tasks
- `POST /tasks` - Create new task
- `GET /tasks` - List tasks (with filters)
- `GET /tasks/{id}` - Get task details
- `PATCH /tasks/{id}` - Update task
- `POST /tasks/bulk-update` - Update multiple tasks

## Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

## Documentation

- Interactive API docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Tutorial

This example is part of the Zenith tutorial series. Follow along at:
https://zenith.ninja/tutorial/01-getting-started