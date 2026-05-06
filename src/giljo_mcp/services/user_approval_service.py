# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Service for the user_approvals primitive (BE-5029 Phase A).

The single validated write path. ``create_pending`` is atomic: it inserts the
user_approvals row, flips the agent's execution status to ``awaiting_user``, and
emits a WebSocket broadcast in the same transaction. If any step fails the
transaction rolls back.

Edition Scope: Both.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.user_approval import UserApproval
from giljo_mcp.repositories.user_approval_repository import UserApprovalRepository
from giljo_mcp.schemas.jsonb_validators import (
    validate_user_approval_context,
    validate_user_approval_options,
)
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


async def build_awaiting_user_blocker(
    session: AsyncSession, execution: AgentExecution, tenant_key: str
) -> dict[str, Any]:
    """Closeout blocker dict for an agent parked on a pending user_approval.

    Returns the standard blocker shape with ``approval_id`` resolved so callers
    can deep-link to ``POST /api/approvals/{id}/decide``.
    """
    stmt = select(UserApproval.id).where(
        UserApproval.tenant_key == tenant_key,
        UserApproval.agent_execution_id == execution.id,
        UserApproval.status == "pending",
    )
    approval_id = (await session.execute(stmt)).scalar_one_or_none()
    return {
        "agent_id": execution.agent_id,
        "agent_name": getattr(execution, "agent_name", None) or execution.agent_display_name,
        "status": "awaiting_user",
        "job_id": execution.job_id,
        "issue_type": "awaiting_user_approval",
        "approval_id": approval_id,
        "suggested_action": f"Resolve approval {approval_id} via POST /api/approvals/{approval_id}/decide.",
    }


