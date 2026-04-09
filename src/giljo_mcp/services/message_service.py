# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MessageService - Message retrieval, acknowledgment, and status management.

Handles read-side message operations: retrieval, acknowledgment, completion,
listing, and status tracking. For sending, routing, and broadcasting, see
MessageRoutingService (message_routing_service.py).

Handover 0123: Original extraction from ToolAccessor.
Handover 0950h: Routing/broadcast methods extracted to MessageRoutingService.
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
    CompleteMessageResult,
    MessageListResult,
    MessageStatusResult,
)
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.utils.db_retry import with_deadlock_retry

logger = logging.getLogger(__name__)


class MessageService:
    """
    Service for message retrieval, acknowledgment, and status management.

    Handles read-side operations:
    - Retrieving pending messages for agents
    - Acknowledging message receipt
    - Completing messages with results
    - Listing and querying messages
    - Message status tracking

    For sending, routing, and broadcasting, see MessageRoutingService.

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

                # Build filtered query
                query = self._build_receive_query(
                    agent_id=agent_id,
                    tenant_key=tenant_key,
                    project_id=job.project_id,
                    exclude_self=exclude_self,
                    exclude_progress=exclude_progress,
                    message_types=message_types,
                    limit=limit,
                )

                result = await session.execute(query)
                messages = result.scalars().all()

                # Auto-acknowledge, update counters, resolve senders, format results
                messages_list = await self._process_received_messages(
                    session=session,
                    messages=messages,
                    agent_id=agent_id,
                    tenant_key=tenant_key,
                    job=job,
                    execution=execution,
                )

                self._logger.info(f"Retrieved {len(messages_list)} messages for agent {agent_id}")

                # Handover 0827c: Append reactivation guidance for auto-blocked agents
                reactivation_guidance = self._build_reactivation_guidance(execution, messages_list)

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

    def _build_receive_query(
        self,
        agent_id: str,
        tenant_key: str,
        project_id: Any,
        exclude_self: bool,
        exclude_progress: bool,
        message_types: Optional[list[str]],
        limit: int,
    ) -> Any:
        """Build the SQLAlchemy query for receive_messages with all filters applied."""
        # Handover 0840b: JOIN on MessageRecipient instead of JSONB containment
        # Handover 0387: fan-out at write means no 'all' broadcast matching needed
        conditions = [
            Message.tenant_key == tenant_key,
            Message.project_id == project_id,
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
            .options(selectinload(Message.acknowledgments), selectinload(Message.recipients))
            .where(and_(*conditions))
            .order_by(Message.created_at)
        )

        # Apply limit
        if isinstance(limit, int) and limit > 0:
            query = query.limit(limit)

        return query

    async def _process_received_messages(
        self,
        session: Any,
        messages: list,
        agent_id: str,
        tenant_key: str,
        job: Any,
        execution: Any,
    ) -> list[dict]:
        """Auto-acknowledge messages, update counters, resolve senders, and format results."""
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
                self._logger.info(f"[COUNTER] Self-healing acknowledge: {len(messages)} messages for {agent_id}")
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

            # Build recipient context for broadcast awareness
            recipient_ids = [r.agent_id for r in msg.recipients] if msg.recipients else []

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
                    "recipients_count": len(recipient_ids),
                    "metadata": {},
                }
            )

        return messages_list

    def _build_reactivation_guidance(
        self,
        execution: Any,
        messages_list: list[dict],
    ) -> Optional[dict]:
        """Build reactivation guidance for auto-blocked agents (Handover 0827c)."""
        # Only show for post-completion auto-blocks (completed_at set),
        # not for mid-work blocks via set_agent_status(status="blocked")
        is_post_completion_block = execution and execution.status == "blocked" and execution.completed_at is not None
        is_mid_work_block = execution and execution.status == "blocked" and execution.completed_at is None
        if is_post_completion_block and messages_list:
            return {
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
        if is_mid_work_block and messages_list:
            return {
                "your_status": "blocked",
                "your_job_id": str(execution.job_id),
                "block_reason": execution.block_reason or "unknown",
                "instruction": (
                    "You are BLOCKED due to an error you reported. "
                    "Review any message(s) above for guidance, then resume by calling:\n"
                    f'report_progress(job_id="{execution.job_id}", '
                    "todo_items=[...your updated tasks...])\n"
                    "This will transition you back to WORKING status."
                ),
            }
        return None

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

        Args:
            project_id: Optional project ID filter
            status: Optional message status filter
            agent_id: Optional agent job ID filter
            tenant_key: Optional tenant key (uses current if not provided)
            limit: Optional maximum number of messages to retrieve

        Returns:
            MessageListResult with messages list and count
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_messages"})

            async with self._get_session() as session:
                query, for_agent_id = await self._build_list_query(
                    session, project_id, status, agent_id, tenant_key, limit
                )
                if query is None:
                    return MessageListResult(messages=[], count=0)

                result = await session.execute(query)
                messages = result.scalars().all()
                message_list = [self._format_list_message(msg, for_agent_id) for msg in messages]
                return MessageListResult(messages=message_list, count=len(message_list))

        except (ResourceNotFoundError, ValidationError, MessageDeliveryError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to list messages")
            raise BaseGiljoError(
                message=str(e), context={"operation": "list_messages", "project_id": project_id, "agent_id": agent_id}
            ) from e

    async def _build_list_query(
        self,
        session: AsyncSession,
        project_id: Optional[str],
        status: Optional[str],
        agent_id: Optional[str],
        tenant_key: str,
        limit: Optional[int],
    ) -> tuple[Any, Optional[str]]:
        """Build the SQLAlchemy query for list_messages.

        Returns:
            Tuple of (query, for_agent_id). query is None if no messages can exist.
            for_agent_id is set when filtering by agent (changes output format).
        """
        if agent_id:
            # TENANT ISOLATION: Always filter by tenant_key
            result = await session.execute(
                select(AgentJob).where(and_(AgentJob.job_id == agent_id, AgentJob.tenant_key == tenant_key))
            )
            job = result.scalar_one_or_none()
            if not job:
                raise ResourceNotFoundError(
                    message=f"Job {agent_id} not found",
                    context={"agent_id": agent_id, "tenant_key": tenant_key},
                )

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
            if status:
                query = query.where(Message.status == status)
            if limit:
                query = query.limit(limit)
            return query, agent_id

        # Project-based query
        if project_id:
            query = (
                select(Message)
                .options(selectinload(Message.recipients))
                .where(and_(Message.project_id == project_id, Message.tenant_key == tenant_key))
            )
        else:
            project_query = select(Project).where(and_(Project.tenant_key == tenant_key, Project.status == "active"))
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()
            if not project:
                project_query = (
                    select(Project).where(Project.tenant_key == tenant_key).order_by(Project.created_at.desc()).limit(1)
                )
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()
            if not project:
                return None, None

            query = (
                select(Message)
                .options(selectinload(Message.recipients))
                .where(Message.project_id == project.id, Message.tenant_key == tenant_key)
            )

        if status:
            query = query.where(Message.status == status)
        if limit:
            query = query.limit(limit)
        return query, None

    def _format_list_message(self, msg: Any, for_agent_id: Optional[str] = None) -> dict:
        """Format a Message record for list_messages output."""
        from_agent = msg.from_agent_id or "unknown"
        base = {
            "id": str(msg.id),
            "from_agent": from_agent,
            "type": msg.message_type,
            "content": msg.content,
            "status": msg.status,
            "priority": msg.priority,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        if for_agent_id:
            base["to_agent"] = for_agent_id
            base["to_agents"] = [for_agent_id]
        else:
            to_agents = [r.agent_id for r in msg.recipients] if msg.recipients else []
            base["to_agent"] = to_agents[0] if to_agents else None
            base["to_agents"] = to_agents
        return base

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

    async def get_message_status(self, message_id: str, tenant_key: Optional[str] = None) -> MessageStatusResult:
        """
        Get delivery and read status for a specific message.

        Allows senders to verify whether recipients consumed their message.

        Args:
            message_id: Message UUID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            MessageStatusResult with acknowledgment and completion details

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: Message not found
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(
                    message="No tenant context available",
                    context={"operation": "get_message_status", "message_id": message_id},
                )

            async with self._get_session() as session:
                stmt = (
                    select(Message)
                    .options(
                        selectinload(Message.acknowledgments),
                        selectinload(Message.recipients),
                        selectinload(Message.completions),
                    )
                    .where(and_(Message.id == message_id, Message.tenant_key == tenant_key))
                )
                result = await session.execute(stmt)
                message = result.scalar_one_or_none()

                if not message:
                    raise ResourceNotFoundError(
                        message="Message not found or access denied",
                        context={"message_id": message_id, "tenant_key": tenant_key},
                    )

                return MessageStatusResult(
                    message_id=message_id,
                    status=message.status or "pending",
                    acknowledged_by=[a.agent_id for a in message.acknowledgments],
                    completed_by=[c.agent_id for c in message.completions] if message.completions else [],
                    recipients_count=len(message.recipients) if message.recipients else 0,
                )

        except (ResourceNotFoundError, ValidationError, BaseGiljoError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps unexpected errors in BaseGiljoError
            self._logger.exception("Failed to get message status")
            raise BaseGiljoError(
                message=str(e), context={"operation": "get_message_status", "message_id": message_id}
            ) from e
