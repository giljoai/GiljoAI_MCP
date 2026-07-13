# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
MessageRoutingService - Hub reactivation coupling (BE-9012d).

BE-9012d (bus retirement, phase d): the bus send/broadcast/broadcast_to_project
methods (and their WS message:sent/received emitters) were HARD-REMOVED. This
service now carries only the piece of bus behavior that was relocated onto the
Hub in BE-9012b (D5): the message->lifecycle auto-block/reactivation coupling.

Responsibilities:
- Auto-blocking completed agents on a directed, action-required Hub post
  (``auto_block_for_thread_post``, called by the MCP wrapper + REST adapter
  after a successful ``post_to_thread``)
- The shared underlying auto-block primitive (``_auto_block_completed_recipients``)

CE-0026: staging broadcast directive detection (formerly Layer 5.5) removed.
The end-of-staging signal is now ``complete_job`` — see
``JobCompletionService._handle_staging_end``.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.domain.project_status import IMMUTABLE_PROJECT_STATUSES
from giljo_mcp.repositories.message_repository import MessageRepository
from giljo_mcp.services._session_helpers import optional_tenant_session
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class MessageRoutingService:
    """
    Service carrying the Hub reactivation coupling (BE-9012d).

    Auto-blocks completed agents that receive a directed, action-required
    post on a project-bound Hub thread — the same lifecycle coupling the
    retired bus's ``send_message`` used to drive.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        websocket_manager: Any | None = None,
        test_session: AsyncSession | None = None,
    ):
        """
        Initialize MessageRoutingService.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            websocket_manager: Optional WebSocket manager for real-time event emissions
            test_session: Optional AsyncSession for tests to share the same transaction
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._repo = MessageRepository()

    def _get_session(self, tenant_key: str | None = None):
        """Yield a tenant-scoped DB session, honoring an injected test session (shared helper, BE-8000d)."""
        return optional_tenant_session(self.db_manager, tenant_key, self._test_session)

    async def _auto_block_completed_recipients(
        self,
        session: AsyncSession,
        resolved_to_agents: list[str],
        project: Any,
        sender_display_name: str,
        is_broadcast_fanout: bool,
        requires_action: bool = False,
    ) -> list[str]:
        """Auto-block completed agents that receive a direct message (Handover 0827b).

        Handover 0435d: Only auto-block if requires_action=True. Informational
        messages (requires_action=False) no longer trigger reactivation.

        Returns:
            List of agent_ids that were auto-blocked.
        """
        if is_broadcast_fanout:
            return []

        if not requires_action:
            return []

        # BE-5039 Phase 2b: derive the closed-project gate from the
        # canonical immutable-status set instead of duplicating the
        # tuple. ``IMMUTABLE_PROJECT_STATUSES`` is the str-mixin enum
        # frozenset {COMPLETED, CANCELLED}.
        if project.status in IMMUTABLE_PROJECT_STATUSES:
            return []

        auto_blocked_ids = []
        # BE-3008b: collect the status-change broadcasts and emit them AFTER the
        # commit, fire-and-forget. The old code awaited broadcast_job_status_update
        # inside the loop — i.e. BEFORE the commit below, while the flushed
        # status='blocked' row was lock-held — so a slow WS client convoyed the
        # transaction and a roll-back could leak a phantom 'blocked' event. The
        # broadcast now runs decoupled from the write path once the change is
        # durable.
        pending_broadcasts: list[dict[str, Any]] = []
        for recipient_id in resolved_to_agents:
            recipient_execution = await self._repo.get_execution_by_agent_id(session, project.tenant_key, recipient_id)

            # Handover 0435b: skip 'closed' agents — they are terminal, no auto-block
            if recipient_execution and recipient_execution.status == "complete":
                old_status = recipient_execution.status
                recipient_execution.status = "blocked"
                recipient_execution.block_reason = f"Received message from {sender_display_name} while completed"
                await self._repo.flush(session)

                auto_blocked_ids.append(recipient_id)

                if self._websocket_manager:
                    job_row = await self._repo.get_job_id_and_project_for_execution(
                        session, project.tenant_key, recipient_execution.job_id
                    )
                    pending_broadcasts.append(
                        {
                            "job_id": recipient_execution.job_id,
                            "agent_display_name": recipient_execution.agent_display_name,
                            "tenant_key": project.tenant_key,
                            "old_status": old_status,
                            "new_status": "blocked",
                            "project_id": str(job_row.project_id) if job_row else None,
                        }
                    )

                self._logger.info(
                    f"[AUTO-BLOCK] Agent {recipient_execution.agent_display_name} "
                    f"({recipient_id}) auto-blocked: message from {sender_display_name}"
                )

        if auto_blocked_ids:
            await session.commit()

            # BE-3008b: broadcast only after the block is durable, off the write
            # path. schedule() fire-and-forgets; if unavailable (older manager),
            # fall back to an inline awaited send so behaviour is never lost.
            if self._websocket_manager and pending_broadcasts:
                schedule = getattr(self._websocket_manager, "schedule", None)
                for kwargs in pending_broadcasts:
                    try:
                        coro = self._websocket_manager.broadcast_job_status_update(**kwargs)
                        if callable(schedule):
                            schedule(coro)
                        else:
                            await coro
                    except (RuntimeError, ValueError) as e:
                        self._logger.warning(
                            f"Failed to broadcast auto-block status change for {kwargs.get('job_id')}: {e}"
                        )

        return auto_blocked_ids

    async def auto_block_for_thread_post(
        self,
        *,
        message_id: str,
        to_participant: str | None,
        sender_display_name: str,
        requires_action: bool,
        tenant_key: str | None = None,
    ) -> list[str]:
        """Relocated reactivation coupling for Hub thread posts (BE-9012b, D5).

        The bus's single message->lifecycle coupling
        (``send_message`` -> :meth:`_auto_block_completed_recipients`) now also fires
        on the Hub: after a ``post_to_thread`` commits, the MCP wrapper and REST
        endpoint call this so a **directed, action-required post on a project-bound
        thread** reproduces the auto-block/reactivation (BE-9012d: this is the ONLY
        remaining bus/Hub coupling — the bus itself is retired). HARD RULES (§6 rows
        7/8/16), enforced before delegating to the shared method (reused verbatim ->
        informational-never-blocks + the ``IMMUTABLE_PROJECT_STATUSES`` skip come
        free): informational (``requires_action=False``), broadcast (no explicit
        ``to_participant`` -> must never fan-reactivate every participant), and
        town-square (message carries a NULL ``project_id``) posts are all inert.
        Returns the auto-blocked agent_ids.
        """
        # Row 8 + the broadcast guard: only a directed, action-required post can
        # reactivate a completed agent.
        if not requires_action or not to_participant:
            return []

        tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        if not tenant_key:
            return []

        async with self._get_session(tenant_key) as session:
            project_id = await self._repo.get_message_project_id(session, tenant_key, message_id)
            # Town-square (NULL project) stays side-effect-free (HARD RULE).
            if not project_id:
                return []

            project = await self._repo.get_project(session, tenant_key, project_id)
            if not project:
                return []

            # Reuse the bus auto-block VERBATIM: a single directed recipient, never a
            # broadcast fan-out. Row 16 (IMMUTABLE_PROJECT_STATUSES skip) and row 8
            # (requires_action guard) are enforced inside the shared method. Forward the
            # already-validated ``requires_action`` (guaranteed True by the guard above)
            # rather than a literal, so this delegation is not mistaken for an
            # informational emitter passing requires_action=True (0435d AST audit).
            return await self._auto_block_completed_recipients(
                session,
                [to_participant],
                project,
                sender_display_name,
                is_broadcast_fanout=False,
                requires_action=requires_action,
            )
