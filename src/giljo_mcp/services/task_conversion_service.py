"""
TaskConversionService - Task-to-project conversion and summary operations.

Extracted from TaskService as part of the god-object refactoring (Handover 0950).

Responsibilities:
- Converting tasks to projects
- Summary statistics aggregation
- Deletion permission checks

Design Principles:
- Single Responsibility: Only conversion and summary domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging

Return Type Conventions (0731c):
- Conversion operations return ConversionResult
- Summary operations return dict (complex nested structure)
- Permission helpers return bool
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
from src.giljo_mcp.schemas.service_responses import ConversionResult
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class TaskConversionService:
    """
    Service for task conversion and summary operations.

    Handles:
    - Converting tasks to projects
    - Task summary statistics
    - Task deletion permission checks

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager = None,
        tenant_manager: TenantManager = None,
        session: AsyncSession | None = None,
    ):
        """
        Initialize TaskConversionService with database and tenant management.

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
    # Task Conversion
    # ============================================================================

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

    # ============================================================================
    # Summary Statistics
    # ============================================================================

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
