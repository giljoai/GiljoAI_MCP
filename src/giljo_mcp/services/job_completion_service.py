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
from giljo_mcp.models.tasks import MessageAcknowledgment
from giljo_mcp.models.user_approval import UserApproval
from giljo_mcp.repositories.agent_completion_repository import AgentCompletionRepository
from giljo_mcp.schemas.service_responses import CompleteJobResult
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
            repo = AgentCompletionRepository()
            async with self._get_session() as session:
                execution = await repo.find_active_execution_for_completion(session, tenant_key, job_id)

                if execution:
                    job = await self._fetch_job_for_completion(session, job_id, tenant_key)

                    await self._validate_completion_requirements(
                        session,
                        job,
                        execution,
                        tenant_key,
                        job_id,
                        completion_attempt_time,
                        acknowledge_closeout_todo=acknowledge_closeout_todo,
                        acknowledge_messages_on_complete=acknowledge_messages_on_complete,
                    )

                    old_status, duration_seconds = self._apply_completion_status(execution, result)

                    await self._finalize_job_if_last_execution(session, job, execution, tenant_key, job_id)

                    await self._handle_completion_side_effects(
                        session=session,
                        job=job,
                        execution=execution,
                        result=result,
                        tenant_key=tenant_key,
                        warnings=warnings,
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
            if job and getattr(job, "job_type", "") == "orchestrator":
                try:
                    from giljo_mcp.services.settings_service import SettingsService

                    async with self._get_session() as settings_session:
                        settings_svc = SettingsService(settings_session, tenant_key)
                        git_settings = await settings_svc.get_setting_value(
                            "integrations",
                            "git_integration",
                            {},
                        )
                    git_enabled = git_settings.get("enabled", False)
                    if git_enabled and "commits" not in (result or {}):
                        warnings.append(
                            "Git integration is enabled but no commits were included in the result. "
                            "Run `git status` to check for uncommitted work, then `git add` and `git commit` "
                            "before writing 360 memory."
                        )

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
        self, execution: AgentExecution, result: dict[str, Any]
    ) -> tuple[str | None, float | None]:
        """Update execution fields for completion. Returns (old_status, duration_seconds)."""
        old_status = execution.status
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
    ) -> None:
        """Mark job as completed if no other active executions remain."""
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
