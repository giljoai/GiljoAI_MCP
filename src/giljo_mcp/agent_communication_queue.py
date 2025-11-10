"""
Agent Communication Queue for GiljoAI MCP.

Handover 0019: JSONB-based message queue for agent-to-agent communication.
Messages are stored in Job.messages JSONB array for atomic operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .database import DatabaseManager
from .models import Job


class AgentCommunicationQueue:
    """
    Agent Communication Queue - manages messages in Job.messages JSONB field.

    Features:
    - JSONB-based message storage for PostgreSQL performance
    - Multi-tenant isolation
    - Message acknowledgment tracking
    - Priority-based message handling (0=low, 1=normal, 2=high)
    - Broadcast and direct messaging
    - Atomic JSONB operations

    Message Object Structure:
    {
        "id": str (UUID),
        "from_agent": str,
        "to_agent": Optional[str],  # None for broadcast
        "type": str,
        "content": str,
        "priority": int (0-2),
        "acknowledged": bool,
        "acknowledged_at": Optional[str ISO datetime],
        "acknowledged_by": Optional[str],
        "timestamp": str (ISO datetime),
        "metadata": dict
    }
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize AgentCommunicationQueue.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager

    async def send_message(
        self,
        session: AsyncSession,
        job_id: str,
        tenant_key: str,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        content: str,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to the job's message queue.

        Args:
            session: Database session
            job_id: Job ID to send message to
            tenant_key: Tenant key for isolation
            from_agent: Agent sending the message
            to_agent: Agent receiving the message (None for broadcast)
            message_type: Type of message (task, info, error, etc.)
            content: Message content
            priority: Message priority (0=low, 1=normal, 2=high)
            metadata: Optional metadata dict

        Returns:
            Dict with status and message_id or error
        """
        try:
            # Validate priority
            if priority not in [0, 1, 2]:
                return {"status": "error", "error": "Priority must be 0 (low), 1 (normal), or 2 (high)"}

            # Validate content
            if not content or not content.strip():
                return {"status": "error", "error": "Message content cannot be empty"}

            # Retrieve job
            result = await session.execute(select(Job).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Create message object
            message = self._create_message_object(
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=message_type,
                content=content,
                priority=priority,
                metadata=metadata,
            )

            # Append to JSONB array
            self._update_job_messages(job, message)

            # Mark field as modified for SQLAlchemy tracking
            try:
                flag_modified(job, "messages")
            except AttributeError:
                # Handle mock objects in tests that don't have _sa_instance_state
                pass

            await session.commit()

            return {"status": "success", "message_id": message["id"]}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def send_message_batch(
        self, session: AsyncSession, job_id: str, tenant_key: str, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple messages to the job's message queue.

        Args:
            session: Database session
            job_id: Job ID to send messages to
            tenant_key: Tenant key for isolation
            messages: List of message dicts with keys:
                - from_agent: str
                - to_agent: Optional[str]
                - type: str
                - content: str
                - priority: int (0-2)
                - metadata: Optional[dict]

        Returns:
            Dict with status and sent_count or error
        """
        try:
            # Retrieve job
            result = await session.execute(select(Job).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Create and append all messages
            sent_count = 0
            for msg_data in messages:
                message = self._create_message_object(
                    from_agent=msg_data.get("from_agent"),
                    to_agent=msg_data.get("to_agent"),
                    message_type=msg_data.get("type"),
                    content=msg_data.get("content"),
                    priority=msg_data.get("priority", 1),
                    metadata=msg_data.get("metadata"),
                )

                self._update_job_messages(job, message)
                sent_count += 1

            # Mark field as modified
            try:
                flag_modified(job, "messages")
            except AttributeError:
                # Handle mock objects in tests
                pass

            await session.commit()

            return {"status": "success", "sent_count": sent_count}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_messages(
        self,
        session: AsyncSession,
        job_id: str,
        tenant_key: str,
        to_agent: Optional[str] = None,
        message_type: Optional[str] = None,
        unread_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve messages from the job's message queue with optional filters.

        Args:
            session: Database session
            job_id: Job ID to retrieve messages from
            tenant_key: Tenant key for isolation
            to_agent: Filter by recipient agent
            message_type: Filter by message type
            unread_only: Only return unacknowledged messages

        Returns:
            Dict with status and messages list or error
        """
        try:
            # Retrieve job
            result = await session.execute(select(Job).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Filter messages
            messages = job.messages or []
            filtered_messages = []

            for msg in messages:
                # Apply filters
                if to_agent and msg.get("to_agent") != to_agent:
                    continue
                if message_type and msg.get("type") != message_type:
                    continue
                if unread_only and msg.get("acknowledged", False):
                    continue

                filtered_messages.append(msg)

            return {"status": "success", "messages": filtered_messages}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_unread_count(
        self, session: AsyncSession, job_id: str, tenant_key: str, to_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get count of unread messages.

        Args:
            session: Database session
            job_id: Job ID to count messages from
            tenant_key: Tenant key for isolation
            to_agent: Optional filter by recipient agent

        Returns:
            Dict with status and unread_count or error
        """
        try:
            # Retrieve job
            result = await session.execute(select(Job).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Count unread messages
            messages = job.messages or []
            unread_count = 0

            for msg in messages:
                # Apply filters
                if to_agent and msg.get("to_agent") != to_agent:
                    continue
                if not msg.get("acknowledged", False):
                    unread_count += 1

            return {"status": "success", "unread_count": unread_count}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def acknowledge_message(
        self, session: AsyncSession, job_id: str, tenant_key: str, message_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """
        Acknowledge a message.

        Args:
            session: Database session
            job_id: Job ID containing the message
            tenant_key: Tenant key for isolation
            message_id: Message ID to acknowledge
            agent_id: Agent acknowledging the message

        Returns:
            Dict with status or error
        """
        try:
            # Retrieve job
            result = await session.execute(select(Job).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Find message
            messages = job.messages or []
            message_found = False

            for msg in messages:
                if msg.get("id") == message_id:
                    message_found = True

                    # Check if already acknowledged
                    if msg.get("acknowledged", False):
                        return {"status": "error", "error": "Message already acknowledged"}

                    # Update message
                    msg["acknowledged"] = True
                    msg["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                    msg["acknowledged_by"] = agent_id

                    break

            if not message_found:
                return {"status": "error", "error": f"Message {message_id} not found"}

            # Mark field as modified
            try:
                flag_modified(job, "messages")
            except AttributeError:
                # Handle mock objects in tests
                pass

            await session.commit()

            return {"status": "success"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def acknowledge_all_messages(
        self, session: AsyncSession, job_id: str, tenant_key: str, agent_id: str, to_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Acknowledge all unread messages for an agent.

        Args:
            session: Database session
            job_id: Job ID containing messages
            tenant_key: Tenant key for isolation
            agent_id: Agent acknowledging messages
            to_agent: Optional filter by recipient agent

        Returns:
            Dict with status and acknowledged_count or error
        """
        try:
            # Retrieve job
            result = await session.execute(select(Job).filter_by(job_id=job_id, tenant_key=tenant_key))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Verify tenant isolation
            if job.tenant_key != tenant_key:
                return {"status": "error", "error": "Tenant key mismatch - access denied"}

            # Acknowledge messages
            messages = job.messages or []
            acknowledged_count = 0

            for msg in messages:
                # Apply filters
                if to_agent and msg.get("to_agent") != to_agent:
                    continue
                if msg.get("acknowledged", False):
                    continue

                # Acknowledge message
                msg["acknowledged"] = True
                msg["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                msg["acknowledged_by"] = agent_id
                acknowledged_count += 1

            # Mark field as modified
            try:
                flag_modified(job, "messages")
            except AttributeError:
                # Handle mock objects in tests
                pass

            await session.commit()

            return {"status": "success", "acknowledged_count": acknowledged_count}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _create_message_object(
        self,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        content: str,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a message object with required structure.

        Args:
            from_agent: Agent sending the message
            to_agent: Agent receiving the message (None for broadcast)
            message_type: Type of message
            content: Message content
            priority: Message priority (0-2)
            metadata: Optional metadata

        Returns:
            Message dict
        """
        return {
            "id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "type": message_type,
            "content": content,
            "priority": priority,
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

    def _update_job_messages(self, job: Job, message: Dict[str, Any]) -> None:
        """
        Append message to job's messages JSONB array.

        Args:
            job: Job instance
            message: Message dict to append
        """
        if job.messages is None:
            job.messages = []

        # Ensure we're working with a mutable list
        messages = list(job.messages)
        messages.append(message)
        job.messages = messages
