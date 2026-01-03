"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

import yaml
from sqlalchemy import and_, select, update

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Message, Product, Project, Task
from giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.services.template_service import TemplateService
from giljo_mcp.services.task_service import TaskService
from giljo_mcp.services.message_service import MessageService
from giljo_mcp.services.context_service import ContextService
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


# ============================================================================
# STANDALONE HELPER FUNCTIONS (For Testing and Tenant Isolation)
# ============================================================================


async def activate_project(
    project_id: str,
    tenant_key: str,
    session
) -> dict[str, Any]:
    """
    Activate a project with tenant isolation (testable helper).

    This is a standalone helper function that extracts the core logic
    from ToolAccessor.gil_activate() for testing purposes.

    Args:
        project_id: Project ID to activate
        tenant_key: Tenant isolation key
        session: Database session

    Returns:
        Success/error dictionary with project details
    """
    try:
        from datetime import datetime, timezone

        # Get project with tenant isolation
        res = await session.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key
                )
            )
        )
        project = res.scalar_one_or_none()

        if not project:
            return {"success": False, "error": "Project not found"}

        if project.status != "inactive":
            return {"success": False, "error": f"Project cannot be activated from status '{project.status}'"}

        # Verify product belongs to same tenant (if exists)
        if project.product_id:
            # TENANT ISOLATION: Filter product by tenant_key
            prod = await session.execute(
                select(Product).where(
                    and_(
                        Product.id == project.product_id,
                        Product.tenant_key == tenant_key
                    )
                )
            )
            product = prod.scalar_one_or_none()
            if not product or not getattr(product, "is_active", False):
                return {"success": False, "error": "Parent product inactive or missing"}

        # Activate the project
        project.status = "active"
        project.updated_at = datetime.now(timezone.utc)
        await session.commit()

        return {
            "success": True,
            "project_id": str(project.id),
            "status": "active",
        }

    except Exception as e:
        logger.exception(f"Failed to activate project: {e}")
        return {"success": False, "error": str(e)}


