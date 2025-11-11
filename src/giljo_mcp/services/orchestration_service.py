"""
OrchestrationService - Dedicated service for orchestration and job management

This service extracts all orchestration and job management operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).

Responsibilities:
- Project orchestration workflow
- Agent job lifecycle management (spawn, acknowledge, complete, error)
- Job progress tracking and reporting
- Workflow status monitoring
- Orchestrator succession/handover

Design Principles:
- Single Responsibility: Only orchestration and job domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import MCPAgentJob, Project
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class OrchestrationService:
    """
    Service for managing orchestration and agent jobs.

    This service handles all orchestration-related operations including:
    - Project orchestration workflows
    - Agent job lifecycle (spawn, acknowledge, complete, error)
    - Job progress tracking
    - Workflow status monitoring
    - Pending job retrieval

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize OrchestrationService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Project Orchestration
    # ============================================================================

    async def orchestrate_project(
        self,
        project_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Execute full project orchestration workflow.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for isolation

        Returns:
            Dict with orchestration results or error

        Example:
            >>> result = await service.orchestrate_project(
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        from giljo_mcp.orchestrator import ProjectOrchestrator

        try:
            async with self.db_manager.get_session_async() as session:
                # Get project with tenant isolation
                result = await session.execute(
                    select(Project).where(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project '{project_id}' not found"}

                if not project.product_id:
                    return {"error": f"Project '{project_id}' has no associated product"}

                # Initialize orchestrator and run workflow
                orchestrator = ProjectOrchestrator()
                result_dict = await orchestrator.process_product_vision(
                    tenant_key=tenant_key,
                    product_id=project.product_id,
                    project_requirements=project.mission
                )

                return result_dict

        except Exception as e:
            self._logger.exception(f"Failed to orchestrate project: {e}")
            return {"error": f"Orchestration failed: {e!s}"}

    async def get_workflow_status(
        self,
        project_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Get workflow status for a project (MCPAgentJob aware).

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for isolation

        Returns:
            Dict with workflow status including agent counts and progress

        Example:
            >>> result = await service.get_workflow_status(
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(f"Progress: {result['progress_percent']}%")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Verify project exists
                result = await session.execute(
                    select(Project).where(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project '{project_id}' not found"}

                # Get all MCPAgentJobs for this project/tenant
                jobs_result = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.tenant_key == tenant_key,
                        MCPAgentJob.project_id == project_id,
                    )
                )
                jobs = jobs_result.scalars().all()

                # Count by status
                working_like = {"active", "working"}
                active_count = sum(1 for job in jobs if job.status in working_like)
                completed_count = sum(1 for job in jobs if job.status in {"complete", "completed"})
                failed_count = sum(1 for job in jobs if job.status == "failed")
                pending_count = sum(1 for job in jobs if job.status in {"waiting", "pending"})
                total_count = len(jobs)

                # Calculate progress
                progress_percent = (completed_count / total_count * 100.0) if total_count > 0 else 0.0

                # Determine current stage
                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == total_count:
                    current_stage = "Completed"
                elif failed_count > 0:
                    current_stage = f"In Progress (with {failed_count} failure(s))"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                return {
                    "active_agents": active_count,
                    "completed_agents": completed_count,
                    "failed_agents": failed_count,
                    "pending_agents": pending_count,
                    "current_stage": current_stage,
                    "progress_percent": round(progress_percent, 2),
                    "total_agents": total_count,
                }

        except Exception as e:
            self._logger.exception(f"Failed to get workflow status: {e}")
            return {"error": f"Failed to get workflow status: {e!s}"}

    # ============================================================================
    # Agent Job Management
    # ============================================================================

    async def spawn_agent_job(
        self,
        agent_type: str,
        agent_name: str,
        mission: str,
        project_id: str,
        tenant_key: str,
        parent_job_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create an agent job with thin client architecture.

        Args:
            agent_type: Type of agent (e.g., "implementer", "analyzer")
            agent_name: Agent name/identifier
            mission: Agent mission description
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            parent_job_id: Optional parent job UUID for spawned agents

        Returns:
            Dict with success status, agent_job_id, and agent_prompt

        Example:
            >>> result = await service.spawn_agent_job(
            ...     agent_type="implementer",
            ...     agent_name="impl-1",
            ...     mission="Implement feature X",
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Get project for context
                result = await session.execute(
                    select(Project).where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == tenant_key
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": "NOT_FOUND", "message": "Project not found"}

                # Create agent job with mission STORED in database
                agent_job_id = str(uuid4())
                agent_job = MCPAgentJob(
                    job_id=agent_job_id,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    agent_type=agent_type,
                    agent_name=agent_name,
                    mission=mission,  # STORED HERE, not in prompt
                    spawned_by=parent_job_id,
                    status="waiting",  # Fixed: was "pending" but constraint only allows "waiting"
                    metadata={
                        "created_via": "thin_client_spawn",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "thin_client": True,
                    },
                )

                session.add(agent_job)
                await session.commit()
                await session.refresh(agent_job)

                # Generate THIN agent prompt (~10 lines)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}".

IDENTITY:
- Agent ID: {agent_job_id}
- Agent Type: {agent_type}
- Project ID: {project_id}
- Parent Orchestrator: {parent_job_id or "None"}

INSTRUCTIONS:
1. Fetch mission: get_agent_mission(agent_job_id='{agent_job_id}', tenant_key='{tenant_key}')
2. Execute mission
3. Report progress: update_job_progress('{agent_job_id}', percent, message)
4. Coordinate via: send_message(to_agent_id, content)

Begin by fetching your mission.
"""

                # Calculate token estimates
                prompt_tokens = len(thin_agent_prompt) // 4  # ~50 tokens
                mission_tokens = len(mission) // 4  # ~2000 tokens

                # Broadcast agent creation via WebSocket HTTP bridge
                self._logger.info(f"[WEBSOCKET DEBUG] About to broadcast agent:created for {agent_name} ({agent_type})")
                try:
                    import httpx

                    self._logger.info(f"[WEBSOCKET DEBUG] httpx imported for agent creation broadcast")

                    # Use HTTP bridge to emit WebSocket event (MCP runs in separate process)
                    async with httpx.AsyncClient() as client:
                        bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                        self._logger.info(f"[WEBSOCKET DEBUG] Sending POST to {bridge_url} for agent:created")

                        response = await client.post(
                            bridge_url,
                            json={
                                "event_type": "agent:created",
                                "tenant_key": tenant_key,
                                "data": {
                                    "project_id": project_id,
                                    "agent_id": agent_job_id,
                                    "agent_job_id": agent_job_id,
                                    "agent_type": agent_type,
                                    "agent_name": agent_name,
                                    "status": "waiting",
                                    "thin_client": True,
                                    "prompt_tokens": prompt_tokens,
                                    "mission_tokens": mission_tokens,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                            },
                            timeout=5.0,
                        )
                        self._logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response for agent:created: {response.status_code}")
                        self._logger.info(f"[WEBSOCKET] Broadcasted agent:created for {agent_name} ({agent_type}) via HTTP bridge")
                except Exception as ws_error:
                    self._logger.error(f"[WEBSOCKET ERROR] Failed to broadcast agent:created via HTTP bridge: {ws_error}", exc_info=True)

                return {
                    "success": True,
                    "agent_job_id": agent_job_id,
                    "agent_prompt": thin_agent_prompt,  # ~10 lines
                    "prompt_tokens": prompt_tokens,  # ~50
                    "mission_stored": True,
                    "mission_tokens": mission_tokens,  # ~2000
                    "total_tokens": prompt_tokens + mission_tokens,
                    "thin_client": True,
                }

        except Exception as e:
            self._logger.exception(f"Failed to spawn agent job: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Failed to spawn agent: {e!s}", "severity": "ERROR"}

    async def get_agent_mission(
        self,
        agent_job_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Get agent-specific mission from database.

        Args:
            agent_job_id: Agent job UUID
            tenant_key: Tenant key for isolation

        Returns:
            Dict with mission details and metadata

        Example:
            >>> result = await service.get_agent_mission(
            ...     agent_job_id="job-123",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == agent_job_id,
                            MCPAgentJob.tenant_key == tenant_key
                        )
                    )
                )
                agent_job = result.scalar_one_or_none()

                if not agent_job:
                    return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

                estimated_tokens = len(agent_job.mission or "") // 4

                return {
                    "success": True,
                    "agent_job_id": agent_job_id,
                    "agent_name": agent_job.agent_type,
                    "agent_type": agent_job.agent_type,
                    "mission": agent_job.mission or "",
                    "project_id": str(agent_job.project_id),
                    "parent_job_id": str(agent_job.spawned_by) if agent_job.spawned_by else None,
                    "estimated_tokens": estimated_tokens,
                    "status": agent_job.status,
                    "thin_client": True,
                }

        except Exception as e:
            self._logger.exception(f"Failed to get agent mission: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}

    async def get_pending_jobs(
        self,
        agent_type: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Get pending jobs for a specific agent type.

        Args:
            agent_type: Type of agent to get jobs for
            tenant_key: Tenant key for isolation

        Returns:
            Dict with list of pending jobs

        Example:
            >>> result = await service.get_pending_jobs(
            ...     agent_type="implementer",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            # Validate inputs
            if not agent_type or not agent_type.strip():
                return {"status": "error", "error": "agent_type cannot be empty", "jobs": [], "count": 0}

            if not tenant_key or not tenant_key.strip():
                return {"status": "error", "error": "tenant_key cannot be empty", "jobs": [], "count": 0}

            # Get pending jobs with tenant isolation (async)
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    select(MCPAgentJob)
                    .where(
                        MCPAgentJob.tenant_key == tenant_key,
                        MCPAgentJob.agent_type == agent_type,
                        MCPAgentJob.status == "waiting",
                    )
                    .limit(10)
                )
                jobs = result.scalars().all()

                # Format jobs for response
                formatted_jobs = []
                for job in jobs:
                    formatted_jobs.append({
                        "job_id": job.job_id,
                        "agent_type": job.agent_type,
                        "mission": job.mission,
                        "context_chunks": job.context_chunks or [],
                        "priority": "normal",
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                    })

                return {"status": "success", "jobs": formatted_jobs, "count": len(formatted_jobs)}

        except Exception as e:
            self._logger.exception(f"Failed to get pending jobs: {e}")
            return {"status": "error", "error": str(e), "jobs": [], "count": 0}

    async def acknowledge_job(
        self,
        job_id: str,
        agent_id: str,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Acknowledge job assignment (MCPAgentJob, async safe).

        Args:
            job_id: Job UUID
            agent_id: Agent identifier
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status and job details

        Example:
            >>> result = await service.acknowledge_job(
            ...     job_id="job-123",
            ...     agent_id="agent-456"
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}
            if not agent_id or not agent_id.strip():
                return {"status": "error", "error": "agent_id cannot be empty"}

            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                job = result.scalar_one_or_none()
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}

                # Idempotent
                if job.acknowledged and job.status in {"working", "active"}:
                    return {
                        "status": "success",
                        "job": {
                            "job_id": job.job_id,
                            "agent_type": job.agent_type,
                            "mission": job.mission,
                            "status": job.status,
                            "started_at": job.started_at.isoformat() if job.started_at else None,
                        },
                        "next_instructions": "Begin executing your mission",
                    }

                job.acknowledged = True
                # Normalize to 'working' for MCPAgentJob
                job.status = "working"
                job.started_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(job)

                return {
                    "status": "success",
                    "job": {
                        "job_id": job.job_id,
                        "agent_type": job.agent_type,
                        "mission": job.mission,
                        "status": job.status,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                    },
                    "next_instructions": "Begin executing your mission",
                }
        except Exception as e:
            self._logger.exception(f"Failed to acknowledge job: {e}")
            return {"status": "error", "error": str(e)}

    async def report_progress(
        self,
        job_id: str,
        progress: dict[str, Any],
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Report job progress (store message in message queue).

        Args:
            job_id: Job UUID
            progress: Progress data dict
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status

        Example:
            >>> result = await service.report_progress(
            ...     job_id="job-123",
            ...     progress={"percent": 50, "message": "Half done"}
            ... )
        """
        from giljo_mcp.agent_message_queue import AgentMessageQueue
        import json

        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}
            if not progress or not isinstance(progress, dict):
                return {"status": "error", "error": "progress must be a non-empty dict"}

            comm_queue = AgentMessageQueue(self.db_manager)  # Using compatibility layer
            async with self.db_manager.get_session_async() as session:
                # Serialize dict to string for message content
                content = json.dumps(progress)
                result = await comm_queue.send_message(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    from_agent=job_id,
                    to_agent=None,
                    message_type="progress",
                    content=content,
                    priority=1,
                    metadata=None,
                )
                if result.get("status") != "success":
                    return {"status": "error", "error": result.get("error")}

            return {"status": "success", "message": "Progress reported successfully"}
        except Exception as e:
            self._logger.exception(f"Failed to report progress: {e}")
            return {"status": "error", "error": str(e)}

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, Any],
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Mark job as complete (MCPAgentJob, async safe).

        Args:
            job_id: Job UUID
            result: Job result data dict
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status

        Example:
            >>> result = await service.complete_job(
            ...     job_id="job-123",
            ...     result={"output": "Task completed successfully"}
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}
            if not result or not isinstance(result, dict):
                return {"status": "error", "error": "result must be a non-empty dict"}

            async with self.db_manager.get_session_async() as session:
                res = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                job = res.scalar_one_or_none()
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}
                job.status = "complete"
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
                return {"status": "success", "job_id": job.job_id, "message": "Job completed successfully"}
        except Exception as e:
            self._logger.exception(f"Failed to complete job: {e}")
            return {"status": "error", "error": str(e)}

    async def report_error(
        self,
        job_id: str,
        error: str,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Report job error (MCPAgentJob, async safe).

        Args:
            job_id: Job UUID
            error: Error message
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status

        Example:
            >>> result = await service.report_error(
            ...     job_id="job-123",
            ...     error="Failed to compile code"
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}
            if not error or not error.strip():
                return {"status": "error", "error": "error message cannot be empty"}

            async with self.db_manager.get_session_async() as session:
                res = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                job = res.scalar_one_or_none()
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}
                job.status = "failed"
                job.failure_reason = "error"
                job.block_reason = error
                await session.commit()
                return {"status": "success", "job_id": job.job_id, "message": "Error reported"}
        except Exception as e:
            self._logger.exception(f"Failed to report error: {e}")
            return {"status": "error", "error": str(e)}

    async def list_jobs(
        self,
        tenant_key: str,
        project_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List agent jobs with flexible filtering.

        Supports filtering by project, status, and agent type with pagination.
        All jobs are filtered by tenant_key for multi-tenant isolation.

        Args:
            tenant_key: Tenant key for isolation (required)
            project_id: Filter by project UUID (optional)
            status_filter: Filter by status (waiting, active, completed, failed) (optional)
            agent_type: Filter by agent type (orchestrator, implementer, etc.) (optional)
            limit: Maximum results (default 100, max 500)
            offset: Pagination offset (default 0)

        Returns:
            Dict with structure:
            {
                "jobs": [list of job dicts],
                "total": int (total count matching filters),
                "limit": int (limit applied),
                "offset": int (offset applied)
            }

        Raises:
            Exception: Database errors (logged and returned in error field)

        Example:
            >>> result = await service.list_jobs(
            ...     tenant_key="tk_abc123",
            ...     project_id="proj_xyz",
            ...     status_filter="active"
            ... )
            >>> print(f"Found {len(result['jobs'])} active jobs")
        """
        try:
            from sqlalchemy import func, select
            from src.giljo_mcp.models import MCPAgentJob

            async with self.db_manager.get_session_async() as session:
                # Build query with filters
                query = select(MCPAgentJob).where(
                    MCPAgentJob.tenant_key == tenant_key
                )

                if project_id:
                    query = query.where(MCPAgentJob.project_id == project_id)
                if status_filter:
                    query = query.where(MCPAgentJob.status == status_filter)
                if agent_type:
                    query = query.where(MCPAgentJob.agent_type == agent_type)

                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar()

                # Apply pagination and order
                query = query.order_by(MCPAgentJob.created_at.desc())
                query = query.limit(limit).offset(offset)

                result = await session.execute(query)
                jobs = result.scalars().all()

                # Convert to dicts
                job_dicts = [
                    {
                        "id": job.id,
                        "job_id": job.job_id,
                        "tenant_key": job.tenant_key,
                        "project_id": job.project_id,
                        "agent_type": job.agent_type,
                        "agent_name": job.agent_name,
                        "mission": job.mission,
                        "status": job.status,
                        "progress": job.progress,
                        "spawned_by": job.spawned_by,
                        "tool_type": job.tool_type,
                        "context_chunks": job.context_chunks or [],
                        "messages": job.messages or [],
                        "acknowledged": job.acknowledged,
                        "started_at": job.started_at,
                        "completed_at": job.completed_at,
                        "created_at": job.created_at,
                        # Note: updated_at field removed - not present in MCPAgentJob model
                    }
                    for job in jobs
                ]

                self._logger.info(
                    f"Listed {len(job_dicts)} jobs (total={total}, "
                    f"project={project_id}, status={status_filter})"
                )

                return {
                    "jobs": job_dicts,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }

        except Exception as e:
            self._logger.exception(f"Failed to list jobs: {e}")
            return {"error": str(e)}
