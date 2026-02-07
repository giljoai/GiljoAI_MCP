"""
MessageRepository - Data access layer for message counter operations

Handover 0387f: Repository for counter-based message persistence.
Provides atomic counter updates for message tracking without JSONB.

Responsibilities:
- Increment/decrement message counters on AgentExecution
- Atomic operations for message statistics
- Multi-tenant isolation

Design Principles:
- Single Responsibility: Only counter operations
- Atomic Updates: Use SQL UPDATE with arithmetic
- Testability: Can be unit tested independently
"""

import logging
from typing import Optional

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution


logger = logging.getLogger(__name__)


class MessageRepository:
    """
    Repository for message counter operations.

    Provides atomic counter updates for message tracking without JSONB persistence.
    """

    def __init__(self):
        """Initialize MessageRepository."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def increment_sent_count(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
        increment: int = 1,
    ) -> None:
        """
        Increment messages_sent_count for an agent.

        Args:
            session: Active database session
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation
            increment: Amount to increment by (default: 1)

        Example:
            >>> await repo.increment_sent_count(
            ...     session=session,
            ...     agent_id="agent-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .values(messages_sent_count=AgentExecution.messages_sent_count + increment)
        )
        result = await session.execute(stmt)

        if result.rowcount == 0:
            self._logger.warning(f"No agent found for agent_id={agent_id}, tenant_key={tenant_key}")
        else:
            self._logger.debug(f"Incremented sent_count for agent {agent_id} by {increment}")

    async def increment_waiting_count(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
        increment: int = 1,
    ) -> None:
        """
        Increment messages_waiting_count for an agent.

        Args:
            session: Active database session
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation
            increment: Amount to increment by (default: 1)

        Example:
            >>> await repo.increment_waiting_count(
            ...     session=session,
            ...     agent_id="agent-456",
            ...     tenant_key="tenant-abc"
            ... )
        """
        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .values(messages_waiting_count=AgentExecution.messages_waiting_count + increment)
        )
        result = await session.execute(stmt)

        if result.rowcount == 0:
            self._logger.warning(f"No agent found for agent_id={agent_id}, tenant_key={tenant_key}")
        else:
            self._logger.debug(f"Incremented waiting_count for agent {agent_id} by {increment}")

    async def decrement_waiting_increment_read(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
    ) -> None:
        """
        Atomically decrement waiting_count and increment read_count.

        This is used when a message is acknowledged - it moves from "waiting" to "read".

        Args:
            session: Active database session
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation

        Example:
            >>> await repo.decrement_waiting_increment_read(
            ...     session=session,
            ...     agent_id="agent-456",
            ...     tenant_key="tenant-abc"
            ... )
        """
        # Use a single UPDATE statement to ensure atomicity
        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .values(
                # Handover 0422-fix: Use func.greatest to prevent negative counters
                messages_waiting_count=func.greatest(0, AgentExecution.messages_waiting_count - 1),
                messages_read_count=AgentExecution.messages_read_count + 1,
            )
        )
        result = await session.execute(stmt)

        if result.rowcount == 0:
            self._logger.warning(f"No agent found for agent_id={agent_id}, tenant_key={tenant_key}")
        else:
            self._logger.debug(f"Decremented waiting_count and incremented read_count for agent {agent_id}")

    async def get_counter_stats(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
    ) -> Optional[dict]:
        """
        Get current counter values for an agent.

        Utility method for debugging and testing.

        Args:
            session: Active database session
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with counter values or None if agent not found

        Example:
            >>> stats = await repo.get_counter_stats(
            ...     session=session,
            ...     agent_id="agent-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(stats["sent"])  # 5
        """
        from sqlalchemy import select

        stmt = select(AgentExecution).where(
            AgentExecution.agent_id == agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            return None

        return {
            "sent": agent.messages_sent_count or 0,
            "waiting": agent.messages_waiting_count or 0,
            "read": agent.messages_read_count or 0,
        }
