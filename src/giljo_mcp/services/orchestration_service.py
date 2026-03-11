"""
OrchestrationService - Dedicated service for orchestration and job management

This service extracts all orchestration and job management operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).

Responsibilities:
- Project orchestration workflow
- Agent job lifecycle management (spawn, acknowledge, complete, error)
- Job progress tracking and reporting
- Workflow status monitoring
- Orchestrator succession/handover

Design Principles:
- Single Responsibility: Only orchestration and job domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Import MessageService for WebSocket-enabled messaging (Handover fix: message counter WebSocket)
# Using TYPE_CHECKING to document the type without circular import risk
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    AlreadyExistsError,
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
    AgentTodoItem,
    Message,
    ProductMemoryEntry,
    Project,
)
from src.giljo_mcp.schemas.service_responses import (
    AgentTodoCounts,
    AgentWorkflowDetail,
    CompleteJobResult,
    ErrorReportResult,
    JobListResult,
    MissionResponse,
    MissionUpdateResult,
    PendingJobsResult,
    ProgressResult,
    SpawnResult,
    WorkflowStatus,
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


class OrchestrationService:
    """
    Service for managing orchestration and agent jobs.

    This service handles all orchestration-related operations including:
    - Project orchestration workflows
    - Agent job lifecycle (spawn, acknowledge, complete, error)
    - Job progress tracking
    - Workflow status monitoring
    - Pending job retrieval

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
        message_service: Optional["MessageService"] = None,
        websocket_manager: Optional[Any] = None,
    ):
        """
        Initialize OrchestrationService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            test_session: Optional AsyncSession for tests to share the same transaction
            message_service: Optional MessageService for WebSocket-enabled messaging
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._message_service = message_service
        self._websocket_manager = websocket_manager or getattr(message_service, "_websocket_manager", None)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Handover 0406: Track todo_items warning timestamps (throttle 1 per 5 min per job)
        self._todo_warning_timestamps: dict[str, datetime] = {}

        # Handover 0450: Initialize orchestration components (from orchestrator.py)
        # Initialize lazily to avoid initialization errors in tests with mocked dependencies
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

        Returns:
            Context manager for database session
        """
        if self._test_session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

    def _can_warn_missing_todos(self, job_id: str, cooldown_minutes: int = 5) -> bool:
        """
        Check if we can send a todo_items warning (throttle: 1 per N minutes per job).

        Args:
            job_id: Job UUID
            cooldown_minutes: Minimum minutes between warnings (default: 5)

        Returns:
            True if we can warn, False if throttled
        """
        last_warning = self._todo_warning_timestamps.get(job_id)
        if not last_warning:
            return True
        elapsed = (datetime.now(timezone.utc) - last_warning).total_seconds()
        return elapsed >= (cooldown_minutes * 60)

    def _record_todo_warning(self, job_id: str) -> None:
        """
        Record that a todo_items warning was sent for this job.

        Args:
            job_id: Job UUID
        """
        self._todo_warning_timestamps[job_id] = datetime.now(timezone.utc)

    # ============================================================================
    # Project Orchestration
    # ============================================================================
    # Note: orchestrate_project() method removed in favor of manual orchestration workflow

    async def get_workflow_status(
        self,
        project_id: str,
        tenant_key: str,
        exclude_job_id: Optional[str] = None,
    ) -> WorkflowStatus:
        """
        Get workflow status for a project.

        Handover 0491: Simplified status model.
        - Counts execution statuses (waiting, working, complete, blocked, silent, decommissioned)
        - Job status comes from AgentJob (active, completed, cancelled)
        - Execution status from AgentExecution (execution progress)
        - Removed: failed_agents, cancelled_agents (replaced by blocked/silent/decommissioned)

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            exclude_job_id: Optional job_id to exclude from the query
                (e.g. the orchestrator's own job to avoid counting itself)

        Returns:
            WorkflowStatus with agent counts, progress, and current stage

        Raises:
            ResourceNotFoundError: Project not found
            DatabaseError: Database operation failed

        Example:
            >>> result = await service.get_workflow_status(
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc",
            ...     exclude_job_id="my-job-id",
            ... )
            >>> print(f"Progress: {result.progress_percent}%")
        """
        try:
            async with self._get_session() as session:
                # Verify project exists
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise ResourceNotFoundError(
                        message=f"Project '{project_id}' not found",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Get all AgentExecutions for this project/tenant (join with AgentJob)
                query = (
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        AgentExecution.tenant_key == tenant_key,
                        AgentJob.project_id == project_id,
                    )
                )
                if exclude_job_id:
                    query = query.where(AgentJob.job_id != exclude_job_id)
                jobs_result = await session.execute(query)
                rows = jobs_result.all()

                # Handover 0491: Count by simplified execution statuses
                executions = [row[0] for row in rows]
                # Handover 0808: Map job_id -> job_type for workflow detail
                job_type_map = {row[1].job_id: row[1].job_type or "" for row in rows}
                active_count = sum(1 for execution in executions if execution.status == "working")
                completed_count = sum(1 for execution in executions if execution.status == "complete")
                pending_count = sum(1 for execution in executions if execution.status == "waiting")
                blocked_count = sum(1 for execution in executions if execution.status == "blocked")
                silent_count = sum(1 for execution in executions if execution.status == "silent")
                decommissioned_count = sum(1 for execution in executions if execution.status == "decommissioned")
                total_count = len(executions)

                # Calculate progress (exclude decommissioned agents from denominator)
                # Decommissioned agents should not prevent progress from reaching 100%
                actionable_count = total_count - decommissioned_count
                progress_percent = (completed_count / actionable_count * 100.0) if actionable_count > 0 else 0.0

                # Determine current stage
                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == actionable_count:
                    current_stage = "Completed"
                elif blocked_count > 0 and silent_count > 0:
                    current_stage = f"In Progress ({blocked_count} blocked, {silent_count} silent)"
                elif blocked_count > 0:
                    current_stage = f"In Progress ({blocked_count} blocked)"
                elif silent_count > 0:
                    current_stage = f"In Progress ({silent_count} silent)"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                # Caller note: remind the agent it's counted in active
                if exclude_job_id:
                    caller_note = "Your job was excluded from these counts."
                else:
                    caller_note = "Note: You (the calling agent) are included in the active count above."

                # Per-agent detail: todo counts and unread messages
                agent_details: list[AgentWorkflowDetail] = []
                if executions:
                    job_ids = [ex.job_id for ex in executions]
                    todo_stmt = (
                        select(
                            AgentTodoItem.job_id,
                            AgentTodoItem.status,
                            func.count().label("cnt"),
                        )
                        .where(
                            AgentTodoItem.job_id.in_(job_ids),
                            AgentTodoItem.tenant_key == tenant_key,
                        )
                        .group_by(AgentTodoItem.job_id, AgentTodoItem.status)
                    )
                    todo_result = await session.execute(todo_stmt)
                    todo_rows = todo_result.all()

                    # Build lookup: job_id -> {status: count}
                    todo_map: dict[str, dict[str, int]] = {}
                    for t_job_id, t_status, t_cnt in todo_rows:
                        todo_map.setdefault(t_job_id, {})[t_status] = t_cnt

                    for execution in executions:
                        counts = todo_map.get(execution.job_id, {})
                        agent_details.append(
                            AgentWorkflowDetail(
                                job_id=execution.job_id,
                                agent_id=execution.agent_id,
                                agent_name=execution.agent_name or "",
                                display_name=execution.agent_display_name or "",
                                status=execution.status or "",
                                job_type=job_type_map.get(execution.job_id, ""),
                                unread_messages=execution.messages_waiting_count or 0,
                                todos=AgentTodoCounts(
                                    completed=counts.get("completed", 0),
                                    in_progress=counts.get("in_progress", 0),
                                    pending=counts.get("pending", 0),
                                    skipped=counts.get("skipped", 0),
                                ),
                            )
                        )

                return WorkflowStatus(
                    active_agents=active_count,
                    completed_agents=completed_count,
                    pending_agents=pending_count,
                    blocked_agents=blocked_count,
                    silent_agents=silent_count,
                    decommissioned_agents=decommissioned_count,
                    current_stage=current_stage,
                    progress_percent=round(progress_percent, 2),
                    total_agents=total_count,
                    caller_note=caller_note,
                    agents=agent_details,
                )

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get workflow status")
            raise DatabaseError(
                message=f"Failed to get workflow status: {e!s}",
                context={"project_id": project_id, "tenant_key": tenant_key},
            ) from e

    # ============================================================================
    # Agent Job Management
    # ============================================================================

    async def spawn_agent_job(
        self,
        agent_display_name: str,
        agent_name: str,
        mission: str,
        project_id: str,
        tenant_key: str,
        parent_job_id: Optional[str] = None,
        context_chunks: Optional[list[str]] = None,
        phase: Optional[int] = None,
        predecessor_job_id: Optional[str] = None,
    ) -> SpawnResult:
        """
        Create an agent job with thin client architecture using dual-model (AgentJob + AgentExecution).

        Handover 0358b: Migrated from MCPAgentJob (monolithic) to AgentJob + AgentExecution.
        - AgentJob: Work order (WHAT) - persists across succession
        - AgentExecution: Executor instance (WHO) - changes on succession

        Handover 0730b: Exception-based error handling (no success wrapper).
        Handover 0497e: predecessor_job_id for recovery spawning (successor agents).

        Args:
            agent_display_name: Display name of agent (UI label - what humans see)
            agent_name: Agent name/identifier (template lookup key)
            mission: Agent mission description
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            parent_job_id: Optional parent agent_id for spawned agents (now refers to executor, not work order)
            context_chunks: Optional context chunks for the agent
            phase: Optional execution phase for multi-terminal ordering (1=first, same=parallel)
            predecessor_job_id: Optional job_id of a completed predecessor agent whose work needs fixing

        Returns:
            Dict with job_id (work order), agent_id (executor), and agent_prompt

        Raises:
            ResourceNotFoundError: Project not found or predecessor job not found
            ValidationError: Predecessor job not in same project/tenant
            DatabaseError: Failed to spawn agent

        Example:
            >>> result = await service.spawn_agent_job(
            ...     agent_display_name="Code Implementer",
            ...     agent_name="impl-1",
            ...     mission="Implement feature X",
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc",
            ...     context_chunks=["chunk1", "chunk2"],
            ...     phase=2,
            ... )
            >>> result["job_id"]  # Work order UUID (persists)
            >>> result["agent_id"]  # Executor UUID (changes on succession)
        """
        try:
            async with self._get_session() as session:
                # Get project for context
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise ResourceNotFoundError(
                        message="Project not found", context={"project_id": project_id, "tenant_key": tenant_key}
                    )

                # Handover 0497e: Predecessor context injection for recovery spawning
                if predecessor_job_id:
                    mission = await self._build_predecessor_context(
                        session, predecessor_job_id, tenant_key, project_id, mission, agent_display_name
                    )

                # Agent name validation + duplicate prevention
                await self._validate_spawn_agent(
                    session, agent_display_name, agent_name, tenant_key, project_id, parent_job_id
                )

                # Generate UUIDs for both job and execution
                job_id = str(uuid4())
                agent_id = str(uuid4())

                # Build job metadata
                metadata_dict = {
                    "created_via": "thin_client_spawn",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "thin_client": True,
                }
                if context_chunks:
                    metadata_dict["context_chunks"] = context_chunks

                # NOTE: Serena instructions removed from spawn-time injection (was double-injecting).
                # get_agent_mission() handles Serena injection dynamically at read time (lines 1772-1786),
                # respecting the toggle and keeping DB missions clean for summary display.

                # Handover 0411a/0417: Resolve template injection for multi-terminal mode
                mission, resolved_template_id = await self._resolve_spawn_template(
                    session, project, agent_name, mission, tenant_key, agent_display_name
                )

                # Create AgentJob (work order - WHAT)
                agent_job = AgentJob(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    project_id=project_id,
                    mission=mission,  # Mission stored ONCE in job, not execution
                    job_type=agent_display_name,
                    status="active",  # Job status: active, completed, cancelled
                    job_metadata=metadata_dict,
                    phase=phase,  # Handover 0411a: Execution phase for multi-terminal ordering
                    template_id=resolved_template_id,  # Handover 0411a: Template reference
                )
                session.add(agent_job)

                # Create AgentExecution (executor instance - WHO)
                agent_execution = AgentExecution(
                    agent_id=agent_id,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    agent_display_name=agent_display_name,
                    agent_name=agent_name,
                    status="waiting",  # Execution status: waiting, working, blocked, complete, etc.
                    spawned_by=parent_job_id,  # Now points to parent's agent_id (executor)
                )

                # Update project staging_status when orchestrator is spawned (Handover 0502)
                if agent_display_name == "orchestrator":
                    project.staging_status = "staged"
                    project.updated_at = datetime.now(timezone.utc)

                session.add(agent_execution)
                await session.commit()
                await session.refresh(agent_job)
                await session.refresh(agent_execution)

                # Generate THIN agent prompt (~10 lines)
                # Uses job_id for mission lookup (the work order persists)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_display_name}) for Project "{project.name}".