class ToolAccessor:
    """Provides direct access to MCP tool functionality for API"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        websocket_manager: Optional[Any] = None,
        test_session: Optional["AsyncSession"] = None
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._test_session = test_session

        # Initialize service layer (Handover 0121 - Phase 1, Handover 0123 - Phase 2 ✅ COMPLETE)
        self._project_service = ProjectService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager  # Fix: Pass WebSocket manager for mission updates
        )
        self._template_service = TemplateService(db_manager, tenant_manager)
        self._task_service = TaskService(db_manager, tenant_manager)
        self._message_service = MessageService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager  # Pass WebSocket manager
        )
        self._context_service = ContextService(db_manager, tenant_manager)
        self._orchestration_service = OrchestrationService(
            db_manager,
            tenant_manager,
            message_service=self._message_service,  # Pass MessageService for WebSocket-enabled messaging
            test_session=test_session  # Pass test session for transaction sharing (Handover 0358c)
        )

    def get_session_async(self):
        """
        Get async session context manager.

        Uses test_session when available for transaction sharing in tests (Handover 0358c).
        """
        if self._test_session is not None:
            # Return async context manager that yields test session
            import contextlib
            @contextlib.asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session
            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    # Project Tools

    async def create_project(
        self,
        name: str,
        mission: str,
        description: str = "",
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        status: str = "inactive",
        context_budget: int = 150000,
    ) -> dict[str, Any]:
        """Create a new project (delegates to ProjectService)"""
        return await self._project_service.create_project(
            name=name,
            mission=mission,
            description=description,
            product_id=product_id,
            tenant_key=tenant_key,
            status=status,
            context_budget=context_budget,
        )

    async def list_projects(self, status: Optional[str] = None, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """List all projects with optional status filter (delegates to ProjectService)"""
        return await self._project_service.list_projects(
            status=status,
            tenant_key=tenant_key
        )

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a specific project by ID (delegates to ProjectService)"""
        return await self._project_service.get_project(project_id)

    async def switch_project(self, project_id: str) -> dict[str, Any]:
        """Switch to a different project (delegates to ProjectService)"""
        return await self._project_service.switch_project(project_id)

    async def project_status(self, project_id: Optional[str] = None) -> dict[str, Any]:
        """Get comprehensive project status (delegates to ProjectService)"""
        return await self._project_service.get_project_status(project_id)

    async def close_project(self, project_id: str, summary: str) -> dict[str, Any]:
        """
        Close a completed project with summary.
        DEPRECATED: Use complete_project instead (delegates to ProjectService)
        """
        return await self._project_service.complete_project(project_id, summary)

    async def complete_project(self, project_id: str, summary: Optional[str] = None) -> dict[str, Any]:
        """Mark a project as completed (delegates to ProjectService)"""
        return await self._project_service.complete_project(project_id, summary)

    async def cancel_project(self, project_id: str, reason: Optional[str] = None) -> dict[str, Any]:
        """Cancel a project (delegates to ProjectService)"""
        return await self._project_service.cancel_project(project_id, reason)

    async def restore_project(self, project_id: str) -> dict[str, Any]:
        """Restore a completed or cancelled project (delegates to ProjectService)"""
        return await self._project_service.restore_project(project_id)

    async def update_project_mission(self, project_id: str, mission: str) -> dict[str, Any]:
        """Update the mission field (delegates to ProjectService)"""
        return await self._project_service.update_project_mission(project_id, mission)

    async def update_agent_mission(
        self, job_id: str, tenant_key: str, mission: str
    ) -> dict[str, Any]:
        """
        Update the mission field of an AgentJob.

        Handover 0380: Used by orchestrators to persist their execution plan during staging.
        This allows fresh-session orchestrators to retrieve the plan via get_agent_mission()
        during implementation phase.

        Args:
            job_id: The AgentJob.job_id (work order UUID)
            tenant_key: Tenant isolation key
            mission: The execution plan/mission to persist

        Returns:
            {"success": True, "job_id": job_id, "mission_updated": True}
        """
        try:
            async with self.get_session_async() as session:
                from sqlalchemy import and_, select

                from giljo_mcp.models.agent_identity import AgentJob

                result = await session.execute(
                    select(AgentJob).where(
                        and_(
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key,
                        )
                    )
                )
                job = result.scalar_one_or_none()

                if not job:
                    return {
                        "error": "NOT_FOUND",
                        "message": f"Agent job {job_id} not found",
                        "troubleshooting": [
                            "Verify job_id is correct",
                            "Ensure tenant_key matches",
                            f"Check database: SELECT * FROM agent_jobs WHERE job_id = '{job_id}'",
                        ],
                    }

                job.mission = mission
                await session.commit()

                # Emit WebSocket event for UI update
                if self._websocket_manager:
                    try:
                        await self._websocket_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="job:mission_updated",
                            data={
                                "job_id": job_id,
                                "job_type": job.job_type,
                                "mission_length": len(mission),
                                "project_id": str(job.project_id) if job.project_id else None,
                            },
                        )
                        logger.info(
                            f"[WEBSOCKET] Broadcasted job:mission_updated for {job_id}",
                            extra={"job_id": job_id, "tenant_key": tenant_key},
                        )
                    except Exception as ws_error:
                        logger.warning(f"[WEBSOCKET] Failed to broadcast job:mission_updated: {ws_error}")

                logger.info(
                    f"[UPDATE_AGENT_MISSION] Updated mission for job {job_id}",
                    extra={
                        "job_id": job_id,
                        "job_type": job.job_type,
                        "mission_length": len(mission),
                        "tenant_key": tenant_key,
                    },
                )

                return {
                    "success": True,
                    "job_id": job_id,
                    "mission_updated": True,
                    "mission_length": len(mission),
                }

        except Exception as e:
            logger.exception(f"Failed to update agent mission: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}

    # Agent Tools

    async def decommission_agent(self, agent_name: str, project_id: str, reason: str = "completed") -> dict[str, Any]:
        """Gracefully end an agent's work"""
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    update(Agent)
                    .where(Agent.name == agent_name, Agent.project_id == project_id)
                    .values(status="decommissioned", meta_data={"reason": reason})
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Agent not found"}

                await session.commit()

                return {
                    "success": True,
                    "message": f"Agent {agent_name} decommissioned",
                }

        except Exception as e:
            logger.exception(f"Failed to decommission agent: {e}")
            return {"success": False, "error": str(e)}

    # Message Tools (delegates to MessageService)

    async def send_message(
        self,
        to_agents: list[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
        from_agent: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send message to one or more agents (delegates to MessageService)"""
        return await self._message_service.send_message(
            to_agents=to_agents,
            content=content,
            project_id=project_id,
            message_type=message_type,
            priority=priority,
            from_agent=from_agent,
            tenant_key=tenant_key,
        )

    async def get_messages(self, agent_name: str, project_id: Optional[str] = None) -> dict[str, Any]:
        """Retrieve pending messages for an agent (delegates to MessageService)"""
        return await self._message_service.get_messages(agent_name=agent_name, project_id=project_id)

    async def complete_message(self, message_id: str, agent_name: str, result: str) -> dict[str, Any]:
        """Mark message as completed with result (delegates to MessageService)"""
        return await self._message_service.complete_message(message_id=message_id, agent_name=agent_name, result=result)

    async def broadcast(self, content: str, project_id: str, priority: str = "normal") -> dict[str, Any]:
        """Broadcast message to all agents in project (delegates to MessageService)"""
        return await self._message_service.broadcast(content=content, project_id=project_id, priority=priority)

    async def receive_messages(
        self,
        agent_id: str,
        limit: int = 10,
        tenant_key: Optional[str] = None,
        exclude_self: bool = True,
        exclude_progress: bool = True,
        message_types: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Receive pending messages for an agent with optional filtering (delegates to MessageService).

        Handover 0360: Added filtering parameters for better message control.
        Handover 0378 Bug 1: Added tenant_key parameter to match MCP tool schema.

        Args:
            agent_id: Agent execution ID
            limit: Maximum messages to retrieve
            tenant_key: Tenant key for multi-tenant isolation
            exclude_self: Filter out messages from same agent_id (default: True)
            exclude_progress: Filter out progress-type messages (default: True)
            message_types: Optional allow-list of message types (default: None = all types)

        Returns:
            List of message dicts
        """
        return await self._message_service.receive_messages(
            agent_id=agent_id,
            limit=limit,
            tenant_key=tenant_key,
            exclude_self=exclude_self,
            exclude_progress=exclude_progress,
            message_types=message_types
        )

    async def list_messages(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        List messages in a project or for a specific agent (delegates to MessageService).

        Handover 0378 Bug 1: Added tenant_key parameter to match MCP tool schema.
        """
        return await self._message_service.list_messages(
            project_id=project_id, status=status, agent_id=agent_id, tenant_key=tenant_key, limit=limit
        )

    # Task Tools

    async def log_task(self, content: str, category: Optional[str] = None, priority: str = "medium") -> dict[str, Any]:
        """Quick task capture (delegates to TaskService)"""
        return await self._task_service.log_task(content=content, category=category, priority=priority)

    async def create_task(
        self, title: str, description: str, priority: str = "medium", assigned_to: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a new task (delegates to TaskService)"""
        return await self._task_service.create_task(
            title=title, description=description, priority=priority, assigned_to=assigned_to
        )

    # Task MCP tools retired Dec 2025 - list_tasks, update_task, assign_task, complete_task removed
    # Web interface uses REST API (/api/v1/tasks/) via TaskService directly

    # Context Tools (delegates to ContextService)

    async def get_context_index(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get the context index for intelligent querying (delegates to ContextService)"""
        return await self._context_service.get_context_index(product_id=product_id)

    async def get_vision(self, part: int = 1, max_tokens: int = 20000) -> dict[str, Any]:
        """Get the vision document (delegates to ContextService)"""
        return await self._context_service.get_vision(part=part, max_tokens=max_tokens)

    async def get_vision_index(self) -> dict[str, Any]:
        """Get the vision document index (delegates to ContextService)"""
        return await self._context_service.get_vision_index()

    async def get_product_settings(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get all product settings for analysis (delegates to ContextService)"""
        return await self._context_service.get_product_settings(product_id=product_id)

    # Template Tools (delegates to TemplateService)

    async def list_templates(self) -> dict[str, Any]:
        """List available templates (delegates to TemplateService)"""
        return await self._template_service.list_templates()

    async def get_template(self, template_name: str) -> dict[str, Any]:
        """Get a specific template (delegates to TemplateService)"""
        return await self._template_service.get_template(template_name=template_name)

    async def create_template(self, name: str, content: str, **kwargs) -> dict[str, Any]:
        """Create a new template (delegates to TemplateService)"""
        return await self._template_service.create_template(name=name, content=content, **kwargs)

    async def update_template(self, template_id: str, **kwargs) -> dict[str, Any]:
        """Update a template (delegates to TemplateService)"""
        return await self._template_service.update_template(template_id=template_id, **kwargs)

    # Agent Export Tools (Handover 0084)

    async def export_agents(
        self,
        product_path: Optional[str] = None,
        personal: bool = False,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Export agent templates to Claude Code format via MCP command.

        Args:
            product_path: Path to product's .claude/agents directory
            personal: Export to user's personal ~/.claude/agents
            product_id: Optional specific product ID (uses active product if not specified)

        Returns:
            Export result dictionary
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            from .claude_export import export_agents_command, get_product_for_tenant

            # If product_path not provided and not personal, try to get from product
            if not product_path and not personal:
                product = await get_product_for_tenant(self.db_manager, tenant_key, product_id)
                if product and product.project_path:
                    product_path = str(Path(product.project_path) / ".claude" / "agents")
                else:
                    return {
                        "success": False,
                        "error": "No product path configured. Set product project_path or use --personal",
                    }

            # Call export command
            result = await export_agents_command(
                db_manager=self.db_manager,
                tenant_key=tenant_key,
                product_path=product_path,
                personal=personal,
            )

            return result

        except Exception as e:
            logger.exception(f"Failed to export agents: {e}")
            return {"success": False, "error": str(e)}

    async def set_product_path(
        self,
        project_path: str,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Set or update product's project path for agent export.

        Args:
            project_path: File system path to product folder
            product_id: Optional specific product ID (uses active product if not specified)

        Returns:
            Update result dictionary
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            from .claude_export import get_product_for_tenant, validate_product_path

            # Get product
            product = await get_product_for_tenant(self.db_manager, tenant_key, product_id)
            if not product:
                return {"success": False, "error": "Product not found"}

            # Validate and update path
            result = await validate_product_path(
                db_manager=self.db_manager,
                tenant_key=tenant_key,
                product_id=str(product.id),
                project_path=project_path,
            )

            return result

        except Exception as e:
            logger.exception(f"Failed to set product path: {e}")
            return {"success": False, "error": str(e)}

    async def get_product_path(
        self,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get product's current project path.

        Args:
            product_id: Optional specific product ID (uses active product if not specified)

        Returns:
            Product path information
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            from .claude_export import get_product_for_tenant

            # Get product
            product = await get_product_for_tenant(self.db_manager, tenant_key, product_id)
            if not product:
                return {"success": False, "error": "Product not found"}

            return {
                "success": True,
                "product_id": str(product.id),
                "product_name": product.name,
                "project_path": product.project_path,
                "has_path": bool(product.project_path),
            }

        except Exception as e:
            logger.exception(f"Failed to get product path: {e}")
            return {"success": False, "error": str(e)}

    # Orchestration Tools

    async def health_check(self) -> dict[str, Any]:
        """MCP server health check"""
        from giljo_mcp.tools.orchestration import health_check

        return await health_check()

    async def get_orchestrator_instructions(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Fetch orchestrator mission with framing-based context instructions (Handover 0350b).

        Returns a lean response (~500 tokens) with:
        - identity: Orchestrator/project identifiers
        - project_description_inline: Description + mission (always inline)
        - context_fetch_instructions: Framing pointers to fetch_context() tool

        The orchestrator uses these instructions to call fetch_context() on-demand,
        avoiding the 50K+ token truncation risk of inline context.
        """
        try:
            async with self.get_session_async() as session:
                from sqlalchemy import and_
                from sqlalchemy.orm import selectinload, joinedload

                from giljo_mcp.mission_planner import MissionPlanner
                from giljo_mcp.models import AgentTemplate, Product, Project

                # Validate inputs
                if not job_id or not job_id.strip():
                    return {"error": "VALIDATION_ERROR", "message": "Job ID is required"}

                if not tenant_key or not tenant_key.strip():
                    return {"error": "VALIDATION_ERROR", "message": "Tenant key is required"}

                # Phase C: Query AgentExecution and join to AgentJob
                # Get current execution for this job (latest instance)
                result = await session.execute(
                    select(AgentExecution)
                    .options(joinedload(AgentExecution.job))
                    .where(
                        and_(
                            AgentExecution.job_id == job_id,
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.instance_number.desc())
                )
                execution = result.scalars().first()

                if not execution:
                    return {"error": "NOT_FOUND", "message": f"Orchestrator execution for job {job_id} not found"}

                # Get the associated AgentJob
                agent_job = execution.job
                if not agent_job:
                    return {"error": "NOT_FOUND", "message": f"Agent job {job_id} not found"}

                # Verify it's an orchestrator
                if agent_job.job_type != "orchestrator":
                    return {"error": "VALIDATION_ERROR", "message": f"Job {job_id} is not an orchestrator"}

                # Get project and product
                result = await session.execute(
                    select(Project).where(and_(Project.id == agent_job.project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": "NOT_FOUND", "message": "Project not found"}

                product = None
                if project.product_id:
                    result = await session.execute(
                        select(Product)
                        .where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
                        .options(selectinload(Product.vision_documents))
                    )
                    product = result.scalar_one_or_none()

                # Get user configuration
                planner = MissionPlanner(self.db_manager)
                metadata = agent_job.job_metadata or {}
                user_id = metadata.get("user_id")

                # Handover 0346: Fetch FRESH user config if user_id available
                if user_id:
                    from giljo_mcp.tools.orchestration import _get_user_config
                    user_config = await _get_user_config(user_id, tenant_key, session)
                    field_priorities = user_config["field_priorities"]
                    depth_config = user_config["depth_config"]
                    logger.info(
                        "[USER_CONFIG] Fetched fresh user config for ToolAccessor",
                        extra={"job_id": job_id, "user_id": user_id}
                    )
                else:
                    field_priorities = metadata.get("field_priorities", {})
                    depth_config = metadata.get("depth_config", {})
                    logger.debug(
                        "[USER_CONFIG] No user_id, using frozen job_metadata config",
                        extra={"job_id": job_id}
                    )

                # Handover 0350b: Generate framing instructions (replaces inline context)
                # This returns ~500 tokens instead of 4-8K (up to 50K with vision)
                fetch_instructions = planner._build_fetch_instructions(
                    product=product,
                    project=project,
                    field_priorities=field_priorities,
                    depth_config=depth_config,
                )

                # Get agent templates for reference
                result = await session.execute(
                    select(AgentTemplate)
                    .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True))
                    .limit(8)
                )
                templates = result.scalars().all()

                # Build agent template summary (needed for spawning - staging prompt references this)
                template_list = [
                    {"name": t.name, "role": t.role, "description": t.description[:200] if t.description else ""}
                    for t in templates
                ]

                # Resolve project path (local developer folder pointer, stored on Product)
                project_path = None
                if product is not None:
                    # Product.project_path is a developer-provided filesystem hint.
                    # It is returned verbatim so agents know where the codebase lives locally.
                    project_path = getattr(product, "project_path", None)

                # Build framing-based response (Handover 0350b + Phase C)
                # Includes: identity, project context, fetch instructions, AND agent templates
                response = {
                    "identity": {
                        "job_id": job_id,
                        "agent_id": execution.agent_id,  # Phase C: Add executor UUID
                        "project_id": str(project.id),
                        "project_name": project.name,
                        "tenant_key": tenant_key,
                        "instance_number": execution.instance_number or 1,
                    },
                    "project_description_inline": {
                        "description": project.description or "",
                        "mission": agent_job.mission or "",  # Phase C: Mission from AgentJob
                        "project_path": project_path,
                    },
                    "context_fetch_instructions": fetch_instructions,
                    "agent_templates": template_list,  # Staging prompt: "Returns: ... AVAILABLE AGENT TEMPLATES"
                    "mcp_tools_available": [
                        "fetch_context",
                        "spawn_agent_job",
                        "get_available_agents",
                        "send_message",
                        "check_succession_status",
                        "create_successor_orchestrator",
                        "report_progress",
                        "complete_job",
                    ],
                    "context_budget": execution.context_budget or 150000,  # Phase C: From AgentExecution
                    "context_used": execution.context_used or 0,  # Phase C: From AgentExecution
                    "field_priorities": field_priorities,
                    "thin_client": True,
                    "architecture": "framing_based",
                }

                # Handover 0351: Add CLI mode rules when execution_mode == 'claude_code_cli'
                # agent_name is SINGLE SOURCE OF TRUTH for template matching
                execution_mode = getattr(project, 'execution_mode', None) or metadata.get("execution_mode", "multi_terminal")
                if execution_mode == "claude_code_cli":
                    allowed_agent_names = [t.name for t in templates]

                    response["agent_spawning_constraint"] = {
                        "mode": "strict_task_tool",
                        "allowed_agent_names": allowed_agent_names,
                        "instruction": (
                            "CRITICAL: You MUST use Claude Code's native Task tool for agent spawning. "
                            "The agent_name parameter must be EXACTLY one of the allowed template names. "
                            f"Allowed agent names: {allowed_agent_names}"
                        ),
                    }

                    response["cli_mode_rules"] = {
                        "agent_name_usage": (
                            "SINGLE SOURCE OF TRUTH - MUST match template filename exactly for Task tool. "
                            "This is the filename without .md extension (e.g., 'implementer-frontend')."
                        ),
                        "agent_type_usage": "Display category label for UI only (e.g., 'implementer').",
                        "task_tool_mapping": "Task(subagent_type=X) where X = agent_name from spawn_agent_job.",
                        "validation": "soft",
                        "template_locations": [
                            "{project}/.claude/agents/",
                            "~/.claude/agents/",
                        ],
                    }

                    logger.info(
                        f"[CLI_MODE_RULES] Added CLI mode rules for orchestrator {job_id}",
                        extra={
                            "job_id": job_id,
                            "execution_mode": execution_mode,
                            "allowed_names": allowed_agent_names,
                        }
                    )

                logger.info(
                    f"[FRAMING_BASED] Returning framing-based orchestrator instructions",
                    extra={
                        "job_id": job_id,
                        "critical_count": len(fetch_instructions.get("critical", [])),
                        "important_count": len(fetch_instructions.get("important", [])),
                        "reference_count": len(fetch_instructions.get("reference", [])),
                    }
                )

                return response

        except Exception as e:
            logger.exception(f"Failed to get orchestrator instructions: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}

    async def spawn_agent_job(
        self,
        agent_type: str,
        agent_name: str,
        mission: str,
        project_id: str,
        tenant_key: str,
        parent_job_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create an agent job (delegates to OrchestrationService)"""
        return await self._orchestration_service.spawn_agent_job(
            agent_type=agent_type,
            agent_name=agent_name,
            mission=mission,
            project_id=project_id,
            tenant_key=tenant_key,
            parent_job_id=parent_job_id
        )

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Get agent-specific mission (delegates to OrchestrationService). Handover 0381: job_id contract."""
        return await self._orchestration_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)

    async def orchestrate_project(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """Full project orchestration workflow (delegates to OrchestrationService)"""
        return await self._orchestration_service.orchestrate_project(project_id=project_id, tenant_key=tenant_key)

    async def get_workflow_status(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """Get workflow status for a project (delegates to OrchestrationService)"""
        return await self._orchestration_service.get_workflow_status(project_id=project_id, tenant_key=tenant_key)

    # Agent Coordination Tools

    async def get_pending_jobs(self, agent_type: str, tenant_key: str) -> dict[str, Any]:
        """Get pending jobs for agent type (delegates to OrchestrationService)"""
        return await self._orchestration_service.get_pending_jobs(agent_type=agent_type, tenant_key=tenant_key)

    async def acknowledge_job(self, job_id: str, agent_id: str, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """Acknowledge job assignment (delegates to OrchestrationService)"""
        return await self._orchestration_service.acknowledge_job(job_id=job_id, agent_id=agent_id)

    async def report_progress(self, job_id: str, progress: dict[str, Any], tenant_key: Optional[str] = None) -> dict[str, Any]:
        """Report job progress (delegates to OrchestrationService)"""
        return await self._orchestration_service.report_progress(job_id=job_id, progress=progress, tenant_key=tenant_key)

    async def complete_job(self, job_id: str, result: dict[str, Any], tenant_key: Optional[str] = None) -> dict[str, Any]:
        """Mark job as complete (delegates to OrchestrationService)"""
        return await self._orchestration_service.complete_job(job_id=job_id, result=result)

    async def report_error(self, job_id: str, error: str, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """Report job error (delegates to OrchestrationService)"""
        return await self._orchestration_service.report_error(job_id=job_id, error=error)

    async def get_next_instruction(self, job_id: str, agent_type: str, tenant_key: str) -> dict[str, Any]:
        """Get next instructions for agent from message queue"""
        from giljo_mcp.agent_message_queue import AgentMessageQueue

        try:
            # Validate inputs
            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}

            if not agent_type or not agent_type.strip():
                return {"status": "error", "error": "agent_type cannot be empty"}

            if not tenant_key or not tenant_key.strip():
                return {"status": "error", "error": "tenant_key cannot be empty"}

            comm_queue = AgentMessageQueue(self.db_manager)  # Using compatibility layer

            # Get unread messages for this job
            async with self.db_manager.get_session_async() as session:
                result = await comm_queue.get_messages(
                    session=session, job_id=job_id, tenant_key=tenant_key, to_agent=agent_type, unread_only=True
                )

                if result.get("status") != "success":
                    return result

                messages = result.get("messages", [])
                has_updates = len(messages) > 0

                # Extract and categorize instructions
                instructions = []
                handoff_requested = False
                context_warning = False

                for msg in messages:
                    msg_type = msg.get("type")
                    content = msg.get("content")

                    if msg_type == "user_feedback":
                        instructions.append(f"USER FEEDBACK: {content}")
                    elif msg_type == "orchestrator_instruction":
                        instructions.append(f"ORCHESTRATOR: {content}")
                    elif msg_type == "handoff_request":
                        handoff_requested = True
                        instructions.append("HANDOFF REQUESTED: Prepare comprehensive summary and context handoff")
                    elif msg_type == "context_warning":
                        context_warning = True
                        instructions.append(f"CONTEXT WARNING: {content} - Plan completion or handoff")
                    elif msg_type == "error_recovery":
                        instructions.append(f"ERROR RECOVERY GUIDANCE: {content}")

                return {
                    "status": "success",
                    "has_updates": has_updates,
                    "instructions": instructions,
                    "handoff_requested": handoff_requested,
                    "context_warning": context_warning,
                    "message_count": len(messages),
                }

        except Exception as e:
            logger.exception(f"Failed to get next instruction: {e}")
            return {"status": "error", "error": str(e)}

    async def get_team_agents(
        self,
        job_id: str,
        tenant_key: str,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        """
        List agent executions (teammates) associated with this job.

        Handover 0360 Feature 2: Team Discovery Tool.

        Enables agents to discover teammates working on the same job/project.

        Args:
            job_id: Job ID to get teammates for
            tenant_key: Tenant key for multi-tenant isolation
            include_inactive: If True, include completed/decommissioned executions

        Returns:
            dict: {
                "success": True,
                "team": [
                    {
                        "agent_id": str,
                        "job_id": str,
                        "agent_type": str,
                        "status": str,
                        "instance_number": int,
                        "agent_name": str,
                        "tenant_key": str
                    },
                    ...
                ]
            }
        """
        from giljo_mcp.tools.agent_coordination import get_team_agents as coordination_get_team_agents

        return await coordination_get_team_agents(
            job_id=job_id,
            tenant_key=tenant_key,
            include_inactive=include_inactive,
        )

    # Succession Tools (Handover 0080)

    async def create_successor_orchestrator(
        self, current_job_id: str, tenant_key: str, reason: str = "context_limit"
    ) -> dict[str, Any]:
        """Create successor orchestrator for context handover (Handover 0080 + Phase C)"""
        try:
            from datetime import datetime, timezone
            from sqlalchemy.orm import joinedload

            async with self.get_session_async() as session:
                # Phase C: Get current execution (latest instance for this job)
                result = await session.execute(
                    select(AgentExecution)
                    .options(joinedload(AgentExecution.job))
                    .where(
                        and_(
                            AgentExecution.job_id == current_job_id,
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.instance_number.desc())
                )
                current_execution = result.scalars().first()

                if not current_execution:
                    return {
                        "success": False,
                        "error": f"Orchestrator execution for job {current_job_id} not found for tenant {tenant_key}",
                    }

                # Get the associated AgentJob
                agent_job = current_execution.job
                if not agent_job:
                    return {"success": False, "error": f"Agent job {current_job_id} not found"}

                # Verify it's an orchestrator
                if agent_job.job_type != "orchestrator":
                    return {
                        "success": False,
                        "error": f"Job {current_job_id} is not an orchestrator (type: {agent_job.job_type})",
                    }

                # Verify job is not already completed
                if agent_job.status == "completed":
                    return {"success": False, "error": f"Job {current_job_id} is already completed"}

                # Phase C: Create successor execution (SAME job_id, NEW agent_id)
                successor_agent_id = str(uuid4())
                successor_instance = (current_execution.instance_number or 1) + 1

                # Generate simple handover summary
                handover_summary = (
                    f"Succession from instance {current_execution.instance_number} to {successor_instance}. "
                    f"Reason: {reason}. "
                    f"Context used: {current_execution.context_used or 0}/{current_execution.context_budget or 150000}."
                )

                # Create new execution
                successor_execution = AgentExecution(
                    agent_id=successor_agent_id,
                    job_id=current_job_id,  # SAME job_id (work order persists)
                    tenant_key=tenant_key,
                    agent_type="orchestrator",
                    agent_name=current_execution.agent_name or "Orchestrator",
                    instance_number=successor_instance,
                    status="waiting",
                    spawned_by=current_execution.agent_id,  # Track previous executor
                    succession_reason=reason,
                    handover_summary=handover_summary,
                    progress=0,
                    context_used=0,
                    context_budget=current_execution.context_budget or 150000,
                )

                session.add(successor_execution)

                # Mark current execution as decommissioned
                current_execution.status = "decommissioned"
                current_execution.succeeded_by = successor_agent_id
                current_execution.completed_at = datetime.now(timezone.utc)

                # Commit changes
                await session.commit()
                await session.refresh(successor_execution)

                logger.info(
                    f"Succession completed: agent {current_execution.agent_id} → {successor_agent_id}, "
                    f"instance {current_execution.instance_number} → {successor_instance}, "
                    f"job {current_job_id} (persistent), reason: {reason}"
                )

                return {
                    "success": True,
                    "successor_id": successor_agent_id,  # NEW: agent_id of successor
                    "job_id": current_job_id,  # SAME: work order persists
                    "instance_number": successor_instance,
                    "status": successor_execution.status,
                    "handover_summary": handover_summary,
                    "message": (
                        f"Successor orchestrator created (instance {successor_instance}). "
                        f"Previous orchestrator marked decommissioned. "
                        f"Launch successor manually from dashboard."
                    ),
                }

        except Exception as e:
            logger.exception(f"Failed to create successor orchestrator: {e}")
            return {"success": False, "error": str(e)}

    async def check_succession_status(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Check if orchestrator should trigger succession (Handover 0080 + Phase C)"""
        try:
            async with self.get_session_async() as session:
                # Phase C: Get current execution (latest instance)
                result = await session.execute(
                    select(AgentExecution)
                    .where(
                        and_(
                            AgentExecution.job_id == job_id,
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.instance_number.desc())
                )
                execution = result.scalars().first()

                if not execution:
                    return {"should_trigger": False, "error": f"Job {job_id} not found"}

                # Calculate context usage percentage (from execution)
                context_used = execution.context_used or 0
                context_budget = execution.context_budget or 200000
                usage_percentage = (context_used / context_budget) * 100 if context_budget > 0 else 0

                # Determine if succession should be triggered (90% threshold)
                should_trigger = usage_percentage >= 90.0

                recommendation = ""
                if usage_percentage < 70:
                    recommendation = "Context usage healthy. Continue normal operation."
                elif usage_percentage < 85:
                    recommendation = "Monitor context usage. Begin planning for potential succession."
                elif usage_percentage < 90:
                    recommendation = "Context usage high. Prepare for succession soon."
                else:
                    recommendation = "Trigger succession now to avoid context overflow."

                return {
                    "should_trigger": should_trigger,
                    "context_used": context_used,
                    "context_budget": context_budget,
                    "usage_percentage": round(usage_percentage, 2),
                    "threshold_reached": should_trigger,
                    "recommendation": recommendation,
                }

        except Exception as e:
            logger.exception(f"Failed to check succession status: {e}")
            return {"should_trigger": False, "error": str(e)}

    # Slash Command Setup Tool (Handover 0093)

    async def setup_slash_commands(
        self, platform: str = None, _api_key: str = None, _server_url: str = None
    ) -> dict[str, Any]:
        """
        Generate one-time download link for slash commands installation.

        Returns download URL instead of executing file operations on server.
        Client downloads and extracts files locally for proper installation.

        Args:
            platform: Optional platform hint (ignored, kept for compatibility)
            _api_key: API key for HTTP authentication (injected by MCP HTTP handler)
            _server_url: Server URL from HTTP request (injected by MCP HTTP handler)

        Returns:
            dict with success, download_url, message, expires_minutes, one_time_use, error (optional)
        """
        try:
            from giljo_mcp.config_manager import get_config
            from giljo_mcp.downloads.token_manager import TokenManager
            from giljo_mcp.file_staging import FileStaging

            # 1. Verify API key (injected by MCP HTTP handler)
            if not _api_key:
                return {
                    "success": False,
                    "error": "API key not provided",
                    "instructions": [
                        "This tool is called via MCP HTTP and requires authentication",
                        "Ensure you are connected to GiljoAI MCP server with valid API key",
                    ],
                }

            # 2. Get tenant context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            # 3. Generate token FIRST and stage with SAME token (single-token flow)
            async with self.db_manager.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                download_token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type="slash_commands",
                    metadata={"filename": "slash_commands.zip"},
                )
                file_staging = FileStaging()
                staging_path = await file_staging.create_staging_directory(tenant_key, download_token)
                zip_path, message = await file_staging.stage_slash_commands(staging_path)
                if not zip_path:
                    await token_manager.mark_failed(download_token, message)
                    await file_staging.cleanup(tenant_key, download_token)
                    logger.error(f"Staging failed for token {download_token}: {message}")
                    return {"success": False, "error": f"File staging failed: {message}"}
                await token_manager.mark_ready(download_token)
                logger.info(f"Staged slash commands ZIP for token {download_token}: {zip_path}")

            # 5. Build download URL (use dynamically detected server URL)
            if not _server_url:
                config = get_config()

                # Read external_host from config.yaml for public IP
                config_path = Path.cwd() / "config.yaml"
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)

                host = config_data.get("services", {}).get("external_host", "localhost")
                _server_url = f"http://{host}:{config.server.api_port}"
                logger.warning(f"Server URL not provided, using fallback: {_server_url}")

            download_url = f"{_server_url}/api/download/temp/{download_token}/slash_commands.zip"

            # 6. Return explicit bash commands for AI agents
            # Cross-platform: Bash tool uses Git Bash on Windows, bash on Linux/macOS
            # Unix-style paths work on ALL platforms via the Bash tool
            bash_cmd = (
                f'curl -o /tmp/slash_commands.zip "{download_url}" && '
                "mkdir -p ~/.claude/commands && "
                "unzip -o /tmp/slash_commands.zip -d ~/.claude/commands/ && "
                "rm /tmp/slash_commands.zip"
            )
            return {
                "success": True,
                "instructions": (
                    "IMPORTANT: Use the Bash tool (not PowerShell) to run this command. "
                    "This works on Windows, Linux, and macOS:\n\n"
                    f"{bash_cmd}\n\n"
                    "After running, tell the user: 'Slash commands installed to ~/.claude/commands/. "
                    "Please restart Claude Code (Ctrl+C and relaunch) for the commands to become available. "
                    "After restart, type / to see available commands.'"
                ),
                "bash_command": bash_cmd,
                "download_url": download_url,
                "expires_minutes": 15,
                "unlimited_downloads": True,
                "install_location": "~/.claude/commands/",
                "cross_platform_note": (
                    "The Bash tool uses Git Bash on Windows and bash on Linux/macOS. "
                    "Unix-style paths (/tmp, ~/.claude/) work on ALL platforms. "
                    "Do NOT use PowerShell or Windows paths like %TEMP%."
                ),
            }

        except Exception as e:
            logger.exception(f"Failed to generate slash commands download: {e}")
            return {"success": False, "error": str(e)}

    # Slash Command Handler Wrapper (Handover 0084b)

    async def gil_handover(self, job_id: str = None, reason: str = "manual") -> dict[str, Any]:
        """
        Trigger orchestrator succession for context handover

        Wrapper for slash command handler that executes via MCP tool call.

        Args:
            job_id: Current orchestrator job UUID (work order identifier)
            reason: Succession reason (context_limit, manual, phase_transition)

        Returns:
            dict with success, message, successor_id, launch_prompt, error (optional)
        """
        try:
            from ..slash_commands import get_slash_command

            handler = get_slash_command("gil_handover")
            if not handler:
                return {"success": False, "message": "Slash command handler not found", "error": "HANDLER_NOT_FOUND"}

            # Get database session (synchronous context manager)
            with self.db_manager.get_session() as session:
                result = await handler(
                    db_session=session,
                    tenant_key=self.tenant_manager.get_current_tenant(),
                    project_id=None,  # Not used by handover
                    orchestrator_job_id=job_id,
                    reason=reason,
                )

            return result

        except Exception as e:
            logger.exception(f"Failed to execute gil_handover: {e}")
            return {"success": False, "message": str(e)}

    async def gil_activate(self, project_id: str) -> dict[str, Any]:
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}
            if not project_id:
                return {"success": False, "error": "project_id is required"}
            from sqlalchemy import select
            from giljo_mcp.models import Project, Product
            from datetime import datetime, timezone
            async with self.get_session_async() as session:
                res = await session.execute(select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key))
                project = res.scalar_one_or_none()
                if not project:
                    return {"success": False, "error": "Project not found"}
                if project.status != "inactive":
                    return {"success": False, "error": f"Project cannot be activated from status '{project.status}'"}
                if project.product_id:
                    # TENANT ISOLATION: Filter product by tenant_key
                    prod = await session.execute(
                        select(Product).where(
                            and_(
                                Product.id == project.product_id,
                                Product.tenant_key == tenant_key
                            )
                        )
                    )
                    product = prod.scalar_one_or_none()
                    if not product or not getattr(product, "is_active", False):
                        return {"success": False, "error": "Parent product inactive or missing"}
                project.status = "active"
                project.updated_at = datetime.now(timezone.utc)
                await session.commit()

                # Phase C: Check if orchestrator job exists
                job_result = await session.execute(
                    select(AgentJob).where(
                        AgentJob.project_id == project_id,
                        AgentJob.tenant_key == tenant_key,
                        AgentJob.job_type == "orchestrator",
                    )
                )
                agent_job = job_result.scalar_one_or_none()

                if not agent_job:
                    # Create both AgentJob and AgentExecution
                    job_id = str(uuid4())
                    agent_id = str(uuid4())

                    # Create AgentJob (work order)
                    agent_job = AgentJob(
                        job_id=job_id,
                        tenant_key=tenant_key,
                        project_id=project_id,
                        mission=(
                            "I am ready to create the project mission based on product context and project description. "
                            "I will write the mission in the mission window and select the proper agents below."
                        ),
                        job_type="orchestrator",
                        status="active",
                    )
                    session.add(agent_job)

                    # Create AgentExecution (executor instance)
                    agent_execution = AgentExecution(
                        agent_id=agent_id,
                        job_id=job_id,
                        tenant_key=tenant_key,
                        agent_type="orchestrator",
                        agent_name="Orchestrator",
                        instance_number=1,
                        status="waiting",
                        progress=0,
                        tool_type="universal",
                        messages=[],
                    )
                    session.add(agent_execution)
                    await session.commit()

            return {"success": True, "project_id": project_id}
        except Exception as e:
            logger.exception(f"gil_activate failed: {e}")
            return {"success": False, "error": str(e)}

    async def gil_launch(self, project_id: str) -> dict[str, Any]:
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}
            if not project_id:
                return {"success": False, "error": "project_id is required"}
            from sqlalchemy import select
            from giljo_mcp.models import Project
            from giljo_mcp.models.agent_identity import AgentJob
            from datetime import datetime, timezone
            async with self.get_session_async() as session:
                pr = await session.execute(select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key))
                project = pr.scalar_one_or_none()
                if not project:
                    return {"success": False, "error": "Project not found"}
                if not project.mission or not project.mission.strip():
                    return {"success": False, "error": "Project mission has not been created. Please complete staging first."}
                ag = await session.execute(
                    select(AgentJob).where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
                )
                agents = ag.scalars().all()
                if not agents:
                    return {"success": False, "error": "No agents have been spawned for this project. Please complete staging first."}
                if hasattr(project, "staging_status"):
                    project.staging_status = "launching"
                    project.updated_at = datetime.now(timezone.utc)
                    await session.commit()
            return {"success": True, "project_id": project_id, "agent_count": len(agents)}
        except Exception as e:
            logger.exception(f"gil_launch failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_agent_download_url(
        self, _api_key: str = None, _server_url: str = None
    ) -> dict[str, Any]:
        """
        Generate one-time download link for active agent templates.

        Stages active agent templates as ZIP and returns download URL.
        Token-based authentication - no API key header needed for download.
        Slash command handles user prompt for install location.

        Args:
            _api_key: API key for HTTP authentication (injected by MCP HTTP handler)
            _server_url: Server URL from HTTP request (injected by MCP HTTP handler)

        Returns:
            dict with success, download_url, expires_minutes, template_count
        """
        try:
            from giljo_mcp.config_manager import get_config
            from giljo_mcp.downloads.token_manager import TokenManager
            from giljo_mcp.file_staging import FileStaging

            # 1. Verify API key (injected by MCP HTTP handler)
            if not _api_key:
                return {
                    "success": False,
                    "error": "API key not provided - connect via MCP with valid API key",
                }

            # 2. Get tenant context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            # 3. Generate token and stage agent templates
            async with self.db_manager.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type="agent_templates",
                    metadata={"filename": "agent_templates.zip"},
                )

            # 4. Stage files in temp directory
            file_staging = FileStaging(db_session=None)
            async with self.db_manager.get_session_async() as session:
                file_staging.db_session = session
                staging_path = await file_staging.create_staging_directory(tenant_key, token)
                zip_path, message = await file_staging.stage_agent_templates(
                    staging_path, tenant_key, db_session=session
                )

                if not zip_path:
                    await token_manager.mark_failed(token, message)
                    await file_staging.cleanup(tenant_key, token)
                    return {"success": False, "error": f"Staging failed: {message}"}

                await token_manager.mark_ready(token)

            # Count templates in ZIP
            import zipfile
            with zipfile.ZipFile(zip_path, "r") as zf:
                template_count = len(zf.namelist())

            logger.info(f"Staged {template_count} agent templates for download: {zip_path}")

            # 5. Update last_exported_at for all exported templates (Handover 0356)
            from datetime import datetime, timezone
            from sqlalchemy import select
            from giljo_mcp.models import AgentTemplate

            async with self.db_manager.get_session_async() as session:
                stmt = select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.is_active == True
                )
                result = await session.execute(stmt)
                templates = result.scalars().all()

                export_timestamp = datetime.now(timezone.utc)
                for template in templates:
                    template.last_exported_at = export_timestamp

                await session.commit()
                logger.info(f"Updated last_exported_at for {len(templates)} templates")

            # 6. Build download URL (token IS auth - no API key needed)
            if not _server_url:
                config = get_config()
                config_path = Path.cwd() / "config.yaml"
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                host = config_data.get("services", {}).get("external_host", "localhost")
                _server_url = f"http://{host}:{config.server.api_port}"

            download_url = f"{_server_url}/api/download/temp/{token}/agent_templates.zip"

            return {
                "success": True,
                "download_url": download_url,
                "expires_minutes": 15,
                "template_count": template_count,
            }

        except Exception as e:
            logger.exception(f"get_agent_download_url failed: {e}")
            return {"success": False, "error": str(e)}

    async def close_project_and_update_memory(
        self,
        project_id: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        tenant_key: str,
    ) -> dict[str, Any]:
        """
        Close project and update product memory with sequential history entries (Handover 0138+).

        This method wraps the project_closeout MCP tool for use via ToolAccessor.
        See project_closeout.py for implementation details.

        Args:
            project_id: UUID of the project being closed
            summary: User-provided summary of project work
            key_outcomes: List of key achievements/outcomes
            decisions_made: List of important decisions made
            tenant_key: Tenant isolation key

        Returns:
            Success/error response with learning_id and sequence number
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory as tool_func

        # Inject dependencies into the tool function call
        return await tool_func(
            project_id=project_id,
            summary=summary,
            key_outcomes=key_outcomes,
            decisions_made=decisions_made,
            tenant_key=tenant_key,
            db_manager=self.db_manager,
        )

    # Unified Context Tool (Handover 0350a)

    async def fetch_context(
        self,
        product_id: str,
        tenant_key: str,
        project_id: str | None = None,
        categories: list[str] | None = None,
        depth_config: dict[str, Any] | None = None,
        apply_user_config: bool = True,
        format: str = "structured"
    ) -> dict[str, Any]:
        """
        Unified context fetcher - single entry point for all context.

        Handover 0350a: Replaces 9 individual tools with 1 unified tool.
        Saves ~720 tokens in MCP schema overhead.

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            project_id: Project UUID (required for 'project' category)
            categories: Categories to fetch, or ["all"]
            depth_config: Override depth settings per category
            apply_user_config: Apply user's saved priority/depth (default: True)
            format: "structured" (nested) or "flat" (merged)

        Returns:
            Dict with context data organized by category
        """
        from giljo_mcp.tools.context_tools.fetch_context import fetch_context

        return await fetch_context(
            product_id=product_id,
            tenant_key=tenant_key,
            project_id=project_id,
            categories=categories or ["all"],
            depth_config=depth_config,
            apply_user_config=apply_user_config,
            format=format,
            db_manager=self.db_manager
        )

    # File Utilities (Handover 0360 Feature 3)

    async def file_exists(
        self,
        path: str,
        tenant_key: str,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        """
        Check whether a file or directory exists within the allowed workspace.

        Handover 0360 Feature 3: Lightweight file existence checking without
        reading entire file contents. Prevents token waste and improves performance.

        Args:
            path: Path to check (relative or absolute)
            tenant_key: Tenant isolation key
            workspace_root: Optional workspace root (defaults to product workspace)

        Returns:
            Dict with:
                - success: bool
                - path: str (normalized path)
                - exists: bool
                - is_file: bool
                - is_dir: bool
                - error: str (if failed)

        Example response:
            {
                "success": true,
                "path": "src/app.py",
                "exists": true,
                "is_file": true,
                "is_dir": false
            }
        """
        from giljo_mcp.tools.file_utils import file_exists

        return await file_exists(
            path=path,
            tenant_key=tenant_key,
            workspace_root=workspace_root,
        )
