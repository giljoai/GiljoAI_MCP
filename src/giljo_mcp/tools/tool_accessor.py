"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import and_, select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.services.context_service import ContextService
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.services.task_service import TaskService
from src.giljo_mcp.services.template_service import TemplateService
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

# ============================================================================
# STANDALONE HELPER FUNCTIONS (For Testing and Tenant Isolation)
# ============================================================================


async def activate_project(project_id: str, tenant_key: str, session) -> dict[str, Any]:
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
            select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
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
                select(Product).where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
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
        websocket_manager: Any | None = None,
        test_session: "AsyncSession" | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._test_session = test_session

        # Initialize service layer (Handover 0121 - Phase 1, Handover 0123 - Phase 2 ✅ COMPLETE)
        self._project_service = ProjectService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,  # Fix: Pass WebSocket manager for mission updates
        )
        self._template_service = TemplateService(db_manager, tenant_manager)
        self._task_service = TaskService(db_manager, tenant_manager)
        self._message_service = MessageService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,  # Pass WebSocket manager
        )
        self._context_service = ContextService(db_manager, tenant_manager)
        self._orchestration_service = OrchestrationService(
            db_manager,
            tenant_manager,
            message_service=self._message_service,  # Pass MessageService for WebSocket-enabled messaging
            test_session=test_session,  # Pass test session for transaction sharing (Handover 0358c)
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
        product_id: str | None = None,
        tenant_key: str | None = None,
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

    async def list_projects(self, status: str | None = None, tenant_key: str | None = None) -> list[dict[str, Any]]:
        """List all projects with optional status filter (delegates to ProjectService)"""
        return await self._project_service.list_projects(status=status, tenant_key=tenant_key)

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a specific project by ID (delegates to ProjectService)"""
        # SECURITY FIX: Pass tenant_key from context (Handover 0424 Phase 0)
        tenant_key = self.tenant_manager.get_current_tenant()
        return await self._project_service.get_project(project_id, tenant_key=tenant_key)

    async def switch_project(self, project_id: str) -> dict[str, Any]:
        """Switch to a different project (delegates to ProjectService)"""
        # SECURITY FIX (Handover 0424): Always pass tenant_key for isolation
        tenant_key = self.tenant_manager.get_current_tenant()
        return await self._project_service.switch_project(project_id, tenant_key=tenant_key)

    async def complete_project(self, project_id: str, summary: str | None = None) -> dict[str, Any]:
        """Mark a project as completed (delegates to ProjectService)"""
        # SECURITY FIX (Handover 0424): Always pass tenant_key for isolation
        tenant_key = self.tenant_manager.get_current_tenant()
        return await self._project_service.complete_project(project_id, summary, tenant_key=tenant_key)

    async def cancel_project(self, project_id: str, reason: str | None = None) -> dict[str, Any]:
        """Cancel a project (delegates to ProjectService)"""
        # NOTE: cancel_project needs service-level fix to accept tenant_key
        return await self._project_service.cancel_project(project_id, reason)

    async def restore_project(self, project_id: str) -> dict[str, Any]:
        """Restore a completed or cancelled project (delegates to ProjectService)"""
        # NOTE: restore_project needs service-level fix to accept tenant_key
        return await self._project_service.restore_project(project_id)

    async def update_project_mission(self, project_id: str, mission: str) -> dict[str, Any]:
        """Update the mission field (delegates to ProjectService)"""
        # SECURITY FIX (Handover 0424): Always pass tenant_key for isolation
        tenant_key = self.tenant_manager.get_current_tenant()
        return await self._project_service.update_project_mission(project_id, mission, tenant_key=tenant_key)

    async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str) -> dict[str, Any]:
        """Delegate to OrchestrationService (Handover 0451)"""
        return await self._orchestration_service.update_agent_mission(job_id, tenant_key, mission)

    # Message Tools (delegates to MessageService)

    async def send_message(
        self,
        to_agents: list[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
        from_agent: str | None = None,
        tenant_key: str | None = None,
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

    async def get_messages(self, agent_name: str, project_id: str | None = None) -> dict[str, Any]:
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
        tenant_key: str | None = None,
        exclude_self: bool = True,
        exclude_progress: bool = True,
        message_types: list[str | None] = None,
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
            message_types=message_types,
        )

    async def list_messages(
        self,
        project_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        tenant_key: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        List messages in a project or for a specific agent (delegates to MessageService).

        Handover 0378 Bug 1: Added tenant_key parameter to match MCP tool schema.
        """
        return await self._message_service.list_messages(
            project_id=project_id, status=status, agent_id=agent_id, tenant_key=tenant_key, limit=limit
        )

    # Task Tools

    async def log_task(self, content: str, category: str | None = None, priority: str = "medium") -> dict[str, Any]:
        """Quick task capture (delegates to TaskService)"""
        return await self._task_service.log_task(content=content, category=category, priority=priority)

    async def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        category: str | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new task with optional category support.

        Args:
            title: Task title/summary
            description: Detailed task description
            priority: Task priority (default: "medium")
            category: Optional category (frontend, backend, database, infra, docs, general)
            assigned_to: Optional agent name to assign to (not implemented yet)

        Returns:
            Dict with success status and task_id or error
        """
        # TaskService.create_task calls log_task which accepts category
        # We need to call log_task directly to pass category
        return await self._task_service.log_task(
            content=description,
            category=category or title,  # Use category if provided, otherwise use title
            priority=priority,
        )

    # Task MCP tools retired Dec 2025 - list_tasks, update_task, assign_task, complete_task removed
    # Web interface uses REST API (/api/v1/tasks/) via TaskService directly

    # Context Tools (delegates to ContextService)

    async def get_context_index(self, product_id: str | None = None) -> dict[str, Any]:
        """Get the context index for intelligent querying (delegates to ContextService)"""
        return await self._context_service.get_context_index(product_id=product_id)

    async def get_vision(self, part: int = 1, max_tokens: int = 20000) -> dict[str, Any]:
        """Get the vision document (delegates to ContextService)"""
        return await self._context_service.get_vision(part=part, max_tokens=max_tokens)

    async def get_vision_index(self) -> dict[str, Any]:
        """Get the vision document index (delegates to ContextService)"""
        return await self._context_service.get_vision_index()

    async def get_product_settings(self, product_id: str | None = None) -> dict[str, Any]:
        """Get all product settings for analysis (delegates to ContextService)"""
        return await self._context_service.get_product_settings(product_id=product_id)

    # Template Tools (delegates to TemplateService)

    async def list_templates(self) -> dict[str, Any]:
        """List available templates (delegates to TemplateService)"""
        return await self._template_service.list_templates()

    async def create_template(self, name: str, content: str, **kwargs) -> dict[str, Any]:
        """Create a new template (delegates to TemplateService)"""
        return await self._template_service.create_template(name=name, content=content, **kwargs)

    async def update_template(self, template_id: str, **kwargs) -> dict[str, Any]:
        """Update a template (delegates to TemplateService)"""
        return await self._template_service.update_template(template_id=template_id, **kwargs)

    # Agent Export Tools (Handover 0084)

    async def export_agents(
        self,
        product_path: str | None = None,
        personal: bool = False,
        product_id: str | None = None,
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
        product_id: str | None = None,
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
        product_id: str | None = None,
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

    async def generate_download_token(self, content_type: str, tenant_key: str) -> dict[str, Any]:
        """
        Generate one-time download URL for agent templates or slash commands.

        The MCP session is already authenticated, so no API key needed.
        Returns download_url valid for 15 minutes.

        Handover 0384: Fix for slash command hallucinating API keys.
        """
        from giljo_mcp.downloads.token_manager import TokenManager
        from giljo_mcp.file_staging import FileStaging

        if content_type not in ["agent_templates", "slash_commands"]:
            return {"success": False, "error": "content_type must be 'agent_templates' or 'slash_commands'"}

        try:
            async with self.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                staging = FileStaging(db_session=session)

                # Generate token
                filename = "slash_commands.zip" if content_type == "slash_commands" else "agent_templates.zip"
                token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type=content_type,
                    metadata={"filename": filename},
                )

                # Stage files
                staging_path = await staging.create_staging_directory(tenant_key, token)
                if content_type == "slash_commands":
                    zip_path, message = await staging.stage_slash_commands(staging_path)
                else:
                    zip_path, message = await staging.stage_agent_templates(
                        staging_path, tenant_key, db_session=session
                    )

                if not zip_path:
                    await token_manager.mark_failed(token, message)
                    return {"success": False, "error": message}

                # Mark ready and build URL
                await token_manager.mark_ready(token)

                # Get server URL from config (same approach as downloads.py)
                from pathlib import Path

                import yaml

                from giljo_mcp.config_manager import get_config

                config = get_config()
                config_path = Path.cwd() / "config.yaml"
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                host = config_data.get("services", {}).get("external_host", "localhost")
                port = config.server.api_port
                server_url = f"http://{host}:{port}"
                download_url = f"{server_url}/api/download/temp/{token}/{filename}"

                token_data = await token_manager.get_token_info(token, tenant_key)

                return {
                    "success": True,
                    "download_url": download_url,
                    "expires_at": token_data.get("expires_at") if token_data else None,
                    "content_type": content_type,
                    "one_time_use": True,
                }
        except Exception as e:
            logger.exception(f"Failed to generate download token: {e}")
            return {"success": False, "error": str(e)}

    async def get_orchestrator_instructions(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Delegate to OrchestrationService (Handover 0451)"""
        return await self._orchestration_service.get_orchestrator_instructions(job_id, tenant_key)

    async def spawn_agent_job(
        self,
        agent_display_name: str,
        agent_name: str,
        mission: str,
        project_id: str,
        tenant_key: str,
        parent_job_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an agent job (delegates to OrchestrationService)"""
        return await self._orchestration_service.spawn_agent_job(
            agent_display_name=agent_display_name,
            agent_name=agent_name,
            mission=mission,
            project_id=project_id,
            tenant_key=tenant_key,
            parent_job_id=parent_job_id,
        )

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Get agent-specific mission (delegates to OrchestrationService). Handover 0381: job_id contract."""
        return await self._orchestration_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)

    async def get_workflow_status(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """Get workflow status for a project (delegates to OrchestrationService)"""
        return await self._orchestration_service.get_workflow_status(project_id=project_id, tenant_key=tenant_key)

    # Agent Coordination Tools

    async def get_pending_jobs(self, agent_display_name: str, tenant_key: str) -> dict[str, Any]:
        """Get pending jobs for agent display name (delegates to OrchestrationService)"""
        return await self._orchestration_service.get_pending_jobs(
            agent_display_name=agent_display_name, tenant_key=tenant_key
        )

    async def acknowledge_job(self, job_id: str, agent_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Acknowledge job assignment (delegates to OrchestrationService)"""
        return await self._orchestration_service.acknowledge_job(job_id=job_id, agent_id=agent_id)

    async def report_progress(
        self,
        job_id: str,
        tenant_key: str | None = None,
        progress: dict[str, Any] | None = None,
        todo_items: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Report job progress (delegates to OrchestrationService).

        Handover 0407: Accept todo_items parameter for simplified progress reporting.
        Agents can now send todo_items directly instead of wrapping in progress dict.
        """
        return await self._orchestration_service.report_progress(
            job_id=job_id,
            progress=progress,
            tenant_key=tenant_key,
            todo_items=todo_items,
        )

    async def complete_job(self, job_id: str, result: dict[str, Any], tenant_key: str | None = None) -> dict[str, Any]:
        """Mark job as complete (delegates to OrchestrationService)"""
        return await self._orchestration_service.complete_job(job_id=job_id, result=result)

    async def report_error(self, job_id: str, error: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Report job error (delegates to OrchestrationService)"""
        return await self._orchestration_service.report_error(job_id=job_id, error=error)

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
                        "agent_display_name": str,
                        "status": str,
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
        """
        Create successor orchestrator context via 360 Memory (Handover 0461f).

        SIMPLIFIED: Writes session context to 360 Memory and resets context_used.
        No new AgentExecution rows created. Same agent_id continues.

        Use fetch_context(categories=['memory_360']) in new session to retrieve context.
        """
        return await self._orchestration_service.create_successor_orchestrator(current_job_id, tenant_key, reason)

    async def check_succession_status(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Delegate to OrchestrationService (Handover 0451)"""
        return await self._orchestration_service.check_succession_status(job_id, tenant_key)

    async def gil_launch(self, project_id: str) -> dict[str, Any]:
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}
            if not project_id:
                return {"success": False, "error": "project_id is required"}
            from datetime import datetime, timezone

            from sqlalchemy import select

            from giljo_mcp.models import Project
            from giljo_mcp.models.agent_identity import AgentJob

            async with self.get_session_async() as session:
                pr = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = pr.scalar_one_or_none()
                if not project:
                    return {"success": False, "error": "Project not found"}
                if not project.mission or not project.mission.strip():
                    return {
                        "success": False,
                        "error": "Project mission has not been created. Please complete staging first.",
                    }
                ag = await session.execute(
                    select(AgentJob).where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
                )
                agents = ag.scalars().all()
                if not agents:
                    return {
                        "success": False,
                        "error": "No agents have been spawned for this project. Please complete staging first.",
                    }
                if hasattr(project, "staging_status"):
                    project.staging_status = "launching"
                    project.updated_at = datetime.now(timezone.utc)
                    await session.commit()
            return {"success": True, "project_id": project_id, "agent_count": len(agents)}
        except Exception as e:
            logger.exception(f"gil_launch failed: {e}")
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

    async def write_360_memory(
        self,
        project_id: str,
        tenant_key: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        entry_type: str = "project_completion",
        author_job_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Write a 360 memory entry for project completion or handover (Handover 0412).

        This method allows agents to create entries in the product_memory_entries table
        during handovers or at project completion.

        Args:
            project_id: UUID of the project
            tenant_key: Tenant isolation key
            summary: 2-3 paragraph summary of work accomplished
            key_outcomes: 3-5 specific achievements
            decisions_made: 3-5 architectural/design decisions
            entry_type: Type of entry ("project_completion", "handover_closeout", or "session_handover")
            author_job_id: Job ID of agent writing entry (optional)

        Returns:
            Success/error response with sequence number
        """
        from giljo_mcp.tools.write_360_memory import write_360_memory as tool_func

        # Inject dependencies into the tool function call
        return await tool_func(
            project_id=project_id,
            tenant_key=tenant_key,
            summary=summary,
            key_outcomes=key_outcomes,
            decisions_made=decisions_made,
            entry_type=entry_type,
            author_job_id=author_job_id,
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
        format: str = "structured",
        agent_name: str | None = None,  # Handover 0430: Required for self_identity category
    ) -> dict[str, Any]:
        """
        Unified context fetcher - single entry point for all context.

        Handover 0350a: Replaces 9 individual tools with 1 unified tool.
        Saves ~720 tokens in MCP schema overhead.
        Handover 0430: Added agent_name parameter for self_identity category.

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            project_id: Project UUID (required for 'project' category)
            categories: Categories to fetch, or ["all"]
            depth_config: Override depth settings per category
            apply_user_config: Apply user's saved priority/depth (default: True)
            format: "structured" (nested) or "flat" (merged)
            agent_name: Agent template name (required for 'self_identity' category)

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
            agent_name=agent_name,  # Handover 0430
            db_manager=self.db_manager,
        )

    # Agent Discovery Tools (Handover 0422)

    async def get_available_agents(
        self, tenant_key: str, active_only: bool = True, depth: str = "full"
    ) -> dict[str, Any]:
        """
        Get available agent templates with staleness info.

        Wraps agent_discovery.get_available_agents() for HTTP MCP exposure.

        Args:
            tenant_key: Tenant isolation key
            active_only: Include only active templates (default: True)
            depth: Detail level - "type_only" (name/role/version) or "full" (includes description)

        Returns:
            Dict with agents list and staleness warning (if applicable):
            {
                "success": True,
                "data": {
                    "agents": [
                        {
                            "name": str,
                            "role": str,
                            "version_tag": str,
                            "may_be_stale": bool,
                            "last_exported_at": str,
                            "updated_at": str,
                            "description": str,  # Only if depth="full"
                            "expected_filename": str,  # Only if depth="full"
                            "created_at": str  # Only if depth="full"
                        }
                    ],
                    "count": int,
                    "fetched_at": str,
                    "note": str,
                    "staleness_warning": {  # Only if stale agents detected
                        "has_stale_agents": bool,
                        "stale_count": int,
                        "stale_agents": list[str],
                        "action_required": str,
                        "options": list[str]
                    }
                }
            }

        Handover 0422: Added for HTTP MCP exposure of agent discovery tool.
        """
        from src.giljo_mcp.tools.agent_discovery import get_available_agents as _get_available_agents

        async with self.get_session_async() as session:
            return await _get_available_agents(session, tenant_key, depth=depth)