## MCP TOOL USAGE

MCP tools are **native tool calls** (like Read/Write/Bash/Glob).
- Use `mcp__giljo-mcp__*` tools directly (no HTTP, curl, or SDKs).

## STARTUP (MANDATORY)

1. Call `mcp__giljo-mcp__get_agent_mission` with:
   - job_id="{job_id}"
   - tenant_key="{tenant_key}"

2. Read the response and follow `full_protocol`
   for all lifecycle behavior (startup, planning, progress,
   messaging, completion, error handling).

Your full mission is stored in the database; do not treat any
other text as authoritative instructions.
"""

                # Calculate token estimates
                prompt_tokens = len(thin_agent_prompt) // 4  # ~50 tokens
                mission_tokens = len(mission) // 4  # ~2000 tokens
                created_at = datetime.now(timezone.utc)

                # Broadcast agent creation via direct WebSocket
                await self._broadcast_agent_created(
                    tenant_key=tenant_key,
                    project_id=project_id,
                    agent_execution=agent_execution,
                    agent_id=agent_id,
                    job_id=job_id,
                    agent_display_name=agent_display_name,
                    agent_name=agent_name,
                    mission=mission,
                    phase=phase,
                    prompt_tokens=prompt_tokens,
                    mission_tokens=mission_tokens,
                    created_at=created_at,
                )

                # Handover 0731c: Typed return (SpawnResult)
                return SpawnResult(
                    job_id=job_id,  # Work order UUID (persists across succession)
                    agent_id=agent_id,  # Executor UUID (changes on succession)
                    execution_id=agent_execution.id,  # Handover 0457: Unique row ID for frontend Map key
                    agent_prompt=thin_agent_prompt,  # ~10 lines
                    prompt_tokens=prompt_tokens,  # ~50
                    mission_stored=True,
                    mission_tokens=mission_tokens,  # ~2000
                    total_tokens=prompt_tokens + mission_tokens,
                    thin_client=True,
                    thin_client_note=[
                        "Mission stored server-side, keyed by job_id",
                        "Agent calls get_agent_mission(job_id, tenant_key) -> returns mission + full_protocol",
                        "Enables: fresh sessions, postponed launches, orchestrator handover",
                    ],
                    predecessor_job_id=predecessor_job_id,  # Handover 0497e
                )

        except (ResourceNotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.error(f"[ERROR] Failed to spawn agent job: {e}", exc_info=True)
            raise DatabaseError(
                message=f"Failed to spawn agent: {e!s}",
                context={"project_id": project_id, "agent_display_name": agent_display_name},
            ) from e

    async def _build_predecessor_context(
        self,
        session: AsyncSession,
        predecessor_job_id: str,
        tenant_key: str,
        project_id: str,
        mission: str,
        agent_display_name: str,
    ) -> str:
        """
        Build predecessor context for recovery spawning and prepend it to the mission.

        Handover 0497e: When a successor agent is spawned to fix a predecessor's work,
        this fetches the predecessor's completion result and injects context into the mission.

        Args:
            session: Active database session
            predecessor_job_id: Job ID of the completed predecessor agent
            tenant_key: Tenant key for isolation
            project_id: Project UUID to validate predecessor belongs to same project
            mission: Original mission text
            agent_display_name: Display name of the successor agent (for logging)

        Returns:
            Modified mission with predecessor context prepended

        Raises:
            ResourceNotFoundError: Predecessor job not found
            ValidationError: Predecessor job belongs to a different project
        """
        # Validate predecessor exists and belongs to same project + tenant
        pred_job_result = await session.execute(
            select(AgentJob).where(
                and_(
                    AgentJob.job_id == predecessor_job_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
        )
        pred_job = pred_job_result.scalar_one_or_none()

        if not pred_job:
            raise ResourceNotFoundError(
                message=f"Predecessor job '{predecessor_job_id}' not found",
                context={"predecessor_job_id": predecessor_job_id, "tenant_key": tenant_key},
            )
        if pred_job.project_id != project_id:
            raise ValidationError(
                message="Predecessor job belongs to a different project",
                context={
                    "predecessor_job_id": predecessor_job_id,
                    "predecessor_project_id": pred_job.project_id,
                    "target_project_id": project_id,
                },
            )

        # Fetch predecessor's completion result
        pred_exec_result = await session.execute(
            select(AgentExecution)
            .where(
                AgentExecution.job_id == predecessor_job_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "complete",
            )
            .order_by(AgentExecution.completed_at.desc())
            .limit(1)
        )
        pred_execution = pred_exec_result.scalar_one_or_none()

        # Build predecessor context
        pred_display_name = pred_execution.agent_display_name if pred_execution else "Unknown"
        pred_result = (pred_execution.result or {}) if pred_execution else {}

        # Truncate summary to 2000 chars
        pred_summary = pred_result.get("summary", "No summary available")
        if len(pred_summary) > 2000:
            pred_summary = pred_summary[:2000] + " [TRUNCATED]"

        # Cap commits list to 10 entries
        pred_commits = pred_result.get("commits", ["No commits recorded"])
        if len(pred_commits) > 10:
            pred_commits = [*pred_commits[:10], f"... and {len(pred_commits) - 10} more"]

        predecessor_context = f"""## PREDECESSOR CONTEXT
