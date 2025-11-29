"""
Task management tools with product isolation
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Project, Task

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
        Create a new task with product isolation (Handover 0076: removed user assignment)

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
            from giljo_mcp.tenant import tenant_manager

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

                # Create task with product isolation (Handover 0076: removed user assignment)
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
            from giljo_mcp.tenant import tenant_manager

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
            from giljo_mcp.tenant import tenant_manager

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
            from giljo_mcp.tenant import tenant_manager

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
            from giljo_mcp.tenant import tenant_manager

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
            from giljo_mcp.tenant import tenant_manager

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
            from giljo_mcp.tenant import tenant_manager

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
            from giljo_mcp.tenant import tenant_manager

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

    @mcp.tool()
    async def project_from_task(
        task_id: str,
        project_name: Optional[str] = None,
        conversion_strategy: str = "single",
        include_subtasks: bool = True,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Convert a task into a full project (Phase 4)

        This tool supports the TaskConverter frontend wizard which has 4 steps:
        1. Select tasks to convert
        2. Choose conversion strategy (single/individual/grouped)
        3. Configure project details
        4. Review and confirm

        Args:
            task_id: ID of task to convert
            project_name: Name for new project (defaults to task title)
            conversion_strategy: How to handle conversion
                - "single": Convert task to single project
                - "individual": Convert each subtask to separate project
                - "grouped": Group related subtasks into projects
            include_subtasks: Whether to include subtasks in conversion
            tenant_key: Tenant key for multi-tenancy

        Returns:
            Created project(s) with conversion metadata
        """
        try:
            from giljo_mcp.tenant import tenant_manager

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
                # Get task
                task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {
                        "success": False,
                        "error": f"Task {task_id} not found or access denied",
                    }

                # Check if already converted
                if task.converted_to_project_id:
                    return {
                        "success": False,
                        "error": f"Task {task_id} already converted to project {task.converted_to_project_id}",
                    }

                # Create project
                project = Project(
                    name=project_name or task.title,
                    mission=task.description or f"Converted from task: {task.title}",
                    product_id=task.product_id,
                    tenant_key=task.tenant_key,
                    status="active",
                )

                session.add(project)
                await session.flush()  # Get project.id

                # Mark task as converted
                task.converted_to_project_id = project.id
                task.status = "converted"

                # Update meta_data for backward compatibility
                if not task.meta_data:
                    task.meta_data = {}
                task.meta_data["converted_to_project"] = str(project.id)
                task.meta_data["conversion_strategy"] = conversion_strategy
                task.meta_data["converted_at"] = datetime.now(timezone.utc).isoformat()

                # Handle subtasks based on strategy
                converted_subtasks = []
                if include_subtasks and conversion_strategy != "individual":
                    subtasks_query = select(Task).where(Task.parent_task_id == task_id)
                    subtasks_result = await session.execute(subtasks_query)
                    subtasks = subtasks_result.scalars().all()

                    for subtask in subtasks:
                        # Convert subtask to project task or new project
                        if conversion_strategy == "single":
                            # Link subtask to new project
                            subtask.project_id = project.id
                            converted_subtasks.append(str(subtask.id))
                        elif conversion_strategy == "grouped":
                            # Group logic (can be enhanced later)
                            subtask.project_id = project.id
                            converted_subtasks.append(str(subtask.id))

                await session.commit()

                logger.info(f"Converted task {task_id} to project {project.id}")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "original_task_id": str(task.id),
                    "conversion_strategy": conversion_strategy,
                    "converted_subtasks": converted_subtasks,
                    "created_at": project.created_at.isoformat(),
                }

        except Exception as e:
            logger.exception(f"Failed to convert task to project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def list_my_tasks(
        filter_type: str = "created",
        status: Optional[str] = None,
        tenant_key: Optional[str] = None,
        current_user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        List tasks created by current user (Handover 0076: removed assignment filter)

        Args:
            filter_type: Type of tasks to list
                - "created": Tasks I created
                - "all": All tasks in tenant
            status: Optional status filter (pending, in_progress, completed, etc.)
            tenant_key: Tenant key for multi-tenancy
            current_user_id: Current user ID (usually from context)

        Returns:
            List of tasks with count
        """
        try:
            from giljo_mcp.tenant import tenant_manager

            # Use current tenant if not provided
            if not tenant_key:
                tenant_key = tenant_manager.get_current_tenant()
                if not tenant_key:
                    return {
                        "success": False,
                        "error": "No active project. Use switch_project first.",
                    }

            if not current_user_id:
                return {
                    "success": False,
                    "error": "current_user_id is required for filtering user tasks",
                }

            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                query = select(Task).where(Task.tenant_key == tenant_key)

                if filter_type == "created":
                    query = query.where(Task.created_by_user_id == current_user_id)
                # "all" filter type shows all tasks in tenant (no filter)

                if status:
                    query = query.where(Task.status == status)

                query = query.order_by(Task.created_at.desc())

                result = await session.execute(query)
                tasks = result.scalars().all()

                task_list = []
                for task in tasks:
                    task_list.append(
                        {
                            "id": str(task.id),
                            "title": task.title,
                            "description": task.description,
                            "status": task.status,
                            "priority": task.priority,
                            "created_by_user_id": task.created_by_user_id,
                            "project_id": task.project_id,
                            "product_id": task.product_id,
                            "created_at": task.created_at.isoformat(),
                        }
                    )

                return {
                    "success": True,
                    "tasks": task_list,
                    "count": len(task_list),
                    "filter_type": filter_type,
                }

        except Exception as e:
            logger.exception(f"Failed to list my tasks: {e}")
            return {"success": False, "error": str(e)}

    # Handover 0072: Slash command for quick task capture from CLI
    @mcp.prompt()
    async def task(context: str = "") -> str:
        """
        Quick task capture from conversation context (Handover 0072)

        Usage: /task <description>

        Creates a task from the command input. The first line becomes the title,
        remaining lines become the description. Priority and category are auto-detected
        from keywords.

        Args:
            context: Task description (user input after /task command)

        Returns:
            Confirmation message with task ID
        """
        try:
            from giljo_mcp.tenant import tenant_manager

            if not context or not context.strip():
                return """Usage: /task <description>

Example: /task Fix authentication bug in login flow"""

            # Split context into lines
            lines = context.strip().split("\n")

            # First line is the title (max 255 chars)
            title = lines[0].strip()[:255] if lines else "Task from CLI"

            # Remove markdown formatting from title
            title = title.replace("**", "").replace("*", "").replace("#", "").strip()

            # Rest is description
            description = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

            # Truncate description if too long
            if description and len(description) > 2000:
                description = description[:1997] + "..."

            # Determine priority based on keywords
            priority = "medium"
            context_lower = context.lower()
            if any(word in context_lower for word in ["critical", "urgent", "asap", "immediately", "blocker"]):
                priority = "high"
            elif any(word in context_lower for word in ["low", "minor", "nice to have", "optional", "someday"]):
                priority = "low"

            # Determine category based on content
            category = "general"
            if any(word in context_lower for word in ["bug", "fix", "error", "issue", "broken"]):
                category = "bug"
            elif any(word in context_lower for word in ["feature", "implement", "add", "create", "new"]):
                category = "feature"
            elif any(word in context_lower for word in ["document", "docs", "readme", "wiki"]):
                category = "documentation"
            elif any(word in context_lower for word in ["test", "testing", "verify", "qa"]):
                category = "testing"
            elif any(word in context_lower for word in ["refactor", "cleanup", "optimize", "improve"]):
                category = "refactoring"

            # Get current tenant (may be None for unassigned tasks)
            tenant_key = tenant_manager.get_current_tenant()

            # Get active product if available
            product_id = None
            if tenant_key:
                from giljo_mcp.models import Product

                db_manager = DatabaseManager(is_async=True)
                async with db_manager.get_session_async() as session:
                    product_query = select(Product).where(
                        and_(Product.tenant_key == tenant_key, Product.status == "active")
                    )
                    product_result = await session.execute(product_query)
                    active_product = product_result.scalar_one_or_none()

                    if active_product:
                        product_id = str(active_product.id)

            # Create task using the create_task tool (project_id will be None for unassigned)
            result = await create_task(
                title=title,
                description=description,
                category=category,
                priority=priority,
                tenant_key=tenant_key,
                product_id=product_id,
                project_id=None,  # Handover 0072: Allow unassigned tasks
            )

            if result.get("success"):
                task_id = result.get("task_id")
                scope_info = ""
                if product_id:
                    scope_info = "\nProduct: Active product"
                else:
                    scope_info = "\nScope: Unassigned (visible in all products)"

                return (
                    f"✅ Task created: '{title}\n"
                    f"Priority: {priority}\n"
                    f"Category: {category}\n"
                    f"ID: {task_id}"
                    f"{scope_info}\n\n"
                    f"Use 'assign_task_to_agent' to auto-spawn an agent job for this task."
                )
            error = result.get("error", "Unknown error")
            return f"❌ Failed to create task: {error}"

        except Exception as e:
            logger.exception(f"Failed to create task from slash command: {e}")
            return f"❌ Error creating task: {e!s}"

    # Handover 0072: Assign task to agent with auto-spawn
    @mcp.tool()
    async def assign_task_to_agent(
        task_id: str,
        agent_type: str,
        mission: Optional[str] = None,
        auto_spawn_job: bool = True,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Assign task to agent and optionally auto-spawn Job (Handover 0072)

        This tool links a task to an agent and creates an agent job for execution.
        Enables task-driven agent orchestration with automatic status synchronization.

        Args:
            task_id: Task ID to assign
            agent_type: Agent type (analyzer, implementer, tester, etc.)
            mission: Optional custom mission (defaults to task title + description)
            auto_spawn_job: Whether to auto-spawn Job (default: True)
            tenant_key: Tenant key for multi-tenancy

        Returns:
            Assignment result with agent job details if spawned
        """
        try:
            from giljo_mcp.agent_job_manager import AgentJobManager
            from giljo_mcp.tenant import tenant_manager

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
                # Get task
                task_query = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {
                        "success": False,
                        "error": f"Task {task_id} not found in tenant {tenant_key}",
                    }

                # Check if task already has an agent job
                if task.agent_job_id:
                    return {
                        "success": False,
                        "error": f"Task already assigned to agent job {task.agent_job_id}",
                        "existing_job_id": task.agent_job_id,
                    }

                # Check if task is converted
                if task.status == "converted":
                    return {
                        "success": False,
                        "error": "Cannot assign converted task to agent (task is now a project)",
                    }

                # Auto-spawn agent job (required for task assignment)
                job_id = None
                if auto_spawn_job:
                    # Build mission from task if not provided
                    if not mission:
                        mission = f"Task: {task.title}\n\n"
                        if task.description:
                            mission += f"Description:\n{task.description}\n\n"
                        mission += f"Priority: {task.priority}\n"
                        mission += f"Category: {task.category}\n"

                    # Create agent job using AgentJobManager
                    job_manager = AgentJobManager(tenant_key=tenant_key)

                    # Spawn agent job
                    job = await job_manager.create_job(
                        agent_type=agent_type,
                        mission=mission,
                        project_id=task.project_id,  # May be None for unassigned tasks
                        spawned_by=None,  # Human-initiated
                        context_chunks=[],
                    )

                    job_id = job.job_id

                    # Update task with assigned agent job
                    task.assigned_agent_id = job_id  # Now references MCPAgentJob.job_id
                    task.agent_job_id = job_id
                    task.status = "in_progress"
                    task.started_at = datetime.now(timezone.utc)

                    logger.info(
                        f"Created agent job {job_id} for task {task_id} (agent_type={agent_type}, tenant={tenant_key})"
                    )
                else:
                    # No job spawned - task remains unassigned
                    return {
                        "success": False,
                        "error": "auto_spawn_job must be True to assign task to agent",
                    }

                await session.commit()

                return {
                    "success": True,
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "assigned_agent_job_id": job_id,
                    "assigned_agent_type": agent_type,
                    "agent_job_id": job_id,
                    "job_spawned": auto_spawn_job,
                    "task_status": task.status,
                }

        except Exception as e:
            logger.exception(f"Failed to assign task to agent: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Task management tools registered successfully")


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
