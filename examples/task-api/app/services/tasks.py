"""
Task service with transaction support.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlmodel import select, and_, or_, func
from app.services import BaseService
from app.models import Task, TaskCreate, TaskUpdate, Project
from app.exceptions import NotFoundError, PermissionError, ValidationError


class TaskService(BaseService):
    """Manages task operations with transaction support."""

    async def create_task(self, task_data: TaskCreate, user_id: int) -> Task:
        """Create a task within a project."""
        # Verify project exists and user owns it
        project = await self.session.get(Project, task_data.project_id)
        if not project:
            raise NotFoundError(f"Project {task_data.project_id} not found")

        if project.owner_id != user_id:
            raise PermissionError("You can only add tasks to your own projects")

        # Create the task
        task = Task(**task_data.model_dump(), created_by=user_id)

        # Set default due date if not provided
        if not task.due_date:
            task.due_date = datetime.utcnow() + timedelta(days=7)

        self.session.add(task)

        # Update project's last activity
        project.updated_at = datetime.utcnow()

        await self.commit()
        await self.session.refresh(task)
        await self.session.refresh(task, ["project", "assignee"])

        return task

    async def get_task(self, task_id: int) -> Task:
        """Get task by ID."""
        task = await self.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")

        await self.session.refresh(task, ["project", "assignee"])
        return task

    async def list_tasks(
        self,
        project_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Task], int]:
        """List tasks with multiple filters."""
        # Start with base query
        query = select(Task)

        # Build filter conditions
        conditions = []

        if project_id:
            conditions.append(Task.project_id == project_id)

        if assignee_id:
            conditions.append(Task.assignee_id == assignee_id)

        if status:
            if status == "completed":
                conditions.append(Task.is_completed == True)
            elif status == "pending":
                conditions.append(Task.is_completed == False)
            elif status == "overdue":
                conditions.append(
                    and_(Task.is_completed == False, Task.due_date < datetime.utcnow())
                )

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Get count
        count_stmt = select(func.count()).select_from(query.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Order by priority and due date
        query = (
            query.order_by(Task.priority.desc(), Task.due_date)
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.exec(query)
        tasks = result.all()

        # Load relationships
        for task in tasks:
            await self.session.refresh(task, ["project", "assignee"])

        return tasks, total

    async def update_task(
        self, task_id: int, task_update: TaskUpdate, user_id: int
    ) -> Task:
        """Update task with permission checks."""
        task = await self.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")

        # Load project to check ownership
        await self.session.refresh(task, ["project"])

        # Permission checks
        is_owner = task.project.owner_id == user_id
        is_assignee = task.assignee_id == user_id

        if not (is_owner or is_assignee):
            raise PermissionError("You don't have permission to update this task")

        # Assignees can only update completion status
        if is_assignee and not is_owner:
            update_data = task_update.model_dump(exclude_unset=True)
            allowed_fields = {"is_completed", "completed_at"}

            if set(update_data.keys()) - allowed_fields:
                raise PermissionError("Assignees can only update completion status")

        # Apply updates
        update_data = task_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(task, field, value)

        # Auto-set completed_at when marking as complete
        if "is_completed" in update_data:
            if update_data["is_completed"]:
                task.completed_at = datetime.utcnow()
            else:
                task.completed_at = None

        task.updated_at = datetime.utcnow()

        await self.commit()
        await self.session.refresh(task)

        return task

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a task (hard delete)."""
        task = await self.get_task(task_id)

        # Load project for permission check
        await self.session.refresh(task, ["project"])

        if task.project.owner_id != user_id:
            raise PermissionError("Only the project owner can delete tasks")

        await self.session.delete(task)
        await self.commit()
        return True

    async def bulk_update_tasks(
        self, task_ids: List[int], update_data: dict, user_id: int
    ) -> int:
        """Update multiple tasks at once."""
        updated_count = 0

        for task_id in task_ids:
            task = await self.session.get(Task, task_id)
            if not task:
                continue

            # Check permissions
            await self.session.refresh(task, ["project"])
            if task.project.owner_id != user_id:
                continue

            # Apply updates
            for field, value in update_data.items():
                if hasattr(task, field):
                    setattr(task, field, value)

            task.updated_at = datetime.utcnow()
            updated_count += 1

        await self.commit()
        return updated_count
