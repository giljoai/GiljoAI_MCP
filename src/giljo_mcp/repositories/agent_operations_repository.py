# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent operations repository for auxiliary agent queries.

BE-5022d: Extracted from AgentJobRepository to keep files under 800 lines.
Contains operations for: heartbeat, silence detection, workflow status,
orchestration service, and job query service.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.models import AgentTodoItem, Message
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.settings import Settings
from giljo_mcp.models.tasks import MessageRecipient


class AgentOperationsRepository:
    """Repository for auxiliary agent operations.

    Provides database operations for heartbeat tracking, silence detection,
    workflow status queries, pending job queries, and job listing.
    """

    # ============================================================================
    # Heartbeat operations
    # ============================================================================

    async def touch_heartbeat(
        self,
        session: AsyncSession,
        job_id: str,
        tenant_key: str,
        debounce_seconds: int = 30,
    ) -> bool:
        """Update last_activity_at with debounce.

        Args:
            session: Async database session
            job_id: AgentJob ID
            tenant_key: Tenant key for isolation
            debounce_seconds: Minimum seconds between updates

        Returns:
            True if update was performed, False if debounced
        """
        now = datetime.now(UTC)
        threshold = now - timedelta(seconds=debounce_seconds)

        conditions = [
            AgentExecution.job_id == job_id,
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.status.notin_(["complete", "closed", "decommissioned"]),
            ((AgentExecution.last_activity_at.is_(None)) | (AgentExecution.last_activity_at < threshold)),
        ]

        result = await session.execute(update(AgentExecution).where(and_(*conditions)).values(last_activity_at=now))
        if result.rowcount:
            await session.flush()
            return True
        return False

    # ============================================================================
    # SilenceDetector operations
    # ============================================================================

    async def find_stale_working_agents(
        self,
        session: AsyncSession,
        cutoff: datetime,
    ) -> list[AgentExecution]:
        """Find working agents that have gone silent (cross-tenant scan).

        TENANT ISOLATION NOTE: This intentionally scans ALL tenants.
        The silence detector is a system-wide background health monitor.

        Args:
            session: Async database session
            cutoff: Datetime threshold; agents inactive since before this are stale

        Returns:
            List of stale AgentExecution instances with eager-loaded job/project
        """
        stmt = (
            select(AgentExecution)
            .options(selectinload(AgentExecution.job).selectinload(AgentJob.project))
            .where(
                AgentExecution.status == "working",
                or_(
                    AgentExecution.last_progress_at < cutoff,
                    and_(
                        AgentExecution.last_progress_at.is_(None),
                        AgentExecution.started_at < cutoff,
                    ),
                ),
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def mark_agents_silent(
        self,
        session: AsyncSession,
        agents: list[AgentExecution],
    ) -> None:
        """Mark a list of agents as silent and flush.

        Args:
            session: Async database session
            agents: List of AgentExecution instances to mark silent
        """
        for agent in agents:
            agent.status = "silent"
        if agents:
            await session.flush()

    async def find_silent_agent_with_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> tuple[AgentExecution | None, str | None]:
        """Find a silent agent by job_id and return with project_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            Tuple of (AgentExecution or None, project_id or None)
        """
        stmt = (
            select(AgentExecution, AgentJob.project_id)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "silent",
            )
        )
        result = await session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None, None
        return row[0], row[1]

    async def clear_silent_to_working(
        self,
        session: AsyncSession,
        agent: AgentExecution,
    ) -> None:
        """Transition a silent agent back to working and flush.

        Args:
            session: Async database session
            agent: AgentExecution to transition
        """
        agent.status = "working"
        agent.last_progress_at = datetime.now(UTC)
        await session.flush()

    async def find_silent_agent_by_agent_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_id: str,
    ) -> tuple[AgentExecution | None, str | None]:
        """Find a silent agent by agent_id and return with project_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_id: Agent execution ID

        Returns:
            Tuple of (AgentExecution or None, project_id or None)
        """
        stmt = (
            select(AgentExecution, AgentJob.project_id)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "silent",
            )
        )
        result = await session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None, None
        return row[0], row[1]

    async def get_silence_threshold_setting(
        self,
        session: AsyncSession,
    ) -> int | None:
        """Read silence threshold from system settings.

        Args:
            session: Async database session

        Returns:
            Threshold in minutes or None if not configured
        """
        stmt = select(Settings).where(Settings.category == "general").limit(1)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings and settings.settings_data:
            threshold = settings.settings_data.get("agent_silence_threshold_minutes")
            if threshold is not None and isinstance(threshold, (int, float)):
                return max(1, int(threshold))
        return None

    # ============================================================================
    # WorkflowStatusService operations
    # ============================================================================

    async def get_workflow_executions(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        exclude_job_id: str | None = None,
    ) -> list[tuple[AgentExecution, AgentJob]]:
        """Get all executions for a project with their jobs.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            exclude_job_id: Optional job_id to exclude

        Returns:
            List of (AgentExecution, AgentJob) tuples
        """
        query = (
            select(AgentExecution, AgentJob)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentExecution.tenant_key == tenant_key,
                AgentJob.project_id == project_id,
            )
        )
        if exclude_job_id:
            query = query.where(AgentJob.job_id != exclude_job_id)
        result = await session.execute(query)
        return list(result.all())

    async def get_todo_counts_by_job(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_ids: list[str],
    ) -> dict[str, dict[str, int]]:
        """Get aggregated TODO counts grouped by job_id and status.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_ids: List of job IDs to query

        Returns:
            Dict mapping job_id -> {status: count}
        """
        if not job_ids:
            return {}

        stmt = (
            select(
                AgentTodoItem.job_id,
                AgentTodoItem.status,
                func.count().label("cnt"),
            )
            .where(
                AgentTodoItem.job_id.in_(job_ids),
                AgentTodoItem.tenant_key == tenant_key,
            )
            .group_by(AgentTodoItem.job_id, AgentTodoItem.status)
        )
        result = await session.execute(stmt)
        rows = result.all()

        todo_map: dict[str, dict[str, int]] = {}
        for t_job_id, t_status, t_cnt in rows:
            todo_map.setdefault(t_job_id, {})[t_status] = t_cnt
        return todo_map

    # ============================================================================
    # OrchestrationService operations
    # ============================================================================

    async def get_pending_executions_with_jobs(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_display_name: str | None = None,
        limit: int = 10,
    ) -> list[tuple[AgentExecution, AgentJob]]:
        """Get pending (waiting) executions with their job records.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_display_name: Optional filter by display name
            limit: Maximum results

        Returns:
            List of (AgentExecution, AgentJob) tuples
        """
        stmt = (
            select(AgentExecution, AgentJob)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "waiting",
            )
        )
        if agent_display_name and agent_display_name.strip():
            stmt = stmt.where(AgentExecution.agent_display_name == agent_display_name)
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return list(result.all())

    async def get_completed_execution_result(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> dict | None:
        """Get the completion result from the latest completed execution.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            Result dict or None
        """
        stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "complete",
            )
            .order_by(AgentExecution.completed_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        execution = result.scalar_one_or_none()
        if execution and execution.result:
            return execution.result
        return None

    # ============================================================================
    # JobQueryService operations
    # ============================================================================

    async def list_jobs_paginated(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str | None = None,
        status_filter: str | None = None,
        agent_display_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[tuple[AgentExecution, AgentJob]], int]:
        """List jobs with pagination, returning executions + jobs and total count.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Optional project filter
            status_filter: Optional execution status filter
            agent_display_name: Optional display name filter
            limit: Max results
            offset: Pagination offset

        Returns:
            Tuple of (list of (AgentExecution, AgentJob) tuples, total count)
        """
        query = (
            select(AgentExecution, AgentJob)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .options(selectinload(AgentJob.todo_items))
            .where(AgentExecution.tenant_key == tenant_key)
        )

        if project_id:
            query = query.where(AgentJob.project_id == project_id)
        if status_filter:
            query = query.where(AgentExecution.status == status_filter)
        if agent_display_name:
            query = query.where(AgentExecution.agent_display_name == agent_display_name)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(AgentJob.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        rows = list(result.all())

        return rows, total or 0

    async def get_job_messages_for_agent(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
        limit: int = 50,
    ) -> tuple[AgentExecution | None, dict[str, str], list[Message]]:
        """Get messages for an agent job (for MessageAuditModal).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID
            limit: Max messages to return

        Returns:
            Tuple of (execution or None, agent_id->display_name lookup, messages list)
        """
        exec_stmt = select(AgentExecution).where(
            AgentExecution.job_id == job_id,
            AgentExecution.tenant_key == tenant_key,
        )
        execution = (await session.execute(exec_stmt)).scalar_one_or_none()

        if not execution:
            return None, {}, []

        agents_stmt = select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
        )
        agents_result = await session.execute(agents_stmt)
        agents = agents_result.scalars().all()

        agent_lookup: dict[str, str] = {}
        for agent in agents:
            display_name = agent.agent_display_name.capitalize() if agent.agent_display_name else "Agent"
            agent_lookup[agent.agent_id] = display_name
            if agent.agent_name:
                agent_lookup[agent.agent_name] = display_name

        msg_stmt = (
            select(Message)
            .outerjoin(MessageRecipient)
            .where(
                Message.tenant_key == tenant_key,
                or_(
                    Message.from_agent_id == execution.agent_id,
                    MessageRecipient.agent_id == execution.agent_id,
                ),
            )
            .options(selectinload(Message.recipients))
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = (await session.execute(msg_stmt)).scalars().unique().all()

        return execution, agent_lookup, list(messages)
