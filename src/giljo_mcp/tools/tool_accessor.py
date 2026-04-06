"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.schemas.service_responses import (
    MessageListResult,
    SendMessageResult,
    WorkflowStatus,
)
from src.giljo_mcp.services.message_routing_service import MessageRoutingService
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.services.task_service import TaskService
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


def _build_setup_instructions(platform: str, download_url: str) -> dict[str, Any]:
    """Build platform-specific extract and config edit instructions for giljo_setup."""
    if platform == "claude_code":
        return {
            "download": f"Download the ZIP: curl -o giljo_setup.zip '{download_url}'",
            "extract_path": "~/.claude/",
            "extract_command": "unzip -o giljo_setup.zip -d ~/.claude/",
            "config_edits": [],
            "cleanup": "rm giljo_setup.zip",
            "post_install": "Restart your CLI tool to activate slash commands and agent templates.",
        }
    if platform == "gemini_cli":
        return {
            "download": f"Download the ZIP: curl -o giljo_setup.zip '{download_url}'",
            "extract_path": "~/.gemini/",
            "extract_command": "unzip -o giljo_setup.zip -d ~/.gemini/",
            "config_edits": [
                {
                    "file": "~/.gemini/settings.json",
                    "action": "merge_json",
                    "value": {"experimental": {"enableAgents": True}},
                    "reason": "Required for Gemini CLI to discover custom agents",
                },
            ],
            "cleanup": "rm giljo_setup.zip",
            "post_install": "Restart your CLI tool to activate slash commands and agent templates.",
        }
    # codex_cli
    return {
        "download": f"Download the ZIP: curl -o giljo_setup.zip '{download_url}'",
        "extract_path": "~/.codex/",
        "extract_command": "unzip -o giljo_setup.zip -d ~/.codex/",
        "config_edits": [
            {
                "file": "~/.codex/config.toml",
                "action": "merge_toml_section",
                "section": "features",
                "value": {"default_mode_request_user_input": True, "multi_agent": True},
                "reason": "Required for interactive skill menus and multi-agent spawning",
            },
            {
                "file": "~/.codex/config.toml",
                "action": "register_agents",
                "reason": (
                    "Register each gil-*.toml file as [agents.gil-<name>] with "
                    "config_file = 'agents/gil-<name>.toml' (relative path), "
                    "model = 'gpt-5.2-codex', model_reasoning_effort = 'medium', "
                    "nickname_candidates = ['gil-<name>']"
                ),
            },
        ],
        "config_merge_rules": {
            "CRITICAL": (
                "config.toml is the user's primary Codex configuration. A corrupt config.toml "
                "will crash Codex on startup (skills/list TUI failure). Follow these rules strictly:"
            ),
            "rules": [
                "NEVER overwrite config.toml — always read-then-merge",
                "Use a TOML parser to read existing config, merge new sections, write back",
                "Do NOT use string substitution, regex, or PowerShell text manipulation",
                "Preserve ALL existing sections not managed by GiljoAI (MCP servers, user prefs, etc.)",
                "TOML values must NOT have doubled quotes — 'agents/gil-analyzer.toml' not ''agents/gil-analyzer.toml''",
                "Back up config.toml before writing: copy to config_backup.toml",
                "After writing, validate the file parses: python -c \"import tomllib; tomllib.load(open('config.toml','rb'))\"",
            ],
            "safe_merge_example": (
                "In Python: import tomllib, tomli_w; "
                "config = tomllib.load(open(path, 'rb')); "
                "config.setdefault('agents', {})['gil-analyzer'] = {"
                "'config_file': 'agents/gil-analyzer.toml', "
                "'model': 'gpt-5.2-codex', "
                "'model_reasoning_effort': 'medium', "
                "'nickname_candidates': ['gil-analyzer']}; "
                "tomli_w.dump(config, open(path, 'wb'))"
            ),
        },
        "cleanup": "rm giljo_setup.zip",
        "post_install": "Restart your CLI tool to activate skills and agent templates.",
    }


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
            websocket_manager=websocket_manager,
        )
        self._message_routing_service = MessageRoutingService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,
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
        project_type: str | None = None,
        series_number: int | None = None,
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

        # Resolve optional type label to project_type_id (Handover 0837b)
        project_type_id = None
        if project_type:
            resolved_type = await self._project_service.get_project_type_by_label(project_type, effective_tenant_key)
            if resolved_type:
                project_type_id = resolved_type.id

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
            project_type_id=project_type_id,
            series_number=series_number,
        )

        logger.info(
            "Created project %s (alias: %s) for tenant %s in product %s",
            project.id,
            project.alias,
            effective_tenant_key,
            product_id,
        )

        # Broadcast WebSocket event so frontend refreshes
        if self._websocket_manager:
            try:
                await self._websocket_manager.broadcast_to_tenant(
                    tenant_key=effective_tenant_key,
                    event_type="project:created",
                    data={"project_id": str(project.id), "name": project.name, "product_id": product_id},
                )
            except (RuntimeError, ValueError, OSError) as e:
                logger.warning(f"Failed to broadcast project:created event: {e}")

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

    # Message Tools (delegates to MessageService / MessageRoutingService)

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
        """Send message to one or more agents (delegates to MessageRoutingService)"""
        return await self._message_routing_service.send_message(
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

        # Broadcast WebSocket event so frontend refreshes
        if self._websocket_manager:
            try:
                await self._websocket_manager.broadcast_to_tenant(
                    tenant_key=effective_tenant_key,
                    event_type="task:created",
                    data={"task_id": task_id, "title": title, "product_id": product_id},
                )
            except (RuntimeError, ValueError, OSError) as e:
                logger.warning(f"Failed to broadcast task:created event: {e}")

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

    async def generate_download_token(
        self, content_type: str, tenant_key: str, platform: str = "claude_code"
    ) -> dict[str, Any]:
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
                    filename=filename,
                )

                # Stage files
                staging_path = await staging.create_staging_directory(tenant_key, token)
                if content_type == "slash_commands":
                    zip_path, message = await staging.stage_slash_commands(staging_path, platform=platform)
                else:
                    zip_path, message = await staging.stage_agent_templates(
                        staging_path, tenant_key, db_session=session, platform=platform
                    )

                if not zip_path:
                    await token_manager.mark_failed(token, message)
                    raise ValidationError(message)

                # Mark ready and build URL
                await token_manager.mark_ready(token)

                # Get server URL from config (same approach as downloads.py)
                from giljo_mcp.config_manager import get_config

                config = get_config()
                host = config.get_nested("services.external_host", "localhost")
                port = config.server.api_port
                protocol = "https" if config.get_nested("features.ssl_enabled", default=False) else "http"
                server_url = f"{protocol}://{host}:{port}"
                download_url = f"{server_url}/api/download/temp/{token}/{filename}"

                token_data = await token_manager.get_token_info(token, tenant_key)

                return {
                    "download_url": download_url,
                    "expires_at": token_data.get("expires_at") if token_data else None,
                    "content_type": content_type,
                    "one_time_use": True,
                }
        except Exception:  # Broad catch: tool boundary, logs and re-raises
            logger.exception("Failed to generate download token")
            raise

    async def bootstrap_setup(self, tenant_key: str, platform: str = "claude_code") -> dict[str, Any]:
        """
        Stage combined slash commands + agent templates ZIP for first-time setup (Handover 0907).

        Returns a download URL for a ZIP containing everything the agent needs.
        Binary transfer — no template content passes through the LLM.
        """
        from giljo_mcp.downloads.token_manager import TokenManager
        from giljo_mcp.file_staging import FileStaging

        try:
            async with self.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                staging = FileStaging(db_session=session)

                filename = "giljo_setup.zip"
                token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type="slash_commands",
                    filename=filename,
                )

                staging_path = await staging.create_staging_directory(tenant_key, token)
                zip_path, message = await staging.stage_combined_setup(
                    staging_path,
                    tenant_key,
                    db_session=session,
                    platform=platform,
                )

                if not zip_path:
                    await token_manager.mark_failed(token, message)
                    raise ValidationError(message)

                await token_manager.mark_ready(token)

                from giljo_mcp.config_manager import get_config

                config = get_config()
                host = config.get_nested("services.external_host", "localhost")
                port = config.server.api_port
                protocol = "https" if config.get_nested("features.ssl_enabled", default=False) else "http"
                server_url = f"{protocol}://{host}:{port}"
                download_url = f"{server_url}/api/download/temp/{token}/{filename}"

                # Build platform-specific install instructions
                instructions = _build_setup_instructions(platform, download_url)

                return {
                    "download_url": download_url,
                    "expires_in_minutes": 15,
                    "platform": platform,
                    "install_instructions": instructions,
                }
        except (ValidationError, ValueError):
            raise
        except Exception:  # Broad catch: tool boundary, logs and re-raises
            logger.exception("Failed to stage bootstrap setup")
            raise

    async def get_agent_templates_for_export(self, tenant_key: str, platform: str) -> dict[str, Any]:
        """
        Export agent templates formatted for the target CLI platform.

        Returns pre-assembled files (Claude Code, Gemini CLI) or structured
        data (Codex CLI) ready for the calling agent to install locally.

        Handover 0836a: Multi-platform agent template export.

        Args:
            tenant_key: Tenant identifier for multi-tenant isolation.
            platform: Target platform — 'claude_code', 'codex_cli', or 'gemini_cli'.

        Returns:
            Dict with platform, agents list, install_paths, template_count, format_version.
        """
        from sqlalchemy import select

        from giljo_mcp.models import AgentTemplate
        from giljo_mcp.template_renderer import select_templates_for_packaging
        from giljo_mcp.tools.agent_template_assembler import AgentTemplateAssembler

        try:
            async with self.get_session_async() as session:
                stmt = (
                    select(AgentTemplate)
                    .where(
                        AgentTemplate.tenant_key == tenant_key,
                        AgentTemplate.is_active,
                    )
                    .order_by(AgentTemplate.name)
                )

                result = await session.execute(stmt)
                all_active = result.scalars().all()

                if not all_active:
                    raise ValidationError(f"No active templates found for tenant: {tenant_key}")

                selected = select_templates_for_packaging(all_active, max_count=8)

                assembler = AgentTemplateAssembler()
                return assembler.assemble(selected, platform)
        except ValidationError:
            raise
        except Exception:  # Broad catch: tool boundary, logs and re-raises
            logger.exception("Failed to export agent templates")
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
        todo_append: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Report job progress (delegates to OrchestrationService).

        Handover 0407: Accept todo_items parameter for simplified progress reporting.
        Handover 0827d: Accept todo_append to add steps without replacing existing ones.
        """
        return await self._orchestration_service.report_progress(
            job_id=job_id,
            progress=progress,
            tenant_key=tenant_key,
            todo_items=todo_items,
            todo_append=todo_append,
        )

    async def complete_job(self, job_id: str, result: dict[str, Any], tenant_key: str | None = None) -> dict[str, Any]:
        """Mark job as complete (delegates to OrchestrationService)"""
        return await self._orchestration_service.complete_job(job_id=job_id, result=result, tenant_key=tenant_key)

    async def reactivate_job(self, job_id: str, tenant_key: str | None = None, reason: str = "") -> dict[str, Any]:
        """Resume work on a completed job (delegates to OrchestrationService). Handover 0827c."""
        return await self._orchestration_service.reactivate_job(job_id=job_id, tenant_key=tenant_key, reason=reason)

    async def dismiss_reactivation(
        self, job_id: str, tenant_key: str | None = None, reason: str = ""
    ) -> dict[str, Any]:
        """Dismiss reactivation and return to complete (delegates to OrchestrationService). Handover 0827c."""
        return await self._orchestration_service.dismiss_reactivation(
            job_id=job_id, tenant_key=tenant_key, reason=reason
        )

    async def set_agent_status(
        self,
        job_id: str,
        status: str,
        reason: str = "",
        wake_in_minutes: int | None = None,
        tenant_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Set agent resting/blocked status (Handover 0880: expanded from report_error)."""
        return await self._orchestration_service.set_agent_status(
            job_id=job_id, status=status, reason=reason, wake_in_minutes=wake_in_minutes, tenant_key=tenant_key
        )

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
            categories: Exactly one category to fetch per call
            depth_config: Override depth settings per category
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
            categories=categories,
            depth_config=depth_config,
            output_format=output_format,
            agent_name=agent_name,  # Handover 0430
            db_manager=self.db_manager,
        )

    # Product Context Tuning (Handover 0831)

    async def submit_tuning_review(
        self,
        product_id: str,
        tenant_key: str,
        proposals: list[dict[str, Any]],
        overall_summary: str | None = None,
    ) -> dict[str, Any]:
        """
        Submit product context tuning proposals after comparing current
        product context against recent project history (Handover 0831).

        Args:
            product_id: Target product UUID
            tenant_key: Tenant isolation key
            proposals: Per-section proposals with drift_detected, evidence, proposed_value
            overall_summary: High-level drift assessment

        Returns:
            Success response with review_id
        """
        from giljo_mcp.tools.submit_tuning_review import submit_tuning_review as tool_func

        return await tool_func(
            product_id=product_id,
            tenant_key=tenant_key,
            proposals=proposals,
            overall_summary=overall_summary,
            db_manager=self.db_manager,
            websocket_manager=self._websocket_manager,
        )

    # Vision Document Analysis (Handover 0842c)

    async def get_vision_doc(
        self,
        product_id: str,
        tenant_key: str,
        chunk: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve vision document with extraction instructions (Handover 0842c)."""
        from giljo_mcp.tools.vision_analysis import gil_get_vision_doc as tool_func

        return await tool_func(
            product_id=product_id,
            tenant_key=tenant_key,
            chunk=chunk,
            db_manager=self.db_manager,
            websocket_manager=self._websocket_manager,
        )

    async def write_product_from_analysis(
        self,
        product_id: str,
        tenant_key: str,
        **fields: Any,
    ) -> dict[str, Any]:
        """Write product fields from vision document analysis (Handover 0842c)."""
        from giljo_mcp.tools.vision_analysis import gil_write_product as tool_func

        return await tool_func(
            product_id=product_id,
            tenant_key=tenant_key,
            db_manager=self.db_manager,
            websocket_manager=self._websocket_manager,
            **fields,
        )

    # Agent Discovery Tools (Handover 0422)
