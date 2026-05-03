# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.schemas.service_responses import (
    MessageListResult,
    SendMessageResult,
    WorkflowStatus,
)
from giljo_mcp.services.message_routing_service import MessageRoutingService
from giljo_mcp.services.message_service import MessageService
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.services.task_service import TaskService
from giljo_mcp.tenant import TenantManager
from giljo_mcp.tools.setup_instructions import build_setup_instructions


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
            message_service=self._message_service,
            test_session=test_session,
        )

        # Sprint 002f: Direct sub-service references for collapsed pass-throughs
        self._mission_service = self._orchestration_service._mission
        self._progress_service = self._orchestration_service._progress
        self._agent_state_service = self._orchestration_service._agent_state
        self._workflow_status_service = self._orchestration_service._workflow_status
        self._job_completion_service = self._orchestration_service._job_completion

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
        subseries: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project bound to the active product. Sprint 002f: delegates to ProjectService."""
        return await self._project_service.create_project_for_mcp(
            name=name,
            mission=mission,
            description=description,
            product_id=product_id,
            tenant_key=tenant_key,
            project_type=project_type,
            series_number=series_number,
            subseries=subseries,
            websocket_manager=self._websocket_manager,
        )

    async def list_projects(
        self,
        status_filter: str | None = None,
        summary_only: bool = True,
        depth: int = 0,
        tenant_key: str | None = None,
        # v1.2.1 server-side filtering parameters
        status: str | list[str] | None = None,
        project_type: str | list[str] | None = None,
        taxonomy_alias_prefix: str | None = None,
        created_after: Any = None,
        created_before: Any = None,
        completed_after: Any = None,
        completed_before: Any = None,
        include_completed: bool = False,
        hidden: bool | None = None,
    ) -> dict[str, Any]:
        """List projects for active product (v1.2.1: server-side filtering).

        Default returns only projects in active lifecycle (excludes completed
        and cancelled). The `hidden` field is per-row UI declutter and does
        NOT affect default visibility -- agent sees hidden and non-hidden alike.
        Pass include_completed=True to retrieve archived projects. Pass
        hidden=True|False to filter explicitly when needed (rare).

        Sprint 002f: delegates to ProjectService.
        """
        return await self._project_service.list_projects_for_mcp(
            status_filter=status_filter,
            summary_only=summary_only,
            depth=depth,
            tenant_key=tenant_key,
            websocket_manager=self._websocket_manager,
            status=status,
            project_type=project_type,
            taxonomy_alias_prefix=taxonomy_alias_prefix,
            created_after=created_after,
            created_before=created_before,
            completed_after=completed_after,
            completed_before=completed_before,
            include_completed=include_completed,
            hidden=hidden,
        )

    async def update_project_metadata(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        tenant_key: str | None = None,
        project_type: str | None = None,
        series_number: int | None = None,
        subseries: str | None = None,
    ) -> dict[str, Any]:
        """Update project metadata. Sprint 002f: delegates to ProjectService."""
        return await self._project_service.update_project_metadata_for_mcp(
            project_id=project_id,
            name=name,
            description=description,
            status=status,
            tenant_key=tenant_key,
            project_type=project_type,
            series_number=series_number,
            subseries=subseries,
            websocket_manager=self._websocket_manager,
        )

    async def update_project_mission(self, project_id: str, mission: str) -> dict[str, Any]:
        """Update the mission field (delegates to ProjectService)"""
        # SECURITY FIX (Handover 0424): Always pass tenant_key for isolation
        tenant_key = self.tenant_manager.get_current_tenant()
        return await self._project_service.update_project_mission(project_id, mission, tenant_key=tenant_key)

    async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str) -> dict[str, Any]:
        """Delegate to MissionService (sprint 002f: collapsed via OrchestrationService)."""
        return await self._mission_service.update_agent_mission(job_id, tenant_key, mission)

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
        requires_action: bool = False,
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
            requires_action=requires_action,
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

    async def inspect_messages(
        self,
        project_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        tenant_key: str | None = None,
        limit: int | None = None,
    ) -> MessageListResult:
        """
        Inspect messages in a project or for a specific agent (read-only, delegates to MessageService).

        Renamed from list_messages to differentiate from receive_messages (which auto-acknowledges).
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
        """Create a task bound to active product. Sprint 002f: delegates to TaskService."""
        return await self._task_service.create_task_for_mcp(
            title=title,
            description=description,
            priority=priority,
            category=category,
            assigned_to=assigned_to,
            tenant_key=tenant_key,
            db_manager=self.db_manager,
            websocket_manager=self._websocket_manager,
        )

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

                # MCP tool context has no FastAPI request, so we can't use
                # request.base_url here. Fall back to GILJO_PUBLIC_URL env var
                # (set in .env.demo / SaaS deploys). CE default covers localhost.
                server_url = os.environ.get("GILJO_PUBLIC_URL", "http://localhost:7272")
                download_url = f"{server_url}/api/download/temp/{token}/{filename}"

                token_data = await token_manager.get_token_info(token, tenant_key)

                return {
                    "download_url": download_url,
                    "expires_at": token_data.get("expires_at") if token_data else None,
                    "content_type": content_type,
                    "one_time_use": True,
                }
        except Exception as _exc:  # Broad catch: tool boundary, logs and re-raises
            logger.exception("Failed to generate download token")
            raise

    async def bootstrap_setup(
        self,
        tenant_key: str,
        platform: str = "claude_code",
        user_id: str | None = None,
    ) -> dict[str, Any]:
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

                # IMP-0023: per-user skills-version stamping removed.

                # MCP tool context has no FastAPI request, so we can't use
                # request.base_url here. Fall back to GILJO_PUBLIC_URL env var
                # (set in .env.demo / SaaS deploys). CE default covers localhost.
                server_url = os.environ.get("GILJO_PUBLIC_URL", "http://localhost:7272")
                download_url = f"{server_url}/api/download/temp/{token}/{filename}"

                # Build natural-language install prompt the LLM will execute
                instructions = build_setup_instructions(platform, download_url)

                return {
                    "status": "ready",
                    "platform": platform,
                    "expires_in_minutes": 15,
                    "action_required": instructions,
                }
        except (ValidationError, ValueError):
            raise
        except Exception as _exc:  # Broad catch: tool boundary, logs and re-raises
            logger.exception("Failed to stage bootstrap setup")
            raise

    async def list_agent_templates(self, tenant_key: str, platform: str) -> dict[str, Any]:
        """
        Export agent templates formatted for the target CLI platform.

        Returns pre-assembled files (Claude Code, Gemini CLI) or structured
        data (Codex CLI) ready for the calling agent to install locally.

        Templates are tenant-scoped: all active templates for the tenant are included.

        Handover 0836a: Multi-platform agent template export.

        Args:
            tenant_key: Tenant identifier for multi-tenant isolation.
            platform: Target platform -- 'claude_code', 'codex_cli', or 'gemini_cli'.

        Returns:
            Dict with platform, agents list, install_paths, template_count, format_version.
        """
        from sqlalchemy import select

        from giljo_mcp.models import AgentTemplate
        from giljo_mcp.template_renderer import select_templates_for_packaging
        from giljo_mcp.tools.agent_template_assembler import AgentTemplateAssembler

        try:
            async with self.get_session_async() as session:
                # Tenant-scoped query for active templates
                stmt = (
                    select(AgentTemplate)
                    .where(
                        AgentTemplate.tenant_key == tenant_key,
                        AgentTemplate.is_active,
                    )
                    .order_by(AgentTemplate.name)
                )

                result = await session.execute(stmt)
                all_active = list(result.scalars().all())

                if not all_active:
                    raise ValidationError("No active templates found for this tenant")

                selected = select_templates_for_packaging(all_active, max_count=8)

                assembler = AgentTemplateAssembler()
                response = assembler.assemble(selected, platform)

                # Update last_exported_at via TemplateService (write discipline)
                from giljo_mcp.services.template_service import TemplateService

                template_svc = TemplateService(
                    db_manager=self.db_manager,
                    tenant_manager=self.tenant_manager,
                )
                template_ids = [str(t.id) for t in selected]
                await template_svc.mark_templates_exported(template_ids, tenant_key)

                return response
        except ValidationError:
            raise
        except Exception as _exc:  # Broad catch: tool boundary, logs and re-raises
            logger.exception("Failed to export agent templates")
            raise

    async def get_orchestrator_instructions(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Delegate to MissionService (sprint 002f: collapsed via OrchestrationService)."""
        return await self._mission_service.get_orchestrator_instructions(job_id, tenant_key)

    async def spawn_job(
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
        """Create an agent job (delegates to OrchestrationService)."""
        return await self._orchestration_service.spawn_job(
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
        """Get agent-specific mission (delegates to MissionService). Sprint 002f: collapsed."""
        return await self._mission_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)

    async def get_workflow_status(
        self, project_id: str, tenant_key: str, exclude_job_id: str | None = None
    ) -> WorkflowStatus:
        """Get workflow status for a project (delegates to WorkflowStatusService). Sprint 002f: collapsed."""
        return await self._workflow_status_service.get_workflow_status(
            project_id=project_id, tenant_key=tenant_key, exclude_job_id=exclude_job_id
        )

    # Agent Coordination Tools

    async def get_pending_jobs(self, agent_display_name: str, tenant_key: str) -> dict[str, Any]:
        """Get pending jobs for agent display name (delegates to OrchestrationService)."""
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
        return await self._progress_service.report_progress(
            job_id=job_id,
            progress=progress,
            tenant_key=tenant_key,
            todo_items=todo_items,
            todo_append=todo_append,
        )

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, Any],
        tenant_key: str | None = None,
        acknowledge_closeout_todo: bool = False,
        acknowledge_messages_on_complete: bool = False,
    ) -> dict[str, Any]:
        """Mark job as complete (delegates to JobCompletionService). Sprint 002f: collapsed.

        Args:
            job_id: Job UUID.
            result: Completion result dict.
            tenant_key: Optional tenant key (uses current if not provided).
            acknowledge_closeout_todo: When True, the gate auto-completes any
                incomplete TODOs whose content describes the closeout itself
                (e.g. "Closeout: complete orchestrator job"). Use this from
                the orchestrator closeout call where the closeout TODO IS the
                very call being made — avoids the chicken-and-egg of needing
                to mark a "call complete_job" TODO completed before calling
                complete_job. Non-closeout incomplete TODOs still block.
            acknowledge_messages_on_complete: When True, the gate marks all
                unread messages addressed to this agent (within tenant+project)
                as ``acknowledged`` before evaluating. Mirror of
                ``acknowledge_closeout_todo`` for the messages gate. Use this
                escape hatch when an agent is stuck in a
                reactivation-on-stale-message loop and needs to close out
                without manually draining its inbox. The TODOs gate is
                independent — this flag does NOT bypass incomplete TODOs.
        """
        return await self._job_completion_service.complete_job(
            job_id=job_id,
            result=result,
            tenant_key=tenant_key,
            acknowledge_closeout_todo=acknowledge_closeout_todo,
            acknowledge_messages_on_complete=acknowledge_messages_on_complete,
        )

    async def close_job(self, job_id: str, tenant_key: str | None = None) -> dict[str, Any]:
        """Close a completed job (final acceptance). Sprint 002f: collapsed."""
        return await self._agent_state_service.close_job(job_id=job_id, tenant_key=tenant_key)

    async def reactivate_job(self, job_id: str, tenant_key: str | None = None, reason: str = "") -> dict[str, Any]:
        """Resume work on a completed job (delegates to AgentStateService). Sprint 002f: collapsed."""
        return await self._agent_state_service.reactivate_job(job_id=job_id, tenant_key=tenant_key, reason=reason)

    async def dismiss_reactivation(
        self, job_id: str, tenant_key: str | None = None, reason: str = ""
    ) -> dict[str, Any]:
        """Dismiss reactivation and return to complete (delegates to AgentStateService). Sprint 002f: collapsed."""
        return await self._agent_state_service.dismiss_reactivation(job_id=job_id, tenant_key=tenant_key, reason=reason)

    async def set_agent_status(
        self,
        job_id: str,
        status: str,
        reason: str = "",
        wake_in_minutes: int | None = None,
        tenant_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Set agent resting/blocked status. Sprint 002f: collapsed to AgentStateService."""
        return await self._agent_state_service.set_agent_status(
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
        git_commits: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
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
            git_commits: Agent-supplied git commits (from local git log)
            tags: Orchestrator-supplied tags from the 16-entry controlled
                vocabulary (CONTROLLED_TAG_VOCABULARY in MemoryEntryWriteSchema).
                None or [] persists with empty tags; invalid tags are rejected
                with MemoryEntryWriteValidationError.

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
            git_commits=git_commits,
            tags=tags,
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
        git_commits: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
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
            entry_type: Type of entry. Workers: baseline, decision, architecture, discovery.
                Orchestrator-only: project_completion, session_handover, action_required.
                Legacy: handover_closeout (preserved for back-compat).
            author_job_id: Job ID of agent writing entry (optional)
            git_commits: Agent-supplied git commits (from local git log)
            tags: Tags for categorization (e.g. 'action_required:description')

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
            git_commits=git_commits,
            tags=tags,
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
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Submit product context tuning proposals after comparing current
        product context against recent project history (Handover 0831).

        Args:
            product_id: Target product UUID
            tenant_key: Tenant isolation key
            proposals: Per-section proposals with drift_detected, evidence, proposed_value
            overall_summary: High-level drift assessment
            force: If True, allow overwriting populated JSONB fields

        Returns:
            Success response with review_id
        """
        from giljo_mcp.tools.submit_tuning_review import submit_tuning_review as tool_func

        return await tool_func(
            product_id=product_id,
            tenant_key=tenant_key,
            proposals=proposals,
            overall_summary=overall_summary,
            force=force,
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
        from giljo_mcp.tools.vision_analysis import get_vision_doc as tool_func

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
        force: bool = False,
        **fields: Any,
    ) -> dict[str, Any]:
        """Write product fields from vision document analysis (Handover 0842c)."""
        from giljo_mcp.tools.vision_analysis import update_product_fields as tool_func

        return await tool_func(
            product_id=product_id,
            tenant_key=tenant_key,
            db_manager=self.db_manager,
            websocket_manager=self._websocket_manager,
            force=force,
            **fields,
        )

    # Agent Discovery Tools (Handover 0422)
