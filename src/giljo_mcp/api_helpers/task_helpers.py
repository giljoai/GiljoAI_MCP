"""
Task helper functions for API endpoints
Direct database operations without MCP tool decorators
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

# Initialize managers lazily
_db_manager = None
tenant_manager = TenantManager()


def get_db_manager():
    """Get or initialize database manager with URL from environment"""
    global _db_manager
    if _db_manager is None:
        import os

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        _db_manager = DatabaseManager(database_url=db_url, is_async=True)
    return _db_manager


async def create_task_for_api(
    title: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    priority: str = "medium",
    product_id: Optional[str] = None,
    project_id: Optional[str] = None,
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a new task with product isolation for API endpoints

    Args:
        title: Task title
        description: Task description
        category: Task category
        priority: Task priority (low, medium, high, critical)
        product_id: Product ID for isolation
        project_id: Project ID if associating with a project
        tenant_key: Tenant key for multi-tenancy

    Returns:
        Created task details or error
    """
    try:
        # Use current tenant if not provided
        if not tenant_key:
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                # For API calls, generate a default tenant if none exists
                tenant_key = str(uuid.uuid4())

        async with get_db_manager().get_session_async() as session:
            # If project_id is provided, get project and use its product_id
            if project_id:
                project_query = select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found",
                    }

            # Create task with product isolation
            task = Task(
                tenant_key=tenant_key,
                product_id=product_id,
                project_id=project_id or str(uuid.uuid4()),  # Default project if not provided
                title=title,
                description=description,
                category=category,
                priority=priority,
                status="pending",
            )

            session.add(task)
            await session.commit()

            logger.info(f"Created task {task.id} with product_id {product_id}")

            return {
                "success": True,
                "task_id": str(task.id),
                "title": task.title,
                "description": task.description,
                "product_id": task.product_id,
                "project_id": task.project_id,
                "category": task.category,
                "status": task.status,
                "priority": task.priority,
                "created_at": (
                    task.created_at.isoformat() if task.created_at else datetime.now(timezone.utc).isoformat()
                ),
            }

    except Exception as e:
        logger.exception(f"Failed to create task: {e}")
        return {"success": False, "error": str(e)}


