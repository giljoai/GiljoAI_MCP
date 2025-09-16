"""
Task management tools with product isolation
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from giljo_mcp.models import Task, Project
from giljo_mcp.database import DatabaseManager

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
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
            from giljo_mcp.tenant import tenant_manager
            
            # Use current tenant if not provided
            if not tenant_key:
                tenant_key = tenant_manager.get_current_tenant()
                if not tenant_key:
                    return {
                        "success": False,
                        "error": "No active project. Use switch_project first."
                    }
            
            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # If project_id is provided, get project and use its product_id
                if project_id:
                    project_query = select(Project).where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == tenant_key
                        )
                    )
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()
                    
                    if not project:
                        return {
                            "success": False,
                            "error": f"Project {project_id} not found"
                        }
                    
                    # Use project's product_id if not explicitly provided
                    if not product_id and hasattr(project, 'product_id'):
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
                    status="pending"
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
                    "created_at": task.created_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def list_tasks(
        product_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
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
                    "error": "No active project. Use switch_project first."
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
                    task_list.append({
                        "id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "product_id": task.product_id,
                        "project_id": task.project_id,
                        "category": task.category,
                        "status": task.status,
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat(),
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None
                    })
                
                return {
                    "success": True,
                    "count": len(task_list),
                    "tasks": task_list,
                    "filters": {
                        "product_id": product_id,
                        "project_id": project_id,
                        "status": status,
                        "priority": priority,
                        "category": category
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def update_task(
        task_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
        assigned_agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
                    "error": "No active project. Use switch_project first."
                }
            
            db_manager = DatabaseManager(is_async=True)
            async with db_manager.get_session_async() as session:
                # Query task with tenant isolation
                task_query = select(Task).where(
                    and_(
                        Task.id == task_id,
                        Task.tenant_key == tenant_key
                    )
                )
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()
                
                if not task:
                    return {
                        "success": False,
                        "error": f"Task {task_id} not found or access denied"
                    }
                
                # Update fields
                if status:
                    task.status = status
                    if status == "in_progress" and not task.started_at:
                        task.started_at = datetime.utcnow()
                    elif status == "completed" and not task.completed_at:
                        task.completed_at = datetime.utcnow()
                
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
                    "updated": True
                }
                
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def get_product_task_summary(
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
                    "error": "No active project. Use switch_project first."
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
                                "low": 0
                            }
                        }
                    
                    stats = product_stats[pid]
                    stats["total"] += 1
                    stats[task.status] = stats.get(task.status, 0) + 1
                    stats["by_priority"][task.priority] = stats["by_priority"].get(task.priority, 0) + 1
                
                return {
                    "success": True,
                    "summary": product_stats,
                    "total_products": len(product_stats),
                    "total_tasks": len(tasks)
                }
                
        except Exception as e:
            logger.error(f"Failed to get product task summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    logger.info("Task management tools registered successfully")