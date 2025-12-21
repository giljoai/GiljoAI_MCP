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
from giljo_mcp.models import Project, AgentJob, AgentExecution
from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from giljo_mcp.tenant import TenantManager

# Import MessageService for WebSocket-enabled messaging (Handover fix: message counter WebSocket)
# Using TYPE_CHECKING to document the type without circular import risk
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


def _generate_team_context_header(
    current_job: "AgentExecution",
    all_project_jobs: list["AgentExecution"],
    mission_lookup: dict[str, str] | None = None
) -> str:
    """
    Generate team-aware context header for agent missions (Handover 0353, 0358b, 0367a).

    This header provides each agent with:
    - YOUR IDENTITY: Role + agent_id for MCP tool calls
    - YOUR TEAM: Roster of all agents on the project
    - YOUR DEPENDENCIES: Upstream/downstream relationships (inferred from roles)
    - COORDINATION: Messaging guidance

    Handover 0367a: Removed MCPAgentJob support - now AgentExecution only.
    For AgentExecution, mission is retrieved from mission_lookup dict or job relationship.

    Args:
        current_job: The agent execution receiving the mission
        all_project_jobs: All agent executions on the same project
        mission_lookup: Optional dict mapping job_id to mission text (for dual-model)

    Returns:
        Multi-line markdown header to prepend to the mission text
    """
    # AgentExecution only
    agent_name = getattr(current_job, 'agent_name', None) or getattr(current_job, 'agent_type', 'unknown')
    agent_type = getattr(current_job, 'agent_type', 'unknown')

    # For AgentExecution, use agent_id
    agent_id = getattr(current_job, 'agent_id', 'unknown')
    job_id = getattr(current_job, 'job_id', agent_id)

    # Build YOUR IDENTITY section (use agent_id for MCP calls)
    identity_section = f"""## YOUR IDENTITY
You are **{agent_name.upper()}** (agent_id: `{agent_id}`, job_id: `{job_id}`)
Role: {agent_type}
"""

    # Build YOUR TEAM section
    num_agents = len(all_project_jobs)
    team_rows = []
    for job in all_project_jobs:
        role_name = getattr(job, 'agent_name', None) or getattr(job, 'agent_type', 'unknown')

        # Get mission: try direct attribute, then job relationship, then lookup dict
        mission_text = ""
        if hasattr(job, 'mission') and job.mission:
            mission_text = job.mission
        elif hasattr(job, 'job') and hasattr(job.job, 'mission') and job.job.mission:
            mission_text = job.job.mission
        elif mission_lookup and hasattr(job, 'job_id') and job.job_id in mission_lookup:
            mission_text = mission_lookup[job.job_id]

        # Extract a short deliverable summary from the mission (first 80 chars)
        deliverable_preview = (mission_text or "")[:80].replace("\n", " ")
        if len(mission_text or "") > 80:
            deliverable_preview += "..."
        team_rows.append(f"| {role_name} | {getattr(job, 'agent_type', 'unknown')} | {deliverable_preview} |")

    team_table = "\n".join(team_rows)
    team_section = f"""## YOUR TEAM
This project has {num_agents} agent(s) working together:

| Agent | Role | Deliverables |
|-------|------|--------------|
{team_table}
"""

    # Build YOUR DEPENDENCIES section
    # Infer basic dependencies based on common role relationships
    dependencies_upstream = []
    dependencies_downstream = []

    # Common dependency patterns (can be expanded)
    dependency_rules = {
        "analyzer": {"upstream": [], "downstream": ["implementer", "documenter", "tester"]},
        "implementer": {"upstream": ["analyzer"], "downstream": ["tester", "reviewer", "documenter"]},
        "tester": {"upstream": ["implementer"], "downstream": ["reviewer"]},
        "reviewer": {"upstream": ["implementer", "tester"], "downstream": ["documenter"]},
        "documenter": {"upstream": ["analyzer", "implementer", "reviewer"], "downstream": []},
    }

    # Get other agents (exclude current by agent_id or job_id)
    current_id = getattr(current_job, 'agent_id', None) or getattr(current_job, 'job_id', None)
    other_agents = [
        j for j in all_project_jobs
        if (getattr(j, 'agent_id', None) or getattr(j, 'job_id', None)) != current_id
    ]
    other_types = {getattr(j, 'agent_type', 'unknown') for j in other_agents}

    if agent_type in dependency_rules:
        rules = dependency_rules[agent_type]
        for upstream in rules["upstream"]:
            if upstream in other_types:
                dependencies_upstream.append(upstream)
        for downstream in rules["downstream"]:
            if downstream in other_types:
                dependencies_downstream.append(downstream)

    if dependencies_upstream:
        upstream_text = f"- You depend on: {', '.join(dependencies_upstream)} (wait for their outputs if needed)"
    else:
        upstream_text = "- You depend on: None (you can start immediately)"

    if dependencies_downstream:
        downstream_text = f"- Others depend on you: {', '.join(dependencies_downstream)} (notify them when your work is ready)"
    else:
        downstream_text = "- Others depend on you: None"

    dependencies_section = f"""## YOUR DEPENDENCIES
{upstream_text}
{downstream_text}
"""

    # Build COORDINATION section
    coordination_section = """## COORDINATION
- Use `mcp__giljo-mcp__send_message` to notify teammates when your work is complete
- Use `mcp__giljo-mcp__receive_messages` to check for instructions or updates
- When you complete a deliverable, send a brief status message to downstream agents
- Check `full_protocol` for detailed messaging and progress reporting guidance

---

"""

    return identity_section + "\n" + team_section + "\n" + dependencies_section + "\n" + coordination_section