class UserApprovalService:
    """Single owning service for user_approvals writes."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        websocket_manager: Any | None = None,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._test_session = test_session
        self._repo = UserApprovalRepository(db_manager)

    def _get_session(self):
        if self._test_session is not None:

            @asynccontextmanager
            async def _wrap():
                yield self._test_session

            return _wrap()
        return self.db_manager.get_session_async()

    async def _resolve_execution(
        self,
        session: AsyncSession,
        *,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution:
        """Resolve the most recent AgentExecution for a job within the tenant."""
        result = await session.execute(
            select(AgentExecution)
            .where(
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.job_id == job_id,
            )
            .order_by(AgentExecution.started_at.desc().nullslast())
            .limit(1)
        )
        execution = result.scalar_one_or_none()
        if execution is None:
            raise ResourceNotFoundError(f"No AgentExecution for job_id={job_id}")
        return execution

    async def _verify_job(
        self,
        session: AsyncSession,
        *,
        tenant_key: str,
        job_id: str,
        project_id: str,
    ) -> None:
        result = await session.execute(
            select(AgentJob).where(
                AgentJob.tenant_key == tenant_key,
                AgentJob.job_id == job_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise ResourceNotFoundError(f"No AgentJob for job_id={job_id}")
        if job.project_id != project_id:
            raise ValidationError(f"job_id={job_id} does not belong to project_id={project_id}")

    async def create_pending(
        self,
        *,
        tenant_key: str,
        job_id: str,
        project_id: str,
        reason: str,
        options: list[dict],
        context: dict | None,
    ) -> UserApproval:
        """Atomically create a pending approval and flip the agent to awaiting_user.

        Single-pending-per-agent invariant: a second pending approval for the same
        execution is rejected with ValidationError (matches ``blocked`` semantics).
        """
        validated_options = validate_user_approval_options(options)
        validated_context = validate_user_approval_context(context)

        async with self._get_session() as session:
            await self._verify_job(
                session,
                tenant_key=tenant_key,
                job_id=job_id,
                project_id=project_id,
            )
            execution = await self._resolve_execution(
                session,
                tenant_key=tenant_key,
                job_id=job_id,
            )

            existing = await self._repo.get_pending_for_agent(
                session,
                tenant_key=tenant_key,
                agent_execution_id=execution.id,
            )
            if existing is not None:
                raise ValidationError(f"Agent execution {execution.id} already has a pending approval ({existing.id})")

            approval = await self._repo.create(
                session,
                tenant_key=tenant_key,
                agent_execution_id=execution.id,
                job_id=job_id,
                project_id=project_id,
                reason=reason,
                options=validated_options,
                context=validated_context,
            )

            old_status = execution.status
            execution.status = "awaiting_user"

            await session.commit()
            await session.refresh(approval)
            await session.refresh(execution)

        await self._broadcast_status_change(
            tenant_key=tenant_key,
            job_id=job_id,
            project_id=project_id,
            execution=execution,
            old_status=old_status,
            approval_id=approval.id,
        )
        return approval

    async def list_pending(
        self,
        *,
        tenant_key: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserApproval], int]:
        """Read-only list of pending approvals scoped to ``tenant_key``.

        Tenant isolation: the repository query filters by ``tenant_key``.
        Cross-tenant rows are unreachable. Returns ``(rows, total_count)``.
        """
        if limit < 1 or limit > 200:
            raise ValidationError(f"limit must be 1..200 (got {limit})")
        if offset < 0:
            raise ValidationError(f"offset must be >= 0 (got {offset})")

        async with self._get_session() as session:
            rows = await self._repo.list_pending_for_tenant(
                session,
                tenant_key=tenant_key,
                limit=limit,
                offset=offset,
            )
            total = await self._repo.count_pending_for_tenant(
                session,
                tenant_key=tenant_key,
            )
        return rows, total

    async def mark_decided(
        self,
        *,
        tenant_key: str,
        approval_id: str,
        option_id: str,
        user_id: str | None,
    ) -> UserApproval:
        """Atomically resolve a pending approval and resume the awaiting agent.

        Single transaction: validates option_id, validates pending status, sets
        ``decided_*`` fields, flips the bound execution from ``awaiting_user``
        back to ``working``, then broadcasts the resume on the existing
        ``agent:status_changed`` channel. Cross-tenant access is rejected as
        ``ResourceNotFoundError`` (do not leak existence).
        """
        async with self._get_session() as session:
            approval = await self._repo.get_by_id(
                session,
                tenant_key=tenant_key,
                approval_id=approval_id,
            )
            if approval is None:
                raise ResourceNotFoundError(f"UserApproval id={approval_id} not found")

            if approval.status != "pending":
                raise ValidationError(f"UserApproval id={approval_id} is not pending (status={approval.status})")

            valid_option_ids = {opt.get("id") for opt in (approval.options or [])}
            if option_id not in valid_option_ids:
                raise ValidationError(
                    f"option_id={option_id!r} not in approval.options (valid: {sorted(valid_option_ids)})"
                )

            decided = await self._repo.mark_decided(
                session,
                tenant_key=tenant_key,
                approval_id=approval_id,
                decided_option_id=option_id,
                decided_by_user_id=user_id,
            )
            if decided is None:
                # Lost race: another caller flipped status between get and update.
                raise ValidationError(f"UserApproval id={approval_id} was modified concurrently; retry")

            execution = await self._resolve_execution(
                session,
                tenant_key=tenant_key,
                job_id=decided.job_id,
            )
            old_status = execution.status
            if old_status == "awaiting_user":
                execution.status = "working"

            await session.commit()
            await session.refresh(decided)
            await session.refresh(execution)

        await self._broadcast_resume(
            tenant_key=tenant_key,
            job_id=decided.job_id,
            project_id=decided.project_id,
            execution=execution,
            old_status=old_status,
            approval_id=decided.id,
            decided_option_id=option_id,
        )
        return decided

    async def _broadcast_resume(
        self,
        *,
        tenant_key: str,
        job_id: str,
        project_id: str,
        execution: AgentExecution,
        old_status: str | None,
        approval_id: str,
        decided_option_id: str,
    ) -> None:
        if not self._websocket_manager:
            return
        try:
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type="agent:status_changed",
                data={
                    "job_id": job_id,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "agent_display_name": execution.agent_display_name,
                    "old_status": old_status,
                    "status": execution.status,
                    "user_approval_id": approval_id,
                    "decided_option_id": decided_option_id,
                },
            )
        except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
            logger.warning(
                "[WEBSOCKET] Failed to broadcast user_approval resume for job=%s: %s",
                job_id,
                ws_error,
            )

    async def _broadcast_status_change(
        self,
        *,
        tenant_key: str,
        job_id: str,
        project_id: str,
        execution: AgentExecution,
        old_status: str | None,
        approval_id: str,
    ) -> None:
        if not self._websocket_manager:
            return
        try:
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type="agent:status_changed",
                data={
                    "job_id": job_id,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "agent_display_name": execution.agent_display_name,
                    "old_status": old_status,
                    "status": "awaiting_user",
                    "user_approval_id": approval_id,
                },
            )
        except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
            logger.warning(
                "[WEBSOCKET] Failed to broadcast user_approval status change for job=%s: %s",
                job_id,
                ws_error,
            )
