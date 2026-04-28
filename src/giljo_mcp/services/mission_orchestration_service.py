# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MissionOrchestrationService - Orchestrator instruction building.

Extracted from MissionService (Handover 0950n) to keep modules under 1000 lines.

Responsibilities:
- get_orchestrator_instructions (public entry point)
- Building orchestrator context from database
- Staging redirect checks
- Assembling the orchestrator response dict
- Execution-mode-specific field building (CLI rules / phase assignment)
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    OrchestrationError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.repositories.mission_repository import MissionRepository
from giljo_mcp.services.protocol_builder import (
    _build_orchestrator_protocol,
    _get_user_config,
)
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class MissionOrchestrationService:
    """
    Service for building orchestrator instructions.

    Extracted from MissionService to reduce module size.
    Handles the get_orchestrator_instructions flow end-to-end.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
        websocket_manager: Optional[Any] = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._repo = MissionRepository()

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.
        """
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    def _build_execution_mode_fields(self, execution_mode: str, templates: list, job_id: str) -> dict[str, Any]:
        """Build execution-mode-specific response fields (CLI rules or phase assignment)."""
        fields: dict[str, Any] = {}

        cli_modes = ("claude_code_cli", "codex_cli", "gemini_cli")

        if execution_mode in cli_modes:
            allowed_agent_names = [t.name for t in templates]

            # Handover 0389: Build dynamic example from actual allowed agent names
            example_agents = allowed_agent_names[:2] if len(allowed_agent_names) >= 2 else allowed_agent_names
            example_str = ", ".join(f"'{n}'" for n in example_agents) if example_agents else "'implementer'"

            # Platform-specific spawning syntax
            if execution_mode == "codex_cli":
                task_tool_mapping = (
                    "spawn_agent(agent='gil-{agent_name}') where agent_name comes from spawn_job. "
                    "CRITICAL: prepend 'gil-' to every agent_name when using Codex CLI."
                )
                template_locations = [
                    "~/.codex/agents/",
                    "{project}/.codex/agents/",
                ]
            elif execution_mode == "gemini_cli":
                task_tool_mapping = "@{agent_name} or /agent {agent_name} — agent_name is used as-is (no prefix)."
                template_locations = [
                    "~/.gemini/agents/",
                    "{project}/.gemini/agents/",
                ]
            else:
                task_tool_mapping = "Task(subagent_type=X) where X = agent_name from spawn_job."
                template_locations = [
                    "{project}/.claude/agents/",
                    "~/.claude/agents/",
                ]

            fields["cli_mode_rules"] = {
                "agent_name_usage": (
                    "SINGLE SOURCE OF TRUTH - binds DB record, spawning tool, and template filename. "
                    f"MUST match template filename exactly (e.g., {example_str})."
                ),
                "agent_display_name_usage": (
                    "Dashboard label - what humans see in UI. "
                    "MUST be unique per agent instance when spawning multiple agents of same template."
                ),
                "multi_agent_example": {
                    "scenario": "Spawning 2 implementers for different domains",
                    "agent_1": {"agent_name": "implementer", "agent_display_name": "api-implementer"},
                    "agent_2": {"agent_name": "implementer", "agent_display_name": "ui-implementer"},
                },
                "task_tool_mapping": task_tool_mapping,
                "validation": "soft",
                "template_locations": template_locations,
            }

            logger.info(
                f"[CLI_MODE_RULES] Added CLI mode rules for orchestrator {job_id}",
                extra={
                    "job_id": job_id,
                    "execution_mode": execution_mode,
                    "allowed_names": allowed_agent_names,
                },
            )
        else:
            # Handover 0411a: Phase assignment instructions for multi-terminal mode
            fields["phase_assignment_instructions"] = (
                "## Execution Phase Assignment (Multi-Terminal Mode)\n\n"
                "When creating agent jobs with spawn_job, assign a `phase` number to each agent:\n"
                "- Phase 1: Agents that should run first (no dependencies). Usually: analyzer, researcher.\n"
                "- Phase 2: Agents that depend on Phase 1 completion. Usually: implementer, designer.\n"
                "- Phase 3: Agents that depend on Phase 2 completion. Usually: tester, reviewer.\n"
                "- Phase 4+: Final agents. Usually: documenter.\n\n"
                "Agents in the SAME phase can run in parallel (user opens multiple terminals).\n"
                "Higher phases should wait until lower phases complete.\n\n"
                "Use your judgment based on the actual agent team and project requirements."
            )

        return fields

    async def get_orchestrator_instructions(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Fetch orchestrator mission with framing-based context instructions (Handover 0350b).

        Returns a lean response (~500 tokens) with:
        - identity: Orchestrator/project identifiers
        - project_description_inline: Description + mission (always inline)
        - orchestrator_protocol: CH2 contains inline fetch_context() calls (Handover 0823)

        CH2 protocol now contains explicit, mandatory fetch_context() calls.
        Agents cannot skip categories. User depth settings control what comes back.
        """
        try:
            async with self._get_session() as session:
                ctx = await self._build_orchestrator_context(session, job_id, tenant_key)

                if ctx.get("early_return"):
                    return ctx["early_return"]

                return self._build_orchestrator_response(ctx, job_id, tenant_key)

        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            logger.exception("Failed to get orchestrator instructions")
            raise OrchestrationError(
                message="Failed to get orchestrator instructions",
                error_code="INTERNAL_ERROR",
                context={"job_id": job_id, "error": str(e)},
            ) from e

    async def _build_orchestrator_context(self, session: AsyncSession, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Gather all data needed for orchestrator instructions response.

        Returns a context dict with execution, job, project, product, config, and templates.
        If a staging redirect is needed, returns {"early_return": <response_dict>}.
        """
        if not job_id or not job_id.strip():
            raise ValidationError(
                message="Job ID is required",
                error_code="VALIDATION_ERROR",
                context={"method": "get_orchestrator_instructions"},
            )

        if not tenant_key or not tenant_key.strip():
            raise ValidationError(
                message="Tenant key is required",
                error_code="VALIDATION_ERROR",
                context={"method": "get_orchestrator_instructions"},
            )

        # Query AgentExecution and join to AgentJob
        execution = await self._repo.get_execution_with_job(session, tenant_key, job_id)

        if not execution:
            raise ResourceNotFoundError(
                message=f"Orchestrator execution for job {job_id} not found",
                error_code="NOT_FOUND",
                context={"job_id": job_id, "method": "get_orchestrator_instructions"},
            )

        agent_job = execution.job
        if not agent_job:
            raise ResourceNotFoundError(
                message=f"Agent job {job_id} not found",
                error_code="NOT_FOUND",
                context={"job_id": job_id, "method": "get_orchestrator_instructions"},
            )

        if agent_job.job_type != "orchestrator":
            raise ValidationError(
                message=f"Job {job_id} is not an orchestrator",
                error_code="VALIDATION_ERROR",
                context={
                    "job_id": job_id,
                    "job_type": agent_job.job_type,
                    "method": "get_orchestrator_instructions",
                },
            )

        project = await self._repo.get_project_by_id(session, tenant_key, agent_job.project_id)

        if not project:
            raise ResourceNotFoundError(
                message="Project not found",
                error_code="NOT_FOUND",
                context={"project_id": str(agent_job.project_id), "method": "get_orchestrator_instructions"},
            )

        # Handover 0830: Response gating branches on implementation_launched_at
        early = self._check_staging_redirect(project, job_id)
        if early:
            return {"early_return": early}

        product = None
        if project.product_id:
            product = await self._repo.get_project_with_vision_docs(session, tenant_key, project.product_id)

        metadata = agent_job.job_metadata or {}
        user_id = metadata.get("user_id")

        if user_id:
            user_config = await _get_user_config(user_id, tenant_key, session)
            field_toggles = user_config["field_toggles"]
            depth_config = user_config["depth_config"]
            logger.info(
                "[USER_CONFIG] Fetched fresh user config for OrchestrationService",
                extra={"job_id": job_id, "user_id": user_id},
            )
        else:
            field_toggles = metadata.get("field_toggles", metadata.get("field_priorities", {}))
            depth_config = metadata.get("depth_config", {})
            logger.debug("[USER_CONFIG] No user_id, using frozen job_metadata config", extra={"job_id": job_id})

        templates = await self._repo.get_active_templates(session, tenant_key)

        # CE-OPT-001: Build category_metadata with Modified timestamps
        category_metadata = await self._build_category_metadata(
            session=session,
            product=product,
            tenant_key=tenant_key,
        )

        # BE-5008: Read integration toggles from DB Settings
        integrations = {}
        try:
            from giljo_mcp.services.settings_service import SettingsService

            settings_svc = SettingsService(session, tenant_key)
            integrations = await settings_svc.get_settings("integrations")
        except Exception as _exc:  # noqa: BLE001
            logger.warning("[INTEGRATIONS] Failed to read settings from DB")

        # SEC-0005b: Fetch tenant-scoped orchestrator prompt override (if any).
        # Instantiate the service locally to avoid pulling in api.app_state (which
        # has heavy side effects at import time and breaks service-layer tests).
        orchestrator_prompt_override: str | None = None
        try:
            from giljo_mcp.system_prompts.service import SystemPromptService

            prompt_service = SystemPromptService(db_manager=self.db_manager)
            prompt_record = await prompt_service.get_orchestrator_prompt(tenant_key=tenant_key, session=session)
            if prompt_record.is_override:
                orchestrator_prompt_override = prompt_record.content
        except Exception as _exc:  # noqa: BLE001
            logger.warning("[SEC-0005b] Failed to read orchestrator prompt override")

        return {
            "execution": execution,
            "agent_job": agent_job,
            "project": project,
            "product": product,
            "metadata": metadata,
            "field_toggles": field_toggles,
            "depth_config": depth_config,
            "templates": templates,
            "category_metadata": category_metadata,
            "integrations": integrations,
            "orchestrator_prompt_override": orchestrator_prompt_override,
        }

    async def _build_category_metadata(
        self,
        session: AsyncSession,
        product: Any | None,
        tenant_key: str,
    ) -> dict[str, dict]:
        """Build category_metadata dict with Modified timestamps for protocol display.

        CE-OPT-001: Enables warm orchestrators to skip unchanged context categories.

        Returns:
            Dict mapping category name -> {modified: str, entries?: int}
        """
        metadata: dict[str, dict] = {}
        if not product:
            return metadata

        # Product-level categories use product.updated_at
        product_updated = getattr(product, "updated_at", None)
        if product_updated:
            # Truncate to minute precision, ISO format
            ts = product_updated.strftime("%Y-%m-%dT%H:%M")
            for cat in ("product_core", "vision_documents", "tech_stack", "architecture", "testing"):
                metadata[cat] = {"modified": ts}

        # memory_360: COUNT + MAX(created_at) from ProductMemoryEntry
        entry_count, max_created = await self._repo.get_category_metadata(session, tenant_key, product.id)
        if entry_count > 0 and max_created:
            metadata["memory_360"] = {
                "modified": max_created.strftime("%Y-%m-%dT%H:%M"),
                "entries": entry_count,
            }

        # git_history: skip (no server-side data, falls back to local git)

        return metadata

    @staticmethod
    def _check_staging_redirect(project: Any, job_id: str) -> dict[str, Any] | None:
        """Return a staging redirect response if applicable, else None."""
        if project.staging_status == "staging_complete":
            identity = {
                "job_id": job_id,
                "project_id": str(project.id),
                "project_name": project.name,
            }
            if project.implementation_launched_at is not None:
                return {
                    "staging_complete": True,
                    "redirect": "get_agent_mission",
                    "identity": identity,
                    "message": (
                        "Implementation is already launched. Your operating protocol and live team "
                        "state are in get_agent_mission. "
                        f"Call get_agent_mission(job_id='{job_id}') to receive your current team "
                        "state and coordination protocol."
                    ),
                    "thin_client": True,
                }
            return {
                "staging_complete": True,
                "redirect": None,
                "identity": identity,
                "message": (
                    "Staging is complete. Return to the dashboard and click Implement to launch "
                    "the implementation phase. Then paste the orchestrator implementation prompt "
                    "into your terminal."
                ),
                "thin_client": True,
            }
        return None

    def _build_orchestrator_response(self, ctx: dict[str, Any], job_id: str, tenant_key: str) -> dict[str, Any]:
        """Assemble the orchestrator instructions response from gathered context."""
        execution = ctx["execution"]
        agent_job = ctx["agent_job"]
        project = ctx["project"]
        product = ctx["product"]
        metadata = ctx["metadata"]
        field_toggles = ctx["field_toggles"]
        depth_config = ctx["depth_config"]
        templates = ctx["templates"]

        template_list = [{"name": t.name, "role": t.role, "description": t.description or ""} for t in templates]

        project_path = None
        if product is not None:
            project_path = getattr(product, "project_path", None)

        # Handover 0408 / BE-5008: Read integration toggles from ctx (loaded in _build_orchestrator_context)
        integrations = ctx.get("integrations", {})
        include_serena = integrations.get("serena_mcp", {}).get("use_in_prompts", False)
        git_integration_enabled = integrations.get("git_integration", {}).get("enabled", False)

        response: dict[str, Any] = {
            "identity": {
                "job_id": job_id,
                "agent_id": execution.agent_id,
                "project_id": str(project.id),
                "project_name": project.name,
                "tenant_key": tenant_key,
                "id_glossary": {
                    "job_id": "Use for: report_progress, complete_job, set_agent_status",
                    "agent_id": "Use for: send_message(from_agent), receive_messages",
                    "project_id": "Use for: send_message(project_id), update_project_mission, spawn_job, get_workflow_status, close_project_and_update_memory",
                },
            },
            "project_description_inline": {
                "description": project.description or "",
                "mission": agent_job.mission or "",
                "project_path": project_path,
            },
            "agent_templates": template_list,
            # Handover 0966: Comprehensive tool list for orchestrator awareness
            "mcp_tools_available": [
                "health_check",
                "fetch_context",
                "spawn_job",
                "get_agent_mission",
                "send_message",
                "receive_messages",
                "inspect_messages",
                "report_progress",
                "set_agent_status",
                "get_workflow_status",
                "update_project_mission",
                "update_agent_mission",
                "complete_job",
                "close_job",
                "reactivate_job",
                "dismiss_reactivation",
                "write_360_memory",
                "close_project_and_update_memory",
                "get_agent_result",
                "create_task",
            ],
            "field_toggles": field_toggles,
            "thin_client": True,
            "architecture": "toggle_based",
            "integrations": {
                "serena_mcp_enabled": include_serena,
                "git_integration_enabled": git_integration_enabled,
            },
        }

        # Handover 0351 / 0411a: Execution-mode-specific fields
        execution_mode = getattr(project, "execution_mode", None) or metadata.get("execution_mode", "multi_terminal")
        response.update(self._build_execution_mode_fields(execution_mode, templates, job_id))

        # Handover 0415: Add chapter-based orchestrator protocol
        cli_execution_modes = ("claude_code_cli", "codex_cli", "gemini_cli")
        cli_mode = execution_mode in cli_execution_modes
        # HO1020 (Wave 2 Item 2): explicit multi_terminal mapping + fail-safe
        # default of "multi_terminal" so an unknown/unmapped execution_mode
        # falls back to the platform-neutral generic branch rather than the
        # Claude Code Task() block.
        execution_mode_to_tool = {
            "claude_code_cli": "claude-code",
            "codex_cli": "codex",
            "gemini_cli": "gemini",
            "multi_terminal": "multi_terminal",
        }
        protocol_tool = execution_mode_to_tool.get(execution_mode, "multi_terminal")
        is_staging = execution.status == "waiting"

        # Handover 0904: Read auto check-in settings from project
        auto_checkin_enabled = getattr(project, "auto_checkin_enabled", False)
        auto_checkin_interval = getattr(project, "auto_checkin_interval", 10)

        # CE-OPT-001: Thread category timestamps into protocol
        category_metadata = ctx.get("category_metadata")

        orchestrator_protocol = _build_orchestrator_protocol(
            cli_mode=cli_mode,
            project_id=str(project.id),
            orchestrator_id=job_id,
            tenant_key=tenant_key,
            include_implementation_reference=not is_staging,
            field_toggles=field_toggles,
            depth_config=depth_config,
            product_id=str(product.id) if product else None,
            tool=protocol_tool,
            auto_checkin_enabled=auto_checkin_enabled,
            auto_checkin_interval=auto_checkin_interval,
            git_integration_enabled=git_integration_enabled,
            category_metadata=category_metadata,
        )
        response["orchestrator_protocol"] = orchestrator_protocol

        # Handover 0431: Inject orchestrator identity/behavioral guidance.
        # SEC-0005b: tenant admin may override the identity content per tenant.
        # HO1027 (three-layer refactor): the system harness (MCP Tool Usage,
        # CHECK-IN PROTOCOL, HARNESS REMINDER OVERRIDE for Claude Code) is
        # ALWAYS appended via compose_orchestrator_identity — even when an
        # admin override is set — so harness mechanics never leak into the
        # admin textarea but always reach the spawned orchestrator.
        from giljo_mcp.template_seeder import compose_orchestrator_identity

        override_content = ctx.get("orchestrator_prompt_override")
        response["orchestrator_identity"] = compose_orchestrator_identity(override_content, tool=protocol_tool)

        logger.info(
            "Returning toggle-based orchestrator instructions",
            extra={
                "job_id": job_id,
                "enabled_categories": sum(1 for v in field_toggles.values() if v),
            },
        )

        return response
