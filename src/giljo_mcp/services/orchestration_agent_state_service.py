# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent state management methods extracted from OrchestrationService.

Handles reactivation, dismissal, agent status transitions, and post-completion
side effects (memory warnings, auto-messages, WebSocket broadcasts).
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    OrchestrationError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import (
    AgentExecution,
    AgentJob,
    Message,
    ProductMemoryEntry,
    Project,
)
from src.giljo_mcp.models.tasks import MessageRecipient
from src.giljo_mcp.schemas.service_responses import (
    DismissResult,
    ErrorReportResult,
    ReactivationResult,
)
from src.giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


class OrchestrationAgentStateService:
    """Handles agent state transitions, reactivation, dismissal, and completion side effects.

    Extracted from OrchestrationService (Handover 0950) to reduce file size.
    All DB queries filter by tenant_key for multi-tenant isolation.
    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    # Handover 0880: Valid statuses for set_agent_status (agent-settable resting/blocked states)
    _AGENT_SETTABLE_STATUSES: ClassVar[set[str]] = {"blocked", "idle", "sleeping"}

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

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

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
                AgentExecution.status.not_in(["complete", "closed", "decommissioned"]),
            )
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

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
                        AgentExecution.status.not_in(["complete", "closed", "decommissioned"]),
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

    async def close_job(self, job_id: str, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """
        Mark a completed job as closed (final orchestrator acceptance). Handover 0435b.

        Transition: complete → closed. Only valid from 'complete' status.
        Closed jobs are terminal — they will not be auto-blocked on incoming messages
        and are not expected to receive further work.

        Args:
            job_id: Job UUID
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with job_id, old_status, new_status

        Raises:
            ValidationError: Invalid input
            ResourceNotFoundError: Job not found or not in 'complete' status
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "close_job"})
            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "close_job"})

            project_id = None
            async with self._get_session() as session:
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status == "complete",
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message="Job not found or not in 'complete' status. Only completed jobs can be closed.",
                        context={"job_id": job_id, "method": "close_job"},
                    )

                execution.status = "closed"

                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_res.scalar_one_or_none()
                project_id = str(job.project_id) if job and job.project_id else None

                await session.flush()
                self._logger.info("Job %s closed (final acceptance)", job_id)

            if self._websocket_manager:
                try:
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data={
                            "job_id": job_id,
                            "project_id": project_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "old_status": "complete",
                            "status": "closed",
                        },
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience
                    self._logger.warning("[WEBSOCKET] Failed to broadcast close: %s", ws_error)

            return {
                "job_id": job_id,
                "old_status": "complete",
                "new_status": "closed",
                "message": "Job closed — final acceptance by orchestrator.",
            }
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary
            self._logger.exception("Failed to close job")
            raise OrchestrationError(message="Failed to close job", context={"job_id": job_id, "error": str(e)}) from e

    async def set_agent_status(
        self,
        job_id: str,
        status: str,
        reason: str = "",
        wake_in_minutes: int | None = None,
        tenant_key: Optional[str] = None,
    ) -> ErrorReportResult:
        """
        Set agent resting or blocked status (Handover 0880: expanded from report_error).

        Handles three agent-settable states:
        - blocked: agent needs human help (shows "Needs Input")
        - idle: agent dispatched work, resting (shows "Monitoring")
        - sleeping: agent will auto-check in N minutes (shows "Sleeping")

        Auto-wake: report_progress() transitions idle/sleeping/blocked → working.

        Args:
            job_id: Job UUID (looks up latest active execution)
            status: Target status — "blocked", "idle", or "sleeping"
            reason: Human-readable reason (displayed in dashboard)
            wake_in_minutes: Sleep interval hint for "sleeping" status
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            ErrorReportResult with status and reason

        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "set_agent_status"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "set_agent_status"})

            if status not in self._AGENT_SETTABLE_STATUSES:
                raise ValidationError(
                    message=f"Invalid status: {status}. Must be one of {sorted(self._AGENT_SETTABLE_STATUSES)}",
                    context={"method": "set_agent_status", "job_id": job_id},
                )

            # For blocked status, reason is required (backward compat with report_error)
            if status == "blocked" and not reason.strip():
                raise ValidationError(
                    message="reason is required for blocked status",
                    context={"method": "set_agent_status", "job_id": job_id},
                )

            # Build block_reason string (stores reason + optional wake metadata)
            block_reason = reason
            if status == "sleeping" and wake_in_minutes:
                block_reason = (
                    f"{reason} | wake_in_minutes={wake_in_minutes}" if reason else f"wake_in_minutes={wake_in_minutes}"
                )

            job = None
            async with self._get_session() as session:
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "closed", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "set_agent_status"},
                    )

                # TENANT ISOLATION: Filter by tenant_key
                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_res.scalar_one_or_none()

                old_status = execution.status
                execution.status = status
                execution.block_reason = block_reason if block_reason else None

                await session.commit()

            # WebSocket broadcast for real-time UI updates
            try:
                if self._websocket_manager:
                    ws_data = {
                        "job_id": job_id,
                        "project_id": str(job.project_id) if job and job.project_id else None,
                        "agent_display_name": execution.agent_display_name,
                        "agent_name": execution.agent_name,
                        "old_status": old_status,
                        "status": status,
                        "block_reason": block_reason,
                    }
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data=ws_data,
                    )
                    self._logger.info(f"[WEBSOCKET] Broadcasted set_agent_status ({status}) for {job_id}")
            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                self._logger.warning(f"[WEBSOCKET] Failed to broadcast set_agent_status: {ws_error}")

            status_labels = {"blocked": "Needs Input", "idle": "Monitoring", "sleeping": "Sleeping"}
            return ErrorReportResult(
                job_id=job_id,
                message=f"Status set to {status_labels.get(status, status)}",
                status=status,
                block_reason=block_reason or reason,
            )
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to set agent status")
            raise OrchestrationError(
                message="Failed to set agent status", context={"job_id": job_id, "error": str(e)}
            ) from e
