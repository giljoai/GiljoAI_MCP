# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
JobQueryService - Agent job listing and queries.

Sprint 002e: Extracted from OrchestrationService to reduce god-class size.
list_jobs is completely self-contained (169 lines) -- pure read query with pagination.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import OrchestrationError, ResourceNotFoundError
from giljo_mcp.models import AgentExecution, AgentJob
from giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from giljo_mcp.repositories.agent_operations_repository import AgentOperationsRepository
from giljo_mcp.schemas.service_responses import JobListResult
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class JobQueryService:
    """Service for listing and querying agent jobs.

    Extracted from OrchestrationService (Sprint 002e).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    async def list_jobs(
        self,
        tenant_key: str,
        project_id: str | None = None,
        status_filter: str | None = None,
        agent_display_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> JobListResult:
        """List agent jobs with flexible filtering.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        Supports filtering by project, status, and agent display name with pagination.
        All jobs are filtered by tenant_key for multi-tenant isolation.

        Args:
            tenant_key: Tenant key for isolation (required)
            project_id: Filter by project UUID (optional)
            status_filter: Filter by execution status (optional)
            agent_display_name: Filter by agent display name (optional)
            limit: Maximum results (default 100, max 500)
            offset: Pagination offset (default 0)

        Returns:
            JobListResult with jobs, total count, limit and offset
        """
        try:
            ops_repo = AgentOperationsRepository()
            async with self._get_session() as session:
                rows, total = await ops_repo.list_jobs_paginated(
                    session,
                    tenant_key,
                    project_id,
                    status_filter,
                    agent_display_name,
                    limit,
                    offset,
                )

                job_dicts = []
                for execution, job in rows:
                    self._logger.debug(
                        f"[LIST_JOBS DEBUG] Agent {execution.agent_display_name} (job={job.job_id}, agent={execution.agent_id}): "
                        f"{execution.messages_sent_count} sent, {execution.messages_waiting_count} waiting, {execution.messages_read_count} read"
                    )

                    steps_summary = self._derive_steps_summary(job)

                    job_dicts.append(
                        {
                            "job_id": job.job_id,
                            "agent_id": execution.agent_id,
                            "execution_id": execution.id,
                            "tenant_key": execution.tenant_key,
                            "project_id": job.project_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "mission": job.mission,
                            "phase": job.phase,
                            "status": execution.status,
                            "progress": execution.progress,
                            "spawned_by": execution.spawned_by,
                            "tool_type": execution.tool_type,
                            "context_chunks": [],
                            "messages_sent_count": execution.messages_sent_count,
                            "messages_waiting_count": execution.messages_waiting_count,
                            "messages_read_count": execution.messages_read_count,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "steps": steps_summary,
                            "todo_items": [
                                {"content": item.content, "status": item.status}
                                for item in sorted(job.todo_items or [], key=lambda x: x.sequence)
                            ],
                            "result": execution.result,
                            "template_id": job.template_id,
                            "accumulated_duration_seconds": execution.accumulated_duration_seconds or 0.0,
                            "reactivation_count": execution.reactivation_count or 0,
                        }
                    )

                self._logger.info(
                    f"Listed {len(job_dicts)} jobs (total={total}, project={project_id}, status={status_filter})"
                )

                return JobListResult(
                    jobs=job_dicts,
                    total=total,
                    limit=limit,
                    offset=offset,
                )

        except Exception as e:
            self._logger.exception("Failed to list jobs")
            raise OrchestrationError(
                message="Failed to list jobs", context={"tenant_key": tenant_key, "error": str(e)}
            ) from e

    async def get_job_messages(
        self,
        tenant_key: str,
        job_id: str,
        limit: int = 50,
    ) -> dict:
        """Get messages for an agent job (for MessageAuditModal).

        Returns messages where the agent is sender or recipient,
        with resolved display names for both directions.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Agent job ID to retrieve messages for
            limit: Maximum messages to retrieve (default 50, max 200)

        Returns:
            Dict with job_id, agent_id, and messages list

        Raises:
            ResourceNotFoundError: Job not found for this tenant
            OrchestrationError: Query failure
        """
        try:
            ops_repo = AgentOperationsRepository()
            async with self._get_session() as session:
                execution, agent_lookup, messages = await ops_repo.get_job_messages_for_agent(
                    session, tenant_key, job_id, limit
                )

                if not execution:
                    raise ResourceNotFoundError(
                        message="Job not found",
                        context={"job_id": job_id, "tenant_key": tenant_key},
                    )

                return {
                    "job_id": job_id,
                    "agent_id": execution.agent_id,
                    "agent_lookup": agent_lookup,
                    "messages": messages,
                }

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self._logger.exception("Failed to get job messages")
            raise OrchestrationError(
                message="Failed to get job messages",
                context={"job_id": job_id, "error": str(e)},
            ) from e

    def _derive_steps_summary(self, job: AgentJob) -> dict | None:
        """Derive steps summary from job metadata or todo_items."""
        try:
            metadata = job.job_metadata or {}
            todo_steps = metadata.get("todo_steps") or {}
            total_steps = todo_steps.get("total_steps")
            completed_steps = todo_steps.get("completed_steps")
            skipped_steps = todo_steps.get("skipped_steps", 0)
            if (
                isinstance(total_steps, int)
                and total_steps > 0
                and isinstance(completed_steps, int)
                and 0 <= completed_steps <= total_steps
            ):
                return {
                    "total": total_steps,
                    "completed": completed_steps,
                    "skipped": skipped_steps if isinstance(skipped_steps, int) else 0,
                }
            if job.todo_items:
                total = len(job.todo_items)
                completed = sum(1 for item in job.todo_items if item.status == "completed")
                skipped = sum(1 for item in job.todo_items if item.status == "skipped")
                if total > 0:
                    return {"total": total, "completed": completed, "skipped": skipped}
        except (KeyError, ValueError, TypeError, AttributeError):
            self._logger.warning(
                "[LIST_JOBS] Failed to derive steps summary from job_metadata",
                exc_info=True,
            )
        return None

    # ---- BE-5022b: Service wrappers for AgentJobRepository read methods ----

    async def get_execution_by_agent_id(
        self,
        tenant_key: str,
        agent_id: str,
        session: AsyncSession | None = None,
    ) -> AgentExecution | None:
        """Get agent execution by agent_id with tenant isolation.

        BE-5022b: Service wrapper for AgentJobRepository.get_execution_by_agent_id().

        Args:
            tenant_key: Tenant isolation key
            agent_id: Agent UUID
            session: Optional existing session

        Returns:
            AgentExecution or None
        """
        repo = AgentJobRepository(None)
        if session is not None:
            return await repo.get_execution_by_agent_id(session=session, tenant_key=tenant_key, agent_id=agent_id)
        async with self._get_session() as new_session:
            return await repo.get_execution_by_agent_id(session=new_session, tenant_key=tenant_key, agent_id=agent_id)

    async def get_execution_by_job_id(
        self,
        tenant_key: str,
        job_id: str,
        session: AsyncSession | None = None,
    ) -> AgentExecution | None:
        """Get agent execution by job_id with tenant isolation.

        BE-5022b: Service wrapper for AgentJobRepository.get_execution_by_job_id().

        Args:
            tenant_key: Tenant isolation key
            job_id: Job UUID
            session: Optional existing session

        Returns:
            AgentExecution or None
        """
        repo = AgentJobRepository(None)
        if session is not None:
            return await repo.get_execution_by_job_id(session=session, tenant_key=tenant_key, job_id=job_id)
        async with self._get_session() as new_session:
            return await repo.get_execution_by_job_id(session=new_session, tenant_key=tenant_key, job_id=job_id)

    async def get_agent_job_by_job_id(
        self,
        tenant_key: str,
        job_id: str,
        session: AsyncSession | None = None,
    ) -> AgentJob | None:
        """Get an agent job record by job_id with tenant isolation.

        BE-5022b: Service wrapper for AgentJobRepository.get_agent_job_by_job_id().

        Args:
            tenant_key: Tenant isolation key
            job_id: Job UUID
            session: Optional existing session

        Returns:
            AgentJob or None
        """
        repo = AgentJobRepository(None)
        if session is not None:
            return await repo.get_agent_job_by_job_id(session=session, tenant_key=tenant_key, job_id=job_id)
        async with self._get_session() as new_session:
            return await repo.get_agent_job_by_job_id(session=new_session, tenant_key=tenant_key, job_id=job_id)

    async def get_latest_execution_for_job(
        self,
        tenant_key: str,
        job_id: str,
        session: AsyncSession | None = None,
    ) -> AgentExecution | None:
        """Get the most recent execution for a job_id with tenant isolation.

        BE-5022b: Service wrapper for AgentJobRepository.get_latest_execution_for_job().

        Args:
            tenant_key: Tenant isolation key
            job_id: Job UUID
            session: Optional existing session

        Returns:
            AgentExecution or None
        """
        repo = AgentJobRepository(None)
        if session is not None:
            return await repo.get_latest_execution_for_job(session=session, tenant_key=tenant_key, job_id=job_id)
        async with self._get_session() as new_session:
            return await repo.get_latest_execution_for_job(session=new_session, tenant_key=tenant_key, job_id=job_id)
