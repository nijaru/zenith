"""
TaskFlow API - Complete task management system built with Zenith.
"""

from fastapi import Body, Depends, Path, Query

from app.auth import get_current_user, get_optional_user
from app.config import settings
from app.database import get_session, init_db
from app.exceptions import APIException, AuthenticationError
from app.models import (
    LoginRequest,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.projects import ProjectService
from app.services.tasks import TaskService
from app.services.users import UserService
from zenith import Zenith
from zenith.responses import JSONResponse

# Create application
app = Zenith(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Complete task management API with authentication, projects, and tasks",
    debug=settings.DEBUG,
)


# Error handler for custom exceptions
@app.exception_handler(APIException)
async def api_exception_handler(request, exc: APIException):
    """Convert custom exceptions to JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )


# Startup event
@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()


# ============= AUTHENTICATION ENDPOINTS =============


@app.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, session=Depends(get_session)):
    """Register a new user."""
    service = UserService(session)
    user = await service.create_user(user_data)
    return user


@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, session=Depends(get_session)):
    """Login and get access token."""
    service = UserService(session)
    result = await service.authenticate(login_data.email, login_data.password)

    if not result:
        raise AuthenticationError("Invalid email or password")

    return TokenResponse(**result)


# ============= USER ENDPOINTS =============


@app.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max users to return"),
    search: str | None = Query(None, description="Search in name/email"),
    session=Depends(get_session),
):
    """List all users with pagination."""
    service = UserService(session)
    users, total = await service.list_users(skip, limit, search)

    return JSONResponse(
        content=[UserResponse.model_validate(user).model_dump() for user in users],
        headers={"X-Total-Count": str(total)},
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., ge=1, description="User ID"), session=Depends(get_session)
):
    """Get a specific user by ID."""
    service = UserService(session)
    user = await service.get_user(user_id)
    return user


@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    user_id: int = Path(..., ge=1),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Update user profile."""
    service = UserService(session)
    user = await service.update_user(user_id, user_update, current_user.id)
    return user


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int = Path(..., ge=1),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Delete (deactivate) a user account."""
    service = UserService(session)
    await service.delete_user(user_id, current_user.id)
    return None


# ============= PROJECT ENDPOINTS =============


@app.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Create a new project."""
    service = ProjectService(session)
    project = await service.create_project(project_data, current_user.id)
    return project


@app.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    my_projects_only: bool = Query(False, description="Only show my projects"),
    include_archived: bool = Query(False, description="Include archived"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_optional_user),
    session=Depends(get_session),
):
    """List projects with filters."""
    service = ProjectService(session)

    user_id = current_user.id if current_user and my_projects_only else None
    projects, total = await service.list_projects(
        user_id=user_id, skip=skip, limit=limit, include_archived=include_archived
    )

    # Convert to response models
    response_data = []
    for project in projects:
        project_dict = ProjectResponse.model_validate(project).model_dump()
        project_dict["task_count"] = len(project.tasks)
        response_data.append(project_dict)

    return JSONResponse(content=response_data, headers={"X-Total-Count": str(total)})


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int = Path(..., ge=1), session=Depends(get_session)):
    """Get project details."""
    service = ProjectService(session)
    project = await service.get_project(project_id)
    return project


@app.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_update: ProjectUpdate,
    project_id: int = Path(..., ge=1),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Update project details."""
    service = ProjectService(session)
    project = await service.update_project(project_id, project_update, current_user.id)
    return project


@app.delete("/projects/{project_id}", response_model=ProjectResponse)
async def archive_project(
    project_id: int = Path(..., ge=1),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Archive (soft delete) a project."""
    service = ProjectService(session)
    project = await service.archive_project(project_id, current_user.id)
    return project


@app.get("/projects/{project_id}/stats")
async def get_project_stats(
    project_id: int = Path(..., ge=1), session=Depends(get_session)
):
    """Get project statistics."""
    service = ProjectService(session)
    stats = await service.get_project_stats(project_id)
    return stats


# ============= TASK ENDPOINTS =============


@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Create a new task."""
    service = TaskService(session)
    task = await service.create_task(task_data, current_user.id)
    return task


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    project_id: int | None = Query(None, description="Filter by project"),
    assignee_id: int | None = Query(None, description="Filter by assignee"),
    status: str | None = Query(None, description="pending, completed, or overdue"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session=Depends(get_session),
):
    """List tasks with multiple filters."""
    service = TaskService(session)
    tasks, total = await service.list_tasks(
        project_id=project_id,
        assignee_id=assignee_id,
        status=status,
        skip=skip,
        limit=limit,
    )

    return JSONResponse(
        content=[TaskResponse.model_validate(task).model_dump() for task in tasks],
        headers={"X-Total-Count": str(total)},
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int = Path(..., ge=1), session=Depends(get_session)):
    """Get task details."""
    service = TaskService(session)
    task = await service.get_task(task_id)
    return task


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_update: TaskUpdate,
    task_id: int = Path(..., ge=1),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Update a task."""
    service = TaskService(session)
    task = await service.update_task(task_id, task_update, current_user.id)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int = Path(..., ge=1),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Delete a task permanently."""
    service = TaskService(session)
    await service.delete_task(task_id, current_user.id)
    return None


@app.post("/tasks/bulk-update")
async def bulk_update_tasks(
    task_ids: list[int] = Body(..., description="List of task IDs"),
    update_data: dict = Body(..., description="Fields to update"),
    current_user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Update multiple tasks at once."""
    service = TaskService(session)
    count = await service.bulk_update_tasks(task_ids, update_data, current_user.id)
    return {"updated_count": count}


# ============= HEALTH & DOCS =============


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
    }


@app.get("/")
async def root():
    """API root with basic info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


# Development runner
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG
    )