You are replacing a previous agent who completed their work but issues were found.

Previous Agent: {pred_display_name} (job_id: {predecessor_job_id})
Completion Summary: {pred_summary}
Commits: {pred_commits}

Your task: Read the predecessor's work, understand what was done, then fix the issues described in your mission below.

If git integration is enabled, run `git log --oneline -10` to see recent commits.
If you need more detail, call `mcp__giljo-mcp__get_agent_result(job_id="{predecessor_job_id}", tenant_key="{tenant_key}")`.

---
"""
        mission = predecessor_context + mission
        self._logger.info(
            "[PREDECESSOR_CONTEXT] Injected predecessor context into successor mission",
            extra={
                "predecessor_job_id": predecessor_job_id,
                "successor_display_name": agent_display_name,
                "predecessor_display_name": pred_display_name,
            },
        )
        return mission

    async def _validate_spawn_agent(
        self,
        session: AsyncSession,
        agent_display_name: str,
        agent_name: str,
        tenant_key: str,
        project_id: str,
        parent_job_id: Optional[str],
    ) -> None:
        """
        Validate agent spawn: check template names and prevent duplicates.

        For non-orchestrator agents:
        - Validates agent_name against active templates
        - Prevents duplicate agent_display_name within the same project

        For orchestrator agents:
        - Prevents duplicate orchestrators unless succession is happening

        Args:
            session: Active database session
            agent_display_name: Display name of agent (UI label)
            agent_name: Agent name/identifier (template lookup key)
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            parent_job_id: Optional parent agent_id for succession check

        Raises:
            ValidationError: Invalid agent_name
            AlreadyExistsError: Duplicate agent display name or orchestrator
        """
        if agent_display_name != "orchestrator":
            # Agent name validation against active templates (backported from tools layer)
            template_result = await session.execute(
                select(AgentTemplate.name).where(
                    and_(
                        AgentTemplate.tenant_key == tenant_key,
                        AgentTemplate.is_active,
                    )
                )
            )
            valid_agent_names = [row[0] for row in template_result.fetchall()]

            if agent_name not in valid_agent_names:
                raise ValidationError(
                    message=f"Invalid agent_name '{agent_name}'. Must be one of: {valid_agent_names}",
                    context={
                        "agent_name": agent_name,
                        "agent_display_name": agent_display_name,
                        "valid_names": valid_agent_names,
                        "tenant_key": tenant_key,
                    },
                )

            # Duplicate agent_display_name prevention for non-orchestrator agents
            duplicate_result = await session.execute(
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentJob.tenant_key == tenant_key,
                        AgentExecution.agent_display_name == agent_display_name,
                        AgentExecution.status.in_(["waiting", "working", "blocked"]),
                    )
                )
            )
            existing_agents = duplicate_result.scalars().all()

            if existing_agents:
                count = len(existing_agents)
                suggestion = f"{agent_display_name} {count + 1}"
                raise AlreadyExistsError(
                    message=(
                        f"DUPLICATE_DISPLAY_NAME: '{agent_display_name}' already has "
                        f"{count} active instance(s) in this project. "
                        f"Use a unique name (e.g., '{suggestion}')"
                    ),
                    context={
                        "error": "DUPLICATE_DISPLAY_NAME",
                        "project_id": project_id,
                        "tenant_key": tenant_key,
                        "agent_display_name": agent_display_name,
                        "existing_count": count,
                        "suggestion": suggestion,
                        "existing_agent_ids": [a.agent_id for a in existing_agents],
                    },
                )

        # Duplicate orchestrator prevention (backported from tools layer)
        if agent_display_name == "orchestrator":
            existing_result = await session.execute(
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentJob.tenant_key == tenant_key,
                        AgentExecution.agent_display_name == "orchestrator",
                        AgentExecution.status.in_(["waiting", "working", "blocked"]),
                    )
                )
            )
            existing_orchestrator = existing_result.scalar_one_or_none()

            if existing_orchestrator:
                # Allow succession: parent_job_id matches existing orchestrator's agent_id
                if parent_job_id and parent_job_id == existing_orchestrator.agent_id:
                    self._logger.info(
                        "Handover: Allowing successor spawn from orchestrator %s",
                        parent_job_id,
                    )
                else:
                    raise AlreadyExistsError(
                        message=(
                            f"Orchestrator already exists for project with status '{existing_orchestrator.status}'"
                        ),
                        context={
                            "project_id": project_id,
                            "tenant_key": tenant_key,
                            "existing_agent_id": existing_orchestrator.agent_id,
                            "existing_status": existing_orchestrator.status,
                        },
                    )

    async def _resolve_spawn_template(
        self,
        session: AsyncSession,
        project: Any,
        agent_name: str,
        mission: str,
        tenant_key: str,
        agent_display_name: str,
    ) -> tuple[str, Optional[str]]:
        """
        Resolve template injection for multi-terminal mode.

        Handover 0417: In multi_terminal execution mode, look up the agent template
        and inject its expertise/protocol instructions into the mission.

        Args:
            session: Active database session
            project: Project model instance
            agent_name: Agent name/identifier (template lookup key)
            mission: Current mission text
            tenant_key: Tenant key for isolation
            agent_display_name: Display name of agent (for logging)

        Returns:
            Tuple of (potentially modified mission, resolved template_id or None)
        """
        resolved_template_id = None

        if project.execution_mode == "multi_terminal":
            # Look up template by agent_name
            template_result = await session.execute(
                select(AgentTemplate).where(
                    and_(
                        AgentTemplate.name == agent_name,
                        AgentTemplate.tenant_key == tenant_key,
                        AgentTemplate.is_active,
                    )
                )
            )
            template = template_result.scalar_one_or_none()

            if template:
                # Handover 0411a: Capture template_id for AgentJob
                resolved_template_id = template.id

                # Get template content (Handover 0106: system_instructions + user_instructions)
                template_expertise = ""
                if template.system_instructions:
                    template_expertise = template.system_instructions
                    if template.user_instructions:
                        template_expertise += "\n\n" + template.user_instructions

                if template_expertise:
                    # Inject template into mission with tidy framing (Handover 0417)
                    # Uses chapter-based visual pattern from _build_orchestrator_protocol
                    framed_mission = f"""╔═════════════════════════════════════════════════════════════════════════╗
║                     AGENT EXPERTISE & PROTOCOL                           ║
╚═════════════════════════════════════════════════════════════════════════╝

{template_expertise}

