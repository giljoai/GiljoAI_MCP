"""
AgentJobManager Service - Coordinated CRUD for AgentJob + AgentExecution (Handover 0366b).

This service manages agent job lifecycle with dual-model architecture:
- AgentJob: Persistent work order (mission, scope) - WHAT
- AgentExecution: Executor instance (who's working, status) - WHO

Key Operations:
- spawn_agent() - Creates BOTH job and execution
- update_agent_status() - Updates execution status (not job)
- complete_job() - Marks job complete and decommissions all executions

Note: cancel_job() was intentionally removed (commit d14e8ff7) - passive HTTP
architecture means agents only see cancellation on next poll (30s-5min delay).
Use project-level cancel or Ctrl+C in terminal for immediate stop.

Design Philosophy:
- Job = Work to be done (persists across succession)
- Execution = Who's doing the work (changes on succession)
- One job can have multiple executions (succession chain)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from contextlib import asynccontextmanager
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class AgentJobManager:
    """
    Service for managing agent jobs with dual-model architecture.

    Handover 0366b: Updated to manage BOTH AgentJob and AgentExecution.

    Responsibilities:
    - Create and manage agent jobs (work orders)
    - Create and manage agent executions (executors)
    - Track job and execution status separately
    - Maintain succession chains (multiple executions per job)
    - Enforce tenant isolation
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
    ):
        """
        Initialize AgentJobManager.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            test_session: Optional AsyncSession for tests to share the same transaction
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.

        Returns:
            Context manager for database session
        """
        if self._test_session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session
            return _test_session_wrapper()

        # Return the context manager directly
        return self.db_manager.get_session_async()

    # ============================================================================
    # Agent Spawning (creates job + execution)
    # ============================================================================

    async def spawn_agent(
        self,
        project_id: str,
        agent_display_name: str,
        mission: str,
        tenant_key: str,
        agent_name: Optional[str] = None,
        tool_type: str = "universal",
        context_budget: int = 150000,
        spawned_by: Optional[str] = None,
        job_metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Spawn a new agent (creates BOTH job and execution).

        Handover 0366b: This is the fundamental coordinated CRUD operation.

        Creates:
        1. AgentJob - Persistent work order (mission, scope)
        2. AgentExecution - First executor (instance_number=1)

        Args:
            project_id: Project ID this agent belongs to
            agent_display_name: Display name of agent (UI label - what humans see)
            mission: Mission/instructions for the agent
            tenant_key: Tenant key for multi-tenant isolation
            agent_name: Optional human-readable name (template lookup key)
            tool_type: AI coding tool assigned (claude-code, codex, gemini, universal)
            context_budget: Maximum context window budget in tokens
            spawned_by: Optional agent_id of parent agent that spawned this agent
            job_metadata: Optional metadata dict

        Returns:
            Dict with success status, job_id, and agent_id

        Example:
            >>> result = await manager.spawn_agent(
            ...     project_id="project-123",
            ...     agent_display_name="Code Analyzer",
            ...     mission="Analyze codebase for security vulnerabilities",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(f"Job ID: {result['job_id']}, Agent ID: {result['agent_id']}")
        """
        try:
            async with self._get_session() as session:
                # Create job (work order)
                job = AgentJob(
                    job_id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    mission=mission,
                    job_type=agent_display_name,
                    status="active",
                    job_metadata=job_metadata or {},
                )

                # Create execution (first executor)
                execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=job.job_id,
                    tenant_key=tenant_key,
                    agent_display_name=agent_display_name,
                    instance_number=1,  # First instance
                    status="waiting",  # Waiting to be launched
                    spawned_by=spawned_by,
                    tool_type=tool_type,
                    context_budget=context_budget,
                    agent_name=agent_name,
                )

                session.add(job)
                session.add(execution)
                await session.commit()
                await session.refresh(job)
                await session.refresh(execution)

                self._logger.info(
                    f"Spawned agent: job_id={job.job_id}, agent_id={execution.agent_id}, "
                    f"agent_display_name={agent_display_name}, project_id={project_id}"
                )

                return {
                    "success": True,
                    "job_id": job.job_id,
                    "agent_id": execution.agent_id,
                    "agent_display_name": agent_display_name,
                    "status": execution.status,
                }

        except Exception as e:
            self._logger.exception(f"Failed to spawn agent: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Execution Status Updates (execution-specific, not job-level)
    # ============================================================================

    async def update_agent_status(
        self,
        agent_id: str,
        status: str,
        tenant_key: str,
        progress: Optional[int] = None,
        current_task: Optional[str] = None,
        block_reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update agent execution status.

        Handover 0366b: Updates AgentExecution, NOT AgentJob.

        Args:
            agent_id: Agent execution ID (executor UUID)
            status: New status (waiting, working, blocked, complete, failed, cancelled, decommissioned)
            tenant_key: Tenant key for multi-tenant isolation
            progress: Optional completion progress (0-100%)
            current_task: Optional description of current task
            block_reason: Optional reason for blocked status

        Returns:
            Dict with success status

        Example:
            >>> await manager.update_agent_status(
            ...     agent_id="agent-uuid-123",
            ...     status="working",
            ...     progress=50,
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Get execution (Handover 0429: get latest instance)
                result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.agent_id == agent_id,
                            AgentExecution.tenant_key == tenant_key
                        )
                    ).order_by(AgentExecution.instance_number.desc()).limit(1)
                )
                execution = result.scalar_one_or_none()

                if not execution:
                    return {
                        "success": False,
                        "error": f"Execution {agent_id} not found"
                    }

                # Update execution status
                execution.status = status
                if progress is not None:
                    execution.progress = progress
                if current_task is not None:
                    execution.current_task = current_task
                if block_reason is not None:
                    execution.block_reason = block_reason

                # Update timestamps
                if status == "working" and not execution.started_at:
                    execution.started_at = datetime.now(timezone.utc)
                elif status in ["complete", "failed", "cancelled"]:
                    execution.completed_at = datetime.now(timezone.utc)
                elif status == "decommissioned":
                    execution.decommissioned_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(execution)

                self._logger.info(
                    f"Updated execution {agent_id} status to {status}"
                )

                return {"success": True, "status": status}

        except Exception as e:
            self._logger.exception(f"Failed to update agent status: {e}")
            return {"success": False, "error": str(e)}

    async def update_agent_progress(
        self,
        agent_id: str,
        progress: int,
        current_task: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update agent execution progress.

        Handover 0366b: Updates AgentExecution progress (executor-specific).

        Args:
            agent_id: Agent execution ID
            progress: Completion progress (0-100%)
            current_task: Optional description of current task
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with success status
        """
        try:
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            async with self._get_session() as session:
                # Handover 0429: Get latest instance by agent_id
                result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.agent_id == agent_id,
                            AgentExecution.tenant_key == tenant_key
                        )
                    ).order_by(AgentExecution.instance_number.desc()).limit(1)
                )
                execution = result.scalar_one_or_none()

                if not execution:
                    return {
                        "success": False,
                        "error": f"Execution {agent_id} not found"
                    }

                execution.progress = progress
                if current_task:
                    execution.current_task = current_task
                execution.last_progress_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(execution)

                return {"success": True, "progress": progress}

        except Exception as e:
            self._logger.exception(f"Failed to update agent progress: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Job Completion (decommissions all executions)
    # ============================================================================

    async def complete_job(
        self,
        job_id: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """
        Complete a job (marks job complete and decommissions all executions).

        Handover 0366b: Updates BOTH AgentJob and ALL AgentExecutions.

        Args:
            job_id: Job ID to complete
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with success status

        Example:
            >>> await manager.complete_job(
            ...     job_id="job-uuid-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Get job
                job_result = await session.execute(
                    select(AgentJob).where(
                        and_(
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key
                        )
                    )
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    return {
                        "success": False,
                        "error": f"Job {job_id} not found"
                    }

                # Mark job complete
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)

                # Decommission ALL executions for this job
                executions_result = await session.execute(
                    select(AgentExecution).where(AgentExecution.job_id == job_id)
                )
                executions = executions_result.scalars().all()

                for execution in executions:
                    execution.status = "decommissioned"
                    execution.decommissioned_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(job)
                for execution in executions:
                    await session.refresh(execution)

                self._logger.info(
                    f"Completed job {job_id} and decommissioned {len(executions)} execution(s)"
                )

                return {
                    "success": True,
                    "job_id": job_id,
                    "executions_decommissioned": len(executions)
                }

        except Exception as e:
            self._logger.exception(f"Failed to complete job: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Query Operations
    # ============================================================================

    async def get_execution_by_agent_id(
        self,
        agent_id: str,
        tenant_key: str,
    ) -> Optional[AgentExecution]:
        """
        Get execution by agent_id (primary lookup method).

        Args:
            agent_id: Agent execution ID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            AgentExecution instance or None
        """
        try:
            async with self._get_session() as session:
                # Handover 0429: Get latest instance by agent_id
                result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.agent_id == agent_id,
                            AgentExecution.tenant_key == tenant_key
                        )
                    ).order_by(AgentExecution.instance_number.desc()).limit(1)
                )
                return result.scalar_one_or_none()

        except Exception as e:
            self._logger.exception(f"Failed to get execution by agent_id: {e}")
            return None

    async def get_job_by_job_id(
        self,
        job_id: str,
        tenant_key: str,
    ) -> Optional[AgentJob]:
        """
        Get job by job_id (work order lookup).

        Args:
            job_id: Job ID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            AgentJob instance or None
        """
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(AgentJob).where(
                        and_(
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key
                        )
                    )
                )
                return result.scalar_one_or_none()

        except Exception as e:
            self._logger.exception(f"Failed to get job by job_id: {e}")
            return None

    async def get_all_executions_for_job(
        self,
        job_id: str,
        tenant_key: str,
    ) -> list[AgentExecution]:
        """
        Get all executions for a job (succession history).

        Args:
            job_id: Job ID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            List of AgentExecution instances (ordered by instance_number)
        """
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.job_id == job_id,
                            AgentExecution.tenant_key == tenant_key
                        )
                    ).order_by(AgentExecution.instance_number)
                )
                return list(result.scalars().all())

        except Exception as e:
            self._logger.exception(f"Failed to get executions for job: {e}")
            return []

    async def get_active_executions_for_project(
        self,
        project_id: str,
        tenant_key: str,
    ) -> list[AgentExecution]:
        """
        Get all active executions for a project (not jobs).

        Handover 0366b: Returns active executions (executors), not jobs (work).

        Args:
            project_id: Project ID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            List of active AgentExecution instances
        """
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(AgentExecution).join(AgentJob).where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentExecution.status.in_(["waiting", "working", "blocked"]),
                            AgentExecution.tenant_key == tenant_key
                        )
                    )
                )
                return list(result.scalars().all())

        except Exception as e:
            self._logger.exception(f"Failed to get active executions for project: {e}")
            return []

    async def list_team_agents(
        self,
        job_id: str,
        tenant_key: str,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List agent executions (teammates) associated with this job.

        Handover 0360 Feature 2: Team Discovery Tool.

        Enables agents to discover teammates working on the same job/project.
        Returns execution details (agent_id, job_id, agent_display_name, status).

        Args:
            job_id: Job ID to get teammates for
            tenant_key: Tenant key for multi-tenant isolation
            include_inactive: If True, include completed/decommissioned executions

        Returns:
            List of dict with team member details:
            [
                {
                    "agent_id": "ae-001",
                    "job_id": "job-abc",
                    "agent_display_name": "Orchestrator",
                    "status": "working",
                    "instance_number": 1,
                    "agent_name": "Orchestrator Instance 1",
                    "tenant_key": "tenant-abc"
                },
                ...
            ]

        Example:
            >>> teammates = await manager.list_team_agents(
            ...     job_id="job-uuid-123",
            ...     tenant_key="tenant-abc",
            ...     include_inactive=False
            ... )
            >>> for member in teammates:
            ...     print(f"{member['agent_display_name']}: {member['status']}")
        """
        try:
            async with self._get_session() as session:
                # Build query
                query = select(AgentExecution).where(
                    and_(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key
                    )
                )

                # Filter by status unless include_inactive is True
                if not include_inactive:
                    # Only return active statuses (waiting, working, blocked)
                    query = query.where(
                        AgentExecution.status.in_(["waiting", "working", "blocked"])
                    )

                # Execute query
                result = await session.execute(query.order_by(AgentExecution.instance_number))
                executions = result.scalars().all()

                # Convert to dict format
                team_members = []
                for execution in executions:
                    team_members.append({
                        "agent_id": execution.agent_id,
                        "job_id": execution.job_id,
                        "agent_display_name": execution.agent_display_name,
                        "status": execution.status,
                        "instance_number": execution.instance_number,
                        "agent_name": execution.agent_name,
                        "tenant_key": execution.tenant_key,
                    })

                self._logger.info(
                    f"Found {len(team_members)} teammates for job {job_id} "
                    f"(include_inactive={include_inactive})"
                )

                return team_members

        except Exception as e:
            self._logger.exception(f"Failed to list team agents: {e}")
            return []
