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
from pathlib import Path

# Import MessageService for WebSocket-enabled messaging (Handover fix: message counter WebSocket)
# Using TYPE_CHECKING to document the type without circular import risk
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

import tiktoken
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# WorkflowEngine import moved to coordinate_agent_workflow() to avoid circular import
from src.giljo_mcp.agent_selector import AgentSelector
from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.enums import AgentRole, ProjectType
from src.giljo_mcp.exceptions import (
    OrchestrationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import (
    AgentExecution,
    AgentJob,
    AgentTemplate,
    AgentTodoItem,
    Message,
    Product,
    ProductMemoryEntry,
    Project,
)
from src.giljo_mcp.optimization import MissionOptimizationInjector, SerenaOptimizer
from src.giljo_mcp.template_adapter import MissionTemplateGeneratorV2
from src.giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


def _generate_team_context_header(
    current_job: "AgentExecution",
    all_project_jobs: list["AgentExecution"],
    mission_lookup: dict[str, str] | None = None,
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
    agent_name = getattr(current_job, "agent_name", None) or getattr(current_job, "agent_display_name", "unknown")
    agent_display_name = getattr(current_job, "agent_display_name", "unknown")

    # For AgentExecution, use agent_id
    agent_id = getattr(current_job, "agent_id", "unknown")
    job_id = getattr(current_job, "job_id", agent_id)

    # Build YOUR IDENTITY section (use agent_id for MCP calls)
    identity_section = f"""## YOUR IDENTITY
You are **{agent_name.upper()}** (agent_id: `{agent_id}`, job_id: `{job_id}`)
Role: {agent_display_name}
"""

    # Build YOUR TEAM section
    num_agents = len(all_project_jobs)
    team_rows = []
    for job in all_project_jobs:
        role_name = getattr(job, "agent_name", None) or getattr(job, "agent_display_name", "unknown")

        # Get mission: prefer lookup dict (avoids lazy load), then direct attribute
        # IMPORTANT: Check mission_lookup FIRST to avoid SQLAlchemy lazy load errors
        # when AgentExecution objects are accessed outside session context (Handover 0366 fix)
        mission_text = ""
        if mission_lookup and hasattr(job, "job_id") and job.job_id in mission_lookup:
            mission_text = mission_lookup[job.job_id]
        elif hasattr(job, "mission") and job.mission:
            mission_text = job.mission

        # Extract a short deliverable summary from the mission (first 80 chars)
        deliverable_preview = (mission_text or "")[:80].replace("\n", " ")
        if len(mission_text or "") > 80:
            deliverable_preview += "..."
        job_agent_id = getattr(job, "agent_id", "unknown")
        team_rows.append(
            f"| {role_name} | `{job_agent_id}` | {getattr(job, 'agent_display_name', 'unknown')} | {deliverable_preview} |"
        )

    team_table = "\n".join(team_rows)
    team_section = f"""## YOUR TEAM
This project has {num_agents} agent(s) working together:

| Agent | agent_id | Role | Deliverables |
|-------|----------|------|--------------|
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
    current_id = getattr(current_job, "agent_id", None) or getattr(current_job, "job_id", None)
    other_agents = [
        j for j in all_project_jobs if (getattr(j, "agent_id", None) or getattr(j, "job_id", None)) != current_id
    ]
    other_types = {getattr(j, "agent_display_name", "unknown") for j in other_agents}

    if agent_display_name in dependency_rules:
        rules = dependency_rules[agent_display_name]
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
        downstream_text = (
            f"- Others depend on you: {', '.join(dependencies_downstream)} (notify them when your work is ready)"
        )
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
    Generate the 5-phase agent lifecycle protocol (Handover 0334, 0355, 0358b, 0359, 0378, 0392).

    This protocol is embedded in get_agent_mission() response to provide
    CLI subagents with self-documenting lifecycle instructions.

    Handover 0392: Simplified progress reporting - agents now send only todo_items array,
    backend calculates percent/steps automatically. Removed redundant field instructions.

    Handover 0378: Fixed three protocol bugs:
    - Bug 2: Protocol now shows distinct job_id and agent_id values (not both job_id)
    - Bug 3: All receive_messages() examples include tenant_key parameter
    - Bug 4: Added "Sync TodoWrite with MCP Progress" section with explicit instructions

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
0. **ENVIRONMENT DETECTION**:
   Detect your OS before executing tasks:
   Call: python -c "import platform; print(platform.system())"
   Store result (Windows/Linux/Darwin) and adapt shell commands to your platform
   - Sleep: Windows 'timeout /t N /nobreak' | Unix 'sleep N'
   - Clear: Windows 'cls' | Unix 'clear'
   - Path separator: Windows '\' | Unix '/'

   **CONTEXT AWARENESS**: Your mission contains authoritative values including `project_path`.
   When creating files or referencing directories, use context-provided paths.
   Do NOT hardcode paths observed in your terminal environment.

1. Call `mcp__giljo-mcp__get_agent_mission(job_id="{job_id}", tenant_key="{tenant_key}")` - Get mission
2. Call `mcp__giljo-mcp__acknowledge_job(job_id="{job_id}", agent_id="{agent_name}")` - Mark as WORKING
3. Call `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` - Check for instructions
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
  - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
  - If queue not empty: Process messages BEFORE continuing
  - If queue empty: Safe to proceed

### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `receive_messages()` - MANDATORY before reporting
   - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
2. Process ALL pending messages
3. Call `report_progress()` with your todo_items:

   mcp__giljo-mcp__report_progress(
       job_id="{job_id}",
       tenant_key="{tenant_key}",
       todo_items=[
           {{{{"content": "Task 1 description", "status": "completed"}}}},
           {{{{"content": "Task 2 description", "status": "in_progress"}}}},
           {{{{"content": "Task 3 description", "status": "pending"}}}}
       ]
   )

**Backend automatically calculates percent and step counts from your list.**
Status values: "pending", "in_progress", "completed"

### CRITICAL: Sync TodoWrite with MCP Progress (Handover 0392)

Every time you update TodoWrite status (mark item complete or in_progress),
IMMEDIATELY call report_progress() with your updated todo_items list.

The todo_items array appears in the Plan/TODOs tab of the dashboard.
Do NOT skip this step - the backend cannot see your TodoWrite updates.

### BACKEND MONITORING ACTIVE (Handover 0406)
The backend monitors report_progress() calls. If todo_items is missing:
- You will receive a WARNING in the response
- Warnings are throttled (1 per 5 minutes per job)
- Dashboard cannot display your progress without todo_items

**MESSAGE HANDLING (CRITICAL - Issue 0361-5):**
- ALWAYS use `receive_messages()` to check messages (NOT `list_messages()`)
- `receive_messages()` auto-acknowledges and removes messages from queue
- `list_messages()` is read-only - messages stay pending (use for debugging only)

### Phase 4: COMPLETION
Before calling `complete_job()`, you MUST verify:
1. All TODO items completed (your TodoWrite list is fully marked completed)
2. All messages read (queue empty after `receive_messages()`)

Final steps:
1. Call `receive_messages()` - Final message check
   - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
2. Process any pending messages - ensure queue is empty
3. Call `complete_job()` - ONLY after TODOs are complete and queue is empty
   - Full call: `mcp__giljo-mcp__complete_job(job_id="{job_id}", result={{"summary": "...", "artifacts": [...]}})`

If you call `complete_job()` without meeting these requirements:
- System will REJECT your completion
- Response will list specific blockers (unread messages, incomplete TODOs)

### Phase 5: ERROR HANDLING & BLOCKED STATUS

**To mark yourself BLOCKED** (unclear requirements, waiting for clarification):
1. Call `mcp__giljo-mcp__report_error(job_id="{job_id}", error="BLOCKED: <reason>")`
   - Sets status to "blocked" and stores block_reason
2. Send message to orchestrator explaining what you need:
   - `mcp__giljo-mcp__send_message(to_agents=["orchestrator"], content="BLOCKER: <details>", ...)`
3. STOP work and poll for response:
   - `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`

**To resume from BLOCKED**:
1. After receiving guidance, call `acknowledge_job()` again:
   - `mcp__giljo-mcp__acknowledge_job(job_id="{job_id}", agent_id="{agent_name}")`
   - Sets status back to "working"
2. Continue execution with Phase 2

**Use BLOCKED for**: Unclear requirements, missing context, waiting for decisions (recoverable)

**To mark yourself FAILED** (unrecoverable error, intentional failure):
1. Call `mcp__giljo-mcp__set_agent_status(
       agent_id="{executor_id}",
       tenant_key="{tenant_key}",
       status="failed",
       reason="<failure reason>"
   )`
2. This is a TERMINAL state - no further work expected
3. Do NOT call complete_job() after failing

**Use FAILED for**: Unrecoverable errors, intentional test failures, cannot proceed (terminal)

## Handover on Context Exhaustion

If you run out of context before completing:

1. Call `write_360_memory(entry_type="handover_closeout")` with progress summary:
   - summary: Brief overview of work completed so far
   - key_outcomes: What you accomplished before running out of context
   - decisions_made: Key decisions and rationale for successor
2. Notify orchestrator via `send_message()` about context exhaustion
3. Call `complete_job()` to mark yourself complete

Do NOT write 360 memory on normal completion - orchestrator handles that.

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
        websocket_manager: Optional[Any] = None,
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
        self._websocket_manager = websocket_manager or getattr(message_service, "_websocket_manager", None)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Handover 0406: Track todo_items warning timestamps (throttle 1 per 5 min per job)
        self._todo_warning_timestamps: dict[str, datetime] = {}

        # Handover 0450: Initialize orchestration components (from orchestrator.py)
        # Initialize lazily to avoid initialization errors in tests with mocked dependencies
        self._mission_planner = None
        self._agent_selector = None
        self._workflow_engine = None
        self._template_generator = None
        self.serena_optimizer = None  # Initialize lazily per tenant

    @property
    def mission_planner(self):
        """Lazy initialization of MissionPlanner."""
        if self._mission_planner is None:
            self._mission_planner = MissionPlanner(self.db_manager)
        return self._mission_planner

    @mission_planner.setter
    def mission_planner(self, value):
        """Allow setting mission_planner for tests."""
        self._mission_planner = value

    @property
    def agent_selector(self):
        """Lazy initialization of AgentSelector."""
        if self._agent_selector is None:
            self._agent_selector = AgentSelector(self.db_manager)
        return self._agent_selector

    @agent_selector.setter
    def agent_selector(self, value):
        """Allow setting agent_selector for tests."""
        self._agent_selector = value

    @property
    def workflow_engine(self):
        """Lazy initialization of WorkflowEngine."""
        if self._workflow_engine is None:
            self._workflow_engine = WorkflowEngine(self.db_manager)
        return self._workflow_engine

    @workflow_engine.setter
    def workflow_engine(self, value):
        """Allow setting workflow_engine for tests."""
        self._workflow_engine = value

    @property
    def template_generator(self):
        """Lazy initialization of MissionTemplateGeneratorV2."""
        if self._template_generator is None:
            self._template_generator = MissionTemplateGeneratorV2(self.db_manager)
        return self._template_generator

    @template_generator.setter
    def template_generator(self, value):
        """Allow setting template_generator for tests."""
        self._template_generator = value

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

    def _can_warn_missing_todos(self, job_id: str, cooldown_minutes: int = 5) -> bool:
        """
        Check if we can send a todo_items warning (throttle: 1 per N minutes per job).

        Args:
            job_id: Job UUID
            cooldown_minutes: Minimum minutes between warnings (default: 5)

        Returns:
            True if we can warn, False if throttled
        """
        last_warning = self._todo_warning_timestamps.get(job_id)
        if not last_warning:
            return True
        elapsed = (datetime.now(timezone.utc) - last_warning).total_seconds()
        return elapsed >= (cooldown_minutes * 60)

    def _record_todo_warning(self, job_id: str) -> None:
        """
        Record that a todo_items warning was sent for this job.

        Args:
            job_id: Job UUID
        """
        self._todo_warning_timestamps[job_id] = datetime.now(timezone.utc)

    # ============================================================================
    # Project Orchestration
    # ============================================================================
    # Note: orchestrate_project() method removed in favor of manual orchestration workflow

    async def get_workflow_status(self, project_id: str, tenant_key: str) -> dict[str, Any]:
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

        Raises:
            ResourceNotFoundError: Project not found
            DatabaseError: Database operation failed

        Example:
            >>> result = await service.get_workflow_status(
            ...     project_id="proj-123",
            ...     tenant_key="tenant-abc"
            ... )
            >>> print(f"Progress: {result['progress_percent']}%")
        """
        from src.giljo_mcp.exceptions import DatabaseError, ResourceNotFoundError

        try:
            async with self._get_session() as session:
                # Verify project exists
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise ResourceNotFoundError(
                        message=f"Project '{project_id}' not found",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

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

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self._logger.exception(f"Failed to get workflow status: {e}")
            raise DatabaseError(
                message=f"Failed to get workflow status: {e!s}",
                context={"project_id": project_id, "tenant_key": tenant_key},
            ) from e

    # ============================================================================
    # Agent Job Management
    # ============================================================================

    async def spawn_agent_job(
        self,
        agent_display_name: str,
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
            agent_display_name: Display name of agent (UI label - what humans see)
            agent_name: Agent name/identifier (template lookup key)
            mission: Agent mission description
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            parent_job_id: Optional parent agent_id for spawned agents (now refers to executor, not work order)
            context_chunks: Optional context chunks for the agent

        Returns:
            Dict with success status, job_id (work order), agent_id (executor), and agent_prompt

        Example:
            >>> result = await service.spawn_agent_job(
            ...     agent_display_name="Code Implementer",
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
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    from src.giljo_mcp.exceptions import ResourceNotFoundError

                    raise ResourceNotFoundError(
                        message="Project not found", context={"project_id": project_id, "tenant_key": tenant_key}
                    )

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

                # Handover 0408: Inject Serena instructions into agent mission if enabled
                include_serena = False
                try:
                    from pathlib import Path

                    import yaml

                    config_path = Path.cwd() / "config.yaml"
                    if config_path.exists():
                        with open(config_path, encoding="utf-8") as f:
                            config_data = yaml.safe_load(f) or {}
                        include_serena = (
                            config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
                        )
                except (OSError, yaml.YAMLError, KeyError, ValueError, TypeError) as e:
                    self._logger.warning(f"[SERENA] Failed to read config for agent spawn: {e}")

                if include_serena:
                    from src.giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions

                    serena_notice = generate_serena_instructions(enabled=True)
                    mission = serena_notice + "\n\n---\n\n" + mission
                    self._logger.info(
                        "[SERENA] Injected notice into agent mission",
                        extra={"agent_name": agent_name, "agent_display_name": agent_display_name},
                    )

                # Handover 0417: Template injection for multi-terminal mode
                if project.execution_mode == "multi_terminal":
                    # Look up template by agent_name
                    template_result = await session.execute(
                        select(AgentTemplate).where(
                            and_(
                                AgentTemplate.name == agent_name,
                                AgentTemplate.tenant_key == tenant_key,
                                AgentTemplate.is_active == True,
                            )
                        )
                    )
                    template = template_result.scalar_one_or_none()

                    if template:
                        # Get template content (Handover 0106: system_instructions + user_instructions)
                        template_expertise = ""
                        if template.system_instructions:
                            template_expertise = template.system_instructions
                            if template.user_instructions:
                                template_expertise += "\n\n" + template.user_instructions

                        if template_expertise:
                            # Inject template into mission with tidy framing (Handover 0417)
                            # Uses chapter-based visual pattern from _build_orchestrator_protocol
                            framed_mission = f"""╔═════════════════════════════════════════════════════════════════════════╗
║                     AGENT EXPERTISE & PROTOCOL                           ║
╚═════════════════════════════════════════════════════════════════════════╝

{template_expertise}

╔═════════════════════════════════════════════════════════════════════════╗
║                       YOUR ASSIGNED WORK                                 ║
╚═════════════════════════════════════════════════════════════════════════╝

{mission}"""
                            mission = framed_mission
                            self._logger.info(
                                "[TEMPLATE_INJECTION] Injected template into mission for multi-terminal mode",
                                extra={
                                    "agent_name": agent_name,
                                    "agent_display_name": agent_display_name,
                                    "template_id": template.id,
                                    "execution_mode": project.execution_mode,
                                },
                            )
                    else:
                        # Template not found - log warning but proceed
                        self._logger.warning(
                            f"[TEMPLATE_INJECTION] No template found for agent_name={agent_name} in multi-terminal mode. "
                            f"Proceeding with orchestrator's mission as-is.",
                            extra={
                                "agent_name": agent_name,
                                "agent_display_name": agent_display_name,
                                "execution_mode": project.execution_mode,
                                "tenant_key": tenant_key,
                            },
                        )
                # For claude_code_cli mode, no injection (Task tool handles template loading)

                # Create AgentJob (work order - WHAT)
                agent_job = AgentJob(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    project_id=project_id,
                    mission=mission,  # Mission stored ONCE in job, not execution
                    job_type=agent_display_name,
                    status="active",  # Job status: active, completed, cancelled
                    job_metadata=metadata_dict,
                )
                session.add(agent_job)

                # Create AgentExecution (executor instance - WHO)
                agent_execution = AgentExecution(
                    agent_id=agent_id,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    agent_display_name=agent_display_name,
                    agent_name=agent_name,
                    status="waiting",  # Execution status: waiting, working, blocked, complete, etc.
                    spawned_by=parent_job_id,  # Now points to parent's agent_id (executor)
                )

                # Set context tracking fields for orchestrators (Handover 0502)
                if agent_display_name == "orchestrator":
                    agent_execution.context_budget = 200000  # Sonnet 4.5 default
                    # Estimate initial context usage from mission
                    try:
                        encoder = tiktoken.get_encoding("cl100k_base")
                        agent_execution.context_used = len(encoder.encode(mission))
                    except Exception:  # noqa: BLE001 - tiktoken can raise various errors, use fallback estimation
                        # Fallback estimation
                        agent_execution.context_used = len(mission) // 4
                    # Update project staging_status when orchestrator is spawned
                    project.staging_status = "staged"
                    project.updated_at = datetime.now(timezone.utc)

                session.add(agent_execution)
                await session.commit()
                await session.refresh(agent_job)
                await session.refresh(agent_execution)

                # Generate THIN agent prompt (~10 lines)
                # Uses job_id for mission lookup (the work order persists)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_display_name}) for Project "{project.name}".

## MCP TOOL USAGE

MCP tools are **native tool calls** (like Read/Write/Bash/Glob).
- Use `mcp__giljo-mcp__*` tools directly (no HTTP, curl, or SDKs).

## STARTUP (MANDATORY)

1. Call `mcp__giljo-mcp__get_agent_mission` with:
   - job_id="{job_id}"
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
                self._logger.info(
                    f"[WEBSOCKET] Broadcasting agent:created for {agent_name} ({agent_display_name}) via direct WebSocket"
                )
                try:
                    if self._websocket_manager:
                        await self._websocket_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="agent:created",
                            data={
                                "project_id": project_id,
                                "execution_id": agent_execution.id,  # Handover 0457: Unique row ID for frontend Map key
                                "agent_id": agent_id,  # Executor UUID
                                "job_id": job_id,  # Work order UUID
                                "agent_display_name": agent_display_name,
                                "agent_name": agent_name,
                                "status": "waiting",
                                "thin_client": True,
                                "prompt_tokens": prompt_tokens,
                                "mission_tokens": mission_tokens,
                                "timestamp": created_at.isoformat(),
                                "mission": mission,  # Handover 0464: Include mission for UI display
                            },
                        )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                    self._logger.error(
                        f"[WEBSOCKET ERROR] Failed to broadcast agent:created: {ws_error}", exc_info=True
                    )

                return {
                    "success": True,
                    "job_id": job_id,  # Work order UUID (persists across succession)
                    "agent_id": agent_id,  # Executor UUID (changes on succession)
                    "execution_id": agent_execution.id,  # Handover 0457: Unique row ID for frontend Map key
                    "agent_prompt": thin_agent_prompt,  # ~10 lines
                    "prompt_tokens": prompt_tokens,  # ~50
                    "mission_stored": True,
                    "mission_tokens": mission_tokens,  # ~2000
                    "total_tokens": prompt_tokens + mission_tokens,
                    "thin_client": True,
                    "thin_client_note": [
                        "Mission stored server-side, keyed by job_id",
                        "Agent calls get_agent_mission(job_id, tenant_key) → returns mission + full_protocol",
                        "Enables: fresh sessions, postponed launches, orchestrator handover",
                    ],
                }

        except ResourceNotFoundError:
            raise
        except Exception as e:
            from src.giljo_mcp.exceptions import DatabaseError

            self._logger.error(f"[ERROR] Failed to spawn agent job: {e}", exc_info=True)
            raise DatabaseError(
                message=f"Failed to spawn agent: {e!s}",
                context={"project_id": project_id, "agent_display_name": agent_display_name},
            ) from e

    async def get_agent_mission(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Get agent-specific mission from database.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        Handover 0381: Renamed parameter from job_id to job_id (new contract).
        - job_id: Work order UUID (what work is assigned)
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
            job_id: Work order UUID (what work is assigned)
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
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key,
                        )
                    )
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    from src.giljo_mcp.exceptions import ResourceNotFoundError

                    raise ResourceNotFoundError(
                        message=f"Agent job {job_id} not found", context={"job_id": job_id, "tenant_key": tenant_key}
                    )

                # Get latest active execution for this job
                exec_result = await session.execute(
                    select(AgentExecution)
                    .where(
                        and_(
                            AgentExecution.job_id == job_id,
                            AgentExecution.tenant_key == tenant_key,
                            AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"]),
                        )
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                execution = exec_result.scalar_one_or_none()

                if not execution:
                    from src.giljo_mcp.exceptions import ResourceNotFoundError

                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "tenant_key": tenant_key},
                    )

                # Handover 0709: Implementation phase gate - check if user has clicked "Implement"
                if job.project_id:
                    from src.giljo_mcp.models.projects import Project

                    project = await session.get(Project, job.project_id)
                    if project and project.implementation_launched_at is None:
                        # BLOCKED: User must click "Implement" button first
                        return {
                            "blocked": True,
                            "mission": None,
                            "full_protocol": None,
                            "error": "BLOCKED: Implementation phase not started by user",
                            "user_instruction": (
                                "Your mission is blocked. The user must click the 'Implement' "
                                "button in the GiljoAI dashboard before you can receive your mission. "
                                "Please inform your user of this requirement and wait."
                            ),
                        }

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
                            "job_id": job_id,
                            "agent_id": execution.agent_id,
                            "agent_display_name": execution.agent_display_name,
                            "old_status": old_status,
                            "new_status": execution.status,
                        },
                    )

            # WebSocket emissions happen after the database transaction is complete
            if execution and first_acknowledgement:
                try:
                    if self._websocket_manager:
                        await self._websocket_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="job:mission_acknowledged",
                            data={
                                "job_id": job_id,
                                "agent_id": execution.agent_id,
                                "agent_display_name": execution.agent_display_name,
                                "agent_name": execution.agent_name,
                                "project_id": str(job.project_id),
                                "mission_acknowledged_at": execution.mission_acknowledged_at.isoformat(),
                            },
                        )

                        if status_changed and old_status is not None:
                            await self._websocket_manager.broadcast_to_tenant(
                                tenant_key=tenant_key,
                                event_type="agent:status_changed",
                                data={
                                    "job_id": job_id,
                                    "project_id": str(job.project_id) if job.project_id else None,
                                    "agent_id": execution.agent_id,
                                    "agent_display_name": execution.agent_display_name,
                                    "agent_name": execution.agent_name,
                                    "old_status": old_status,
                                    "status": "working",
                                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                                },
                            )

                    self._logger.info(
                        "[WEBSOCKET] Emitted mission acknowledgment/start events for get_agent_mission",
                        extra={"job_id": job_id, "agent_id": execution.agent_id},
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                    # Do not fail mission fetch on WebSocket bridge issues
                    self._logger.warning(f"[WEBSOCKET] Failed to emit mission acknowledgment/status events: {ws_error}")

            if not execution or not job:
                # Safety guard – should be unreachable due to earlier NOT_FOUND raise
                from src.giljo_mcp.exceptions import ResourceNotFoundError

                raise ResourceNotFoundError(
                    message=f"Agent job {job_id} not found", context={"job_id": job_id, "tenant_key": tenant_key}
                )

            # Handover 0353: Generate team-aware mission with context header
            team_context_header = _generate_team_context_header(
                execution, all_project_executions, mission_lookup=mission_lookup
            )
            raw_mission = job.mission or ""
            full_mission = team_context_header + raw_mission

            # Inject Serena MCP notice if enabled (User Settings -> Integrations)
            try:
                from pathlib import Path

                import yaml

                config_path = Path.cwd() / "config.yaml"
                if config_path.exists():
                    with open(config_path, encoding="utf-8") as f:
                        config_data = yaml.safe_load(f) or {}
                    include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

                    if include_serena:
                        from src.giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions

                        serena_instructions = generate_serena_instructions(enabled=True)
                        full_mission = serena_instructions + "\n\n---\n\n" + full_mission
                        self._logger.info(
                            "[SERENA] Injected Serena notice into agent mission",
                            extra={"job_id": job_id, "agent_id": execution.agent_id},
                        )
            except (ImportError, AttributeError, OSError) as e:
                self._logger.warning(f"[SERENA] Failed to inject Serena notice into agent mission: {e}")

            estimated_tokens = len(full_mission) // 4

            # Generate 5-phase lifecycle protocol (Handover 0334, 0359, 0378 Bug 2)
            full_protocol = _generate_agent_protocol(
                job_id=job_id,
                tenant_key=tenant_key,
                agent_name=execution.agent_display_name,
                agent_id=str(execution.agent_id),
            )

            return {
                "success": True,
                "job_id": job.job_id,  # Work order UUID
                "agent_id": execution.agent_id,  # Executor UUID
                "agent_name": execution.agent_display_name,
                "agent_display_name": execution.agent_display_name,
                "mission": full_mission,  # Handover 0353: Team-aware mission with context header
                "project_id": str(job.project_id),
                "parent_job_id": str(execution.spawned_by) if execution.spawned_by else None,
                "estimated_tokens": estimated_tokens,
                "status": execution.status,  # Execution status
                "created_at": job.created_at.isoformat() if job.created_at else None,  # Job creation time
                "started_at": execution.started_at.isoformat()
                if execution.started_at
                else None,  # Execution start time
                "thin_client": True,
                "full_protocol": full_protocol,  # Handover 0334: 6-phase agent lifecycle
            }

        except ResourceNotFoundError:
            raise
        except Exception as e:
            from src.giljo_mcp.exceptions import DatabaseError

            self._logger.exception(f"Failed to get agent mission: {e}")
            raise DatabaseError(
                message=f"Unexpected error: {e!s}", context={"job_id": job_id, "tenant_key": tenant_key}
            ) from e

    async def get_pending_jobs(self, tenant_key: str, agent_display_name: Optional[str] = None) -> dict[str, Any]:
        """
        Get pending jobs, optionally filtered by agent display name.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Queries AgentExecution.status for execution state (waiting, working, etc.)
        - Mission comes from AgentJob via join
        - Returns both job_id (work order) and agent_id (executor)

        Args:
            tenant_key: Tenant key for isolation
            agent_display_name: Optional display name of agent to filter by

        Returns:
            Dict with list of pending jobs

        Example:
            >>> result = await service.get_pending_jobs(
            ...     tenant_key="tenant-abc",
            ...     agent_display_name="Code Implementer"  # Optional filter
            ... )
        """
        from src.giljo_mcp.exceptions import DatabaseError, ValidationError

        try:
            # Validate inputs

            if not tenant_key or not tenant_key.strip():
                raise ValidationError(
                    message="tenant_key cannot be empty",
                    context={"agent_display_name": agent_display_name, "tenant_key": tenant_key},
                )

            # Get pending executions with their jobs (dual-model)
            async with self._get_session() as session:
                # Build query with optional agent_display_name filter
                stmt = (
                    select(AgentExecution, AgentJob)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status == "waiting",  # Execution status, not job status
                    )
                )
                # Add optional filter by agent_display_name
                if agent_display_name and agent_display_name.strip():
                    stmt = stmt.where(AgentExecution.agent_display_name == agent_display_name)
                stmt = stmt.limit(10)
                result = await session.execute(stmt)
                rows = result.all()

                # Format jobs for response
                formatted_jobs = []
                for execution, job in rows:
                    formatted_jobs.append(
                        {
                            "job_id": job.job_id,  # Work order ID
                            "agent_id": execution.agent_id,  # Executor ID
                            "execution_id": str(execution.id) if hasattr(execution, "id") else None,  # Unique row ID
                            "tenant_key": execution.tenant_key,  # For job_to_response
                            "project_id": job.project_id,  # From AgentJob
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "mission": job.mission,  # Mission from AgentJob
                            "status": execution.status,  # Execution status
                            "progress": execution.progress if hasattr(execution, "progress") else 0,
                            "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "priority": "normal",
                        }
                    )

                return {"jobs": formatted_jobs, "count": len(formatted_jobs)}

        except ValidationError:
            raise
        except Exception as e:
            self._logger.exception(f"Failed to get pending jobs: {e}")
            raise DatabaseError(
                message=f"Failed to get pending jobs: {e!s}",
                context={"agent_display_name": agent_display_name, "tenant_key": tenant_key},
            ) from e

    async def acknowledge_job(
        self, job_id: str, agent_id: Optional[str] = None, tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Acknowledge job assignment (AgentExecution, async safe).

        Args:
            job_id: Job UUID (looks up latest active execution)
            agent_id: Agent identifier (not used in query, kept for API compatibility)
            tenant_key: Optional tenant key (uses current if not provided)

        Returns:
            Dict with success status and job details

        Example:
            >>> result = await service.acknowledge_job(
            ...     job_id="job-123",
            ...     tenant_key="tenant_key"
            ... )
        """
        from src.giljo_mcp.exceptions import DatabaseError, ResourceNotFoundError, ValidationError

        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(
                    message="No tenant context available", context={"job_id": job_id, "agent_id": agent_id}
                )

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"tenant_key": tenant_key})
            # Note: agent_id not used in query - parameter kept for API compatibility

            async with self._get_session() as session:
                # Get latest active execution for this job
                stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "tenant_key": tenant_key},
                    )

                # Get job for mission details
                job_result = await session.execute(select(AgentJob).where(AgentJob.job_id == job_id))
                job = job_result.scalar_one_or_none()
                if not job:
                    raise ResourceNotFoundError(
                        message=f"Job {job_id} not found", context={"job_id": job_id, "tenant_key": tenant_key}
                    )

                # Handover 0709: Implementation phase gate - check if user has clicked "Implement"
                if job.project_id:
                    from src.giljo_mcp.models.projects import Project

                    project = await session.get(Project, job.project_id)
                    if project and project.implementation_launched_at is None:
                        # BLOCKED: User must click "Implement" button first
                        return {
                            "success": False,
                            "error": "BLOCKED: Implementation not launched by user",
                            "action_required": "User must click 'Implement' button in dashboard",
                        }

                # Idempotent - if already in working status, return current state
                if execution.status in {"working"}:
                    return {
                        "job": {
                            "job_id": job.job_id,
                            "agent_display_name": execution.agent_display_name,
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

                # Capture all values before session closes (to avoid detached instance issues)
                response_data = {
                    "job": {
                        "job_id": job.job_id,
                        "agent_display_name": execution.agent_display_name,
                        "mission": job.mission,
                        "status": execution.status,
                        "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    },
                    "next_instructions": "Begin executing your mission",
                }
                ws_data = {
                    "job_id": job_id,
                    "project_id": str(job.project_id) if job.project_id else None,
                    "agent_display_name": execution.agent_display_name,
                    "agent_name": execution.agent_name,
                    "old_status": old_status,
                    "status": "working",
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                }

            # WebSocket emission for real-time UI updates (after session closed)
            try:
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data=ws_data,
                    )
                    self._logger.info(f"[WEBSOCKET] Broadcasted acknowledge_job status change for {job_id}")
            except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                self._logger.warning(f"[WEBSOCKET] Failed to broadcast acknowledge_job: {ws_error}")
                # Don't fail the operation if WebSocket broadcast fails

            return response_data
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            self._logger.exception(f"Failed to acknowledge job: {e}")
            raise DatabaseError(
                message=f"Failed to acknowledge job: {e!s}", context={"job_id": job_id, "tenant_key": tenant_key}
            ) from e

    async def report_progress(
        self,
        job_id: str,
        progress: dict[str, Any] | None = None,
        tenant_key: Optional[str] = None,
        todo_items: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Report job progress (store message in message queue).

        Args:
            job_id: Job UUID
            progress: Progress data dict (legacy format, optional)
            tenant_key: Optional tenant key (uses current if not provided)
            todo_items: Simplified TODO items array (Handover 0392)
                        [{"content": "Task A", "status": "completed"}, ...]

        Returns:
            Dict with success status

        Example (new simplified format):
            >>> result = await service.report_progress(
            ...     job_id="job-123",
            ...     todo_items=[
            ...         {"content": "Task A", "status": "completed"},
            ...         {"content": "Task B", "status": "in_progress"},
            ...         {"content": "Task C", "status": "pending"}
            ...     ]
            ... )

        Example (legacy format, still supported):
            >>> result = await service.report_progress(
            ...     job_id="job-123",
            ...     progress={"percent": 50, "message": "Half done"}
            ... )
        """

        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"method": "report_progress"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "report_progress"})

            # Handover 0392: Support top-level todo_items parameter (simplified format)
            # If todo_items provided at top level, derive progress metrics from it
            if todo_items is not None:
                if not isinstance(todo_items, list):
                    raise ValidationError(
                        message="todo_items must be a list",
                        context={"method": "report_progress", "todo_items_type": type(todo_items).__name__},
                    )

                # Calculate progress metrics from todo_items
                completed_steps = len([t for t in todo_items if t.get("status") == "completed"])
                total_steps = len(todo_items)
                in_progress_items = [t for t in todo_items if t.get("status") == "in_progress"]
                current_step = in_progress_items[0].get("content") if in_progress_items else None
                percent = (completed_steps / total_steps * 100) if total_steps > 0 else 0

                # Build progress dict for backwards compatibility with existing code
                progress = {
                    "mode": "todo",
                    "percent": percent,
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "current_step": current_step,
                    "todo_items": todo_items,
                }
            elif progress is None:
                raise ValidationError(
                    message="Either progress or todo_items must be provided", context={"method": "report_progress"}
                )
            elif not isinstance(progress, dict):
                raise ValidationError(
                    message="progress must be a dict",
                    context={"method": "report_progress", "progress_type": type(progress).__name__},
                )

            # Extract todo_items from progress dict if not already set (backwards compatibility)
            if todo_items is None and "todo_items" in progress:
                todo_items = progress.get("todo_items")

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
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "report_progress"},
                    )

                # Get job for metadata and project_id
                job_res = await session.execute(select(AgentJob).where(AgentJob.job_id == job_id))
                job = job_res.scalar_one_or_none()

                if not job:
                    raise ResourceNotFoundError(
                        message=f"Job {job_id} not found", context={"job_id": job_id, "method": "report_progress"}
                    )

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

                # Handover 0402: Store todo_items in dedicated table for Plan/TODOs tab display
                # Process todo_items array: [{ content: "...", status: "pending|in_progress|completed" }, ...]
                todo_items = progress.get("todo_items")
                if isinstance(todo_items, list) and len(todo_items) > 0:
                    from sqlalchemy import delete as sql_delete

                    # Delete existing items for this job (replace strategy)
                    await session.execute(sql_delete(AgentTodoItem).where(AgentTodoItem.job_id == job_id))

                    # Insert new items with sequence
                    for seq, item in enumerate(todo_items):
                        if isinstance(item, dict) and item.get("content"):
                            status = item.get("status", "pending")
                            # Validate status
                            if status not in ("pending", "in_progress", "completed"):
                                status = "pending"

                            todo_item = AgentTodoItem(
                                job_id=job_id,
                                tenant_key=tenant_key,
                                content=str(item["content"])[:255],  # Truncate to column limit
                                status=status,
                                sequence=seq,
                            )
                            session.add(todo_item)

                await session.commit()
                await session.refresh(execution)
                await session.refresh(job)

            if not job:
                raise ResourceNotFoundError(
                    message=f"Job {job_id} not found after commit",
                    context={"job_id": job_id, "method": "report_progress"},
                )

            # Handover 0402: Query todo_items for WebSocket payload
            todo_items_payload = None
            async with self._get_session() as session:
                result = await session.execute(
                    select(AgentTodoItem).where(AgentTodoItem.job_id == job_id).order_by(AgentTodoItem.sequence)
                )
                items = result.scalars().all()
                if items:
                    todo_items_payload = [{"content": item.content, "status": item.status} for item in items]

            # Handover 0386: Direct WebSocket emission for progress updates
            # DO NOT use MessageService.send_message() - that creates erroneous message records
            # Progress is already persisted in execution.progress and job.job_metadata["todo_steps"]
            # We only need to emit a WebSocket event for real-time UI updates
            try:
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="job:progress_update",
                        data={
                            "job_id": job_id,
                            "project_id": str(job.project_id) if job.project_id else None,
                            "agent_id": execution.agent_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "progress": progress,
                            "progress_percent": execution.progress,
                            "current_task": execution.current_task,
                            "todo_steps": job.job_metadata.get("todo_steps") if job.job_metadata else None,
                            "todo_items": todo_items_payload,  # Handover 0402: Include for Plan/TODOs tab
                            "last_progress_at": execution.last_progress_at.isoformat()
                            if execution.last_progress_at
                            else None,
                        },
                    )
                    self._logger.info(f"[WEBSOCKET] Broadcasted job:progress_update for {job_id}")
            except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                self._logger.warning(f"[WEBSOCKET] Failed to broadcast progress: {ws_error}")

            # Handover 0406: Reactive warning for missing todo_items
            warnings = []
            todo_items = progress.get("todo_items")
            if not isinstance(todo_items, list) or len(todo_items) == 0:
                # Check throttle - only warn once per 5 minutes per job
                if self._can_warn_missing_todos(job_id):
                    warnings.append(
                        "WARNING: todo_items missing! Dashboard Steps shows '--'. "
                        "Include todo_items=[{content, status}] in every report_progress() call."
                    )
                    self._record_todo_warning(job_id)

            return {
                "status": "success",
                "message": "Progress reported successfully",
                "warnings": warnings,
            }
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            self._logger.exception(f"Failed to report progress: {e}")
            raise OrchestrationError(
                message="Failed to report progress", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def complete_job(
        self, job_id: str, result: dict[str, Any], tenant_key: Optional[str] = None
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
                raise ValidationError(message="No tenant context available", context={"method": "complete_job"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "complete_job"})
            if not result or not isinstance(result, dict):
                raise ValidationError(
                    message="result must be a non-empty dict",
                    context={"method": "complete_job", "result_type": type(result).__name__},
                )

            completion_attempt_time = datetime.now(timezone.utc)

            # Database update
            job = None
            execution = None
            old_status = None
            duration_seconds = None
            warnings = []  # Handover 0710: Soft warnings for orchestrator completion
            async with self._get_session() as session:
                # Try new dual-model path first
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if execution:
                    # NEW PATH: Dual-model (AgentExecution)
                    # Get job
                    job_res = await session.execute(
                        select(AgentJob).where(
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key,
                        )
                    )
                    job = job_res.scalar_one_or_none()
                    if not job:
                        raise ResourceNotFoundError(
                            message=f"Job {job_id} not found", context={"job_id": job_id, "method": "complete_job"}
                        )

                    # Validate completion requirements (unread messages and incomplete TODOs)
                    unread_query = select(Message).where(
                        and_(
                            Message.tenant_key == tenant_key,
                            Message.project_id == job.project_id,
                            Message.status == "pending",
                            Message.to_agents.contains([execution.agent_id]),
                        )
                    )
                    unread_res = await session.execute(unread_query)
                    unread_messages = unread_res.scalars().all()

                    def _is_before_attempt(message: Message) -> bool:
                        if not message.created_at:
                            return True
                        created_at = message.created_at
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=timezone.utc)
                        return created_at <= completion_attempt_time

                    unread_messages = [message for message in unread_messages if _is_before_attempt(message)]

                    todo_query = select(AgentTodoItem).where(
                        and_(
                            AgentTodoItem.job_id == job_id,
                            AgentTodoItem.tenant_key == tenant_key,
                            AgentTodoItem.status != "completed",
                        )
                    )
                    todo_res = await session.execute(todo_query)
                    incomplete_todos = todo_res.scalars().all()

                    if unread_messages or incomplete_todos:
                        reasons = []
                        if unread_messages:
                            unread_ids = [str(msg.id) for msg in unread_messages[:5]]
                            reasons.append(f"{len(unread_messages)} unread messages waiting: {unread_ids}")
                        if incomplete_todos:
                            todo_names = [todo.content for todo in incomplete_todos[:5]]
                            reasons.append(f"{len(incomplete_todos)} TODO items not completed: {todo_names}")

                        self._logger.info(
                            "Completion blocked by protocol validation",
                            extra={
                                "job_id": job_id,
                                "tenant_key": tenant_key,
                                "unread_messages": len(unread_messages),
                                "incomplete_todos": len(incomplete_todos),
                            },
                        )

                        raise ValidationError(
                            message="COMPLETION_BLOCKED: Complete all TODO items and read all messages before calling complete_job()",
                            error_code="COMPLETION_BLOCKED",
                            context={
                                "job_id": job_id,
                                "reasons": reasons,
                                "unread_messages": len(unread_messages),
                                "incomplete_todos": len(incomplete_todos),
                            },
                        )

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
                    other_active_stmt = select(AgentExecution).where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.agent_id != execution.agent_id,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"]),
                    )
                    other_active_res = await session.execute(other_active_stmt)
                    other_active = other_active_res.scalar_one_or_none()

                    if not other_active:
                        # No other active executions, mark job as completed
                        job.status = "completed"
                        job.completed_at = execution.completed_at

                    # Handover 0710: Check if orchestrator needs 360 memory reminder
                    if execution.agent_display_name == "orchestrator":
                        # Get project to check staging status
                        project_stmt = select(Project).where(
                            Project.id == job.project_id,
                            Project.tenant_key == tenant_key,
                        )
                        project_res = await session.execute(project_stmt)
                        project = project_res.scalar_one_or_none()

                        # Only warn for non-staging orchestrators with a product
                        skip_staging = project and project.staging_status in ("staging", "staged", "launching")
                        has_product = project and project.product_id

                        if not skip_staging and has_product:
                            # Check if any 360 memory entry exists for this project
                            memory_stmt = (
                                select(ProductMemoryEntry)
                                .where(
                                    ProductMemoryEntry.project_id == str(job.project_id),
                                    ProductMemoryEntry.tenant_key == tenant_key,
                                )
                                .limit(1)
                            )
                            memory_res = await session.execute(memory_stmt)
                            has_memory = memory_res.scalar_one_or_none() is not None

                            if not has_memory:
                                warnings.append(
                                    "REMINDER: No 360 Memory entry found for this project. "
                                    "Consider calling write_360_memory() to preserve project "
                                    "knowledge for future orchestrators."
                                )

                    await session.commit()
                else:
                    # No active execution found
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "complete_job"},
                    )

            # WebSocket emission for real-time UI updates (after session closed)
            if execution:
                try:
                    if self._websocket_manager:
                        await self._websocket_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="agent:status_changed",
                            data={
                                "job_id": job_id,
                                "project_id": str(job.project_id) if job.project_id else None,
                                "agent_display_name": execution.agent_display_name,
                                "agent_name": execution.agent_name,
                                "old_status": old_status,
                                "status": "complete",
                                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                                "duration_seconds": duration_seconds,
                            },
                        )
                        self._logger.info(f"[WEBSOCKET] Broadcasted complete_job status change for {job_id}")
                except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                    self._logger.warning(f"[WEBSOCKET] Failed to broadcast complete_job: {ws_error}")

            # Handover 0710: Include warnings in response (follows report_progress pattern)
            response = {
                "status": "success",
                "job_id": job_id,
                "message": "Job completed successfully",
                "warnings": warnings,
            }
            return response
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            self._logger.exception(f"Failed to complete job: {e}")
            raise OrchestrationError(
                message="Failed to complete job", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def report_error(self, job_id: str, error: str, tenant_key: Optional[str] = None) -> dict[str, Any]:
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
                raise ValidationError(message="No tenant context available", context={"method": "report_error"})

            if not job_id or not job_id.strip():
                raise ValidationError(message="job_id cannot be empty", context={"method": "report_error"})
            if not error or not error.strip():
                raise ValidationError(
                    message="error message cannot be empty", context={"method": "report_error", "job_id": job_id}
                )

            job = None
            async with self._get_session() as session:
                # Get latest active execution
                exec_stmt = (
                    select(AgentExecution)
                    .where(
                        AgentExecution.job_id == job_id,
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status.not_in(["complete", "failed", "cancelled", "decommissioned"]),
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                exec_res = await session.execute(exec_stmt)
                execution = exec_res.scalar_one_or_none()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"No active execution found for job {job_id}",
                        context={"job_id": job_id, "method": "report_error"},
                    )

                # Get job for project_id (needed for WebSocket event filtering)
                job_res = await session.execute(select(AgentJob).where(AgentJob.job_id == job_id))
                job = job_res.scalar_one_or_none()

                # Capture old status before updating
                old_status = execution.status

                # Update execution status to blocked (failed is system-enforced)
                execution.status = "blocked"
                execution.failure_reason = None
                execution.block_reason = error

                await session.commit()

            # WebSocket emission for real-time UI updates (after session closed)
            try:
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_to_tenant(
                        tenant_key=tenant_key,
                        event_type="agent:status_changed",
                        data={
                            "job_id": job_id,
                            "project_id": str(job.project_id) if job and job.project_id else None,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "old_status": old_status,
                            "status": "blocked",
                            "block_reason": error,
                        },
                    )
                    self._logger.info(f"[WEBSOCKET] Broadcasted report_error status change for {job_id}")
            except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                self._logger.warning(f"[WEBSOCKET] Failed to broadcast report_error: {ws_error}")

            return {"status": "success", "job_id": job_id, "message": "Error reported"}
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            self._logger.exception(f"Failed to report error: {e}")
            raise OrchestrationError(
                message="Failed to report error", context={"job_id": job_id, "error": str(e)}
            ) from e

    async def list_jobs(
        self,
        tenant_key: str,
        project_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        agent_display_name: Optional[str] = None,
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

        Supports filtering by project, status, and agent display name with pagination.
        All jobs are filtered by tenant_key for multi-tenant isolation.

        Args:
            tenant_key: Tenant key for isolation (required)
            project_id: Filter by project UUID (optional)
            status_filter: Filter by status (waiting, active, completed, failed) (optional)
            agent_display_name: Filter by agent display name (Orchestrator, Implementer, etc.) (optional)
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
            from sqlalchemy.orm import selectinload

            async with self._get_session() as session:
                # Build query with filters (join AgentExecution with AgentJob)
                # Handover 0423: Load todo_items relationship for Plan tab display
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
                    # DIAGNOSTIC: Log message counters for debugging persistence
                    self._logger.debug(
                        f"[LIST_JOBS DEBUG] Agent {execution.agent_display_name} (job={job.job_id}, agent={execution.agent_id}): "
                        f"{execution.messages_sent_count} sent, {execution.messages_waiting_count} waiting, {execution.messages_read_count} read"
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
                        # Fallback: derive steps from todo_items if metadata doesn't have it
                        if not steps_summary and job.todo_items:
                            total = len(job.todo_items)
                            completed = sum(1 for item in job.todo_items if item.status == "completed")
                            if total > 0:
                                steps_summary = {"total": total, "completed": completed}
                    except (KeyError, ValueError, TypeError, AttributeError):
                        # Do not break listing if metadata has unexpected shape
                        self._logger.warning(
                            "[LIST_JOBS] Failed to derive steps summary from job_metadata",
                            exc_info=True,
                        )

                    job_dicts.append(
                        {
                            "job_id": job.job_id,  # Work order ID
                            "agent_id": execution.agent_id,  # Executor ID (same across succession)
                            "execution_id": execution.id,  # UNIQUE per row - use as Map key
                            "tenant_key": execution.tenant_key,
                            "project_id": job.project_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "mission": job.mission,  # Mission from AgentJob
                            "status": execution.status,  # Execution status
                            "progress": execution.progress,  # Execution progress
                            "spawned_by": execution.spawned_by,  # Parent agent_id
                            "tool_type": execution.tool_type,
                            "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
                            # Counter fields replace JSONB messages array (Handover 0387)
                            "messages_sent_count": execution.messages_sent_count,
                            "messages_waiting_count": execution.messages_waiting_count,
                            "messages_read_count": execution.messages_read_count,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "mission_acknowledged_at": execution.mission_acknowledged_at.isoformat()
                            if execution.mission_acknowledged_at
                            else None,
                            "steps": steps_summary,
                            # Handover 0423: Include todo_items for Plan tab display
                            "todo_items": [
                                {"content": item.content, "status": item.status}
                                for item in sorted(job.todo_items or [], key=lambda x: x.sequence)
                            ],
                            # Note: updated_at field removed - not present in models
                        }
                    )

                self._logger.info(
                    f"Listed {len(job_dicts)} jobs (total={total}, project={project_id}, status={status_filter})"
                )

                return {
                    "jobs": job_dicts,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }

        except Exception as e:
            self._logger.exception(f"Failed to list jobs: {e}")
            raise OrchestrationError(
                message="Failed to list jobs", context={"tenant_key": tenant_key, "error": str(e)}
            ) from e

    # NOTE: update_context_usage(), estimate_message_tokens(), and _trigger_auto_succession()
    # were removed in Handover 0422 - the MCP server is passive and cannot track
    # external CLI tool context usage. Manual succession via /gil_handover remains available.

    async def trigger_succession(
        self, job_id: str, reason: str = "manual", tenant_key: Optional[str] = None, agent_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        REMOVED (Handover 0700d): Legacy Agent ID Swap succession removed.
        Use simple_handover.py endpoint instead for 360 Memory-based session continuity.

        This method stub remains for backward compatibility.
        """
        raise NotImplementedError(
            "trigger_succession() removed in Handover 0700d. Use POST /api/agent-jobs/{job_id}/simple-handover instead."
        )

    # ========================================================================
    # Handover 0450: Orchestrator Logic Consolidation
    # Methods moved from orchestrator.py to OrchestrationService
    # ========================================================================

    async def _get_agent_template_internal(
        self, role: str, tenant_key: str, product_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Optional[AgentTemplate]:
        """
        Get agent template for role with cascade resolution.

        Resolution order (highest to lowest priority):
        1. Product-specific template (if product_id provided)
        2. Tenant-specific template (user customizations)
        3. System default template (is_default=True)

        Args:
            role: Agent role name (e.g., "implementer", "tester")
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Optional product ID for product-specific templates
            session: Optional AsyncSession (if not provided, creates new session)

        Returns:
            AgentTemplate instance or None if no template found

        Multi-tenant isolation:
            - Only returns templates owned by tenant
            - No cross-tenant leakage possible
        """
        # Use provided session or create new one
        if session:
            # Use provided session (no context manager, caller manages session)
            # Try product-specific template first (if product_id provided)
            if product_id:
                stmt = select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.role == role,
                    AgentTemplate.product_id == product_id,
                    AgentTemplate.is_active == True,
                )
                result = await session.execute(stmt)
                template = result.scalar_one_or_none()
                if template:
                    self._logger.info(
                        f"[_get_agent_template_internal] Found product-specific template for "
                        f"role={role}, product={product_id}, tenant={tenant_key}"
                    )
                    return template

            # Try tenant-specific template (no product_id constraint)
            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role == role,
                AgentTemplate.product_id == None,
                AgentTemplate.is_active == True,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                self._logger.info(
                    f"[_get_agent_template_internal] Found tenant-specific template for role={role}, tenant={tenant_key}"
                )
                return template

            # Try system default template (is_default=True, any tenant)
            stmt = select(AgentTemplate).where(
                AgentTemplate.role == role,
                AgentTemplate.is_default == True,
                AgentTemplate.is_active == True,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                self._logger.info(f"[_get_agent_template_internal] Found system default template for role={role}")
                return template

            self._logger.warning(
                f"[_get_agent_template_internal] No template found for role={role}, tenant={tenant_key}, product={product_id}"
            )
            return None
        # Create new session
        async with self._get_session() as session:
            return await self._get_agent_template_internal(role, tenant_key, product_id, session)

    async def _spawn_claude_code_agent_internal(
        self,
        session: AsyncSession,
        project: Project,
        role: AgentRole,
        template: AgentTemplate,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
    ) -> AgentExecution:
        """
        Spawn Claude Code agent for project execution.

        Process:
        1. Generate mission with MCP coordination instructions
        2. Apply Serena optimization for context prioritization
        3. Create Agent record with mode='claude'

        Args:
            session: Active AsyncSession
            project: Project instance
            role: Agent role enum
            template: AgentTemplate instance
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions
            parent_agent_id: Optional parent agent ID

        Returns:
            Created AgentExecution instance with tool_type='claude'
        """
        # 1. Generate mission
        if custom_mission:
            mission = custom_mission
        else:
            # Generate mission using template generator
            mission = await self.template_generator.generate_agent_mission(
                role=role.value,
                project_name=project.name,
                custom_mission=None,
                additional_instructions=additional_instructions,
            )

        # Add MCP coordination protocol to mission
        mcp_instructions = self._generate_mcp_instructions_internal(project.tenant_key, role.value, mission)
        mission = f"{mission}\n\n{mcp_instructions}"

        # 2. Apply Serena optimization
        optimizer = self._get_serena_optimizer_internal(project.tenant_key)
        if optimizer:
            try:
                injector = MissionOptimizationInjector(optimizer)

                context_data = {
                    "project_id": project.id,
                    "project_type": "general",
                    "codebase_size": "medium",
                    "primary_language": "python",
                }

                optimized_mission = await injector.inject_optimization_rules(
                    agent_role=role.value, mission=mission, context_data=context_data
                )

                self._logger.info(
                    f"[_spawn_claude_code_agent_internal] Enhanced {role.value} agent mission with Serena optimization"
                )
                mission = optimized_mission

            except (ImportError, AttributeError, OSError, ValueError) as e:
                self._logger.warning(f"[_spawn_claude_code_agent_internal] Failed to inject Serena optimization: {e}")
                # Continue with original mission

        # 3. Create AgentJob (work order) and AgentExecution (executor instance)
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=project.tenant_key,
            project_id=project.id,
            mission=mission,
            job_type=role.value,
            status="active",
        )
        session.add(agent_job)

        # Create AgentExecution (executor instance)
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=project.tenant_key,
            agent_display_name=role.value,
            agent_name=role.value,
            status="waiting",
            progress=0,
            tool_type="claude",
            messages=[],
            spawned_by=parent_agent_id,
            meta_data={
                "template_id": template.id,
                "template_name": template.name,
                "tool": template.tool,
            },
        )
        session.add(agent_execution)
        await session.commit()
        await session.refresh(agent_execution)

        self._logger.info(
            f"[_spawn_claude_code_agent_internal] Created Claude Code agent: role={role.value}, "
            f"template={template.name}, project={project.id}, job_id={job_id}, agent_id={agent_id}"
        )

        return agent_execution

    async def _spawn_generic_agent_internal(
        self,
        session: AsyncSession,
        project: Project,
        role: AgentRole,
        template: AgentTemplate,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
    ) -> AgentExecution:
        """
        Spawn generic agent (Codex/Gemini with job queue).

        Process:
        1. Create MCP job via AgentJobManager
        2. Generate CLI prompt with MCP tool examples
        3. Create Agent record with mode='codex'/'gemini', job_id, status='waiting_acknowledgment'
        4. Store CLI prompt in Agent metadata

        Args:
            session: Active AsyncSession
            project: Project instance
            role: Agent role enum
            template: AgentTemplate instance
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions
            parent_agent_id: Optional parent agent ID

        Returns:
            Created AgentExecution instance with tool_type='codex' or 'gemini'
        """
        # 1. Generate mission
        if custom_mission:
            mission = custom_mission
        else:
            mission = await self.template_generator.generate_agent_mission(
                role=role.value,
                project_name=project.name,
                custom_mission=None,
                additional_instructions=additional_instructions,
            )

        # Add MCP coordination protocol
        mcp_instructions = self._generate_mcp_instructions_internal(project.tenant_key, role.value, mission)
        full_mission = f"{mission}\n\n{mcp_instructions}"

        # 2. Create AgentJob (work order) and AgentExecution (executor instance)
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=project.tenant_key,
            project_id=project.id,
            mission=full_mission,
            job_type=role.value,
            status="active",
        )
        session.add(agent_job)

        # Create AgentExecution (executor instance)
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=project.tenant_key,
            agent_display_name=role.value,
            agent_name=role.value,
            status="waiting_acknowledgment",
            progress=0,
            tool_type=template.tool,  # 'codex' or 'gemini'
            messages=[],
            spawned_by=parent_agent_id,
            meta_data={
                "template_id": template.id,
                "template_name": template.name,
                "tool": template.tool,
            },
        )
        session.add(agent_execution)
        await session.commit()
        await session.refresh(agent_execution)

        self._logger.info(
            f"[_spawn_generic_agent_internal] Created {template.tool} agent: role={role.value}, "
            f"job_id={job_id}, agent_id={agent_id}, project={project.id}"
        )

        # 3. Generate CLI prompt (simplified - no _generate_cli_prompt method in service yet)
        cli_prompt = f"# Agent Mission\n\nJob ID: {job_id}\nAgent: {role.value}\n\n{full_mission}"

        # Update agent_execution with CLI prompt
        if not agent_execution.meta_data:
            agent_execution.meta_data = {}
        agent_execution.meta_data["cli_prompt"] = cli_prompt
        await session.commit()

        return agent_execution

    def _generate_mcp_instructions_internal(
        self, tenant_key: str, agent_role: str, mission_text: Optional[str] = None
    ) -> str:
        """
        Generate MCP coordination protocol instructions.

        Includes:
        - Checkpoint recommendations (every 2-3 tasks)
        - MCP tool call examples (acknowledge_job, report_progress, complete_job, report_error)
        - Tenant-specific examples (include tenant_key)

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            agent_role: Agent role for contextualized examples
            mission_text: Optional mission text (unused, for compatibility)

        Returns:
            Formatted MCP instructions text
        """
        return f"""
## MCP Coordination Protocol

**IMPORTANT**: Use MCP tools for coordination and progress tracking.

### Checkpointing Guidelines
- Report progress every 2-3 completed tasks
- Use `report_progress` tool to save state
- Include files modified and context used
- Request handoff if context usage exceeds 25K tokens

### MCP Tool Examples

1. **Acknowledge Job** (First step after assignment):
```
acknowledge_job(
    job_id="<your-job-id>",
    agent_id="{agent_role}",
    tenant_key="{tenant_key}"
)
```

2. **Report Progress** (After completing tasks):
```
report_progress(
    job_id="<your-job-id>",
    completed_todo="Implemented user authentication module",
    files_modified=["src/auth.py", "tests/test_auth.py"],
    context_used=15000,
    tenant_key="{tenant_key}"
)
```

3. **Complete Job** (When mission accomplished):
```
complete_job(
    job_id="<your-job-id>",
    result={{
        "summary": "Successfully implemented feature X",
        "files_created": ["src/new_module.py"],
        "files_modified": ["src/main.py"],
        "tests_written": ["tests/test_new_module.py"],
        "coverage": "95%",
        "notes": "All tests passing"
    }},
    tenant_key="{tenant_key}"
)
```

4. **Report Error** (If blocking issues encountered):
```
report_error(
    job_id="<your-job-id>",
    error_type="test_failure",
    error_message="<full error details>",
    context="What you were doing when error occurred",
    tenant_key="{tenant_key}"
)
```
"""

    def _get_serena_optimizer_internal(self, tenant_key: str) -> Optional[SerenaOptimizer]:
        """
        Get or initialize Serena optimizer for tenant.

        Args:
            tenant_key: Tenant key for isolation

        Returns:
            SerenaOptimizer instance or None if initialization fails
        """
        if self.serena_optimizer is None:
            try:
                self.serena_optimizer = SerenaOptimizer(tenant_key=tenant_key)
                self._logger.info(f"Initialized Serena optimizer for tenant {tenant_key}")
            except (ImportError, ValueError, AttributeError) as e:
                self._logger.warning(f"Failed to initialize Serena optimizer: {e}")
                return None
        return self.serena_optimizer

    async def spawn_agent_legacy(
        self,
        project_id: str,
        role: AgentRole,
        custom_mission: Optional[str] = None,
        project_type: Optional[ProjectType] = None,
        additional_instructions: Optional[str] = None,
    ) -> AgentExecution:
        """
        Spawn a new agent with intelligent routing to Claude Code OR Codex/Gemini.

        Routes agents based on template.tool field:
        - tool='claude' → Claude Code (hybrid mode with auto-export)
        - tool='codex' → Codex CLI (job queue mode)
        - tool='gemini' → Gemini CLI (job queue mode)

        Args:
            project_id: Project UUID
            role: Agent role from AgentRole enum
            custom_mission: Optional custom mission override
            project_type: Optional project type for customization
            additional_instructions: Optional additional instructions

        Returns:
            Created AgentExecution instance
        """
        async with self._get_session() as session:
            # Get project
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Validate product is active before spawning agents
            if project.product_id:
                product = await session.get(Product, project.product_id)
                if product and not product.is_active:
                    raise ValueError(
                        f"Cannot spawn agent - product '{product.name}' is not active. "
                        f"Please activate the product before spawning agents."
                    )

            # Try to get agent template for routing
            template = await self._get_agent_template_internal(
                role=role.value,
                tenant_key=project.tenant_key,
                product_id=project.product_id,
                session=session,
            )

            # Route based on template.tool field
            if template:
                self._logger.info(
                    f"[spawn_agent_legacy] Routing {role.value} agent via template: "
                    f"tool={template.tool}, template={template.name}"
                )

                if template.tool == "claude":
                    # Claude Code mode: Auto-export template + create agent
                    agent = await self._spawn_claude_code_agent_internal(
                        session=session,
                        project=project,
                        role=role,
                        template=template,
                        custom_mission=custom_mission,
                        additional_instructions=additional_instructions,
                    )
                elif template.tool in ["codex", "gemini"]:
                    # Generic mode: Create job + link agent
                    agent = await self._spawn_generic_agent_internal(
                        session=session,
                        project=project,
                        role=role,
                        template=template,
                        custom_mission=custom_mission,
                        additional_instructions=additional_instructions,
                    )
                else:
                    self._logger.warning(
                        f"[spawn_agent_legacy] Unknown tool type: {template.tool}, falling back to default"
                    )
                    template = None  # Force fallback

                # If routing succeeded, return agent
                if template:
                    self._logger.info(f"[spawn_agent_legacy] Spawned {agent.tool_type} agent for project {project_id}")
                    return agent

            # FALLBACK: Original spawn logic (no template or unknown tool)
            self._logger.info(f"[spawn_agent_legacy] No template found for {role.value}, using legacy spawn logic")

            # Generate mission based on role
            if role == AgentRole.ORCHESTRATOR:
                # Use comprehensive orchestrator template
                additional_context = {"project_type": project_type} if project_type else None
                mission = await self.template_generator.generate_orchestrator_mission(
                    project_name=project.name,
                    project_mission=project.mission,
                    additional_context=additional_context,
                )
            else:
                # Use role-specific agent template
                mission = await self.template_generator.generate_agent_mission(
                    role=role.value,
                    project_name=project.name,
                    custom_mission=custom_mission,
                    additional_instructions=additional_instructions,
                )

            # SERENA OPTIMIZATION: Inject optimization rules into mission
            try:
                optimizer = self._get_serena_optimizer_internal(project.tenant_key)
                if optimizer:
                    injector = MissionOptimizationInjector(optimizer)

                    # Gather context for optimization
                    context_data = {
                        "project_id": project_id,
                        "project_type": project_type.value if project_type else "general",
                        "codebase_size": "medium",
                        "primary_language": "python",
                    }

                    # Inject optimization rules
                    optimized_mission = await injector.inject_optimization_rules(
                        agent_role=role.value, mission=mission, context_data=context_data
                    )

                    self._logger.info(f"Enhanced {role.value} agent mission with Serena optimization rules")
                    mission = optimized_mission

            except (ImportError, AttributeError, ValueError) as e:
                self._logger.warning(f"Failed to inject Serena optimization rules: {e}")
                # Continue with original mission if optimization fails

            # Create AgentJob (work order) and AgentExecution (executor instance)
            job_id = str(uuid4())
            agent_id = str(uuid4())

            # Create AgentJob (work order)
            agent_job = AgentJob(
                job_id=job_id,
                tenant_key=project.tenant_key,
                project_id=project_id,
                mission=mission,
                job_type=role.value,
                status="active",
            )
            session.add(agent_job)

            # Create AgentExecution (executor instance)
            agent_execution = AgentExecution(
                agent_id=agent_id,
                job_id=job_id,
                tenant_key=project.tenant_key,
                agent_display_name=role.value,
                agent_name=role.value,
                status="waiting",
                progress=0,
                tool_type="claude",  # Default to claude for legacy
                messages=[],
                spawned_by=None,  # No parent in fallback path
            )
            session.add(agent_execution)
            await session.commit()
            await session.refresh(agent_execution)

            self._logger.info(
                f"Spawned optimized {role.value} agent (fallback): job_id={job_id}, "
                f"agent_id={agent_id}, project={project_id}"
            )

            return agent_execution

    async def generate_mission_plan(
        self, product: "Product", project_description: str, user_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate missions from vision analysis.

        Algorithm:
        1. Analyze requirements (MissionPlanner.analyze_requirements)
        2. Generate missions (MissionPlanner.generate_missions)
        3. Return mission plan

        Args:
            product: Product with vision document
            project_description: Project requirements description
            user_id: Optional user ID for field priority configuration

        Returns:
            Dict mapping agent roles to Mission objects
        """
        self._logger.info(
            "Generating mission plan",
            extra={
                "product_id": str(product.id),
                "user_id": user_id,
                "has_user_id": user_id is not None,
            },
        )

        # Generate missions based on requirements
        missions = await self.mission_planner.generate_mission(
            product=product,
            project_description=project_description,
            user_id=user_id,
        )

        self._logger.info(f"Generated mission plan for product {product.id}: {len(missions)} missions created")

        return missions

    async def select_agents_for_mission(
        self, requirements: Any, tenant_key: str, product_id: Optional[str] = None
    ) -> list[Any]:
        """
        Smart agent selection based on requirements.

        Uses AgentSelector to query database templates.

        Args:
            requirements: RequirementAnalysis from MissionPlanner
            tenant_key: Tenant key for isolation
            product_id: Optional product ID for context

        Returns:
            List of AgentConfig objects
        """
        agent_configs = await self.agent_selector.select_agents(
            requirements=requirements, tenant_key=tenant_key, product_id=product_id
        )

        self._logger.info(f"Selected {len(agent_configs)} agents for mission: {[ac.role for ac in agent_configs]}")

        return agent_configs

    async def coordinate_agent_workflow(
        self, agent_configs: list[Any], workflow_type: str, tenant_key: str, project_id: str
    ) -> Any:
        """
        Monitor and coordinate agent team.

        Uses WorkflowEngine to execute workflow pattern.

        Args:
            agent_configs: List of AgentConfig objects
            workflow_type: 'waterfall' or 'parallel'
            tenant_key: Tenant key for isolation
            project_id: Project ID

        Returns:
            WorkflowResult from execution
        """
        # Lazy import to avoid circular dependency

        workflow_result = await self.workflow_engine.execute_workflow(
            agent_configs=agent_configs, workflow_type=workflow_type, tenant_key=tenant_key, project_id=project_id
        )

        self._logger.info(
            f"Workflow coordination complete for project {project_id}: "
            f"status={workflow_result.status}, "
            f"completed={len(workflow_result.completed)}, "
            f"failed={len(workflow_result.failed)}"
        )

        return workflow_result

    async def process_product_vision(
        self,
        tenant_key: str,
        product_id: str,
        project_requirements: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        MAIN ORCHESTRATION WORKFLOW.

        Complete workflow:
        1. Load product and validate vision
        2. Chunk vision if needed
        3. Create or use existing project
        4. Analyze requirements
        5. Select agents
        6. Generate missions
        7. Coordinate workflow

        Args:
            tenant_key: Tenant key for isolation
            product_id: Product UUID
            project_requirements: Project requirements description
            user_id: Optional user ID for field priority configuration
            project_id: Optional project UUID to use existing project instead of creating new

        Returns:
            Dict with:
            - project_id: Created/used project ID
            - mission_plan: Generated missions
            - selected_agents: List of agent roles
            - spawned_jobs: List of job IDs
            - workflow_result: Workflow execution result
            - token_reduction: Context prioritization metrics

        Raises:
            ValueError: If product not found or not active
        """
        self._logger.info(
            "Processing product vision",
            extra={
                "product_id": product_id,
                "tenant_key": tenant_key,
                "user_id": user_id,
                "has_user_id": user_id is not None,
                "project_id": project_id,
            },
        )

        # 1. Load product and validate vision
        async with self._get_session() as session:
            product = await session.get(Product, product_id)
            if not product or product.tenant_key != tenant_key:
                raise ValueError(f"Product {product_id} not found")

            # Validate product is active before processing
            if not product.is_active:
                raise ValueError(
                    f"Cannot process product vision - product '{product.name}' is not active. "
                    f"Activate the product before creating agent missions."
                )

            # Get vision content from VisionDocument relationship
            storage_type = product.primary_vision_storage_type
            if storage_type == "inline":
                vision_content = product.primary_vision_text
            elif storage_type == "file" and product.primary_vision_path:
                vision_content = Path(product.primary_vision_path).read_text(encoding="utf-8")
            else:
                raise ValueError(f"Product {product_id} has no vision document")

        # 2. Chunk vision if needed (using new vision_documents relationship)
        if not product.vision_is_chunked:
            self._logger.info(f"Chunking vision document for product {product_id}")
            chunker = VisionDocumentChunker(target_chunk_size=2000)
            chunks = chunker.chunk_document(vision_content, product_id=product_id)

            # Store chunks in database and mark primary vision document as chunked
            async with self._get_session() as session:
                db_product = await session.get(Product, product_id)
                # Mark the first vision document as chunked
                if db_product.vision_documents:
                    db_product.vision_documents[0].chunked = True
                await session.commit()

            self._logger.info(f"Chunked vision into {len(chunks)} chunks")

        # 3. Create project or use existing
        if project_id:
            # Use existing project
            async with self._get_session() as session:
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()
                if not project:
                    raise ValueError(f"Project {project_id} not found")
            self._logger.info(f"Using existing project {project_id}")
        else:
            # Create new project
            from src.giljo_mcp.services.project_service import ProjectService

            project_service = ProjectService(self.db_manager, self.tenant_manager)
            project = await project_service.create_project(
                name=f"Vision Project: {product.name}",
                description=project_requirements,
                tenant_key=tenant_key,
                product_id=product_id,
            )
            self._logger.info(f"Created new project {project.id}")

        # 4. Generate mission plan
        missions = await self.generate_mission_plan(product, project_requirements, user_id=user_id)

        # 5. Select agents
        analysis = await self.mission_planner.analyze_requirements(product, project_requirements)
        agent_configs = await self.select_agents_for_mission(
            requirements=analysis, tenant_key=tenant_key, product_id=product_id
        )

        # 6. Assign missions to agents
        for agent_config in agent_configs:
            if agent_config.role in missions:
                agent_config.mission = missions[agent_config.role]

        # 7. Coordinate workflow (default: waterfall)
        workflow_result = await self.coordinate_agent_workflow(
            agent_configs=agent_configs, workflow_type="waterfall", tenant_key=tenant_key, project_id=project.id
        )

        # 8. Calculate context prioritization metrics
        total_mission_tokens = sum(
            mission.token_count for mission in missions.values() if hasattr(mission, "token_count")
        )
        # Estimate what it would have been without optimization (3x)
        estimated_unoptimized = total_mission_tokens * 3
        token_reduction_percent = (
            ((estimated_unoptimized - total_mission_tokens) / estimated_unoptimized) * 100
            if estimated_unoptimized > 0
            else 0
        )

        # 9. Collect job IDs from workflow result
        spawned_jobs = []
        for stage in workflow_result.completed:
            if hasattr(stage, "job_ids"):
                spawned_jobs.extend(stage.job_ids)

        self._logger.info(
            f"Completed product vision processing for {product_id}: "
            f"project={project.id}, agents={len(agent_configs)}, "
            f"jobs={len(spawned_jobs)}, token_reduction={token_reduction_percent:.1f}%"
        )

        # 10. Return comprehensive result
        return {
            "project_id": project.id,
            "mission_plan": {role: mission.to_dict() for role, mission in missions.items()},
            "selected_agents": [ac.role for ac in agent_configs],
            "spawned_jobs": spawned_jobs,
            "workflow_result": workflow_result,
            "token_reduction": {
                "original_tokens": estimated_unoptimized,
                "optimized_tokens": total_mission_tokens,
                "reduction_percent": round(token_reduction_percent, 1),
            },
        }

    # ============================================================================
    # Orchestrator Instructions & Mission Management (Handover 0451 Phase 2)
    # ============================================================================

    async def get_orchestrator_instructions(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Fetch orchestrator mission with framing-based context instructions (Handover 0350b).

        Returns a lean response (~500 tokens) with:
        - identity: Orchestrator/project identifiers
        - project_description_inline: Description + mission (always inline)
        - context_fetch_instructions: Framing pointers to fetch_context() tool

        The orchestrator uses these instructions to call fetch_context() on-demand,
        avoiding the 50K+ token truncation risk of inline context.
        """
        try:
            async with self._get_session() as session:
                from sqlalchemy import and_
                from sqlalchemy.orm import joinedload, selectinload

                from src.giljo_mcp.mission_planner import MissionPlanner
                from src.giljo_mcp.models import AgentTemplate, Product, Project

                # Validate inputs
                if not job_id or not job_id.strip():
                    raise ValidationError(
                        message="Job ID is required",
                        error_code="VALIDATION_ERROR",
                        context={"method": "get_orchestrator_instructions"},
                    )

                if not tenant_key or not tenant_key.strip():
                    raise ValidationError(
                        message="Tenant key is required",
                        error_code="VALIDATION_ERROR",
                        context={"method": "get_orchestrator_instructions"},
                    )

                # Phase C: Query AgentExecution and join to AgentJob
                # Get current execution for this job (latest instance)
                result = await session.execute(
                    select(AgentExecution)
                    .options(joinedload(AgentExecution.job))
                    .where(
                        and_(
                            AgentExecution.job_id == job_id,
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.started_at.desc())
                )
                execution = result.scalars().first()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"Orchestrator execution for job {job_id} not found",
                        error_code="NOT_FOUND",
                        context={"job_id": job_id, "method": "get_orchestrator_instructions"},
                    )

                # Get the associated AgentJob
                agent_job = execution.job
                if not agent_job:
                    raise ResourceNotFoundError(
                        message=f"Agent job {job_id} not found",
                        error_code="NOT_FOUND",
                        context={"job_id": job_id, "method": "get_orchestrator_instructions"},
                    )

                # Verify it's an orchestrator
                if agent_job.job_type != "orchestrator":
                    raise ValidationError(
                        message=f"Job {job_id} is not an orchestrator",
                        error_code="VALIDATION_ERROR",
                        context={
                            "job_id": job_id,
                            "job_type": agent_job.job_type,
                            "method": "get_orchestrator_instructions",
                        },
                    )

                # Get project and product
                result = await session.execute(
                    select(Project).where(and_(Project.id == agent_job.project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise ResourceNotFoundError(
                        message="Project not found",
                        error_code="NOT_FOUND",
                        context={"project_id": str(agent_job.project_id), "method": "get_orchestrator_instructions"},
                    )

                product = None
                if project.product_id:
                    result = await session.execute(
                        select(Product)
                        .where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
                        .options(selectinload(Product.vision_documents))
                    )
                    product = result.scalar_one_or_none()

                # Get user configuration
                planner = MissionPlanner(self.db_manager)
                metadata = agent_job.job_metadata or {}
                user_id = metadata.get("user_id")

                # Handover 0346: Fetch FRESH user config if user_id available
                if user_id:
                    from src.giljo_mcp.tools.orchestration import _get_user_config

                    user_config = await _get_user_config(user_id, tenant_key, session)
                    field_priorities = user_config["field_priorities"]
                    depth_config = user_config["depth_config"]
                    logger.info(
                        "[USER_CONFIG] Fetched fresh user config for OrchestrationService",
                        extra={"job_id": job_id, "user_id": user_id},
                    )
                else:
                    field_priorities = metadata.get("field_priorities", {})
                    depth_config = metadata.get("depth_config", {})
                    logger.debug("[USER_CONFIG] No user_id, using frozen job_metadata config", extra={"job_id": job_id})

                # Handover 0350b: Generate framing instructions (replaces inline context)
                # This returns ~500 tokens instead of 4-8K (up to 50K with vision)
                fetch_instructions = planner._build_fetch_instructions(
                    product=product,
                    project=project,
                    field_priorities=field_priorities,
                    depth_config=depth_config,
                )

                # Get agent templates for reference
                result = await session.execute(
                    select(AgentTemplate)
                    .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True))
                    .limit(8)
                )
                templates = result.scalars().all()

                # Build agent template summary (needed for spawning - staging prompt references this)
                template_list = [
                    {"name": t.name, "role": t.role, "description": t.description[:200] if t.description else ""}
                    for t in templates
                ]

                # Resolve project path (local developer folder pointer, stored on Product)
                project_path = None
                if product is not None:
                    # Product.project_path is a developer-provided filesystem hint.
                    # It is returned verbatim so agents know where the codebase lives locally.
                    project_path = getattr(product, "project_path", None)

                # Handover 0408: Read integration toggles from config
                include_serena = False
                git_integration_enabled = False
                try:
                    from pathlib import Path

                    import yaml

                    config_path = Path.cwd() / "config.yaml"
                    if config_path.exists():
                        with open(config_path, encoding="utf-8") as f:
                            config_data = yaml.safe_load(f) or {}
                        features = config_data.get("features", {})
                        include_serena = features.get("serena_mcp", {}).get("use_in_prompts", False)
                        git_integration_enabled = features.get("git_integration", {}).get("enabled", False)
                except (OSError, yaml.YAMLError, KeyError, ValueError, TypeError) as e:
                    logger.warning(f"[INTEGRATIONS] Failed to read config: {e}")

                # Build framing-based response (Handover 0350b + Phase C)
                # Includes: identity, project context, fetch instructions, AND agent templates
                response = {
                    "identity": {
                        "job_id": job_id,
                        "agent_id": execution.agent_id,  # Phase C: Add executor UUID
                        "project_id": str(project.id),
                        "project_name": project.name,
                        "tenant_key": tenant_key,
                        "id_glossary": {
                            "job_id": "Use for: acknowledge_job, report_progress, complete_job, report_error",
                            "agent_id": "Use for: send_message(from_agent), receive_messages",
                        },
                    },
                    "project_description_inline": {
                        "description": project.description or "",
                        "mission": agent_job.mission or "",  # Phase C: Mission from AgentJob
                        "project_path": project_path,
                    },
                    "context_fetch_instructions": fetch_instructions,
                    "agent_templates": template_list,  # Staging prompt: "Returns: ... AVAILABLE AGENT TEMPLATES"
                    "mcp_tools_available": [
                        "fetch_context",
                        "spawn_agent_job",
                        "get_available_agents",
                        "send_message",
                        "check_succession_status",
                        "create_successor_orchestrator",
                        "report_progress",
                        "complete_job",
                    ],
                    "context_budget": execution.context_budget or 150000,  # Phase C: From AgentExecution
                    "context_used": execution.context_used or 0,  # Phase C: From AgentExecution
                    "field_priorities": field_priorities,
                    "thin_client": True,
                    "architecture": "framing_based",
                    # Handover 0408: Integration toggles status
                    "integrations": {
                        "serena_mcp_enabled": include_serena,
                        "git_integration_enabled": git_integration_enabled,
                    },
                }

                # Handover 0351: Add CLI mode rules when execution_mode == 'claude_code_cli'
                # agent_name is SINGLE SOURCE OF TRUTH for template matching
                execution_mode = getattr(project, "execution_mode", None) or metadata.get(
                    "execution_mode", "multi_terminal"
                )
                if execution_mode == "claude_code_cli":
                    allowed_agent_names = [t.name for t in templates]

                    response["agent_spawning_constraint"] = {
                        "mode": "strict_task_tool",
                        "allowed_agent_names": allowed_agent_names,
                        "instruction": (
                            "CRITICAL: You MUST use Claude Code's native Task tool for agent spawning. "
                            "The agent_name parameter must be EXACTLY one of the allowed template names. "
                            f"Allowed agent names: {allowed_agent_names}"
                        ),
                    }

                    # Handover 0389: Build dynamic example from actual allowed agent names
                    example_agents = allowed_agent_names[:2] if len(allowed_agent_names) >= 2 else allowed_agent_names
                    example_str = ", ".join(f"'{n}'" for n in example_agents) if example_agents else "'implementer'"

                    response["cli_mode_rules"] = {
                        "agent_name_usage": (
                            "SINGLE SOURCE OF TRUTH - binds DB record, Task tool, and template filename. "
                            f"MUST match template filename exactly (e.g., {example_str})."
                        ),
                        "agent_display_name_usage": (
                            "Dashboard label - what humans see in UI. "
                            "MUST be unique per agent instance when spawning multiple agents of same template."
                        ),
                        "multi_agent_example": {
                            "scenario": "Spawning 2 implementers for different domains",
                            "agent_1": {"agent_name": "implementer", "agent_display_name": "api-implementer"},
                            "agent_2": {"agent_name": "implementer", "agent_display_name": "ui-implementer"},
                        },
                        "task_tool_mapping": "Task(subagent_type=X) where X = agent_name from spawn_agent_job.",
                        "validation": "soft",
                        "template_locations": [
                            "{project}/.claude/agents/",
                            "~/.claude/agents/",
                        ],
                    }

                    logger.info(
                        f"[CLI_MODE_RULES] Added CLI mode rules for orchestrator {job_id}",
                        extra={
                            "job_id": job_id,
                            "execution_mode": execution_mode,
                            "allowed_names": allowed_agent_names,
                        },
                    )

                # Handover 0415: Add chapter-based orchestrator protocol
                # Handover 0420d: Exclude CH5 during staging to save tokens
                from src.giljo_mcp.tools.orchestration import _build_orchestrator_protocol

                cli_mode = execution_mode == "claude_code_cli"
                # Staging phase (waiting status) does not need CH5 implementation reference
                is_staging = agent_job.status == "waiting"
                orchestrator_protocol = _build_orchestrator_protocol(
                    cli_mode=cli_mode,
                    context_budget=execution.context_budget or 150000,
                    project_id=str(project.id),
                    orchestrator_id=job_id,
                    tenant_key=tenant_key,
                    include_implementation_reference=not is_staging,  # False for staging, True for implementation
                )
                response["orchestrator_protocol"] = orchestrator_protocol

                # Handover 0431: Inject orchestrator identity/behavioral guidance
                # Orchestrators don't have AgentTemplate records (SYSTEM_MANAGED_ROLES skip)
                # so they get behavioral guidance via this field instead of fetch_context(self_identity)
                from src.giljo_mcp.template_seeder import get_orchestrator_identity_content

                response["orchestrator_identity"] = get_orchestrator_identity_content()

                logger.info(
                    "[FRAMING_BASED] Returning framing-based orchestrator instructions",
                    extra={
                        "job_id": job_id,
                        "critical_count": len(fetch_instructions.get("critical", [])),
                        "important_count": len(fetch_instructions.get("important", [])),
                        "reference_count": len(fetch_instructions.get("reference", [])),
                    },
                )

                return response

        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            logger.exception(f"Failed to get orchestrator instructions: {e}")
            raise OrchestrationError(
                message="Failed to get orchestrator instructions",
                error_code="INTERNAL_ERROR",
                context={"job_id": job_id, "error": str(e)},
            ) from e

    async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str) -> dict[str, Any]:
        """
        Update the mission field of an AgentJob.

        Handover 0380: Used by orchestrators to persist their execution plan during staging.
        This allows fresh-session orchestrators to retrieve the plan via get_agent_mission()
        during implementation phase.

        Args:
            job_id: The AgentJob.job_id (work order UUID)
            tenant_key: Tenant isolation key
            mission: The execution plan/mission to persist

        Returns:
            {"success": True, "job_id": job_id, "mission_updated": True}
        """
        try:
            async with self._get_session() as session:
                from sqlalchemy import and_, select

                from src.giljo_mcp.models.agent_identity import AgentJob

                result = await session.execute(
                    select(AgentJob).where(
                        and_(
                            AgentJob.job_id == job_id,
                            AgentJob.tenant_key == tenant_key,
                        )
                    )
                )
                job = result.scalar_one_or_none()

                if not job:
                    raise ResourceNotFoundError(
                        message=f"Agent job {job_id} not found",
                        error_code="NOT_FOUND",
                        context={
                            "job_id": job_id,
                            "tenant_key": tenant_key,
                            "method": "update_agent_mission",
                            "troubleshooting": [
                                "Verify job_id is correct",
                                "Ensure tenant_key matches",
                            ],
                        },
                    )

                job.mission = mission
                await session.commit()

                # Emit WebSocket event for UI update
                if self._websocket_manager:
                    try:
                        await self._websocket_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="job:mission_updated",
                            data={
                                "job_id": job_id,
                                "job_type": job.job_type,
                                "mission_length": len(mission),
                                "project_id": str(job.project_id) if job.project_id else None,
                            },
                        )
                        logger.info(
                            f"[WEBSOCKET] Broadcasted job:mission_updated for {job_id}",
                            extra={"job_id": job_id, "tenant_key": tenant_key},
                        )
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                        logger.warning(f"[WEBSOCKET] Failed to broadcast job:mission_updated: {ws_error}")

                logger.info(
                    f"[UPDATE_AGENT_MISSION] Updated mission for job {job_id}",
                    extra={
                        "job_id": job_id,
                        "job_type": job.job_type,
                        "mission_length": len(mission),
                        "tenant_key": tenant_key,
                    },
                )

                return {
                    "success": True,
                    "job_id": job_id,
                    "mission_updated": True,
                    "mission_length": len(mission),
                }

        except Exception as e:
            logger.exception(f"Failed to update agent mission: {e}")
            raise OrchestrationError(
                message="Failed to update agent mission",
                error_code="INTERNAL_ERROR",
                context={"job_id": job_id, "error": str(e)},
            ) from e

    async def create_successor_orchestrator(
        self, current_job_id: str, tenant_key: str, reason: str = "manual"
    ) -> dict[str, Any]:
        """
        Create successor orchestrator context via 360 Memory (Handover 0461f).

        SIMPLIFIED: No longer creates new AgentExecution rows or swaps IDs.
        Instead, writes session context to 360 Memory and resets context_used.

        Args:
            current_job_id: Current orchestrator job_id or agent_id
            tenant_key: Tenant key for isolation
            reason: Handover reason (default: "manual")

        Returns:
            Dict with success status, continuation instructions, and memory entry info

        Raises:
            ResourceNotFoundError: When execution or project not found
            ValidationError: When non-orchestrator attempts succession
            OrchestrationError: When succession operation fails
        """
        try:
            from datetime import datetime, timezone

            async with self._get_session() as session:
                # Find current execution by job_id
                result = await session.execute(
                    select(AgentExecution)
                    .where(
                        and_(
                            AgentExecution.job_id == current_job_id,
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.started_at.desc())
                )
                execution = result.scalars().first()

                # Fallback: try agent_id if job_id didn't match
                if not execution:
                    result = await session.execute(
                        select(AgentExecution).where(
                            and_(
                                AgentExecution.agent_id == current_job_id,
                                AgentExecution.tenant_key == tenant_key,
                            )
                        )
                    )
                    execution = result.scalars().first()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"Execution not found for {current_job_id}",
                        context={"job_id": current_job_id, "tenant_key": tenant_key},
                    )

                # Verify it's an orchestrator
                if execution.agent_display_name != "orchestrator":
                    raise ValidationError(
                        message=f"Only orchestrators can use succession (found: {execution.agent_display_name})",
                        context={
                            "job_id": current_job_id,
                            "agent_display_name": execution.agent_display_name,
                        },
                    )

                # Get project_id from associated job
                job_result = await session.execute(select(AgentJob).where(AgentJob.job_id == execution.job_id))
                job = job_result.scalars().first()

                if not job or not job.project_id:
                    raise ResourceNotFoundError(
                        message="Associated project not found", context={"job_id": execution.job_id}
                    )

                # Build session context for 360 Memory
                session_context = {
                    "context_used": execution.context_used or 0,
                    "context_budget": execution.context_budget or 150000,
                    "progress": execution.progress or 0,
                    "current_task": execution.current_task,
                    "agent_id": execution.agent_id,
                    "job_id": execution.job_id,
                    "reason": reason,
                    "handover_at": datetime.now(timezone.utc).isoformat(),
                }

                # Write to 360 Memory using the existing tool
                from src.giljo_mcp.tools.write_360_memory import write_360_memory

                memory_result = await write_360_memory(
                    project_id=str(job.project_id),
                    summary=f"Session handover ({reason}) at {execution.context_used or 0}/{execution.context_budget or 150000} tokens.",
                    key_outcomes=[
                        f"Progress: {execution.progress or 0}%",
                        f"Task: {execution.current_task or 'N/A'}",
                    ],
                    decisions_made=[f"Handover triggered: {reason}"],
                    entry_type="session_handover",
                    author_job_id=execution.job_id,
                    tenant_key=tenant_key,
                )

                # Reset context_used (same agent continues, fresh context)
                old_context = execution.context_used or 0
                execution.context_used = 0
                await session.commit()

                logger.info(
                    f"Simple succession: {execution.agent_id} context reset "
                    f"({old_context} -> 0), reason: {reason}, "
                    f"memory_entry: {memory_result.get('entry_id') if isinstance(memory_result, dict) else 'created'}"
                )

                # Return simplified response - SAME agent_id (no swap!)
                return {
                    "success": True,
                    "job_id": execution.job_id,
                    "agent_id": execution.agent_id,  # SAME agent_id (no swap)
                    "context_reset": True,
                    "old_context_used": old_context,
                    "new_context_used": 0,
                    "memory_entry_created": True,
                    "reason": reason,
                    "message": "Session context written to 360 Memory. Use fetch_context(categories=['memory_360']) in new session to retrieve.",
                }

        except (ResourceNotFoundError, ValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.exception(f"Failed to create successor orchestrator: {e}")
            raise OrchestrationError(
                message=f"Failed to create successor orchestrator: {e!s}",
                context={"job_id": current_job_id, "reason": reason},
            ) from e

    async def check_succession_status(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Check if orchestrator should trigger succession (Handover 0080 + Phase C)"""
        try:
            async with self._get_session() as session:
                # Phase C: Get current execution (latest instance)
                result = await session.execute(
                    select(AgentExecution)
                    .where(
                        and_(
                            AgentExecution.job_id == job_id,
                            AgentExecution.tenant_key == tenant_key,
                        )
                    )
                    .order_by(AgentExecution.started_at.desc())
                )
                execution = result.scalars().first()

                if not execution:
                    raise ResourceNotFoundError(
                        message=f"Job {job_id} not found",
                        context={"job_id": job_id, "method": "check_succession_status"},
                    )

                # Calculate context usage percentage (from execution)
                context_used = execution.context_used or 0
                context_budget = execution.context_budget or 200000
                usage_percentage = (context_used / context_budget) * 100 if context_budget > 0 else 0

                # Determine if succession should be triggered (90% threshold)
                should_trigger = usage_percentage >= 90.0

                recommendation = ""
                if usage_percentage < 70:
                    recommendation = "Context usage healthy. Continue normal operation."
                elif usage_percentage < 85:
                    recommendation = "Monitor context usage. Begin planning for potential succession."
                elif usage_percentage < 90:
                    recommendation = "Context usage high. Prepare for succession soon."
                else:
                    recommendation = "Trigger succession now to avoid context overflow."

                return {
                    "should_trigger": should_trigger,
                    "context_used": context_used,
                    "context_budget": context_budget,
                    "usage_percentage": round(usage_percentage, 2),
                    "threshold_reached": should_trigger,
                    "recommendation": recommendation,
                }

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Failed to check succession status: {e}")
            raise OrchestrationError(
                message="Failed to check succession status", context={"job_id": job_id, "error": str(e)}
            ) from e
