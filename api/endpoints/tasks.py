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
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.task import TaskUpdate, TaskConversionRequest, ProjectConversionResponse, TaskResponse
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Task, Project, User


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

    return (
        task.tenant_key == user.tenant_key and
        task.created_by_user_id == user.id
    )


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
        agent_job_id=task.agent_job_id,
        parent_task_id=task.parent_task_id,
        created_by_user_id=task.created_by_user_id,
        converted_to_project_id=task.converted_to_project_id,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        due_date=task.due_date,
        estimated_effort=task.estimated_effort,
        actual_effort=task.actual_effort
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
    db: AsyncSession = Depends(get_db_session)
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
        db: Database session

    Returns:
        List of TaskResponse objects
    """
    logger.debug(f"User {current_user.username} listing tasks (filter_type: {filter_type})")

    # Start with tenant filter (multi-tenant isolation)
    query = select(Task).where(Task.tenant_key == current_user.tenant_key)

    # Apply product-scoped filters (Handover 0076)
    if filter_type == "product_tasks":
        # Get active product for current tenant
        product_query = select(Product).where(
            Product.tenant_key == current_user.tenant_key,
            Product.is_active == True
        )
        product_result = await db.execute(product_query)
        active_product = product_result.scalar_one_or_none()

        if active_product:
            query = query.where(Task.product_id == active_product.id)
        else:
            # No active product, return empty list
            query = query.where(Task.id == None)  # Always false

    elif filter_type == "all_tasks":
        # Tasks with NULL product_id (created via MCP without active product)
        query = query.where(Task.product_id.is_(None))

    if created_by_me:
        query = query.where(Task.created_by_user_id == current_user.id)

    # Apply other filters
    if status:
        query = query.where(Task.status == status)

    if priority:
        query = query.where(Task.priority == priority)

    if project_id:
        query = query.where(Task.project_id == project_id)

    if product_id:
        query = query.where(Task.product_id == product_id)

    # Execute query
    query = query.order_by(Task.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    logger.info(f"Found {len(tasks)} tasks for user {current_user.username}")
    return [task_to_response(task) for task in tasks]


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
        db: Database session

    Returns:
        Updated task data

    Raises:
        HTTPException: 403 if user lacks permission
        HTTPException: 404 if task not found
    """
    logger.debug(f"User {current_user.username} updating task {task_id}")

    # Query task filtered by tenant (multi-tenant isolation)
    stmt = select(Task).where(Task.id == task_id, Task.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Task {task_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Permission check
    if not can_modify_task(task, current_user):
        logger.warning(f"User {current_user.username} not authorized to update task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Update fields (only update non-None values)
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # Update timestamps
    if "status" in update_data and update_data["status"] == "in_progress" and not task.started_at:
        task.started_at = datetime.now(timezone.utc)
    elif "status" in update_data and update_data["status"] == "completed" and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    logger.info(f"Updated task {task_id} by user {current_user.username}")
    return task_to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a task.

    Only the creator or admin can delete tasks.

    Args:
        task_id: Task ID to delete
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: 403 if user lacks permission
        HTTPException: 404 if task not found
    """
    logger.debug(f"User {current_user.username} deleting task {task_id}")

    # Query task filtered by tenant (multi-tenant isolation)
    stmt = select(Task).where(Task.id == task_id, Task.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Task {task_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Permission check
    if not can_delete_task(task, current_user):
        logger.warning(f"User {current_user.username} not authorized to delete task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only task creator or admin can delete"
        )

    await db.delete(task)
    await db.commit()

    logger.info(f"Deleted task {task_id} by user {current_user.username}")
    return None


@router.post("/{task_id}/convert", response_model=ProjectConversionResponse)
async def convert_task_to_project(
    task_id: str,
    conversion_request: TaskConversionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> ProjectConversionResponse:
    """
    Convert a task to a project.

    This endpoint supports the TaskConverter frontend wizard.
    Only the task creator or admin can convert tasks.

    Args:
        task_id: Task ID to convert
        conversion_request: Conversion configuration
        current_user: Current authenticated user
        db: Database session

    Returns:
        Conversion result with new project details

    Raises:
        HTTPException: 400 if task already converted
        HTTPException: 403 if user lacks permission
        HTTPException: 404 if task not found
    """
    logger.debug(f"User {current_user.username} converting task {task_id} to project")

    # Query task filtered by tenant (multi-tenant isolation)
    stmt = select(Task).where(Task.id == task_id, Task.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Task {task_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Check if already converted
    if task.converted_to_project_id:
        logger.warning(f"Task {task_id} already converted to project {task.converted_to_project_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task already converted to project {task.converted_to_project_id}"
        )

    # Permission check (only creator or admin can convert)
    if current_user.role != "admin" and task.created_by_user_id != current_user.id:
        logger.warning(f"User {current_user.username} not authorized to convert task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only task creator or admin can convert"
        )

    # Handover 0076: Get active product (required for project creation per Handover 0050)
    product_query = select(Product).where(
        Product.tenant_key == current_user.tenant_key,
        Product.is_active == True
    )
    product_result = await db.execute(product_query)
    active_product = product_result.scalar_one_or_none()

    if not active_product:
        logger.warning(f"No active product for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active product. Please activate a product before converting tasks to projects."
        )

    # Create project
    project_name = conversion_request.project_name or task.title
    project = Project(
        name=project_name,
        mission=task.description or f"Project created from task: {task.title}",
        product_id=active_product.id,
        tenant_key=current_user.tenant_key,
        status="active"
    )

    db.add(project)
    await db.flush()  # Get project ID without committing

    # Mark task as completed (converted) - Handover 0076
    task.converted_to_project_id = project.id
    task.status = "completed"  # Mark as completed, not 'converted'

    # Handle subtasks if requested
    if conversion_request.include_subtasks:
        stmt = select(Task).where(Task.parent_task_id == task_id)
        result = await db.execute(stmt)
        subtasks = result.scalars().all()

        for subtask in subtasks:
            subtask.project_id = project.id

    await db.commit()
    await db.refresh(project)

    logger.info(f"Converted task {task_id} to project {project.id} (strategy: {conversion_request.strategy})")

    return ProjectConversionResponse(
        project_id=project.id,
        project_name=project.name,
        original_task_id=task.id,
        conversion_strategy=conversion_request.strategy,
        created_at=project.created_at
    )