╔═════════════════════════════════════════════════════════════════════════╗
║                       YOUR ASSIGNED WORK                                 ║
╚═════════════════════════════════════════════════════════════════════════╝

{mission}"""
                    mission = framed_mission
                    self._logger.info(
                        "[TEMPLATE_INJECTION] Injected template into mission for multi-terminal mode",
                        extra={
                            "agent_name": agent_name,
                            "agent_display_name": agent_display_name,
                            "template_id": template.id,
                            "execution_mode": project.execution_mode,
                        },
                    )
            else:
                # Template not found - log warning but proceed
                self._logger.warning(
                    f"[TEMPLATE_INJECTION] No template found for agent_name={agent_name} in multi-terminal mode. "
                    f"Proceeding with orchestrator's mission as-is.",
                    extra={
                        "agent_name": agent_name,
                        "agent_display_name": agent_display_name,
                        "execution_mode": project.execution_mode,
                        "tenant_key": tenant_key,
                    },
                )
        # For claude_code_cli mode, no injection (Task tool handles template loading)

        return mission, resolved_template_id

    async def _broadcast_agent_created(
        self,
        tenant_key: str,
        project_id: str,
        agent_execution: Any,
        agent_id: str,
        job_id: str,
        agent_display_name: str,
        agent_name: str,
        mission: str,
        phase: Optional[int],
        prompt_tokens: int,
        mission_tokens: int,
        created_at: datetime,
    ) -> None:
        """
        Broadcast agent:created event via WebSocket.

        Args:
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            agent_execution: AgentExecution model instance (for execution_id)
            agent_id: Executor UUID
            job_id: Work order UUID
            agent_display_name: Display name of agent
            agent_name: Agent name/identifier
            mission: Agent mission text
            phase: Execution phase for multi-terminal ordering
            prompt_tokens: Estimated prompt token count
            mission_tokens: Estimated mission token count
            created_at: Timestamp of creation
        """
        self._logger.info(
            f"[WEBSOCKET] Broadcasting agent:created for {agent_name} ({agent_display_name}) via direct WebSocket"
        )
        try:
            if self._websocket_manager:
                await self._websocket_manager.broadcast_to_tenant(
                    tenant_key=tenant_key,
                    event_type="agent:created",
                    data={
                        "project_id": project_id,
                        "execution_id": agent_execution.id,  # Handover 0457: Unique row ID for frontend Map key
                        "agent_id": agent_id,  # Executor UUID
                        "job_id": job_id,  # Work order UUID
                        "agent_display_name": agent_display_name,
                        "agent_name": agent_name,
                        "status": "waiting",
                        "thin_client": True,
                        "prompt_tokens": prompt_tokens,
                        "mission_tokens": mission_tokens,
                        "timestamp": created_at.isoformat(),
                        "mission": mission,  # Handover 0464: Include mission for UI display
                        "phase": phase,  # Handover 0411a: Execution phase
                    },
                )
        except Exception as ws_error:  # Broad catch: WebSocket resilience, non-critical broadcast
            self._logger.error(f"[WEBSOCKET ERROR] Failed to broadcast agent:created: {ws_error}", exc_info=True)

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> MissionResponse:
        """
        Get agent-specific mission from database.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        Handover 0381: Renamed parameter from job_id to job_id (new contract).
        - job_id: Work order UUID (what work is assigned)
        - Queries AgentJob for mission
        - Queries latest active AgentExecution for the job

        Handover 0730b: Exception-based error handling (no success wrapper).

        For CLI subagents (Handover 0262 / 0332), this method implements
        the atomic job start semantics:

        - On first successful fetch for an execution in "waiting" status:
          - Transitions status waiting -> working
          - Sets started_at timestamp
          - Emits agent:status_changed (drives status chip)
        - On subsequent fetches:
          - Returns mission and metadata without mutating timestamps or status
          - Does NOT emit additional WebSocket events (idempotent re-read)

        Args:
            job_id: Work order UUID (what work is assigned)
            tenant_key: Tenant key for isolation

        Returns:
            Dict with mission details and metadata

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

            async with self._get_session() as session:
                # Get the job (work order)
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

                # Get latest active execution for this job
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

                # Handover 0709: Implementation phase gate - check if user has clicked "Implement"
                if job.project_id:
                    from src.giljo_mcp.models.projects import Project

                    # TENANT ISOLATION: Replace session.get() with tenant-scoped query (Phase D audit fix)
                    project_res = await session.execute(
                        select(Project).where(Project.id == job.project_id, Project.tenant_key == tenant_key)
                    )
                    project = project_res.scalar_one_or_none()
                    if project and project.implementation_launched_at is None:
                        # BLOCKED: User must click "Implement" button first
                        return MissionResponse(
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

                # Handover 0353: Fetch all project executions for team context
                if job.project_id:
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

                    # Build mission lookup for team context generation
                    for _, job_row in rows:
                        mission_lookup[job_row.job_id] = job_row.mission
                else:
                    all_project_executions = [execution]
                    mission_lookup[job.job_id] = job.mission

                # Atomic start semantics on FIRST mission fetch
                if execution.status == "waiting":
                    now = datetime.now(timezone.utc)
                    old_status = execution.status
                    execution.status = "working"
                    execution.started_at = now
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
                    # Do not fail mission fetch on WebSocket broadcast issues
                    self._logger.warning(f"[WEBSOCKET] Failed to emit status events: {ws_error}")

            if not execution or not job:
                # Safety guard - should be unreachable due to earlier NOT_FOUND raise
                raise ResourceNotFoundError(
                    message=f"Agent job {job_id} not found",
                    context={"job_id": job_id, "tenant_key": tenant_key},
                )

            # Handover 0353: Generate team-aware mission with context header
            team_context_header = _generate_team_context_header(
                execution, all_project_executions, mission_lookup=mission_lookup
            )
            raw_mission = job.mission or ""
            full_mission = team_context_header + raw_mission

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

            estimated_tokens = len(full_mission) // 4

            # Generate 5-phase lifecycle protocol (Handover 0334, 0359, 0378 Bug 2, 0497d)
            project_exec_mode = getattr(project, "execution_mode", "multi_terminal") if project else "multi_terminal"
            git_enabled = get_config().get_nested("features.git_integration.enabled", default=False)
            full_protocol = _generate_agent_protocol(
                job_id=job_id,
                tenant_key=tenant_key,
                agent_name=execution.agent_display_name,
                agent_id=str(execution.agent_id),
                execution_mode=project_exec_mode,
                git_integration_enabled=git_enabled,
            )

            # Handover 0731c: Typed return (MissionResponse)
            return MissionResponse(
                job_id=job.job_id,  # Work order UUID
                agent_id=execution.agent_id,  # Executor UUID
                agent_name=execution.agent_display_name,
                agent_display_name=execution.agent_display_name,
                mission=full_mission,  # Handover 0353: Team-aware mission with context header
                project_id=str(job.project_id),
                parent_job_id=str(execution.spawned_by) if execution.spawned_by else None,
                estimated_tokens=estimated_tokens,
                status=execution.status,  # Execution status
                created_at=job.created_at.isoformat() if job.created_at else None,  # Job creation time
                started_at=execution.started_at.isoformat() if execution.started_at else None,  # Execution start time
                thin_client=True,
                full_protocol=full_protocol,  # Handover 0334: 6-phase agent lifecycle
            )

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get agent mission")
            raise DatabaseError(
                message=f"Unexpected error: {e!s}", context={"job_id": job_id, "tenant_key": tenant_key}
            ) from e

    async def get_pending_jobs(self, tenant_key: str, agent_display_name: Optional[str] = None) -> PendingJobsResult:
        """
        Get pending jobs, optionally filtered by agent display name.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Queries AgentExecution.status for execution state (waiting, working, etc.)
        - Mission comes from AgentJob via join
        - Returns both job_id (work order) and agent_id (executor)

        Args:
            tenant_key: Tenant key for isolation
            agent_display_name: Optional display name of agent to filter by

        Returns:
            Dict with list of pending jobs

        Example:
            >>> result = await service.get_pending_jobs(
            ...     tenant_key="tenant-abc",
            ...     agent_display_name="Code Implementer"  # Optional filter
            ... )
        """
        try:
            # Validate inputs

            if not tenant_key or not tenant_key.strip():
                raise ValidationError(
                    message="tenant_key cannot be empty",
                    context={"agent_display_name": agent_display_name, "tenant_key": tenant_key},
                )

            # Get pending executions with their jobs (dual-model)
            async with self._get_session() as session:
                # Build query with optional agent_display_name filter
                stmt = (
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status == "waiting",  # Execution status, not job status
                    )
                )
                # Add optional filter by agent_display_name
                if agent_display_name and agent_display_name.strip():
                    stmt = stmt.where(AgentExecution.agent_display_name == agent_display_name)
                stmt = stmt.limit(10)
                result = await session.execute(stmt)
                rows = result.all()

                # Format jobs for response
                formatted_jobs = []
                for execution, job in rows:
                    formatted_jobs.append(
                        {
                            "job_id": job.job_id,  # Work order ID
                            "agent_id": execution.agent_id,  # Executor ID
                            "execution_id": str(execution.id) if hasattr(execution, "id") else None,  # Unique row ID
                            "tenant_key": execution.tenant_key,  # For job_to_response
                            "project_id": job.project_id,  # From AgentJob
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "mission": job.mission,  # Mission from AgentJob
                            "status": execution.status,  # Execution status
                            "progress": execution.progress if hasattr(execution, "progress") else 0,
                            "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "priority": "normal",
                        }
                    )

                return PendingJobsResult(jobs=formatted_jobs, count=len(formatted_jobs))

        except ValidationError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get pending jobs")
            raise DatabaseError(
                message=f"Failed to get pending jobs: {e!s}",
                context={"agent_display_name": agent_display_name, "tenant_key": tenant_key},
            ) from e

    async def report_progress(
        self,
        job_id: str,
        progress: dict[str, Any] | None = None,
        tenant_key: Optional[str] = None,
        todo_items: list[dict] | None = None,
    ) -> ProgressResult:
        """
        Report job progress (store message in message queue).

        Args:
            job_id: Job UUID
            progress: Progress data dict (legacy format, optional)
            tenant_key: Optional tenant key (uses current if not provided)
            todo_items: Simplified TODO items array (Handover 0392)
                        [{"content": "Task A", "status": "completed"}, ...]

        Returns:
            Dict with success status

        Example (new simplified format):
            >>> result = await service.report_progress(
            ...     job_id="job-123",
            ...     todo_items=[
            ...         {"content": "Task A", "status": "completed"},
            ...         {"content": "Task B", "status": "in_progress"},
            ...         {"content": "Task C", "status": "pending"}
            ...     ]
            ... )

        Example (legacy format, still supported):
            >>> result = await service.report_progress(
            ...     job_id="job-123",
            ...     progress={"percent": 50, "message": "Half done"}
            ... )
        """

        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "report_progress"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "report_progress"})

            # Handover 0392: Support top-level todo_items parameter (simplified format)
            # If todo_items provided at top level, derive progress metrics from it
            if todo_items is not None:
                if not isinstance(todo_items, list):
                    raise ValidationError(
                        message="todo_items must be a list",
                        context={"method": "report_progress", "todo_items_type": type(todo_items).__name__},
                    )

                # Calculate progress metrics from todo_items
                completed_steps = len([t for t in todo_items if t.get("status") == "completed"])
                total_steps = len(todo_items)
                in_progress_items = [t for t in todo_items if t.get("status") == "in_progress"]
                current_step = in_progress_items[0].get("content") if in_progress_items else None
                percent = (completed_steps / total_steps * 100) if total_steps > 0 else 0

                # Build progress dict for backwards compatibility with existing code
                progress = {
                    "mode": "todo",
                    "percent": percent,
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "current_step": current_step,
                    "todo_items": todo_items,
                }
            elif progress is None:
                raise ValidationError(
                    message="Either progress or todo_items must be provided", context={"method": "report_progress"}
                )
            elif not isinstance(progress, dict):
                raise ValidationError(
                    message="progress must be a dict",
                    context={"method": "report_progress", "progress_type": type(progress).__name__},
                )

            # Extract todo_items from progress dict if not already set (backwards compatibility)
            if todo_items is None and "todo_items" in progress:
                todo_items = progress.get("todo_items")

            # Fetch execution and job info for progress tracking
            job = None
            execution = None
            async with self._get_session() as session:
                # Get latest active execution
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "report_progress"},
                    )

                # Get job for metadata and project_id
                # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_res.scalar_one_or_none()

                if not job:
                    raise ResourceNotFoundError(
                        message=f"Job {job_id} not found", context={"job_id": job_id, "method": "report_progress"}
                    )

                # Update execution progress fields
                execution.last_progress_at = datetime.now(timezone.utc)

                # Extract progress percentage and current task from progress dict
                if "percent" in progress:
                    execution.progress = min(100, max(0, int(progress["percent"])))
                if "message" in progress or "current_step" in progress:
                    execution.current_task = progress.get("message") or progress.get("current_step")

                # Optional TODO-style steps tracking for Steps column (Handover 0297)
                # Store in AgentJob.job_metadata (job-level data)
                mode = progress.get("mode")
                if mode == "todo":
                    total_steps = progress.get("total_steps")
                    completed_steps = progress.get("completed_steps")
                    current_step = progress.get("current_step")

                    if (
                        isinstance(total_steps, int)
                        and total_steps > 0
                        and isinstance(completed_steps, int)
                        and 0 <= completed_steps <= total_steps
                    ):
                        # Persist latest TODO summary into job_metadata.todo_steps
                        from sqlalchemy.orm.attributes import flag_modified

                        metadata = job.job_metadata or {}
                        skipped_steps = progress.get("skipped_steps", 0)
                        todo_steps = {
                            "total_steps": total_steps,
                            "completed_steps": completed_steps,
                            "skipped_steps": skipped_steps if isinstance(skipped_steps, int) else 0,
                        }
                        if isinstance(current_step, str) and current_step.strip():
                            todo_steps["current_step"] = current_step

                        metadata["todo_steps"] = todo_steps
                        job.job_metadata = metadata
                        flag_modified(job, "job_metadata")

                # Handover 0402: Store todo_items in dedicated table for Plan/TODOs tab display
                # Process todo_items array: [{ content: "...", status: "pending|in_progress|completed" }, ...]
                todo_items = progress.get("todo_items")
                if isinstance(todo_items, list) and len(todo_items) > 0:
                    from sqlalchemy import delete as sql_delete

                    # Delete existing items for this job (replace strategy)
                    # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                    await session.execute(
                        sql_delete(AgentTodoItem).where(
                            AgentTodoItem.job_id == job_id, AgentTodoItem.tenant_key == tenant_key
                        )
                    )

                    # Insert new items with sequence
                    for seq, item in enumerate(todo_items):
                        if isinstance(item, dict) and item.get("content"):
                            status = item.get("status", "pending")
                            # Validate status
                            if status not in ("pending", "in_progress", "completed", "skipped"):
                                status = "pending"

                            todo_item = AgentTodoItem(
                                job_id=job_id,
                                tenant_key=tenant_key,
                                content=str(item["content"])[:255],  # Truncate to column limit
                                status=status,
                                sequence=seq,
                            )
                            session.add(todo_item)

                await session.commit()
                await session.refresh(execution)
                await session.refresh(job)

            if not job:
                raise ResourceNotFoundError(
                    message=f"Job {job_id} not found after commit",
                    context={"job_id": job_id, "method": "report_progress"},
                )

            await self._fetch_and_broadcast_progress(tenant_key, job_id, job, execution, progress)

            # Handover 0406: Reactive warning for missing todo_items
            warnings = []
            todo_items = progress.get("todo_items")
            # Check throttle - only warn once per 5 minutes per job
            if (not isinstance(todo_items, list) or len(todo_items) == 0) and self._can_warn_missing_todos(job_id):
                warnings.append(
                    "WARNING: todo_items missing! Dashboard Steps shows '--'. "
                    "Include todo_items=[{content, status}] in every report_progress() call."
                )
                self._record_todo_warning(job_id)

            return ProgressResult(
                status="success",
                message="Progress reported successfully",
                warnings=warnings,
            )
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to report progress")
            raise OrchestrationError(
                message="Failed to report progress", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def _fetch_and_broadcast_progress(
        self,
        tenant_key: str,
        job_id: str,
        job: "AgentJob",
        execution: "AgentExecution",
        progress: dict[str, Any],
    ) -> None:
        """Fetch todo_items from DB and broadcast progress update via WebSocket."""
        # Handover 0402: Query todo_items for WebSocket payload
        todo_items_payload = None
        async with self._get_session() as session:
            # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
            result = await session.execute(
                select(AgentTodoItem)
                .where(AgentTodoItem.job_id == job_id, AgentTodoItem.tenant_key == tenant_key)
                .order_by(AgentTodoItem.sequence)
            )
            items = result.scalars().all()
            if items:
                todo_items_payload = [{"content": item.content, "status": item.status} for item in items]

        # Handover 0386: Direct WebSocket emission for progress updates
        # DO NOT use MessageService.send_message() - that creates erroneous message records
        # Progress is already persisted in execution.progress and job.job_metadata["todo_steps"]
        # We only need to emit a WebSocket event for real-time UI updates
        try:
            if self._websocket_manager:
                await self._websocket_manager.broadcast_to_tenant(
                    tenant_key=tenant_key,
                    event_type="job:progress_update",
                    data={
                        "job_id": job_id,
                        "project_id": str(job.project_id) if job.project_id else None,
                        "agent_id": execution.agent_id,
                        "agent_display_name": execution.agent_display_name,
                        "agent_name": execution.agent_name,
                        "progress": progress,
                        "progress_percent": execution.progress,
                        "current_task": execution.current_task,
                        "todo_steps": job.job_metadata.get("todo_steps") if job.job_metadata else None,
                        "todo_items": todo_items_payload,  # Handover 0402: Include for Plan/TODOs tab
                        "last_progress_at": execution.last_progress_at.isoformat()
                        if execution.last_progress_at
                        else None,
                    },
                )
                self._logger.info(f"[WEBSOCKET] Broadcasted job:progress_update for {job_id}")
        except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
            self._logger.warning(f"[WEBSOCKET] Failed to broadcast progress: {ws_error}")

    async def complete_job(
        self, job_id: str, result: dict[str, Any], tenant_key: Optional[str] = None
    ) -> CompleteJobResult:
        """
        Mark job as complete (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
            result: Job result data dict (for backwards compatibility, not currently used)
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status

        Example:
            >>> result = await service.complete_job(
            ...     job_id="job-123",
            ...     result={"output": "Task completed successfully"}
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "complete_job"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "complete_job"})
            if not result or not isinstance(result, dict):
                raise ValidationError(
                    message="result must be a non-empty dict",
                    context={"method": "complete_job", "result_type": type(result).__name__},
                )

            completion_attempt_time = datetime.now(timezone.utc)

            # Database update
            job = None
            execution = None
            old_status = None
            duration_seconds = None
            warnings = []  # Handover 0710: Soft warnings for orchestrator completion
            async with self._get_session() as session:
                # Try new dual-model path first
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if execution:
                    # NEW PATH: Dual-model (AgentExecution)
                    # Get job
                    job_res = await session.execute(
                        select(AgentJob).where(
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key,
                        )
                    )
                    job = job_res.scalar_one_or_none()
                    if not job:
                        raise ResourceNotFoundError(
                            message=f"Job {job_id} not found", context={"job_id": job_id, "method": "complete_job"}
                        )

                    # Validate completion requirements (unread messages and incomplete TODOs)
                    unread_query = select(Message).where(
                        and_(
                            Message.tenant_key == tenant_key,
                            Message.project_id == job.project_id,
                            Message.status == "pending",
                            Message.to_agents.contains([execution.agent_id]),
                        )
                    )
                    unread_res = await session.execute(unread_query)
                    unread_messages = unread_res.scalars().all()

                    def _is_before_attempt(message: Message) -> bool:
                        if not message.created_at:
                            return True
                        created_at = message.created_at
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=timezone.utc)
                        return created_at <= completion_attempt_time

                    unread_messages = [message for message in unread_messages if _is_before_attempt(message)]

                    todo_query = select(AgentTodoItem).where(
                        and_(
                            AgentTodoItem.job_id == job_id,
                            AgentTodoItem.tenant_key == tenant_key,
                            AgentTodoItem.status != "completed",
                        )
                    )
                    todo_res = await session.execute(todo_query)
                    incomplete_todos = todo_res.scalars().all()

                    if unread_messages or incomplete_todos:
                        reasons = []
                        if unread_messages:
                            unread_ids = [str(msg.id) for msg in unread_messages[:5]]
                            reasons.append(
                                f"Read and process {len(unread_messages)} pending message(s) before completing. "
                                f"Call receive_messages() to retrieve: {unread_ids}"
                            )
                        if incomplete_todos:
                            todo_names = [todo.content for todo in incomplete_todos[:5]]
                            reasons.append(f"{len(incomplete_todos)} TODO items not completed: {todo_names}")

                        self._logger.info(
                            "Completion blocked by protocol validation",
                            extra={
                                "job_id": job_id,
                                "tenant_key": tenant_key,
                                "unread_messages": len(unread_messages),
                                "incomplete_todos": len(incomplete_todos),
                            },
                        )

                        raise ValidationError(
                            message="COMPLETION_BLOCKED: Complete all TODO items and read all messages before calling complete_job()",
                            error_code="COMPLETION_BLOCKED",
                            context={
                                "job_id": job_id,
                                "reasons": reasons,
                                "unread_messages": len(unread_messages),
                                "incomplete_todos": len(incomplete_todos),
                            },
                        )

                    # Capture old status before updating
                    old_status = execution.status

                    # Update execution status
                    execution.status = "complete"
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.progress = 100  # Set to 100% on completion
                    # 0497b: Persist completion result
                    execution.result = result

                    # Calculate duration if started_at exists
                    if execution.started_at and execution.completed_at:
                        duration_seconds = (execution.completed_at - execution.started_at).total_seconds()

                    # Also update job status to completed if this is the last active execution
                    # Check if there are any other active executions
                    # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                    other_active_stmt = select(AgentExecution).where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.agent_id != execution.agent_id,
                        AgentExecution.status.not_in(["complete", "decommissioned"]),
                    )
                    other_active_res = await session.execute(other_active_stmt)
                    other_active = other_active_res.scalar_one_or_none()

                    if not other_active:
                        # No other active executions, mark job as completed
                        job.status = "completed"
                        job.completed_at = execution.completed_at

                    # Handover 0710: Check if orchestrator needs 360 memory reminder
                    if execution.agent_display_name == "orchestrator":
                        # Get project to check staging status
                        project_stmt = select(Project).where(
                            Project.id == job.project_id,
                            Project.tenant_key == tenant_key,
                        )
                        project_res = await session.execute(project_stmt)
                        project = project_res.scalar_one_or_none()

                        # Only warn for non-staging orchestrators with a product
                        skip_staging = project and project.staging_status in ("staging", "staged")
                        has_product = project and project.product_id

                        if not skip_staging and has_product:
                            # Check if any 360 memory entry exists for this project
                            memory_stmt = (
                                select(ProductMemoryEntry)
                                .where(
                                    ProductMemoryEntry.project_id == str(job.project_id),
                                    ProductMemoryEntry.tenant_key == tenant_key,
                                )
                                .limit(1)
                            )
                            memory_res = await session.execute(memory_stmt)
                            has_memory = memory_res.scalar_one_or_none() is not None

                            if not has_memory:
                                warnings.append(
                                    "REMINDER: No 360 Memory entry found for this project. "
                                    "Consider calling write_360_memory() to preserve project "
                                    "knowledge for future orchestrators."
                                )

                    # 0497b: Auto-generate completion message to orchestrator
                    if job.project_id and execution.agent_display_name != "orchestrator":
                        orch_exec = await self._find_orchestrator_execution(session, str(job.project_id), tenant_key)
                        if orch_exec and orch_exec.agent_id != execution.agent_id:
                            summary = result.get("summary", "Work completed")
                            auto_message = Message(
                                tenant_key=tenant_key,
                                project_id=str(job.project_id),
                                meta_data={"_from_agent": str(execution.agent_id), "auto_generated": True},
                                to_agents=[orch_exec.agent_id],
                                content=f"COMPLETION REPORT from {execution.agent_display_name}: {summary}",
                                message_type="completion_report",
                                status="pending",
                            )
                            session.add(auto_message)
                            orch_exec.messages_waiting_count = (orch_exec.messages_waiting_count or 0) + 1
                            execution.messages_sent_count = (execution.messages_sent_count or 0) + 1

                    await session.commit()
                else:
                    # No active execution found
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "complete_job"},
                    )

            # WebSocket emission for real-time UI updates (after session closed)
            if execution:
                await self._broadcast_completion(tenant_key, job_id, job, execution, old_status, duration_seconds)

            # Handover 0731c: Typed return (CompleteJobResult)
            return CompleteJobResult(
                status="success",
                job_id=job_id,
                message="Job completed successfully",
                warnings=warnings,
                result_stored=True,
            )
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to complete job")
            raise OrchestrationError(
                message="Failed to complete job", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def _broadcast_completion(
        self,
        tenant_key: str,
        job_id: str,
        job: "AgentJob",
        execution: "AgentExecution",
        old_status: str | None,
        duration_seconds: float | None,
    ) -> None:
        """Broadcast job completion status change via WebSocket."""
        try:
            if self._websocket_manager:
                await self._websocket_manager.broadcast_to_tenant(
                    tenant_key=tenant_key,
                    event_type="agent:status_changed",
                    data={
                        "job_id": job_id,
                        "project_id": str(job.project_id) if job.project_id else None,
                        "agent_display_name": execution.agent_display_name,
                        "agent_name": execution.agent_name,
                        "old_status": old_status,
                        "status": "complete",
                        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                        "duration_seconds": duration_seconds,
                        "has_result": True,
                    },
                )
                self._logger.info(f"[WEBSOCKET] Broadcasted complete_job status change for {job_id}")
        except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
            self._logger.warning(f"[WEBSOCKET] Failed to broadcast complete_job: {ws_error}")

    async def _find_orchestrator_execution(self, session, project_id: str, tenant_key: str):
        """Find the active orchestrator execution for a project."""
        from sqlalchemy import select

        from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentJob.tenant_key == tenant_key,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.status.not_in(["complete", "decommissioned"]),
            )
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_agent_result(self, job_id: str, tenant_key: str | None = None) -> dict | None:
        """Fetch the completion result for a given job's latest execution.

        Args:
            job_id: Job UUID
            tenant_key: Tenant key for isolation

        Returns:
            Result dict or None if no completed execution found
        """
        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            return None

        async with self._get_session() as session:
            stmt = (
                select(AgentExecution)
                .where(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status == "complete",
                )
                .order_by(AgentExecution.completed_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            execution = res.scalar_one_or_none()
            if execution and execution.result:
                return execution.result
            return None

    async def report_error(self, job_id: str, error: str, tenant_key: Optional[str] = None) -> ErrorReportResult:
        """
        Report job error (AgentExecution, async safe).

        Handover 0491: Simplified - severity parameter removed.
        All errors set status to 'blocked' with block_reason.
        Agents can recover from blocked state.

        Args:
            job_id: Job UUID (looks up latest active execution)
            error: Error message
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status

        Example:
            >>> result = await service.report_error(
            ...     job_id="job-123",
            ...     error="Failed to compile code"
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "report_error"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "report_error"})
            if not error or not error.strip():
                raise ValidationError(
                    message="error message cannot be empty", context={"method": "report_error", "job_id": job_id}
                )

            job = None
            async with self._get_session() as session:
                # Get latest active execution
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "report_error"},
                    )

                # Get job for project_id (needed for WebSocket event filtering)
                # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_res.scalar_one_or_none()

                # Capture old status before updating
                old_status = execution.status

                # Handover 0491: Always set to blocked with block_reason
                execution.status = "blocked"
                execution.block_reason = error

                await session.commit()

            # WebSocket emission for real-time UI updates (after session closed)
            try:
                if self._websocket_manager:
                    ws_data = {
                        "job_id": job_id,
                        "project_id": str(job.project_id) if job and job.project_id else None,
                        "agent_display_name": execution.agent_display_name,
                        "agent_name": execution.agent_name,
                        "old_status": old_status,
                        "status": "blocked",
                        "block_reason": error,
                    }
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data=ws_data,
                    )
                    self._logger.info(f"[WEBSOCKET] Broadcasted report_error status change for {job_id}")
            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                self._logger.warning(f"[WEBSOCKET] Failed to broadcast report_error: {ws_error}")

            return ErrorReportResult(job_id=job_id, message="Error reported")
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to report error")
            raise OrchestrationError(
                message="Failed to report error", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def list_jobs(
        self,
        tenant_key: str,
        project_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        agent_display_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> JobListResult:
        """
        List agent jobs with flexible filtering.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Joins AgentExecution with AgentJob to get complete data
        - Mission comes from AgentJob
        - Status, progress, timestamps from AgentExecution
        - Returns both job_id (work order) and agent_id (executor)

        Supports filtering by project, status, and agent display name with pagination.
        All jobs are filtered by tenant_key for multi-tenant isolation.

        Args:
            tenant_key: Tenant key for isolation (required)
            project_id: Filter by project UUID (optional)
            status_filter: Filter by status (waiting, active, completed, failed) (optional)
            agent_display_name: Filter by agent display name (Orchestrator, Implementer, etc.) (optional)
            limit: Maximum results (default 100, max 500)
            offset: Pagination offset (default 0)

        Returns:
            Dict with structure:
            {
                "jobs": [list of job dicts],
                "total": int (total count matching filters),
                "limit": int (limit applied),
                "offset": int (offset applied)
            }

        Raises:
            Exception: Database errors (logged and returned in error field)

        Example:
            >>> result = await service.list_jobs(
            ...     tenant_key="tk_abc123",
            ...     project_id="proj_xyz",
            ...     status_filter="active"
            ... )
            >>> print(f"Found {len(result['jobs'])} active jobs")
        """
        try:
            from sqlalchemy import func, select
            from sqlalchemy.orm import selectinload

            async with self._get_session() as session:
                # Build query with filters (join AgentExecution with AgentJob)
                # Handover 0423: Load todo_items relationship for Plan tab display
                query = (
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .options(selectinload(AgentJob.todo_items))
                    .where(AgentExecution.tenant_key == tenant_key)
                )

                if project_id:
                    query = query.where(AgentJob.project_id == project_id)
                if status_filter:
                    query = query.where(AgentExecution.status == status_filter)
                if agent_display_name:
                    query = query.where(AgentExecution.agent_display_name == agent_display_name)

                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar()

                # Apply pagination and order
                query = query.order_by(AgentJob.created_at.desc())
                query = query.limit(limit).offset(offset)

                result = await session.execute(query)
                rows = result.all()

                # Convert to dicts
                job_dicts = []
                for execution, job in rows:
                    # DIAGNOSTIC: Log message counters for debugging persistence
                    self._logger.debug(
                        f"[LIST_JOBS DEBUG] Agent {execution.agent_display_name} (job={job.job_id}, agent={execution.agent_id}): "
                        f"{execution.messages_sent_count} sent, {execution.messages_waiting_count} waiting, {execution.messages_read_count} read"
                    )

                    # Derive simple numeric steps summary from job_metadata.todo_steps (Handover 0297)
                    steps_summary = None
                    try:
                        metadata = job.job_metadata or {}
                        todo_steps = metadata.get("todo_steps") or {}
                        total_steps = todo_steps.get("total_steps")
                        completed_steps = todo_steps.get("completed_steps")
                        skipped_steps = todo_steps.get("skipped_steps", 0)
                        if (
                            isinstance(total_steps, int)
                            and total_steps > 0
                            and isinstance(completed_steps, int)
                            and 0 <= completed_steps <= total_steps
                        ):
                            steps_summary = {
                                "total": total_steps,
                                "completed": completed_steps,
                                "skipped": skipped_steps if isinstance(skipped_steps, int) else 0,
                            }
                        # Fallback: derive steps from todo_items if metadata doesn't have it
                        if not steps_summary and job.todo_items:
                            total = len(job.todo_items)
                            completed = sum(1 for item in job.todo_items if item.status == "completed")
                            skipped = sum(1 for item in job.todo_items if item.status == "skipped")
                            if total > 0:
                                steps_summary = {"total": total, "completed": completed, "skipped": skipped}
                    except (KeyError, ValueError, TypeError, AttributeError):
                        # Do not break listing if metadata has unexpected shape
                        self._logger.warning(
                            "[LIST_JOBS] Failed to derive steps summary from job_metadata",
                            exc_info=True,
                        )

                    job_dicts.append(
                        {
                            "job_id": job.job_id,  # Work order ID
                            "agent_id": execution.agent_id,  # Executor ID (same across succession)
                            "execution_id": execution.id,  # UNIQUE per row - use as Map key
                            "tenant_key": execution.tenant_key,
                            "project_id": job.project_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "mission": job.mission,  # Mission from AgentJob
                            "phase": job.phase,  # Handover 0411a: Execution phase
                            "status": execution.status,  # Execution status
                            "progress": execution.progress,  # Execution progress
                            "spawned_by": execution.spawned_by,  # Parent agent_id
                            "tool_type": execution.tool_type,
                            "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
                            # Counter fields replace JSONB messages array (Handover 0387)
                            "messages_sent_count": execution.messages_sent_count,
                            "messages_waiting_count": execution.messages_waiting_count,
                            "messages_read_count": execution.messages_read_count,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "steps": steps_summary,
                            # Handover 0423: Include todo_items for Plan tab display
                            "todo_items": [
                                {"content": item.content, "status": item.status}
                                for item in sorted(job.todo_items or [], key=lambda x: x.sequence)
                            ],
                            "result": execution.result,  # Handover 0497e
                            "template_id": job.template_id,  # Handover 0814: for AgentDetailsModal lookup
                        }
                    )

                self._logger.info(
                    f"Listed {len(job_dicts)} jobs (total={total}, project={project_id}, status={status_filter})"
                )

                return JobListResult(
                    jobs=job_dicts,
                    total=total,
                    limit=limit,
                    offset=offset,
                )

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list jobs")
            raise OrchestrationError(
                message="Failed to list jobs", context={"tenant_key": tenant_key, "error": str(e)}
            ) from e

    # NOTE: update_context_usage(), estimate_message_tokens(), _trigger_auto_succession(),
    # and trigger_succession() were removed in Handover 0422/0700d - the MCP server is passive
    # and cannot track external CLI tool context usage.
    # Manual succession via UI button (simple-handover REST endpoint).

    # ========================================================================
    # Handover 0450: Orchestrator Logic Consolidation
    # Methods moved from orchestrator.py to OrchestrationService
    # ========================================================================

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

    # ============================================================================
    # Orchestrator Instructions & Mission Management (Handover 0451 Phase 2)
    # ============================================================================

    def _build_execution_mode_fields(self, execution_mode: str, templates: list, job_id: str) -> dict[str, Any]:
        """Build execution-mode-specific response fields (CLI rules or phase assignment)."""
        fields: dict[str, Any] = {}

        if execution_mode == "claude_code_cli":
            allowed_agent_names = [t.name for t in templates]

            # Handover 0389: Build dynamic example from actual allowed agent names
            example_agents = allowed_agent_names[:2] if len(allowed_agent_names) >= 2 else allowed_agent_names
            example_str = ", ".join(f"'{n}'" for n in example_agents) if example_agents else "'implementer'"

            fields["cli_mode_rules"] = {
                "agent_name_usage": (
                    "SINGLE SOURCE OF TRUTH - binds DB record, Task tool, and template filename. "
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
        - context_fetch_instructions: Framing pointers to fetch_context() tool

        The orchestrator uses these instructions to call fetch_context() on-demand,
        avoiding the 50K+ token truncation risk of inline context.
        """
        try:
            async with self._get_session() as session:
                from sqlalchemy import and_
                from sqlalchemy.orm import joinedload, selectinload

                from src.giljo_mcp.mission_planner import MissionPlanner
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
                    .order_by(AgentExecution.started_at.desc())
                )
                execution = result.scalars().first()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"Orchestrator execution for job {job_id} not found",
                        error_code="NOT_FOUND",
                        context={"job_id": job_id, "method": "get_orchestrator_instructions"},
                    )

                # Get the associated AgentJob
                agent_job = execution.job
                if not agent_job:
                    raise ResourceNotFoundError(
                        message=f"Agent job {job_id} not found",
                        error_code="NOT_FOUND",
                        context={"job_id": job_id, "method": "get_orchestrator_instructions"},
                    )

                # Verify it's an orchestrator
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

                # Get project and product
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
                    user_config = await _get_user_config(user_id, tenant_key, session)
                    field_priorities = user_config["field_priorities"]
                    depth_config = user_config["depth_config"]
                    logger.info(
                        "[USER_CONFIG] Fetched fresh user config for OrchestrationService",
                        extra={"job_id": job_id, "user_id": user_id},
                    )
                else:
                    field_priorities = metadata.get("field_priorities", {})
                    depth_config = metadata.get("depth_config", {})
                    logger.debug("[USER_CONFIG] No user_id, using frozen job_metadata config", extra={"job_id": job_id})

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
                    .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active))
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

                # Handover 0408: Read integration toggles from config
                include_serena = False
                git_integration_enabled = False
                try:
                    cfg = get_config()
                    include_serena = cfg.get_nested("features.serena_mcp.use_in_prompts", default=False)
                    git_integration_enabled = cfg.get_nested("features.git_integration.enabled", default=False)
                except (OSError, KeyError, ValueError, TypeError) as e:
                    logger.warning(f"[INTEGRATIONS] Failed to read config: {e}")

                # Build framing-based response (Handover 0350b + Phase C)
                # Includes: identity, project context, fetch instructions, AND agent templates
                response = {
                    "identity": {
                        "job_id": job_id,
                        "agent_id": execution.agent_id,  # Phase C: Add executor UUID
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
                        "report_progress",
                        "complete_job",
                    ],
                    "field_priorities": field_priorities,
                    "thin_client": True,
                    "architecture": "framing_based",
                    # Handover 0408: Integration toggles status
                    "integrations": {
                        "serena_mcp_enabled": include_serena,
                        "git_integration_enabled": git_integration_enabled,
                    },
                }

                # Handover 0351 / 0411a: Execution-mode-specific fields
                execution_mode = getattr(project, "execution_mode", None) or metadata.get(
                    "execution_mode", "multi_terminal"
                )
                response.update(self._build_execution_mode_fields(execution_mode, templates, job_id))

                # Handover 0415: Add chapter-based orchestrator protocol
                # Handover 0420d: Exclude CH5 during staging to save tokens
                cli_mode = execution_mode == "claude_code_cli"
                # Staging phase (waiting status) does not need CH5 implementation reference
                is_staging = execution.status == "waiting"
                orchestrator_protocol = _build_orchestrator_protocol(
                    cli_mode=cli_mode,
                    project_id=str(project.id),
                    orchestrator_id=job_id,
                    tenant_key=tenant_key,
                    include_implementation_reference=not is_staging,  # False for staging, True for implementation
                )
                response["orchestrator_protocol"] = orchestrator_protocol

                # Handover 0431: Inject orchestrator identity/behavioral guidance
                # Orchestrators don't have AgentTemplate records (SYSTEM_MANAGED_ROLES skip)
                # so they get behavioral guidance via this field instead of fetch_context(self_identity)
                from src.giljo_mcp.template_seeder import get_orchestrator_identity_content

                response["orchestrator_identity"] = get_orchestrator_identity_content()

                logger.info(
                    "[FRAMING_BASED] Returning framing-based orchestrator instructions",
                    extra={
                        "job_id": job_id,
                        "critical_count": len(fetch_instructions.get("critical", [])),
                        "important_count": len(fetch_instructions.get("important", [])),
                        "reference_count": len(fetch_instructions.get("reference", [])),
                    },
                )

                return response

        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            logger.exception("Failed to get orchestrator instructions")
            raise OrchestrationError(
                message="Failed to get orchestrator instructions",
                error_code="INTERNAL_ERROR",
                context={"job_id": job_id, "error": str(e)},
            ) from e

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

    @staticmethod
    async def health_check() -> dict[str, Any]:
        """MCP server health check."""
        return {
            "status": "healthy",
            "server": "giljo-mcp",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "message": "GiljoAI MCP server is operational",
        }

    # Succession methods removed (0391/0461/0700d)
    # Session refresh is handled by:
    #   - REST: POST /api/agent-jobs/{job_id}/simple-handover (UI button)
    # Agents cannot self-detect context exhaustion (passive HTTP architecture).
