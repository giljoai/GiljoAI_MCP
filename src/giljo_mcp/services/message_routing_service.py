# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MessageRoutingService - Message routing, recipient resolution, and broadcast fanout.

Extracted from MessageService (Handover 0950h) to separate routing/coordination
concerns from CRUD/acknowledgment operations.

Responsibilities:
- Sending messages with recipient resolution
- Broadcasting to multiple agents
- Recipient resolution (display name to agent_id)
- Auto-blocking completed recipients on direct message
- WebSocket event emission for sent/received messages
- Staging broadcast directive detection

For message retrieval, acknowledgment, and status, see MessageService.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    MessageDeliveryError,
    ResourceNotFoundError,
    RetryExhaustedError,
    ValidationError,
)
from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.tasks import MessageRecipient
from src.giljo_mcp.repositories.message_repository import MessageRepository
from src.giljo_mcp.schemas.service_responses import (
    BroadcastResult,
    SendMessageResult,
    StagingDirective,
)
from src.giljo_mcp.services.dto import BroadcastMessageContext
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.utils.db_retry import with_deadlock_retry


logger = logging.getLogger(__name__)


class MessageRoutingService:
    """
    Service for message routing, broadcasting, and recipient resolution.

    Handles the send-side of inter-agent messaging:
    - Sending messages to one or more agents
    - Broadcasting to all agents in a project
    - Resolving agent display names to execution IDs
    - Auto-blocking completed agents on direct message receipt
    - Emitting WebSocket events for real-time UI updates

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        websocket_manager: Optional[Any] = None,
        test_session: Optional[AsyncSession] = None,
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

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    # ============================================================================
    # Message Sending
    # ============================================================================

    async def send_message(
        self,
        to_agents: list[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
        from_agent: Optional[str] = None,
        tenant_key: Optional[str] = None,
        requires_action: bool = False,
    ) -> SendMessageResult:
        """
        Send a message to one or more agents.

        Handover 0372: Routes by agent_id (executor) instead of job_id (work order).

        Args:
            to_agents: List of agent names to send to
            content: Message content
            project_id: Project ID this message belongs to
            message_type: Type of message (default: "direct")
            priority: Message priority (default: "normal")
            from_agent: Sender agent name (default: "orchestrator")
            tenant_key: Tenant key for multi-tenant isolation (required for security)

        Returns:
            SendMessageResult with message_id, to_agents, message_type,
            and optional staging_directive
        """
        try:
            async with self._get_session() as session:
                tenant_key, project = await self._validate_send_message_inputs(session, tenant_key, project_id)

                # Handover 0410: Detect broadcast intent before fan-out resolution
                is_broadcast_fanout = "all" in to_agents

                resolved_to_agents = await self._resolve_message_recipients(
                    session, to_agents, project_id, tenant_key, from_agent
                )

                # Sort recipients for deterministic lock ordering (prevents deadlocks)
                resolved_to_agents.sort()

                # Resolve sender display name for message enrichment (Handover 0827a)
                sender_display_name = await self._resolve_sender_display_name(session, from_agent, project)

                messages, message_id = await self._persist_messages(
                    session,
                    resolved_to_agents,
                    project,
                    content,
                    is_broadcast_fanout,
                    message_type,
                    priority,
                    from_agent,
                    sender_display_name,
                    requires_action,
                )

                self._logger.info(
                    f"Sent {message_type} message {message_id} from {from_agent or 'orchestrator'} to {to_agents}"
                )

                self._logger.info(
                    f"[WEBSOCKET DEBUG] websocket_manager is {'AVAILABLE' if self._websocket_manager else 'NONE'} "
                    f"for message {message_id}"
                )

                sender_execution = await self._handle_send_message_side_effects(
                    session, messages, project, from_agent, project_id, resolved_to_agents
                )

                # Handover 0827b: Auto-block completed agents that receive direct messages
                # Handover 0435d: Only auto-block if requires_action=True
                await self._auto_block_completed_recipients(
                    session,
                    resolved_to_agents,
                    project,
                    sender_display_name,
                    is_broadcast_fanout,
                    requires_action,
                )

                await self._broadcast_message_events(
                    BroadcastMessageContext(
                        session=session,
                        messages=messages,
                        message_id=message_id,
                        project=project,
                        tenant_key=tenant_key,
                        to_agents=to_agents,
                        resolved_to_agents=resolved_to_agents,
                        from_agent=from_agent,
                        message_type=message_type,
                        content=content,
                        priority=priority,
                        sender_execution=sender_execution,
                    ),
                )

                response = SendMessageResult(
                    message_id=message_id,
                    to_agents=resolved_to_agents,
                    message_type=message_type,
                )

                await self._check_staging_broadcast_directive(
                    session,
                    response,
                    resolved_to_agents,
                    to_agents,
                    from_agent,
                    tenant_key,
                    project,
                )

                return response

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to send message")
            raise BaseGiljoError(message=str(e), context={"operation": "send_message", "project_id": project_id}) from e

    async def _validate_send_message_inputs(
        self,
        session: AsyncSession,
        tenant_key: Optional[str],
        project_id: str,
    ) -> tuple[str, Any]:
        """Validate tenant context and resolve project for send_message."""
        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available",
                context={"operation": "send_message", "project_id": project_id},
            )

        result = await session.execute(
            select(Project).where(and_(Project.tenant_key == tenant_key, Project.id == project_id))
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ResourceNotFoundError(
                message="Project not found or access denied",
                context={"project_id": project_id, "tenant_key": tenant_key},
            )

        return tenant_key, project

    async def _resolve_message_recipients(
        self,
        session: AsyncSession,
        to_agents: list[str],
        project_id: str,
        tenant_key: str,
        from_agent: Optional[str],
    ) -> list[str]:
        """Resolve agent display names/refs to agent_id UUIDs.

        Handover 0372: Routes by agent_id (executor) instead of job_id (work order).
        """
        resolved_to_agents: list[str] = []
        for agent_ref in to_agents:
            if agent_ref == "all":
                exec_result = await session.execute(
                    select(AgentExecution)
                    .join(AgentJob)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentExecution.status.in_(["waiting", "working", "blocked"]),
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                )
                executions = exec_result.scalars().all()

                sender_ref = from_agent or "orchestrator"
                for execution in executions:
                    if sender_ref in (execution.agent_display_name, execution.agent_id):
                        continue
                    resolved_to_agents.append(execution.agent_id)
                    self._logger.info(f"[FANOUT] Expanded broadcast to agent_id '{execution.agent_id}'")
            elif len(agent_ref) == 36 and "-" in agent_ref:
                resolved_to_agents.append(agent_ref)
            else:
                exec_result = await session.execute(
                    select(AgentExecution)
                    .join(AgentJob)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentExecution.agent_display_name == agent_ref,
                            AgentExecution.status.in_(["waiting", "working", "blocked", "complete"]),
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                execution = exec_result.scalar_one_or_none()
                if execution:
                    resolved_to_agents.append(execution.agent_id)
                    self._logger.info(
                        f"[RESOLVER] Resolved agent_display_name '{agent_ref}' to agent_id '{execution.agent_id}'"
                    )
                else:
                    resolved_to_agents.append(agent_ref)
                    self._logger.warning(
                        f"[RESOLVER] Could not resolve agent_display_name '{agent_ref}' "
                        f"to active execution in project {project_id}"
                    )
        return resolved_to_agents

    async def _resolve_sender_display_name(
        self,
        session: AsyncSession,
        from_agent: Optional[str],
        project: Any,
    ) -> str:
        """Resolve sender agent reference to display name (Handover 0827a)."""
        sender_display_name = from_agent or "orchestrator"
        if from_agent:
            sender_lookup = await session.execute(
                select(AgentExecution.agent_display_name)
                .join(AgentJob)
                .where(
                    and_(
                        AgentJob.project_id == project.id,
                        AgentExecution.tenant_key == project.tenant_key,
                        (AgentExecution.agent_display_name == from_agent) | (AgentExecution.agent_id == from_agent),
                    )
                )
                .order_by(AgentExecution.started_at.desc())
                .limit(1)
            )
            sender_display_row = sender_lookup.scalar_one_or_none()
            if sender_display_row:
                sender_display_name = sender_display_row
        return sender_display_name

    async def _persist_messages(
        self,
        session: AsyncSession,
        resolved_to_agents: list[str],
        project: Any,
        content: str,
        is_broadcast_fanout: bool,
        message_type: str,
        priority: str,
        from_agent: Optional[str],
        sender_display_name: str,
        requires_action: bool = False,
    ) -> tuple[list[Message], str | None]:
        """Create Message + MessageRecipient rows for each recipient. Returns (messages, first_message_id)."""
        messages: list[Message] = []
        if len(resolved_to_agents) > 0:
            for recipient_id in resolved_to_agents:
                message = Message(
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    content=content,
                    message_type="broadcast" if is_broadcast_fanout else message_type,
                    priority=priority,
                    status="pending",
                    from_agent_id=from_agent or "orchestrator",
                    from_display_name=sender_display_name,
                    requires_action=requires_action,
                )
                session.add(message)
                await session.flush()
                session.add(
                    MessageRecipient(
                        message_id=message.id,
                        agent_id=recipient_id,
                        tenant_key=project.tenant_key,
                    )
                )
                messages.append(message)
            await session.flush()
            message_ids = [str(msg.id) for msg in messages]
            await session.commit()
            message_id = message_ids[0] if message_ids else None
        else:
            await session.commit()
            message_id = None
        return messages, message_id

    async def _check_staging_broadcast_directive(
        self,
        session: AsyncSession,
        response: SendMessageResult,
        resolved_to_agents: list[str],
        to_agents: list[str],
        from_agent: Optional[str],
        tenant_key: str,
        project: Any,
    ) -> None:
        """Detect staging orchestrator broadcast and enrich response with STOP directive.

        Handover 0709b: Defense-in-depth Layer 5.5 for staging completion.
        """
        is_broadcast = len(resolved_to_agents) > 1 or (to_agents and to_agents[0] == "all")

        if not (is_broadcast and from_agent):
            return

        sender_result = await session.execute(
            select(AgentExecution)
            .where(and_(AgentExecution.agent_id == from_agent, AgentExecution.tenant_key == tenant_key))
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        sender_execution = sender_result.scalar_one_or_none()
        if not sender_execution:
            return

        # TENANT ISOLATION: Filter by tenant_key
        sender_job_result = await session.execute(
            select(AgentJob).where(AgentJob.job_id == sender_execution.job_id, AgentJob.tenant_key == tenant_key)
        )
        sender_job = sender_job_result.scalar_one_or_none()
        if not sender_job:
            return

        is_orchestrator = sender_execution.agent_name == "orchestrator"
        is_staging = sender_execution.status == "waiting"

        if is_orchestrator and is_staging:
            if project.staging_status != "staging_complete":
                project.staging_status = "staging_complete"
                project.updated_at = datetime.now(timezone.utc)

            response.staging_directive = StagingDirective(
                status="STAGING_SESSION_COMPLETE",
                action="STOP",
                message=(
                    "STAGING IS COMPLETE. Your session must end NOW. "
                    "Do NOT proceed to implementation. Do NOT call Task(). "
                    "Do NOT call complete_job() or write_360_memory(). "
                    "The user will click 'Implement' in the dashboard to start "
                    "a new implementation session with a fresh orchestrator."
                ),
                implementation_gate="LOCKED",
                next_step="Report staging complete to user and stop.",
            )
            self._logger.info(
                f"[STAGING DIRECTIVE] Added STOP directive to staging orchestrator broadcast "
                f"(agent_id={from_agent}, status=waiting)"
            )

    async def _handle_send_message_side_effects(
        self,
        session: AsyncSession,
        messages: list,
        project: Any,
        from_agent: Optional[str],
        project_id: str,
        recipient_ids: Optional[list[str]] = None,
    ) -> Any:
        """Update message counters (sent/waiting) with deadlock retry.

        Handover 0387f: Update message counters instead of JSONB persistence.
        Handover 0821: Replaced N+1 per-row UPDATEs with a single batch UPDATE.

        Args:
            recipient_ids: Pre-resolved recipient agent_ids (one per message, same order).

        Returns:
            The sender's AgentExecution record, or None if not found.
        """
        sender_execution = None
        if not messages:
            return sender_execution

        sender_ref = from_agent or "orchestrator"

        async def _counter_update():
            nonlocal sender_execution
            sender_result = await session.execute(
                select(AgentExecution)
                .join(AgentJob)
                .where(
                    and_(
                        AgentJob.project_id == project.id,
                        AgentExecution.tenant_key == project.tenant_key,
                        (AgentExecution.agent_display_name == sender_ref) | (AgentExecution.agent_id == sender_ref),
                    )
                )
                .order_by(AgentExecution.started_at.desc())
                .limit(1)
            )
            sender_execution = sender_result.scalar_one_or_none()

            sent_increments: dict[str, int] = {}
            waiting_increments: dict[str, int] = {}

            if sender_execution:
                sent_increments[sender_execution.agent_id] = 1

            resolved = recipient_ids or []
            for idx, _msg in enumerate(messages):
                rid = resolved[idx] if idx < len(resolved) else None
                if rid:
                    waiting_increments[rid] = waiting_increments.get(rid, 0) + 1

            if sent_increments or waiting_increments:
                await self._repo.batch_update_counters(
                    session=session,
                    tenant_key=project.tenant_key,
                    sent_increments=sent_increments,
                    waiting_increments=waiting_increments,
                )

            await session.commit()
            self._logger.info(f"[COUNTER] Updated counters: sender +1 sent, {len(messages)} recipients +1 waiting each")

        try:
            await with_deadlock_retry(
                session,
                _counter_update,
                operation_name="send_counter_update",
                context={"project_id": project_id},
            )
        except RetryExhaustedError as counter_error:
            self._logger.warning("Failed to update message counters: %s", counter_error)

        return sender_execution

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

        if project.status in ("completed", "cancelled"):
            return []

        auto_blocked_ids = []
        for recipient_id in resolved_to_agents:
            exec_result = await session.execute(
                select(AgentExecution)
                .where(
                    AgentExecution.agent_id == recipient_id,
                    AgentExecution.tenant_key == project.tenant_key,
                )
                .order_by(AgentExecution.started_at.desc())
                .limit(1)
            )
            recipient_execution = exec_result.scalar_one_or_none()

            # Handover 0435b: skip 'closed' agents — they are terminal, no auto-block
            if recipient_execution and recipient_execution.status == "complete":
                old_status = recipient_execution.status
                recipient_execution.status = "blocked"
                recipient_execution.block_reason = f"Received message from {sender_display_name} while completed"
                await session.flush()

                auto_blocked_ids.append(recipient_id)

                if self._websocket_manager:
                    try:
                        job_result = await session.execute(
                            select(AgentJob.job_id, AgentJob.project_id).where(
                                AgentJob.job_id == recipient_execution.job_id,
                                AgentJob.tenant_key == project.tenant_key,
                            )
                        )
                        job_row = job_result.first()
                        await self._websocket_manager.broadcast_job_status_update(
                            job_id=recipient_execution.job_id,
                            agent_display_name=recipient_execution.agent_display_name,
                            tenant_key=project.tenant_key,
                            old_status=old_status,
                            new_status="blocked",
                            project_id=str(job_row.project_id) if job_row else None,
                        )
                    except (RuntimeError, ValueError) as e:
                        self._logger.warning(f"Failed to broadcast auto-block status change for {recipient_id}: {e}")

                self._logger.info(
                    f"[AUTO-BLOCK] Agent {recipient_execution.agent_display_name} "
                    f"({recipient_id}) auto-blocked: message from {sender_display_name}"
                )

        if auto_blocked_ids:
            await session.commit()

        return auto_blocked_ids

    async def _broadcast_message_events(
        self,
        ctx: BroadcastMessageContext,
    ) -> None:
        """Emit WebSocket events for sent/received messages."""
        session = ctx.session
        messages = ctx.messages
        message_id = ctx.message_id
        project = ctx.project
        tenant_key = ctx.tenant_key
        to_agents = ctx.to_agents
        resolved_to_agents = ctx.resolved_to_agents
        from_agent = ctx.from_agent
        message_type = ctx.message_type
        content = ctx.content
        priority = ctx.priority
        sender_execution = ctx.sender_execution
        if self._websocket_manager and messages:
            self._logger.info(f"[WEBSOCKET DEBUG] Calling broadcast_message_sent for message {message_id}")
            try:
                to_agent_value = None
                if len(to_agents) == 1 and to_agents[0] != "all":
                    to_agent_value = to_agents[0]

                recipient_agent_ids = []
                if to_agents and to_agents[0] == "all":
                    # TENANT ISOLATION: Filter by tenant_key
                    result = await session.execute(
                        select(AgentExecution)
                        .join(AgentJob)
                        .where(
                            and_(
                                AgentJob.project_id == project.id,
                                AgentExecution.status.in_(["waiting", "working", "blocked"]),
                                AgentExecution.tenant_key == tenant_key,
                            )
                        )
                    )
                    all_executions = result.scalars().all()
                    sender_ref = from_agent or "orchestrator"
                    recipient_agent_ids = [
                        execution.agent_id
                        for execution in all_executions
                        if sender_ref not in (execution.agent_display_name, execution.agent_id)
                    ]
                    self._logger.info(
                        f"[WEBSOCKET DEBUG] Broadcast to all: {len(recipient_agent_ids)} recipients "
                        f"(excluded sender: {sender_ref})"
                    )
                else:
                    recipient_agent_ids = resolved_to_agents
                    self._logger.info(f"[WEBSOCKET DEBUG] Direct message to: {recipient_agent_ids}")

                # Handover 0387g: Fetch updated counter values after commit
                sender_sent_count = None
                if sender_execution:
                    await session.refresh(sender_execution)
                    sender_sent_count = sender_execution.messages_sent_count

                # TENANT ISOLATION: Filter by tenant_key
                recipient_waiting_count = None
                if recipient_agent_ids:
                    recipient_result = await session.execute(
                        select(AgentExecution)
                        .where(
                            and_(
                                AgentExecution.agent_id == recipient_agent_ids[0],
                                AgentExecution.tenant_key == tenant_key,
                            )
                        )
                        .order_by(AgentExecution.started_at.desc())
                        .limit(1)
                    )
                    first_recipient = recipient_result.scalar_one_or_none()
                    if first_recipient:
                        await session.refresh(first_recipient)
                        recipient_waiting_count = first_recipient.messages_waiting_count

                await self._websocket_manager.broadcast_message_sent(
                    message_id=message_id,
                    job_id=sender_execution.agent_id if sender_execution else "",
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    from_agent=from_agent or "orchestrator",
                    to_agent=to_agent_value,
                    to_job_ids=recipient_agent_ids,
                    message_type=message_type,
                    content_preview=content[:200] if content else "",
                    priority={"low": 0, "normal": 1, "high": 2}.get(priority, 1),
                    sender_sent_count=sender_sent_count,
                    recipient_waiting_count=recipient_waiting_count,
                )
                self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_sent {message_id}")

                if recipient_agent_ids:
                    ws_waiting_count = recipient_waiting_count if len(recipient_agent_ids) == 1 else None
                    await self._websocket_manager.broadcast_message_received(
                        message_id=message_id,
                        job_id=sender_execution.agent_id if sender_execution else "",
                        project_id=project.id,
                        tenant_key=project.tenant_key,
                        from_agent=from_agent or "orchestrator",
                        to_agent_ids=recipient_agent_ids,
                        message_type=message_type,
                        content_preview=content[:200] if content else "",
                        priority={"low": 0, "normal": 1, "high": 2}.get(priority, 1),
                        waiting_count=ws_waiting_count,
                    )
                    self._logger.info(
                        f"[WEBSOCKET DEBUG] Successfully broadcast message_received to {len(recipient_agent_ids)} recipient(s)"
                    )

            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                self._logger.warning(f"Failed to emit WebSocket event for message {message_id}: {ws_error}")
        else:
            self._logger.debug(
                f"[WEBSOCKET DEBUG] Skipping broadcast for message {message_id} - websocket_manager is None"
            )

    # ============================================================================
    # Broadcasting
    # ============================================================================

    async def broadcast(
        self,
        content: str,
        project_id: str,
        priority: str = "normal",
        from_agent: str = "orchestrator",
        tenant_key: Optional[str] = None,
    ) -> SendMessageResult:
        """
        Broadcast a message to all agents in a project.

        Args:
            content: Message content
            project_id: Project ID to broadcast to
            priority: Message priority (default: "normal")
            from_agent: Sender agent name (default: "orchestrator")
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            SendMessageResult with message_id, to_agents, message_type
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(
                    message="No tenant context available",
                    context={"operation": "broadcast", "project_id": project_id},
                )

            async with self._get_session() as session:
                # TENANT ISOLATION: Filter agent jobs by tenant_key
                result = await session.execute(
                    select(AgentJob).where(and_(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key))
                )
                agent_jobs = result.scalars().all()

                if not agent_jobs:
                    raise ResourceNotFoundError(
                        message="No agent jobs found in project",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                agent_display_names = [job.job_type for job in agent_jobs]

                result = await self.send_message(
                    to_agents=agent_display_names,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority=priority,
                    from_agent=from_agent,
                    tenant_key=tenant_key,
                )

                if self._websocket_manager and result.message_id and tenant_key:
                    try:
                        await self._websocket_manager.broadcast_job_message(
                            job_id=project_id,
                            message_id=result.message_id or "",
                            from_agent=from_agent,
                            tenant_key=tenant_key,
                            to_agent=None,
                            message_type="broadcast",
                            content_preview=content[:100] if content else "",
                        )
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                        self._logger.warning(f"Failed to emit WebSocket broadcast event: {ws_error}")

                return result

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to broadcast message")
            raise BaseGiljoError(message=str(e), context={"operation": "broadcast", "project_id": project_id}) from e

    async def broadcast_to_project(
        self,
        project_id: str,
        content: str,
        from_agent: str = "orchestrator",
        tenant_key: Optional[str] = None,
    ) -> BroadcastResult:
        """
        Broadcast a message to all active executions in a project.

        Handover 0372: Added from 0366b for agent-level broadcasting.
        Differs from broadcast() which sends to agent types, not active executors.

        Args:
            project_id: Project ID to broadcast to
            content: Message content
            from_agent: Sender agent_id or agent_display_name (default: "orchestrator")
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            BroadcastResult with message_id, to_agents, message_type, and recipients_count
        """
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(AgentExecution)
                    .join(AgentJob)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentExecution.status.in_(["waiting", "working", "blocked"]),
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                )
                executions = result.scalars().all()

                if not executions:
                    raise ResourceNotFoundError(
                        message="No active executions found in project",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                agent_ids = [execution.agent_id for execution in executions]

                send_result = await self.send_message(
                    to_agents=agent_ids,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority="normal",
                    from_agent=from_agent,
                    tenant_key=tenant_key,
                )

                return BroadcastResult(
                    message_id=send_result.message_id,
                    to_agents=send_result.to_agents,
                    message_type=send_result.message_type,
                    recipients_count=len(agent_ids),
                )

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to broadcast message to project")
            raise BaseGiljoError(
                message=str(e), context={"operation": "broadcast_to_project", "project_id": project_id}
            ) from e
