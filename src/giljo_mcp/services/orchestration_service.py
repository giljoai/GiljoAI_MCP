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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
import tiktoken
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import MCPAgentJob, Project
from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from giljo_mcp.tenant import TenantManager

# Import MessageService for WebSocket-enabled messaging (Handover fix: message counter WebSocket)
# Using TYPE_CHECKING to document the type without circular import risk
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


def _generate_agent_protocol(job_id: str, tenant_key: str) -> str:
    """
    Generate the 5-phase agent lifecycle protocol (Handover 0334).

    This protocol is embedded in get_agent_mission() response to provide
    CLI subagents with self-documenting lifecycle instructions.

    Args:
        job_id: Agent job UUID for MCP tool calls
        tenant_key: Tenant key for MCP tool calls

    Returns:
        Multi-line protocol string with 5 phases and MCP tool references
    """
    return f"""## Agent Lifecycle Protocol (5 Phases)

### Phase 1: STARTUP (BEFORE ANY WORK)
1. Call `mcp__giljo-mcp__get_agent_mission(agent_job_id="{job_id}", tenant_key="{tenant_key}")` - Get mission
2. Call `mcp__giljo-mcp__acknowledge_job(job_id="{job_id}", agent_id="your-type")` - Mark as WORKING
3. Call `mcp__giljo-mcp__receive_messages(agent_id="your-type")` - Check for instructions
4. Review any messages and incorporate feedback BEFORE starting work

### Phase 2: EXECUTION
- Execute assigned tasks from mission
- Use todo lists to track progress internally
- Maintain focus on mission objectives

### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `mcp__giljo-mcp__report_progress(job_id="{job_id}", progress={{"percent": X, "message": "..."}})`
2. Call `mcp__giljo-mcp__receive_messages(agent_id="your-type")` - Check for new instructions
3. Incorporate any orchestrator feedback before continuing

### Phase 4: COMPLETION
1. Call `mcp__giljo-mcp__complete_job(job_id="{job_id}", result={{"summary": "...", "artifacts": [...]}})`
2. Await acknowledgment or further instructions

### Phase 5: ERROR HANDLING (If blocked)
1. Call `mcp__giljo-mcp__report_error(job_id="{job_id}", error="description")` - Marks job as BLOCKED
2. STOP work and await orchestrator guidance

---
**CRITICAL: MCP tools are NATIVE tool calls. Use them like Read/Write/Bash.**
**Do NOT use curl, HTTP, or SDK calls.**
"""


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

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
        message_service: Optional["MessageService"] = None,
    ):
        """
        Initialize OrchestrationService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            test_session: Optional AsyncSession for tests to share the same transaction
            message_service: Optional MessageService for WebSocket-enabled messaging
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._message_service = message_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.
        
        Returns:
            Context manager for database session
        """
        if self._test_session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session
            return _test_session_wrapper()
        
        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

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
            async with self._get_session() as session:
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
            async with self._get_session() as session:
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
        context_chunks: Optional[list[str]] = None,
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
            context_chunks: Optional context chunks for the agent

        Returns:
            Dict with success status, agent_job_id, and agent_prompt

        Example:
            >>> result = await service.spawn_agent_job(
            ...     agent_type="implementer",
            ...     agent_name="impl-1",
            ...     mission="Implement feature X",
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc",
            ...     context_chunks=["chunk1", "chunk2"]
            ... )
        """
        try:
            async with self._get_session() as session:
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
                metadata_dict = {
                    "created_via": "thin_client_spawn",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "thin_client": True,
                }
                if context_chunks:
                    metadata_dict["context_chunks"] = context_chunks

                agent_job = MCPAgentJob(
                    job_id=agent_job_id,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    agent_type=agent_type,
                    agent_name=agent_name,
                    mission=mission,  # STORED HERE, not in prompt
                    spawned_by=parent_job_id,
                    status="waiting",  # Fixed: was "pending" but constraint only allows "waiting"
                    metadata=metadata_dict,
                )

                # Set context tracking fields for orchestrators (Handover 0502)
                if agent_type == "orchestrator":
                    agent_job.context_budget = 200000  # Sonnet 4.5 default
                    # Estimate initial context usage from mission
                    try:
                        encoder = tiktoken.get_encoding("cl100k_base")
                        agent_job.context_used = len(encoder.encode(mission))
                    except Exception:
                        # Fallback estimation
                        agent_job.context_used = len(mission) // 4

                session.add(agent_job)
                await session.commit()
                await session.refresh(agent_job)

                # Generate THIN agent prompt (~10 lines)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}".

## CRITICAL: MCP TOOL USAGE

MCP tools are **NATIVE tool calls** - identical to Read, Write, Bash, Glob.
- CORRECT: Call `mcp__giljo-mcp__get_agent_mission` directly as a tool
- WRONG: curl, HTTP, fetch, requests, SDK calls

## MANDATORY STARTUP SEQUENCE

Execute these IN ORDER before starting your mission:

1. **Get Mission:**
   Tool: mcp__giljo-mcp__get_agent_mission
   Parameters: {{"agent_job_id": "{agent_job_id}", "tenant_key": "{tenant_key}"}}

2. **Acknowledge Job (marks you as WORKING):**
   Tool: mcp__giljo-mcp__acknowledge_job
   Parameters: {{"job_id": "{agent_job_id}", "agent_id": "{agent_type}"}}

3. **Check Messages (BEFORE starting work):**
   Tool: mcp__giljo-mcp__receive_messages
   Parameters: {{"agent_id": "{agent_type}"}}

4. **Execute your mission** (details in get_agent_mission response)

5. **Report Progress** (after each milestone):
   Tool: mcp__giljo-mcp__report_progress
   Parameters: {{"job_id": "{agent_job_id}", "progress": {{"percent": X, "message": "..."}}}}

6. **Complete Job** (when done):
   Tool: mcp__giljo-mcp__complete_job
   Parameters: {{"job_id": "{agent_job_id}", "result": {{"summary": "...", "artifacts": [...]}}}}

Your full mission is in the database. Call get_agent_mission to retrieve it.
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

        For CLI subagents (Handover 0262 / 0332), this method implements
        the atomic job start semantics:

        - On first successful fetch for a job in "waiting" status:
          - Sets mission_acknowledged_at (job acknowledged)
          - Transitions status waiting -> working
          - Sets started_at timestamp
          - Emits:
            - job:mission_acknowledged (drives "Job Acknowledged" column)
            - agent:status_changed (drives status chip)
        - On subsequent fetches:
          - Returns mission and metadata without mutating timestamps or status
          - Does NOT emit additional WebSocket events (idempotent re-read)

        Args:
            agent_job_id: Agent job UUID
            tenant_key: Tenant key for isolation

        Returns:
            Dict with mission details and metadata.
        """
        try:
            first_acknowledgement = False
            status_changed = False
            old_status: Optional[str] = None
            agent_job: Optional[MCPAgentJob] = None

            async with self._get_session() as session:
                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == agent_job_id,
                            MCPAgentJob.tenant_key == tenant_key,
                        )
                    )
                )
                agent_job = result.scalar_one_or_none()

                if not agent_job:
                    return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

                # Atomic start semantics on FIRST mission fetch
                if agent_job.mission_acknowledged_at is None:
                    now = datetime.now(timezone.utc)
                    first_acknowledgement = True
                    old_status = agent_job.status

                    agent_job.mission_acknowledged_at = now

                    # Only transition waiting -> working (do not touch other states)
                    if agent_job.status == "waiting":
                        agent_job.status = "working"
                        agent_job.started_at = now
                        status_changed = True

                    await session.commit()
                    await session.refresh(agent_job)

                    self._logger.info(
                        "[JOB SIGNALING] Mission acknowledged via get_agent_mission",
                        extra={
                            "agent_job_id": agent_job_id,
                            "agent_type": agent_job.agent_type,
                            "old_status": old_status,
                            "new_status": agent_job.status,
                        },
                    )

            # WebSocket emissions happen after the database transaction is complete
            if agent_job and first_acknowledgement:
                try:
                    import httpx

                    bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"

                    # 1) job:mission_acknowledged – drives "Job Acknowledged" column
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            bridge_url,
                            json={
                                "event_type": "job:mission_acknowledged",
                                "tenant_key": tenant_key,
                                "data": {
                                    "job_id": agent_job_id,
                                    "project_id": str(agent_job.project_id),
                                    "mission_acknowledged_at": agent_job.mission_acknowledged_at.isoformat(),
                                },
                            },
                            timeout=5.0,
                        )

                    # 2) agent:status_changed – only when we actually transitioned to working
                    if status_changed and old_status is not None:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                bridge_url,
                                json={
                                    "event_type": "agent:status_changed",
                                    "tenant_key": tenant_key,
                                    "data": {
                                        "job_id": agent_job_id,
                                        "agent_type": agent_job.agent_type,
                                        "agent_name": agent_job.agent_name,
                                        "old_status": old_status,
                                        "status": "working",
                                        "started_at": agent_job.started_at.isoformat()
                                        if agent_job.started_at
                                        else None,
                                    },
                                },
                                timeout=5.0,
                            )

                    self._logger.info(
                        "[WEBSOCKET] Emitted mission acknowledgment/start events for get_agent_mission",
                        extra={"agent_job_id": agent_job_id},
                    )
                except Exception as ws_error:
                    # Do not fail mission fetch on WebSocket bridge issues
                    self._logger.warning(
                        f"[WEBSOCKET] Failed to emit mission acknowledgment/status events: {ws_error}"
                    )

            if not agent_job:
                # Safety guard – should be unreachable due to earlier NOT_FOUND return
                return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

            estimated_tokens = len(agent_job.mission or "") // 4

            # Generate 6-phase lifecycle protocol (Handover 0334)
            full_protocol = _generate_agent_protocol(agent_job_id, tenant_key)

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
                "full_protocol": full_protocol,  # Handover 0334: 6-phase agent lifecycle
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
            async with self._get_session() as session:
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

            async with self._get_session() as session:
                result = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                job = result.scalar_one_or_none()
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}

                # Idempotent - if already in working status, return current state
                if job.status in {"working", "active"}:
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

                # Capture old status before updating
                old_status = job.status

                # Normalize to 'working' for MCPAgentJob
                job.status = "working"
                job.started_at = datetime.now(timezone.utc)
                job.mission_acknowledged_at = datetime.now(timezone.utc)  # Handover 0233
                await session.commit()
                await session.refresh(job)

            # WebSocket emission for real-time UI updates (after session closed)
            try:
                async with httpx.AsyncClient() as client:
                    bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                    await client.post(
                        bridge_url,
                        json={
                            "event_type": "agent:status_changed",
                            "tenant_key": tenant_key,
                            "data": {
                                "job_id": job_id,
                                "agent_type": job.agent_type,
                                "agent_name": job.agent_name,
                                "old_status": old_status,
                                "status": "working",
                                "started_at": job.started_at.isoformat() if job.started_at else None,
                            }
                        },
                        timeout=5.0,
                    )
                    self._logger.info(f"[WEBSOCKET] Broadcasted acknowledge_job status change for {job_id}")
            except Exception as ws_error:
                self._logger.warning(f"[WEBSOCKET] Failed to broadcast acknowledge_job: {ws_error}")
                # Don't fail the operation if WebSocket broadcast fails

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

            # Fetch job info to get project_id for MessageService
            job = None
            async with self._get_session() as session:
                res = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                job = res.scalar_one_or_none()

                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}

                # Optional TODO-style steps tracking for Steps column (Handover 0297)
                mode = progress.get("mode")
                if mode == "todo":
                    total_steps = progress.get("total_steps")
                    completed_steps = progress.get("completed_steps")
                    current_step = progress.get("current_step")

                    if (
                        isinstance(total_steps, int)
                        and total_steps > 0
                        and isinstance(completed_steps, int)
                        and 0 <= completed_steps <= total_steps
                    ):
                        # Persist latest TODO summary into job_metadata.todo_steps
                        from sqlalchemy.orm.attributes import flag_modified

                        metadata = job.job_metadata or {}
                        todo_steps = {
                            "total_steps": total_steps,
                            "completed_steps": completed_steps,
                        }
                        if isinstance(current_step, str) and current_step.strip():
                            todo_steps["current_step"] = current_step

                        metadata["todo_steps"] = todo_steps
                        job.job_metadata = metadata
                        flag_modified(job, "job_metadata")
                        await session.commit()
                        await session.refresh(job)

            if not job:
                return {"status": "error", "error": f"Job {job_id} not found"}

            # Serialize progress dict to string for message content
            content = json.dumps(progress)

            # Use MessageService if available (includes WebSocket emission)
            # Otherwise fall back to AgentMessageQueue (legacy, no WebSocket)
            if self._message_service:
                self._logger.info(f"[PROGRESS] Using MessageService with WebSocket for job {job_id}")
                result = await self._message_service.send_message(
                    to_agents=[job_id],  # Progress sent to self (stored in job's messages)
                    content=content,
                    project_id=job.project_id,
                    message_type="progress",
                    priority="normal",
                    from_agent=job_id,
                    tenant_key=tenant_key,
                )
                if not result.get("success"):
                    return {"status": "error", "error": result.get("error")}
            else:
                # Fallback to AgentMessageQueue (no WebSocket)
                self._logger.warning(f"[PROGRESS] Using AgentMessageQueue fallback (no WebSocket) for job {job_id}")
                from giljo_mcp.agent_message_queue import AgentMessageQueue
                comm_queue = AgentMessageQueue(self.db_manager)
                async with self._get_session() as session:
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

                # Legacy HTTP bridge for WebSocket (only when MessageService unavailable)
                try:
                    async with httpx.AsyncClient() as client:
                        bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                        await client.post(
                            bridge_url,
                            json={
                                "event_type": "message:new",
                                "tenant_key": tenant_key,
                                "data": {
                                    "job_id": job_id,
                                    "message_type": "progress",
                                    "from_agent": job.agent_name or job.agent_type,
                                    "progress": progress,
                                }
                            },
                            timeout=5.0,
                        )
                        self._logger.info(f"[WEBSOCKET] Broadcasted progress for {job_id} (via HTTP bridge)")
                except Exception as ws_error:
                    self._logger.warning(f"[WEBSOCKET] Failed to broadcast progress: {ws_error}")

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

            # Database update
            job = None
            old_status = None
            duration_seconds = None
            async with self._get_session() as session:
                res = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                job = res.scalar_one_or_none()
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}

                # Capture old status before updating
                old_status = job.status

                job.status = "complete"
                job.completed_at = datetime.now(timezone.utc)

                # Calculate duration if started_at exists
                if job.started_at and job.completed_at:
                    duration_seconds = (job.completed_at - job.started_at).total_seconds()

                await session.commit()

            # WebSocket emission for real-time UI updates (after session closed)
            if job:
                try:
                    async with httpx.AsyncClient() as client:
                        bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                        await client.post(
                            bridge_url,
                            json={
                                "event_type": "agent:status_changed",
                                "tenant_key": tenant_key,
                                "data": {
                                    "job_id": job_id,
                                    "agent_type": job.agent_type,
                                    "agent_name": job.agent_name,
                                    "old_status": old_status,
                                    "status": "complete",
                                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                                    "duration_seconds": duration_seconds,
                                }
                            },
                            timeout=5.0,
                        )
                        self._logger.info(f"[WEBSOCKET] Broadcasted complete_job status change for {job_id}")
                except Exception as ws_error:
                    self._logger.warning(f"[WEBSOCKET] Failed to broadcast complete_job: {ws_error}")

            return {"status": "success", "job_id": job.job_id if job else job_id, "message": "Job completed successfully"}
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

            async with self._get_session() as session:
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

            async with self._get_session() as session:
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
                job_dicts = []
                for job in jobs:
                    # DIAGNOSTIC: Log messages field for debugging persistence
                    messages_data = job.messages or []
                    self._logger.info(
                        f"[LIST_JOBS DEBUG] Agent {job.agent_type} ({job.job_id}): "
                        f"messages field = {messages_data!r} (type: {type(job.messages)})"
                    )

                    # Derive simple numeric steps summary from job_metadata.todo_steps (Handover 0297)
                    steps_summary = None
                    try:
                        metadata = job.job_metadata or {}
                        todo_steps = metadata.get("todo_steps") or {}
                        total_steps = todo_steps.get("total_steps")
                        completed_steps = todo_steps.get("completed_steps")
                        if (
                            isinstance(total_steps, int)
                            and total_steps > 0
                            and isinstance(completed_steps, int)
                            and 0 <= completed_steps <= total_steps
                        ):
                            steps_summary = {
                                "total": total_steps,
                                "completed": completed_steps,
                            }
                    except Exception:
                        # Do not break listing if metadata has unexpected shape
                        self._logger.warning(
                            "[LIST_JOBS] Failed to derive steps summary from job_metadata",
                            exc_info=True,
                        )

                    job_dicts.append({
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
                        "messages": messages_data,
                        "started_at": job.started_at,
                        "completed_at": job.completed_at,
                        "created_at": job.created_at,
                        "mission_acknowledged_at": job.mission_acknowledged_at,  # Handover 0297
                        "steps": steps_summary,
                        # Note: updated_at field removed - not present in MCPAgentJob model
                    })

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

    async def update_context_usage(
        self,
        job_id: str,
        additional_tokens: int,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Increment context_used for job and check 90% succession threshold.

        Args:
            job_id: Agent job UUID
            additional_tokens: Token count to add to context_used
            tenant_key: Tenant key for isolation (optional)

        Returns:
            Dict with success status, updated usage metrics, succession_triggered flag

        Raises:
            ValueError: If job not found
        """
        async with self._get_session() as session:
            # Get job with tenant isolation
            query = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)
            if tenant_key:
                query = query.where(MCPAgentJob.tenant_key == tenant_key)

            result = await session.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError("Job not found")

            # Increment context_used
            if job.context_used is None:
                job.context_used = 0
            job.context_used += additional_tokens

            # Calculate usage percentage
            usage_percentage = 0.0
            if job.context_budget and job.context_budget > 0:
                usage_percentage = (job.context_used / job.context_budget) * 100

            # Check if we need to trigger succession (90% threshold)
            succession_triggered = False
            if usage_percentage >= 90.0 and job.handover_to is None:
                await self._trigger_auto_succession(job, session)
                succession_triggered = True

            await session.commit()

            self._logger.info(
                f"Updated context usage for job {job_id}: "
                f"{job.context_used}/{job.context_budget} ({usage_percentage:.1f}%) "
                f"succession_triggered={succession_triggered}"
            )

            return {
                "success": True,
                "context_used": job.context_used,
                "context_budget": job.context_budget,
                "usage_percentage": usage_percentage,
                "succession_triggered": succession_triggered
            }

    async def estimate_message_tokens(self, message: str) -> int:
        """
        Estimate token count using tiktoken cl100k_base encoding.

        Args:
            message: Text message to estimate tokens for

        Returns:
            Estimated token count
        """
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(message))
        except Exception as e:
            self._logger.warning(f"Failed to estimate tokens with tiktoken: {e}, using fallback")
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(message) // 4

    async def _trigger_auto_succession(self, job: MCPAgentJob, session):
        """
        Auto-trigger succession when 90% threshold reached.

        Args:
            job: MCPAgentJob instance at 90%+ context usage
            session: Active database session

        Side effects:
            Creates successor via OrchestratorSuccessionManager
            Updates job.handover_to and job.succession_reason
        """
        try:
            # Create succession manager
            succession_manager = OrchestratorSuccessionManager(
                db_session=session,
                tenant_key=job.tenant_key
            )

            # Create successor
            successor = await succession_manager.create_successor(
                current_job_id=job.job_id,
                reason="context_limit"
            )

            # Update current job with succession info
            job.handover_to = successor.job_id
            job.succession_reason = "context_limit"

            self._logger.info(
                f"Auto-triggered succession for job {job.job_id} -> {successor.job_id} "
                f"(context limit reached)"
            )

        except Exception as e:
            self._logger.error(
                f"Failed to auto-trigger succession for job {job.job_id}: {e}",
                exc_info=True
            )
            # Don't raise - succession failure shouldn't block context update

    async def trigger_succession(
        self,
        job_id: str,
        reason: str = "manual",
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Manually trigger orchestrator succession.

        Args:
            job_id: Agent job UUID
            reason: Succession reason (default="manual")
            tenant_key: Tenant key for isolation (optional)

        Returns:
            Dict with success=True and successor job details

        Raises:
            ValueError: If job not found, not orchestrator, or already has successor
        """
        async with self._get_session() as session:
            # Get job with tenant isolation
            query = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)
            if tenant_key:
                query = query.where(MCPAgentJob.tenant_key == tenant_key)

            result = await session.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError("Job not found")

            # Validate: must be orchestrator
            if job.agent_type != "orchestrator":
                raise ValueError("Only orchestrator agents can trigger succession")

            # Validate: must not already have successor
            if job.handover_to is not None:
                raise ValueError("Job already has a successor")

            # Create successor (async-friendly path)
            parent_metadata = job.job_metadata or {}
            execution_mode = parent_metadata.get("execution_mode", "multi-terminal")
            # Reuse mission generator from succession manager for consistency
            succession_manager = OrchestratorSuccessionManager(
                db_session=session,
                tenant_key=job.tenant_key,
            )
            handover_mission = succession_manager._generate_handover_mission(job)  # type: ignore[protected-access]

            successor_metadata = {
                "execution_mode": execution_mode,
                "predecessor_id": job.job_id,
                "succession_reason": reason,
                "field_priorities": parent_metadata.get("field_priorities", {}),
                "depth_config": parent_metadata.get("depth_config", {}),
                "user_id": parent_metadata.get("user_id"),
                "tool": parent_metadata.get("tool", "universal"),
                "created_via": "orchestrator_succession",
            }

            successor = MCPAgentJob(
                tenant_key=job.tenant_key,
                job_id=str(uuid4()),
                agent_type="orchestrator",
                mission=handover_mission,
                status="waiting",
                instance_number=(job.instance_number or 0) + 1,
                spawned_by=job.job_id,
                project_id=job.project_id,
                context_used=0,
                context_budget=job.context_budget,
                context_chunks=[],
                messages=[],
                job_metadata=successor_metadata,
            )

            session.add(successor)

            # Update current job with succession info
            job.handover_to = successor.job_id
            job.succession_reason = reason

            await session.commit()

            self._logger.info(
                f"Manually triggered succession for job {job.job_id} -> {successor.job_id} "
                f"(reason: {reason})"
            )

            return {
                "success": True,
                "successor_job_id": successor.job_id,
                "successor_agent_name": successor.agent_name,
                "successor_instance_number": successor.instance_number,
                "reason": reason
            }
