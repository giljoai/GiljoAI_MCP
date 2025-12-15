"""
Task management tools with product isolation

Handover Note: Task MCP tools retired (Dec 2025)
- Removed: list_tasks, update_task, get_product_task_summary, get_task_dependencies,
           bulk_update_tasks, create_task_conversion_history, get_conversion_history,
           project_from_task, list_my_tasks, assign_task_to_agent
- Kept: create_task (for MCP quick capture), /task prompt (CLI slash command)
- Web interface uses REST API (/api/v1/tasks/) unchanged
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

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
                    f"Task created: '{title}'\n"
                    f"Priority: {priority}\n"
                    f"Category: {category}\n"
                    f"ID: {task_id}"
                    f"{scope_info}\n\n"
                    f"Manage tasks in web UI: Tasks tab"
                )
            error = result.get("error", "Unknown error")
            return f"Failed to create task: {error}"

        except Exception as e:
            logger.exception(f"Failed to create task from slash command: {e}")
            return f"Error creating task: {e!s}"

    logger.info("Task management tools registered successfully")
