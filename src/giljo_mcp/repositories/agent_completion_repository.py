# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent completion and lifecycle repository.

BE-5022d: Extracted from AgentJobRepository to keep files under 800 lines.
Contains operations for: job completion validation, job lifecycle spawning,
predecessor context, template resolution, and display name collision handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import AgentTodoItem, Message, ProductMemoryEntry, Project
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.tasks import MessageRecipient
from giljo_mcp.models.templates import AgentTemplate


class AgentCompletionRepository:
    """Repository for job completion and lifecycle operations.

    Provides database operations for job completion validation,
    HITL enforcement, predecessor context, template resolution,
    and display name collision handling.
    """

    async def get_agent_job_by_job_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentJob | None:
        """Get agent job by job_id with tenant isolation.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID to retrieve

        Returns:
            AgentJob or None
        """
        stmt = select(AgentJob).where(
            AgentJob.tenant_key == tenant_key,
            AgentJob.job_id == job_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================================================
    # JobCompletionService operations
    # ============================================================================

    async def find_active_execution_for_completion(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution | None:
        """Find the latest active execution for job completion.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            AgentExecution or None
        """
        stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status.not_in(["complete", "closed", "decommissioned"]),
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_unread_messages_for_agent(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        agent_id: str,
    ) -> list[Message]:
        """Get unread (pending) messages for an agent in a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            agent_id: Recipient agent ID

        Returns:
            List of pending Message instances
        """
        stmt = (
            select(Message)
            .join(MessageRecipient)
            .where(
                and_(
                    Message.tenant_key == tenant_key,
                    Message.project_id == project_id,
                    Message.status == "pending",
                    MessageRecipient.agent_id == agent_id,
                )
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_incomplete_todos(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> list[AgentTodoItem]:
        """Get incomplete TODO items for a job.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            List of incomplete AgentTodoItem instances
        """
        stmt = select(AgentTodoItem).where(
            and_(
                AgentTodoItem.job_id == job_id,
                AgentTodoItem.tenant_key == tenant_key,
                AgentTodoItem.status.notin_(["completed", "skipped"]),
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def check_360_memory_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> bool:
        """Check if 360 memory exists for a project's product.

        Fetches the project, then checks for project_completion memory entries.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            True if memory entry exists or project/product not found
        """
        project_res = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_key == tenant_key,
            )
        )
        project = project_res.scalar_one_or_none()
        if not project or not project.product_id:
            return True

        stmt = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == project.product_id,
                ProductMemoryEntry.tenant_key == tenant_key,
                ProductMemoryEntry.entry_type == "project_completion",
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_other_active_executions_by_agent_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
        exclude_agent_id: str,
    ) -> AgentExecution | None:
        """Check if other non-terminal executions exist for a job (by agent_id).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID
            exclude_agent_id: Agent UUID to exclude from check

        Returns:
            AgentExecution or None
        """
        stmt = select(AgentExecution).where(
            AgentExecution.job_id == job_id,
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.agent_id != exclude_agent_id,
            AgentExecution.status.not_in(["complete", "closed", "decommissioned"]),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_decommissioned_execution(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution | None:
        """Find the latest decommissioned execution for a job.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            Decommissioned AgentExecution or None
        """
        stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "decommissioned",
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_execution_hitl_block(
        self,
        session: AsyncSession,
        execution_id: int,
        status: str,
        block_reason: str,
    ) -> None:
        """Update an execution's status and block_reason for HITL.

        Args:
            session: Async database session
            execution_id: Execution primary key (int id)
            status: New status value
            block_reason: Block reason string
        """
        exec_obj = await session.get(AgentExecution, execution_id)
        if exec_obj:
            exec_obj.status = status
            exec_obj.block_reason = block_reason
            await session.commit()

    async def commit(self, session: AsyncSession) -> None:
        """Commit the current transaction."""
        await session.commit()

    # ============================================================================
    # JobLifecycleService operations
    # ============================================================================

    async def persist_job_and_execution(
        self,
        session: AsyncSession,
        agent_job: AgentJob,
        agent_execution: AgentExecution,
        project: Any | None = None,
        is_orchestrator: bool = False,
    ) -> tuple[AgentJob, AgentExecution]:
        """Persist AgentJob + AgentExecution, update project staging if orchestrator.

        Args:
            session: Async database session
            agent_job: AgentJob instance to persist
            agent_execution: AgentExecution instance to persist
            project: Project instance to update staging_status (if orchestrator)
            is_orchestrator: Whether the agent is an orchestrator

        Returns:
            Tuple of (AgentJob, AgentExecution) after commit and refresh
        """
        session.add(agent_job)

        if is_orchestrator and project is not None:
            project.staging_status = "staging"
            project.updated_at = datetime.now(timezone.utc)

        session.add(agent_execution)
        await session.commit()
        await session.refresh(agent_job)
        await session.refresh(agent_execution)
        return agent_job, agent_execution

    async def get_predecessor_job(
        self,
        session: AsyncSession,
        tenant_key: str,
        predecessor_job_id: str,
    ) -> AgentJob | None:
        """Get a predecessor job by ID with tenant isolation.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            predecessor_job_id: Predecessor job UUID

        Returns:
            AgentJob or None
        """
        result = await session.execute(
            select(AgentJob).where(
                and_(
                    AgentJob.job_id == predecessor_job_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_completed_execution_for_job(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution | None:
        """Get the latest completed execution for a job.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID

        Returns:
            Completed AgentExecution or None
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
        return result.scalar_one_or_none()

    async def get_active_display_names_in_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> set[str]:
        """Get all active display names in a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            Set of active agent_display_name values
        """
        result = await session.execute(
            select(AgentExecution.agent_display_name)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.status.in_(["waiting", "working", "blocked"]),
                )
            )
        )
        return {row[0] for row in result.fetchall()}

    async def get_active_template_names(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> list[str]:
        """Get active agent template names.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            List of active template name strings
        """
        result = await session.execute(
            select(AgentTemplate.name).where(
                and_(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.is_active,
                )
            )
        )
        return [row[0] for row in result.fetchall()]

    async def find_active_orchestrator_in_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> AgentExecution | None:
        """Find the active orchestrator execution in a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            Active orchestrator AgentExecution or None
        """
        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.agent_display_name == "orchestrator",
                    AgentExecution.status.in_(["waiting", "working", "blocked"]),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_template_by_name(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_name: str,
    ) -> AgentTemplate | None:
        """Get an active agent template by name.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_name: Template name to look up

        Returns:
            AgentTemplate or None
        """
        result = await session.execute(
            select(AgentTemplate).where(
                and_(
                    AgentTemplate.name == agent_name,
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.is_active,
                )
            )
        )
        return result.scalar_one_or_none()
