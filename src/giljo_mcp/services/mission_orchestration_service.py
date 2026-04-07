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

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    OrchestrationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import (
    AgentExecution,
    AgentTemplate,
)
from src.giljo_mcp.services.protocol_builder import (
    _build_orchestrator_protocol,
    _get_user_config,
)
from src.giljo_mcp.tenant import TenantManager


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
                    "spawn_agent(agent='gil-{agent_name}') where agent_name comes from spawn_agent_job. "
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
                task_tool_mapping = "Task(subagent_type=X) where X = agent_name from spawn_agent_job."
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
                "When creating agent jobs with spawn_agent_job, assign a `phase` number to each agent:\n"
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
        from sqlalchemy.orm import joinedload, selectinload

        from src.giljo_mcp.models import Product, Project

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
        result = await session.execute(
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .where(
                and_(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == tenant_key,
                )
            )
            .order_by(AgentExecution.started_at.desc())
        )
        execution = result.scalars().first()

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

        result = await session.execute(
            select(Project).where(and_(Project.id == agent_job.project_id, Project.tenant_key == tenant_key))
        )
        project = result.scalar_one_or_none()

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
            result = await session.execute(
                select(Product)
                .where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
                .options(selectinload(Product.vision_documents))
            )
            product = result.scalar_one_or_none()

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

        result = await session.execute(
            select(AgentTemplate).where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active)).limit(8)
        )
        templates = result.scalars().all()

        return {
            "execution": execution,
            "agent_job": agent_job,
            "project": project,
            "product": product,
            "metadata": metadata,
            "field_toggles": field_toggles,
            "depth_config": depth_config,
            "templates": templates,
        }

    @staticmethod
    def _check_staging_redirect(project: Any, job_id: str) -> dict[str, Any] | None:
        """Return a staging redirect response if applicable, else None."""
        if project.staging_status in ("staged", "staging_complete"):
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

        template_list = [
            {"name": t.name, "role": t.role, "description": t.description[:200] if t.description else ""}
            for t in templates
        ]

        project_path = None
        if product is not None:
            project_path = getattr(product, "project_path", None)

        # Handover 0408: Read integration toggles from config
        include_serena = False
        git_integration_enabled = False
        try:
            cfg = get_config()
            include_serena = cfg.get_nested("features.serena_mcp.use_in_prompts", default=False)
            git_integration_enabled = cfg.get_nested("features.git_integration.enabled", default=False)
        except (OSError, KeyError, ValueError, TypeError) as e:
            logger.warning(f"[INTEGRATIONS] Failed to read config: {e}")

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
                },
            },
            "project_description_inline": {
                "description": project.description or "",
                "mission": agent_job.mission or "",
                "project_path": project_path,
            },
            "agent_templates": template_list,
            "mcp_tools_available": [
                "fetch_context",
                "spawn_agent_job",
                "send_message",
                "report_progress",
                "complete_job",
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
        execution_mode_to_tool = {
            "claude_code_cli": "claude-code",
            "codex_cli": "codex",
            "gemini_cli": "gemini",
        }
        protocol_tool = execution_mode_to_tool.get(execution_mode, "claude-code")
        is_staging = execution.status == "waiting"

        # Handover 0904: Read auto check-in settings from project
        auto_checkin_enabled = getattr(project, "auto_checkin_enabled", False)
        auto_checkin_interval = getattr(project, "auto_checkin_interval", 10)

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
        )
        response["orchestrator_protocol"] = orchestrator_protocol

        # Handover 0431: Inject orchestrator identity/behavioral guidance
        from src.giljo_mcp.template_seeder import get_orchestrator_identity_content

        response["orchestrator_identity"] = get_orchestrator_identity_content()

        logger.info(
            "Returning toggle-based orchestrator instructions",
            extra={
                "job_id": job_id,
                "enabled_categories": sum(1 for v in field_toggles.values() if v),
            },
        )

        return response
