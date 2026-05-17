# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
JobCompletionService - Agent job completion orchestration.

Sprint 002e: Extracted from OrchestrationService to reduce god-class size.
Contains complete_job and its 8 helper methods (~330 lines).
"""

import logging
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import OrchestrationError, ResourceNotFoundError, ValidationError
from giljo_mcp.models import AgentExecution, AgentJob
from giljo_mcp.models.projects import Project
from giljo_mcp.models.tasks import MessageAcknowledgment
from giljo_mcp.models.user_approval import UserApproval
from giljo_mcp.repositories.agent_completion_repository import AgentCompletionRepository
from giljo_mcp.schemas.service_responses import CompleteJobResult, StagingDirective
from giljo_mcp.services.project_helpers import mark_staging_complete
from giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService
    from giljo_mcp.services.orchestration_agent_state_service import OrchestrationAgentStateService

logger = logging.getLogger(__name__)


# Narrow regex matching TODO content describing the closeout call itself.
# Used by complete_job(acknowledge_closeout_todo=True) to auto-complete
# self-referential TODOs that would otherwise block the gate.
CLOSEOUT_TODO_PATTERN = re.compile(r"(?i)\b(closeout|complete[_ ]job|close[_ ]project)\b")


class JobCompletionService:
    """Service for agent job completion orchestration.

    Extracted from OrchestrationService (Sprint 002e).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
        message_service: Optional["MessageService"] = None,
        websocket_manager: Any | None = None,
        agent_state_service: Optional["OrchestrationAgentStateService"] = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._message_service = message_service
        self._websocket_manager = websocket_manager
        self._agent_state = agent_state_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, Any],
        tenant_key: str | None = None,
        acknowledge_closeout_todo: bool = False,
        acknowledge_messages_on_complete: bool = False,
    ) -> CompleteJobResult:
        """Mark job as complete (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
            result: Job result data dict
            tenant_key: Optional tenant key (uses current if not provided)
            acknowledge_closeout_todo: If True, auto-complete any incomplete TODOs
                whose content matches the closeout pattern (e.g. "Closeout: ...",
                "complete_job ...", "close_project ..."). Use this from the
                orchestrator closeout call where the closeout TODO IS this call.
                Non-closeout incomplete TODOs still block. Unread-messages gate
                is unaffected.
            acknowledge_messages_on_complete: If True, drain (mark
                ``acknowledged``) all unread messages addressed to this
                execution's agent_id in the project+tenant before evaluating
                the gate. Mirror of ``acknowledge_closeout_todo`` for the
                messages gate. Use this when an agent is stuck in a
                reactivation-on-stale-message loop and needs to close out
                without manually draining its inbox. The TODOs gate is
                independent — this flag does NOT bypass incomplete TODOs.

        Returns:
            CompleteJobResult with success status
        """
        try:
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

            completion_attempt_time = datetime.now(UTC)

            job = None
            execution = None
            old_status = None
            duration_seconds = None
            warnings: list[str] = []
            staging_directive: StagingDirective | None = None
            is_staging_end: bool = False
            repo = AgentCompletionRepository()
            async with self._get_session() as session:
                execution = await repo.find_active_execution_for_completion(session, tenant_key, job_id)

                if execution:
                    job = await self._fetch_job_for_completion(session, job_id, tenant_key)

                    # CE-0032: detect staging-end BEFORE validation so the
                    # TODOs-bypass key can read project flags. The detector
                    # loads the project and returns it for downstream reuse,
                    # avoiding a second query.
                    is_staging_end, staging_end_project = await self._is_staging_end_orchestrator_call(
                        session, job, execution, tenant_key
                    )

                    await self._validate_completion_requirements(
                        session,
                        job,
                        execution,
                        tenant_key,
                        job_id,
                        completion_attempt_time,
                        acknowledge_closeout_todo=acknowledge_closeout_todo,
                        acknowledge_messages_on_complete=acknowledge_messages_on_complete,
                        project=staging_end_project,
                    )

                    old_status, duration_seconds = self._apply_completion_status(
                        execution, result, is_staging_end=is_staging_end
                    )

                    await self._finalize_job_if_last_execution(
                        session, job, execution, tenant_key, job_id, is_staging_end=is_staging_end
                    )

                    await self._handle_completion_side_effects(
                        session=session,
                        job=job,
                        execution=execution,
                        result=result,
                        tenant_key=tenant_key,
                        warnings=warnings,
                    )

                    # CE-0026 / CE-0032: state-machine branch for staging-phase
                    # orchestrator. Flips project.staging_status (idempotent)
                    # and returns a STOP directive. CE-0032 removed the
                    # CE-0029 Item 2 pre-spawn — the same orch exec stays
                    # alive in status='waiting' until the user pastes the
                    # impl prompt.
                    staging_directive = await self._handle_staging_end(
                        session,
                        job,
                        execution,
                        tenant_key,
                        is_staging_end=is_staging_end,
                        project=staging_end_project,
                    )

                    await repo.commit(session)
                else:
                    await self._raise_for_missing_execution(session, job_id, tenant_key)

            if execution:
                await self._broadcast_completion(tenant_key, job_id, job, execution, old_status, duration_seconds)

            if execution and job and result and "resolved_action_items" in result:
                # INF-5025b: warn-and-ignore for one release. Cutover deferred to BE-5054
                # (after 2026-06-05) -- not removed in INF-5025d; only the prose was finalized then.
                self._logger.warning(
                    "resolved_action_items is deprecated; cite task/project IDs in decisions_made instead"
                )

            closeout_checklist = None
            # CE-0027 / CE-0032: closeout_checklist (request_approval, deferred
            # findings) is implementation-phase closeout guidance. Skip it for
            # staging-end orchestrator calls — they get the staging_directive
            # instead. Under CE-0032's single-exec model the prior key on
            # execution.project_phase no longer disambiguates phases (every
            # orch exec has project_phase='staging'); is_staging_end (derived
            # from project flags) is the authoritative phase signal.
            is_impl_phase_orch = job and getattr(job, "job_type", "") == "orchestrator" and not is_staging_end
            if is_impl_phase_orch:
                # INF-5076: orchestrators are coordinators, not committers — commits
                # flow through close_project_and_update_memory(git_commits=[...])
                # on the next call, not through complete_job's result. The previous
                # git-commits warning here fired on every correctly-structured
                # closeout. Agents that actually commit (implementer, tester) are
                # not orchestrators and never reached this branch, so removing the
                # warning loses no coverage.
                try:
                    closeout_checklist = self._build_closeout_checklist()
                except Exception as _exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to build closeout checklist during job completion",
                        exc_info=True,
                    )
                    closeout_checklist = self._build_closeout_checklist()

            return CompleteJobResult(
                status="success",
                job_id=job_id,
                message="Job completed successfully",
                warnings=warnings,
                result_stored=True,
                closeout_checklist=closeout_checklist,
                staging_directive=staging_directive,
            )
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            self._logger.exception("Failed to complete job")
            raise OrchestrationError(
                message="Failed to complete job", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def _fetch_job_for_completion(self, session: AsyncSession, job_id: str, tenant_key: str) -> AgentJob:
        """Fetch the AgentJob record for completion, raising if not found."""
        repo = AgentCompletionRepository()
        job = await repo.get_agent_job_by_job_id(session, tenant_key, job_id)
        if not job:
            raise ResourceNotFoundError(
                message=f"Job {job_id} not found", context={"job_id": job_id, "method": "complete_job"}
            )
        return job

    async def _check_360_memory_written(self, session: AsyncSession, job: AgentJob, tenant_key: str) -> bool:
        """Check if a 360 memory entry exists for the project (Handover 0435d)."""
        if not job.project_id:
            return True
        repo = AgentCompletionRepository()
        return await repo.check_360_memory_for_project(session, tenant_key, job.project_id)

    async def _validate_completion_requirements(
        self,
        session: AsyncSession,
        job: AgentJob,
        execution: AgentExecution,
        tenant_key: str,
        job_id: str,
        completion_attempt_time: datetime,
        acknowledge_closeout_todo: bool = False,
        acknowledge_messages_on_complete: bool = False,
        project: Project | None = None,
    ) -> None:
        """Check unread messages and incomplete TODOs; raise if completion is blocked.

        When ``acknowledge_closeout_todo`` is True, any incomplete TODOs whose
        ``content`` matches :data:`CLOSEOUT_TODO_PATTERN` are auto-completed in
        place before the gate evaluates. Non-closeout incomplete TODOs still
        block.

        When ``acknowledge_messages_on_complete`` is True, all unread messages
        addressed to this execution's ``agent_id`` (filtered by tenant_key and
        project_id) are marked ``status='acknowledged'`` before the gate
        evaluates. The TODOs gate is unaffected by this flag.

        The two flags are independent: each drains its own gate. Combining them
        is conjunctive (both gates use their own flag).
        """
        # BE-5059 Phase B: refuse completion when this execution is parked on a
        # pending user_approval. The TODOs/messages gates do not catch this --
        # an agent in awaiting_user has by definition deferred a decision to the
        # human and cannot self-complete.
        if execution.status == "awaiting_user":
            pending_stmt = select(UserApproval).where(
                UserApproval.tenant_key == tenant_key,
                UserApproval.agent_execution_id == execution.id,
                UserApproval.status == "pending",
            )
            pending_approval = (await session.execute(pending_stmt)).scalar_one_or_none()
            approval_id = pending_approval.id if pending_approval is not None else None
            raise ValidationError(
                message=(
                    "COMPLETION_BLOCKED: Agent is awaiting user approval. "
                    "Resolve via POST /api/approvals/{id}/decide before calling complete_job()."
                ),
                error_code="AWAITING_USER_APPROVAL",
                context={
                    "job_id": job_id,
                    "approval_id": approval_id,
                    "agent_status": "awaiting_user",
                    "reasons": [
                        "Agent has a pending user_approval; user must decide before completion is allowed.",
                    ],
                },
            )

        repo = AgentCompletionRepository()
        all_unread = await repo.get_unread_messages_for_agent(session, tenant_key, job.project_id, execution.agent_id)

        def _is_before_attempt(message) -> bool:
            if not message.created_at:
                return True
            created_at = message.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            return created_at <= completion_attempt_time

        unread_messages = [message for message in all_unread if _is_before_attempt(message)]

        if acknowledge_messages_on_complete and unread_messages:
            now = datetime.now(UTC)
            for msg in unread_messages:
                msg.status = "acknowledged"
                msg.acknowledged_at = now
                # Junction-table insert for audit trail (Handover 0840b pattern,
                # mirrors message_service._process_received_messages).
                ack_stmt = (
                    pg_insert(MessageAcknowledgment)
                    .values(
                        message_id=str(msg.id),
                        agent_id=execution.agent_id,
                        tenant_key=tenant_key,
                    )
                    .on_conflict_do_nothing(constraint="uq_msg_ack")
                )
                await session.execute(ack_stmt)
            await session.flush()
            self._logger.info(
                "Auto-acknowledged %d unread message(s) on acknowledged complete_job for job %s (agent %s)",
                len(unread_messages),
                job_id,
                execution.agent_id,
            )
            unread_messages = []

        incomplete_todos = await repo.get_incomplete_todos(session, tenant_key, job_id)

        # CE-0027 / CE-0032: Staging-phase orchestrator TODOs ARE the
        # deliverable plan for downstream implementer/tester agents. The
        # orchestrator writes them during staging precisely BECAUSE they are
        # not yet done; the plan is what survives into implementation.
        # Blocking the staging-end complete_job on these would force the
        # agent to lie about completion status to get past the gate (the
        # dogfood Paddle test). Skip the TODOs gate entirely for staging-
        # phase orchestrators. The unread-messages gate still applies —
        # orchestrators should not abandon their inbox at staging-end.
        #
        # CE-0032 re-keyed the bypass off the vestigial execution.project_phase
        # column onto project flags. Truth table (project|impl_launched_at):
        #   ('staging'|None) → staging-end (fires; TODOs survive into impl)
        #   ('staged'|None)  → defensive; pre-orch-start (fires; no TODOs anyway)
        #   ('staging_complete'|None) → defensive re-call after auto-flip (fires)
        #   ('staging_complete'|<ts>) → impl-end (does NOT fire; TODOs must be done)
        # The restage path (project_staging_service) clears impl_launched_at
        # so restage-after-completion lands back in the staging-end branch.
        is_staging_orchestrator = (
            job.job_type == "orchestrator"
            and project is not None
            and project.staging_status in ("staging", "staged", "staging_complete")
            and project.implementation_launched_at is None
        )
        if is_staging_orchestrator and incomplete_todos:
            self._logger.info(
                "[STAGING] Bypassing incomplete-TODOs gate for staging-phase orchestrator "
                "(%d deliverable TODOs survive into implementation)",
                len(incomplete_todos),
                extra={"job_id": job_id, "tenant_key": tenant_key},
            )
            incomplete_todos = []

        if acknowledge_closeout_todo and incomplete_todos:
            closeout_todos = [t for t in incomplete_todos if CLOSEOUT_TODO_PATTERN.search(t.content or "")]
            remainder = [t for t in incomplete_todos if t not in closeout_todos]
            if closeout_todos:
                now = datetime.now(UTC)
                for todo in closeout_todos:
                    todo.status = "completed"
                    todo.updated_at = now
                await session.flush()
                self._logger.info(
                    "Auto-completed %d closeout TODO(s) on acknowledged complete_job for job %s",
                    len(closeout_todos),
                    job_id,
                )
            incomplete_todos = remainder

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
        self,
        execution: AgentExecution,
        result: dict[str, Any],
        *,
        is_staging_end: bool = False,
    ) -> tuple[str | None, float | None]:
        """Update execution fields for completion. Returns (old_status, duration_seconds).

        CE-0032: when ``is_staging_end`` is True, the orchestrator entity is
        pausing between staging and implementation — not ending. Set
        ``status='waiting'`` (NOT 'complete'), leave ``completed_at`` unset,
        and preserve the prior ``progress`` so the dashboard doesn't lie about
        a session-end. The same ``AgentExecution`` row will transition back to
        'working' on the next ``get_agent_mission`` call when the user pastes
        the implementation prompt (existing logic in mission_service.py:174).
        ``result`` is still stored for audit trail.
        """
        old_status = execution.status

        if is_staging_end:
            execution.status = "waiting"
            execution.result = result
            execution.completed_at = None
            return old_status, None

        execution.status = "complete"
        execution.completed_at = datetime.now(UTC)
        execution.progress = 100
        execution.result = result

        duration_seconds = None
        if execution.started_at and execution.completed_at:
            duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        return old_status, duration_seconds

    async def _finalize_job_if_last_execution(
        self,
        session: AsyncSession,
        job: AgentJob,
        execution: AgentExecution,
        tenant_key: str,
        job_id: str,
        *,
        is_staging_end: bool = False,
    ) -> None:
        """Mark job as completed if no other active executions remain.

        CE-0028: when this complete_job call is the staging→implementation
        transition for the orchestrator, preserve ``job.status='active'``.
        The same AgentJob carries the orchestrator across both phases; the
        implementation-phase execution attaches to this row and the job's
        completion only fires when the implementation session closes. Flipping
        the job to 'completed' at staging-end made the UI treat the project
        as fully done (closeout modal + 360-memory poll), blocking the
        Implement (play) button flow.
        """
        if is_staging_end:
            return

        repo = AgentCompletionRepository()
        other_active = await repo.find_other_active_executions_by_agent_id(
            session, tenant_key, job_id, execution.agent_id
        )

        if not other_active:
            job.status = "completed"
            job.completed_at = execution.completed_at

    async def _raise_for_missing_execution(self, session: AsyncSession, job_id: str, tenant_key: str) -> None:
        """Check if execution was decommissioned and raise appropriate error."""
        repo = AgentCompletionRepository()
        decommissioned_exec = await repo.find_decommissioned_execution(session, tenant_key, job_id)

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

    async def _broadcast_completion(self, tenant_key, job_id, job, execution, old_status, duration_seconds):
        """Delegate to OrchestrationAgentStateService for broadcast."""
        if self._agent_state:
            await self._agent_state._broadcast_completion(
                tenant_key, job_id, job, execution, old_status, duration_seconds
            )

    async def _handle_completion_side_effects(self, session, job, execution, result, tenant_key, warnings):
        """Delegate to OrchestrationAgentStateService for side effects."""
        if self._agent_state:
            await self._agent_state._handle_completion_side_effects(
                session, job, execution, result, tenant_key, warnings
            )

    async def _is_staging_end_orchestrator_call(
        self,
        session: AsyncSession,
        job: AgentJob,
        execution: AgentExecution,
        tenant_key: str,
    ) -> tuple[bool, Project | None]:
        """Detect whether this complete_job is the staging→implementation
        transition for an orchestrator. Single source of truth for CE-0026
        (STOP directive) and CE-0028 (preserve job.status='active').

        Returns ``(is_staging_end, project)``. When ``is_staging_end`` is True,
        callers must:
          * preserve ``job.status='active'`` (do NOT flip to 'completed'); and
          * emit a STOP ``staging_directive`` in the response.

        The Project (possibly None) is returned so callers can reuse it
        without a second lookup. A None project on a staging-end call is
        anomalous — ``_handle_staging_end`` logs a warning but still returns
        the directive.

        Args:
            session: Active session.
            job: AgentJob being completed.
            execution: AgentExecution being marked complete.
            tenant_key: Tenant key for isolation.
        """
        if job.job_type != "orchestrator":
            return False, None
        if getattr(execution, "project_phase", None) != "staging":
            return False, None
        if not job.project_id:
            return False, None

        stmt = select(Project).where(
            Project.id == str(job.project_id),
            Project.tenant_key == tenant_key,
        )
        project = (await session.execute(stmt)).scalar_one_or_none()
        # CE-0026 safeguard: if implementation has already been launched, this
        # complete_job is NOT a staging-end signal — it's the staging-phase
        # execution catching up (orch stayed alive across the
        # staging→implementation transition without complete_job being called
        # at the right boundary). Treat as a normal closeout; no STOP directive.
        if project is not None and project.implementation_launched_at is not None:
            return False, project
        return True, project

    async def _handle_staging_end(
        self,
        session: AsyncSession,
        job: AgentJob,
        execution: AgentExecution,
        tenant_key: str,
        *,
        is_staging_end: bool,
        project: Project | None,
    ) -> StagingDirective | None:
        """Flip the staging flag and return the STOP directive (CE-0026).

        Detection is performed once by ``_is_staging_end_orchestrator_call``
        and the result is passed in. This method only mutates and shapes the
        response. Calls the canonical ``mark_staging_complete`` helper
        (idempotent — ``mission_service`` may already have flipped the flag
        earlier in this session).

        Args:
            session: Active session (will be committed by caller).
            job: AgentJob being completed.
            execution: AgentExecution being marked complete.
            tenant_key: Tenant key for isolation.
            is_staging_end: Output of ``_is_staging_end_orchestrator_call``.
            project: Project loaded by the detector (may be None on the
                anomalous staging-end-without-project case).

        Returns:
            StagingDirective when ``is_staging_end`` is True; otherwise None.
        """
        if not is_staging_end:
            return None

        if project is None:
            self._logger.warning(
                "[STAGING_END] Project %s not found for staging orchestrator job %s — "
                "skipping flag flip but still returning STOP directive",
                job.project_id,
                job.job_id,
            )
            return StagingDirective()

        await mark_staging_complete(
            session,
            project,
            source="complete_job:staging_end",
            websocket_manager=self._websocket_manager,
        )

        # CE-0032: no pre-spawn. Under the single-orchestrator-entity model
        # the same AgentExecution row carries the orchestrator across the
        # staging→implementation boundary; _apply_completion_status (called
        # earlier in this complete_job) left it at status='waiting'. The
        # Implement-click endpoint sets project.implementation_launched_at and
        # broadcasts; the user pastes the impl prompt; the orch's first
        # get_agent_mission call flips this row's status back to 'working'.
        return StagingDirective()

    # _resolve_action_items removed in INF-5025b

    @staticmethod
    def _build_closeout_checklist() -> dict[str, Any]:
        """Build the closeout checklist for orchestrator jobs.

        Returns instructions for the orchestrator to follow between
        ``complete_job()`` and ``close_project_and_update_memory()``. When the
        orchestrator needs user input on deferred findings it must call
        ``mcp__giljo_mcp__request_approval`` -- see CH4 for the tool reference.
        The agent's status is flipped to ``awaiting_user`` automatically and
        ``complete_job`` will refuse until the user decides via
        ``POST /api/approvals/{id}/decide``.
        """
        return {
            "follow_up_items": ("Create tasks/projects for any deferred work via create_task() or create_project()."),
            "instruction": (
                "When the closeout has deferred findings to review, call "
                "request_approval(...) -- your status will be flipped to "
                "awaiting_user automatically; complete_job will refuse until "
                "the user decides."
            ),
        }