async def list_tasks_for_api(
    product_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    List tasks with product isolation filtering for API endpoints

    Args:
        product_id: Filter by product ID
        project_id: Filter by project ID
        status: Filter by status
        priority: Filter by priority
        category: Filter by category
        limit: Maximum number of tasks to return
        tenant_key: Tenant key for filtering

    Returns:
        List of tasks matching filters
    """
    try:
        # Use current tenant if not provided
        if not tenant_key:
            tenant_key = tenant_manager.get_current_tenant()

        async with get_db_manager().get_session_async() as session:
            # Build query with filters
            query = select(Task)

            # Apply tenant filter if available
            if tenant_key:
                query = query.where(Task.tenant_key == tenant_key)

            # Apply product filter
            if product_id:
                query = query.where(Task.product_id == product_id)

            # Apply other filters
            if project_id:
                query = query.where(Task.project_id == project_id)
            if status:
                query = query.where(Task.status == status)
            if priority:
                query = query.where(Task.priority == priority)
            if category:
                query = query.where(Task.category == category)

            # Order by creation date and limit
            query = query.order_by(Task.created_at.desc()).limit(limit)

            result = await session.execute(query)
            tasks = result.scalars().all()

            task_list = []
            for task in tasks:
                task_list.append(
                    {
                        "id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "product_id": task.product_id,
                        "project_id": task.project_id,
                        "category": task.category,
                        "status": task.status,
                        "priority": task.priority,
                        "created_at": (task.created_at.isoformat() if task.created_at else None),
                        "started_at": (task.started_at.isoformat() if task.started_at else None),
                        "completed_at": (task.completed_at.isoformat() if task.completed_at else None),
                    }
                )

            return {
                "success": True,
                "count": len(task_list),
                "tasks": task_list,
                "filters": {
                    "product_id": product_id,
                    "project_id": project_id,
                    "status": status,
                    "priority": priority,
                    "category": category,
                },
            }

    except Exception as e:
        logger.exception(f"Failed to list tasks: {e}")
        return {"success": False, "error": str(e), "tasks": []}


async def update_task_for_api(
    task_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    description: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update a task (respects product isolation) for API endpoints

    Args:
        task_id: Task ID to update
        status: New status
        priority: New priority
        description: New description
        assigned_agent_id: Agent to assign task to
        tenant_key: Tenant key for validation

    Returns:
        Updated task details
    """
    try:
        # Use current tenant if not provided
        if not tenant_key:
            tenant_key = tenant_manager.get_current_tenant()

        async with get_db_manager().get_session_async() as session:
            # Query task
            task_query = select(Task).where(Task.id == task_id)

            # Apply tenant filter if available
            if tenant_key:
                task_query = task_query.where(Task.tenant_key == tenant_key)

            task_result = await session.execute(task_query)
            task = task_result.scalar_one_or_none()

            if not task:
                return {
                    "success": False,
                    "error": f"Task {task_id} not found or access denied",
                }

            # Update fields
            if status:
                task.status = status
                if status == "in_progress" and not task.started_at:
                    task.started_at = datetime.now(timezone.utc)
                elif status == "completed" and not task.completed_at:
                    task.completed_at = datetime.now(timezone.utc)

            if priority:
                task.priority = priority

            if description is not None:
                task.description = description

            if assigned_agent_id is not None:
                task.assigned_agent_id = assigned_agent_id

            await session.commit()

            return {
                "success": True,
                "task_id": str(task.id),
                "title": task.title,
                "product_id": task.product_id,
                "project_id": task.project_id,
                "status": task.status,
                "priority": task.priority,
                "updated": True,
            }

    except Exception as e:
        logger.exception(f"Failed to update task: {e}")
        return {"success": False, "error": str(e)}


async def get_product_task_summary_for_api(
    product_id: Optional[str] = None, tenant_key: Optional[str] = None
) -> dict[str, Any]:
    """
    Get task summary for a product or all products for API endpoints

    Args:
        product_id: Optional product ID to filter by
        tenant_key: Tenant key for filtering

    Returns:
        Task statistics grouped by product
    """
    try:
        # Use current tenant if not provided
        if not tenant_key:
            tenant_key = tenant_manager.get_current_tenant()

        async with get_db_manager().get_session_async() as session:
            # Build base query
            query = select(Task)

            # Apply tenant filter if available
            if tenant_key:
                query = query.where(Task.tenant_key == tenant_key)

            if product_id:
                query = query.where(Task.product_id == product_id)

            result = await session.execute(query)
            tasks = result.scalars().all()

            # Group by product
            product_stats = {}
            for task in tasks:
                pid = task.product_id or "no-product"
                if pid not in product_stats:
                    product_stats[pid] = {
                        "total": 0,
                        "pending": 0,
                        "in_progress": 0,
                        "completed": 0,
                        "blocked": 0,
                        "cancelled": 0,
                        "by_priority": {
                            "critical": 0,
                            "high": 0,
                            "medium": 0,
                            "low": 0,
                        },
                    }

                stats = product_stats[pid]
                stats["total"] += 1

                # Count by status
                task_status = task.status or "pending"
                if task_status in stats:
                    stats[task_status] += 1

                # Count by priority
                task_priority = task.priority or "medium"
                if task_priority in stats["by_priority"]:
                    stats["by_priority"][task_priority] += 1

            return {
                "success": True,
                "summary": product_stats,
                "total_products": len(product_stats),
                "total_tasks": len(tasks),
            }

    except Exception as e:
        logger.exception(f"Failed to get product task summary: {e}")
        return {"success": False, "error": str(e), "summary": {}}