def _generate_agent_protocol(job_id: str, tenant_key: str, agent_name: str, agent_id: str | None = None) -> str:
    """
    Generate the 5-phase agent lifecycle protocol (Handover 0334, 0355, 0358b, 0359).

    This protocol is embedded in get_agent_mission() response to provide
    CLI subagents with self-documenting lifecycle instructions.

    Handover 0359: Fixed progress format to match backend implementation.
    Protocol now instructs mode="todo", completed_steps, total_steps, current_step
    instead of old steps_completed/steps_total format. This fixes Steps column
    tracking in Jobs table.

    Handover 0355: Enhanced message checking - Phase 2 checks after each task,
    Phase 3 reordered to check before reporting, Phase 4 gates on empty queue,
    plus "When to Check Messages" guidance section.

    Handover 0358b: Added agent_id parameter. In the dual-model architecture:
    - job_id = work order UUID (persists across succession)
    - agent_id = executor UUID (changes on succession)

    Args:
        job_id: Agent job UUID for MCP tool calls (work order)
        tenant_key: Tenant key for MCP tool calls
        agent_name: Agent name for acknowledge_job (matches template filename)
        agent_id: Optional executor UUID (defaults to job_id for backwards compat)

    Returns:
        Multi-line protocol string with 5 phases and MCP tool references
    """
    # Use agent_id if provided, otherwise fall back to job_id (backwards compat)
    executor_id = agent_id or job_id

    return f"""## Agent Lifecycle Protocol (5 Phases)

### Phase 1: STARTUP (BEFORE ANY WORK)
1. Call `mcp__giljo-mcp__get_agent_mission(agent_job_id="{job_id}", tenant_key="{tenant_key}")` - Get mission
2. Call `mcp__giljo-mcp__acknowledge_job(job_id="{job_id}", agent_id="{agent_name}")` - Mark as WORKING
3. Call `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}")` - Check for instructions
4. Review any messages and incorporate feedback BEFORE starting work

5. **MANDATORY: Create TodoWrite task list** (BEFORE implementation):
   - Break mission into 3-7 specific, actionable tasks
   - Count and announce: "X steps to complete: [list items]"
   - NEVER skip this step - planning prevents poor execution

### Phase 2: EXECUTION
Execute your assigned tasks (TodoWrite created in Phase 1):
- Maintain focus on mission objectives
- Update todos as you progress
- **MESSAGE CHECK**: Call `receive_messages()` after completing each TodoWrite task
  - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}")`
  - If queue not empty: Process messages BEFORE continuing
  - If queue empty: Safe to proceed

### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `receive_messages()` - MANDATORY before reporting
   - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}")`
2. Process ALL pending messages
3. Call `report_progress()` with current status
   - Full call: `mcp__giljo-mcp__report_progress(job_id="{job_id}", progress={{"mode": "todo", "completed_steps": Y, "total_steps": Z, "current_step": "task description", "percent": X}})`
   - Optional: Include "message" field for additional context

**MESSAGE HANDLING (CRITICAL - Issue 0361-5):**
- ALWAYS use `receive_messages()` to check messages (NOT `list_messages()`)
- `receive_messages()` auto-acknowledges and removes messages from queue
- `list_messages()` is read-only - messages stay pending (use for debugging only)

### Phase 4: COMPLETION
1. Call `receive_messages()` - Final message check
   - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}")`
2. Process any pending messages - ensure queue is empty
3. Call `complete_job()` - ONLY after queue is empty
   - Full call: `mcp__giljo-mcp__complete_job(job_id="{job_id}", result={{"summary": "...", "artifacts": [...]}})`

### Phase 5: ERROR HANDLING (If blocked)
1. Call `mcp__giljo-mcp__report_error(job_id="{job_id}", error="description")` - Marks job as BLOCKED
2. STOP work and await orchestrator guidance

---
**Your Identifiers:**
- job_id (work order): `{job_id}` - Use for mission, progress, completion
- agent_id (executor): `{executor_id}` - Use for messages

**When to Check Messages:**
- Phase 1 (STARTUP): Before starting work
- Phase 2 (EXECUTION): After each TodoWrite task
- Phase 3 (PROGRESS): Before reporting progress
- Phase 4 (COMPLETION): Before calling complete_job()

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
        Get workflow status for a project.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Counts execution statuses (waiting, working, complete, failed)
        - Job status comes from AgentJob (active, completed, cancelled)
        - Execution status from AgentExecution (execution progress)

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

                # Get all AgentExecutions for this project/tenant (join with AgentJob)
                jobs_result = await session.execute(
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        AgentExecution.tenant_key == tenant_key,
                        AgentJob.project_id == project_id,
                    )
                )
                rows = jobs_result.all()

                # Count by execution status
                executions = [row[0] for row in rows]
                working_like = {"active", "working"}
                active_count = sum(1 for execution in executions if execution.status in working_like)
                completed_count = sum(1 for execution in executions if execution.status in {"complete", "completed"})
                failed_count = sum(1 for execution in executions if execution.status == "failed")
                pending_count = sum(1 for execution in executions if execution.status in {"waiting", "pending"})
                total_count = len(executions)

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
        Create an agent job with thin client architecture using dual-model (AgentJob + AgentExecution).

        Handover 0358b: Migrated from MCPAgentJob (monolithic) to AgentJob + AgentExecution.
        - AgentJob: Work order (WHAT) - persists across succession
        - AgentExecution: Executor instance (WHO) - changes on succession

        Args:
            agent_type: Type of agent (e.g., "implementer", "analyzer")
            agent_name: Agent name/identifier
            mission: Agent mission description
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            parent_job_id: Optional parent agent_id for spawned agents (now refers to executor, not work order)
            context_chunks: Optional context chunks for the agent

        Returns:
            Dict with success status, job_id (work order), agent_id (executor), and agent_prompt

        Example:
            >>> result = await service.spawn_agent_job(
            ...     agent_type="implementer",
            ...     agent_name="impl-1",
            ...     mission="Implement feature X",
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc",
            ...     context_chunks=["chunk1", "chunk2"]
            ... )
            >>> result["job_id"]  # Work order UUID (persists)
            >>> result["agent_id"]  # Executor UUID (changes on succession)
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

                # Generate UUIDs for both job and execution
                job_id = str(uuid4())
                agent_id = str(uuid4())

                # Build job metadata
                metadata_dict = {
                    "created_via": "thin_client_spawn",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "thin_client": True,
                }
                if context_chunks:
                    metadata_dict["context_chunks"] = context_chunks

                # Create AgentJob (work order - WHAT)
                agent_job = AgentJob(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    project_id=project_id,
                    mission=mission,  # Mission stored ONCE in job, not execution
                    job_type=agent_type,
                    status="active",  # Job status: active, completed, cancelled
                    job_metadata=metadata_dict,
                )
                session.add(agent_job)

                # Create AgentExecution (executor instance - WHO)
                agent_execution = AgentExecution(
                    agent_id=agent_id,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    agent_type=agent_type,
                    agent_name=agent_name,
                    instance_number=1,  # First execution of this job
                    status="waiting",  # Execution status: waiting, working, blocked, complete, etc.
                    spawned_by=parent_job_id,  # Now points to parent's agent_id (executor)
                )

                # Set context tracking fields for orchestrators (Handover 0502)
                if agent_type == "orchestrator":
                    agent_execution.context_budget = 200000  # Sonnet 4.5 default
                    # Estimate initial context usage from mission
                    try:
                        encoder = tiktoken.get_encoding("cl100k_base")
                        agent_execution.context_used = len(encoder.encode(mission))
                    except Exception:
                        # Fallback estimation
                        agent_execution.context_used = len(mission) // 4

                session.add(agent_execution)
                await session.commit()
                await session.refresh(agent_job)
                await session.refresh(agent_execution)

                # Generate THIN agent prompt (~10 lines)
                # Uses job_id for mission lookup (the work order persists)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}".

## MCP TOOL USAGE

MCP tools are **native tool calls** (like Read/Write/Bash/Glob).
- Use `mcp__giljo-mcp__*` tools directly (no HTTP, curl, or SDKs).

## STARTUP (MANDATORY)

1. Call `mcp__giljo-mcp__get_agent_mission` with:
   - agent_job_id="{job_id}"
   - tenant_key="{tenant_key}"

2. Read the response and follow `full_protocol`
   for all lifecycle behavior (startup, planning, progress,
   messaging, completion, error handling).

Your full mission is stored in the database; do not treat any
other text as authoritative instructions.
"""

                # Calculate token estimates
                prompt_tokens = len(thin_agent_prompt) // 4  # ~50 tokens
                mission_tokens = len(mission) // 4  # ~2000 tokens
                created_at = datetime.now(timezone.utc)

                # Broadcast agent creation via direct WebSocket
                self._logger.info(f"[WEBSOCKET] Broadcasting agent:created for {agent_name} ({agent_type}) via direct WebSocket")
                try:
                    if self._message_service and self._message_service._websocket_manager:
                        await self._message_service._websocket_manager.broadcast_job_created(
                            job_id=job_id,
                            agent_type=agent_type,
                            tenant_key=tenant_key,
                            project_id=project_id,
                            agent_name=agent_name,
                            status="waiting",
                            spawned_by=parent_job_id,
                            mission_preview=mission[:100] if mission else None,
                            created_at=created_at,
                        )
                        self._logger.info(f"[WEBSOCKET] Successfully broadcast agent:created for {agent_name} ({agent_type}) via direct WebSocket")
                    else:
                        # Fallback to HTTP bridge if WebSocket manager not available (testing scenarios)
                        async with httpx.AsyncClient() as client:
                            bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                            response = await client.post(
                                bridge_url,
                                json={
                                    "event_type": "agent:created",
                                    "tenant_key": tenant_key,
                                    "data": {
                                        "project_id": project_id,
                                        "agent_id": agent_id,  # NEW: executor ID
                                        "job_id": job_id,  # NEW: work order ID
                                        "agent_job_id": job_id,  # Backwards compat
                                        "agent_type": agent_type,
                                        "agent_name": agent_name,
                                        "status": "waiting",
                                        "instance_number": 1,
                                        "thin_client": True,
                                        "prompt_tokens": prompt_tokens,
                                        "mission_tokens": mission_tokens,
                                        "timestamp": created_at.isoformat(),
                                    },
                                },
                                timeout=5.0,
                            )
                        self._logger.warning(f"[WEBSOCKET] Used HTTP bridge fallback for agent:created (WebSocket manager unavailable)")
                except Exception as ws_error:
                    self._logger.error(f"[WEBSOCKET ERROR] Failed to broadcast agent:created: {ws_error}", exc_info=True)

                return {
                    "success": True,
                    "job_id": job_id,  # NEW: Work order UUID (persists across succession)
                    "agent_id": agent_id,  # NEW: Executor UUID (changes on succession)
                    "agent_job_id": job_id,  # Backwards compat (deprecated, use job_id)
                    "agent_prompt": thin_agent_prompt,  # ~10 lines
                    "prompt_tokens": prompt_tokens,  # ~50
                    "mission_stored": True,
                    "mission_tokens": mission_tokens,  # ~2000
                    "total_tokens": prompt_tokens + mission_tokens,
                    "thin_client": True,
                    "instance_number": 1,  # NEW: First execution instance
                }

        except Exception as e:
            self._logger.error(f"[ERROR] Failed to spawn agent job: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": f"Failed to spawn agent: {e!s}", "severity": "ERROR"}

    async def get_agent_mission(
        self,
        agent_job_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Get agent-specific mission from database.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - agent_job_id parameter is actually job_id (work order UUID)
        - Queries AgentJob for mission
        - Queries latest active AgentExecution for the job
        - Mission acknowledgment logic applies to execution

        For CLI subagents (Handover 0262 / 0332), this method implements
        the atomic job start semantics:

        - On first successful fetch for an execution in "waiting" status:
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
            agent_job_id: Job UUID (work order - NOT executor agent_id)
            tenant_key: Tenant key for isolation

        Returns:
            Dict with mission details and metadata.
        """
        try:
            first_acknowledgement = False
            status_changed = False
            old_status: Optional[str] = None
            execution: Optional[AgentExecution] = None
            job: Optional[AgentJob] = None
            all_project_executions: list[AgentExecution] = []
            mission_lookup: dict[str, str] = {}

            async with self._get_session() as session:
                # Get the job (work order)
                job_result = await session.execute(
                    select(AgentJob).where(
                        and_(
                            AgentJob.job_id == agent_job_id,
                            AgentJob.tenant_key == tenant_key,
                        )
                    )
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

                # Get latest active execution for this job
                exec_result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.job_id == agent_job_id,
                            AgentExecution.tenant_key == tenant_key,
                            AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                        )
                    )
                    .order_by(AgentExecution.instance_number.desc())
                    .limit(1)
                )
                execution = exec_result.scalar_one_or_none()

                if not execution:
                    return {"error": "NOT_FOUND", "message": f"No active execution found for job {agent_job_id}"}

                # Handover 0353: Fetch all project executions for team context
                if job.project_id:
                    all_exec_result = await session.execute(
                        select(AgentExecution, AgentJob)
                        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                        .where(
                            and_(
                                AgentJob.project_id == job.project_id,
                                AgentExecution.tenant_key == tenant_key,
                            )
                        )
                    )
                    rows = all_exec_result.all()
                    all_project_executions = [row[0] for row in rows]

                    # Build mission lookup for team context generation
                    for exec_row, job_row in rows:
                        mission_lookup[job_row.job_id] = job_row.mission
                else:
                    all_project_executions = [execution]
                    mission_lookup[job.job_id] = job.mission

                # Atomic start semantics on FIRST mission fetch
                if execution.mission_acknowledged_at is None:
                    now = datetime.now(timezone.utc)
                    first_acknowledgement = True
                    old_status = execution.status

                    execution.mission_acknowledged_at = now

                    # Only transition waiting -> working (do not touch other states)
                    if execution.status == "waiting":
                        execution.status = "working"
                        execution.started_at = now
                        status_changed = True

                    await session.commit()
                    await session.refresh(execution)

                    self._logger.info(
                        "[JOB SIGNALING] Mission acknowledged via get_agent_mission",
                        extra={
                            "job_id": agent_job_id,
                            "agent_id": execution.agent_id,
                            "agent_type": execution.agent_type,
                            "old_status": old_status,
                            "new_status": execution.status,
                        },
                    )

            # WebSocket emissions happen after the database transaction is complete
            if execution and first_acknowledgement:
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
                                    "agent_id": execution.agent_id,
                                    "project_id": str(job.project_id),
                                    "mission_acknowledged_at": execution.mission_acknowledged_at.isoformat(),
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
                                        "agent_id": execution.agent_id,
                                        "agent_type": execution.agent_type,
                                        "agent_name": execution.agent_name,
                                        "old_status": old_status,
                                        "status": "working",
                                        "started_at": execution.started_at.isoformat()
                                        if execution.started_at
                                        else None,
                                    },
                                },
                                timeout=5.0,
                            )

                    self._logger.info(
                        "[WEBSOCKET] Emitted mission acknowledgment/start events for get_agent_mission",
                        extra={"job_id": agent_job_id, "agent_id": execution.agent_id},
                    )
                except Exception as ws_error:
                    # Do not fail mission fetch on WebSocket bridge issues
                    self._logger.warning(
                        f"[WEBSOCKET] Failed to emit mission acknowledgment/status events: {ws_error}"
                    )

            if not execution or not job:
                # Safety guard – should be unreachable due to earlier NOT_FOUND return
                return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

            # Handover 0353: Generate team-aware mission with context header
            team_context_header = _generate_team_context_header(
                execution,
                all_project_executions,
                mission_lookup=mission_lookup
            )
            raw_mission = job.mission or ""
            full_mission = team_context_header + raw_mission

            estimated_tokens = len(full_mission) // 4

            # Generate 5-phase lifecycle protocol (Handover 0334, 0359)
            full_protocol = _generate_agent_protocol(agent_job_id, tenant_key, execution.agent_type)

            return {
                "success": True,
                "agent_job_id": agent_job_id,  # Backwards compat (deprecated, use job_id)
                "job_id": job.job_id,  # Work order UUID
                "agent_id": execution.agent_id,  # Executor UUID
                "agent_name": execution.agent_type,
                "agent_type": execution.agent_type,
                "mission": full_mission,  # Handover 0353: Team-aware mission with context header
                "project_id": str(job.project_id),
                "parent_job_id": str(execution.spawned_by) if execution.spawned_by else None,
                "estimated_tokens": estimated_tokens,
                "status": execution.status,  # Execution status
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

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Queries AgentExecution.status for execution state (waiting, working, etc.)
        - Mission comes from AgentJob via join
        - Returns both job_id (work order) and agent_id (executor)

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

            # Get pending executions with their jobs (dual-model)
            async with self._get_session() as session:
                result = await session.execute(
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.agent_type == agent_type,
                        AgentExecution.status == "waiting",  # Execution status, not job status
                    )
                    .limit(10)
                )
                rows = result.all()

                # Format jobs for response
                formatted_jobs = []
                for execution, job in rows:
                    formatted_jobs.append({
                        "job_id": job.job_id,  # Work order ID
                        "agent_id": execution.agent_id,  # Executor ID
                        "agent_job_id": job.job_id,  # Backwards compat (deprecated)
                        "agent_type": execution.agent_type,
                        "mission": job.mission,  # Mission from AgentJob
                        "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
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
        Acknowledge job assignment (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
            agent_id: Agent identifier (for backwards compatibility, not used in query)
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
                # Get latest active execution for this job
                stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                    )
                    .order_by(AgentExecution.instance_number.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if not execution:
                    return {"status": "error", "error": f"No active execution found for job {job_id}"}

                # Get job for mission details
                job_result = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id)
                )
                job = job_result.scalar_one_or_none()
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}

                # Idempotent - if already in working status, return current state
                if execution.status in {"working"}:
                    return {
                        "status": "success",
                        "job": {
                            "job_id": job.job_id,
                            "agent_type": execution.agent_type,
                            "mission": job.mission,
                            "status": execution.status,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                        },
                        "next_instructions": "Begin executing your mission",
                    }

                # Capture old status before updating
                old_status = execution.status

                # Update execution to 'working' status
                execution.status = "working"
                execution.started_at = datetime.now(timezone.utc)
                execution.mission_acknowledged_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(execution)

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
                                "agent_type": execution.agent_type,
                                "agent_name": execution.agent_name,
                                "old_status": old_status,
                                "status": "working",
                                "started_at": execution.started_at.isoformat() if execution.started_at else None,
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
                    "agent_type": execution.agent_type,
                    "mission": job.mission,
                    "status": execution.status,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
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

            # Fetch execution and job info for progress tracking
            job = None
            execution = None
            async with self._get_session() as session:
                # Get latest active execution
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                    )
                    .order_by(AgentExecution.instance_number.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    return {"status": "error", "error": f"No active execution found for job {job_id}"}

                # Get job for metadata and project_id
                job_res = await session.execute(
                    select(AgentJob).where(AgentJob.job_id == job_id)
                )
                job = job_res.scalar_one_or_none()

                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}

                # Update execution progress fields
                execution.last_progress_at = datetime.now(timezone.utc)

                # Extract progress percentage and current task from progress dict
                if "percent" in progress:
                    execution.progress = min(100, max(0, int(progress["percent"])))
                if "message" in progress or "current_step" in progress:
                    execution.current_task = progress.get("message") or progress.get("current_step")

                # Optional TODO-style steps tracking for Steps column (Handover 0297)
                # Store in AgentJob.job_metadata (job-level data)
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
                await session.refresh(execution)
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
        Mark job as complete (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
            result: Job result data dict (for backwards compatibility, not currently used)
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
            execution = None
            old_status = None
            duration_seconds = None
            async with self._get_session() as session:
                # Try new dual-model path first
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                    )
                    .order_by(AgentExecution.instance_number.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if execution:
                    # NEW PATH: Dual-model (AgentExecution)
                    # Get job
                    job_res = await session.execute(
                        select(AgentJob).where(AgentJob.job_id == job_id)
                    )
                    job = job_res.scalar_one_or_none()
                    if not job:
                        return {"status": "error", "error": f"Job {job_id} not found"}

                    # Capture old status before updating
                    old_status = execution.status

                    # Update execution status
                    execution.status = "complete"
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.progress = 100  # Set to 100% on completion

                    # Calculate duration if started_at exists
                    if execution.started_at and execution.completed_at:
                        duration_seconds = (execution.completed_at - execution.started_at).total_seconds()

                    # Also update job status to completed if this is the last active execution
                    # Check if there are any other active executions
                    other_active_stmt = (
                        select(AgentExecution)
                        .where(
                            AgentExecution.job_id == job_id,
                            AgentExecution.agent_id != execution.agent_id,
                            AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                        )
                    )
                    other_active_res = await session.execute(other_active_stmt)
                    other_active = other_active_res.scalar_one_or_none()

                    if not other_active:
                        # No other active executions, mark job as completed
                        job.status = "completed"
                        job.completed_at = execution.completed_at

                    await session.commit()
                else:
                    # No active execution found
                    return {"status": "error", "error": f"No active execution found for job {job_id}"}

            # WebSocket emission for real-time UI updates (after session closed)
            if execution:
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
                                    "agent_type": execution.agent_type,
                                    "agent_name": execution.agent_name,
                                    "old_status": old_status,
                                    "status": "complete",
                                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                                    "duration_seconds": duration_seconds,
                                }
                            },
                            timeout=5.0,
                        )
                        self._logger.info(f"[WEBSOCKET] Broadcasted complete_job status change for {job_id}")
                except Exception as ws_error:
                    self._logger.warning(f"[WEBSOCKET] Failed to broadcast complete_job: {ws_error}")

            return {"status": "success", "job_id": job_id, "message": "Job completed successfully"}
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
        Report job error (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
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
                # Get latest active execution
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                    )
                    .order_by(AgentExecution.instance_number.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    return {"status": "error", "error": f"No active execution found for job {job_id}"}

                # Update execution status to failed
                execution.status = "failed"
                execution.failure_reason = "error"
                execution.block_reason = error

                await session.commit()
                return {"status": "success", "job_id": job_id, "message": "Error reported"}
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

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Joins AgentExecution with AgentJob to get complete data
        - Mission comes from AgentJob
        - Status, progress, timestamps from AgentExecution
        - Returns both job_id (work order) and agent_id (executor)

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

            async with self._get_session() as session:
                # Build query with filters (join AgentExecution with AgentJob)
                query = (
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(AgentExecution.tenant_key == tenant_key)
                )

                if project_id:
                    query = query.where(AgentJob.project_id == project_id)
                if status_filter:
                    query = query.where(AgentExecution.status == status_filter)
                if agent_type:
                    query = query.where(AgentExecution.agent_type == agent_type)

                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar()

                # Apply pagination and order
                query = query.order_by(AgentJob.created_at.desc())
                query = query.limit(limit).offset(offset)

                result = await session.execute(query)
                rows = result.all()

                # Convert to dicts
                job_dicts = []
                for execution, job in rows:
                    # DIAGNOSTIC: Log messages field for debugging persistence
                    messages_data = execution.messages or []
                    self._logger.info(
                        f"[LIST_JOBS DEBUG] Agent {execution.agent_type} (job={job.job_id}, agent={execution.agent_id}): "
                        f"messages field = {messages_data!r} (type: {type(execution.messages)})"
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
                        "id": execution.agent_id,  # Executor ID (backwards compat - was job.id)
                        "job_id": job.job_id,  # Work order ID
                        "agent_id": execution.agent_id,  # Executor ID
                        "agent_job_id": job.job_id,  # Backwards compat (deprecated)
                        "tenant_key": execution.tenant_key,
                        "project_id": job.project_id,
                        "agent_type": execution.agent_type,
                        "agent_name": execution.agent_name,
                        "mission": job.mission,  # Mission from AgentJob
                        "status": execution.status,  # Execution status
                        "progress": execution.progress,  # Execution progress
                        "spawned_by": execution.spawned_by,  # Parent agent_id
                        "tool_type": execution.tool_type,
                        "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
                        "messages": messages_data,
                        "started_at": execution.started_at,
                        "completed_at": execution.completed_at,
                        "created_at": job.created_at,  # Job creation time
                        "mission_acknowledged_at": execution.mission_acknowledged_at,  # Handover 0297
                        "steps": steps_summary,
                        # Note: updated_at field removed - not present in models
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
        Increment context_used for execution and check 90% succession threshold.

        Args:
            job_id: Agent job UUID (looks up latest active execution)
            additional_tokens: Token count to add to context_used
            tenant_key: Tenant key for isolation (optional)

        Returns:
            Dict with success status, updated usage metrics, succession_triggered flag

        Raises:
            ValueError: If no active execution found
        """
        async with self._get_session() as session:
            # Get latest active execution with tenant isolation
            exec_stmt = (
                select(AgentExecution)
                .where(
                    AgentExecution.job_id == job_id,
                    AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"])
                )
            )
            if tenant_key:
                exec_stmt = exec_stmt.where(AgentExecution.tenant_key == tenant_key)

            exec_stmt = exec_stmt.order_by(AgentExecution.instance_number.desc()).limit(1)

            result = await session.execute(exec_stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError("No active execution found for job")

            # Increment context_used
            if execution.context_used is None:
                execution.context_used = 0
            execution.context_used += additional_tokens

            # Calculate usage percentage
            usage_percentage = 0.0
            if execution.context_budget and execution.context_budget > 0:
                usage_percentage = (execution.context_used / execution.context_budget) * 100

            # Check if we need to trigger succession (90% threshold)
            succession_triggered = False
            if usage_percentage >= 90.0 and execution.succeeded_by is None:
                await self._trigger_auto_succession(execution, session)
                succession_triggered = True

            await session.commit()

            self._logger.info(
                f"Updated context usage for job {job_id}: "
                f"{execution.context_used}/{execution.context_budget} ({usage_percentage:.1f}%) "
                f"succession_triggered={succession_triggered}"
            )

            return {
                "success": True,
                "context_used": execution.context_used,
                "context_budget": execution.context_budget,
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

    async def _trigger_auto_succession(self, execution: AgentExecution, session):
        """
        Auto-trigger succession when 90% threshold reached.

        Handover 0358b: Migrated from MCPAgentJob to dual-model (AgentJob + AgentExecution).
        Creates new AgentExecution on SAME job, not new job.

        Args:
            execution: Current execution that reached threshold
            session: Database session (must be same session as caller)
        """
        # Create successor execution using OrchestratorSuccessionManager
        succession_manager = OrchestratorSuccessionManager(
            db_session=session,
            tenant_key=execution.tenant_key,
        )

        successor_execution = await succession_manager.create_successor(
            current_execution=execution,
            reason="context_limit"
        )

        # Generate handover summary for the successor
        handover_summary = succession_manager.generate_handover_summary(execution)

        # Store handover summary directly in execution field (handover_summary is JSONB column)
        successor_execution.handover_summary = handover_summary

        # Note: create_successor() already committed, this stores handover summary
        # Caller's commit will persist handover_summary update

        self._logger.info(
            f"Auto-triggered succession for execution {execution.agent_id} -> {successor_execution.agent_id} "
            f"(job_id: {execution.job_id}, instance: {execution.instance_number} -> {successor_execution.instance_number}, "
            f"reason: context_limit)"
        )

    async def trigger_succession(
        self,
        job_id: str,
        reason: str = "manual",
        tenant_key: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Manually trigger orchestrator succession.

        Handover 0358b: Migrated from MCPAgentJob to dual-model (AgentJob + AgentExecution).
        Creates new AgentExecution on SAME job, not new job.

        Args:
            job_id: Work order UUID (for backwards compatibility, can also be agent_id)
            reason: Succession reason (default="manual")
            tenant_key: Tenant key for isolation (optional)
            agent_id: Optional executor UUID (if not provided, job_id is treated as agent_id for backwards compat)

        Returns:
            Dict with success=True, job_id (work order), successor_agent_id (new executor), and instance number
            Also includes deprecated successor_job_id for backwards compatibility (same as job_id)

        Raises:
            ValueError: If execution not found, not orchestrator, or already has successor
        """
        async with self._get_session() as session:
            # Determine which ID to use (backwards compatibility: job_id could be agent_id)
            # In the dual-model: agent_id is the executor, job_id is the work order
            executor_id = agent_id or job_id

            # Try to find execution by agent_id first (new dual-model path)
            query = select(AgentExecution).where(AgentExecution.agent_id == executor_id)
            if tenant_key:
                query = query.where(AgentExecution.tenant_key == tenant_key)

            result = await session.execute(query)
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError("Execution not found")

            # Dual-model succession (AgentExecution)
            # Validate: must be orchestrator
            if execution.agent_type != "orchestrator":
                raise ValueError("Only orchestrator agents can trigger succession")

            # Validate: must not already have successor
            if execution.succeeded_by is not None:
                raise ValueError("Execution already has a successor")

            # Create successor execution using OrchestratorSuccessionManager
            succession_manager = OrchestratorSuccessionManager(
                db_session=session,
                tenant_key=execution.tenant_key,
            )

            successor_execution = await succession_manager.create_successor(
                current_execution=execution,
                reason=reason
            )

            # Generate handover summary for the successor
            handover_summary = succession_manager.generate_handover_summary(execution)

            # Store handover summary directly in execution field (handover_summary is JSONB column)
            successor_execution.handover_summary = handover_summary

            await session.commit()
            await session.refresh(successor_execution)

            self._logger.info(
                f"Manually triggered succession for execution {execution.agent_id} -> {successor_execution.agent_id} "
                f"(job_id: {execution.job_id}, instance: {execution.instance_number} -> {successor_execution.instance_number}, "
                f"reason: {reason})"
            )

            return {
                "success": True,
                "job_id": execution.job_id,  # Work order ID (stays same)
                "successor_agent_id": successor_execution.agent_id,  # NEW executor
                "successor_instance_number": successor_execution.instance_number,
                "instance_number": successor_execution.instance_number,
                "reason": reason,
                # Backwards compatibility (deprecated):
                "successor_job_id": execution.job_id,  # Same as job_id in dual-model
                "successor_agent_name": successor_execution.agent_name,
            }
