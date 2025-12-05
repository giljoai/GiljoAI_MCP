"""
INTERNAL/LEGACY: Agent messaging tools for FastMCP/stdio mode.

WARNING: These tools are INTERNAL and should NOT be used by HTTP MCP agents.
HTTP MCP agents should use the canonical tools via MessageService:
- send_message
- receive_messages (auto-acknowledges messages)
- list_messages

This module is retained for:
- Backward compatibility with stdio-based agent tools
- Internal testing and debugging
- Potential future deprecation

See Handover 0295 for the messaging contract.
See Handover 0298 for cleanup decisions.

DO NOT expose these functions via the /mcp HTTP endpoint.

Original Purpose (Handover 0073):
Provides send_mcp_message and read_mcp_messages tools for inter-agent
communication through the message center.

Production-grade features:
- Multi-tenant isolation enforcement
- Comprehensive error handling
- Message status management
- WebSocket event broadcasting
- Type validation and safety checks
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from sqlalchemy import select

from ..models import Job


logger = logging.getLogger(__name__)

# Maximum message content length
MAX_MESSAGE_LENGTH = 10000


async def send_mcp_message(
    job_id: str,
    tenant_key: str,
    content: str,
    target: Literal["orchestrator", "broadcast", "agent"],
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    MCP tool for sending messages through the message center.

    Args:
        job_id: Sender's job ID
        tenant_key: Tenant identifier for multi-tenant isolation
        content: Message content (max 10000 chars)
        target: Where to send ("orchestrator", "broadcast", or "agent")
        agent_id: Target agent job ID (required if target="agent")

    Returns:
        dict: {
            "success": bool,
            "message_id": str (UUID),
            "target": str,
            "broadcast_count": Optional[int],  # If broadcast
            "timestamp": str (ISO format)
        }

    Raises:
        ValueError: If content too long, missing agent_id when target="agent"
        ValueError: If target agent doesn't exist or is in different tenant
        ValueError: If invalid parameters

    Security:
        - Multi-tenant isolation enforced via tenant_key filtering
        - Messages can only be sent within same tenant
        - No cross-tenant messaging possible

    Message Structure:
        Appends to job's messages JSONB array:
        {
            "id": str(uuid4()),
            "from_agent": str,  # Sender's job_id
            "to_agent": Optional[str],  # Target job_id or null for broadcast
            "content": str,
            "timestamp": str (ISO),
            "status": "pending",
            "type": "mcp_message",
            "is_broadcast": bool
        }
    """
    try:
        # Validate input parameters
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"content cannot exceed {MAX_MESSAGE_LENGTH} characters, got: {len(content)}")

        if target not in ("orchestrator", "broadcast", "agent"):
            raise ValueError(f"target must be one of: orchestrator, broadcast, agent. Got: {target}")

        if target == "agent" and not agent_id:
            raise ValueError("agent_id is required when target='agent'")

        # Import database manager and websocket manager
        from api.websocket import websocket_manager

        from ..database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            # Verify sender job exists
            stmt = select(Job).where(Job.job_id == job_id, Job.tenant_key == tenant_key)
            result = await session.execute(stmt)
            sender_job = result.scalar_one_or_none()

            if not sender_job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            # Generate message ID
            message_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)

            # Create base message structure
            message = {
                "id": message_id,
                "from_agent": job_id,
                "content": content,
                "timestamp": timestamp.isoformat(),
                "status": "pending",
                "type": "mcp_message",
                "is_broadcast": False,
            }

            broadcast_count = 0

            if target == "orchestrator":
                # Send to orchestrator
                message["to_agent"] = "orchestrator"

                # Store in sender's messages (for tracking)
                if sender_job.messages is None:
                    sender_job.messages = []
                sender_job.messages.append(message)

            elif target == "broadcast":
                # Broadcast to all jobs in tenant
                message["to_agent"] = None
                message["is_broadcast"] = True

                # Get all jobs in tenant
                stmt = select(Job).where(Job.tenant_key == tenant_key)
                result = await session.execute(stmt)
                all_jobs = result.scalars().all()

                # Add message to all jobs (including sender)
                for job in all_jobs:
                    if job.messages is None:
                        job.messages = []
                    job.messages.append(message.copy())
                    broadcast_count += 1

            elif target == "agent":
                # Send to specific agent
                # Verify target agent exists in same tenant
                stmt = select(Job).where(Job.job_id == agent_id, Job.tenant_key == tenant_key)
                result = await session.execute(stmt)
                target_job = result.scalar_one_or_none()

                if not target_job:
                    raise ValueError(
                        f"Target agent {agent_id} not found for tenant {tenant_key}. "
                        f"Agent may not exist or may be in a different tenant."
                    )

                message["to_agent"] = agent_id

                # Add message to target's messages
                if target_job.messages is None:
                    target_job.messages = []
                target_job.messages.append(message)

            # Commit changes
            await session.commit()

            # Broadcast WebSocket event
            try:
                await websocket_manager.broadcast_job_message(
                    job_id=job_id,
                    message_id=message_id,
                    from_agent=job_id,
                    tenant_key=tenant_key,
                    to_agent=message.get("to_agent"),
                    message_type="mcp_message",
                    content_preview=content[:100],  # First 100 chars
                    timestamp=timestamp,
                )
            except Exception as ws_error:
                logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                # Non-critical - continue without WebSocket broadcast

            logger.info(
                f"[send_mcp_message] Message sent from {job_id} to {target}, "
                f"tenant={tenant_key}, message_id={message_id}"
            )

            result = {
                "success": True,
                "message_id": message_id,
                "target": target,
                "timestamp": timestamp.isoformat(),
            }

            if target == "broadcast":
                result["broadcast_count"] = broadcast_count

            return result

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[send_mcp_message] Error sending message: {e}", exc_info=True)
        raise ValueError(f"Failed to send message: {e!s}")


