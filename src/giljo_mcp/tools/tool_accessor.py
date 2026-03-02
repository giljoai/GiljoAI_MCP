"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp._config_io import read_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.schemas.service_responses import (
    MessageListResult,
    SendMessageResult,
    WorkflowStatus,
)
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.services.task_service import TaskService
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ToolAccessor:
    """Provides direct access to MCP tool functionality for API"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        websocket_manager: Any | None = None,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._test_session = test_session

        # Initialize service layer (Handover 0121 - Phase 1, Handover 0123 - Phase 2 ✅ COMPLETE)
        # Note: ProductService requires tenant_key directly, we'll pass it when needed
        self._product_service = None  # Lazy initialization per-request
        self._project_service = ProjectService(
            db_manager,
            tenant_manager,
            test_session=test_session,
            websocket_manager=websocket_manager,  # Fix: Pass WebSocket manager for mission updates
        )
        self._task_service = TaskService(db_manager, tenant_manager)
        self._message_service = MessageService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,  # Pass WebSocket manager
        )
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
        mission: str = "",
        description: str = "",
        product_id: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project bound to the active product.

        Args:
            name: Project name (required)
            mission: AI-generated mission statement (default: "" - orchestrator fills later)
            description: Human-written project description (default: "")
            product_id: Parent product ID (auto-resolved from active product if not provided)
            tenant_key: Tenant isolation key (injected by MCP security layer)

        Returns:
            Dict with success status, project_id, alias, and metadata

        Raises:
            ValidationError: If no active product is set for the tenant
        """
        # Validate required fields (description validated at MCP schema layer)
        if not name or not name.strip():
            raise ValidationError(
                "Project name is required and cannot be empty.",
                context={"operation": "create_project"},
            )
        name = name.strip()
        description = description.strip() if description else ""

        # Resolve effective tenant key
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        # Resolve product_id from active product if not explicitly provided
        if not product_id:
            product_service = ProductService(
                db_manager=self.db_manager,
                tenant_key=effective_tenant_key,
                websocket_manager=self._websocket_manager,
                test_session=self._test_session,
            )
            active_product = await product_service.get_active_product()

            if not active_product:
                raise ValidationError(
                    "No active product set. Please activate a product first.",
                    context={
                        "tenant_key": effective_tenant_key,
                        "operation": "create_project",
                    },
                )

            product_id = active_product.id

        # Delegate to ProjectService (always create as inactive)
        project = await self._project_service.create_project(
            name=name,
            mission=mission,
            description=description,
            product_id=product_id,
            tenant_key=effective_tenant_key,
            status="inactive",
        )

        logger.info(
            "Created project %s (alias: %s) for tenant %s in product %s",
            project.id,
            project.alias,
            effective_tenant_key,
            product_id,
        )

        return {
            "success": True,
            "project_id": project.id,
            "alias": project.alias,
            "name": project.name,
            "description": project.description,
            "mission": project.mission,
            "status": project.status,
            "product_id": project.product_id,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "message": f"Project '{project.name}' created successfully",
        }

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
    ) -> SendMessageResult:
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

    async def receive_messages(
        self,
        agent_id: str,
        limit: int = 10,
        tenant_key: str | None = None,
        exclude_self: bool = True,
        exclude_progress: bool = True,
        message_types: list[str | None] = None,
    ) -> MessageListResult:
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
            MessageListResult with messages list and count
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
    ) -> MessageListResult:
        """
        List messages in a project or for a specific agent (delegates to MessageService).

        Handover 0378 Bug 1: Added tenant_key parameter to match MCP tool schema.
        """
        return await self._message_service.list_messages(
            project_id=project_id, status=status, agent_id=agent_id, tenant_key=tenant_key, limit=limit
        )

    # Task Tools

    async def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        category: str | None = None,
        assigned_to: str | None = None,
        tenant_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new task bound to the active product.

        Args:
            title: Task title/summary
            description: Detailed task description
            priority: Task priority (default: "medium")
            category: Optional category (frontend, backend, database, infra, docs, general)
            assigned_to: Optional agent name to assign to (not implemented yet)
            tenant_key: Tenant isolation key (injected by MCP security layer)

        Returns:
            Dict with success status and task_id or error

        Raises:
            ValidationError: If no active product is set for the tenant

        Example:
            >>> result = await tool_accessor.create_task(
            ...     title="Fix login bug",
            ...     description="Users cannot login with email",
            ...     priority="high",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(result["task_id"])
        """
        # Use tenant_key from parameter or fall back to tenant_manager
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        # Fetch active product for tenant (Handover 0433 Phase 3)
        # ProductService requires tenant_key in constructor, instantiate per-request
        product_service = ProductService(
            db_manager=self.db_manager,
            tenant_key=effective_tenant_key,
            websocket_manager=self._websocket_manager,
            test_session=self._test_session,
        )
        active_product = await product_service.get_active_product()

        if not active_product:
            raise ValidationError(
                "No active product set. Please activate a product first.",
                context={
                    "tenant_key": effective_tenant_key,
                    "operation": "create_task",
                },
            )

        product_id = active_product.id

        # Default category to "general" when not provided (Bug 3 fix)
        effective_category = category or "general"

        # Create task with product binding and tenant isolation
        task_id = await self._task_service.log_task(
            content=title,
            title=title,
            description=description,
            category=effective_category,
            priority=priority,
            product_id=product_id,
            tenant_key=effective_tenant_key,
        )

        logger.info(
            "Created task %s for tenant %s in product %s",
            task_id,
            effective_tenant_key,
            product_id,
        )

        return {
            "success": True,
            "task_id": task_id,
            "title": title,
            "priority": priority,
            "category": effective_category,
            "product_id": product_id,
            "message": f"Task '{title}' created successfully",
        }

    # Orchestration Tools

    async def health_check(self) -> dict[str, Any]:
        """MCP server health check"""
        from giljo_mcp.services.orchestration_service import OrchestrationService

        return await OrchestrationService.health_check()

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
            raise ValidationError("content_type must be 'agent_templates' or 'slash_commands'")

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
                    raise ValidationError(message)

                # Mark ready and build URL
                await token_manager.mark_ready(token)

                # Get server URL from config (same approach as downloads.py)
                from giljo_mcp.config_manager import get_config

                config = get_config()
                config_data = read_config()
                host = config_data.get("services", {}).get("external_host", "localhost")
                port = config.server.api_port
                server_url = f"http://{host}:{port}"
                download_url = f"{server_url}/api/download/temp/{token}/{filename}"

                token_data = await token_manager.get_token_info(token, tenant_key)

                return {
                    "download_url": download_url,
                    "expires_at": token_data.get("expires_at") if token_data else None,
                    "content_type": content_type,
                    "one_time_use": True,
                }
        except Exception:
            logger.exception("Failed to generate download token")
            raise

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
        phase: int | None = None,
        predecessor_job_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an agent job (delegates to OrchestrationService)"""
        return await self._orchestration_service.spawn_agent_job(
            agent_display_name=agent_display_name,
            agent_name=agent_name,
            mission=mission,
            project_id=project_id,
            tenant_key=tenant_key,
            parent_job_id=parent_job_id,
            phase=phase,
            predecessor_job_id=predecessor_job_id,
        )

    async def get_agent_result(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Fetch completion result for a completed agent job (delegates to OrchestrationService). Handover 0497e."""
        result = await self._orchestration_service.get_agent_result(job_id=job_id, tenant_key=tenant_key)
        if result is None:
            return {"result": None, "message": "No completion result found for this job"}
        return {"result": result}

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Get agent-specific mission (delegates to OrchestrationService). Handover 0381: job_id contract."""
        return await self._orchestration_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)

    async def get_workflow_status(
        self, project_id: str, tenant_key: str, exclude_job_id: str | None = None
    ) -> WorkflowStatus:
        """Get workflow status for a project (delegates to OrchestrationService)"""
        return await self._orchestration_service.get_workflow_status(
            project_id=project_id, tenant_key=tenant_key, exclude_job_id=exclude_job_id
        )

    # Agent Coordination Tools

    async def get_pending_jobs(self, agent_display_name: str, tenant_key: str) -> dict[str, Any]:
        """Get pending jobs for agent display name (delegates to OrchestrationService)"""
        return await self._orchestration_service.get_pending_jobs(
            agent_display_name=agent_display_name, tenant_key=tenant_key
        )

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
        return await self._orchestration_service.complete_job(job_id=job_id, result=result, tenant_key=tenant_key)

    async def report_error(
        self, job_id: str, error: str, tenant_key: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Report job error (delegates to OrchestrationService). Handover 0491: severity param removed."""
        return await self._orchestration_service.report_error(job_id=job_id, error=error, tenant_key=tenant_key)

    async def close_project_and_update_memory(
        self,
        project_id: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        tenant_key: str,
        force: bool = False,
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
            force: If True, auto-decommission active agents and close anyway

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
            force=force,
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
        output_format: str = "structured",
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
            output_format=output_format,
            agent_name=agent_name,  # Handover 0430
            db_manager=self.db_manager,
        )

    # Agent Discovery Tools (Handover 0422)
