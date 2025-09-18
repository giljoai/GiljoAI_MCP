"""
Task management tools with product isolation
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Task

from .task_templates import register_task_template_tools


logger = logging.getLogger(__name__)


def register_task_tools(mcp):
    """Register task management tools with product isolation"""

    @mcp.tool()
    async def create_task(
        title: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        priority: str = "medium",
        tenant_key: Optional[str] = None,
        product_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new task with product isolation

        Args:
            title: Task title
            description: Task description
            category: Task category
            priority: Task priority (low, medium, high, critical)
            tenant_key: Tenant key for multi-tenancy
            product_id: Product ID for product isolation
            project_id: Project ID if associating with a project

        Returns:
            Created task details
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            # Use current tenant if not provided
            if not tenant_key:
                tenant_key = tenant_manager.get_current_tenant()
                if not tenant_key:
                    return {
                        "success": False,
                        "error": "No active project. Use switch_project first.",
                    }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # If project_id is provided, get project and use its product_id
                if project_id:
                    project_query = select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == tenant_key)
                    )
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()

                    if not project:
                        return {
                            "success": False,
                            "error": f"Project {project_id} not found",
                        }

                    # Use project's product_id if not explicitly provided
                    if not product_id and hasattr(project, "product_id"):
                        product_id = project.product_id

                # Create task with product isolation
                task = Task(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    project_id=project_id,
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
                    "product_id": task.product_id,
                    "project_id": task.project_id,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat(),
                }

        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def list_tasks(
        product_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        List tasks with product isolation filtering

        Args:
            product_id: Filter by product ID
            project_id: Filter by project ID
            status: Filter by status
            priority: Filter by priority
            category: Filter by category
            limit: Maximum number of tasks to return

        Returns:
            List of tasks matching filters
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Build query with filters
                query = select(Task).where(Task.tenant_key == tenant_key)

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
                            "created_at": task.created_at.isoformat(),
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
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def update_task(
        task_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update a task (respects product isolation)

        Args:
            task_id: Task ID to update
            status: New status
            priority: New priority
            description: New description
            assigned_agent_id: Agent to assign task to

        Returns:
            Updated task details
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Query task with tenant isolation
                task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
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

    @mcp.tool()
    async def get_product_task_summary(
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get task summary for a product or all products

        Args:
            product_id: Optional product ID to filter by

        Returns:
            Task statistics grouped by product
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Build base query
                query = select(Task).where(Task.tenant_key == tenant_key)

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
                    stats[task.status] = stats.get(task.status, 0) + 1
                    stats["by_priority"][task.priority] = stats["by_priority"].get(task.priority, 0) + 1

                return {
                    "success": True,
                    "summary": product_stats,
                    "total_products": len(product_stats),
                    "total_tasks": len(tasks),
                }

        except Exception as e:
            logger.exception(f"Failed to get product task summary: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_task_dependencies(
        task_id: str,
        include_subtasks: bool = True,
        include_parent: bool = True,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """
        Get task dependency relationships for visualization and management

        Args:
            task_id: Task ID to analyze
            include_subtasks: Include child tasks
            include_parent: Include parent task
            max_depth: Maximum depth to traverse

        Returns:
            Task dependency tree with relationships
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Get the main task
                main_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                main_result = await session.execute(main_query)
                main_task = main_result.scalar_one_or_none()

                if not main_task:
                    return {"success": False, "error": f"Task {task_id} not found"}

                dependency_tree = {
                    "main_task": {
                        "id": str(main_task.id),
                        "title": main_task.title,
                        "status": main_task.status,
                        "priority": main_task.priority,
                        "parent_task_id": main_task.parent_task_id,
                    },
                    "dependencies": {
                        "parent_chain": [],
                        "child_tasks": [],
                        "sibling_tasks": [],
                    },
                }

                # Get parent chain if requested
                if include_parent and main_task.parent_task_id:
                    parent_chain = await _get_parent_chain(session, main_task.parent_task_id, tenant_key, max_depth)
                    dependency_tree["dependencies"]["parent_chain"] = parent_chain

                # Get child tasks if requested
                if include_subtasks:
                    child_tasks = await _get_child_tasks(session, task_id, tenant_key, max_depth)
                    dependency_tree["dependencies"]["child_tasks"] = child_tasks

                # Get sibling tasks (tasks with same parent)
                if main_task.parent_task_id:
                    sibling_query = select(Task).where(
                        and_(
                            Task.parent_task_id == main_task.parent_task_id,
                            Task.tenant_key == tenant_key,
                            Task.id != task_id,
                        )
                    )
                    sibling_result = await session.execute(sibling_query)
                    siblings = sibling_result.scalars().all()

                    for sibling in siblings:
                        dependency_tree["dependencies"]["sibling_tasks"].append(
                            {
                                "id": str(sibling.id),
                                "title": sibling.title,
                                "status": sibling.status,
                                "priority": sibling.priority,
                            }
                        )

                return {
                    "success": True,
                    "dependency_tree": dependency_tree,
                    "analysis": {
                        "has_dependencies": bool(dependency_tree["dependencies"]["parent_chain"]),
                        "has_subtasks": bool(dependency_tree["dependencies"]["child_tasks"]),
                        "has_siblings": bool(dependency_tree["dependencies"]["sibling_tasks"]),
                        "total_related": (
                            len(dependency_tree["dependencies"]["parent_chain"])
                            + len(dependency_tree["dependencies"]["child_tasks"])
                            + len(dependency_tree["dependencies"]["sibling_tasks"])
                        ),
                    },
                }

        except Exception as e:
            logger.exception(f"Failed to get task dependencies: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def bulk_update_tasks(
        task_ids: list[str], updates: dict[str, Any], operation_type: str = "update"
    ) -> dict[str, Any]:
        """
        Perform bulk operations on multiple tasks

        Args:
            task_ids: List of task IDs to update
            updates: Dictionary of field updates to apply
            operation_type: Type of operation (update, reorder, batch_convert)

        Returns:
            Results of bulk operation with success/failure details
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                results = {
                    "operation_type": operation_type,
                    "total_tasks": len(task_ids),
                    "successful": [],
                    "failed": [],
                    "summary": {},
                }

                for task_id in task_ids:
                    try:
                        # Get task with tenant isolation
                        task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                        task_result = await session.execute(task_query)
                        task = task_result.scalar_one_or_none()

                        if not task:
                            results["failed"].append(
                                {
                                    "task_id": task_id,
                                    "error": "Task not found or access denied",
                                }
                            )
                            continue

                        # Apply updates
                        updated_fields = []
                        for field, value in updates.items():
                            if hasattr(task, field):
                                old_value = getattr(task, field)
                                setattr(task, field, value)
                                updated_fields.append(f"{field}: {old_value} -> {value}")

                        # Handle special operations
                        if operation_type == "reorder" and "parent_task_id" in updates:
                            # Validate parent task exists
                            if updates["parent_task_id"]:
                                parent_query = select(Task).where(
                                    and_(
                                        Task.id == updates["parent_task_id"],
                                        Task.tenant_key == tenant_key,
                                    )
                                )
                                parent_result = await session.execute(parent_query)
                                if not parent_result.scalar_one_or_none():
                                    results["failed"].append(
                                        {
                                            "task_id": task_id,
                                            "error": f"Parent task {updates['parent_task_id']} not found",
                                        }
                                    )
                                    continue

                        results["successful"].append(
                            {
                                "task_id": task_id,
                                "title": task.title,
                                "updated_fields": updated_fields,
                            }
                        )

                    except Exception as task_error:
                        results["failed"].append({"task_id": task_id, "error": str(task_error)})

                # Commit all successful changes
                if results["successful"]:
                    await session.commit()

                results["summary"] = {
                    "successful_count": len(results["successful"]),
                    "failed_count": len(results["failed"]),
                    "success_rate": (len(results["successful"]) / len(task_ids) if task_ids else 0),
                }

                return {"success": True, "results": results}

        except Exception as e:
            logger.exception(f"Failed bulk task operation: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def create_task_conversion_history(
        original_task_id: str,
        converted_project_id: str,
        conversion_type: str = "task_to_project",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Create conversion history entry tracking task-to-project conversions

        Args:
            original_task_id: ID of the original task
            converted_project_id: ID of the created project
            conversion_type: Type of conversion performed
            metadata: Additional conversion metadata

        Returns:
            Conversion history entry details
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Verify original task exists
                task_query = select(Task).where(and_(Task.id == original_task_id, Task.tenant_key == tenant_key))
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {
                        "success": False,
                        "error": f"Original task {original_task_id} not found",
                    }

                # Update task metadata to include conversion history
                if not task.meta_data:
                    task.meta_data = {}

                conversion_entry = {
                    "conversion_id": str(uuid4()),
                    "converted_to_project_id": converted_project_id,
                    "conversion_type": conversion_type,
                    "converted_at": datetime.now(timezone.utc).isoformat(),
                    "original_title": task.title,
                    "original_status": task.status,
                    "original_priority": task.priority,
                    "metadata": metadata or {},
                }

                if "conversion_history" not in task.meta_data:
                    task.meta_data["conversion_history"] = []

                task.meta_data["conversion_history"].append(conversion_entry)

                # Mark task as converted
                task.status = "converted"
                task.meta_data["converted_to_project"] = converted_project_id

                await session.commit()

                return {
                    "success": True,
                    "conversion_id": conversion_entry["conversion_id"],
                    "original_task": {
                        "id": str(task.id),
                        "title": task.title,
                        "status": task.status,
                    },
                    "converted_project_id": converted_project_id,
                    "conversion_type": conversion_type,
                    "conversion_history": task.meta_data["conversion_history"],
                }

        except Exception as e:
            logger.exception(f"Failed to create conversion history: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_conversion_history(
        task_id: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50
    ) -> dict[str, Any]:
        """
        Get conversion history for tasks or find tasks converted to specific projects

        Args:
            task_id: Get conversion history for specific task
            project_id: Find tasks converted to specific project
            limit: Maximum number of entries to return

        Returns:
            Conversion history entries
        """
        try:
            from src.giljo_mcp.tenant import tenant_manager

            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first.",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                if task_id:
                    # Get specific task conversion history
                    task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                    task_result = await session.execute(task_query)
                    task = task_result.scalar_one_or_none()

                    if not task:
                        return {"success": False, "error": f"Task {task_id} not found"}

                    conversion_history = task.meta_data.get("conversion_history", []) if task.meta_data else []

                    return {
                        "success": True,
                        "task_id": task_id,
                        "task_title": task.title,
                        "conversion_history": conversion_history,
                        "has_conversions": len(conversion_history) > 0,
                    }

                if project_id:
                    # Find all tasks converted to this project
                    query = (
                        select(Task)
                        .where(
                            and_(
                                Task.tenant_key == tenant_key,
                                Task.meta_data.contains({"converted_to_project": project_id}),
                            )
                        )
                        .limit(limit)
                    )

                    result = await session.execute(query)
                    tasks = result.scalars().all()

                    converted_tasks = []
                    for task in tasks:
                        conversion_history = task.meta_data.get("conversion_history", []) if task.meta_data else []
                        converted_tasks.append(
                            {
                                "id": str(task.id),
                                "title": task.title,
                                "original_status": task.status,
                                "conversion_history": conversion_history,
                            }
                        )

                    return {
                        "success": True,
                        "project_id": project_id,
                        "converted_tasks": converted_tasks,
                        "total_converted": len(converted_tasks),
                    }

                # Get all recent conversions
                query = (
                    select(Task)
                    .where(
                        and_(
                            Task.tenant_key == tenant_key,
                            Task.status == "converted",
                        )
                    )
                    .order_by(Task.updated_at.desc())
                    .limit(limit)
                )

                result = await session.execute(query)
                tasks = result.scalars().all()

                recent_conversions = []
                for task in tasks:
                    conversion_history = task.meta_data.get("conversion_history", []) if task.meta_data else []
                    if conversion_history:
                        latest_conversion = conversion_history[-1]
                        recent_conversions.append(
                            {
                                "task_id": str(task.id),
                                "task_title": task.title,
                                "converted_to_project_id": latest_conversion.get("converted_to_project_id"),
                                "conversion_type": latest_conversion.get("conversion_type"),
                                "converted_at": latest_conversion.get("converted_at"),
                            }
                        )

                return {
                    "success": True,
                    "recent_conversions": recent_conversions,
                    "total_found": len(recent_conversions),
                }

        except Exception as e:
            logger.exception(f"Failed to get conversion history: {e}")
            return {"success": False, "error": str(e)}

    # Register template integration tools
    register_task_template_tools(mcp)

    logger.info("Task management tools with templates registered successfully")


# Helper functions for dependency mapping
async def _get_parent_chain(
    session, parent_id: str, tenant_key: str, max_depth: int, current_depth: int = 0
) -> list[dict[str, Any]]:
    """Recursively get parent task chain"""
    if current_depth >= max_depth:
        return []

    parent_query = select(Task).where(and_(Task.id == parent_id, Task.tenant_key == tenant_key))
    parent_result = await session.execute(parent_query)
    parent = parent_result.scalar_one_or_none()

    if not parent:
        return []

    parent_info = {
        "id": str(parent.id),
        "title": parent.title,
        "status": parent.status,
        "priority": parent.priority,
        "depth": current_depth,
    }

    chain = [parent_info]
    if parent.parent_task_id:
        chain.extend(await _get_parent_chain(session, parent.parent_task_id, tenant_key, max_depth, current_depth + 1))

    return chain


async def _get_child_tasks(
    session, parent_id: str, tenant_key: str, max_depth: int, current_depth: int = 0
) -> list[dict[str, Any]]:
    """Recursively get child task tree"""
    if current_depth >= max_depth:
        return []

    children_query = select(Task).where(and_(Task.parent_task_id == parent_id, Task.tenant_key == tenant_key))
    children_result = await session.execute(children_query)
    children = children_result.scalars().all()

    child_tree = []
    for child in children:
        child_info = {
            "id": str(child.id),
            "title": child.title,
            "status": child.status,
            "priority": child.priority,
            "depth": current_depth,
            "children": await _get_child_tasks(session, str(child.id), tenant_key, max_depth, current_depth + 1),
        }
        child_tree.append(child_info)

    return child_tree
