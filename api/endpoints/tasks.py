"""
Task Management API endpoints for Phase 4: Task-Centric Multi-User Dashboard.

Provides REST API for comprehensive task CRUD operations:
- GET /tasks - List tasks with user filtering
- POST /tasks - Create new task
- PATCH /tasks/{id} - Update task (permission-based)
- DELETE /tasks/{id} - Delete task (permission-based)
- POST /tasks/{id}/convert - Convert task to project

All endpoints enforce role-based access control and multi-tenant isolation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.dependencies import get_task_service
from api.schemas.task import (
    ProjectConversionResponse,
    StatusUpdate,
    TaskConversionRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Product, Task, User
from src.giljo_mcp.services.task_service import TaskService


logger = logging.getLogger(__name__)
router = APIRouter()


# Helper Functions


def can_modify_task(task: Task, user: User) -> bool:
    """
    Check if user can modify a task.

    Args:
        task: Task to check
        user: User attempting modification

    Returns:
        True if user can modify task, False otherwise

    Authorization rules (Handover 0076: removed assignment check):
    - Admins can modify any task in their tenant
    - Users can modify tasks they created
    """
    if user.role == "admin":
        return task.tenant_key == user.tenant_key

    return task.tenant_key == user.tenant_key and task.created_by_user_id == user.id


def can_delete_task(task: Task, user: User) -> bool:
    """
    Check if user can delete a task.

    Args:
        task: Task to check
        user: User attempting deletion

    Returns:
        True if user can delete task, False otherwise

    Authorization rules:
    - Admins can delete any task in their tenant
    - Users can only delete tasks they created
    """
    if user.role == "admin":
        return task.tenant_key == user.tenant_key

    return task.tenant_key == user.tenant_key and task.created_by_user_id == user.id


def task_to_response(task: Task) -> TaskResponse:
    """
    Convert Task model to TaskResponse schema.

    Args:
        task: Task model instance

    Returns:
        TaskResponse schema (Handover 0076: removed assignment fields)
    """
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        category=task.category,
        status=task.status,
        priority=task.priority,
        product_id=task.product_id,
        project_id=task.project_id,
        parent_task_id=task.parent_task_id,
        created_by_user_id=task.created_by_user_id,
        converted_to_project_id=task.converted_to_project_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        due_date=task.due_date,
        estimated_effort=task.estimated_effort,
        actual_effort=task.actual_effort,
    )


# API Endpoints


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    filter_type: Optional[str] = Query(None, description="Filter: 'product_tasks' | 'all_tasks'"),
    created_by_me: Optional[bool] = Query(None, description="Only tasks I created"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    product_id: Optional[str] = Query(None, description="Filter by product"),
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    """
    List tasks with product-scoped filtering (Handover 0076).

    Filter types:
    - 'product_tasks': Tasks for active product only
    - 'all_tasks': Tasks with product_id = NULL

    Args:
        filter_type: Filter preset ('product_tasks' or 'all_tasks')
        created_by_me: Only tasks created by current user
        status: Filter by task status
        priority: Filter by task priority
        project_id: Filter by project
        product_id: Filter by product
        current_user: Current authenticated user
        task_service: Task service instance

    Returns:
        List of TaskResponse objects

    Raises:
        ValidationError: No tenant context
        DatabaseError: Database operation failed
    """
    logger.debug(f"User {current_user.username} listing tasks (filter_type: {filter_type})")

    # Build filters for service call
    created_by_user_id = str(current_user.id) if created_by_me else None

    # Use TaskService.list_tasks() with enhanced filtering (Handover 0324)
    result = await task_service.list_tasks(
        filter_type=filter_type,
        product_id=product_id,
        project_id=project_id,
        status=status,
        priority=priority,
        created_by_user_id=created_by_user_id,
        tenant_key=current_user.tenant_key,
    )

    # Service returns list[Task] ORM objects directly (0731 typed returns)
    logger.info(f"Found {len(result)} tasks for user {current_user.username}")

    # Convert Task ORM objects to TaskResponse using helper
    return [task_to_response(task) for task in result]


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_create: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """
    Create a new task.

    The creator becomes the task owner. Product binding is required (Handover 0433)
    to ensure all tasks are isolated to a specific product.
    """
    logger.debug(f"User {getattr(current_user, 'username', 'unknown')} creating task '{task_create.title}'")

    # Validate the product exists, is active, and belongs to the user's tenant
    stmt = select(Product).where(
        and_(
            Product.id == task_create.product_id,
            Product.tenant_key == current_user.tenant_key,
            Product.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or does not belong to your tenant.",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active product set. Please activate a product before creating tasks.",
        )

    task = Task(
        tenant_key=current_user.tenant_key,
        product_id=task_create.product_id,
        project_id=task_create.project_id,
        parent_task_id=task_create.parent_task_id,
        title=task_create.title,
        description=task_create.description,
        category=task_create.category,
        status=task_create.status or "pending",
        priority=task_create.priority or "medium",
        estimated_effort=task_create.estimated_effort,
        actual_effort=task_create.actual_effort,
        due_date=task_create.due_date,
        created_by_user_id=current_user.id,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"Created task {task.id} by user {current_user.username}")
    return task_to_response(task)


@router.get("/summary")
@router.get("/summary/")
async def get_task_summary(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Return simple task summary metrics grouped by product for the current tenant.
    Structure is compatible with UI store expectations.

    NOTE: Route must be defined BEFORE /{task_id}/ to avoid FastAPI matching
    "summary" as a task_id parameter (route ordering matters in FastAPI).

    Raises:
        ValidationError: No tenant context
        DatabaseError: Database operation failed
    """
    data = await task_service.get_summary(product_id=product_id)

    return {
        "success": True,
        "summary": data["summary"],
        "total_products": data["total_products"],
        "total_tasks": data["total_tasks"],
    }


