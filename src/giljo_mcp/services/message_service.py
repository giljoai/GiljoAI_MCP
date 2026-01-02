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
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from contextlib import asynccontextmanager

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Message, Project
from giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from giljo_mcp.tenant import TenantManager


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
    ) -> dict[str, Any]:
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
            Dict with success status and message details or error

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
                # Get project with tenant isolation filter (Handover 0325)
                if tenant_key:
                    result = await session.execute(
                        select(Project).where(
                            Project.tenant_key == tenant_key,
                            Project.id == project_id
                        )
                    )
                else:
                    # Fallback for backward compatibility - will be deprecated
                    result = await session.execute(
                        select(Project).where(Project.id == project_id)
                    )
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": "Project not found or access denied"
                    }

                # Resolve agent_type strings to agent_id UUIDs (executor, not work order)
                # Handover 0372: This enables succession - messages route to NEW executor after handover
                resolved_to_agents = []
                for agent_ref in to_agents:
                    if agent_ref == 'all':
                        # FAN-OUT: Query active agents in project (Handover 0387)
                        exec_result = await session.execute(
                            select(AgentExecution).join(AgentJob).where(
                                and_(
                                    AgentJob.project_id == project_id,
                                    AgentExecution.status.in_(["waiting", "working", "blocked"]),
                                    AgentExecution.tenant_key == tenant_key,
                                )
                            )
                        )
                        executions = exec_result.scalars().all()

                        # Expand to individual recipients (excluding sender)
                        sender_type = from_agent or "orchestrator"
                        for execution in executions:
                            # Skip sender
                            if execution.agent_type == sender_type:
                                continue
                            resolved_to_agents.append(execution.agent_id)
                            self._logger.info(f"[FANOUT] Expanded broadcast to agent_id '{execution.agent_id}'")
                    elif len(agent_ref) == 36 and '-' in agent_ref:
                        # Already a UUID (agent_id) - use directly
                        resolved_to_agents.append(agent_ref)
                    else:
                        # Agent type string (e.g., "orchestrator") - resolve to active execution agent_id
                        exec_result = await session.execute(
                            select(AgentExecution).join(AgentJob).where(
                                and_(
                                    AgentJob.project_id == project_id,
                                    AgentExecution.agent_type == agent_ref,
                                    AgentExecution.status.in_(["waiting", "working", "blocked"]),  # Active statuses
                                    AgentExecution.tenant_key == tenant_key
                                )
                            ).order_by(AgentExecution.instance_number.desc()).limit(1)  # Latest instance
                        )
                        execution = exec_result.scalar_one_or_none()
                        if execution:
                            resolved_to_agents.append(execution.agent_id)
                            self._logger.info(
                                f"[RESOLVER] Resolved agent_type '{agent_ref}' to agent_id '{execution.agent_id}'"
                            )
                        else:
                            # Could not resolve - keep original (will fail to deliver)
                            resolved_to_agents.append(agent_ref)
                            self._logger.warning(
                                f"[RESOLVER] Could not resolve agent_type '{agent_ref}' to active execution in project {project_id}"
                            )

                # Create individual messages for each recipient (Handover 0387 - Broadcast Fan-out)
                message_ids = []
                if len(resolved_to_agents) > 0:
                    for recipient_id in resolved_to_agents:
                        message = Message(
                            project_id=project.id,
                            tenant_key=project.tenant_key,
                            to_agents=[recipient_id],  # Single recipient per message (fan-out)
                            content=content,
                            message_type=message_type,
                            priority=priority,
                            status="pending",
                            # Store project_id as job_id for WebSocket consumers that key off job_id/project_id.
                            meta_data={"_from_agent": from_agent or "orchestrator", "job_id": project.id},
                        )
                        session.add(message)
                        message_ids.append(str(message.id))
                    await session.commit()
                    message_id = message_ids[0] if message_ids else None
                else:
                    # No recipients (e.g., broadcast to empty project) - skip message creation
                    await session.commit()
                    message_id = None

                self._logger.info(
                    f"Sent {message_type} message {message_id} "
                    f"from {from_agent or 'orchestrator'} to {to_agents}"
                )

                # DIAGNOSTIC: Check WebSocket manager availability
                self._logger.info(
                    f"[WEBSOCKET DEBUG] websocket_manager is {'AVAILABLE' if self._websocket_manager else 'NONE'} "
                    f"for message {message_id}"
                )

                # Emit WebSocket events if manager is available
                if self._websocket_manager:
                    self._logger.info(f"[WEBSOCKET DEBUG] Calling broadcast_message_sent for message {message_id}")
                    try:
                        # Determine to_agent: None for broadcasts (including ['all']), specific agent for direct messages
                        to_agent_value = None
                        if len(to_agents) == 1 and to_agents[0] != 'all':
                            to_agent_value = to_agents[0]

                        # Determine recipient agent IDs (agent_ids) for explicit job identifiers in event payloads
                        recipient_agent_ids = []
                        if to_agents and to_agents[0] == 'all':
                            # Broadcast: Get ALL agent executions in the project, EXCLUDING sender
                            result = await session.execute(
                                select(AgentExecution).join(AgentJob).where(
                                    and_(
                                        AgentJob.project_id == project.id,
                                        AgentExecution.status.in_(["waiting", "working", "blocked"])
                                    )
                                )
                            )
                            all_executions = result.scalars().all()
                            # Exclude sender from recipients to prevent self-notification
                            sender_agent_type = from_agent or "orchestrator"
                            recipient_agent_ids = [
                                exec.agent_id for exec in all_executions
                                if exec.agent_type != sender_agent_type
                            ]
                            self._logger.info(
                                f"[WEBSOCKET DEBUG] Broadcast to all: {len(recipient_agent_ids)} recipients "
                                f"(excluded sender: {sender_agent_type})"
                            )
                        else:
                            # Direct message: resolved_to_agents already contains agent_ids
                            recipient_agent_ids = resolved_to_agents
                            self._logger.info(f"[WEBSOCKET DEBUG] Direct message to: {recipient_agent_ids}")

                        # Event 1: Broadcast to SENDER (increments "Messages Sent")
                        await self._websocket_manager.broadcast_message_sent(
                            message_id=message_id,
                            job_id=message.meta_data.get("job_id", ""),
                            project_id=project.id,
                            tenant_key=project.tenant_key,
                            from_agent=from_agent or "orchestrator",
                            to_agent=to_agent_value,
                            to_job_ids=recipient_agent_ids,
                            message_type=message_type,
                            content_preview=content[:200] if content else "",
                            priority={"low": 0, "normal": 1, "high": 2}.get(priority, 1),
                        )
                        self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_sent {message_id}")

                        # Event 2: Broadcast to RECIPIENT(S) (increments "Messages Waiting")
                        # Emit message:received event to recipients
                        if recipient_agent_ids:
                            await self._websocket_manager.broadcast_message_received(
                                message_id=message_id,
                                job_id=message.meta_data.get("job_id", ""),
                                project_id=project.id,
                                tenant_key=project.tenant_key,
                                from_agent=from_agent or "orchestrator",
                                to_agent_ids=recipient_agent_ids,
                                message_type=message_type,
                                content_preview=content[:200] if content else "",
                                priority={"low": 0, "normal": 1, "high": 2}.get(priority, 1),
                            )
                            self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_received to {len(recipient_agent_ids)} recipient(s)")

                        # CRITICAL: Persist messages to agent_executions.messages JSONB column for counter persistence
                        # Handover 0372: Now persists to agent_executions, not agent_jobs
                        await self._persist_message_to_agent_jsonb(
                            session=session,
                            message_id=message_id,
                            from_agent=from_agent or "orchestrator",
                            recipient_job_ids=recipient_agent_ids,  # Now contains agent_ids, not job_ids
                            content=content,
                            message_type=message_type,
                            priority=priority,
                            project_id=project.id,
                            tenant_key=project.tenant_key,
                        )
                        self._logger.info(f"[PERSISTENCE] Saved message {message_id} to agent JSONB columns")

                    except Exception as ws_error:
                        # Log WebSocket errors but don't fail the message send
                        self._logger.warning(
                            f"Failed to emit WebSocket event for message {message_id}: {ws_error}"
                        )
                else:
                    self._logger.warning(
                        f"[WEBSOCKET DEBUG] Skipping broadcast for message {message_id} - websocket_manager is None"
                    )

                return {
                    "success": True,
                    "message_id": message_id,
                    "to_agents": resolved_to_agents,
                    "type": message_type,
                }

        except Exception as e:
            self._logger.exception(f"Failed to send message: {e}")
            return {"success": False, "error": str(e)}

    async def broadcast(
        self,
        content: str,
        project_id: str,
        priority: str = "normal",
        from_agent: str = "orchestrator"
    ) -> dict[str, Any]:
        """
        Broadcast a message to all agents in a project.

        Args:
            content: Message content
            project_id: Project ID to broadcast to
            priority: Message priority (default: "normal")
            from_agent: Sender agent name (default: "orchestrator")

        Returns:
            Dict with success status and message details or error

        Example:
            >>> result = await service.broadcast(
            ...     content="Project status update",
            ...     project_id="project-123",
            ...     priority="high"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Get all agent jobs in project
                result = await session.execute(
                    select(AgentJob).where(AgentJob.project_id == project_id)
                )
                agent_jobs = result.scalars().all()

                if not agent_jobs:
                    return {
                        "success": False,
                        "error": "No agent jobs found in project"
                    }

                agent_types = [job.job_type for job in agent_jobs]

                # Get tenant_key from first agent job for WebSocket broadcast
                tenant_key = agent_jobs[0].tenant_key if agent_jobs else None

                # Send message to all agents
                result = await self.send_message(
                    to_agents=agent_types,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority=priority,
                    from_agent=from_agent,
                )

                # Emit additional broadcast-specific WebSocket event if manager is available
                if self._websocket_manager and result.get("success") and tenant_key:
                    try:
                        await self._websocket_manager.broadcast_job_message(
                            job_id=project_id,
                            message_id=result.get("message_id", ""),
                            from_agent=from_agent,
                            tenant_key=tenant_key,
                            to_agent=None,  # Broadcast has no single target
                            message_type="broadcast",
                            content_preview=content[:100] if content else "",
                        )
                    except Exception as ws_error:
                        # Log WebSocket errors but don't fail the broadcast
                        self._logger.warning(
                            f"Failed to emit WebSocket broadcast event: {ws_error}"
                        )

                return result

        except Exception as e:
            self._logger.exception(f"Failed to broadcast message: {e}")
            return {"success": False, "error": str(e)}

    async def broadcast_to_project(
        self,
        project_id: str,
        content: str,
        from_agent: str = "orchestrator",
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Broadcast a message to all active executions in a project.

        Handover 0372: Added from 0366b for agent-level broadcasting.
        Differs from broadcast() which sends to agent types, not active executors.

        Args:
            project_id: Project ID to broadcast to
            content: Message content
            from_agent: Sender agent_id or agent_type (default: "orchestrator")
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with success status and message details or error

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
                    select(AgentExecution).join(AgentJob).where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentExecution.status.in_(["waiting", "working", "blocked"]),
                            AgentExecution.tenant_key == tenant_key
                        )
                    )
                )
                executions = result.scalars().all()

                if not executions:
                    return {
                        "success": False,
                        "error": "No active executions found in project"
                    }

                agent_ids = [exec.agent_id for exec in executions]

                # Send message to all active executors
                result = await self.send_message(
                    to_agents=agent_ids,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority="normal",
                    from_agent=from_agent,
                    tenant_key=tenant_key,
                )

                if result.get("success"):
                    result["count"] = len(agent_ids)

                return result

        except Exception as e:
            self._logger.exception(f"Failed to broadcast message to project: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Message Retrieval
    # ============================================================================

    async def get_messages(
        self,
        agent_name: str,
        project_id: Optional[str] = None,
        status: str = "pending"
    ) -> dict[str, Any]:
        """
        Retrieve messages for a specific agent.

        Args:
            agent_name: Name of agent to get messages for
            project_id: Optional project ID filter
            status: Message status filter (default: "pending")

        Returns:
            Dict with success status and list of messages or error

        Example:
            >>> result = await service.get_messages(
            ...     agent_name="impl-1",
            ...     project_id="project-123"
            ... )
            >>> for msg in result["messages"]:
            ...     print(f"{msg['from']}: {msg['content']}")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Build query
                query = select(Message).where(Message.status == status)

                if project_id:
                    query = query.where(Message.project_id == project_id)

                result = await session.execute(query)
                messages = result.scalars().all()

                # Filter messages for this agent
                agent_messages = []
                for msg in messages:
                    # Include if agent is in to_agents list or if broadcast (empty to_agents)
                    if agent_name in msg.to_agents or not msg.to_agents:
                        agent_messages.append({
                            "id": str(msg.id),
                            "from": msg.meta_data.get("_from_agent", "unknown"),
                            "content": msg.content,
                            "type": msg.message_type,
                            "priority": msg.priority,
                            "created": msg.created_at.isoformat() if msg.created_at else None,
                        })

                return {
                    "success": True,
                    "agent": agent_name,
                    "count": len(agent_messages),
                    "messages": agent_messages,
                }

        except Exception as e:
            self._logger.exception(f"Failed to get messages: {e}")
            return {"success": False, "error": str(e)}

    async def receive_messages(
        self,
        agent_id: str,
        limit: int = 10,
        tenant_key: Optional[str] = None,
        exclude_self: bool = True,
        exclude_progress: bool = True,
        message_types: Optional[list[str]] = None
    ) -> dict[str, Any]:
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
            Dict with success status and list of messages or error

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
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                # Handover 0372: Look up AgentExecution by agent_id, then get job
                result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.agent_id == agent_id,
                            AgentExecution.tenant_key == tenant_key
                        )
                    )
                )
                execution = result.scalar_one_or_none()

                if not execution:
                    return {
                        "success": False,
                        "error": f"Agent execution {agent_id} not found"
                    }

                # Get the job to access project_id
                job_result = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == execution.job_id)
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    return {
                        "success": False,
                        "error": f"Job not found for execution {agent_id}"
                    }

                # Query messages using native SQLAlchemy queries
                # Include messages where:
                # 1. Direct message to this agent (to_agents contains agent_id as JSON array element)
                # 2. Broadcast message (to_agents contains 'all') BUT exclude sender (Issue 0361-3)
                # 3. Only pending messages (unread_only=True by default)
                from sqlalchemy import or_, func, String
                from sqlalchemy.dialects.postgresql import JSONB

                # Build query conditions (Handover 0372: Agent-ID filtering from 0366b)
                conditions = [
                    Message.tenant_key == tenant_key,
                    Message.project_id == job.project_id,
                    Message.status == "pending",  # Only unread messages
                    or_(
                        # Direct message: JSONB array contains agent_id
                        func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
                        # Broadcast: JSONB array contains 'all' BUT exclude sender (Issue 0361-3)
                        and_(
                            func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB)),
                            func.coalesce(
                                Message.meta_data.op('->')('_from_agent').astext,
                                func.cast('', String)
                            ) != job.job_type
                        )
                    )
                ]

                # HANDOVER 0372: Apply filtering conditions from 0366b

                # Filter: exclude_self - Filter out messages from the same agent
                if exclude_self:
                    # Meta_data._from_agent should not equal current agent_id
                    conditions.append(
                        func.coalesce(
                            Message.meta_data.op('->>')('_from_agent'),
                            ''
                        ) != agent_id
                    )

                # Filter: exclude_progress - Filter out progress-type messages
                if exclude_progress:
                    conditions.append(Message.message_type != "progress")

                # Filter: message_types - Allow-list of message types
                if message_types is not None:
                    if len(message_types) == 0:
                        # Empty allow-list means no messages should pass
                        conditions.append(Message.id == None)  # noqa: E711
                    else:
                        # Only allow specified message types
                        conditions.append(Message.message_type.in_(message_types))

                query = select(Message).where(and_(*conditions)).order_by(Message.created_at)

                # Apply limit
                if isinstance(limit, int) and limit > 0:
                    query = query.limit(limit)

                result = await session.execute(query)
                messages = result.scalars().all()

                # AUTO-ACKNOWLEDGE: Bulk update all retrieved messages to acknowledged status (Handover 0326)
                # This happens immediately when agent retrieves messages
                if messages:
                    from datetime import datetime, timezone

                    for msg in messages:
                        msg.status = "acknowledged"
                        msg.acknowledged_at = datetime.now(timezone.utc)
                        # Maintain acknowledged_by as a list (JSONB array in database)
                        if not msg.acknowledged_by:
                            msg.acknowledged_by = []
                        if agent_id not in msg.acknowledged_by:
                            msg.acknowledged_by.append(agent_id)

                    await session.commit()
                    self._logger.info(f"Auto-acknowledged {len(messages)} messages for agent {agent_id}")

                    # Update JSONB messages array status for UI counter (Handover 0326)
                    # The dashboard reads from AgentJob.messages JSONB, not Message table
                    await self._update_jsonb_message_status(
                        session=session,
                        job_id=agent_id,
                        message_ids=[str(msg.id) for msg in messages],
                        new_status="acknowledged"
                    )

                    # Emit WebSocket event for UI update (Handover 0326)
                    # Use broadcast_message_acknowledged for real-time counter updates
                    if self._websocket_manager:
                        try:
                            await self._websocket_manager.broadcast_message_acknowledged(
                                message_id=str(messages[0].id) if messages else "",
                                agent_id=agent_id,
                                tenant_key=tenant_key,
                                project_id=str(job.project_id),
                                message_ids=[str(msg.id) for msg in messages],
                            )
                            self._logger.info(f"[WEBSOCKET] Broadcast message:acknowledged for {len(messages)} messages")
                        except Exception as e:
                            self._logger.warning(f"Failed to emit WebSocket for acknowledged messages: {e}")

                # Convert to AgentMessageQueue-compatible format
                messages_list = []
                for msg in messages:
                    # Map priority to integer for backward compatibility
                    priority_reverse_map = {"low": 0, "normal": 1, "high": 2, "critical": 2}
                    priority_int = priority_reverse_map.get(msg.priority, 1)

                    messages_list.append({
                        "id": str(msg.id),
                        "from_agent": msg.meta_data.get("_from_agent", "") if msg.meta_data else "",
                        "to_agent": msg.to_agents[0] if msg.to_agents else None,
                        "type": msg.message_type,
                        "content": msg.content,
                        "priority": priority_int,
                        "acknowledged": msg.status in ["acknowledged", "completed"],
                        "acknowledged_at": msg.acknowledged_at.isoformat() if msg.acknowledged_at else None,
                        "acknowledged_by": msg.acknowledged_by[0] if msg.acknowledged_by else None,
                        "timestamp": msg.created_at.isoformat(),
                        "metadata": msg.meta_data or {},
                    })

                self._logger.info(f"Retrieved {len(messages_list)} messages for agent {agent_id}")

                return {
                    "success": True,
                    "messages": messages_list,
                    "count": len(messages_list)
                }

        except Exception as e:
            self._logger.exception(f"Failed to receive messages: {e}")
            return {"success": False, "error": str(e)}

    async def list_messages(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        limit: Optional[int] = None
    ) -> dict[str, Any]:
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
            Dict with success status and list of messages or error

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

            if not tenant_key and not project_id:
                return {
                    "success": False,
                    "error": "No active project or tenant context"
                }

            async with self.db_manager.get_session_async() as session:
                # If agent_id provided, filter messages for that agent
                if agent_id:
                    # Get agent job to verify it exists and get project context
                    # Build WHERE conditions
                    conditions = [AgentJob.job_id == agent_id]
                    if tenant_key:
                        conditions.append(AgentJob.tenant_key == tenant_key)

                    result = await session.execute(
                        select(AgentJob).where(and_(*conditions))
                    )
                    job = result.scalar_one_or_none()

                    if not job:
                        return {
                            "success": False,
                            "error": f"Job {agent_id} not found"
                        }

                    # Query messages for this agent using native queries
                    from sqlalchemy import or_, func
                    from sqlalchemy.dialects.postgresql import JSONB

                    query = select(Message).where(
                        and_(
                            Message.tenant_key == job.tenant_key,
                            Message.project_id == job.project_id,
                            or_(
                                # Direct message: JSONB array contains agent_id
                                # Cast both sides to JSONB to avoid type mismatch
                                func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
                                # Broadcast: JSONB array contains 'all'
                                func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB))
                            )
                        )
                    ).order_by(Message.created_at)

                    # Apply limit if provided
                    if limit:
                        query = query.limit(limit)

                    result = await session.execute(query)
                    messages = result.scalars().all()

                    # Convert to standard format (not AgentMessageQueue format)
                    message_list = []
                    for msg in messages:
                        from_agent = msg.meta_data.get("_from_agent", "unknown") if msg.meta_data else "unknown"
                        to_agents = msg.to_agents if msg.to_agents else []
                        to_agent = to_agents[0] if to_agents else None

                        message_list.append({
                            "id": str(msg.id),
                            "from_agent": from_agent,
                            "to_agent": to_agent,
                            "to_agents": to_agents,
                            "type": msg.message_type,
                            "content": msg.content,
                            "status": msg.status,
                            "priority": msg.priority,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        })

                    return {
                        "success": True,
                        "messages": message_list,
                        "count": len(message_list)
                    }

                # Otherwise, list by project
                if project_id:
                    query = select(Message).where(Message.project_id == project_id)
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
                        return {
                            "success": False,
                            "error": "Project not found"
                        }

                    query = select(Message).where(Message.project_id == project.id)

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
                    # Extract from_agent from meta_data (stored as _from_agent)
                    from_agent = msg.meta_data.get("_from_agent", "unknown") if msg.meta_data else "unknown"

                    # to_agents is already a list in the database
                    to_agents = msg.to_agents if msg.to_agents else []

                    # For backward compatibility, provide to_agent as first recipient
                    to_agent = to_agents[0] if to_agents else None

                    message_list.append({
                        "id": str(msg.id),
                        "from_agent": from_agent,
                        "to_agent": to_agent,  # Single recipient for backward compatibility
                        "to_agents": to_agents,  # Full list
                        "type": msg.message_type,  # Database field is message_type, not type
                        "content": msg.content,
                        "status": msg.status,
                        "priority": msg.priority,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    })

                return {
                    "success": True,
                    "messages": message_list,
                    "count": len(message_list)
                }

        except Exception as e:
            self._logger.exception(f"Failed to list messages: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Message Status Updates
    # ============================================================================

    async def complete_message(
        self,
        message_id: str,
        agent_name: str,
        result: str
    ) -> dict[str, Any]:
        """
        Mark a message as completed with a result.

        Args:
            message_id: Message UUID
            agent_name: Name of agent completing the message
            result: Completion result/response

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.complete_message(
            ...     message_id="msg-123",
            ...     agent_name="impl-1",
            ...     result="Code review completed successfully"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                msg_result = await session.execute(
                    select(Message).where(Message.id == message_id)
                )
                message = msg_result.scalar_one_or_none()

                if not message:
                    return {
                        "success": False,
                        "error": "Message not found"
                    }

                # Update message
                message.status = "completed"
                message.result = result
                message.completed_by = agent_name
                message.completed_at = datetime.now(timezone.utc)

                await session.commit()

                self._logger.info(
                    f"Message {message_id} completed by {agent_name}"
                )

                # Emit WebSocket event if manager is available
                if self._websocket_manager:
                    try:
                        await self._websocket_manager.broadcast_message_update(
                            message_id=message_id,
                            project_id=message.project_id or "",
                            update_type="completed",
                            message_data={"completed_by": agent_name, "status": "completed", "result": result[:100] if result else ""},
                        )
                    except Exception as ws_error:
                        # Log WebSocket errors but don't fail the completion
                        self._logger.warning(
                            f"Failed to emit WebSocket event for message completion {message_id}: {ws_error}"
                        )

                return {
                    "success": True,
                    "message_id": message_id,
                    "completed_by": agent_name,
                }

        except Exception as e:
            self._logger.exception(f"Failed to complete message: {e}")
            return {"success": False, "error": str(e)}

    async def acknowledge_message(
        self,
        message_id: str,
        agent_id: str,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Explicitly acknowledge a message using agent_id (executor).

        Handover 0372: Added from 0366b for explicit acknowledgment workflow.
        Note: receive_messages() auto-acknowledges, so this is optional.

        Args:
            message_id: Message UUID
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.acknowledge_message(
            ...     message_id="msg-123",
            ...     agent_id="agent-uuid-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self._get_session() as session:
                # Get message
                msg_result = await session.execute(
                    select(Message).where(
                        and_(
                            Message.id == message_id,
                            Message.tenant_key == tenant_key
                        )
                    )
                )
                message = msg_result.scalar_one_or_none()

                if not message:
                    return {
                        "success": False,
                        "error": "Message not found or access denied"
                    }

                # Update message
                message.status = "acknowledged"
                message.acknowledged_at = datetime.now(timezone.utc)
                if not message.acknowledged_by:
                    message.acknowledged_by = []
                if agent_id not in message.acknowledged_by:
                    message.acknowledged_by.append(agent_id)

                await session.commit()

                self._logger.info(
                    f"Message {message_id} acknowledged by agent {agent_id}"
                )

                # Update JSONB for UI counter sync
                await self._update_jsonb_message_status(
                    session=session,
                    job_id=agent_id,
                    message_ids=[message_id],
                    new_status="acknowledged"
                )

                # Emit WebSocket event if manager available
                if self._websocket_manager:
                    try:
                        await self._websocket_manager.broadcast_message_acknowledged(
                            message_id=message_id,
                            agent_id=agent_id,
                            tenant_key=tenant_key,
                            project_id=message.project_id,
                            message_ids=[message_id],
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"Failed to emit WebSocket for ack: {ws_error}")

                return {
                    "success": True,
                    "acknowledged": True,
                    "message_id": message_id,
                }

        except Exception as e:
            self._logger.exception(f"Failed to acknowledge message: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Message Persistence to Agent JSONB Column
    # ============================================================================

    async def _persist_message_to_agent_jsonb(
        self,
        session: AsyncSession,
        message_id: str,
        from_agent: str,
        recipient_job_ids: list[str],  # Handover 0372: Now contains agent_ids, not job_ids
        content: str,
        message_type: str,
        priority: str,
        project_id: str,
        tenant_key: str,
    ) -> None:
        """
        Persist message to agent_executions.messages JSONB column for counter persistence.

        Handover 0372: Updated to use AgentExecution instead of AgentJob.

        This ensures message counters survive page refreshes by storing messages
        in the PostgreSQL JSONB column that the frontend reads on load.

        Args:
            session: Active database session
            message_id: Unique message ID
            from_agent: Sender agent name
            recipient_job_ids: List of recipient agent IDs (now agent_ids, not job_ids)
            content: Message content
            message_type: Type of message (direct, broadcast)
            priority: Message priority (low, normal, high)
            project_id: Project ID to scope sender lookup (prevents cross-project issues)
            tenant_key: Tenant key for multi-tenant isolation (Handover 0325)
        """
        from sqlalchemy.orm.attributes import flag_modified

        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            # Add message to SENDER's outbound messages (for "Messages Sent" counter)
            # Handover 0372: Look up AgentExecution, not AgentJob
            from sqlalchemy import and_, or_
            sender_result = await session.execute(
                select(AgentExecution).join(AgentJob).where(
                    and_(
                        AgentExecution.tenant_key == tenant_key,
                        AgentJob.project_id == project_id,
                        or_(
                            AgentExecution.agent_id == from_agent,
                            AgentExecution.agent_type == from_agent
                        )
                    )
                ).limit(1)
            )
            sender_agent = sender_result.scalar_one_or_none()

            if sender_agent:
                if not sender_agent.messages:
                    sender_agent.messages = []

                sender_agent.messages.append({
                    "id": message_id,
                    "from": from_agent,
                    "direction": "outbound",
                    "status": "sent",
                    "text": content[:200],  # Truncate for storage
                    "priority": priority,
                    "timestamp": timestamp,
                    "to_agents": recipient_job_ids,  # Now contains agent_ids
                })

                # CRITICAL: flag_modified() tells SQLAlchemy the JSONB column changed
                flag_modified(sender_agent, "messages")

                self._logger.info(f"[PERSISTENCE] Added outbound message to {from_agent} JSONB column (flagged modified)")

            # Add message to each RECIPIENT's inbound messages (for "Messages Waiting" counter)
            # Skip sender - they already got the outbound copy above
            sender_agent_id = sender_agent.agent_id if sender_agent else None
            for recipient_agent_id in recipient_job_ids:  # Now contains agent_ids
                # Skip sender - don't add inbound message to the sender
                if recipient_agent_id == sender_agent_id:
                    self._logger.debug(
                        f"[PERSISTENCE] Skipping inbound message for sender {recipient_agent_id}"
                    )
                    continue

                # Handover 0372: Look up AgentExecution by agent_id
                recipient_result = await session.execute(
                    select(AgentExecution).join(AgentJob).where(
                        and_(
                            AgentExecution.tenant_key == tenant_key,
                            AgentJob.project_id == project_id,
                            AgentExecution.agent_id == recipient_agent_id
                        )
                    )
                )
                recipient_agent = recipient_result.scalar_one_or_none()

                if recipient_agent:
                    if not recipient_agent.messages:
                        recipient_agent.messages = []

                    recipient_agent.messages.append({
                        "id": message_id,
                        "from": from_agent,
                        "direction": "inbound",
                        "status": "waiting",  # Waiting to be read
                        "text": content[:200],  # Truncate for storage
                        "priority": priority,
                        "timestamp": timestamp,
                    })

                    # CRITICAL: flag_modified() tells SQLAlchemy the JSONB column changed
                    flag_modified(recipient_agent, "messages")

                    self._logger.info(
                        f"[PERSISTENCE] Added inbound message to {recipient_agent.agent_type} "
                        f"({recipient_agent_id}) JSONB column (flagged modified)"
                    )

            # Commit changes to persist JSONB updates
            await session.commit()
            self._logger.info(f"[PERSISTENCE] Committed message {message_id} to database")

        except Exception as e:
            self._logger.error(f"[PERSISTENCE] Failed to persist message to JSONB: {e}")
            # Don't re-raise - message was already saved to messages table

    async def _update_jsonb_message_status(
        self,
        session: AsyncSession,
        job_id: str,
        message_ids: list[str],
        new_status: str,
    ) -> None:
        """
        Update status of messages in AgentJob.messages JSONB column.

        This syncs the JSONB message status with the Message table status,
        ensuring the dashboard counters (Messages Waiting, Messages Read) are accurate.

        Args:
            session: Active database session
            job_id: Job ID (work order) whose JSONB messages to update
            message_ids: List of message IDs to update
            new_status: New status value (e.g., 'acknowledged', 'read')
        """
        from sqlalchemy.orm.attributes import flag_modified

        try:
            # Get the agent job
            result = await session.execute(
                select(AgentJob).where(AgentJob.job_id == job_id)
            )
            agent_job = result.scalar_one_or_none()

            if not agent_job or not agent_job.messages:
                self._logger.debug(f"[JSONB UPDATE] No messages to update for job {job_id}")
                return

            # Update status for matching messages
            updated_count = 0
            message_ids_set = set(message_ids)

            for msg in agent_job.messages:
                if msg.get("id") in message_ids_set and msg.get("status") != new_status:
                    msg["status"] = new_status
                    updated_count += 1

            if updated_count > 0:
                # CRITICAL: flag_modified() tells SQLAlchemy the JSONB column changed
                flag_modified(agent_job, "messages")
                await session.commit()
                self._logger.info(
                    f"[JSONB UPDATE] Updated {updated_count} messages to '{new_status}' "
                    f"for job {job_id}"
                )
            else:
                self._logger.debug(f"[JSONB UPDATE] No messages needed status update for job {job_id}")

        except Exception as e:
            self._logger.error(f"[JSONB UPDATE] Failed to update message status: {e}")
            # Don't re-raise - this is a secondary update
