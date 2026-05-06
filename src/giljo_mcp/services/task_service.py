# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.database import DatabaseManager
from giljo_mcp.domain.task_status import VALID_TASK_STATUSES
from giljo_mcp.exceptions import (
    AuthorizationError,
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.models import Task
from giljo_mcp.repositories.task_repository import TaskRepository
from giljo_mcp.schemas.service_responses import ConversionResult, TaskUpdateResult
from giljo_mcp.services.task_conversion_service import TaskConversionService
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

# Field allowlist for task updates — only these fields may be set via
# update_task().  Replaces the previous hasattr() gate which allowed setting
# any model attribute including id, tenant_key, created_at, etc.
_ALLOWED_TASK_UPDATE_FIELDS: frozenset[str] = frozenset(
    {
        "title",
        "description",
        "task_type_id",
        "status",
        "priority",
        "estimated_effort",
        "actual_effort",
        "due_date",
        "project_id",
        "parent_task_id",
        "converted_to_project_id",
    }
)


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
        self._repo = TaskRepository()
        self._conversion = TaskConversionService(db_manager, tenant_manager, session)

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
        task_type_id: str | None = None,
        priority: str = "medium",
        project_id: str | None = None,
        product_id: str | None = None,
        tenant_key: str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> str:
        """Quick task capture - logs a task with minimal information.

        Args:
            content: Task content (used as fallback for title and description)
            task_type_id: Optional taxonomy_types FK (resolved upstream from abbreviation)
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
            ...     task_type_id="abc-123",
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
                    task_type_id,
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
                    task_type_id,
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
        task_type_id: str | None,
        priority: str,
        project_id: str | None,
        product_id: str | None,
        tenant_key: str | None,
        title: str | None = None,
        description: str | None = None,
    ) -> str:
        """Implementation of log_task with explicit session parameter.

        Args:
            session: Database session
            content: Task content (used as fallback for title and description)
            task_type_id: Optional taxonomy_types FK (resolved upstream from abbreviation)
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
            project = await self._repo.get_project_by_id(session, project_id, product_id, tenant_key)

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
            task_type_id=task_type_id,
            priority=priority,
            status="pending",
        )

        await self._repo.add_and_commit(session, task)

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
        assigned_to: str | None = None,
        project_id: str | None = None,
        product_id: str | None = None,
        tenant_key: str | None = None,
        task_type_id: str | None = None,
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
            task_type_id=task_type_id,
        )

    # ============================================================================
    # Task Retrieval
    # ============================================================================

    async def list_tasks(
        self,
        status: str | None = None,
        assigned_to: str | None = None,
        project_id: str | None = None,
        product_id: str | None = None,
        priority: str | None = None,
        created_by_user_id: str | None = None,
        filter_type: str | None = None,
        tenant_key: str | None = None,
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
        status: str | None,
        project_id: str | None,
        product_id: str | None,
        priority: str | None,
        created_by_user_id: str | None,
        filter_type: str | None,
    ) -> list[Task]:
        """Implementation of list_tasks with explicit session parameter.

        Returns:
            List of Task ORM models

        Raises:
            ValidationError: No tenant context
        """
        # Start with tenant-scoped base query, eager-load task_type so callers
        # can read task.task_type.abbreviation outside the session.
        query = select(Task).options(selectinload(Task.task_type)).where(Task.tenant_key == tenant_key)

        # Handle special filter types (product-scoped filtering)
        if filter_type == "product_tasks":
            # Use explicit product_id if provided, otherwise get active product
            if product_id:
                query = query.where(Task.product_id == product_id)
            else:
                # Get active product for tenant
                active_product = await self._repo.get_active_product(session, tenant_key)

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
        return await self._repo.list_tasks(session, query)

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

        task = await self._repo.get_task_by_id(session, task_id, tenant_key)

        if not task:
            raise ResourceNotFoundError(
                message="Task not found or access denied",
                context={"task_id": task_id, "tenant_key": tenant_key},
            )

        # Update fields (allowlist-gated — see _ALLOWED_TASK_UPDATE_FIELDS)
        updated_fields = []
        for key, value in kwargs.items():
            if key in _ALLOWED_TASK_UPDATE_FIELDS:
                setattr(task, key, value)
                updated_fields.append(key)
            else:
                self._logger.warning(f"Rejected update to disallowed field '{key}' on task {task_id}")

        # Auto-update timestamps based on status changes (Handover 0324)
        if "status" in kwargs:
            new_status = kwargs["status"]
            now = datetime.now(UTC)

            if new_status == "in_progress" and not task.started_at:
                task.started_at = now
                updated_fields.append("started_at")
                self._logger.debug(f"Auto-set started_at for task {task_id}")

            elif new_status in ("completed", "cancelled") and not task.completed_at:
                task.completed_at = now
                updated_fields.append("completed_at")
                self._logger.debug(f"Auto-set completed_at for task {task_id}")

        await self._repo.commit(session)

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

        task = await self._repo.get_task_by_id(session, task_id, tenant_key)

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
        task = await self._repo.get_task_by_id(session, task_id, tenant_key)

        if not task:
            raise ResourceNotFoundError(
                message="Task not found", context={"task_id": task_id, "tenant_key": tenant_key}
            )

        # Get user for permission check
        user = await self._repo.get_user_by_id(session, user_id)

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Permission check
        if not self._conversion.can_delete_task(task, user):
            raise AuthorizationError(
                message="Not authorized to delete this task. Only task creator or admin can delete.",
                context={"task_id": task_id, "user_id": user_id},
            )

        # Delete task
        await self._repo.delete_and_commit(session, task)

        self._logger.info(f"Deleted task {task_id} by user {user_id}")

    async def convert_to_project(self, *a, **kw) -> ConversionResult:
        """Facade: delegates to TaskConversionService."""
        return await self._conversion.convert_to_project(*a, **kw)

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

        task = await self._repo.get_task_by_id(session, task_id, tenant_key)

        if not task:
            raise ResourceNotFoundError(
                message="Task not found", context={"task_id": task_id, "tenant_key": tenant_key}
            )

        # Update status
        task.status = new_status

        # Update timestamps based on status
        now = datetime.now(UTC)
        if new_status == "in_progress" and not task.started_at:
            task.started_at = now
        elif new_status in ("completed", "cancelled") and not task.completed_at:
            task.completed_at = now

        await self._repo.commit_and_refresh(session, task)

        self._logger.info(f"Changed task {task_id} status to {new_status}")

        return task

    async def get_summary(self, product_id: str | None = None) -> dict[str, Any]:
        """Facade: delegates to TaskConversionService."""
        return await self._conversion.get_summary(product_id)

    # ============================================================================
    # MCP Tool Methods (sprint 002f: pushed down from ToolAccessor)
    # ============================================================================

    async def create_task_for_mcp(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        task_type: str | None = None,
        assigned_to: str | None = None,
        tenant_key: str | None = None,
        db_manager: Any | None = None,
        websocket_manager: Any | None = None,
    ) -> dict[str, Any]:
        """Create a task via MCP tool (validation + active product resolution).

        Phase B (agent-parity): ``task_type`` replaces the old ``category``
        free-form string. Validation goes through TaxonomyService; unknown
        abbreviations raise ValidationError with the valid_types payload.
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        effective_db = db_manager or self.db_manager

        from giljo_mcp.services.product_service import ProductService
        from giljo_mcp.services.taxonomy_service import TaxonomyService

        task_type_id: str | None = None
        resolved_type_label = ""
        if task_type and task_type.strip():
            taxonomy = TaxonomyService(db_manager=effective_db, session=self._session)
            resolved_type = await taxonomy.validate(task_type.strip(), effective_tenant_key)
            task_type_id = resolved_type.id
            resolved_type_label = resolved_type.abbreviation

        product_service = ProductService(
            db_manager=effective_db,
            tenant_key=effective_tenant_key,
            websocket_manager=websocket_manager,
            test_session=self._session,
        )
        active_product = await product_service.get_active_product()

        if not active_product:
            raise ValidationError(
                "No active product set. Please activate a product first.",
                context={"tenant_key": effective_tenant_key, "operation": "create_task"},
            )

        product_id = active_product.id

        task_id = await self.log_task(
            content=title,
            title=title,
            description=description,
            task_type_id=task_type_id,
            priority=priority,
            product_id=product_id,
            tenant_key=effective_tenant_key,
        )

        self._logger.info(
            "Created task %s for tenant %s in product %s",
            task_id,
            effective_tenant_key,
            product_id,
        )

        if websocket_manager:
            try:
                await websocket_manager.broadcast_to_tenant(
                    tenant_key=effective_tenant_key,
                    event_type="task:created",
                    data={"task_id": task_id, "title": title, "product_id": product_id},
                )
            except (RuntimeError, ValueError, OSError) as e:
                self._logger.warning(f"Failed to broadcast task:created event: {e}")

        response: dict[str, Any] = {
            "success": True,
            "task_id": task_id,
            "title": title,
            "priority": priority,
            "task_type": resolved_type_label,
            "product_id": product_id,
            "message": f"Task '{title}' created successfully",
        }
        if not task_type:
            taxonomy = TaxonomyService(db_manager=effective_db, session=self._session)
            response["valid_types"] = await taxonomy._valid_types_payload(effective_tenant_key)
        return response

    async def update_task_for_mcp(
        self,
        task_id: str,
        tenant_key: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        due_date: Any = None,
        project_id: str | None = None,
        estimated_effort: float | None = None,
        actual_effort: float | None = None,
    ) -> dict[str, Any]:
        """Update a task via the MCP surface. Phase C; mirrors update_project.

        Only fields actually supplied (non-None) are written; the underlying
        ``update_task`` enforces the field allowlist (post-0962 write
        discipline). Unknown ``task_type`` abbreviations are rejected via
        TaxonomyService.validate before any write happens.
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        if not effective_tenant_key:
            raise ValidationError(
                message="tenant_key is required",
                context={"operation": "update_task_for_mcp", "task_id": task_id},
            )

        if status is not None and status not in VALID_TASK_STATUSES:
            valid_status_values = sorted(s.value for s in VALID_TASK_STATUSES)
            raise ValidationError(
                message=f"Unknown task status '{status}'. Valid statuses: {valid_status_values}",
                context={
                    "operation": "update_task_for_mcp",
                    "task_id": task_id,
                    "valid_statuses": valid_status_values,
                },
            )

        update_kwargs: dict[str, Any] = {}
        if title is not None:
            update_kwargs["title"] = title
        if description is not None:
            update_kwargs["description"] = description
        if status is not None:
            update_kwargs["status"] = status
        if priority is not None:
            update_kwargs["priority"] = priority
        if due_date is not None:
            update_kwargs["due_date"] = due_date
        if project_id is not None:
            update_kwargs["project_id"] = project_id
        if estimated_effort is not None:
            update_kwargs["estimated_effort"] = estimated_effort
        if actual_effort is not None:
            update_kwargs["actual_effort"] = actual_effort

        if task_type is not None:
            if task_type == "":
                update_kwargs["task_type_id"] = None
            else:
                from giljo_mcp.services.taxonomy_service import TaxonomyService

                taxonomy = TaxonomyService(db_manager=self.db_manager, session=self._session)
                resolved = await taxonomy.validate(task_type.strip(), effective_tenant_key)
                update_kwargs["task_type_id"] = resolved.id

        if not update_kwargs:
            return {
                "task_id": task_id,
                "updated_fields": [],
                "message": "No fields supplied; nothing to update.",
            }

        # Route through update_task; it owns the allowlist and timestamp logic.
        # update_task pulls tenant from tenant_manager — set it explicitly so
        # tenant_key parameter wins on the MCP-tool path.
        previous = self.tenant_manager.get_current_tenant() if self.tenant_manager else None
        try:
            if self.tenant_manager:
                self.tenant_manager.set_current_tenant(effective_tenant_key)
            result = await self.update_task(task_id, **update_kwargs)
        finally:
            if self.tenant_manager and previous is not None:
                self.tenant_manager.set_current_tenant(previous)

        return {
            "task_id": result.task_id,
            "updated_fields": list(result.updated_fields),
            "message": f"Task {result.task_id} updated: {sorted(result.updated_fields)}",
        }

    async def complete_task_for_mcp(
        self,
        task_id: str,
        tenant_key: str | None = None,
        completion_notes: str | None = None,
    ) -> dict[str, Any]:
        """Mark a task completed (status + completed_at + optional notes).

        Phase C of agent-parity. Tenant-scoped, TaskService-routed; identical
        write discipline to ``update_task_for_mcp``. ``completion_notes``,
        when provided, is appended to the description so the audit trail keeps
        a record without introducing a new column.
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        if not effective_tenant_key:
            raise ValidationError(
                message="tenant_key is required",
                context={"operation": "complete_task", "task_id": task_id},
            )

        task = await self._change_status_with_tenant(task_id, "completed", effective_tenant_key)

        if completion_notes:
            await self._append_completion_notes(task_id, effective_tenant_key, completion_notes)

        return {
            "task_id": task_id,
            "status": task.status,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "completion_notes": completion_notes,
            "message": f"Task {task_id} marked completed",
        }

    async def list_tasks_for_mcp(
        self,
        tenant_key: str | None = None,
        mode: str = "summary",
        status: str | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        due_before: Any = None,
        summary_only: bool | None = None,
        memory_limit: int | None = None,
    ) -> dict[str, Any]:
        """List tasks for the current tenant with summary/full projection modes.

        Phase D of agent-parity. Two modes only:

        - ``summary``: id, title, status, priority, task_type, due_date,
          created_at — keeps the response under ~80 lines for a typical
          ~50-task corpus.
        - ``full``: every column on Task plus an embedded task_type block.
          ``memory_limit`` truncates description if set.

        Filters: status, priority, task_type (abbreviation), due_before.
        Every query filters by tenant_key; cross-tenant tasks are never
        visible.
        """
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        if not effective_tenant_key:
            raise ValidationError(
                message="tenant_key is required",
                context={"operation": "list_tasks_for_mcp"},
            )

        if summary_only is True:
            mode = "summary"
        elif summary_only is False:
            mode = "full"
        if mode not in {"summary", "full"}:
            raise ValidationError(
                message=f"Unknown mode '{mode}'. Valid modes: summary, full",
                context={"operation": "list_tasks_for_mcp", "mode": mode},
            )

        task_type_id: str | None = None
        if task_type:
            from giljo_mcp.services.taxonomy_service import TaxonomyService

            taxonomy = TaxonomyService(db_manager=self.db_manager, session=self._session)
            resolved = await taxonomy.validate(task_type.strip(), effective_tenant_key)
            task_type_id = resolved.id

        if self._session:
            tasks = await self._list_tasks_for_mcp_impl(
                self._session,
                effective_tenant_key,
                status=status,
                priority=priority,
                task_type_id=task_type_id,
                due_before=due_before,
            )
        else:
            async with self._get_session() as session:
                tasks = await self._list_tasks_for_mcp_impl(
                    session,
                    effective_tenant_key,
                    status=status,
                    priority=priority,
                    task_type_id=task_type_id,
                    due_before=due_before,
                )

        if mode == "summary":
            rows = [self._task_to_summary_row(t) for t in tasks]
        else:
            rows = [self._task_to_full_row(t, memory_limit=memory_limit) for t in tasks]

        return {
            "tasks": rows,
            "count": len(rows),
            "mode": mode,
            "tenant_key": effective_tenant_key,
        }

    # ------------------------------------------------------------------
    # MCP-task helpers (private)
    # ------------------------------------------------------------------

    async def _change_status_with_tenant(self, task_id: str, new_status: str, tenant_key: str) -> Task:
        """Tenant-explicit variant of change_status. Routes through repo."""

        async def _do(session: AsyncSession) -> Task:
            task = await self._repo.get_task_by_id(session, task_id, tenant_key)
            if not task:
                raise ResourceNotFoundError(
                    message="Task not found",
                    context={"task_id": task_id, "tenant_key": tenant_key},
                )
            task.status = new_status
            now = datetime.now(UTC)
            if new_status == "in_progress" and not task.started_at:
                task.started_at = now
            elif new_status in ("completed", "cancelled") and not task.completed_at:
                task.completed_at = now
            await self._repo.commit_and_refresh(session, task)
            self._logger.info("Task %s status -> %s (tenant=%s)", task_id, new_status, tenant_key)
            return task

        if self._session:
            return await _do(self._session)
        async with self._get_session() as session:
            return await _do(session)

    async def append_completion_notes(self, task_id: str, notes: str) -> None:
        """Public entry point for appending completion notes (REST PATCH path).

        Resolves tenant from TenantManager (matches the rest of the public
        TaskService surface). Delegates to ``_append_completion_notes`` so the
        REST and MCP paths share a single audit-trail format.
        """
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="tenant_key is required",
                context={"operation": "append_completion_notes", "task_id": task_id},
            )
        await self._append_completion_notes(task_id, tenant_key, notes)

    async def _append_completion_notes(self, task_id: str, tenant_key: str, notes: str) -> None:
        """Append completion notes to the task description (audit trail)."""

        async def _do(session: AsyncSession) -> None:
            task = await self._repo.get_task_by_id(session, task_id, tenant_key)
            if not task:
                return
            stamped = f"\n\n[completed {datetime.now(UTC).isoformat()}] {notes}"
            task.description = (task.description or "") + stamped
            await self._repo.commit_and_refresh(session, task)

        if self._session:
            await _do(self._session)
            return
        async with self._get_session() as session:
            await _do(session)

    async def _list_tasks_for_mcp_impl(
        self,
        session: AsyncSession,
        tenant_key: str,
        *,
        status: str | None,
        priority: str | None,
        task_type_id: str | None,
        due_before: Any,
    ) -> list[Task]:
        stmt = (
            select(Task)
            .options(selectinload(Task.task_type))
            .where(Task.tenant_key == tenant_key)
            .order_by(Task.created_at.desc())
        )
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if task_type_id:
            stmt = stmt.where(Task.task_type_id == task_type_id)
        if due_before is not None:
            stmt = stmt.where(Task.due_date < due_before)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _task_to_summary_row(task: Task) -> dict[str, Any]:
        return {
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "task_type": task.task_type.abbreviation if task.task_type else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }

    @staticmethod
    def _task_to_full_row(task: Task, *, memory_limit: int | None) -> dict[str, Any]:
        description = task.description or ""
        if memory_limit and len(description) > memory_limit:
            description = description[:memory_limit] + "..."
        return {
            "task_id": str(task.id),
            "title": task.title,
            "description": description,
            "status": task.status,
            "priority": task.priority,
            "task_type": (
                {
                    "id": task.task_type.id,
                    "abbreviation": task.task_type.abbreviation,
                    "label": task.task_type.label,
                    "color": task.task_type.color,
                }
                if task.task_type
                else None
            ),
            "task_type_id": task.task_type_id,
            "product_id": task.product_id,
            "project_id": task.project_id,
            "parent_task_id": task.parent_task_id,
            "estimated_effort": task.estimated_effort,
            "actual_effort": task.actual_effort,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
