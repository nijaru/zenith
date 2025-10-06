"""
Project service for managing projects and team collaboration.
"""

from datetime import datetime

from sqlmodel import func, select

from app.exceptions import NotFoundError, PermissionError
from app.models import Project, ProjectCreate, ProjectUpdate
from app.services import BaseService


class ProjectService(BaseService):
    """Manages project operations."""

    async def create_project(
        self, project_data: ProjectCreate, owner_id: int
    ) -> Project:
        """Create a new project."""
        project = Project(**project_data.model_dump(), owner_id=owner_id)

        self.session.add(project)
        await self.commit()
        await self.session.refresh(project)

        # Load owner relationship
        await self.session.refresh(project, ["owner"])

        return project

    async def get_project(self, project_id: int) -> Project:
        """Get project with owner loaded."""
        project = await self.session.get(Project, project_id)
        if not project:
            raise NotFoundError(f"Project {project_id} not found")

        # Eager load relationships
        await self.session.refresh(project, ["owner", "tasks"])
        return project

    async def list_projects(
        self,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> tuple[list[Project], int]:
        """List projects with filters."""
        query = select(Project)

        # Filter by owner if specified
        if user_id:
            query = query.where(Project.owner_id == user_id)

        # Exclude archived unless requested
        if not include_archived:
            query = query.where(Project.is_archived == False)

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Apply pagination and ordering
        query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.exec(query)
        projects = result.all()

        # Load owners for all projects
        for project in projects:
            await self.session.refresh(project, ["owner"])

        return projects, total

    async def update_project(
        self, project_id: int, project_update: ProjectUpdate, user_id: int
    ) -> Project:
        """Update project if user is owner."""
        project = await self.get_project(project_id)

        # Check ownership
        if project.owner_id != user_id:
            raise PermissionError("Only the project owner can update it")

        # Update fields
        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        project.updated_at = datetime.utcnow()

        await self.commit()
        await self.session.refresh(project)

        return project

    async def archive_project(self, project_id: int, user_id: int) -> Project:
        """Archive (soft delete) a project."""
        project = await self.get_project(project_id)

        if project.owner_id != user_id:
            raise PermissionError("Only the project owner can archive it")

        project.is_archived = True
        project.archived_at = datetime.utcnow()

        await self.commit()
        return project

    async def get_project_stats(self, project_id: int) -> dict:
        """Get project statistics."""
        project = await self.get_project(project_id)

        total_tasks = len(project.tasks)
        completed_tasks = sum(1 for t in project.tasks if t.is_completed)

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": total_tasks - completed_tasks,
            "completion_rate": (
                completed_tasks / total_tasks * 100 if total_tasks > 0 else 0
            ),
        }
