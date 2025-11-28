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

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize MessageService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
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

                # Create message
                message = Message(
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    to_agents=to_agents,
                    content=content,
                    message_type=message_type,
                    priority=priority,
                    status="pending",
                    meta_data={"_from_agent": from_agent or "orchestrator"},
                )

                session.add(message)
                await session.commit()

                message_id = str(message.id)

                self._logger.info(
                    f"Sent {message_type} message {message_id} "
                    f"from {from_agent or 'orchestrator'} to {to_agents}"
                )

                return {
                    "success": True,
                    "message_id": message_id,
                    "to_agents": to_agents,
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

                # Send message to all agents
                return await self.send_message(
                    to_agents=agent_types,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority=priority,
                    from_agent=from_agent,
                )

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

        This method integrates with AgentMessageQueue for compatibility.

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

            from giljo_mcp.agent_message_queue import AgentMessageQueue

            comm_queue = AgentMessageQueue(self.db_manager)
            async with self.db_manager.get_session_async() as session:
                result = await comm_queue.get_messages(
                    session=session,
                    job_id=agent_id,
                    tenant_key=tenant_key,
                    to_agent=None,
                    message_type=None,
                    unread_only=True,
                )

                if result.get("status") != "success":
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }

                messages = result.get("messages", [])
                if isinstance(limit, int) and limit > 0:
                    messages = messages[:limit]

                return {
                    "success": True,
                    "messages": messages,
                    "count": len(messages)
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
                # If agent_id provided, use communication queue
                if agent_id:
                    from giljo_mcp.agent_message_queue import AgentMessageQueue

                    comm_queue = AgentMessageQueue(self.db_manager)
                    result = await comm_queue.get_messages(
                        session=session,
                        job_id=agent_id,
                        tenant_key=tenant_key or "",
                        to_agent=None,
                        message_type=None,
                        unread_only=False,
                    )

                    if result.get("status") != "success":
                        return {
                            "success": False,
                            "error": result.get("error", "Unknown error")
                        }

                    messages = result.get("messages", [])
                    return {
                        "success": True,
                        "messages": messages,
                        "count": len(messages)
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

    async def acknowledge_message(
        self,
        message_id: str,
        agent_name: str
    ) -> dict[str, Any]:
        """
        Mark a message as acknowledged/received by an agent.

        Args:
            message_id: Message UUID
            agent_name: Name of agent acknowledging

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.acknowledge_message(
            ...     message_id="msg-123",
            ...     agent_name="impl-1"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Message).where(Message.id == message_id)
                )
                message = result.scalar_one_or_none()

                if not message:
                    return {
                        "success": False,
                        "error": "Message not found"
                    }

                # Add to acknowledged_by array
                if not message.acknowledged_by:
                    message.acknowledged_by = []

                if agent_name not in message.acknowledged_by:
                    message.acknowledged_by.append(agent_name)
                    await session.commit()

                self._logger.info(
                    f"Message {message_id} acknowledged by {agent_name}"
                )

                return {
                    "success": True,
                    "message_id": message_id,
                    "acknowledged_by": agent_name,
                }

        except Exception as e:
            self._logger.exception(f"Failed to acknowledge message: {e}")
            return {"success": False, "error": str(e)}

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

                return {
                    "success": True,
                    "message_id": message_id,
                    "completed_by": agent_name,
                }

        except Exception as e:
            self._logger.exception(f"Failed to complete message: {e}")
            return {"success": False, "error": str(e)}
