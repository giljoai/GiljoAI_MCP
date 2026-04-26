# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
JobCompletionService - Agent job completion orchestration.

Sprint 002e: Extracted from OrchestrationService to reduce god-class size.
Contains complete_job and its 8 helper methods (~330 lines).
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import OrchestrationError, ResourceNotFoundError, ValidationError
from giljo_mcp.models import AgentExecution, AgentJob
from giljo_mcp.repositories.agent_completion_repository import AgentCompletionRepository
from giljo_mcp.schemas.service_responses import CompleteJobResult
from giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService
    from giljo_mcp.services.orchestration_agent_state_service import OrchestrationAgentStateService

logger = logging.getLogger(__name__)


class JobCompletionService:
    """Service for agent job completion orchestration.

    Extracted from OrchestrationService (Sprint 002e).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
        message_service: Optional["MessageService"] = None,
        websocket_manager: Optional[Any] = None,
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
        self, job_id: str, result: dict[str, Any], tenant_key: Optional[str] = None
    ) -> CompleteJobResult:
        """Mark job as complete (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
            result: Job result data dict
            tenant_key: Optional tenant key (uses current if not provided)

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

            completion_attempt_time = datetime.now(timezone.utc)

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
                        session, job, execution, tenant_key, job_id, completion_attempt_time
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

            if execution and job:
                await self._resolve_action_items(result, tenant_key, job)

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
                        general_settings = await settings_svc.get_setting_value(
                            "general",
                            "closeout_mode",
                            "hitl",
                        )
                    git_enabled = git_settings.get("enabled", False)
                    if git_enabled and "commits" not in (result or {}):
                        warnings.append(
                            "Git integration is enabled but no commits were included in the result. "
                            "Run `git status` to check for uncommitted work, then `git add` and `git commit` "
                            "before writing 360 memory."
                        )

                    closeout_mode = general_settings if isinstance(general_settings, str) else "hitl"
                    if closeout_mode not in ("hitl", "autonomous"):
                        closeout_mode = "hitl"

                    # Smart HITL: only require approval when there are actual
                    # deferred findings to review. Clean closeouts proceed
                    # automatically even in HITL mode.
                    has_deferred = bool(
                        (result or {}).get("deferred_findings") or (result or {}).get("action_required_tags")
                    )
                    closeout_checklist = self._build_closeout_checklist(
                        user_approval_required=(closeout_mode == "hitl") and has_deferred,
                    )
                except Exception as _exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to build closeout checklist during job completion",
                        exc_info=True,
                    )
                    # Provide a safe default checklist on failure
                    closeout_checklist = self._build_closeout_checklist(
                        user_approval_required=True,
                    )

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
    ) -> None:
        """Check unread messages and incomplete TODOs; raise if completion is blocked."""
        repo = AgentCompletionRepository()
        all_unread = await repo.get_unread_messages_for_agent(session, tenant_key, job.project_id, execution.agent_id)

        def _is_before_attempt(message) -> bool:
            if not message.created_at:
                return True
            created_at = message.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return created_at <= completion_attempt_time

        unread_messages = [message for message in all_unread if _is_before_attempt(message)]

        incomplete_todos = await repo.get_incomplete_todos(session, tenant_key, job_id)

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
        execution.completed_at = datetime.now(timezone.utc)
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

    async def _resolve_action_items(
        self,
        result: dict[str, Any],
        tenant_key: str,
        job: "AgentJob",
    ) -> None:
        """Auto-resolve action_required tasks when agent reports them resolved.

        BE-5022f: Scans result['resolved_action_items'] for matching tasks
        with category='360' and marks them completed.

        Args:
            result: Job completion result dict
            tenant_key: Tenant key for isolation
            job: The completing job (provides product_id)
        """
        resolved_items = result.get("resolved_action_items")
        if not resolved_items or not isinstance(resolved_items, list):
            return

        product_id = getattr(job, "product_id", None)
        if not product_id:
            return

        product_id_str = str(product_id)

        from giljo_mcp.repositories.task_repository import TaskRepository
        from giljo_mcp.services.task_service import TaskService

        task_repo = TaskRepository()
        task_svc = TaskService(
            db_manager=self.db_manager,
            tenant_manager=self.tenant_manager,
        )

        for item_title in resolved_items:
            if not isinstance(item_title, str) or not item_title.strip():
                continue
            try:
                async with self._get_session() as session:
                    task = await task_repo.find_pending_by_category_and_title(
                        session=session,
                        tenant_key=tenant_key,
                        product_id=product_id_str,
                        category="360",
                        title=item_title.strip(),
                    )
                    if task:
                        task_id_str = str(task.id)
                if task:
                    await task_svc.change_status(task_id_str, "completed")
                    self._logger.info(
                        "Auto-resolved action item task %s: %s",
                        task_id_str,
                        item_title,
                    )
            except Exception as _exc:  # noqa: BLE001
                self._logger.warning(
                    "Failed to auto-resolve action item: %s",
                    item_title,
                    exc_info=True,
                )

    @staticmethod
    def _build_closeout_checklist(*, user_approval_required: bool) -> dict[str, Any]:
        """Build the HITL closeout checklist for orchestrator jobs.

        Returns a dict with instructions for the orchestrator agent to follow
        between complete_job() and close_project_and_update_memory().
        """
        instruction = (
            "If user_approval_required: set status blocked with reason "
            "'Closeout: awaiting user review' and present closure options to user. "
            "Otherwise: proceed with best judgment on tags and follow-ups."
        )
        return {
            "action_required_tags": (
                "Review all agent results for deferred findings. "
                "Write action_required tags via write_360_memory() "
                "BEFORE calling close_project_and_update_memory()."
            ),
            "follow_up_items": ("Create tasks/projects for any deferred work via create_task() or create_project()."),
            "user_approval_required": user_approval_required,
            "instruction": instruction,
        }
