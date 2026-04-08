# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProgressService - Agent job progress reporting.

Extracted from OrchestrationService (Handover 0769) as part of the facade pattern
refactoring to keep individual modules under 1000 lines.

Responsibilities:
- Progress reporting (report_progress)
- TODO item management (todo_items, todo_append)
- WebSocket broadcast for progress updates
- Missing TODO warning throttling
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    OrchestrationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import (
    AgentExecution,
    AgentJob,
    AgentTodoItem,
)
from src.giljo_mcp.schemas.service_responses import ProgressResult
from src.giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


class ProgressService:
    """
    Service for agent job progress reporting.

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
        # Handover 0406: Track todo_items warning timestamps (throttle 1 per 5 min per job)
        self._todo_warning_timestamps: dict[str, datetime] = {}

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

    async def report_progress(
        self,
        job_id: str,
        progress: dict[str, Any] | None = None,
        tenant_key: Optional[str] = None,
        todo_items: list[dict] | None = None,
        todo_append: list[dict] | None = None,
    ) -> ProgressResult:
        """
        Report job progress (store message in message queue).

        Args:
            job_id: Job UUID
            progress: Progress data dict (legacy format, optional)
            tenant_key: Optional tenant key (uses current if not provided)
            todo_items: Simplified TODO items array (Handover 0392)
                        [{"content": "Task A", "status": "completed"}, ...]
            todo_append: Steps to APPEND to existing TODO list (Handover 0827d).
                         Preserves existing completed steps, adds new ones.

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

            # Handover 0827d: todo_append is mutually exclusive with todo_items
            if todo_append is not None and todo_items is not None:
                raise ValidationError(
                    message="Cannot use both todo_items and todo_append in the same call",
                    context={"method": "report_progress"},
                )

            # Derive progress dict from todo_items/todo_append or validate raw progress
            progress, todo_items = self._derive_progress_dict(progress, todo_items, todo_append)

            # Fetch execution and job info for progress tracking
            job = None
            execution = None
            blocked_to_working = False
            async with self._get_session() as session:
                execution = await self._fetch_active_execution(session, job_id, tenant_key)
                job = await self._fetch_job(session, job_id, tenant_key)

                # Update execution progress fields
                execution.last_progress_at = datetime.now(timezone.utc)

                # Auto-wake transition: if an agent reports progress while in a
                # resting state (blocked/idle/sleeping), resume "working" status.
                # Handover 0880: extended from blocked-only to all resting states.
                old_resting_status = None
                if execution.status in ("blocked", "idle", "sleeping"):
                    old_resting_status = execution.status
                    execution.status = "working"
                    execution.block_reason = None
                    blocked_to_working = True

                    self._logger.info(
                        "Agent resumed from %s: agent_id=%s, job_id=%s",
                        old_resting_status,
                        execution.agent_id,
                        job_id,
                    )

                # Extract progress percentage and current task from progress dict
                if "percent" in progress:
                    execution.progress = min(100, max(0, int(progress["percent"])))
                if "message" in progress or "current_step" in progress:
                    execution.current_task = progress.get("message") or progress.get("current_step")

                # Process TODO items (replace or append strategies)
                await self._process_todo_items(session, job, job_id, tenant_key, progress, todo_append)

                await session.commit()
                await session.refresh(execution)
                await session.refresh(job)

            if not job:
                raise ResourceNotFoundError(
                    message=f"Job {job_id} not found after commit",
                    context={"job_id": job_id, "method": "report_progress"},
                )

            # Broadcast updates and build warnings
            return await self._broadcast_progress_update(
                tenant_key,
                job_id,
                job,
                execution,
                progress,
                blocked_to_working,
                old_resting_status=old_resting_status,
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

    def _derive_progress_dict(
        self,
        progress: dict[str, Any] | None,
        todo_items: list[dict] | None,
        todo_append: list[dict] | None,
    ) -> tuple[dict[str, Any], list[dict] | None]:
        """Derive a normalised progress dict from the various input formats.

        Returns:
            Tuple of (progress_dict, todo_items).
        """
        # Handover 0392: Support top-level todo_items parameter (simplified format)
        if todo_items is not None:
            if not isinstance(todo_items, list):
                raise ValidationError(
                    message="todo_items must be a list",
                    context={"method": "report_progress", "todo_items_type": type(todo_items).__name__},
                )

            completed_steps = len([t for t in todo_items if t.get("status") == "completed"])
            total_steps = len(todo_items)
            in_progress_items = [t for t in todo_items if t.get("status") == "in_progress"]
            current_step = in_progress_items[0].get("content") if in_progress_items else None
            percent = (completed_steps / total_steps * 100) if total_steps > 0 else 0

            progress = {
                "mode": "todo",
                "percent": percent,
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "current_step": current_step,
                "todo_items": todo_items,
            }
        elif todo_append is not None:
            # Handover 0827d: todo_append can be called standalone
            if not isinstance(todo_append, list):
                raise ValidationError(
                    message="todo_append must be a list",
                    context={"method": "report_progress", "todo_append_type": type(todo_append).__name__},
                )
            progress = {"mode": "append"}
        elif progress is None:
            raise ValidationError(
                message="Either progress, todo_items, or todo_append must be provided",
                context={"method": "report_progress"},
            )
        elif not isinstance(progress, dict):
            raise ValidationError(
                message="progress must be a dict",
                context={"method": "report_progress", "progress_type": type(progress).__name__},
            )

        # Extract todo_items from progress dict if not already set (backwards compatibility)
        if todo_items is None and "todo_items" in progress:
            todo_items = progress.get("todo_items")

        return progress, todo_items

    async def _fetch_active_execution(
        self,
        session: AsyncSession,
        job_id: str,
        tenant_key: str,
    ) -> AgentExecution:
        """Fetch the latest active execution for a job, raising on not-found."""
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
            # Check if decommissioned for better diagnostics (Handover 0824)
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
                        f"Job {job_id} was decommissioned and cannot report progress. "
                        f"This typically happens when close_project_and_update_memory(force=true) "
                        f"was called before complete_job()."
                    ),
                    context={
                        "job_id": job_id,
                        "method": "report_progress",
                        "execution_status": "decommissioned",
                        "cause": "Project was force-closed before this job called complete_job()",
                    },
                )

            raise ResourceNotFoundError(
                message=f"No active execution found for job {job_id}",
                context={"job_id": job_id, "method": "report_progress"},
            )

        return execution

    async def _fetch_job(
        self,
        session: AsyncSession,
        job_id: str,
        tenant_key: str,
    ) -> AgentJob:
        """Fetch the job record, raising on not-found."""
        # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
        job_res = await session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
        )
        job = job_res.scalar_one_or_none()

        if not job:
            raise ResourceNotFoundError(
                message=f"Job {job_id} not found", context={"job_id": job_id, "method": "report_progress"}
            )
        return job

    async def _process_todo_items(
        self,
        session: AsyncSession,
        job: AgentJob,
        job_id: str,
        tenant_key: str,
        progress: dict[str, Any],
        todo_append: list[dict] | None,
    ) -> None:
        """Persist TODO-style steps tracking data (replace or append strategies)."""
        # Optional TODO-style steps tracking for Steps column (Handover 0297)
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
        todo_items = progress.get("todo_items")
        if isinstance(todo_items, list) and len(todo_items) > 0:
            from sqlalchemy import delete as sql_delete

            # Delete existing items for this job (replace strategy)
            # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
            await session.execute(
                sql_delete(AgentTodoItem).where(AgentTodoItem.job_id == job_id, AgentTodoItem.tenant_key == tenant_key)
            )

            # Insert new items with sequence
            for seq, item in enumerate(todo_items):
                if isinstance(item, dict) and item.get("content"):
                    status = item.get("status", "pending")
                    if status not in ("pending", "in_progress", "completed", "skipped"):
                        status = "pending"

                    todo_item = AgentTodoItem(
                        job_id=job_id,
                        tenant_key=tenant_key,
                        content=str(item["content"])[:255],
                        status=status,
                        sequence=seq,
                    )
                    session.add(todo_item)

        # Handover 0827d: Append new items without deleting existing ones
        if isinstance(todo_append, list) and len(todo_append) > 0:
            await self._append_todo_items(session, job, job_id, tenant_key, todo_append)

    async def _append_todo_items(
        self,
        session: AsyncSession,
        job: AgentJob,
        job_id: str,
        tenant_key: str,
        todo_append: list[dict],
    ) -> None:
        """Append new TODO items after existing ones and recount totals."""
        from sqlalchemy import func as sa_func

        # Find current max sequence number
        max_seq_result = await session.execute(
            select(sa_func.max(AgentTodoItem.sequence))
            .where(AgentTodoItem.job_id == job_id)
            .where(AgentTodoItem.tenant_key == tenant_key)
        )
        max_seq = max_seq_result.scalar() or -1

        # Insert only new items after existing ones
        appended_count = 0
        for i, item in enumerate(todo_append):
            if isinstance(item, dict) and item.get("content"):
                status = item.get("status", "pending")
                if status not in ("pending", "in_progress", "completed", "skipped"):
                    status = "pending"

                todo_item = AgentTodoItem(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    content=str(item["content"])[:255],
                    status=status,
                    sequence=max_seq + 1 + i,
                )
                session.add(todo_item)
                appended_count += 1

        # Recount totals and update JSONB summary
        if appended_count > 0:
            from sqlalchemy.orm.attributes import flag_modified

            await session.flush()

            total_result = await session.execute(
                select(sa_func.count(AgentTodoItem.id))
                .where(AgentTodoItem.job_id == job_id)
                .where(AgentTodoItem.tenant_key == tenant_key)
            )
            completed_result = await session.execute(
                select(sa_func.count(AgentTodoItem.id))
                .where(AgentTodoItem.job_id == job_id)
                .where(AgentTodoItem.tenant_key == tenant_key)
                .where(AgentTodoItem.status == "completed")
            )
            skipped_result = await session.execute(
                select(sa_func.count(AgentTodoItem.id))
                .where(AgentTodoItem.job_id == job_id)
                .where(AgentTodoItem.tenant_key == tenant_key)
                .where(AgentTodoItem.status == "skipped")
            )

            total_count = total_result.scalar()
            completed_count = completed_result.scalar()
            skipped_count = skipped_result.scalar()

            metadata = job.job_metadata or {}
            metadata["todo_steps"] = {
                "total_steps": total_count,
                "completed_steps": completed_count,
                "skipped_steps": skipped_count,
            }
            job.job_metadata = metadata
            flag_modified(job, "job_metadata")

    async def _broadcast_progress_update(
        self,
        tenant_key: str,
        job_id: str,
        job: AgentJob,
        execution: AgentExecution,
        progress: dict[str, Any],
        blocked_to_working: bool,
        old_resting_status: str | None = None,
    ) -> ProgressResult:
        """Broadcast WebSocket events and return the progress result with warnings."""
        # Broadcast resting->working AFTER commit succeeds (not before)
        if blocked_to_working and self._websocket_manager:
            try:
                await self._websocket_manager.broadcast_to_tenant(
                    tenant_key=tenant_key,
                    event_type="agent:status_changed",
                    data={
                        "job_id": str(job_id),
                        "agent_display_name": execution.agent_display_name or "unknown",
                        "old_status": old_resting_status or "blocked",
                        "status": "working",
                        "project_id": str(job.project_id),
                    },
                )
            except Exception:  # Broad catch: WebSocket resilience, non-critical broadcast
                self._logger.exception(
                    "Failed to broadcast %s->working for agent %s",
                    old_resting_status or "blocked",
                    execution.agent_id,
                )

        await self._fetch_and_broadcast_progress(tenant_key, job_id, job, execution, progress)

        # Handover 0406: Reactive warning for missing todo_items
        warnings: list[str] = []
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
