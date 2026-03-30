"""
OrchestrationService - Facade for orchestration and job management.

Handover 0769: Refactored into a facade that delegates to:
- JobLifecycleService: spawn_agent_job, validation, template resolution
- MissionService: get_agent_mission, get_orchestrator_instructions, update_agent_mission
- ProgressService: report_progress, progress broadcasting

Remaining in this file: workflow status, pending jobs, job listing,
completion, error reporting, reactivation, health check.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Import MessageService for WebSocket-enabled messaging (Handover fix: message counter WebSocket)
# Using TYPE_CHECKING to document the type without circular import risk
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    DatabaseError,
    OrchestrationError,
    ProjectStateError,
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
from src.giljo_mcp.models.tasks import MessageRecipient
from src.giljo_mcp.schemas.service_responses import (
    AgentTodoCounts,
    AgentWorkflowDetail,
    CompleteJobResult,
    DismissResult,
    ErrorReportResult,
    JobListResult,
    MissionResponse,
    MissionUpdateResult,
    PendingJobsResult,
    ProgressResult,
    ReactivationResult,
    SpawnResult,
    WorkflowStatus,
)
from src.giljo_mcp.services.dto import BroadcastAgentCreatedContext
from src.giljo_mcp.services.job_lifecycle_service import JobLifecycleService
from src.giljo_mcp.services.mission_service import MissionService
from src.giljo_mcp.services.progress_service import ProgressService
from src.giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


class OrchestrationService:
    """Facade for orchestration and agent jobs (Handover 0769).

    Delegates to JobLifecycleService, MissionService, ProgressService.
    Retains: workflow status, pending jobs, listing, completion, error, reactivation.
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

        # Handover 0769: Facade sub-services
        self._job_lifecycle = JobLifecycleService(
            db_manager, tenant_manager, test_session, message_service, websocket_manager
        )
        self._mission = MissionService(db_manager, tenant_manager, test_session, message_service, websocket_manager)
        self._progress = ProgressService(db_manager, tenant_manager, test_session, message_service, websocket_manager)

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
        """Get a session, preferring an injected test session when provided."""
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
    # Agent Job Management — Facade Delegations (Handover 0769)
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
        """Facade: delegates to JobLifecycleService.spawn_agent_job."""
        return await self._job_lifecycle.spawn_agent_job(
            agent_display_name=agent_display_name,
            agent_name=agent_name,
            mission=mission,
            project_id=project_id,
            tenant_key=tenant_key,
            parent_job_id=parent_job_id,
            context_chunks=context_chunks,
            phase=phase,
            predecessor_job_id=predecessor_job_id,
        )

    async def _build_predecessor_context(
        self,
        session: AsyncSession,
        predecessor_job_id: str,
        tenant_key: str,
        project_id: str,
        mission: str,
        agent_display_name: str,
    ) -> str:
        """Facade: delegates to JobLifecycleService._build_predecessor_context."""
        return await self._job_lifecycle._build_predecessor_context(
            session, predecessor_job_id, tenant_key, project_id, mission, agent_display_name
        )

    async def _validate_spawn_agent(
        self,
        session: AsyncSession,
        agent_display_name: str,
        agent_name: str,
        tenant_key: str,
        project_id: str,
        parent_job_id: Optional[str],
    ) -> None:
        """Facade: delegates to JobLifecycleService._validate_spawn_agent."""
        return await self._job_lifecycle._validate_spawn_agent(
            session, agent_display_name, agent_name, tenant_key, project_id, parent_job_id
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
        """Facade: delegates to JobLifecycleService._resolve_spawn_template."""
        return await self._job_lifecycle._resolve_spawn_template(
            session, project, agent_name, mission, tenant_key, agent_display_name
        )

    async def _broadcast_agent_created(
        self,
        ctx: BroadcastAgentCreatedContext,
    ) -> None:
        """Facade: delegates to JobLifecycleService._broadcast_agent_created."""
        return await self._job_lifecycle._broadcast_agent_created(ctx)

    # ============================================================================
    # Mission & Orchestrator Instructions — Facade Delegations (Handover 0769)
    # ============================================================================

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> MissionResponse:
        """Facade: delegates to MissionService.get_agent_mission."""
        return await self._mission.get_agent_mission(job_id, tenant_key)

    async def get_orchestrator_instructions(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Facade: delegates to MissionService.get_orchestrator_instructions."""
        return await self._mission.get_orchestrator_instructions(job_id, tenant_key)

    async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str) -> MissionUpdateResult:
        """Facade: delegates to MissionService.update_agent_mission."""
        return await self._mission.update_agent_mission(job_id, tenant_key, mission)

    async def _get_agent_template_internal(
        self, role: str, tenant_key: str, product_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Optional[AgentTemplate]:
        """Facade: delegates to MissionService._get_agent_template_internal."""
        return await self._mission._get_agent_template_internal(role, tenant_key, product_id, session)

    def _build_execution_mode_fields(self, execution_mode: str, templates: list, job_id: str) -> dict[str, Any]:
        """Facade: delegates to MissionService._build_execution_mode_fields."""
        return self._mission._build_execution_mode_fields(execution_mode, templates, job_id)

    # ============================================================================
    # Progress Reporting — Facade Delegation (Handover 0769)
    # ============================================================================

    async def report_progress(
        self,
        job_id: str,
        progress: dict[str, Any] | None = None,
        tenant_key: Optional[str] = None,
        todo_items: list[dict] | None = None,
        todo_append: list[dict] | None = None,
    ) -> ProgressResult:
        """Facade: delegates to ProgressService.report_progress."""
        return await self._progress.report_progress(
            job_id=job_id,
            progress=progress,
            tenant_key=tenant_key,
            todo_items=todo_items,
            todo_append=todo_append,
        )

    async def _fetch_and_broadcast_progress(
        self,
        tenant_key: str,
        job_id: str,
        job: "AgentJob",
        execution: "AgentExecution",
        progress: dict[str, Any],
    ) -> None:
        """Facade: delegates to ProgressService._fetch_and_broadcast_progress."""
        return await self._progress._fetch_and_broadcast_progress(tenant_key, job_id, job, execution, progress)

    # ============================================================================
    # Pending Jobs
    # ============================================================================

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

    # ============================================================================
    # Job Completion, Error Reporting, Reactivation
    # ============================================================================

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
            warnings: list[str] = []  # Handover 0710: Soft warnings for orchestrator completion
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
                    job = await self._fetch_job_for_completion(session, job_id, tenant_key)

                    # Validate completion requirements (unread messages and incomplete TODOs)
                    await self._validate_completion_requirements(
                        session, job, execution, tenant_key, job_id, completion_attempt_time
                    )

                    # Update execution and job status
                    old_status, duration_seconds = self._apply_completion_status(execution, result)

                    # Check if this is the last active execution and update job
                    await self._finalize_job_if_last_execution(session, job, execution, tenant_key, job_id)

                    # Handle post-completion side effects (warnings, auto-messages)
                    await self._handle_completion_side_effects(
                        session=session,
                        job=job,
                        execution=execution,
                        result=result,
                        tenant_key=tenant_key,
                        warnings=warnings,
                    )

                    await session.commit()
                else:
                    # No active execution found -- check if decommissioned (Handover 0824)
                    await self._raise_for_missing_execution(session, job_id, tenant_key)

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

    async def _fetch_job_for_completion(self, session: AsyncSession, job_id: str, tenant_key: str) -> "AgentJob":
        """Fetch the AgentJob record for completion, raising if not found."""
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
        return job

    async def _validate_completion_requirements(
        self,
        session: AsyncSession,
        job: "AgentJob",
        execution: "AgentExecution",
        tenant_key: str,
        job_id: str,
        completion_attempt_time: datetime,
    ) -> None:
        """Check unread messages and incomplete TODOs; raise if completion is blocked."""
        unread_query = (
            select(Message)
            .join(MessageRecipient)
            .where(
                and_(
                    Message.tenant_key == tenant_key,
                    Message.project_id == job.project_id,
                    Message.status == "pending",
                    MessageRecipient.agent_id == execution.agent_id,
                )
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

    def _apply_completion_status(
        self, execution: "AgentExecution", result: dict[str, Any]
    ) -> tuple[str | None, float | None]:
        """Update execution fields for completion. Returns (old_status, duration_seconds)."""
        old_status = execution.status
        execution.status = "complete"
        execution.completed_at = datetime.now(timezone.utc)
        execution.progress = 100  # Set to 100% on completion
        # 0497b: Persist completion result
        execution.result = result

        # Calculate duration if started_at exists
        duration_seconds = None
        if execution.started_at and execution.completed_at:
            duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        return old_status, duration_seconds

    async def _finalize_job_if_last_execution(
        self,
        session: AsyncSession,
        job: "AgentJob",
        execution: "AgentExecution",
        tenant_key: str,
        job_id: str,
    ) -> None:
        """Mark job as completed if no other active executions remain."""
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

    async def _raise_for_missing_execution(self, session: AsyncSession, job_id: str, tenant_key: str) -> None:
        """Check if execution was decommissioned and raise appropriate error."""
        decomm_stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "decommissioned",
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        decomm_res = await session.execute(decomm_stmt)
        decommissioned_exec = decomm_res.scalar_one_or_none()

        if decommissioned_exec:
            raise ResourceNotFoundError(
                message=(
                    f"Job {job_id} was decommissioned and cannot transition to 'completed'. "
                    f"This typically happens when close_project_and_update_memory(force=true) "
                    f"was called before complete_job()."
                ),
                context={
                    "job_id": job_id,
                    "method": "complete_job",
                    "execution_status": "decommissioned",
                    "cause": "Project was force-closed before this job called complete_job()",
                },
            )

        raise ResourceNotFoundError(
            message=f"No active execution found for job {job_id}",
            context={"job_id": job_id, "method": "complete_job"},
        )

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

    async def _handle_completion_side_effects(
        self,
        session: Any,
        job: "AgentJob",
        execution: "AgentExecution",
        result: dict[str, Any],
        tenant_key: str,
        warnings: list[str],
    ) -> None:
        """Handle post-completion side effects: memory warnings and auto-messages.

        Handover 0710: Check if orchestrator needs 360 memory reminder.
        0497b: Auto-generate completion message to orchestrator.
        """
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
            skip_staging = project and project.staging_status in ("staging", "staged", "staging_complete")
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
                    from_agent_id=str(execution.agent_id),
                    from_display_name=execution.agent_display_name,
                    auto_generated=True,
                    content=f"COMPLETION REPORT from {execution.agent_display_name}: {summary}",
                    message_type="completion_report",
                    status="pending",
                )
                session.add(auto_message)
                await session.flush()
                session.add(
                    MessageRecipient(
                        message_id=auto_message.id,
                        agent_id=orch_exec.agent_id,
                        tenant_key=tenant_key,
                    )
                )
                # Handover 0821: Single batch UPDATE for completion report counters
                # prevents cross-statement deadlock with concurrent broadcasts
                from src.giljo_mcp.repositories.message_repository import MessageRepository

                _msg_repo = MessageRepository()
                await _msg_repo.batch_update_counters(
                    session=session,
                    tenant_key=tenant_key,
                    sent_increments={execution.agent_id: 1},
                    waiting_increments={orch_exec.agent_id: 1},
                )

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

    async def reactivate_job(
        self, job_id: str, tenant_key: Optional[str] = None, reason: str = ""
    ) -> ReactivationResult:
        """
        Resume work on a completed job after receiving a follow-up message.

        Handover 0827c: Only works when the execution is in 'blocked' status
        (auto-set by 0827b when a message arrives for a completed agent).

        Transitions: execution blocked->working, job completed->active.
        Accumulates prior working duration and increments reactivation counter.

        Args:
            job_id: Job UUID
            tenant_key: Optional tenant key (uses current if not provided)
            reason: Why the agent is reactivating

        Returns:
            ReactivationResult with status, reactivation_count, and instruction

        Raises:
            ResourceNotFoundError: Job not found or execution not in blocked status
            ProjectStateError: Project is already closed out
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "reactivate_job"})
            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "reactivate_job"})

            async with self._get_session() as session:
                # Find execution in blocked status
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status == "blocked",
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message="Job not found or not in blocked status. Only auto-blocked (post-completion) agents can reactivate.",
                        context={"job_id": job_id, "method": "reactivate_job"},
                    )

                # Get job
                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_res.scalar_one_or_none()
                if not job:
                    raise ResourceNotFoundError(
                        message=f"Job {job_id} not found", context={"job_id": job_id, "method": "reactivate_job"}
                    )

                # Check project is not closed out
                if job.project_id:
                    project_res = await session.execute(
                        select(Project).where(Project.id == job.project_id, Project.tenant_key == tenant_key)
                    )
                    project = project_res.scalar_one_or_none()
                    if project and project.status in ("completed", "cancelled"):
                        raise ProjectStateError(
                            message="Cannot reactivate - project is already closed out.",
                            context={"job_id": job_id, "project_status": project.status},
                        )

                # Accumulate prior working duration
                if execution.completed_at and execution.started_at:
                    elapsed = (execution.completed_at - execution.started_at).total_seconds()
                    current_accumulated = execution.accumulated_duration_seconds or 0.0
                    execution.accumulated_duration_seconds = current_accumulated + elapsed

                # Transition execution: blocked -> working
                old_status = execution.status
                execution.status = "working"
                execution.completed_at = None
                execution.started_at = datetime.now(timezone.utc)
                execution.block_reason = None

                # Increment reactivation counter
                reactivation_count = (execution.reactivation_count or 0) + 1
                execution.reactivation_count = reactivation_count

                # Transition job: completed -> active
                if job.status == "completed":
                    job.status = "active"
                    job.completed_at = None

                await session.flush()

                project_id = str(job.project_id) if job.project_id else None

                self._logger.info("Job %s reactivated (#%d): %s", job_id, reactivation_count, reason)

            # Broadcast status change (outside session)
            try:
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data={
                            "job_id": job_id,
                            "project_id": project_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "old_status": old_status,
                            "status": "working",
                            "reactivation_count": reactivation_count,
                        },
                    )
            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                self._logger.warning("[WEBSOCKET] Failed to broadcast reactivation: %s", ws_error)

            return ReactivationResult(
                status="reactivated",
                job_id=job_id,
                reactivation_count=reactivation_count,
                instruction=(
                    "You have been reactivated. Follow these steps:\n"
                    "1. Review the message(s) that triggered reactivation.\n"
                    "2. Call report_progress with todo_append to ADD new steps "
                    "(do NOT replace your existing completed steps).\n"
                    "3. Do the work, reporting progress as normal.\n"
                    "4. Call complete_job() when finished."
                ),
            )
        except (ValidationError, ResourceNotFoundError, ProjectStateError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps unexpected errors in OrchestrationError
            self._logger.exception("Failed to reactivate job")
            raise OrchestrationError(
                message="Failed to reactivate job", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def dismiss_reactivation(
        self, job_id: str, tenant_key: Optional[str] = None, reason: str = ""
    ) -> DismissResult:
        """
        Acknowledge a post-completion message without resuming work.

        Handover 0827c: Returns a blocked (auto-blocked from complete) agent
        back to complete status. Used when the message is informational.

        Args:
            job_id: Job UUID
            tenant_key: Optional tenant key (uses current if not provided)
            reason: Why no action is needed

        Returns:
            DismissResult with status and instruction

        Raises:
            ResourceNotFoundError: Job not found or execution not in blocked status
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "dismiss_reactivation"})
            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "dismiss_reactivation"})

            async with self._get_session() as session:
                # Find execution in blocked status
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status == "blocked",
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message="Job not found or not in blocked status.",
                        context={"job_id": job_id, "method": "dismiss_reactivation"},
                    )

                # Return to complete (restore previous state)
                old_status = execution.status
                execution.status = "complete"
                execution.block_reason = None

                # Restore job status if it was completed before
                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_res.scalar_one_or_none()

                if job and job.status == "active":
                    # Only restore if no other executions are still active
                    other_active_stmt = select(AgentExecution).where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.id != execution.id,
                        AgentExecution.status.not_in(["complete", "decommissioned"]),
                    )
                    other_active_res = await session.execute(other_active_stmt)
                    other_active = other_active_res.scalar_one_or_none()
                    if not other_active:
                        job.status = "completed"

                await session.flush()

                project_id = str(job.project_id) if job and job.project_id else None

                self._logger.info("Job %s reactivation dismissed: %s", job_id, reason)

            # Broadcast status change (outside session)
            try:
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data={
                            "job_id": job_id,
                            "project_id": project_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "old_status": old_status,
                            "status": "complete",
                        },
                    )
            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                self._logger.warning("[WEBSOCKET] Failed to broadcast dismiss: %s", ws_error)

            return DismissResult(
                status="dismissed",
                job_id=job_id,
                instruction="Message acknowledged. No action needed. You remain in complete status.",
            )
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps unexpected errors in OrchestrationError
            self._logger.exception("Failed to dismiss reactivation")
            raise OrchestrationError(
                message="Failed to dismiss reactivation", context={"job_id": job_id, "error": str(e)}
            ) from e

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

            return ErrorReportResult(job_id=job_id, message="Error reported", status="blocked", block_reason=error)
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
                            # Handover 0827d: Reactivation tracking for frontend duration display
                            "accumulated_duration_seconds": execution.accumulated_duration_seconds or 0.0,
                            "reactivation_count": execution.reactivation_count or 0,
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

    @staticmethod
    async def health_check() -> dict[str, Any]:
        """MCP server health check."""
        return {
            "status": "healthy",
            "server": "giljo_mcp",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "message": "GiljoAI MCP server is operational",
        }

    # Succession methods removed (0391/0461/0700d)
    # Session refresh is handled by:
    #   - REST: POST /api/agent-jobs/{job_id}/simple-handover (UI button)
    # Agents cannot self-detect context exhaustion (passive HTTP architecture).
