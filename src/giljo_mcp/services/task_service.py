"""
TaskService - Dedicated service for task management

This service extracts all task-related operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).

Responsibilities:
- CRUD operations for tasks
- Task assignment to agents
- Task status tracking and lifecycle
- Task prioritization and categorization

Design Principles:
- Single Responsibility: Only task domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Project, Task
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class TaskService:
    """
    Service for managing tasks.

    This service handles all task-related operations including:
    - Creating and logging tasks
    - Listing and filtering tasks
    - Updating task status and properties
    - Task-agent assignment
    - Task completion

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize TaskService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Task Creation
    # ============================================================================

    async def log_task(
        self,
        content: str,
        category: Optional[str] = None,
        priority: str = "medium",
        project_id: Optional[str] = None,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Quick task capture - logs a task with minimal information.

        If no project_id is provided, finds or creates an active project.
        If no tenant_key is provided, uses current tenant context.

        Args:
            content: Task description (used as both title and description)
            category: Optional category/classification
            priority: Task priority (default: "medium")
            project_id: Optional project ID to attach task to
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status and task_id or error

        Example:
            >>> result = await service.log_task(
            ...     content="Fix authentication bug",
            ...     category="bug",
            ...     priority="high"
            ... )
            >>> print(result["task_id"])
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            async with self.db_manager.get_session_async() as session:
                project = None

                # Get or find project
                if project_id:
                    result = await session.execute(
                        select(Project).where(Project.id == project_id)
                    )
                    project = result.scalar_one_or_none()
                else:
                    # Find first active project
                    stmt = select(Project).where(Project.status == "active").limit(1)
                    result = await session.execute(stmt)
                    project = result.scalar_one_or_none()

                # Create default project if needed
                if not project:
                    project = Project(
                        name="Default Tasks",
                        mission="Default project for task logging",
                        tenant_key=tenant_key or f"tk_{uuid4().hex[:12]}",
                        status="active",
                    )
                    session.add(project)
                    await session.flush()

                # Create task
                task = Task(
                    tenant_key=project.tenant_key,
                    product_id=project.product_id,  # Inherit from project
                    project_id=str(project.id),
                    title=content,  # Use content as title
                    description=content,  # Also store as description
                    category=category,
                    priority=priority,
                    status="pending",
                )

                session.add(task)
                await session.commit()

                task_id = str(task.id)

                self._logger.info(
                    f"Logged task {task_id} in project {project.id}"
                )

                return {
                    "success": True,
                    "task_id": task_id,
                    "message": "Task logged successfully",
                }

        except Exception as e:
            self._logger.exception(f"Failed to log task: {e}")
            return {"success": False, "error": str(e)}

    async def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        assigned_to: Optional[str] = None,
        project_id: Optional[str] = None,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Create a new task with full details.

        This delegates to log_task for simplicity, using description as content
        and title as category.

        Args:
            title: Task title/summary
            description: Detailed task description
            priority: Task priority (default: "medium")
            assigned_to: Optional agent name to assign to (not implemented yet)
            project_id: Optional project ID
            tenant_key: Optional tenant key

        Returns:
            Dict with success status and task_id or error

        Example:
            >>> result = await service.create_task(
            ...     title="Implement feature X",
            ...     description="Add new feature X with unit tests",
            ...     priority="high"
            ... )
        """
        return await self.log_task(
            content=description,
            category=title,
            priority=priority,
            project_id=project_id,
            tenant_key=tenant_key
        )

    # ============================================================================
    # Task Retrieval
    # ============================================================================

    async def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        project_id: Optional[str] = None,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List tasks with optional filters.

        Args:
            status: Filter by task status (optional)
            assigned_to: Filter by assigned agent (not yet implemented)
            project_id: Filter by project ID (uses active project if not provided)
            tenant_key: Tenant key for filtering (uses current if not provided)

        Returns:
            Dict with success status and list of tasks or error

        Example:
            >>> result = await service.list_tasks(status="pending")
            >>> for task in result["tasks"]:
            ...     print(f"{task['id']}: {task['description']}")
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                project = None

                # Get or find project
                if project_id:
                    result = await session.execute(
                        select(Project).where(Project.id == project_id)
                    )
                    project = result.scalar_one_or_none()
                else:
                    # Find active project
                    project_query = select(Project).where(
                        and_(Project.tenant_key == tenant_key, Project.status == "active")
                    )
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()

                    # Fallback to most recent project
                    if not project:
                        project_query = (
                            select(Project)
                            .where(Project.tenant_key == tenant_key)
                            .order_by(Project.created_at.desc())
                            .limit(1)
                        )
                        project_result = await session.execute(project_query)
                        project = project_result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                # Query tasks
                query = select(Task).where(Task.project_id == project.id)
                if status:
                    query = query.where(Task.status == status)

                result = await session.execute(query)
                tasks = result.scalars().all()

                task_list = []
                for task in tasks:
                    task_list.append({
                        "id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "status": task.status,
                        "priority": task.priority,
                        "project_id": task.project_id,
                        "assigned_to": task.assigned_to if hasattr(task, "assigned_to") else None,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                    })

                return {
                    "success": True,
                    "tasks": task_list,
                    "count": len(task_list)
                }

        except Exception as e:
            self._logger.exception(f"Failed to list tasks: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Task Updates
    # ============================================================================

    async def update_task(
        self,
        task_id: str,
        **kwargs
    ) -> dict[str, Any]:
        """
        Update a task with arbitrary fields.

        Args:
            task_id: Task UUID (required)
            **kwargs: Field names and values to update

        Returns:
            Dict with success status and updated fields or error

        Example:
            >>> result = await service.update_task(
            ...     task_id="abc-123",
            ...     status="in_progress",
            ...     priority="high"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                task_query = select(Task).where(Task.id == task_id)
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {
                        "success": False,
                        "error": f"Task {task_id} not found"
                    }

                # Update fields
                updated_fields = []
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                        updated_fields.append(key)
                    else:
                        self._logger.warning(
                            f"Attempted to update non-existent field '{key}' on task {task_id}"
                        )

                await session.commit()

                self._logger.info(f"Updated task {task_id}: {updated_fields}")

                return {
                    "success": True,
                    "task_id": task_id,
                    "updated_fields": updated_fields
                }

        except Exception as e:
            self._logger.exception(f"Failed to update task: {e}")
            return {"success": False, "error": str(e)}

    async def assign_task(
        self,
        task_id: str,
        agent_name: str
    ) -> dict[str, Any]:
        """
        Assign a task to an agent.

        Args:
            task_id: Task UUID
            agent_name: Name of agent to assign to

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.assign_task(
            ...     task_id="abc-123",
            ...     agent_name="impl-1"
            ... )
        """
        return await self.update_task(
            task_id,
            assigned_to=agent_name,
            status="assigned"
        )

    async def complete_task(self, task_id: str) -> dict[str, Any]:
        """
        Mark a task as completed.

        Args:
            task_id: Task UUID

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.complete_task("abc-123")
        """
        return await self.update_task(task_id, status="completed")
