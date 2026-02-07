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
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    AuthorizationError,
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.tenant import TenantManager


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

    def __init__(
        self,
        db_manager: DatabaseManager = None,
        tenant_manager: TenantManager = None,
        session: AsyncSession | None = None,
    ):
        """
        Initialize TaskService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            session: Optional AsyncSession for test transaction isolation (Handover 0324)
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._session = session  # Store for test transaction isolation
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
        tenant_key: Optional[str] = None,
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
            if self._session:
                return await self._log_task_impl(self._session, content, category, priority, project_id, tenant_key)
            async with self.db_manager.get_session_async() as session:
                return await self._log_task_impl(session, content, category, priority, project_id, tenant_key)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to log task")
            raise BaseGiljoError(message=str(e), context={"operation": "log_task"}) from e

    async def _log_task_impl(
        self,
        session: AsyncSession,
        content: str,
        category: Optional[str],
        priority: str,
        project_id: Optional[str],
        tenant_key: Optional[str],
    ) -> dict[str, Any]:
        """Implementation of log_task with explicit session parameter."""
        # Use provided tenant_key or get from context
        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()

        project = None

        # Get or find project
        if project_id:
            # Filter by tenant_key to prevent cross-tenant access
            if tenant_key:
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
            else:
                # Fallback for backward compatibility
                result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            # If project_id was provided but project not found, fail immediately
            # This prevents cross-tenant access attempts from creating default projects
            if not project:
                raise ResourceNotFoundError(
                    message=f"Project {project_id} not found or access denied",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )
        else:
            # Find first active project
            stmt = select(Project).where(Project.status == "active").limit(1)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

        # Create default project if needed
        if not project:
            project = Project(
                name="Default Tasks",
                description="Default project for task logging",
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

        self._logger.info(f"Logged task {task_id} in project {project.id}")

        return {
            "success": True,
            "task_id": task_id,
            "message": "Task logged successfully",
        }

    async def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        assigned_to: Optional[str] = None,
        project_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
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
            content=description, category=title, priority=priority, project_id=project_id, tenant_key=tenant_key
        )

    # ============================================================================
    # Task Retrieval
    # ============================================================================

    async def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        project_id: Optional[str] = None,
        product_id: Optional[str] = None,
        priority: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        filter_type: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        List tasks with optional filters (enhanced for API endpoint support - Handover 0324).

        Args:
            status: Filter by task status (optional)
            assigned_to: Filter by assigned agent (not yet implemented)
            project_id: Filter by project ID (optional)
            product_id: Filter by product ID (optional)
            priority: Filter by priority level (optional)
            created_by_user_id: Filter by creator user ID (optional)
            filter_type: Special filter type ('product_tasks', 'all_tasks', or None)
            tenant_key: Tenant key for filtering (uses current if not provided)

        Returns:
            Dict with success status and list of tasks or error

        Example:
            >>> result = await service.list_tasks(status="pending", priority="high")
            >>> for task in result["tasks"]:
            ...     print(f"{task['id']}: {task['description']}")
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_tasks"})

            async with self.db_manager.get_session_async() as session:
                # Start with tenant-scoped base query
                query = select(Task).where(Task.tenant_key == tenant_key)

                # Handle special filter types (product-scoped filtering)
                if filter_type == "product_tasks":
                    # Use explicit product_id if provided, otherwise get active product
                    if product_id:
                        query = query.where(Task.product_id == product_id)
                    else:
                        # Get active product for tenant
                        from src.giljo_mcp.models.products import Product

                        product_query = select(Product).where(and_(Product.tenant_key == tenant_key, Product.is_active))
                        product_result = await session.execute(product_query)
                        active_product = product_result.scalar_one_or_none()

                        if active_product:
                            query = query.where(Task.product_id == active_product.id)
                        else:
                            # No active product - return empty list
                            return {"success": True, "tasks": [], "count": 0}

                elif filter_type == "all_tasks":
                    # Tasks with NULL product_id
                    query = query.where(Task.product_id.is_(None))

                # Apply other filters
                if product_id and not filter_type:
                    query = query.where(Task.product_id == product_id)

                if project_id:
                    query = query.where(Task.project_id == project_id)

                if status:
                    query = query.where(Task.status == status)

                if priority:
                    query = query.where(Task.priority == priority)

                if created_by_user_id:
                    query = query.where(Task.created_by_user_id == created_by_user_id)

                # Order by creation date (newest first)
                query = query.order_by(Task.created_at.desc())

                # Execute query
                result = await session.execute(query)
                tasks = result.scalars().all()

                # Convert to dict list
                task_list = [
                    {
                        "id": str(task.id),
                        "tenant_key": task.tenant_key,
                        "product_id": task.product_id,
                        "project_id": task.project_id,
                        "parent_task_id": task.parent_task_id,
                        "job_id": task.job_id,
                        "created_by_user_id": task.created_by_user_id,
                        "converted_to_project_id": task.converted_to_project_id,
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "status": task.status,
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "estimated_effort": task.estimated_effort,
                        "actual_effort": task.actual_effort,
                    }
                    for task in tasks
                ]

                return {"success": True, "tasks": task_list, "count": len(task_list)}

        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to list tasks")
            raise BaseGiljoError(message=str(e), context={"operation": "list_tasks"}) from e

    # ============================================================================
    # Task Updates
    # ============================================================================

    async def update_task(self, task_id: str, **kwargs) -> dict[str, Any]:
        """
        Update a task with arbitrary fields.

        Automatically handles timestamp updates based on status changes:
        - status → "in_progress": Sets started_at if not already set
        - status → "completed" or "cancelled": Sets completed_at if not already set

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
                    raise ResourceNotFoundError(message=f"Task {task_id} not found", context={"task_id": task_id})

                # Update fields
                updated_fields = []
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                        updated_fields.append(key)
                    else:
                        self._logger.warning(f"Attempted to update non-existent field '{key}' on task {task_id}")

                # Auto-update timestamps based on status changes (Handover 0324)
                if "status" in kwargs:
                    new_status = kwargs["status"]
                    now = datetime.now(timezone.utc)

                    if new_status == "in_progress" and not task.started_at:
                        task.started_at = now
                        updated_fields.append("started_at")
                        self._logger.debug(f"Auto-set started_at for task {task_id}")

                    elif new_status in ("completed", "cancelled") and not task.completed_at:
                        task.completed_at = now
                        updated_fields.append("completed_at")
                        self._logger.debug(f"Auto-set completed_at for task {task_id}")

                await session.commit()

                self._logger.info(f"Updated task {task_id}: {updated_fields}")

                return {"success": True, "task_id": task_id, "updated_fields": updated_fields}

        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to update task")
            raise BaseGiljoError(message=str(e), context={"operation": "update_task", "task_id": task_id}) from e

    async def assign_task(self, task_id: str, agent_name: str) -> dict[str, Any]:
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
        return await self.update_task(task_id, assigned_to=agent_name, status="assigned")

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

    # ============================================================================
    # Enhanced Operations (Handover 0322 Phase 3)
    # ============================================================================

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """
        Retrieve a single task by ID.

        This method retrieves a task with full tenant isolation.
        Only tasks within the current tenant can be accessed.

        Args:
            task_id: Task UUID

        Returns:
            Dict with success status and task data:
            {
                "success": True,
                "data": {
                    "id": "...",
                    "title": "...",
                    "description": "...",
                    ...
                }
            }

        Example:
            >>> result = await service.get_task("abc-123")
            >>> if result["success"]:
            ...     print(result["data"]["title"])
        """
        try:
            if self._session:
                return await self._get_task_impl(self._session, task_id)
            async with self.db_manager.get_session_async() as session:
                return await self._get_task_impl(session, task_id)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to get task {task_id}")
            raise BaseGiljoError(message=str(e), context={"operation": "get_task", "task_id": task_id}) from e

    async def _get_task_impl(self, session: AsyncSession, task_id: str) -> dict[str, Any]:
        """Implementation of get_task with explicit session parameter."""
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available", context={"operation": "get_task", "task_id": task_id}
            )

        stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise ResourceNotFoundError(
                message="Task not found", context={"task_id": task_id, "tenant_key": tenant_key}
            )

        # Convert to dict
        task_data = {
            "id": str(task.id),
            "tenant_key": task.tenant_key,
            "product_id": task.product_id,
            "project_id": task.project_id,
            "parent_task_id": task.parent_task_id,
            "job_id": task.job_id,
            "created_by_user_id": task.created_by_user_id,
            "converted_to_project_id": task.converted_to_project_id,
            "title": task.title,
            "description": task.description,
            "category": task.category,
            "status": task.status,
            "priority": task.priority,
            "estimated_effort": task.estimated_effort,
            "actual_effort": task.actual_effort,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "meta_data": task.meta_data,
        }

        return {"success": True, "data": task_data}

    async def delete_task(self, task_id: str, user_id: str) -> dict[str, Any]:
        """
        Delete a task (with permission check).

        Only the task creator or an admin can delete tasks.
        This performs a hard delete from the database.

        Args:
            task_id: Task UUID
            user_id: User performing deletion

        Returns:
            Dict with success status:
            {
                "success": True,
                "message": "Task deleted successfully"
            }

        Example:
            >>> result = await service.delete_task("abc-123", user.id)
        """
        try:
            if self._session:
                return await self._delete_task_impl(self._session, task_id, user_id)
            async with self.db_manager.get_session_async() as session:
                return await self._delete_task_impl(session, task_id, user_id)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to delete task {task_id}")
            raise BaseGiljoError(message=str(e), context={"operation": "delete_task", "task_id": task_id}) from e

    async def _delete_task_impl(self, session: AsyncSession, task_id: str, user_id: str) -> dict[str, Any]:
        """Implementation of delete_task with explicit session parameter."""
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available", context={"operation": "delete_task", "task_id": task_id}
            )

        # Get task
        task_stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
        task_result = await session.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise ResourceNotFoundError(
                message="Task not found", context={"task_id": task_id, "tenant_key": tenant_key}
            )

        # Get user for permission check
        from src.giljo_mcp.models.auth import User

        user_stmt = select(User).where(User.id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Permission check
        if not self.can_delete_task(task, user):
            raise AuthorizationError(
                message="Not authorized to delete this task. Only task creator or admin can delete.",
                context={"task_id": task_id, "user_id": user_id},
            )

        # Delete task
        await session.delete(task)
        await session.commit()

        self._logger.info(f"Deleted task {task_id} by user {user_id}")

        return {"success": True, "message": "Task deleted successfully"}

    async def convert_to_project(
        self, task_id: str, project_name: Optional[str], strategy: str, include_subtasks: bool, user_id: str
    ) -> dict[str, Any]:
        """
        Convert task to project with optional subtask handling.

        This is a complex multi-entity operation involving:
        - Task retrieval
        - Product lookup
        - Project creation via ProjectService
        - Subtask conversion (if include_subtasks=True)
        - Task deletion/archival

        Args:
            task_id: Task UUID to convert
            project_name: Optional custom project name (defaults to task title)
            strategy: Conversion strategy ("create_new", "merge", etc.)
            include_subtasks: Whether to include child tasks
            user_id: User performing conversion

        Returns:
            Dict with success status and new project data:
            {
                "success": True,
                "data": {
                    "project_id": "...",
                    "project_name": "...",
                    "original_task_id": "...",
                    "conversion_strategy": "create_new"
                }
            }

        Example:
            >>> result = await service.convert_to_project(
            ...     task_id="abc-123",
            ...     project_name="New Project",
            ...     strategy="create_new",
            ...     include_subtasks=True,
            ...     user_id=user.id
            ... )
        """
        try:
            if self._session:
                return await self._convert_to_project_impl(
                    self._session, task_id, project_name, strategy, include_subtasks, user_id
                )
            async with self.db_manager.get_session_async() as session:
                return await self._convert_to_project_impl(
                    session, task_id, project_name, strategy, include_subtasks, user_id
                )
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to convert task {task_id} to project")
            raise BaseGiljoError(message=str(e), context={"operation": "convert_to_project", "task_id": task_id}) from e

    async def _convert_to_project_impl(
        self,
        session: AsyncSession,
        task_id: str,
        project_name: Optional[str],
        strategy: str,
        include_subtasks: bool,
        user_id: str,
    ) -> dict[str, Any]:
        """Implementation of convert_to_project with explicit session parameter."""
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available", context={"operation": "convert_to_project", "task_id": task_id}
            )

        # Get task
        task_stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
        task_result = await session.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise ResourceNotFoundError(
                message="Task not found", context={"task_id": task_id, "tenant_key": tenant_key}
            )

        # Check if already converted
        if task.converted_to_project_id:
            raise ValidationError(
                message=f"Task already converted to project {task.converted_to_project_id}",
                context={"task_id": task_id, "converted_to_project_id": task.converted_to_project_id},
            )

        # Get user for permission check
        from src.giljo_mcp.models.auth import User

        user_stmt = select(User).where(User.id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Permission check (only creator or admin can convert)
        if user.role != "admin" and task.created_by_user_id != user.id:
            raise AuthorizationError(
                message="Not authorized to convert this task. Only task creator or admin can convert.",
                context={"task_id": task_id, "user_id": user_id},
            )

        # Get active product (required for project creation per Handover 0050)
        from src.giljo_mcp.models.products import Product

        product_stmt = select(Product).where(and_(Product.tenant_key == tenant_key, Product.is_active))
        product_result = await session.execute(product_stmt)
        active_product = product_result.scalar_one_or_none()

        if not active_product:
            raise ValidationError(
                message="No active product. Please activate a product before converting tasks to projects.",
                context={"operation": "convert_to_project", "tenant_key": tenant_key},
            )

        # Check for existing active project and deactivate it
        # (only ONE project can be active per product - Handover 0050b)
        existing_active_stmt = select(Project).where(
            and_(Project.product_id == active_product.id, Project.status == "active")
        )
        existing_active_result = await session.execute(existing_active_stmt)
        existing_active_project = existing_active_result.scalar_one_or_none()

        if existing_active_project:
            self._logger.info(
                f"Deactivating existing active project {existing_active_project.id} "
                f"before creating new project from task {task_id}"
            )
            existing_active_project.status = "inactive"
            existing_active_project.updated_at = datetime.now(timezone.utc)

        # Create project
        final_project_name = project_name or task.title
        new_project = Project(
            name=final_project_name,
            description=task.description or f"Project created from task: {task.title}",
            mission="",  # Leave empty - orchestrator will generate mission during staging
            product_id=active_product.id,
            tenant_key=tenant_key,
            status="inactive",  # Projects start inactive, user activates when ready
        )

        session.add(new_project)
        await session.flush()  # Get project ID without committing

        # Mark task as converted and completed
        task.converted_to_project_id = new_project.id
        task.status = "completed"  # Mark as completed, not 'converted'

        # Handle subtasks if requested
        if include_subtasks:
            subtask_stmt = select(Task).where(Task.parent_task_id == task_id)
            subtask_result = await session.execute(subtask_stmt)
            subtasks = subtask_result.scalars().all()

            for subtask in subtasks:
                subtask.project_id = new_project.id

        # Delete the task after successful conversion
        await session.delete(task)
        self._logger.info(f"Deleted task {task_id} after successful conversion to project {new_project.id}")

        await session.commit()
        await session.refresh(new_project)

        self._logger.info(f"Converted task {task_id} to project {new_project.id} (strategy: {strategy})")

        return {
            "success": True,
            "data": {
                "project_id": str(new_project.id),
                "project_name": new_project.name,
                "original_task_id": str(task_id),
                "conversion_strategy": strategy,
                "created_at": new_project.created_at.isoformat() if new_project.created_at else None,
            },
        }

    async def change_status(self, task_id: str, new_status: str) -> dict[str, Any]:
        """
        Change task status with automatic timestamp updates.

        Status transitions:
        - "todo" → "in_progress": Set started_at
        - * → "completed": Set completed_at
        - * → "cancelled": Set completed_at

        Args:
            task_id: Task UUID
            new_status: New status value

        Returns:
            Dict with success status and updated task:
            {
                "success": True,
                "data": {
                    "id": "...",
                    "status": "in_progress",
                    "started_at": "2025-11-20T10:00:00Z",
                    ...
                }
            }

        Example:
            >>> result = await service.change_status("abc-123", "in_progress")
        """
        try:
            if self._session:
                return await self._change_status_impl(self._session, task_id, new_status)
            async with self.db_manager.get_session_async() as session:
                return await self._change_status_impl(session, task_id, new_status)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to change task {task_id} status")
            raise BaseGiljoError(message=str(e), context={"operation": "change_status", "task_id": task_id}) from e

    async def _change_status_impl(self, session: AsyncSession, task_id: str, new_status: str) -> dict[str, Any]:
        """Implementation of change_status with explicit session parameter."""
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available", context={"operation": "change_status", "task_id": task_id}
            )

        stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise ResourceNotFoundError(
                message="Task not found", context={"task_id": task_id, "tenant_key": tenant_key}
            )

        # Update status
        task.status = new_status

        # Update timestamps based on status
        now = datetime.now(timezone.utc)
        if new_status == "in_progress" and not task.started_at:
            task.started_at = now
        elif new_status in ("completed", "cancelled") and not task.completed_at:
            task.completed_at = now

        await session.commit()
        await session.refresh(task)

        self._logger.info(f"Changed task {task_id} status to {new_status}")

        # Convert to dict for response
        task_data = {
            "id": str(task.id),
            "status": task.status,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "title": task.title,
            "description": task.description,
        }

        return {"success": True, "data": task_data}

    async def get_summary(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get task summary statistics.

        Returns counts grouped by status, optionally filtered by product.

        Args:
            product_id: Optional product filter

        Returns:
            Dict with success status and summary data:
            {
                "success": True,
                "data": {
                    "summary": {
                        "product-id-1": {
                            "total": 10,
                            "pending": 3,
                            "in_progress": 2,
                            "completed": 5,
                            "blocked": 0,
                            "cancelled": 0,
                            "by_priority": {
                                "critical": 1,
                                "high": 2,
                                "medium": 5,
                                "low": 2
                            }
                        },
                        ...
                    },
                    "total_products": 2,
                    "total_tasks": 25
                }
            }

        Example:
            >>> result = await service.get_summary()
            >>> print(result["data"]["total_tasks"])
        """
        try:
            if self._session:
                return await self._get_summary_impl(self._session, product_id)
            async with self.db_manager.get_session_async() as session:
                return await self._get_summary_impl(session, product_id)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            self._logger.exception("Failed to get task summary")
            raise BaseGiljoError(message=str(e), context={"operation": "get_summary"}) from e

    async def _get_summary_impl(self, session: AsyncSession, product_id: Optional[str] = None) -> dict[str, Any]:
        """Implementation of get_summary with explicit session parameter."""
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={"operation": "get_summary"})

        # Build base query
        base_query = select(Task).where(Task.tenant_key == tenant_key)
        if product_id:
            base_query = base_query.where(Task.product_id == product_id)

        result = await session.execute(base_query)
        tasks = result.scalars().all()

        # Aggregate by product
        summary = {}
        for task in tasks:
            pid = task.product_id or "no-product"
            if pid not in summary:
                summary[pid] = {
                    "total": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "blocked": 0,
                    "cancelled": 0,
                    "by_priority": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                }

            s = summary[pid]
            s["total"] += 1

            # Count by status
            status = task.status or "pending"
            if status in s:
                s[status] += 1

            # Count by priority
            priority = task.priority or "medium"
            if priority in s["by_priority"]:
                s["by_priority"][priority] += 1

        return {
            "success": True,
            "data": {"summary": summary, "total_products": len(summary), "total_tasks": len(tasks)},
        }

    # ============================================================================
    # Permission Helpers (Handover 0322 Phase 3)
    # ============================================================================

    def can_modify_task(self, task: Task, user) -> bool:
        """
        Check if user can modify task.

        Rules:
        - Admin: can modify any task in tenant
        - Developer: can modify own tasks (created_by_user_id)
        - Viewer: cannot modify

        Args:
            task: Task to check
            user: User attempting modification

        Returns:
            True if user can modify task, False otherwise

        Example:
            >>> if service.can_modify_task(task, current_user):
            ...     # Allow modification
        """

        # Admin can modify any task in their tenant
        if user.role == "admin":
            return task.tenant_key == user.tenant_key

        # Developer can modify tasks they created
        return task.tenant_key == user.tenant_key and task.created_by_user_id == user.id

    def can_delete_task(self, task: Task, user) -> bool:
        """
        Check if user can delete task.

        Rules:
        - Admin: can delete any task in tenant
        - Developer: can delete own tasks
        - Viewer: cannot delete

        Args:
            task: Task to check
            user: User attempting deletion

        Returns:
            True if user can delete task, False otherwise

        Example:
            >>> if service.can_delete_task(task, current_user):
            ...     # Allow deletion
        """

        # Admin can delete any task in their tenant
        if user.role == "admin":
            return task.tenant_key == user.tenant_key

        # Developer can delete tasks they created
        return task.tenant_key == user.tenant_key and task.created_by_user_id == user.id
