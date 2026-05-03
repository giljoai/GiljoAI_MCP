# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from typing import Any

from sqlalchemy import and_, case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.models import Message, Project
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.tasks import MessageRecipient


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
    ) -> dict | None:
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

    # ============================================================================
    # Routing / Write Operations (BE-5022c)
    # ============================================================================

    async def get_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """
        Get a project by ID with tenant isolation.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            Project instance or None
        """
        result = await session.execute(
            select(Project).where(
                and_(
                    Project.tenant_key == tenant_key,
                    Project.id == project_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def resolve_broadcast_recipients(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[AgentExecution]:
        """
        Get active agent executions for broadcast (waiting/working/blocked).

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            List of AgentExecution instances
        """
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
        return list(result.scalars().all())

    async def resolve_agent_by_display_name(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        agent_display_name: str,
    ) -> AgentExecution | None:
        """
        Resolve agent display name to latest active execution.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            agent_display_name: Display name to resolve

        Returns:
            AgentExecution instance or None
        """
        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.agent_display_name == agent_display_name,
                    AgentExecution.status.in_(["waiting", "working", "blocked", "complete"]),
                    AgentExecution.tenant_key == tenant_key,
                )
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def resolve_sender_display_name(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        from_agent: str,
    ) -> str | None:
        """
        Resolve sender agent reference to display name.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            from_agent: Sender agent reference (display name or agent_id)

        Returns:
            Display name string or None
        """
        result = await session.execute(
            select(AgentExecution.agent_display_name)
            .join(AgentJob)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.tenant_key == tenant_key,
                    (AgentExecution.agent_display_name == from_agent) | (AgentExecution.agent_id == from_agent),
                )
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_sender_execution(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        sender_ref: str,
    ) -> AgentExecution | None:
        """
        Find the sender's AgentExecution by display name or agent_id.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            sender_ref: Sender reference (display name or agent_id)

        Returns:
            AgentExecution instance or None
        """
        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.tenant_key == tenant_key,
                    (AgentExecution.agent_display_name == sender_ref) | (AgentExecution.agent_id == sender_ref),
                )
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def persist_message_with_recipient(
        self,
        session: AsyncSession,
        message: Message,
        recipient_id: str,
    ) -> None:
        """
        Persist a Message and its MessageRecipient row.

        Args:
            session: Active database session
            message: Message instance to persist
            recipient_id: Recipient agent_id
        """
        session.add(message)
        await session.flush()
        session.add(
            MessageRecipient(
                message_id=message.id,
                agent_id=recipient_id,
                tenant_key=message.tenant_key,
            )
        )

    async def flush(self, session: AsyncSession) -> None:
        """Flush pending changes."""
        await session.flush()

    async def commit(self, session: AsyncSession) -> None:
        """Commit the current transaction."""
        await session.commit()

    async def get_execution_by_agent_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_id: str,
    ) -> AgentExecution | None:
        """
        Get latest execution by agent_id.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            agent_id: Agent UUID

        Returns:
            AgentExecution instance or None
        """
        result = await session.execute(
            select(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_agent_job_by_job_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentJob | None:
        """
        Get agent job by job_id with tenant isolation.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            AgentJob instance or None
        """
        result = await session.execute(
            select(AgentJob).where(
                AgentJob.job_id == job_id,
                AgentJob.tenant_key == tenant_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_agent_job_ids_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[AgentJob]:
        """
        Get all agent jobs for a project.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            List of AgentJob instances
        """
        result = await session.execute(
            select(AgentJob).where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
        )
        return list(result.scalars().all())

    async def refresh_execution(
        self,
        session: AsyncSession,
        execution: AgentExecution,
    ) -> None:
        """
        Refresh an AgentExecution from the database.

        Args:
            session: Active database session
            execution: AgentExecution instance to refresh
        """
        await session.refresh(execution)

    async def get_job_id_and_project_for_execution(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> Any:
        """
        Get job_id and project_id for a given job.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            Row with job_id, project_id or None
        """
        result = await session.execute(
            select(AgentJob.job_id, AgentJob.project_id).where(
                AgentJob.job_id == job_id,
                AgentJob.tenant_key == tenant_key,
            )
        )
        return result.first()

    # ========================================================================
    # Message queries (BE-5022d: moved from message_service.py)
    # ========================================================================

    async def execute_query(
        self,
        session: AsyncSession,
        query,
    ) -> list:
        """
        Execute a pre-built message query and return scalar results.

        Args:
            session: Active database session
            query: SQLAlchemy select statement

        Returns:
            List of ORM instances
        """
        result = await session.execute(query)
        return list(result.scalars().all())

    async def execute_ack_stmt(
        self,
        session: AsyncSession,
        stmt,
    ) -> None:
        """
        Execute a statement (e.g., acknowledgment insert).

        Args:
            session: Active database session
            stmt: SQLAlchemy statement to execute
        """
        await session.execute(stmt)

    async def execute_update_stmt(
        self,
        session: AsyncSession,
        stmt,
    ) -> int:
        """
        Execute an update statement and return affected row count.

        Args:
            session: Active database session
            stmt: SQLAlchemy update statement

        Returns:
            Number of rows affected
        """
        result = await session.execute(stmt)
        return result.rowcount

    async def count_pending_messages(
        self,
        session: AsyncSession,
        query,
    ) -> int:
        """
        Execute a count query for pending messages.

        Args:
            session: Active database session
            query: SQLAlchemy count select statement

        Returns:
            Count result
        """
        result = await session.execute(query)
        return result.scalar() or 0

    async def get_message_by_id(
        self,
        session: AsyncSession,
        message_id: str,
        tenant_key: str,
    ) -> Message | None:
        """
        Get a message by ID with tenant isolation.

        Args:
            session: Active database session
            message_id: Message UUID
            tenant_key: Tenant key for isolation

        Returns:
            Message ORM instance or None
        """
        stmt = select(Message).where(and_(Message.id == message_id, Message.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_message_with_relations(
        self,
        session: AsyncSession,
        message_id: str,
        tenant_key: str,
    ) -> Message | None:
        """
        Get a message with all relationships loaded.

        Args:
            session: Active database session
            message_id: Message UUID
            tenant_key: Tenant key for isolation

        Returns:
            Message ORM instance or None
        """
        from sqlalchemy.orm import selectinload

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
        return result.scalar_one_or_none()

    async def resolve_sender_names_batch(
        self,
        session: AsyncSession,
        agent_ids: list[str],
        tenant_key: str,
    ) -> dict[str, str]:
        """
        Batch-resolve sender display names from agent IDs.

        Args:
            session: Active database session
            agent_ids: List of agent UUID strings
            tenant_key: Tenant key for isolation

        Returns:
            Dict mapping agent_id to display name
        """
        if not agent_ids:
            return {}
        result = await session.execute(
            select(AgentExecution.agent_id, AgentExecution.agent_display_name).where(
                AgentExecution.agent_id.in_(agent_ids),
                AgentExecution.tenant_key == tenant_key,
            )
        )
        return {row.agent_id: row.agent_display_name for row in result}

    async def get_active_project(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> Project | None:
        """
        Get the active project for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            Project ORM instance or None
        """
        result = await session.execute(
            select(Project).where(and_(Project.tenant_key == tenant_key, Project.status == ProjectStatus.ACTIVE))
        )
        return result.scalar_one_or_none()

    async def get_latest_project(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> Project | None:
        """
        Get the most recent project for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            Project ORM instance or None
        """
        result = await session.execute(
            select(Project).where(Project.tenant_key == tenant_key).order_by(Project.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()
