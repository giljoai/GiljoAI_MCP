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

from sqlalchemy import case, update
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

    async def batch_update_counters(
        self,
        session: AsyncSession,
        tenant_key: str,
        sent_increments: dict[str, int] | None = None,
        waiting_increments: dict[str, int] | None = None,
    ) -> int:
        """
        Batch-update sent and waiting counters in a single SQL statement.

        Uses a single UPDATE with CASE expressions to touch all affected rows
        atomically. PostgreSQL acquires row locks within one statement, which
        eliminates the cross-statement circular-wait deadlock that occurs with
        N+1 individual UPDATEs.

        Args:
            session: Active database session
            tenant_key: Tenant key for multi-tenant isolation
            sent_increments: {agent_id: increment} for messages_sent_count
            waiting_increments: {agent_id: increment} for messages_waiting_count

        Returns:
            Number of rows affected

        Example:
            >>> await repo.batch_update_counters(
            ...     session=session,
            ...     tenant_key="tenant-abc",
            ...     sent_increments={"agent-1": 1},
            ...     waiting_increments={"agent-2": 1, "agent-3": 1},
            ... )
        """
        sent_increments = sent_increments or {}
        waiting_increments = waiting_increments or {}

        all_agent_ids = set(sent_increments.keys()) | set(waiting_increments.keys())
        if not all_agent_ids:
            return 0

        values: dict = {}

        if sent_increments:
            values["messages_sent_count"] = case(
                *[
                    (AgentExecution.agent_id == agent_id, AgentExecution.messages_sent_count + inc)
                    for agent_id, inc in sent_increments.items()
                ],
                else_=AgentExecution.messages_sent_count,
            )

        if waiting_increments:
            values["messages_waiting_count"] = case(
                *[
                    (AgentExecution.agent_id == agent_id, AgentExecution.messages_waiting_count + inc)
                    for agent_id, inc in waiting_increments.items()
                ],
                else_=AgentExecution.messages_waiting_count,
            )

        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id.in_(all_agent_ids),
                AgentExecution.tenant_key == tenant_key,
            )
            .values(**values)
        )
        result = await session.execute(stmt)

        self._logger.debug(
            "Batch counter update: %d rows affected (sent=%s, waiting=%s)",
            result.rowcount,
            list(sent_increments.keys()),
            list(waiting_increments.keys()),
        )
        return result.rowcount

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
