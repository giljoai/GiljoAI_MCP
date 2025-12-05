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

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import MCPAgentJob, Message, Project
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
        websocket_manager: Optional[Any] = None
    ):
        """
        Initialize MessageService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            websocket_manager: Optional WebSocket manager for real-time event emissions
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

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
    ) -> dict[str, Any]:
        """
        Send a message to one or more agents.

        Args:
            to_agents: List of agent names to send to
            content: Message content
            project_id: Project ID this message belongs to
            message_type: Type of message (default: "direct")
            priority: Message priority (default: "normal")
            from_agent: Sender agent name (default: "orchestrator")

        Returns:
            Dict with success status and message details or error

        Example:
            >>> result = await service.send_message(
            ...     to_agents=["impl-1", "analyzer-1"],
            ...     content="Review code changes",
            ...     project_id="project-123",
            ...     priority="high"
            ... )
            >>> print(result["message_id"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Get project
                result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                # Resolve agent_type strings to job_id UUIDs before storing
                # This ensures receive_messages (MCP over HTTP) can find messages by job_id
                resolved_to_agents = []
                for agent_ref in to_agents:
                    if agent_ref == 'all':
                        # Broadcast - keep as-is, receive_messages handles 'all' specially
                        resolved_to_agents.append('all')
                    elif len(agent_ref) == 36 and '-' in agent_ref:
                        # Already a UUID (job_id) - use directly
                        resolved_to_agents.append(agent_ref)
                    else:
                        # Agent type string (e.g., "orchestrator") - resolve to job_id
                        agent_result = await session.execute(
                            select(MCPAgentJob).where(
                                MCPAgentJob.project_id == project_id,
                                MCPAgentJob.agent_type == agent_ref
                            ).limit(1)
                        )
                        agent_job = agent_result.scalar_one_or_none()
                        if agent_job:
                            resolved_to_agents.append(agent_job.job_id)
                            self._logger.info(
                                f"[RESOLVER] Resolved '{agent_ref}' to job_id '{agent_job.job_id}'"
                            )
                        else:
                            # Could not resolve - keep original (will fail to deliver)
                            resolved_to_agents.append(agent_ref)
                            self._logger.warning(
                                f"[RESOLVER] Could not resolve agent_type '{agent_ref}' in project {project_id}"
                            )

                # Create message with resolved job_ids
                message = Message(
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    to_agents=resolved_to_agents,
                    content=content,
                    message_type=message_type,
                    priority=priority,
                    status="pending",
                    # Store project_id as job_id for WebSocket consumers that key off job_id/project_id.
                    meta_data={"_from_agent": from_agent or "orchestrator", "job_id": project.id},
                )

                session.add(message)
                await session.commit()

                message_id = str(message.id)

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

                        # Event 1: Broadcast to SENDER (increments "Messages Sent")
                        await self._websocket_manager.broadcast_message_sent(
                            message_id=message_id,
                            job_id=message.meta_data.get("job_id", ""),
                            project_id=project.id,
                            tenant_key=project.tenant_key,
                            from_agent=from_agent or "orchestrator",
                            to_agent=to_agent_value,
                            message_type=message_type,
                            content_preview=content[:200] if content else "",
                            priority={"low": 0, "normal": 1, "high": 2}.get(priority, 1),
                        )
                        self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_sent {message_id}")

                        # Event 2: Broadcast to RECIPIENT(S) (increments "Messages Waiting")
                        # Determine recipient job IDs
                        recipient_job_ids = []
                        if to_agents[0] == 'all':
                            # Broadcast: Get ALL agent job IDs in the project
                            result = await session.execute(
                                select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                            )
                            all_agents = result.scalars().all()
                            recipient_job_ids = [agent.job_id for agent in all_agents]
                            self._logger.info(f"[WEBSOCKET DEBUG] Broadcast to all: {len(recipient_job_ids)} recipients")
                        else:
                            # Direct message: Resolve agent_type to job_id if needed
                            # to_agents can contain job_ids (UUIDs) or agent_types (like "analyzer")
                            resolved_job_ids = []
                            for agent_ref in to_agents:
                                # Check if this looks like a UUID (job_id) or an agent_type
                                # UUIDs contain hyphens and are 36 chars, agent_types are short names
                                if len(agent_ref) == 36 and '-' in agent_ref:
                                    # Looks like a job_id UUID - use directly
                                    resolved_job_ids.append(agent_ref)
                                else:
                                    # Looks like an agent_type - resolve to job_id
                                    agent_result = await session.execute(
                                        select(MCPAgentJob).where(
                                            MCPAgentJob.project_id == project.id,
                                            MCPAgentJob.agent_type == agent_ref
                                        ).limit(1)
                                    )
                                    agent_job = agent_result.scalar_one_or_none()
                                    if agent_job:
                                        resolved_job_ids.append(agent_job.job_id)
                                        self._logger.info(
                                            f"[WEBSOCKET DEBUG] Resolved agent_type '{agent_ref}' "
                                            f"to job_id '{agent_job.job_id}'"
                                        )
                                    else:
                                        # Couldn't resolve - keep original for logging
                                        resolved_job_ids.append(agent_ref)
                                        self._logger.warning(
                                            f"[WEBSOCKET DEBUG] Could not resolve agent_type '{agent_ref}' "
                                            f"to job_id in project {project.id}"
                                        )
                            recipient_job_ids = resolved_job_ids
                            self._logger.info(f"[WEBSOCKET DEBUG] Direct message to: {recipient_job_ids}")

                        # Emit message:received event to recipients
                        if recipient_job_ids:
                            await self._websocket_manager.broadcast_message_received(
                                message_id=message_id,
                                job_id=message.meta_data.get("job_id", ""),
                                project_id=project.id,
                                tenant_key=project.tenant_key,
                                from_agent=from_agent or "orchestrator",
                                to_agent_ids=recipient_job_ids,
                                message_type=message_type,
                                content_preview=content[:200] if content else "",
                                priority={"low": 0, "normal": 1, "high": 2}.get(priority, 1),
                            )
                            self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_received to {len(recipient_job_ids)} recipient(s)")

                        # CRITICAL: Persist messages to mcp_agent_jobs.messages JSONB column for counter persistence
                        # This ensures counters survive page refresh
                        await self._persist_message_to_agent_jsonb(
                            session=session,
                            message_id=message_id,
                            from_agent=from_agent or "orchestrator",
                            recipient_job_ids=recipient_job_ids,
                            content=content,
                            message_type=message_type,
                            priority=priority,
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
                    select(MCPAgentJob).where(MCPAgentJob.project_id == project_id)
                )
                agent_jobs = result.scalars().all()

                if not agent_jobs:
                    return {
                        "success": False,
                        "error": "No agent jobs found in project"
                    }

                agent_types = [job.agent_type for job in agent_jobs]

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
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Receive pending messages for an agent by job_id.

        Uses native Message queries (NOT AgentMessageQueue which has broken SQL).

        Args:
            agent_id: Agent job ID
            limit: Maximum number of messages to retrieve (default: 10)
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status and list of messages or error

        Example:
            >>> result = await service.receive_messages(
            ...     agent_id="job-123",
            ...     limit=5
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
                # Retrieve agent job to get project context
                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == agent_id,
                            MCPAgentJob.tenant_key == tenant_key
                        )
                    )
                )
                job = result.scalar_one_or_none()

                if not job:
                    return {
                        "success": False,
                        "error": f"Job {agent_id} not found"
                    }

                # Query messages using native SQLAlchemy queries
                # Include messages where:
                # 1. Direct message to this agent (to_agents contains agent_id as JSON array element)
                # 2. Broadcast message (to_agents contains 'all')
                # 3. Only pending messages (unread_only=True by default)
                from sqlalchemy import or_, func
                from sqlalchemy.dialects.postgresql import JSONB

                query = select(Message).where(
                    and_(
                        Message.tenant_key == tenant_key,
                        Message.project_id == job.project_id,
                        Message.status == "pending",  # Only unread messages
                        or_(
                            # Direct message: JSONB array contains agent_id
                            # Use PostgreSQL JSONB containment operator @>
                            # Cast both sides to JSONB to avoid type mismatch
                            func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
                            # Broadcast: JSONB array contains 'all'
                            func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB))
                        )
                    )
                ).order_by(Message.created_at)

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

                    # Emit WebSocket events for UI update (Handover 0326)
                    if self._websocket_manager:
                        for msg in messages:
                            try:
                                await self._websocket_manager.broadcast_message_update(
                                    message_id=str(msg.id),
                                    project_id=str(msg.project_id),
                                    update_type="acknowledged",
                                    message_data={
                                        "from_agent": msg.meta_data.get("_from_agent", "") if msg.meta_data else "",
                                        "to_agents": msg.to_agents,
                                        "status": "acknowledged",
                                        "acknowledged_by": msg.acknowledged_by,
                                        "acknowledged_at": msg.acknowledged_at.isoformat() if msg.acknowledged_at else None,
                                    }
                                )
                            except Exception as e:
                                self._logger.warning(f"Failed to emit WebSocket for message {msg.id}: {e}")

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
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List messages in a project or for a specific agent.

        Uses native Message queries (NOT AgentMessageQueue which has broken SQL).

        Args:
            project_id: Optional project ID filter
            status: Optional message status filter
            agent_id: Optional agent job ID filter
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status and list of messages or error

        Example:
            >>> result = await service.list_messages(
            ...     project_id="project-123",
            ...     status="pending"
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
                    conditions = [MCPAgentJob.job_id == agent_id]
                    if tenant_key:
                        conditions.append(MCPAgentJob.tenant_key == tenant_key)

                    result = await session.execute(
                        select(MCPAgentJob).where(and_(*conditions))
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

    # ============================================================================
    # Message Persistence to Agent JSONB Column
    # ============================================================================

    async def _persist_message_to_agent_jsonb(
        self,
        session: AsyncSession,
        message_id: str,
        from_agent: str,
        recipient_job_ids: list[str],
        content: str,
        message_type: str,
        priority: str,
    ) -> None:
        """
        Persist message to mcp_agent_jobs.messages JSONB column for counter persistence.

        This ensures message counters survive page refreshes by storing messages
        in the PostgreSQL JSONB column that the frontend reads on load.

        Args:
            session: Active database session
            message_id: Unique message ID
            from_agent: Sender agent name
            recipient_job_ids: List of recipient agent job IDs
            content: Message content
            message_type: Type of message (direct, broadcast)
            priority: Message priority (low, normal, high)
        """
        from sqlalchemy.orm.attributes import flag_modified
        from src.giljo_mcp.models.agents import MCPAgentJob

        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            # Add message to SENDER's outbound messages (for "Messages Sent" counter)
            # Find sender agent (usually orchestrator)
            sender_result = await session.execute(
                select(MCPAgentJob).where(
                    MCPAgentJob.agent_type == from_agent
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
                    "to_agents": recipient_job_ids,
                })

                # CRITICAL: flag_modified() tells SQLAlchemy the JSONB column changed
                # Without this, SQLAlchemy won't detect the append() and won't save changes!
                flag_modified(sender_agent, "messages")

                self._logger.info(f"[PERSISTENCE] Added outbound message to {from_agent} JSONB column (flagged modified)")

            # Add message to each RECIPIENT's inbound messages (for "Messages Waiting" counter)
            for recipient_job_id in recipient_job_ids:
                recipient_result = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == recipient_job_id
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
                        f"({recipient_job_id}) JSONB column (flagged modified)"
                    )

            # Commit changes to persist JSONB updates
            await session.commit()
            self._logger.info(f"[PERSISTENCE] Committed message {message_id} to database")

        except Exception as e:
            self._logger.error(f"[PERSISTENCE] Failed to persist message to JSONB: {e}")
            # Don't re-raise - message was already saved to messages table
