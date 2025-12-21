"""
MessageService - Agent-ID-based message routing (Handover 0366b).

This service updates message routing to use agent_id (executor) instead of job_id (work).

Key Changes:
- send_message(to_agents=[agent_id]) - Routes to specific executor
- receive_messages(agent_id=...) - Filters by executor agent_id
- Agent type resolution - Resolves "orchestrator" → active execution agent_id
- Multi-tenant isolation - All queries filter by tenant_key

Design Philosophy:
- Messages are sent to EXECUTORS (agent_id), not WORK (job_id)
- Succession: Messages route to NEW executor (active execution)
- Broadcast: Send to ALL active executions in project
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from contextlib import asynccontextmanager

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from giljo_mcp.models.tasks import Message
from giljo_mcp.models.projects import Project
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class MessageService:
    """
    Service for managing inter-agent messages with agent_id routing.

    Handover 0366b: Updated to route messages to agent_id (executor) instead of job_id (work).

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
    # Message Sending (agent_id routing)
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
        Send a message to one or more agent executors.

        Handover 0366b: to_agents now expects agent_id (executor UUIDs) or agent_type strings.

        Args:
            to_agents: List of agent_id (executor UUIDs) or agent_type strings
            content: Message content
            project_id: Project ID this message belongs to
            message_type: Type of message (default: "direct")
            priority: Message priority (default: "normal")
            from_agent: Sender agent_id or agent_type (default: None)
            tenant_key: Tenant key for multi-tenant isolation (required for security)

        Returns:
            Dict with success status and message details or error

        Example:
            >>> # Send to specific executor
            >>> result = await service.send_message(
            ...     to_agents=["agent-uuid-123"],
            ...     content="Review code changes",
            ...     project_id="project-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> # Send to agent type (resolves to active executor)
            >>> result = await service.send_message(
            ...     to_agents=["orchestrator"],
            ...     content="Status update",
            ...     project_id="project-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Get project with tenant isolation filter
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

                # Resolve agent_type strings to agent_id UUIDs
                resolved_to_agents = []
                for agent_ref in to_agents:
                    if len(agent_ref) == 36 and '-' in agent_ref:
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

                # Create message with resolved agent_ids
                message = Message(
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    to_agents=resolved_to_agents,
                    content=content,
                    message_type=message_type,
                    priority=priority,
                    status="pending",
                    meta_data={"_from_agent": from_agent or "system", "project_id": project.id},
                )

                session.add(message)
                await session.commit()

                message_id = str(message.id)

                self._logger.info(
                    f"Sent {message_type} message {message_id} "
                    f"from {from_agent or 'system'} to {resolved_to_agents}"
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

    async def broadcast_to_project(
        self,
        project_id: str,
        content: str,
        from_agent: str = "orchestrator",
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Broadcast a message to all active executions in a project.

        Handover 0366b: Broadcasts to ALL active executions (not jobs).

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
            self._logger.exception(f"Failed to broadcast message: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Message Retrieval (agent_id filtering)
    # ============================================================================

    async def receive_messages(
        self,
        agent_id: str,
        limit: int = 10,
        tenant_key: Optional[str] = None,
        exclude_self: bool = True,
        exclude_progress: bool = True,
        message_types: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """
        Receive pending messages for an agent executor with optional filtering.

        Handover 0366b: Filters by agent_id (executor), NOT job_id (work).
        Handover 0366c: Updated return type to list for test compatibility.
        Handover 0360: Added filtering capabilities (exclude_self, exclude_progress, message_types).

        Args:
            agent_id: Agent execution ID (executor UUID)
            limit: Maximum number of messages to retrieve (default: 10)
            tenant_key: Optional tenant key (uses current if not provided)
            exclude_self: Filter out messages from same agent_id (default: True)
            exclude_progress: Filter out progress-type messages (default: True)
            message_types: Optional allow-list of message types (default: None = all types)

        Returns:
            List of message dicts (empty list on error or no messages)

        Example:
            >>> # Basic usage (with default filters)
            >>> messages = await service.receive_messages(
            ...     agent_id="agent-uuid-123",
            ...     limit=5,
            ...     tenant_key="tenant-abc"
            ... )
            >>> # With custom filters
            >>> messages = await service.receive_messages(
            ...     agent_id="agent-uuid-123",
            ...     exclude_self=False,
            ...     exclude_progress=False,
            ...     message_types=["direct", "broadcast"],
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                self._logger.warning("No tenant context available for receive_messages")
                return []

            async with self._get_session() as session:
                # Retrieve agent execution to verify it exists
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
                    self._logger.warning(f"Execution {agent_id} not found")
                    return []

                # Get job to access project_id
                job_result = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == execution.job_id)
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    self._logger.warning(f"Job {execution.job_id} not found")
                    return []

                # Query messages using native SQLAlchemy queries
                # Include messages where:
                # 1. Direct message to this agent (to_agents contains agent_id as JSON array element)
                # 2. Broadcast message (to_agents contains multiple agent_ids)
                # 3. Only pending messages (unread_only=True by default)
                from sqlalchemy import func
                from sqlalchemy.dialects.postgresql import JSONB

                # Build base query conditions
                conditions = [
                    Message.tenant_key == tenant_key,
                    Message.project_id == job.project_id,
                    Message.status == "pending",  # Only unread messages
                    # Direct message: JSONB array contains agent_id
                    # Use PostgreSQL JSONB containment operator @>
                    func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB))
                ]

                # HANDOVER 0360: Apply filtering conditions

                # Filter: exclude_self - Filter out messages from the same agent
                if exclude_self:
                    # Meta_data._from_agent should not equal current agent_id
                    # Use PostgreSQL JSONB ->> operator to extract _from_agent field
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
                        # Add impossible condition to return no results
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

                # AUTO-ACKNOWLEDGE: Bulk update all retrieved messages to acknowledged status
                if messages:
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

                # Convert to response format
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

                return messages_list

        except Exception as e:
            self._logger.exception(f"Failed to receive messages: {e}")
            return []

    # ============================================================================
    # Message Acknowledgment
    # ============================================================================

    async def acknowledge_message(
        self,
        message_id: str,
        agent_id: str,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Acknowledge a message using agent_id (executor).

        Handover 0366b: Uses agent_id (executor), NOT job_id (work).

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

                return {
                    "success": True,
                    "acknowledged": True,
                    "message_id": message_id,
                }

        except Exception as e:
            self._logger.exception(f"Failed to acknowledge message: {e}")
            return {"success": False, "error": str(e)}