@router.get("/{task_id}/", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Get a single task by ID within the current tenant.

    Raises:
        ValidationError: No tenant context
        ResourceNotFoundError: Task not found
        DatabaseError: Database operation failed
    """
    task = await task_service.get_task(task_id)
    return task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
@router.put("/{task_id}/", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Update a task.

    Users can update:
    - Their own tasks (created_by_user_id == current_user.id)
    - Tasks assigned to them (assigned_to_user_id == current_user.id)

    Admins can update any task in their tenant.

    Args:
        task_id: Task ID to update
        task_update: Fields to update
        current_user: Current authenticated user
        task_service: Task service instance

    Returns:
        Updated task data

    Raises:
        HTTPException: 403 if user lacks permission
        HTTPException: 404 if task not found
    """
    logger.debug(f"User {current_user.username} updating task {task_id}")

    # First verify task exists and user has permission via get_task
    task = await task_service.get_task(task_id)

    # Simple permission check: admin or creator (Task ORM attribute access)
    if current_user.role != "admin" and str(task.created_by_user_id) != str(current_user.id):
        logger.warning(f"User {current_user.username} not authorized to update task {task_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task")

    # Use TaskService.update_task() to perform the update
    update_data = task_update.dict(exclude_unset=True)
    await task_service.update_task(task_id, **update_data)

    logger.info(f"Updated task {task_id} by user {current_user.username}")

    # Fetch updated task for response
    task = await task_service.get_task(task_id)
    return task_to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{task_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Delete a task.

    Only the creator or admin can delete tasks.

    Args:
        task_id: Task ID to delete
        current_user: Current authenticated user
        task_service: Task service instance

    Raises:
        ValidationError: No tenant context
        ResourceNotFoundError: Task not found
        AuthorizationError: User not authorized to delete task
        DatabaseError: Database operation failed
    """
    logger.debug(f"User {current_user.username} deleting task {task_id}")

    await task_service.delete_task(task_id, str(current_user.id))

    logger.info(f"Deleted task {task_id} by user {current_user.username}")


@router.post("/{task_id}/convert", response_model=ProjectConversionResponse)
@router.post("/{task_id}/convert/", response_model=ProjectConversionResponse)
async def convert_task_to_project(
    task_id: str,
    conversion_request: TaskConversionRequest,
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
) -> ProjectConversionResponse:
    """
    Convert a task to a project.

    This endpoint supports the TaskConverter frontend wizard.
    Only the task creator or admin can convert tasks.

    Args:
        task_id: Task ID to convert
        conversion_request: Conversion configuration
        current_user: Current authenticated user
        task_service: Task service instance

    Returns:
        Conversion result with new project details

    Raises:
        ValidationError: Task already converted or no active product
        ResourceNotFoundError: Task or user not found
        AuthorizationError: User not authorized
        DatabaseError: Database operation failed
    """
    logger.debug(f"User {current_user.username} converting task {task_id} to project")

    data = await task_service.convert_to_project(
        task_id=task_id,
        project_name=conversion_request.project_name,
        strategy=conversion_request.strategy,
        include_subtasks=conversion_request.include_subtasks,
        user_id=str(current_user.id),
    )

    logger.info(f"Converted task {task_id} to project {data.project_id} (strategy: {conversion_request.strategy})")

    return ProjectConversionResponse(
        project_id=data.project_id,
        project_name=data.project_name,
        original_task_id=data.task_id,
        conversion_strategy=conversion_request.strategy,
        created_at=datetime.now(timezone.utc),
    )


@router.patch("/{task_id}/status/", response_model=TaskResponse)
async def change_task_status(
    task_id: str,
    status_update: StatusUpdate,
    current_user: User = Depends(get_current_active_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Change only the status field of a task. Convenience endpoint for UI.

    Raises:
        ValidationError: No tenant context
        ResourceNotFoundError: Task not found
        DatabaseError: Database operation failed
    """
    task = await task_service.change_status(task_id, status_update.status)
    return task_to_response(task)
