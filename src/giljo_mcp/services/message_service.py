"""
MessageService - Dedicated service for inter-agent message management

This service extracts all message-related operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).

Responsibilities:
- CRUD operations for messages
- Message routing between agents
- Message acknowledgment and completion
- Message priority handling
- Broadcasting to multiple agents

Design Principles:
- Single Responsibility: Only message domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from src.giljo_mcp.models.tasks import MessageAcknowledgment, MessageCompletion, MessageRecipient
from src.giljo_mcp.repositories.message_repository import MessageRepository
from src.giljo_mcp.schemas.service_responses import (
    BroadcastResult,
    CompleteMessageResult,
    MessageListResult,
    SendMessageResult,
    StagingDirective,
)
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.utils.db_retry import with_deadlock_retry


logger = logging.getLogger(__name__)


class MessageService:
    """
    Service for managing inter-agent messages.

    This service handles all message-related operations including:
    - Sending messages between agents
    - Retrieving pending messages
    - Acknowledging message receipt
    - Completing messages with results
    - Broadcasting to all agents in a project

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
        Initialize MessageService with database and tenant management.

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
        self._repo = MessageRepository()  # Handover 0387f: Counter-based persistence

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
    ) -> SendMessageResult:
        """
        Send a message to one or more agents.

        Handover 0372: Routes by agent_id (executor) instead of job_id (work order).
        This enables succession support - messages route to NEW executor after handover.

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

        Example:
            >>> result = await service.send_message(
            ...     to_agents=["impl-1", "analyzer-1"],
            ...     content="Review code changes",
            ...     project_id="project-123",
            ...     priority="high",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(result["message_id"])
        """
        try:
            async with self._get_session() as session:
                # Validate inputs and resolve project
                tenant_key, project = await self._validate_send_message_inputs(session, tenant_key, project_id)

                # Handover 0410: Detect broadcast intent before fan-out resolution
                is_broadcast_fanout = "all" in to_agents

                # Resolve agent_display_name strings to agent_id UUIDs (executor, not work order)
                # Handover 0372: This enables succession - messages route to NEW executor after handover
                resolved_to_agents = []
                for agent_ref in to_agents:
                    if agent_ref == "all":
                        # FAN-OUT: Query active agents in project (Handover 0387)
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

                        # Expand to individual recipients (excluding sender)
                        sender_ref = from_agent or "orchestrator"
                        for execution in executions:
                            # Skip sender - compare both agent_display_name and agent_id
                            if sender_ref in (execution.agent_display_name, execution.agent_id):
                                continue
                            resolved_to_agents.append(execution.agent_id)
                            self._logger.info(f"[FANOUT] Expanded broadcast to agent_id '{execution.agent_id}'")
                    elif len(agent_ref) == 36 and "-" in agent_ref:
                        # Already a UUID (agent_id) - use directly
                        resolved_to_agents.append(agent_ref)
                    else:
                        # Agent display name string (e.g., "Orchestrator") - resolve to active execution agent_id
                        exec_result = await session.execute(
                            select(AgentExecution)
                            .join(AgentJob)
                            .where(
                                and_(
                                    AgentJob.project_id == project_id,
                                    AgentExecution.agent_display_name == agent_ref,
                                    AgentExecution.status.in_(
                                        ["waiting", "working", "blocked", "complete"]
                                    ),  # Active + completed statuses (0827a)
                                    AgentExecution.tenant_key == tenant_key,
                                )
                            )
                            .order_by(AgentExecution.started_at.desc())
                            .limit(1)  # Latest instance
                        )
                        execution = exec_result.scalar_one_or_none()
                        if execution:
                            resolved_to_agents.append(execution.agent_id)
                            self._logger.info(
                                f"[RESOLVER] Resolved agent_display_name '{agent_ref}' to agent_id '{execution.agent_id}'"
                            )
                        else:
                            # Could not resolve - keep original (will fail to deliver)
                            resolved_to_agents.append(agent_ref)
                            self._logger.warning(
                                f"[RESOLVER] Could not resolve agent_display_name '{agent_ref}' to active execution in project {project_id}"
                            )

                # Sort recipients for deterministic lock ordering (prevents deadlocks
                # when concurrent broadcasts update the same AgentExecution counter rows)
                resolved_to_agents.sort()

                # Resolve sender display name for message enrichment (Handover 0827a)
                sender_display_name = from_agent or "orchestrator"
                if from_agent:
                    sender_lookup = await session.execute(
                        select(AgentExecution.agent_display_name)
                        .join(AgentJob)
                        .where(
                            and_(
                                AgentJob.project_id == project.id,
                                AgentExecution.tenant_key == project.tenant_key,
                                (AgentExecution.agent_display_name == from_agent)
                                | (AgentExecution.agent_id == from_agent),
                            )
                        )
                        .order_by(AgentExecution.started_at.desc())
                        .limit(1)
                    )
                    sender_display_row = sender_lookup.scalar_one_or_none()
                    if sender_display_row:
                        sender_display_name = sender_display_row

                # Create individual messages for each recipient (Handover 0387 - Broadcast Fan-out)
                messages = []
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
                        )
                        session.add(message)
                        await session.flush()  # Flush to assign message.id before creating recipient
                        session.add(
                            MessageRecipient(
                                message_id=message.id,
                                agent_id=recipient_id,
                                tenant_key=project.tenant_key,
                            )
                        )
                        messages.append(message)
                    await session.flush()  # Flush all recipients
                    message_ids = [str(msg.id) for msg in messages]
                    await session.commit()
                    message_id = message_ids[0] if message_ids else None
                else:
                    # No recipients (e.g., broadcast to empty project) - skip message creation
                    await session.commit()
                    message_id = None

                self._logger.info(
                    f"Sent {message_type} message {message_id} from {from_agent or 'orchestrator'} to {to_agents}"
                )

                # DIAGNOSTIC: Check WebSocket manager availability
                self._logger.info(
                    f"[WEBSOCKET DEBUG] websocket_manager is {'AVAILABLE' if self._websocket_manager else 'NONE'} "
                    f"for message {message_id}"
                )

                # Update message counters (sent/waiting) with deadlock retry
                sender_execution = await self._handle_send_message_side_effects(
                    session, messages, project, from_agent, project_id, resolved_to_agents
                )

                # Handover 0827b: Auto-block completed agents that receive direct messages
                await self._auto_block_completed_recipients(
                    session,
                    resolved_to_agents,
                    project,
                    sender_display_name,
                    is_broadcast_fanout,
                )

                # Emit WebSocket events if manager is available
                await self._broadcast_message_events(
                    session,
                    messages,
                    message_id,
                    project,
                    tenant_key,
                    to_agents,
                    resolved_to_agents,
                    from_agent,
                    message_type,
                    content,
                    priority,
                    sender_execution,
                )

                # Handover 0731c: Build typed response (SendMessageResult)
                response = SendMessageResult(
                    message_id=message_id,
                    to_agents=resolved_to_agents,
                    message_type=message_type,
                )

                # Handover 0709b: Detect staging orchestrator broadcast and enrich response
                # Defense-in-depth Layer 5.5: Reinforced advisory STOP signal for staging completion
                # Conditions:
                # 1. Sender is an orchestrator (agent_name == "orchestrator")
                # 2. Job is in staging phase (status == "waiting")
                # 3. Message is a broadcast (to_agents resolved to multiple agents or was ['all'])
                is_broadcast = len(resolved_to_agents) > 1 or (to_agents and to_agents[0] == "all")

                if is_broadcast and from_agent:
                    # Look up sender's execution to check if this is a staging orchestrator
                    sender_result = await session.execute(
                        select(AgentExecution)
                        .where(and_(AgentExecution.agent_id == from_agent, AgentExecution.tenant_key == tenant_key))
                        .order_by(AgentExecution.started_at.desc())
                        .limit(1)
                    )
                    sender_execution = sender_result.scalar_one_or_none()

                    if sender_execution:
                        # Look up the job to check agent_name and status
                        # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                        sender_job_result = await session.execute(
                            select(AgentJob).where(
                                AgentJob.job_id == sender_execution.job_id, AgentJob.tenant_key == tenant_key
                            )
                        )
                        sender_job = sender_job_result.scalar_one_or_none()

                        if sender_job:
                            # Check if this is a staging orchestrator:
                            # - agent_name is "orchestrator" (on AgentExecution)
                            # - status is "waiting" (staging phase, not yet acknowledged)
                            is_orchestrator = sender_execution.agent_name == "orchestrator"
                            is_staging = sender_execution.status == "waiting"

                            if is_orchestrator and is_staging:
                                # Set staging_status now that staging is truly complete
                                if project.staging_status != "staging_complete":
                                    project.staging_status = "staging_complete"
                                    project.updated_at = datetime.now(timezone.utc)

                                # Enrich response with staging directive (typed model)
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

                return response

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to send message")
            raise BaseGiljoError(message=str(e), context={"operation": "send_message", "project_id": project_id}) from e

    async def _validate_send_message_inputs(
        self,
        session: AsyncSession,
        tenant_key: Optional[str],
        project_id: str,
    ) -> tuple[str, Any]:
        """Validate tenant context and resolve project for send_message.

        Returns:
            Tuple of (validated_tenant_key, project) after verification.

        Raises:
            ValidationError: If no tenant context is available.
            ResourceNotFoundError: If the project is not found or access is denied.
        """
        # TENANT ISOLATION: Require tenant_key, fall back to context
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
        Handover 0821: Replaced N+1 per-row UPDATEs with a single batch UPDATE
        using CASE expressions. One SQL statement = PostgreSQL handles all lock
        acquisition internally = no cross-statement deadlock.

        Args:
            recipient_ids: Pre-resolved recipient agent_ids (one per message, same order).
                Handover 0840b: Avoids lazy-loading recipients relationship in async context.

        Returns:
            The sender's AgentExecution record, or None if not found.
        """
        sender_execution = None
        if not messages:
            return sender_execution

        sender_ref = from_agent or "orchestrator"

        async def _counter_update():
            nonlocal sender_execution
            # Step 1: Look up sender execution
            # Handover 0429: Get latest instance when matching by agent_id
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

            # Step 2: Build batch counter dicts
            sent_increments: dict[str, int] = {}
            waiting_increments: dict[str, int] = {}

            if sender_execution:
                sent_increments[sender_execution.agent_id] = 1

            # Handover 0840b: Use pre-resolved recipient_ids to avoid async lazy-load
            resolved = recipient_ids or []
            for idx, _msg in enumerate(messages):
                rid = resolved[idx] if idx < len(resolved) else None
                if rid:
                    waiting_increments[rid] = waiting_increments.get(rid, 0) + 1

            # Step 3: Single batch UPDATE (Handover 0821 - deadlock fix)
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
            # Counter update is a non-critical side effect; message is already committed.
            # Log and continue -- counter skew is recoverable, duplicate messages are not.
            self._logger.warning("Failed to update message counters: %s", counter_error)

        return sender_execution

    async def _auto_block_completed_recipients(
        self,
        session: AsyncSession,
        resolved_to_agents: list[str],
        project: Any,
        sender_display_name: str,
        is_broadcast_fanout: bool,
    ) -> list[str]:
        """Auto-block completed agents that receive a direct message (Handover 0827b).

        When a direct message is delivered to an agent in 'complete' status,
        transitions it to 'blocked' with a reason. This renders as orange
        "Needs Input" on the dashboard — a strong visual signal.

        Skips broadcast messages and closed-out projects.

        Returns:
            List of agent_ids that were auto-blocked.
        """
        if is_broadcast_fanout:
            return []

        # Guard: Don't auto-block if project is closed out
        if project.status in ("completed", "cancelled"):
            return []

        auto_blocked_ids = []
        for recipient_id in resolved_to_agents:
            # Look up recipient execution
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

            if recipient_execution and recipient_execution.status == "complete":
                old_status = recipient_execution.status
                recipient_execution.status = "blocked"
                recipient_execution.block_reason = f"Received message from {sender_display_name} while completed"
                await session.flush()

                auto_blocked_ids.append(recipient_id)

                # Broadcast status change via WebSocket
                if self._websocket_manager:
                    try:
                        # Resolve project_id for the broadcast
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
        session: AsyncSession,
        messages: list,
        message_id: Optional[str],
        project: Any,
        tenant_key: str,
        to_agents: list[str],
        resolved_to_agents: list[str],
        from_agent: Optional[str],
        message_type: str,
        content: str,
        priority: str,
        sender_execution: Any,
    ) -> None:
        """Emit WebSocket events for sent/received messages.

        Broadcasts message_sent event to the sender and message_received event
        to each recipient via the WebSocket manager.
        """
        if self._websocket_manager and messages:
            self._logger.info(f"[WEBSOCKET DEBUG] Calling broadcast_message_sent for message {message_id}")
            try:
                # Determine to_agent: None for broadcasts (including ['all']), specific agent for direct messages
                to_agent_value = None
                if len(to_agents) == 1 and to_agents[0] != "all":
                    to_agent_value = to_agents[0]

                # Determine recipient agent IDs (agent_ids) for explicit job identifiers in event payloads
                recipient_agent_ids = []
                if to_agents and to_agents[0] == "all":
                    # Broadcast: Get ALL agent executions in the project, EXCLUDING sender
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
                    # Exclude sender from recipients to prevent self-notification
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
                    # Direct message: resolved_to_agents already contains agent_ids
                    recipient_agent_ids = resolved_to_agents
                    self._logger.info(f"[WEBSOCKET DEBUG] Direct message to: {recipient_agent_ids}")

                # Handover 0387g: Fetch updated counter values after commit
                # Refresh sender execution to get updated counter
                sender_sent_count = None
                if sender_execution:
                    await session.refresh(sender_execution)
                    sender_sent_count = sender_execution.messages_sent_count

                # For recipient counter, get first recipient's waiting count
                # Handover 0429: Get latest instance by agent_id
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

                # Event 1: Broadcast to SENDER (increments "Messages Sent")
                # Handover 0407: Use sender's agent_id (executor UUID) instead of project ID
                # The frontend resolves by agent_id to find the correct job in the store
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

                # Event 2: Broadcast to RECIPIENT(S) (increments "Messages Waiting")
                # Emit message:received event to recipients
                # Handover 0407: Use sender's agent_id for from_job_id consistency
                # Only send waiting_count for single-recipient messages; for broadcasts
                # the count is per-recipient so omit it (frontend uses +1 fallback)
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
                # Log WebSocket errors but don't fail the message send
                self._logger.warning(f"Failed to emit WebSocket event for message {message_id}: {ws_error}")
        else:
            self._logger.debug(
                f"[WEBSOCKET DEBUG] Skipping broadcast for message {message_id} - websocket_manager is None"
            )

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

        Raises:
            ResourceNotFoundError: No agent jobs found in project
            ValidationError: No tenant context available

        Example:
            >>> result = await service.broadcast(
            ...     content="Project status update",
            ...     project_id="project-123",
            ...     priority="high",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            # TENANT ISOLATION: Require tenant_key, fall back to context
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

                # Send message to all agents (pass tenant_key explicitly)
                result = await self.send_message(
                    to_agents=agent_display_names,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority=priority,
                    from_agent=from_agent,
                    tenant_key=tenant_key,
                )

                # Emit additional broadcast-specific WebSocket event if manager is available
                # Handover 0731c: Check for message_id on typed SendMessageResult
                if self._websocket_manager and result.message_id and tenant_key:
                    try:
                        await self._websocket_manager.broadcast_job_message(
                            job_id=project_id,
                            message_id=result.message_id or "",
                            from_agent=from_agent,
                            tenant_key=tenant_key,
                            to_agent=None,  # Broadcast has no single target
                            message_type="broadcast",
                            content_preview=content[:100] if content else "",
                        )
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                        # Log WebSocket errors but don't fail the broadcast
                        self._logger.warning(f"Failed to emit WebSocket broadcast event: {ws_error}")

                return result

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
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

        Raises:
            ResourceNotFoundError: No active executions found in project

        Example:
            >>> result = await service.broadcast_to_project(
            ...     project_id="project-123",
            ...     content="Project status update",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Get all active executions in project
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

                # Send message to all active executors
                send_result = await self.send_message(
                    to_agents=agent_ids,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority="normal",
                    from_agent=from_agent,
                    tenant_key=tenant_key,
                )

                # Handover 0731c: Return BroadcastResult typed model
                return BroadcastResult(
                    message_id=send_result.message_id,
                    to_agents=send_result.to_agents,
                    message_type=send_result.message_type,
                    recipients_count=len(agent_ids),
                )

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to broadcast message to project")
            raise BaseGiljoError(
                message=str(e), context={"operation": "broadcast_to_project", "project_id": project_id}
            ) from e

    # ============================================================================
    # Message Retrieval
    # ============================================================================

    async def get_messages(
        self,
        agent_name: str,
        project_id: Optional[str] = None,
        status: str = "pending",
        tenant_key: Optional[str] = None,
    ) -> MessageListResult:
        """
        Retrieve messages for a specific agent.

        Args:
            agent_name: Name of agent to get messages for
            project_id: Optional project ID filter
            status: Message status filter (default: "pending")
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            MessageListResult with agent, count, and messages list

        Raises:
            ValidationError: No tenant context available

        Example:
            >>> result = await service.get_messages(
            ...     agent_name="impl-1",
            ...     project_id="project-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> for msg in result["messages"]:
            ...     print(f"{msg['from']}: {msg['content']}")
        """
        try:
            # TENANT ISOLATION: Require tenant_key, fall back to context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(
                    message="No tenant context available",
                    context={"operation": "get_messages", "agent_name": agent_name},
                )

            async with self._get_session() as session:
                # TENANT ISOLATION: Always filter by tenant_key
                # Handover 0840b: JOIN on MessageRecipient instead of JSONB containment
                query = (
                    select(Message)
                    .join(MessageRecipient)
                    .where(
                        and_(
                            Message.status == status,
                            Message.tenant_key == tenant_key,
                            MessageRecipient.agent_id == agent_name,
                        )
                    )
                )

                if project_id:
                    query = query.where(Message.project_id == project_id)

                result = await session.execute(query)
                messages = result.scalars().all()

                # Build message dicts
                agent_messages = [
                    {
                        "id": str(msg.id),
                        "from": msg.from_agent_id or "unknown",
                        "content": msg.content,
                        "type": msg.message_type,
                        "priority": msg.priority,
                        "created": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in messages
                ]

                # Handover 0731c: Return MessageListResult typed model
                return MessageListResult(
                    agent=agent_name,
                    count=len(agent_messages),
                    messages=agent_messages,
                )

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to get messages")
            raise BaseGiljoError(
                message=str(e),
                context={"operation": "get_messages", "agent_name": agent_name, "project_id": project_id},
            ) from e

    async def receive_messages(
        self,
        agent_id: str,
        limit: int = 10,
        tenant_key: Optional[str] = None,
        exclude_self: bool = True,
        exclude_progress: bool = True,
        message_types: Optional[list[str]] = None,
    ) -> MessageListResult:
        """
        Receive pending messages for an agent executor with optional filtering.

        Handover 0372: Added filtering parameters from 0366b for noise reduction.

        Args:
            agent_id: Agent execution ID (executor UUID)
            limit: Maximum number of messages to retrieve (default: 10)
            tenant_key: Optional tenant key (uses current if not provided)
            exclude_self: Filter out messages from same agent_id (default: True)
            exclude_progress: Filter out progress-type messages (default: True)
            message_types: Optional allow-list of message types (default: None = all types)

        Returns:
            MessageListResult with messages list and count

        Example:
            >>> result = await service.receive_messages(
            ...     agent_id="agent-123",
            ...     limit=5,
            ...     exclude_self=True,
            ...     exclude_progress=True
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "receive_messages"})

            async with self._get_session() as session:
                # Handover 0372: Look up AgentExecution by agent_id, then get job
                # Handover 0429: Get latest instance by agent_id
                result = await session.execute(
                    select(AgentExecution)
                    .where(and_(AgentExecution.agent_id == agent_id, AgentExecution.tenant_key == tenant_key))
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                execution = result.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"Agent execution {agent_id} not found",
                        context={"agent_id": agent_id, "tenant_key": tenant_key},
                    )

                # Get the job to access project_id
                # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                job_result = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == execution.job_id, AgentJob.tenant_key == tenant_key)
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    raise ResourceNotFoundError(
                        message=f"Job not found for execution {agent_id}",
                        context={"agent_id": agent_id, "job_id": execution.job_id},
                    )

                # Query messages using native SQLAlchemy queries
                # Handover 0840b: JOIN on MessageRecipient instead of JSONB containment
                # Handover 0387: fan-out at write means no 'all' broadcast matching needed
                conditions = [
                    Message.tenant_key == tenant_key,
                    Message.project_id == job.project_id,
                    Message.status == "pending",  # Only unread messages
                    MessageRecipient.agent_id == agent_id,
                ]

                # HANDOVER 0372: Apply filtering conditions from 0366b

                # Filter: exclude_self - Filter out messages from the same agent
                if exclude_self:
                    # Handover 0840b: from_agent_id is now a proper column
                    conditions.append(func.coalesce(Message.from_agent_id, "") != agent_id)

                # Filter: exclude_progress - Filter out progress-type messages
                if exclude_progress:
                    conditions.append(Message.message_type != "progress")

                # Filter: message_types - Allow-list of message types
                if message_types is not None:
                    if len(message_types) == 0:
                        # Empty allow-list means no messages should pass
                        conditions.append(Message.id is None)
                    else:
                        # Only allow specified message types
                        conditions.append(Message.message_type.in_(message_types))

                query = (
                    select(Message)
                    .join(MessageRecipient)
                    .options(selectinload(Message.acknowledgments))
                    .where(and_(*conditions))
                    .order_by(Message.created_at)
                )

                # Apply limit
                if isinstance(limit, int) and limit > 0:
                    query = query.limit(limit)

                result = await session.execute(query)
                messages = result.scalars().all()

                # AUTO-ACKNOWLEDGE: Bulk update all retrieved messages to acknowledged status (Handover 0326)
                # This happens immediately when agent retrieves messages
                if messages:
                    for msg in messages:
                        msg.status = "acknowledged"
                        msg.acknowledged_at = datetime.now(timezone.utc)
                        # Handover 0840b: INSERT into junction table instead of JSONB append
                        ack_stmt = (
                            pg_insert(MessageAcknowledgment)
                            .values(
                                message_id=str(msg.id),
                                agent_id=agent_id,
                                tenant_key=tenant_key,
                            )
                            .on_conflict_do_nothing(constraint="uq_msg_ack")
                        )
                        await session.execute(ack_stmt)

                    await session.commit()
                    self._logger.info(f"Auto-acknowledged {len(messages)} messages for agent {agent_id}")

                    # Self-healing counter: count actual remaining pending messages
                    # instead of blindly decrementing (prevents permanent counter drift)
                    async def _acknowledge_counters():
                        # Count actual remaining pending messages for this agent
                        # Handover 0840b: JOIN on MessageRecipient instead of JSONB containment
                        pending_stmt = (
                            select(func.count())
                            .select_from(Message)
                            .join(MessageRecipient)
                            .where(
                                Message.tenant_key == tenant_key,
                                Message.project_id == job.project_id,
                                Message.status == "pending",
                                MessageRecipient.agent_id == agent_id,
                            )
                        )
                        pending_result = await session.execute(pending_stmt)
                        actual_pending = pending_result.scalar() or 0

                        # SET waiting count to actual pending (self-healing)
                        # INCREMENT read count by number of messages just acknowledged
                        await session.execute(
                            update(AgentExecution)
                            .where(
                                AgentExecution.agent_id == agent_id,
                                AgentExecution.tenant_key == tenant_key,
                            )
                            .values(
                                messages_waiting_count=actual_pending,
                                messages_read_count=AgentExecution.messages_read_count + len(messages),
                            )
                        )
                        await session.commit()

                    try:
                        await with_deadlock_retry(
                            session,
                            _acknowledge_counters,
                            operation_name="receive_counter_update",
                            context={"agent_id": agent_id},
                        )
                        self._logger.info(
                            f"[COUNTER] Self-healing acknowledge: {len(messages)} messages for {agent_id}"
                        )
                    except RetryExhaustedError:
                        # Counter update is non-critical; messages are already acknowledged.
                        # Log at ERROR for visibility -- counter drift until next receive.
                        self._logger.exception("Failed to update receive counters for %s", agent_id)

                    # Emit WebSocket event for UI update (Handover 0326)
                    # Use broadcast_message_acknowledged for real-time counter updates
                    if self._websocket_manager:
                        try:
                            # Fetch updated counter values after commit (Handover 0425 fix)
                            counter_stats = await self._repo.get_counter_stats(
                                session=session,
                                agent_id=agent_id,
                                tenant_key=tenant_key,
                            )
                            waiting_count = counter_stats["waiting"] if counter_stats else 0
                            read_count = counter_stats["read"] if counter_stats else 0

                            await self._websocket_manager.broadcast_message_acknowledged(
                                message_id=str(messages[0].id) if messages else "",
                                agent_id=agent_id,
                                tenant_key=tenant_key,
                                project_id=str(job.project_id),
                                message_ids=[str(msg.id) for msg in messages],
                                waiting_count=waiting_count,
                                read_count=read_count,
                            )
                            self._logger.info(
                                f"[WEBSOCKET] Broadcast message:acknowledged for {len(messages)} messages (waiting={waiting_count}, read={read_count})"
                            )
                        except (RuntimeError, ValueError) as e:
                            self._logger.warning(f"Failed to emit WebSocket for acknowledged messages: {e}")

                # Handover 0827a: Batch-resolve sender display names for old messages (fallback)
                # Handover 0840b: Use from_agent_id / from_display_name columns
                sender_ids = {msg.from_agent_id for msg in messages if msg.from_agent_id and not msg.from_display_name}
                uuid_ids = [s for s in sender_ids if s and "-" in s and len(s) == 36]
                sender_name_map: dict[str, str] = {}
                if uuid_ids:
                    name_result = await session.execute(
                        select(AgentExecution.agent_id, AgentExecution.agent_display_name).where(
                            AgentExecution.agent_id.in_(uuid_ids),
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    sender_name_map = {row.agent_id: row.agent_display_name for row in name_result}

                # Convert to AgentMessageQueue-compatible format
                messages_list = []
                for msg in messages:
                    # Map priority to integer for backward compatibility
                    priority_reverse_map = {"low": 0, "normal": 1, "high": 2, "critical": 2}
                    priority_int = priority_reverse_map.get(msg.priority, 1)

                    # Handover 0827a: Prefer display name over raw UUID
                    # Handover 0840b: Use from_agent_id / from_display_name columns
                    from_agent_raw = msg.from_agent_id or ""
                    from_display = msg.from_display_name or sender_name_map.get(from_agent_raw, "")

                    messages_list.append(
                        {
                            "id": str(msg.id),
                            "from_agent": from_display or from_agent_raw,
                            "from_agent_id": from_agent_raw,
                            "type": msg.message_type,
                            "content": msg.content,
                            "priority": priority_int,
                            "acknowledged": msg.status in ["acknowledged", "completed"],
                            "acknowledged_at": msg.acknowledged_at.isoformat() if msg.acknowledged_at else None,
                            "acknowledged_by": msg.acknowledgments[0].agent_id if msg.acknowledgments else None,
                            "timestamp": msg.created_at.isoformat(),
                            "metadata": {},
                        }
                    )

                self._logger.info(f"Retrieved {len(messages_list)} messages for agent {agent_id}")

                # Handover 0827c: Append reactivation guidance for auto-blocked agents
                reactivation_guidance = None
                if execution and execution.status == "blocked" and messages_list:
                    reactivation_guidance = {
                        "your_status": "blocked",
                        "your_job_id": str(execution.job_id),
                        "instruction": (
                            "You were in COMPLETE status and received a message. "
                            "Review the message(s) above, then choose ONE action:\n"
                            f'- If action is needed: call reactivate_job(job_id="{execution.job_id}", '
                            'reason="brief reason")\n'
                            f'- If no action needed: call dismiss_reactivation(job_id="{execution.job_id}", '
                            'reason="informational only")'
                        ),
                    }

                # Handover 0731c: Return MessageListResult typed model
                result = MessageListResult(messages=messages_list, count=len(messages_list))
                if reactivation_guidance:
                    # Attach guidance as extra field on the dict representation
                    # MessageListResult.model_dump() won't include this, so we
                    # monkey-patch _reactivation_guidance for the tool response
                    result._reactivation_guidance = reactivation_guidance
                return result

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to receive messages")
            raise BaseGiljoError(message=str(e), context={"operation": "receive_messages", "agent_id": agent_id}) from e

    async def list_messages(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> MessageListResult:
        """
        List messages in a project or for a specific agent.

        Uses native Message queries (NOT AgentMessageQueue which has broken SQL).

        Args:
            project_id: Optional project ID filter
            status: Optional message status filter
            agent_id: Optional agent job ID filter
            tenant_key: Optional tenant key (uses current if not provided)
            limit: Optional maximum number of messages to retrieve

        Returns:
            MessageListResult with messages list and count

        Raises:
            ResourceNotFoundError: Job not found
            ValidationError: No active project or tenant context

        Example:
            >>> result = await service.list_messages(
            ...     project_id="project-123",
            ...     status="pending",
            ...     limit=50
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            # TENANT ISOLATION: tenant_key is always required (Phase D audit fix)
            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_messages"})

            async with self._get_session() as session:
                # If agent_id provided, filter messages for that agent
                if agent_id:
                    # Get agent job to verify it exists and get project context
                    # TENANT ISOLATION: Always filter by tenant_key (Phase D audit fix)
                    conditions = [AgentJob.job_id == agent_id, AgentJob.tenant_key == tenant_key]

                    result = await session.execute(select(AgentJob).where(and_(*conditions)))
                    job = result.scalar_one_or_none()

                    if not job:
                        raise ResourceNotFoundError(
                            message=f"Job {agent_id} not found",
                            context={"agent_id": agent_id, "tenant_key": tenant_key},
                        )

                    # Query messages for this agent using native queries
                    # Handover 0840b: JOIN on MessageRecipient instead of JSONB containment
                    query = (
                        select(Message)
                        .join(MessageRecipient)
                        .where(
                            and_(
                                Message.tenant_key == job.tenant_key,
                                Message.project_id == job.project_id,
                                MessageRecipient.agent_id == agent_id,
                            )
                        )
                        .order_by(Message.created_at)
                    )

                    # Apply limit if provided
                    if limit:
                        query = query.limit(limit)

                    result = await session.execute(query)
                    messages = result.scalars().all()

                    # Convert to standard format (not AgentMessageQueue format)
                    # Handover 0840b: Use from_agent_id column; agent_id known from filter
                    message_list = []
                    for msg in messages:
                        from_agent = msg.from_agent_id or "unknown"

                        message_list.append(
                            {
                                "id": str(msg.id),
                                "from_agent": from_agent,
                                "to_agent": agent_id,
                                "to_agents": [agent_id],
                                "type": msg.message_type,
                                "content": msg.content,
                                "status": msg.status,
                                "priority": msg.priority,
                                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                            }
                        )

                    # Handover 0731c: Return MessageListResult typed model
                    return MessageListResult(messages=message_list, count=len(message_list))

                # Otherwise, list by project
                if project_id:
                    # TENANT ISOLATION: Always filter by tenant_key (Phase D audit fix)
                    query = (
                        select(Message)
                        .options(selectinload(Message.recipients))
                        .where(and_(Message.project_id == project_id, Message.tenant_key == tenant_key))
                    )
                else:
                    # Find project by tenant key
                    project_query = select(Project).where(
                        and_(Project.tenant_key == tenant_key, Project.status == "active")
                    )
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()

                    # Fallback to most recent project
                    if not project:
                        project_query = (
                            select(Project)
                            .where(Project.tenant_key == tenant_key)
                            .order_by(Project.created_at.desc())
                            .limit(1)
                        )
                        project_result = await session.execute(project_query)
                        project = project_result.scalar_one_or_none()

                    if not project:
                        # No project = no messages - return empty list, not error (Handover 0464)
                        # Handover 0731c: Return MessageListResult typed model
                        return MessageListResult(messages=[], count=0)

                    # TENANT ISOLATION: Always filter by tenant_key (Phase D audit fix)
                    query = (
                        select(Message)
                        .options(selectinload(Message.recipients))
                        .where(Message.project_id == project.id, Message.tenant_key == tenant_key)
                    )

                # Apply status filter
                if status:
                    query = query.where(Message.status == status)

                # Apply limit if provided
                if limit:
                    query = query.limit(limit)

                result = await session.execute(query)
                messages = result.scalars().all()

                message_list = []
                for msg in messages:
                    # Handover 0840b: Use from_agent_id column and recipients relationship
                    from_agent = msg.from_agent_id or "unknown"
                    to_agents = [r.agent_id for r in msg.recipients] if msg.recipients else []
                    to_agent = to_agents[0] if to_agents else None

                    message_list.append(
                        {
                            "id": str(msg.id),
                            "from_agent": from_agent,
                            "to_agent": to_agent,  # Single recipient for backward compatibility
                            "to_agents": to_agents,  # Full list
                            "type": msg.message_type,  # Database field is message_type, not type
                            "content": msg.content,
                            "status": msg.status,
                            "priority": msg.priority,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }
                    )

                # Handover 0731c: Return MessageListResult typed model
                return MessageListResult(messages=message_list, count=len(message_list))

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to list messages")
            raise BaseGiljoError(
                message=str(e), context={"operation": "list_messages", "project_id": project_id, "agent_id": agent_id}
            ) from e

    # ============================================================================
    # Message Status Updates
    # ============================================================================

    async def complete_message(
        self, message_id: str, agent_name: str, result: str, tenant_key: Optional[str] = None
    ) -> CompleteMessageResult:
        """
        Mark a message as completed with a result.

        Args:
            message_id: Message UUID
            agent_name: Name of agent completing the message
            result: Completion result/response
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            CompleteMessageResult with message_id and completed_by

        Raises:
            ValidationError: No tenant context available

        Example:
            >>> result = await service.complete_message(
            ...     message_id="msg-123",
            ...     agent_name="impl-1",
            ...     result="Code review completed successfully",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            # TENANT ISOLATION: Require tenant_key, fall back to context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(
                    message="No tenant context available",
                    context={"operation": "complete_message", "message_id": message_id},
                )

            async with self._get_session() as session:
                # TENANT ISOLATION: Filter by both message_id AND tenant_key
                msg_result = await session.execute(
                    select(Message).where(and_(Message.id == message_id, Message.tenant_key == tenant_key))
                )
                message = msg_result.scalar_one_or_none()

                if not message:
                    raise ResourceNotFoundError(
                        message="Message not found or access denied",
                        context={"message_id": message_id, "tenant_key": tenant_key},
                    )

                # Update message
                message.status = "completed"
                message.result = result
                message.completed_at = datetime.now(timezone.utc)

                # Handover 0840b: INSERT into junction table instead of JSONB field
                completion_stmt = (
                    pg_insert(MessageCompletion)
                    .values(
                        message_id=str(message.id),
                        agent_id=agent_name,
                        tenant_key=tenant_key,
                    )
                    .on_conflict_do_nothing(constraint="uq_msg_completion")
                )
                await session.execute(completion_stmt)

                await session.commit()

                self._logger.info(f"Message {message_id} completed by {agent_name}")

                # Emit WebSocket event if manager is available
                if self._websocket_manager:
                    try:
                        await self._websocket_manager.broadcast_message_update(
                            message_id=message_id,
                            project_id=message.project_id or "",
                            update_type="completed",
                            message_data={
                                "completed_by": agent_name,
                                "status": "completed",
                                "result": result[:100] if result else "",
                            },
                        )
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                        # Log WebSocket errors but don't fail the completion
                        self._logger.warning(
                            f"Failed to emit WebSocket event for message completion {message_id}: {ws_error}"
                        )

                # Handover 0731c: Return CompleteMessageResult typed model
                return CompleteMessageResult(
                    message_id=message_id,
                    completed_by=agent_name,
                )

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to complete message")
            raise BaseGiljoError(
                message=str(e), context={"operation": "complete_message", "message_id": message_id}
            ) from e
