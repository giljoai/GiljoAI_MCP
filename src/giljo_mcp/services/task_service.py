"""
TaskService - Dedicated service for task management

This service extracts all task-related operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).
Updated for typed returns (Handover 0731c).

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

Return Type Conventions (0731c):
- Simple lookups return the ORM model directly (Task)
- Not-found cases raise ResourceNotFoundError
- Validation failures raise ValidationError
- Authorization failures raise AuthorizationError
- Delete operations return None (already correct)
- Update operations return TaskUpdateResult
- Conversion operations return ConversionResult
- List operations return list[Task]
- Summary operations return dict (complex nested structure)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

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
from src.giljo_mcp.schemas.service_responses import ConversionResult, TaskUpdateResult
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

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.

        Returns:
            Context manager for database session
        """
        if self._session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._session

            return _test_session_wrapper()

        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

    # ============================================================================
    # Task Creation
    # ============================================================================

    async def log_task(
        self,
        content: str,
        category: Optional[str] = None,
        priority: str = "medium",
        project_id: Optional[str] = None,
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Quick task capture - logs a task with minimal information.

        Args:
            content: Task content (used as fallback for title and description)
            category: Optional category/classification
            priority: Task priority (default: "medium")
            project_id: Optional project ID to attach task to
            product_id: Required product ID (task must belong to a product)
            tenant_key: Required tenant key for multi-tenant isolation
            title: Optional explicit title (overrides content for Task.title)
            description: Optional explicit description (overrides content for Task.description)

        Returns:
            Task ID of created task

        Raises:
            ValidationError: Missing required parameters (product_id, tenant_key)
            ResourceNotFoundError: Project not found
            DatabaseError: Database operation failed

        Example:
            >>> task_id = await service.log_task(
            ...     content="Fix authentication bug",
            ...     category="bug",
            ...     priority="high",
            ...     product_id="prod-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(task_id)
        """
        try:
            if self._session:
                return await self._log_task_impl(
                    self._session,
                    content,
                    category,
                    priority,
                    project_id,
                    product_id,
                    tenant_key,
                    title=title,
                    description=description,
                )
            async with self._get_session() as session:
                return await self._log_task_impl(
                    session,
                    content,
                    category,
                    priority,
                    project_id,
                    product_id,
                    tenant_key,
                    title=title,
                    description=description,
                )
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to log task")
            raise BaseGiljoError(message=str(e), context={"operation": "log_task"}) from e

    async def _log_task_impl(
        self,
        session: AsyncSession,
        content: str,
        category: Optional[str],
        priority: str,
        project_id: Optional[str],
        product_id: Optional[str],
        tenant_key: Optional[str],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Implementation of log_task with explicit session parameter.

        Args:
            session: Database session
            content: Task content (used as fallback for title and description)
            category: Optional category/classification
            priority: Task priority
            project_id: Optional project ID
            product_id: Required product ID
            tenant_key: Required tenant key
            title: Optional explicit title (overrides content for Task.title)
            description: Optional explicit description (overrides content for Task.description)

        Returns:
            Task ID of created task

        Raises:
            ValidationError: Missing tenant_key or product_id
            ResourceNotFoundError: Project not found
        """
        # Use provided tenant_key or get from context
        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()

        # Validate required parameters (Handover 0433 Phase 2)
        if not tenant_key:
            raise ValidationError(
                message="tenant_key is required for task creation",
                context={"operation": "log_task"},
            )

        if not product_id:
            raise ValidationError(
                message="product_id is required for task creation",
                context={"operation": "log_task"},
            )

        project = None

        # Get project if specified
        if project_id:
            # Always filter by both tenant_key AND product_id for security
            result = await session.execute(
                select(Project).where(
                    and_(Project.id == project_id, Project.product_id == product_id, Project.tenant_key == tenant_key)
                )
            )
            project = result.scalar_one_or_none()

            # If project_id was provided but project not found, fail immediately
            if not project:
                raise ResourceNotFoundError(
                    message=f"Project {project_id} not found or access denied",
                    context={"project_id": project_id, "product_id": product_id, "tenant_key": tenant_key},
                )

        # Use title/description if provided, fall back to content for backwards compat
        task_title = title or content
        task_description = description or content

        # Create task
        task = Task(
            tenant_key=tenant_key,
            product_id=product_id,
            project_id=str(project.id) if project else None,
            title=task_title,
            description=task_description,
            category=category,
            priority=priority,
            status="pending",
        )

        session.add(task)
        await session.commit()

        task_id = str(task.id)

        if project:
            self._logger.info(f"Logged task {task_id} in project {project.id}")
        else:
            self._logger.info(f"Logged task {task_id} for product {product_id}")

        return task_id

    async def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        assigned_to: Optional[str] = None,
        project_id: Optional[str] = None,
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> str:
        """
        Create a new task with full details.

        Delegates to log_task with separate title and description parameters
        so that both are preserved independently on the Task model.

        Args:
            title: Task title/summary
            description: Detailed task description
            priority: Task priority (default: "medium")
            assigned_to: Optional agent name to assign to (not implemented yet)
            project_id: Optional project ID
            product_id: Required product ID (task must belong to a product)
            tenant_key: Required tenant key for multi-tenant isolation

        Returns:
            Task ID string (delegated from log_task)

        Example:
            >>> task_id = await service.create_task(
            ...     title="Implement feature X",
            ...     description="Add new feature X with unit tests",
            ...     priority="high",
            ...     product_id="prod-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        return await self.log_task(
            content=title,
            title=title,
            description=description,
            priority=priority,
            project_id=project_id,
            product_id=product_id,
            tenant_key=tenant_key,
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
    ) -> list[Task]:
        """List tasks with optional filters (enhanced for API endpoint support - Handover 0324).

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
            List of Task ORM models (0731c typed return)

        Raises:
            ValidationError: No tenant context
            DatabaseError: Database operation failed

        Example:
            >>> tasks = await service.list_tasks(status="pending", priority="high")
            >>> for task in tasks:
            ...     print(f"{task.id}: {task.description}")
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_tasks"})

            if self._session:
                return await self._list_tasks_impl(
                    self._session,
                    tenant_key,
                    status,
                    project_id,
                    product_id,
                    priority,
                    created_by_user_id,
                    filter_type,
                )
            async with self._get_session() as session:
                return await self._list_tasks_impl(
                    session,
                    tenant_key,
                    status,
                    project_id,
                    product_id,
                    priority,
                    created_by_user_id,
                    filter_type,
                )

        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list tasks")
            raise BaseGiljoError(message=str(e), context={"operation": "list_tasks"}) from e

    async def _list_tasks_impl(
        self,
        session: AsyncSession,
        tenant_key: str,
        status: Optional[str],
        project_id: Optional[str],
        product_id: Optional[str],
        priority: Optional[str],
        created_by_user_id: Optional[str],
        filter_type: Optional[str],
    ) -> list[Task]:
        """Implementation of list_tasks with explicit session parameter.

        Returns:
            List of Task ORM models

        Raises:
            ValidationError: No tenant context
        """
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
                    return []

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

        return list(tasks)

    # ============================================================================
    # Task Updates
    # ============================================================================

    async def update_task(self, task_id: str, **kwargs) -> TaskUpdateResult:
        """Update a task with arbitrary fields.

        Automatically handles timestamp updates based on status changes:
        - status -> "in_progress": Sets started_at if not already set
        - status -> "completed" or "cancelled": Sets completed_at if not already set

        Args:
            task_id: Task UUID (required)
            **kwargs: Field names and values to update

        Returns:
            TaskUpdateResult with task_id and list of updated field names

        Raises:
            ResourceNotFoundError: Task not found
            DatabaseError: Database operation failed

        Example:
            >>> result = await service.update_task(
            ...     task_id="abc-123",
            ...     status="in_progress",
            ...     priority="high"
            ... )
            >>> print(result.updated_fields)
        """
        try:
            if self._session:
                return await self._update_task_impl(self._session, task_id, **kwargs)
            async with self._get_session() as session:
                return await self._update_task_impl(session, task_id, **kwargs)

        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to update task")
            raise BaseGiljoError(message=str(e), context={"operation": "update_task", "task_id": task_id}) from e

    async def _update_task_impl(self, session: AsyncSession, task_id: str, **kwargs) -> TaskUpdateResult:
        """Implementation of update_task with explicit session parameter.

        Returns:
            TaskUpdateResult with task_id and list of updated field names

        Raises:
            ResourceNotFoundError: Task not found or access denied
            ValidationError: No tenant context available
        """
        # TENANT ISOLATION: Require tenant_key for all task updates
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available",
                context={"operation": "update_task", "task_id": task_id},
            )

        task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
        task_result = await session.execute(task_query)
        task = task_result.scalar_one_or_none()

        if not task:
            raise ResourceNotFoundError(
                message="Task not found or access denied",
                context={"task_id": task_id, "tenant_key": tenant_key},
            )

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

        return TaskUpdateResult(task_id=task_id, updated_fields=updated_fields)

    # ============================================================================
    # Enhanced Operations (Handover 0322 Phase 3)
    # ============================================================================

    async def get_task(self, task_id: str) -> Task:
        """Retrieve a single task by ID.

        This method retrieves a task with full tenant isolation.
        Only tasks within the current tenant can be accessed.

        Args:
            task_id: Task UUID

        Returns:
            Task ORM model (0731c typed return)

        Raises:
            ValidationError: No tenant context
            ResourceNotFoundError: Task not found
            DatabaseError: Database operation failed

        Example:
            >>> task = await service.get_task("abc-123")
            >>> print(task.title)
        """
        try:
            if self._session:
                return await self._get_task_impl(self._session, task_id)
            async with self._get_session() as session:
                return await self._get_task_impl(session, task_id)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get task {task_id}")
            raise BaseGiljoError(message=str(e), context={"operation": "get_task", "task_id": task_id}) from e

    async def _get_task_impl(self, session: AsyncSession, task_id: str) -> Task:
        """Implementation of get_task with explicit session parameter.

        Returns:
            Task ORM model

        Raises:
            ValidationError: No tenant context
            ResourceNotFoundError: Task not found
        """
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

        return task

    async def delete_task(self, task_id: str, user_id: str) -> None:
        """Delete a task (with permission check).

        Only the task creator or an admin can delete tasks.
        This performs a hard delete from the database.

        Args:
            task_id: Task UUID
            user_id: User performing deletion

        Returns:
            None on successful deletion

        Raises:
            ValidationError: No tenant context
            ResourceNotFoundError: Task or user not found
            AuthorizationError: User not authorized to delete task
            DatabaseError: Database operation failed

        Example:
            >>> await service.delete_task("abc-123", user.id)
        """
        try:
            if self._session:
                return await self._delete_task_impl(self._session, task_id, user_id)
            async with self._get_session() as session:
                return await self._delete_task_impl(session, task_id, user_id)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to delete task {task_id}")
            raise BaseGiljoError(message=str(e), context={"operation": "delete_task", "task_id": task_id}) from e

    async def _delete_task_impl(self, session: AsyncSession, task_id: str, user_id: str) -> None:
        """Implementation of delete_task with explicit session parameter.

        Returns:
            None on successful deletion

        Raises:
            ValidationError: No tenant context
            ResourceNotFoundError: Task or user not found
            AuthorizationError: User not authorized to delete task
        """
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

    async def convert_to_project(
        self, task_id: str, project_name: Optional[str], strategy: str, include_subtasks: bool, user_id: str
    ) -> ConversionResult:
        """Convert task to project with optional subtask handling.

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
            ConversionResult with task_id, project_id, and project_name (0731c typed return)

        Raises:
            ValidationError: No tenant context, already converted, no active product
            ResourceNotFoundError: Task or user not found
            AuthorizationError: User not authorized
            DatabaseError: Database operation failed

        Example:
            >>> result = await service.convert_to_project(
            ...     task_id="abc-123",
            ...     project_name="New Project",
            ...     strategy="create_new",
            ...     include_subtasks=True,
            ...     user_id=user.id
            ... )
            >>> print(result.project_id)
        """
        try:
            if self._session:
                return await self._convert_to_project_impl(
                    self._session, task_id, project_name, strategy, include_subtasks, user_id
                )
            async with self._get_session() as session:
                return await self._convert_to_project_impl(
                    session, task_id, project_name, strategy, include_subtasks, user_id
                )
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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
    ) -> ConversionResult:
        """Implementation of convert_to_project with explicit session parameter.

        Returns:
            ConversionResult with task_id, project_id, and project_name

        Raises:
            ValidationError: No tenant context, already converted, no active product
            ResourceNotFoundError: Task or user not found
            AuthorizationError: User not authorized
        """
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
            # TENANT ISOLATION: Filter subtasks by tenant_key
            subtask_stmt = select(Task).where(and_(Task.parent_task_id == task_id, Task.tenant_key == tenant_key))
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

        return ConversionResult(
            task_id=str(task_id),
            project_id=str(new_project.id),
            project_name=new_project.name,
        )

    async def change_status(self, task_id: str, new_status: str) -> Task:
        """Change task status with automatic timestamp updates.

        Status transitions:
        - "todo" -> "in_progress": Set started_at
        - * -> "completed": Set completed_at
        - * -> "cancelled": Set completed_at

        Args:
            task_id: Task UUID
            new_status: New status value

        Returns:
            Task ORM model with updated status and timestamps (0731c typed return)

        Raises:
            ValidationError: No tenant context
            ResourceNotFoundError: Task not found
            DatabaseError: Database operation failed

        Example:
            >>> task = await service.change_status("abc-123", "in_progress")
            >>> print(task.status)
        """
        try:
            if self._session:
                return await self._change_status_impl(self._session, task_id, new_status)
            async with self._get_session() as session:
                return await self._change_status_impl(session, task_id, new_status)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to change task {task_id} status")
            raise BaseGiljoError(message=str(e), context={"operation": "change_status", "task_id": task_id}) from e

    async def _change_status_impl(self, session: AsyncSession, task_id: str, new_status: str) -> Task:
        """Implementation of change_status with explicit session parameter.

        Returns:
            Task ORM model with updated status and timestamps

        Raises:
            ValidationError: No tenant context
            ResourceNotFoundError: Task not found
        """
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

        return task

    async def get_summary(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get task summary statistics.

        Returns counts grouped by status, optionally filtered by product.

        Args:
            product_id: Optional product filter

        Returns:
            Summary data dictionary with:
            - summary: dict of product_id -> stats (total, by status, by priority)
            - total_products: count of products with tasks
            - total_tasks: total number of tasks

        Raises:
            ValidationError: No tenant context
            DatabaseError: Database operation failed

        Example:
            >>> summary = await service.get_summary()
            >>> print(summary["total_tasks"])
        """
        try:
            if self._session:
                return await self._get_summary_impl(self._session, product_id)
            async with self._get_session() as session:
                return await self._get_summary_impl(session, product_id)
        except (BaseGiljoError, ResourceNotFoundError, ValidationError, AuthorizationError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get task summary")
            raise BaseGiljoError(message=str(e), context={"operation": "get_summary"}) from e

    async def _get_summary_impl(self, session: AsyncSession, product_id: Optional[str] = None) -> dict[str, Any]:
        """Implementation of get_summary with explicit session parameter.

        Returns:
            Summary data dictionary with task statistics

        Raises:
            ValidationError: No tenant context
        """
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

        return {"summary": summary, "total_products": len(summary), "total_tasks": len(tasks)}

    # ============================================================================
    # Permission Helpers (Handover 0322 Phase 3)
    # ============================================================================

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