async def read_mcp_messages(
    job_id: str,
    tenant_key: str,
    unread_only: bool = True,
    limit: int = 10,
    mark_as_read: bool = True,
) -> Dict[str, Any]:
    """
    MCP tool for agents to read their message queue.

    Args:
        job_id: Agent's job ID
        tenant_key: Tenant identifier for multi-tenant isolation
        unread_only: Only return unread messages (default: True)
        limit: Maximum messages to return (1-100, default: 10)
        mark_as_read: Auto-mark returned messages as read (default: True)

    Returns:
        dict: {
            "success": bool,
            "messages": list[dict],  # Message objects
            "unread_count": int,
            "total_count": int
        }

    Raises:
        ValueError: If limit out of range (1-100)
        ValueError: If job doesn't exist or belongs to different tenant

    Security:
        - Multi-tenant isolation enforced via tenant_key filtering
        - Only messages for jobs owned by tenant are returned
        - No cross-tenant message access

    Message Status:
        - Messages marked as "acknowledged" when mark_as_read=True
        - Original status "pending" indicates unread
    """
    try:
        # Validate input parameters
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if limit < 1 or limit > 100:
            raise ValueError(f"limit must be between 1 and 100, got: {limit}")

        # Import database manager
        from ..database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            # Import MCPAgentJob for activity tracking (Handover 0107)
            from ..models import MCPAgentJob

            # Get job with tenant isolation
            stmt = select(Job).where(Job.job_id == job_id, Job.tenant_key == tenant_key)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            # Handover 0107: Update last_message_check_at timestamp for health monitoring
            try:
                agent_job_stmt = select(MCPAgentJob).where(
                    MCPAgentJob.job_id == job_id,
                    MCPAgentJob.tenant_key == tenant_key
                )
                agent_job_result = await session.execute(agent_job_stmt)
                agent_job = agent_job_result.scalar_one_or_none()

                if agent_job:
                    agent_job.last_message_check_at = datetime.now(timezone.utc)
            except Exception as update_error:
                logger.warning(f"Failed to update last_message_check_at for job {job_id}: {update_error}")
                # Non-critical - continue with message retrieval

            # Get messages
            all_messages = job.messages or []

            # Count unread messages
            unread_count = sum(1 for msg in all_messages if msg.get("status") == "pending")

            # Filter messages if unread_only
            if unread_only:
                filtered_messages = [msg for msg in all_messages if msg.get("status") == "pending"]
            else:
                filtered_messages = all_messages

            # Apply limit
            messages_to_return = filtered_messages[:limit]

            # Mark as read if requested
            if mark_as_read and messages_to_return:
                for msg in all_messages:
                    # Mark as acknowledged if it's in the returned set
                    if any(m["id"] == msg["id"] for m in messages_to_return):
                        if msg.get("status") == "pending":
                            msg["status"] = "acknowledged"

                # Update job
                job.messages = all_messages
                await session.commit()

            logger.info(
                f"[read_mcp_messages] Retrieved {len(messages_to_return)} messages "
                f"for job {job_id}, unread={unread_count}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "messages": messages_to_return,
                "unread_count": unread_count,
                "total_count": len(all_messages),
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[read_mcp_messages] Error reading messages: {e}", exc_info=True)
        raise ValueError(f"Failed to read messages: {e!s}")


def register_agent_messaging_tools(server, db_manager, tenant_manager=None):
    """
    Register agent messaging tools with MCP server.

    Args:
        server: MCP server instance with @server.tool() decorator
        db_manager: DatabaseManager instance (not directly used, but kept for consistency)
        tenant_manager: Optional TenantManager instance (not used for these tools)
    """

    @server.tool()
    async def send_mcp_message_tool(
        job_id: str,
        tenant_key: str,
        content: str,
        target: Literal["orchestrator", "broadcast", "agent"],
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send message through the message center.

        Agents use this tool to communicate with the orchestrator, broadcast
        messages to all agents, or send directed messages to specific agents.

        Args:
            job_id: Sender's job ID
            tenant_key: Tenant identifier for multi-tenant isolation
            content: Message content (max 10000 chars)
            target: Message destination (orchestrator, broadcast, agent)
            agent_id: Target agent job ID (required if target="agent")

        Returns:
            Message send result with message_id and timestamp

        Examples:
            Send to orchestrator:
            >>> send_mcp_message_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     content="Need guidance on architecture decision",
            ...     target="orchestrator"
            ... )

            Broadcast to all agents:
            >>> send_mcp_message_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     content="Database migration complete",
            ...     target="broadcast"
            ... )

            Send to specific agent:
            >>> send_mcp_message_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     content="Please review my implementation",
            ...     target="agent",
            ...     agent_id="def-456"
            ... )
        """
        return await send_mcp_message(
            job_id=job_id,
            tenant_key=tenant_key,
            content=content,
            target=target,
            agent_id=agent_id,
        )

    @server.tool()
    async def read_mcp_messages_tool(
        job_id: str,
        tenant_key: str,
        unread_only: bool = True,
        limit: int = 10,
        mark_as_read: bool = True,
    ) -> Dict[str, Any]:
        """
        Read messages from agent's message queue.

        Agents use this tool to retrieve messages sent to them by the orchestrator,
        other agents, or broadcast messages.

        Args:
            job_id: Agent's job ID
            tenant_key: Tenant identifier for multi-tenant isolation
            unread_only: Only return unread messages (default: True)
            limit: Maximum messages to return 1-100 (default: 10)
            mark_as_read: Auto-mark returned messages as read (default: True)

        Returns:
            Messages with unread count and total count

        Examples:
            Read unread messages:
            >>> read_mcp_messages_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     unread_only=True,
            ...     limit=10
            ... )

            Read all messages without marking as read:
            >>> read_mcp_messages_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     unread_only=False,
            ...     limit=50,
            ...     mark_as_read=False
            ... )
        """
        return await read_mcp_messages(
            job_id=job_id,
            tenant_key=tenant_key,
            unread_only=unread_only,
            limit=limit,
            mark_as_read=mark_as_read,
        )

    logger.info("[agent_messaging] Registered agent messaging tools for MCP orchestration")
