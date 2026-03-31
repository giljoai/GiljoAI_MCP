"""
MissionService - Agent mission retrieval and orchestrator instructions.

Extracted from OrchestrationService (Handover 0769) as part of the facade pattern
refactoring to keep individual modules under 1000 lines.

Responsibilities:
- Agent mission retrieval (get_agent_mission)
- Orchestrator instructions (get_orchestrator_instructions)
- Mission updates (update_agent_mission)
- Agent template resolution
- Execution mode field building
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    DatabaseError,
    OrchestrationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import (
    AgentExecution,
    AgentJob,
    AgentTemplate,
    Project,
)
from src.giljo_mcp.schemas.service_responses import (
    MissionResponse,
    MissionUpdateResult,
)
from src.giljo_mcp.services.protocol_builder import (
    _build_orchestrator_protocol,
    _generate_agent_protocol,
    _generate_team_context_header,
    _get_user_config,
)
from src.giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


class MissionService:
    """
    Service for agent mission retrieval and orchestrator instructions.

    Extracted from OrchestrationService to reduce module size.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
        message_service: Optional["MessageService"] = None,
        websocket_manager: Optional[Any] = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._message_service = message_service
        self._websocket_manager = websocket_manager or getattr(message_service, "_websocket_manager", None)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._mission_planner = None
        self._template_generator = None

    @property
    def mission_planner(self):
        """Lazy initialization of MissionPlanner."""
        if self._mission_planner is None:
            self._mission_planner = MissionPlanner(self.db_manager)
        return self._mission_planner

    @mission_planner.setter
    def mission_planner(self, value):
        """Allow setting mission_planner for tests."""
        self._mission_planner = value

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

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> MissionResponse:
        """
        Get agent-specific mission from database.

        Implements atomic job start semantics: first fetch transitions
        waiting -> working; subsequent fetches are idempotent re-reads.

        Args:
            job_id: Work order UUID (what work is assigned)
            tenant_key: Tenant key for isolation

        Returns:
            MissionResponse with mission details and metadata

        Raises:
            ResourceNotFoundError: Job or execution not found
            DatabaseError: Unexpected database error
        """
        try:
            status_changed = False
            old_status: Optional[str] = None
            execution: Optional[AgentExecution] = None
            job: Optional[AgentJob] = None
            all_project_executions: list[AgentExecution] = []
            mission_lookup: dict[str, str] = {}
            agent_identity: Optional[str] = None
            current_team_state: Optional[list[dict]] = None
            project = None

            async with self._get_session() as session:
                job, execution = await self._fetch_job_and_execution(session, job_id, tenant_key)

                # Handover 0709: Implementation phase gate
                if job.project_id:
                    project, gate_response = await self._check_implementation_gate(
                        session,
                        job,
                        job_id,
                        tenant_key,
                    )
                    if gate_response is not None:
                        return gate_response

                # Fetch team context and orchestrator state
                all_project_executions, mission_lookup, current_team_state = await self._fetch_team_context(
                    session, job, execution, job_id, tenant_key
                )

                # Resolve agent identity from template (Handover 0825)
                agent_identity = await self._resolve_mission_template(
                    session,
                    job,
                    execution,
                    tenant_key,
                )

                # Atomic start semantics on FIRST mission fetch
                if execution.status == "waiting":
                    now = datetime.now(timezone.utc)
                    old_status = execution.status
                    execution.status = "working"
                    execution.started_at = now
                    execution.last_progress_at = now
                    status_changed = True

                    await session.commit()
                    await session.refresh(execution)

                    self._logger.info(
                        "[JOB SIGNALING] Mission started via get_agent_mission",
                        extra={
                            "job_id": job_id,
                            "agent_id": execution.agent_id,
                            "agent_display_name": execution.agent_display_name,
                            "old_status": old_status,
                            "new_status": execution.status,
                        },
                    )

            # WebSocket emissions happen after the database transaction is complete
            if execution and status_changed and old_status is not None:
                try:
                    if self._websocket_manager:
                        await self._websocket_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="agent:status_changed",
                            data={
                                "job_id": job_id,
                                "project_id": str(job.project_id) if job.project_id else None,
                                "agent_id": execution.agent_id,
                                "agent_display_name": execution.agent_display_name,
                                "agent_name": execution.agent_name,
                                "old_status": old_status,
                                "status": "working",
                                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            },
                        )

                    self._logger.info(
                        "[WEBSOCKET] Emitted status change events for get_agent_mission",
                        extra={"job_id": job_id, "agent_id": execution.agent_id},
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"[WEBSOCKET] Failed to emit status events: {ws_error}")

            if not execution or not job:
                raise ResourceNotFoundError(
                    message=f"Agent job {job_id} not found",
                    context={"job_id": job_id, "tenant_key": tenant_key},
                )

            return self._assemble_mission_context(
                job=job,
                execution=execution,
                project=project,
                agent_identity=agent_identity,
                all_project_executions=all_project_executions,
                mission_lookup=mission_lookup,
                current_team_state=current_team_state,
                tenant_key=tenant_key,
            )

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get agent mission")
            raise DatabaseError(
                message=f"Unexpected error: {e!s}", context={"job_id": job_id, "tenant_key": tenant_key}
            ) from e

    async def _get_agent_template_internal(
        self, role: str, tenant_key: str, product_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Optional[AgentTemplate]:
        """
        Get agent template for role with cascade resolution.

        Resolution order (highest to lowest priority):
        1. Product-specific template (if product_id provided)
        2. Tenant-specific template (user customizations)
        3. System default template (is_default=True)

        Args:
            role: Agent role name (e.g., "implementer", "tester")
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Optional product ID for product-specific templates
            session: Optional AsyncSession (if not provided, creates new session)

        Returns:
            AgentTemplate instance or None if no template found

        Multi-tenant isolation:
            - Only returns templates owned by tenant
            - No cross-tenant leakage possible
        """
        # Use provided session or create new one
        if session:
            # Use provided session (no context manager, caller manages session)
            # Try product-specific template first (if product_id provided)
            if product_id:
                stmt = select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.role == role,
                    AgentTemplate.product_id == product_id,
                    AgentTemplate.is_active,
                )
                result = await session.execute(stmt)
                template = result.scalar_one_or_none()
                if template:
                    self._logger.info(
                        f"[_get_agent_template_internal] Found product-specific template for "
                        f"role={role}, product={product_id}, tenant={tenant_key}"
                    )
                    return template

            # Try tenant-specific template (no product_id constraint)
            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role == role,
                AgentTemplate.product_id.is_(None),
                AgentTemplate.is_active,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                self._logger.info(
                    f"[_get_agent_template_internal] Found tenant-specific template for role={role}, tenant={tenant_key}"
                )
                return template

            # Try system default template (is_default=True, any tenant)
            # Use .limit(1) since multiple system defaults may exist for same role
            stmt = (
                select(AgentTemplate)
                .where(
                    AgentTemplate.role == role,
                    AgentTemplate.is_default,
                    AgentTemplate.is_active,
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                self._logger.info(f"[_get_agent_template_internal] Found system default template for role={role}")
                return template

            self._logger.warning(
                f"[_get_agent_template_internal] No template found for role={role}, tenant={tenant_key}, product={product_id}"
            )
            return None
        # Create new session
        async with self._get_session() as db_session:
            return await self._get_agent_template_internal(role, tenant_key, product_id, db_session)

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

    async def _fetch_job_and_execution(
        self,
        session: AsyncSession,
        job_id: str,
        tenant_key: str,
    ) -> tuple[AgentJob, AgentExecution]:
        """Fetch the job and its latest active execution, raising on not-found."""
        job_result = await session.execute(
            select(AgentJob).where(
                and_(
                    AgentJob.job_id == job_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
        )
        job = job_result.scalar_one_or_none()

        if not job:
            raise ResourceNotFoundError(
                message=f"Agent job {job_id} not found", context={"job_id": job_id, "tenant_key": tenant_key}
            )

        exec_result = await session.execute(
            select(AgentExecution)
            .where(
                and_(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status.not_in(["complete", "decommissioned"]),
                )
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        execution = exec_result.scalar_one_or_none()

        if not execution:
            raise ResourceNotFoundError(
                message=f"No active execution found for job {job_id}",
                context={"job_id": job_id, "tenant_key": tenant_key},
            )

        return job, execution

    async def _check_implementation_gate(
        self,
        session: AsyncSession,
        job: AgentJob,
        job_id: str,
        tenant_key: str,
    ) -> tuple[Any, Optional[MissionResponse]]:
        """Check implementation phase gate.

        Returns:
            Tuple of (project, gate_response). gate_response is non-None if blocked.
        """
        from src.giljo_mcp.models.projects import Project

        project_res = await session.execute(
            select(Project).where(Project.id == job.project_id, Project.tenant_key == tenant_key)
        )
        project = project_res.scalar_one_or_none()

        if project and project.implementation_launched_at is None:
            if job.job_type == "orchestrator":
                return project, MissionResponse(
                    job_id=job_id,
                    blocked=True,
                    mission=None,
                    full_protocol=None,
                    error="BLOCKED: Implementation phase not launched",
                    user_instruction=(
                        "Staging is complete but implementation has not been launched. "
                        "Return to the dashboard and click Implement, then paste your "
                        "orchestrator prompt into the terminal."
                    ),
                )
            return project, MissionResponse(
                job_id=job_id,
                blocked=True,
                mission=None,
                full_protocol=None,
                error="BLOCKED: Implementation phase not started by user",
                user_instruction=(
                    "Your mission is blocked. The user must click the 'Implement' "
                    "button in the GiljoAI dashboard before you can receive your mission. "
                    "Please inform your user of this requirement and wait."
                ),
            )

        return project, None

    async def _fetch_team_context(
        self,
        session: AsyncSession,
        job: AgentJob,
        execution: AgentExecution,
        job_id: str,
        tenant_key: str,
    ) -> tuple[list[AgentExecution], dict[str, str], Optional[list[dict]]]:
        """Fetch project-wide executions and build team context for orchestrator.

        Returns:
            Tuple of (all_project_executions, mission_lookup, current_team_state).
        """
        current_team_state: Optional[list[dict]] = None

        if not job.project_id:
            return [execution], {job.job_id: job.mission}, None

        all_exec_result = await session.execute(
            select(AgentExecution, AgentJob)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == job.project_id,
                    AgentExecution.tenant_key == tenant_key,
                )
            )
        )
        rows = all_exec_result.all()
        all_project_executions = [row[0] for row in rows]

        mission_lookup: dict[str, str] = {}
        for _, job_row in rows:
            mission_lookup[job_row.job_id] = job_row.mission

        # Handover 0830: Build live team state for orchestrator
        if job.job_type == "orchestrator":
            current_team_state = []
            for exec_row, job_row in rows:
                if job_row.job_id == job_id:
                    continue
                current_team_state.append(
                    {
                        "agent_name": exec_row.agent_name,
                        "agent_display_name": exec_row.agent_display_name,
                        "job_id": job_row.job_id,
                        "agent_id": str(exec_row.agent_id),
                        "execution_status": exec_row.status,
                        "phase": job_row.phase,
                    }
                )
            current_team_state.sort(key=lambda x: x.get("phase") or 0)

        return all_project_executions, mission_lookup, current_team_state

    async def _resolve_mission_template(
        self,
        session: AsyncSession,
        job: AgentJob,
        execution: AgentExecution,
        tenant_key: str,
    ) -> Optional[str]:
        """Resolve agent identity from template or orchestrator defaults.

        Handover 0825: Identity is resolved at read-time, not baked at spawn.

        Returns:
            Agent identity string, or None if no template and not an orchestrator.
        """
        agent_identity: Optional[str] = None
        job_id = job.job_id

        if getattr(job, "template_id", None):
            template_result = await session.execute(
                select(AgentTemplate).where(
                    and_(
                        AgentTemplate.id == job.template_id,
                        AgentTemplate.tenant_key == tenant_key,
                    )
                )
            )
            identity_template = template_result.scalar_one_or_none()

            if identity_template:
                identity_parts = []

                # Framing directive -- tells the LLM how to process this field
                role_label = (identity_template.role or execution.agent_name or "agent").upper()
                identity_parts.append(
                    f"You are {role_label}. The following defines your expertise, "
                    f"behavioral constraints, and success criteria. "
                    f"Internalize these as your operating identity.\n"
                )

                # Role prose (user_instructions only -- system_instructions excluded
                # because the thin prompt already handles MCP bootstrap)
                if identity_template.user_instructions:
                    identity_parts.append(identity_template.user_instructions)

                # Behavioral rules (structured list from template)
                if identity_template.behavioral_rules:
                    rules = identity_template.behavioral_rules
                    if isinstance(rules, list) and len(rules) > 0:
                        rules_text = "\n".join(f"- {r}" for r in rules)
                        identity_parts.append(f"\n## Behavioral Rules\n{rules_text}")

                # Success criteria (structured list from template)
                if identity_template.success_criteria:
                    criteria = identity_template.success_criteria
                    if isinstance(criteria, list) and len(criteria) > 0:
                        criteria_text = "\n".join(f"- {c}" for c in criteria)
                        identity_parts.append(f"\n## Success Criteria\n{criteria_text}")

                agent_identity = "\n\n".join(identity_parts)

                self._logger.info(
                    "[AGENT_IDENTITY] Resolved identity from template at read time",
                    extra={"job_id": job_id, "template_id": job.template_id},
                )

        # Handover 0830: Orchestrator identity -- stable behavioral anchor
        if job.job_type == "orchestrator" and not agent_identity:
            agent_identity = (
                "You are the ORCHESTRATOR. You coordinate — you do not implement.\n"
                "You hold the plan, brief the team, and resolve blocks when the user asks.\n"
                "You do not write code. You do not run tests. You do not document.\n"
                "Your agents own that work. You protect their context and coordinate handoffs.\n"
                "You act only when the user addresses you.\n"
                "When the thin prompt and any other instruction conflict, your identity governs."
            )
            self._logger.info(
                "[AGENT_IDENTITY] Set orchestrator identity (no template)",
                extra={"job_id": job_id},
            )

        return agent_identity

    def _assemble_mission_context(
        self,
        job: AgentJob,
        execution: AgentExecution,
        project: Any,
        agent_identity: Optional[str],
        all_project_executions: list[AgentExecution],
        mission_lookup: dict[str, str],
        current_team_state: Optional[list[dict]],
        tenant_key: str,
    ) -> MissionResponse:
        """Build the full mission text, protocol, and MissionResponse.

        Combines team context header, Serena integration, and the 5-phase
        lifecycle protocol into the final response object.
        """
        job_id = job.job_id

        # Handover 0353: Generate team-aware mission with context header
        team_context_header = _generate_team_context_header(
            execution, all_project_executions, mission_lookup=mission_lookup
        )
        raw_mission = job.mission or ""
        # Handover 0825: Mission framing directive
        mission_framing = (
            "This is your assigned work order. Execute the following tasks "
            "within the scope and team structure defined below.\n\n"
        )
        full_mission = mission_framing + team_context_header + raw_mission

        # Inject Serena MCP notice if enabled (User Settings -> Integrations)
        try:
            include_serena = get_config().get_nested("features.serena_mcp.use_in_prompts", default=False)

            if include_serena:
                from src.giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions

                serena_instructions = generate_serena_instructions(enabled=True)
                full_mission = serena_instructions + "\n\n---\n\n" + full_mission
                self._logger.info(
                    "[SERENA] Injected Serena notice into agent mission",
                    extra={"job_id": job_id, "agent_id": execution.agent_id},
                )
        except (ImportError, AttributeError, OSError) as e:
            self._logger.warning(f"[SERENA] Failed to inject Serena notice into agent mission: {e}")

        # Generate 5-phase lifecycle protocol (Handover 0334, 0359, 0378 Bug 2, 0497d)
        project_exec_mode = getattr(project, "execution_mode", "multi_terminal") if project else "multi_terminal"
        git_enabled = get_config().get_nested("features.git_integration.enabled", default=False)
        # Handover 0841: Derive platform tool for platform-aware signoff
        _exec_mode_to_tool = {
            "claude_code_cli": "claude-code",
            "codex_cli": "codex",
            "gemini_cli": "gemini",
        }
        agent_tool = _exec_mode_to_tool.get(project_exec_mode, "claude-code")
        full_protocol = _generate_agent_protocol(
            job_id=job_id,
            tenant_key=tenant_key,
            agent_name=execution.agent_display_name,
            agent_id=str(execution.agent_id),
            execution_mode=project_exec_mode,
            git_integration_enabled=git_enabled,
            job_type=job.job_type,
            tool=agent_tool,
        )

        # Handover 0731c: Typed return (MissionResponse)
        return MissionResponse(
            job_id=job.job_id,
            agent_id=execution.agent_id,
            agent_name=execution.agent_display_name,
            agent_display_name=execution.agent_display_name,
            agent_identity=agent_identity,
            mission=full_mission,
            project_id=str(job.project_id),
            parent_job_id=str(execution.spawned_by) if execution.spawned_by else None,
            status=execution.status,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            thin_client=True,
            full_protocol=full_protocol,
            current_team_state=current_team_state,
        )

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
                # Gather all context data needed for the response
                ctx = await self._build_orchestrator_context(session, job_id, tenant_key)

                # If staging redirect was triggered, return early
                if ctx.get("early_return"):
                    return ctx["early_return"]

                # Assemble the response from gathered context
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
        from sqlalchemy import and_
        from sqlalchemy.orm import joinedload, selectinload

        from src.giljo_mcp.models import AgentTemplate, Product, Project

        # Validate inputs
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

        # Phase C: Query AgentExecution and join to AgentJob
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

        # Get project
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

        # Get product
        product = None
        if project.product_id:
            result = await session.execute(
                select(Product)
                .where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
                .options(selectinload(Product.vision_documents))
            )
            product = result.scalar_one_or_none()

        # Get user configuration
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

        # Get agent templates
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

        # Build agent template summary
        template_list = [
            {"name": t.name, "role": t.role, "description": t.description[:200] if t.description else ""}
            for t in templates
        ]

        # Resolve project path
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
                    "job_id": "Use for: report_progress, complete_job, report_error",
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

    async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str) -> MissionUpdateResult:
        """
        Update the mission field of an AgentJob.

        Handover 0380: Used by orchestrators to persist their execution plan during staging.
        This allows fresh-session orchestrators to retrieve the plan via get_agent_mission()
        during implementation phase.

        Handover 0730b: Exception-based error handling (no success wrapper).

        Args:
            job_id: The AgentJob.job_id (work order UUID)
            tenant_key: Tenant isolation key
            mission: The execution plan/mission to persist

        Returns:
            {"job_id": job_id, "mission_updated": True, "mission_length": len(mission)}

        Raises:
            ResourceNotFoundError: Agent job not found
            OrchestrationError: Failed to update agent mission
        """
        try:
            async with self._get_session() as session:
                from sqlalchemy import and_, select

                from src.giljo_mcp.models.agent_identity import AgentJob

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
                    raise ResourceNotFoundError(
                        message=f"Agent job {job_id} not found",
                        error_code="NOT_FOUND",
                        context={
                            "job_id": job_id,
                            "tenant_key": tenant_key,
                            "method": "update_agent_mission",
                            "troubleshooting": [
                                "Verify job_id is correct",
                                "Ensure tenant_key matches",
                            ],
                        },
                    )

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
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                        logger.warning(f"[WEBSOCKET] Failed to broadcast job:mission_updated: {ws_error}")

                # Handover 0826: Server-side staging completion signal
                # When an orchestrator persists its mission and sub-agents exist,
                # staging is structurally complete -- emit a deterministic signal
                # so the UI doesn't rely solely on the LLM sending a broadcast message.
                if job.job_type == "orchestrator" and job.project_id:
                    agent_count_result = await session.execute(
                        select(func.count())
                        .select_from(AgentExecution)
                        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                        .where(
                            AgentJob.project_id == job.project_id,
                            AgentJob.tenant_key == tenant_key,
                            AgentExecution.agent_display_name != "orchestrator",
                            AgentExecution.status.not_in(["decommissioned"]),
                        )
                    )
                    agent_count = agent_count_result.scalar() or 0

                    if agent_count > 0:
                        project_result = await session.execute(
                            select(Project).where(
                                Project.id == job.project_id,
                                Project.tenant_key == tenant_key,
                            )
                        )
                        project = project_result.scalar_one_or_none()
                        if project and project.staging_status != "staging_complete":
                            project.staging_status = "staging_complete"
                            project.updated_at = datetime.now(timezone.utc)
                            await session.commit()

                            if self._websocket_manager:
                                try:
                                    await self._websocket_manager.broadcast_to_tenant(
                                        tenant_key=tenant_key,
                                        event_type="project:staging_complete",
                                        data={
                                            "project_id": str(job.project_id),
                                            "agent_count": agent_count,
                                            "staging_status": "staging_complete",
                                        },
                                    )
                                    logger.info(
                                        f"[STAGING_COMPLETE] project={job.project_id} agents={agent_count}",
                                        extra={"project_id": str(job.project_id), "tenant_key": tenant_key},
                                    )
                                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience
                                    logger.warning(
                                        f"[WEBSOCKET] Failed to broadcast project:staging_complete: {ws_error}"
                                    )

                logger.info(
                    f"[UPDATE_AGENT_MISSION] Updated mission for job {job_id}",
                    extra={
                        "job_id": job_id,
                        "job_type": job.job_type,
                        "mission_length": len(mission),
                        "tenant_key": tenant_key,
                    },
                )

                # Handover 0731c: Typed return (MissionUpdateResult)
                return MissionUpdateResult(
                    job_id=job_id,
                    mission_updated=True,
                    mission_length=len(mission),
                )

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            logger.exception("Failed to update agent mission")
            raise OrchestrationError(
                message="Failed to update agent mission",
                error_code="INTERNAL_ERROR",
                context={"job_id": job_id, "error": str(e)},
            ) from e
