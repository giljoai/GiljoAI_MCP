"""
AgentJobManager Service - Coordinated CRUD for AgentJob + AgentExecution (Handover 0366b).

This service manages agent job lifecycle with dual-model architecture:
- AgentJob: Persistent work order (mission, scope) - WHAT
- AgentExecution: Executor instance (who's working, status) - WHO

Key Operations:
- spawn_agent() - Creates BOTH job and execution
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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import BaseGiljoError, ResourceNotFoundError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.schemas.jsonb_validators import validate_job_metadata
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
        spawned_by: Optional[str] = None,
        job_metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[str, str, str, str]:
        """
        Spawn a new agent (creates BOTH job and execution).

        Handover 0366b: This is the fundamental coordinated CRUD operation.
        Handover 0730b: Converted to exception-based error handling.

        Creates:
        1. AgentJob - Persistent work order (mission, scope)
        2. AgentExecution - Executor instance

        Args:
            project_id: Project ID this agent belongs to
            agent_display_name: Display name of agent (UI label - what humans see)
            mission: Mission/instructions for the agent
            tenant_key: Tenant key for multi-tenant isolation
            agent_name: Optional human-readable name (template lookup key)
            tool_type: AI coding agent assigned (claude-code, codex, gemini, universal)
            spawned_by: Optional agent_id of parent agent that spawned this agent
            job_metadata: Optional metadata dict

        Returns:
            Tuple of (job_id, agent_id, agent_display_name, status)

        Raises:
            BaseGiljoError: Database operation failed

        Example:
            >>> job_id, agent_id, display_name, status = await manager.spawn_agent(
            ...     project_id="project-123",
            ...     agent_display_name="Code Analyzer",
            ...     mission="Analyze codebase for security vulnerabilities",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(f"Job ID: {job_id}, Agent ID: {agent_id}")
        """
        try:
            async with self._get_session() as session:
                # Create job (work order)
                validated_metadata = validate_job_metadata(job_metadata) or {}
                job = AgentJob(
                    job_id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    mission=mission,
                    job_type=agent_display_name,
                    status="active",
                    job_metadata=validated_metadata,
                )

                # Create execution (first executor)
                execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=job.job_id,
                    tenant_key=tenant_key,
                    agent_display_name=agent_display_name,
                    status="waiting",  # Waiting to be launched
                    spawned_by=spawned_by,
                    tool_type=tool_type,
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

                return (job.job_id, execution.agent_id, agent_display_name, execution.status)

        except BaseGiljoError:
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to spawn agent")
            raise BaseGiljoError(message=str(e), context={"operation": "spawn_agent"}) from e

    # ============================================================================
    # Execution Spawning (creates execution for existing job)
    # ============================================================================

    async def spawn_execution(
        self,
        job_id: str,
        agent_display_name: str,
        tenant_key: str,
        spawned_by: str | None = None,
    ) -> tuple[str, str]:
        """
        Spawn a NEW execution for an EXISTING job (Handover 0769a).

        Creates an AgentExecution (executor instance) for an existing AgentJob.
        Enables agent succession while preserving job continuity.

        Args:
            job_id: AgentJob UUID to spawn execution for (must exist)
            agent_display_name: Display name for this executor
            tenant_key: Tenant key for multi-tenant isolation
            spawned_by: Parent executor's agent_id (for succession tracking)

        Returns:
            Tuple of (job_id, agent_id)

        Raises:
            ResourceNotFoundError: Job not found for tenant
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                job_result = await session.execute(
                    select(AgentJob).where(
                        AgentJob.job_id == job_id,
                        AgentJob.tenant_key == tenant_key,
                    )
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    raise ResourceNotFoundError(
                        message=f"AgentJob with job_id={job_id} not found for tenant {tenant_key}",
                        context={"job_id": job_id, "tenant_key": tenant_key},
                    )

                new_agent_id = str(uuid4())
                execution = AgentExecution(
                    agent_id=new_agent_id,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    agent_display_name=agent_display_name,
                    status="waiting",
                    spawned_by=spawned_by,
                    agent_name=agent_display_name.title(),
                    tool_type="universal",
                )

                session.add(execution)
                await session.commit()
                await session.refresh(execution)

                self._logger.info(
                    f"Spawned execution: agent_id={new_agent_id} for job_id={job_id}, tenant={tenant_key}"
                )

                return (job_id, new_agent_id)

        except (ResourceNotFoundError, BaseGiljoError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to spawn execution")
            raise BaseGiljoError(message=str(e), context={"operation": "spawn_execution", "job_id": job_id}) from e

    # ============================================================================
    # Job Completion (decommissions all executions)
    # ============================================================================

    async def complete_job(
        self,
        job_id: str,
        tenant_key: str,
    ) -> int:
        """
        Complete a job (marks job complete and decommissions all executions).

        Handover 0366b: Updates BOTH AgentJob and ALL AgentExecutions.
        Handover 0730b: Converted to exception-based error handling.

        Args:
            job_id: Job ID to complete
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Number of executions decommissioned

        Raises:
            ResourceNotFoundError: Job not found
            BaseGiljoError: Database operation failed

        Example:
            >>> count = await manager.complete_job(
            ...     job_id="job-uuid-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(f"Decommissioned {count} execution(s)")
        """
        try:
            async with self._get_session() as session:
                # Get job
                job_result = await session.execute(
                    select(AgentJob).where(and_(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key))
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    raise ResourceNotFoundError(message=f"Job {job_id} not found", context={"job_id": job_id})

                # Mark job complete
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)

                # Decommission ALL executions for this job
                # TENANT ISOLATION: Filter by tenant_key (Phase D audit fix)
                executions_result = await session.execute(
                    select(AgentExecution).where(
                        AgentExecution.job_id == job_id, AgentExecution.tenant_key == tenant_key
                    )
                )
                executions = executions_result.scalars().all()

                for execution in executions:
                    execution.status = "complete"

                await session.commit()
                await session.refresh(job)
                for execution in executions:
                    await session.refresh(execution)

                self._logger.info(f"Completed job {job_id} and marked {len(executions)} execution(s) as complete")

                return len(executions)

        except (ResourceNotFoundError, BaseGiljoError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to complete job")
            raise BaseGiljoError(message=str(e), context={"operation": "complete_job"}) from e

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
                    and_(AgentExecution.job_id == job_id, AgentExecution.tenant_key == tenant_key)
                )

                # Filter by status unless include_inactive is True
                if not include_inactive:
                    # Only return active statuses (waiting, working, blocked)
                    query = query.where(AgentExecution.status.in_(["waiting", "working", "blocked"]))

                # Execute query
                result = await session.execute(query.order_by(AgentExecution.started_at))
                executions = result.scalars().all()

                # Convert to dict format
                team_members = [
                    {
                        "agent_id": execution.agent_id,
                        "job_id": execution.job_id,
                        "agent_display_name": execution.agent_display_name,
                        "status": execution.status,
                        "agent_name": execution.agent_name,
                        "tenant_key": execution.tenant_key,
                    }
                    for execution in executions
                ]

                self._logger.info(
                    f"Found {len(team_members)} teammates for job {job_id} (include_inactive={include_inactive})"
                )

                return team_members

        except Exception:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list team agents")
            return []
