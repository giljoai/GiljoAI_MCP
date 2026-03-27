"""
Protocol Builder - Protocol generation helpers for orchestration.

Extracted from orchestration_service.py (Handover 0750e2) to reduce monolith size.
These are stateless module-level functions with zero shared class state.

Responsibilities:
- Team context header generation for agent missions
- Agent lifecycle protocol generation (5-phase protocol)
- User configuration fetching and normalization
- Orchestrator protocol building (chapter-based)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select


if TYPE_CHECKING:
    from src.giljo_mcp.models import AgentExecution

from src.giljo_mcp.config.defaults import DEFAULT_CATEGORY_TOGGLES
from src.giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as _DEFAULT_DEPTH_CONFIG
from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY as _DEFAULT_FIELD_PRIORITY


logger = logging.getLogger(__name__)


def _generate_team_context_header(
    current_job: AgentExecution,
    all_project_jobs: list[AgentExecution],
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
        dependencies_upstream.extend([upstream for upstream in rules["upstream"] if upstream in other_types])
        dependencies_downstream.extend([downstream for downstream in rules["downstream"] if downstream in other_types])

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
    coordination_section = f"""## COORDINATION
- **UUID-ONLY MESSAGING**: Always use agent_id UUIDs from the team table above when addressing agents
- Use `mcp__giljo-mcp__send_message(to_agents=["{agent_id}"], from_agent="{agent_id}", ...)` with UUID values
- Use `mcp__giljo-mcp__receive_messages` to check for instructions or updates
- When you complete a deliverable, send a brief status message to downstream agents using their agent_id UUIDs
- Use `to_agents=['all']` for broadcast messages to the entire team
- NEVER use display names (e.g., "orchestrator", "implementer") in to_agents - use the UUID from the team table
- Check `full_protocol` for detailed messaging and progress reporting guidance

---

"""

    return identity_section + "\n" + team_section + "\n" + dependencies_section + "\n" + coordination_section


def _generate_orchestrator_protocol(job_id: str, tenant_key: str, executor_id: str) -> str:
    """
    Generate 3-phase orchestrator coordination protocol (Handover 0830).

    Unlike the worker 5-phase lifecycle, the orchestrator is reactive and user-mediated.
    It reads pre-planned TODOs from staging — never replaces them with todo_items.
    """
    return f"""These are your coordination operating procedures. Follow them from startup through closeout.

## Orchestrator Coordination Protocol (3 Phases)

### PHASE 1 — STARTUP (execute once, after get_agent_mission)

1. Read the `current_team_state` field from this response — it is live-queried, not stale.
2. Read your pre-planned coordination TODOs (written during staging, waiting for you).
   **DO NOT replace them** with a new list.
   If additional tasks are needed mid-implementation, use `todo_append` — **NEVER** `todo_items`.
3. Report to user:
   - Agent names, statuses, and phase order (from `current_team_state`)
   - "Copy agent prompts from the dashboard to start them."
   - "I will coordinate when you need me."

### PHASE 2 — REACTIVE COORDINATION (user-triggered only — no polling, no loops)

**"check messages":**
  → `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
  → Summarize content for user

**"agent X is blocked":**
  → Read the message content
  → Consult your `mission` field for relevant context
  → Reply: `mcp__giljo-mcp__send_message(to_agents=["<agent_id>"], content="...", from_agent="{executor_id}", project_id="...", message_type="direct")`
  → Tell user: "Go to that agent's terminal and say: the orchestrator responded"

**"spawn a replacement agent":**
  → `mcp__giljo-mcp__spawn_agent_job(...)`
  → Tell user to paste the new prompt in a NEW terminal
  → New agent reads predecessor context via `get_agent_mission`

**"check status":**
  → `mcp__giljo-mcp__get_workflow_status(project_id="...")`
  → Report agent statuses to user

**Adding new tasks mid-implementation:**
  → `mcp__giljo-mcp__report_progress(job_id="{job_id}", tenant_key="{tenant_key}", todo_append=[...])`
  → **NEVER** use `todo_items` — it will wipe your pre-planned coordination TODOs

### PHASE 3 — CLOSEOUT (all agents complete or decommissioned)

1. `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` — process final reports
2. `mcp__giljo-mcp__write_360_memory()` — preserve project knowledge for future projects
3. `mcp__giljo-mcp__complete_job(job_id="{job_id}", result={{"summary": "...", "artifacts": [...]}})` — mark orchestrator complete
4. Tell user: "Project complete. Use /gil_add for follow-up tasks or tech debt."

## ORCHESTRATOR CONSTRAINTS
- **Git commit requirement does NOT apply.** You coordinate, you do not commit.
- **Handover-on-context-exhaustion does NOT apply.** If context is exhausted, tell the user.
- **If uncertain what to do, ask the user.** You are user-mediated by design.

---
**Your Identifiers:**
- job_id (work order): `{job_id}` — Use for progress, completion
- agent_id (executor): `{executor_id}` — Use for messages (from_agent and receive_messages)

**MESSAGING RULE: UUID-ONLY ADDRESSING**
- ALWAYS use agent_id UUIDs in `to_agents` (from current_team_state)
- NEVER use display names like "implementer" in `to_agents`
- Your `from_agent` is always: `{executor_id}`

**CRITICAL: MCP tools are NATIVE tool calls. Use them like Read/Write/Bash.**
**Do NOT use curl, HTTP, or SDK calls.**
"""


def _generate_agent_protocol(
    job_id: str,
    tenant_key: str,
    agent_name: str,
    agent_id: str | None = None,
    execution_mode: str = "multi_terminal",
    git_integration_enabled: bool = False,
    job_type: str = "agent",
) -> str:
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
        agent_name: Agent name (matches template filename)
        agent_id: Optional executor UUID (defaults to job_id for backwards compat)

    Returns:
        Multi-line protocol string with 5 phases and MCP tool references
    """
    # Use agent_id if provided, otherwise fall back to job_id (backwards compat)
    executor_id = agent_id or job_id

    # Handover 0830: Orchestrator protocol fork — 3-phase coordination lifecycle
    if job_type == "orchestrator":
        return _generate_orchestrator_protocol(job_id, tenant_key, executor_id)

    # 0497d: Conditional Phase 4 blocks
    git_commit_block = ""
    if git_integration_enabled:
        git_commit_block = """
### Git Commit (REQUIRED - Git Integration Enabled)
Before calling `complete_job()`, commit your work:
1. Stage your changes: `git add` relevant files (never use `git add -A`)
2. Write a descriptive commit message summarizing your work
3. Include the commit hash in your completion result:
   `complete_job(job_id, result={"summary": "...", "commits": ["abc123"], "artifacts": [...]})`
"""

    gil_add_block = ""
    if execution_mode == "multi_terminal":
        gil_add_block = """
### User Guidance (Multi-Terminal)
After completing your work, tell the user:
"My work is complete. If you discovered technical debt or follow-up work,
tell me and I'll use /gil_add to save it to your dashboard."
"""

    # Conditional Phase 1 Step 4: scope TodoWrite to job_type
    if job_type == "orchestrator":
        phase1_step4 = (
            "4. **MANDATORY: Create TodoWrite task list** (BEFORE coordination):\n"
            "   - Orchestration ONLY: spawning, monitoring, coordinating, unblocking, closing out\n"
            "   - NEVER include implementation, testing, or documentation tasks — those belong to your agents\n"
            '   - Count and announce: "X steps to complete: [list items]"\n'
            "   - NEVER skip this step - planning prevents poor execution"
        )
    else:
        phase1_step4 = (
            "4. **MANDATORY: Create TodoWrite task list** (BEFORE implementation):\n"
            "   - Break mission into 3-7 specific, actionable tasks\n"
            '   - Count and announce: "X steps to complete: [list items]"\n'
            "   - NEVER skip this step - planning prevents poor execution"
        )

    # Handover 0825: Framing directive for lifecycle protocol
    protocol_framing = "These are your lifecycle operating procedures. Follow them from startup through completion.\n\n"
    return (
        protocol_framing
        + rf"""## Agent Lifecycle Protocol (5 Phases)

### Phase 1: STARTUP (BEFORE ANY WORK)
0. **ENVIRONMENT DETECTION**:
   Detect your shell environment before executing tasks:
   Call: `python -c "import os; print(os.environ.get('SHELL', os.environ.get('COMSPEC', 'unknown')))"`
   This detects the **actual shell** (bash, zsh, powershell, cmd), not just the OS.
   Adapt commands to the detected shell:
   - If shell contains "bash" or "zsh" (includes Git Bash on Windows):
     Sleep: `sleep N` | Clear: `clear` | Paths: use `/`
   - If shell contains "powershell" or "pwsh":
     Sleep: `Start-Sleep -Seconds N` | Clear: `cls` | Paths: use `\` or `/`
   - If shell contains "cmd":
     Sleep: `timeout /t N /nobreak >nul` | Clear: `cls` | Paths: use `\`
   - Default (unknown): use `sleep N` (works in most environments)

   **CONTEXT AWARENESS**: Your mission contains authoritative values including `project_path`.
   When creating files or referencing directories, use context-provided paths.
   Do NOT hardcode paths observed in your terminal environment.

1. Call `mcp__giljo-mcp__get_agent_mission(job_id="{job_id}", tenant_key="{tenant_key}")` - Get mission (auto-transitions to WORKING)
2. Call `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` - Check for instructions
3. Review any messages and incorporate feedback BEFORE starting work

{phase1_step4}

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
{git_commit_block}{gil_add_block}
### Phase 5: ERROR HANDLING & BLOCKED STATUS

**To mark yourself BLOCKED** (unclear requirements, waiting for clarification):
1. Call `mcp__giljo-mcp__report_error(job_id="{job_id}", error="BLOCKED: <reason>")`
   - Sets status to "blocked" and stores block_reason
2. Send message to orchestrator explaining what you need (use orchestrator's agent_id UUID from YOUR TEAM table):
   - `mcp__giljo-mcp__send_message(to_agents=["<orchestrator-agent-id-uuid>"], content="BLOCKER: <details>", from_agent="{executor_id}", project_id="...", message_type="direct")`
   - ALWAYS use the orchestrator's agent_id UUID, NEVER the display name "orchestrator"
3. STOP work and poll for response (use longer intervals while blocked — 15-20 seconds between polls, up to 5 attempts):
   - `mcp__giljo-mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`

**To resume from BLOCKED**:
1. After receiving guidance, call `report_progress()` with your updated TODO list:
   - `mcp__giljo-mcp__report_progress(job_id="{job_id}", tenant_key="{tenant_key}", todo_items=[...])`
   - This automatically transitions your status from "blocked" back to "working"
2. Continue execution with Phase 2

**Use BLOCKED for**: Unclear requirements, missing context, waiting for decisions, unrecoverable errors (all errors use blocked status)

## Handover on Context Exhaustion

If you run out of context before completing:

1. Call `write_360_memory(entry_type="handover_closeout")` with progress summary:
   - summary: Brief overview of work completed so far
   - key_outcomes: What you accomplished before running out of context
   - decisions_made: Key decisions and rationale for successor
2. Notify orchestrator via `send_message(to_agents=["<orchestrator-agent-id-uuid>"], ...)` about context exhaustion (use UUID from YOUR TEAM table)
3. Call `complete_job()` to mark yourself complete

Do NOT write 360 memory on normal completion - orchestrator handles that.

---
**Your Identifiers:**
- job_id (work order): `{job_id}` - Use for mission, progress, completion
- agent_id (executor): `{executor_id}` - Use for messages (from_agent and receive_messages)

**MESSAGING RULE: UUID-ONLY ADDRESSING**
- ALWAYS use agent_id UUIDs in `to_agents` (from YOUR TEAM table in mission header)
- NEVER use display names like "orchestrator" or "implementer" in `to_agents`
- Use `to_agents=['all']` for broadcast only
- Your `from_agent` is always your agent_id: `{executor_id}`

**Message Prefixes:**
- **BLOCKER:** - Urgent, needs immediate help (triggers blocked status)
- **PROGRESS:** - Milestone update to orchestrator
- **COMPLETE:** - Work finished notification
- **READY:** - Available for new work
- **REQUEST_CONTEXT:** - Need broader project context from orchestrator

**Requesting Broader Context:**
If your mission references undefined entities, has unclear dependencies, or ambiguous scope:
1. Send: `send_message(to_agents=["<orchestrator-uuid>"], content="REQUEST_CONTEXT: <specific need>", from_agent="{executor_id}", project_id="...", message_type="direct")`
2. Be specific (e.g., "REQUEST_CONTEXT: What database schema is used for user auth?")
3. Wait for response via `receive_messages()`
4. Do NOT guess at major ambiguities - ask first

**When to Check Messages:**
- Phase 1 (STARTUP): Before starting work
- Phase 2 (EXECUTION): After each TodoWrite task
- Phase 3 (PROGRESS): Before reporting progress
- Phase 4 (COMPLETION): Before calling complete_job()

**CRITICAL: MCP tools are NATIVE tool calls. Use them like Read/Write/Bash.**
**Do NOT use curl, HTTP, or SDK calls.**
"""
    )


# ============================================================================
# MODULE-LEVEL HELPER FUNCTIONS (Moved from tools/orchestration.py - Phase 2)
# These were previously imported back INTO this service creating inverted
# dependency (service importing from tools). Now they live here natively.
# ============================================================================

# Extract inner structure for backward compatibility with existing code
# defaults.py uses versioned structure: {"version": "4.0", "priorities": {...}}
# This code expects flat structure: {"field": {"toggle": True}}
DEFAULT_FIELD_PRIORITIES = _DEFAULT_FIELD_PRIORITY["priorities"]
# Handover 0840d: DEFAULT_DEPTH_CONFIG is now a flat dict (no "depths" wrapper)
DEFAULT_DEPTH_CONFIG = _DEFAULT_DEPTH_CONFIG


def _normalize_field_toggles(field_config: dict[str, Any]) -> dict[str, bool]:
    """
    Normalize field config to a flat toggle dict.

    Supports multiple input formats:
    - v3.0: {"field": {"toggle": True}}
    - v2.x legacy: {"field": {"toggle": True, "priority": X}}
    - Flat bool: {"field": True}
    - Legacy int: {"field": 1} (treated as enabled if < 4)

    Args:
        field_config: Dict with field toggle/priority values

    Returns:
        Dict mapping field names to boolean toggle values
    """
    normalized = {}
    for field_key, value in field_config.items():
        if isinstance(value, dict):
            normalized[field_key] = value.get("toggle", True)
        elif isinstance(value, bool):
            normalized[field_key] = value
        elif isinstance(value, int):
            normalized[field_key] = value < 4
        else:
            normalized[field_key] = True
    return normalized


async def _get_user_config(
    user_id: str,
    tenant_key: str,
    session: Any,  # AsyncSession type hint would create circular import
) -> dict[str, Any]:
    """
    Fetch user's field toggle config and depth config from normalized tables/columns.

    Handover 0840d: Reads from user_field_priorities table and depth columns on users.

    Args:
        user_id: User UUID
        tenant_key: Tenant isolation key
        session: SQLAlchemy AsyncSession

    Returns:
        dict with 'field_toggles' and 'depth_config' keys
    """
    from src.giljo_mcp.models.auth import User, UserFieldPriority

    try:
        result = await session.execute(
            select(User).where(and_(User.id == user_id, User.tenant_key == tenant_key, User.is_active))
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "user_not_found_using_defaults",
                extra={"user_id": user_id, "tenant_key": tenant_key},
            )
            normalized_defaults = _normalize_field_toggles(DEFAULT_FIELD_PRIORITIES.copy())
            return {"field_toggles": normalized_defaults, "depth_config": DEFAULT_DEPTH_CONFIG.copy()}

        # Build field toggles from user_field_priorities table
        prio_result = await session.execute(
            select(UserFieldPriority).where(
                and_(UserFieldPriority.user_id == user_id, UserFieldPriority.tenant_key == tenant_key)
            )
        )
        rows = prio_result.scalars().all()

        if rows:
            # Start with defaults, override with user rows
            field_toggles = dict(DEFAULT_CATEGORY_TOGGLES)
            for row in rows:
                field_toggles[row.category] = row.enabled
            # Always-on categories
            field_toggles["product_core"] = True
            field_toggles["project_description"] = True
        else:
            field_toggles = _normalize_field_toggles(DEFAULT_FIELD_PRIORITIES.copy())

        # Build depth config from columns (normalize keys for internal use)
        key_mapping = {
            "memory_last_n_projects": "memory_360",
            "git_commits": "git_history",
            "agent_templates": "agent_templates",
            "vision_documents": "vision_documents",
        }

        raw_depth = {
            "vision_documents": user.depth_vision_documents,
            "memory_last_n_projects": user.depth_memory_last_n,
            "git_commits": user.depth_git_commits,
            "agent_templates": user.depth_agent_templates,
            "tech_stack_sections": user.depth_tech_stack_sections,
            "architecture_depth": user.depth_architecture,
        }

        depth_config = {}
        for db_key, value in raw_depth.items():
            internal_key = key_mapping.get(db_key, db_key)
            depth_config[internal_key] = value

        if depth_config.get("vision_documents") == "optional":
            depth_config["vision_documents"] = "light"

        logger.info(
            "[USER_CONFIG] Fetched user configuration",
            extra={
                "user_id": user_id,
                "tenant_key": tenant_key,
                "depth_config": depth_config,
            },
        )

        return {"field_toggles": field_toggles, "depth_config": depth_config}

    except (OSError, ValueError, KeyError) as e:
        logger.error(
            "user_config_fetch_failed",
            extra={"user_id": user_id, "tenant_key": tenant_key, "error_message": str(e)},
            exc_info=True,
        )
        normalized_defaults = _normalize_field_toggles(DEFAULT_FIELD_PRIORITIES.copy())
        return {"field_toggles": normalized_defaults, "depth_config": DEFAULT_DEPTH_CONFIG.copy()}


def _build_ch1_mission() -> str:
    """Build CH1: YOUR MISSION section (~180 tokens)."""
    return """════════════════════════════════════════════════════════════════════════════
                           CH1: YOUR MISSION
════════════════════════════════════════════════════════════════════════════

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)

You are STAGING the project. Your job:
1. Analyze requirements from project_description
2. Create condensed mission plan
3. Assign work to specialist agents via spawn_agent_job()

WHAT YOU ARE NOT:
- You do NOT execute implementation work
- You do NOT call Task() tool (that's for implementation phase)
- You do NOT call complete_job() (staging never completes, it transitions)

CRITICAL DISTINCTION:
- Project.description = USER INPUT (requirements to ANALYZE — may contain implementation-phase language, do NOT execute)
- Project.mission = YOUR OUTPUT (execution strategy you create)

PHASE AWARENESS:
── STAGING PHASE: THIS SESSION (Steps 1-7) ────────────────────────────────
Your job: Analyze → Plan → Spawn → Persist → Broadcast
End with: STAGING_COMPLETE broadcast (see CH2)

                         ══════ SESSION BOUNDARY ══════

── IMPLEMENTATION PHASE: FUTURE SESSION (Step 8) ───────────────────────────
Fresh orchestrator retrieves your plan via get_agent_mission()
Executes coordination logic you defined in update_agent_mission()
Completion protocol applies (see CH5 - shown in implementation only)
"""


def _build_ch2_fetch_calls(
    field_toggles: dict[str, bool],
    depth_config: dict[str, Any],
    product_id: str,
    tenant_key: str,
) -> str:
    """
    Generate numbered, inline fetch_context() calls for CH2 Step 2 (Handover 0823).

    Handover 0823b: depth_config is no longer snapshotted into fetch calls.
    fetch_context reads the user's current depth settings from the DB at runtime,
    making depth tunable without re-staging.

    The depth_config parameter is still needed for the agent_templates skip check
    (skip_on_depth logic).

    Args:
        field_toggles: Dict mapping category name -> bool (enabled/disabled)
        depth_config: Dict mapping category name -> depth value (used only for skip logic)
        product_id: Product UUID
        tenant_key: Tenant isolation key

    Returns:
        Formatted string with numbered fetch calls, or empty string if none enabled.
    """
    # Category configs: maps field name to framing text and depth-awareness.
    # Handover 0823b: Framing text is now generic (no depth placeholders).
    # Depth is resolved at fetch_context runtime, not at protocol build time.
    category_configs = {
        "product_core": {
            "framing": "Product name, description, and core features.",
            "depth_aware": False,
        },
        "vision_documents": {
            "framing": "Vision document content.",
            "depth_aware": True,
            "default_depth": "medium",
        },
        "tech_stack": {
            "framing": "Programming languages, frameworks, and databases.",
            "depth_aware": False,
        },
        "architecture": {
            "framing": "System architecture patterns, API style, and design principles.",
            "depth_aware": False,
        },
        "testing": {
            "framing": "Quality standards, testing strategy, and frameworks.",
            "depth_aware": False,
        },
        "memory_360": {
            "framing": "Recent product project closeouts (cumulative knowledge).",
            "depth_aware": True,
            "default_depth": 3,
        },
        "git_history": {
            "framing": "Recent git commits.",
            "depth_aware": True,
            "default_depth": 25,
        },
        "agent_templates": {
            "framing": "Full agent templates with complete prompts for spawning.",
            "depth_aware": True,
            "skip_on_depth": "type_only",
            "default_depth": "type_only",
        },
    }

    inlined_fields = {"project_description"}
    calls = []

    for field, enabled in field_toggles.items():
        if not enabled:
            continue
        if field in inlined_fields:
            continue

        config = category_configs.get(field)
        if not config:
            continue

        # Handle agent_templates skip for type_only
        if config.get("depth_aware"):
            field_depth = depth_config.get(field, config.get("default_depth"))
            skip_value = config.get("skip_on_depth")
            if skip_value and field_depth == skip_value:
                continue

        # Build the call string (no depth_config -- resolved at runtime per 0823b)
        call_str = f'fetch_context(categories=["{field}"], product_id="{product_id}", tenant_key="{tenant_key}")'

        # Framing text is now static/generic (no depth placeholders per 0823b)
        framing = config["framing"]

        calls.append((call_str, framing))

    if not calls:
        return ""

    lines = []
    for i, (call_str, framing) in enumerate(calls, 1):
        lines.append(f"{i}. {call_str}")
        lines.append(f"   -> {framing}")
        lines.append("")

    return "\n".join(lines)


def _build_ch2_startup(
    orchestrator_id: str,
    project_id: str,
    field_toggles: dict[str, bool] | None = None,
    depth_config: dict[str, Any] | None = None,
    product_id: str | None = None,
    tenant_key: str | None = None,
) -> str:
    """
    Build CH2: STARTUP SEQUENCE section (Handover 0823: inline fetch calls).

    When field_toggles and depth_config are provided, Step 2 contains explicit
    numbered fetch_context() calls. The agent sees exactly what to call.

    Args:
        orchestrator_id: Job ID for parameter substitution
        project_id: Project UUID for parameter substitution
        field_toggles: Category toggle dict (True=enabled). If None, Step 2 is generic.
        depth_config: Depth settings per category. If None, uses defaults.
        product_id: Product UUID for fetch calls.
        tenant_key: Tenant key for fetch calls.
    """
    # Build the dynamic Step 2 content
    if field_toggles and product_id and tenant_key:
        fetch_calls = _build_ch2_fetch_calls(
            field_toggles=field_toggles,
            depth_config=depth_config or {},
            product_id=product_id,
            tenant_key=tenant_key,
        )
        step2_body = f"""── STEP 2: Fetch Context ───────────────────────────────────────────────────
Call: get_orchestrator_instructions(job_id='{orchestrator_id}')
Note: tenant_key auto-injected by server from API key session
Returns: project_description, mission, field_toggles, orchestrator_protocol

Read this protocol via orchestrator_protocol field.

Then call fetch_context() for EVERY category below.
You MUST call each one. These are configured by the user and are NOT optional.
Do NOT skip any.

{fetch_calls}"""
    else:
        step2_body = f"""── STEP 2: Fetch Context ───────────────────────────────────────────────────
Call: get_orchestrator_instructions(job_id='{orchestrator_id}')
Note: tenant_key auto-injected by server from API key session
Returns:
  - project_description: User requirements (INPUT for your analysis)
  - mission: Product context with priority fields applied
  - field_toggles: User's context toggle configuration
  - agent_templates: Available agent templates (name, role, description)

Read this protocol via orchestrator_protocol field."""

    return f"""════════════════════════════════════════════════════════════════════════════
                       CH2: STARTUP SEQUENCE
════════════════════════════════════════════════════════════════════════════

Follow these steps IN ORDER (Steps 0-7 for staging):

── STEP 0: Detect Environment ──────────────────────────────────────────────
Detect your shell environment before planning:
Call: `python -c "import os; print(os.environ.get('SHELL', os.environ.get('COMSPEC', 'unknown')))"`
This detects the **actual shell** (bash, zsh, powershell, cmd), not just the OS.
Adapt commands for agent missions to match the detected shell:
- If shell contains "bash" or "zsh" (includes Git Bash on Windows):
  Sleep: `sleep N` | Clear: `clear` | Paths: use `/`
- If shell contains "powershell" or "pwsh":
  Sleep: `Start-Sleep -Seconds N` | Clear: `cls` | Paths: use `\\` or `/`
- If shell contains "cmd":
  Sleep: `timeout /t N /nobreak >nul` | Clear: `cls` | Paths: use `\\`
- Default (unknown): use `sleep N` (works in most environments)

── STEP 1: Verify MCP ──────────────────────────────────────────────────────
Call: health_check()
Expected: {{"status": "healthy", "database": "connected"}}
If failed: Abort and notify user

── STEP 1b: Initialize Progress Tracking ───────────────────────────────────
Create a TodoWrite task list for your staging work, then sync with dashboard:

Call: report_progress(
          job_id='{orchestrator_id}',
          todo_items=[{{"content": "<step description>", "status": "pending"}}]
      )
Note: tenant_key auto-injected by server from API key session

Scope: Orchestration tasks ONLY — verifying, fetching context, discovering
       agents, planning, spawning. NEVER include implementation tasks.

Update TodoWrite AND call report_progress() as each staging step completes.

{step2_body}

⚠️  CONTEXT VARIABLES (CRITICAL):
Your fetch_context() responses contain AUTHORITATIVE values:
  - project_path: The project directory - USE THIS in missions
  - product_name: The product name
  - tenant_key: Your tenant isolation key
When writing missions or referencing directories, ALWAYS use values from context.
NEVER hardcode paths you observe in your terminal session.

── STEP 3: Discover Agents ─────────────────────────────────────────────────
Use the agent_templates field from the Step 2 get_orchestrator_instructions() response.
This already contains the list of available agent templates (name, role, description).
Use agent_name from agent_templates when spawning (see CH3 for rules)

── STEP 4: Create Mission ──────────────────────────────────────────────────
Analyze project_description + product context
Generate condensed execution plan:
  - Break down requirements into work items
  - Identify which agents handle which work
  - Define success criteria
  - Keep mission concise (<5K tokens target)

── STEP 5: Persist Mission ─────────────────────────────────────────────────
Call: update_project_mission(project_id='{project_id}',
                              mission=YOUR_CONDENSED_MISSION)
This stores your plan in Project.mission for UI display

── STEP 6: Spawn Agents ────────────────────────────────────────────────────
For each agent in your plan:
  spawn_agent_job(
      agent_name='exact-template-name',  # From Step 3
      agent_display_name='implementer',   # Display category
      mission='Agent-specific instructions',
      project_id='{project_id}'
  )
Note: tenant_key auto-injected by server from API key session

See CH3 for agent_name vs agent_display_name rules

── STEP 7: Persist Execution Plan ──────────────────────────────────────────
Call: update_agent_mission(job_id='{orchestrator_id}',
                            mission=YOUR_EXECUTION_STRATEGY)
Note: tenant_key auto-injected by server from API key session

Document in YOUR_EXECUTION_STRATEGY:
  - Agent execution order (sequential/parallel/hybrid)
  - Dependencies between agents
  - Coordination checkpoints
  - How you will monitor progress in implementation phase

Why: Fresh orchestrator in implementation phase retrieves this plan

── STEP 7 FINALE: Signal Complete ──────────────────────────────────────────
Call: send_message(
          to_agents=['all'],
          content='STAGING_COMPLETE: Mission created, N agents spawned',
          project_id='{project_id}',
          message_type='broadcast'
      )
Note: tenant_key auto-injected by server from API key session

This broadcast enables the "Implement" button in UI (REQUIRED)

The server will confirm staging completion in the response with a
`staging_directive` field containing status: "STAGING_SESSION_COMPLETE".
When you receive this directive, your session is DONE. Stop immediately.

⚠️  STAGING ENDS HERE - DO NOT call complete_job() or write_360_memory()
   Your session is done. Implementation happens in a new session.
"""


def _build_ch3_spawning_rules(tool: str = "claude-code") -> str:
    """Build CH3: AGENT SPAWNING RULES section (~200 tokens).

    Args:
        tool: Platform identifier — 'claude-code', 'codex', or 'gemini'.
              Defaults to 'claude-code' for backward compatibility.
    """
    cli_mode = tool in ("claude-code", "codex", "gemini")

    if tool == "codex":
        cli_mode_block = """── CODEX CLI MODE ───────────────────────────────────────────────────────────
spawn_agent tool syntax (IMPLEMENTATION PHASE ONLY - not during staging):
  spawn_agent(agent='gil-{agent_name}', instructions='...')

CRITICAL: ALL GiljoAI agents use the 'gil-' prefix in Codex CLI.
The server returns agent_name WITHOUT the prefix. You MUST prepend 'gil-'.

Example:
  spawn_agent_job(agent_name='tdd-implementor',
                  agent_display_name='implementer', ...)

  Later in implementation:
  spawn_agent(agent='gil-tdd-implementor', ...)  # note: gil- prefix!

Built-in Codex roles shadow unprefixed names — always use gil- prefix.
DO NOT invoke spawn_agent() during staging - this is planning reference only
"""
        multi_terminal_mode_block = ""
    elif tool == "gemini":
        cli_mode_block = """── GEMINI CLI MODE ───────────────────────────────────────────────────────────
Subagent invocation syntax (IMPLEMENTATION PHASE ONLY - not during staging):
  @{agent_name} followed by instructions

Or use the /agent command:
  /agent {agent_name}
  <instructions>

CRITICAL: agent_name is used as-is (no prefix required).

Example:
  spawn_agent_job(agent_name='tdd-implementor',
                  agent_display_name='implementer', ...)

  Later in implementation:
  @tdd-implementor <your instructions here>

DO NOT invoke subagents during staging - this is planning reference only
"""
        multi_terminal_mode_block = ""
    elif cli_mode:
        cli_mode_block = """── CLAUDE CODE CLI MODE ────────────────────────────────────────────────────
Task tool syntax (IMPLEMENTATION PHASE ONLY - not during staging):
  Task(subagent_type='{agent_name}', instructions='...')

CRITICAL: Task() uses agent_name value, NOT agent_display_name

Example:
  spawn_agent_job(agent_name='tdd-implementor',
                  agent_display_name='implementer', ...)

  Later in implementation:
  Task(subagent_type='tdd-implementor', ...)  # agent_name!

DO NOT invoke Task() during staging - this is planning reference only
"""
        multi_terminal_mode_block = ""
    else:
        cli_mode_block = ""
        multi_terminal_mode_block = """── MULTI-TERMINAL MODE (CCW) ───────────────────────────────────────────────
User manually launches agents via [Copy Prompt] button in Claude Code Web
Agents spawned via spawn_agent_job() during staging phase
Each spawned agent gets a thin prompt (~10 lines)
Agent calls get_agent_mission() to fetch full instructions
Coordination happens via MCP messaging tools (send_message, receive_messages)
MESSAGING: Always use agent_id UUIDs in to_agents (from spawn_agent_job response)
Orchestrator has NO active role after STAGING_COMPLETE broadcast
"""

    return f"""════════════════════════════════════════════════════════════════════════════
                    CH3: AGENT SPAWNING RULES
════════════════════════════════════════════════════════════════════════════

PARAMETER REQUIREMENTS:

── agent_name (CRITICAL) ───────────────────────────────────────────────────
MUST exactly match template name from agent_templates (returned by get_orchestrator_instructions)
This is the SINGLE SOURCE OF TRUTH for agent identity
Example: 'tdd-implementor' (not 'TDD Implementor' or 'implementer')

File mapping: agent_name → .claude/agents/{{agent_name}}.md

Common mistakes:
  ✗ Using agent_display_name value for agent_name parameter
  ✗ Inventing names not in agent_templates
  ✗ Case mismatch ('TDD-Implementor' vs 'tdd-implementor')

Claude Code CLI Mode Note:
  - Task(subagent_type=X) where X = agent_name (NOT display_name)
  - agent_name binds DB record, Task tool, and template filename
  - Example: spawn with agent_name='tdd-implementor', Task uses 'tdd-implementor'

── agent_display_name ──────────────────────────────────────────────────────
Display category for UI (user-facing label)
Options: implementer, tester, analyzer, documenter, reviewer
This is for UI display only - does NOT affect template selection

── mission ─────────────────────────────────────────────────────────────────
Agent-specific instructions (what THIS agent should do)
Should be focused and actionable
Target: 200-500 tokens per agent mission

SPAWNING LIMITS:

- Max recommended: 2-5 agents for typical projects
- Max agent_display_names: 8 total
- Max instances per type: Unlimited (can spawn multiple 'implementer' agents)
- Budget awareness: Each agent costs ~1,253 tokens for thin prompt

EXECUTION MODE AWARENESS:

{cli_mode_block}{multi_terminal_mode_block}

VALIDATION BEFORE SPAWNING:

1. Verify agent_name exists in agent_templates from get_orchestrator_instructions()
2. Check you haven't exceeded recommended limits
3. Ensure mission is specific to this agent's role
4. Confirm project_id and tenant_key are correct
"""


def _build_ch4_error_handling() -> str:
    """Build CH4: ERROR HANDLING section (~400 tokens)."""
    return """════════════════════════════════════════════════════════════════════════════
                       CH4: ERROR HANDLING
════════════════════════════════════════════════════════════════════════════

COMMON ERRORS AND RESPONSES:

── MCP Connection Lost ─────────────────────────────────────────────────────
Symptom: Tools not responding, timeouts
Action: Abort staging immediately
Notify: Call report_error(job_id, "MCP connection lost", tenant_key)
Do NOT: Attempt to continue spawning agents

── Invalid Agent Name ──────────────────────────────────────────────────────
Symptom: spawn_agent_job() returns error "agent not found"
Action: Check agent_name against agent_templates from get_orchestrator_instructions()
Common cause: Typo, case mismatch, using display_name instead of name
Fix: Use exact agent_name from discovery response

── Spawn Failure ───────────────────────────────────────────────────────────
Symptom: spawn_agent_job() fails for any reason
Action: Log via report_error(), do NOT continue spawning
Why: Partial spawns create incomplete agent teams
Recovery: User must fix issue and restart staging

── Mission Too Large ───────────────────────────────────────────────────────
Symptom: Generated mission exceeds 10K tokens
Action: Condense mission further, focus on essentials
Technique: Reference vision docs instead of embedding content
Target: <5K tokens for mission plan

── Agent Templates Empty ───────────────────────────────────────────────────
Symptom: agent_templates list from get_orchestrator_instructions() is empty
Cause: No active agent templates in database
Action: Report to user - template configuration required
Fix: User must activate templates in My Settings → Agent Templates

── STATUS TRANSITIONS ──────────────────────────────────────────────────────
waiting ─[get_agent_mission()]─→ working (auto-transition on first fetch)
working ─[report_progress()]─→ working (updates progress/todos)
working ─[complete_job()]─→ complete
working ─[report_error()]─→ blocked
blocked ─[complete_job()]─→ complete (orchestrator force-completes blocked agent)

Note: All report_error() calls set status to "blocked". Use "BLOCKED: <reason>"
message format when asking for clarification vs actual errors.

GENERAL ERROR PROTOCOL:

1. Log error with context (agent_id, job_id, tenant_key)
2. Call report_error() to persist error state
3. Send broadcast message to notify user
4. Do NOT attempt to continue workflow after critical errors
5. Wait for user intervention

ERROR SEVERITY LEVELS:

- CRITICAL: MCP connection lost, database errors → Abort immediately
- HIGH: Spawn failures, invalid agent names → Stop spawning, report
- MEDIUM: Mission size warnings → Continue but log warning
- LOW: Context optimization suggestions → Continue normally
"""


def _build_ch5_reference(project_id: str, orchestrator_id: str) -> str:
    """Build CH5: REFERENCE section for implementation phase (~380 tokens)."""
    return f"""════════════════════════════════════════════════════════════════════════════
                CH5: REFERENCE (Implementation Phase Only)
════════════════════════════════════════════════════════════════════════════

⚠️  NOTE: This chapter is for IMPLEMENTATION PHASE reference only.
   If you are in STAGING PHASE, you do NOT need this information.
   This content is provided so you can plan your execution strategy.

────────────────────────────────────────────────────────────────────────────

IMPLEMENTATION PHASE MONITORING:

When you (or a fresh orchestrator instance) enters implementation phase:

1. Retrieve execution plan via get_agent_mission(job_id, tenant_key)
2. Follow coordination strategy you defined in Step 7
3. Coordinate handoffs between dependent agents
4. Ask user if they want you to auto-monitor agents (sleep and periodically check progress and message queues). Warn user this can drastically increase token consumption.

COORDINATION PATTERNS:

Sequential Pattern:
  Spawn agent A → Wait for completion →
  Send handoff message (using agent_id UUID) → Spawn agent B → Repeat

Parallel Pattern:
  Spawn all agents → Check progress when user requests or when auto-monitoring →
  Coordinate as agents finish → Track completion states

Hybrid Pattern:
  Spawn parallel batch 1 → Wait for batch 1 complete →
  Send handoff messages (using agent_id UUIDs) → Spawn batch 2 → Repeat

MESSAGING RULE: UUID-ONLY ADDRESSING
- ALWAYS use agent_id UUIDs in send_message(to_agents=[...])
- Each spawn_agent_job() returns agent_id - save these for messaging
- Use to_agents=['all'] for broadcast only
- NEVER use display names (e.g., "implementer") in to_agents

MANDATORY: Before calling complete_job():
- Ensure all agent TODO items are completed
- Call receive_messages() and process all pending messages
System rejects completion attempts with unread messages or incomplete TODOs.

────────────────────────────────────────────────────────────────────────────

COMPLETION PROTOCOL (After ALL agents finish their work):

── STEP 1: Write 360 Memory ────────────────────────────────────────────────
Call: write_360_memory(
          project_id='{project_id}',
          summary='2-3 paragraph mission accomplishment overview',
          key_outcomes=['Achievement 1', 'Achievement 2', ...],
          decisions_made=['Decision 1 + rationale', ...],
          entry_type='project_completion',
          author_job_id='{orchestrator_id}'
      )
Note: tenant_key auto-injected by server from API key session

CRITICAL: Auto-generate content from your knowledge.
          Never ask user to fill placeholders.

Purpose: Creates sequential history entry in Product.product_memory
Visible: User sees in UI Product Memory timeline

── STEP 2: Mark Complete ───────────────────────────────────────────────────
Call: complete_job(
          job_id='{orchestrator_id}',
          result={{"summary": "...", "status": "completed"}}
      )
Note: tenant_key auto-injected by server from API key session

This transitions orchestrator job from 'active' to 'completed'

── STEP 3: User Review ─────────────────────────────────────────────────────
User reviews 360 memory entry in UI
User chooses:
  - "Continue Working" → Spawns new orchestrator for next iteration
  - "Close Out Project" → Marks project as completed

Orchestrator waits for user decision (no further action)

────────────────────────────────────────────────────────────────────────────

END OF IMPLEMENTATION PHASE REFERENCE
"""


def _build_orchestrator_protocol(
    cli_mode: bool,
    project_id: str,
    orchestrator_id: str,
    tenant_key: str,
    include_implementation_reference: bool = True,
    field_toggles: dict[str, bool] | None = None,
    depth_config: dict[str, Any] | None = None,
    product_id: str | None = None,
    tool: str = "claude-code",
) -> dict:
    """
    Build chapter-based orchestrator protocol.

    Creates 5 navigable chapters with clear visual boundaries.
    Solves the "rotation problem" where content gets buried.

    Args:
        cli_mode: True if execution_mode is any CLI subagent mode
        project_id: Project UUID for parameter substitution
        orchestrator_id: Job ID for parameter substitution
        tenant_key: Tenant key for parameter substitution
        include_implementation_reference: Include CH5 (default True)
        field_toggles: Category toggles for inline fetch injection (Handover 0823)
        depth_config: Depth settings per category (Handover 0823)
        product_id: Product UUID for fetch calls (Handover 0823)
        tool: Platform identifier for platform-specific spawning rules (Handover 0838)

    Returns:
        Dict with chapter keys and navigation_hint
    """
    ch1 = _build_ch1_mission()
    ch2 = _build_ch2_startup(
        orchestrator_id,
        project_id,
        field_toggles=field_toggles,
        depth_config=depth_config,
        product_id=product_id,
        tenant_key=tenant_key,
    )
    ch3 = _build_ch3_spawning_rules(tool if cli_mode else "multi_terminal")
    ch4 = _build_ch4_error_handling()
    ch5 = _build_ch5_reference(project_id, orchestrator_id) if include_implementation_reference else ""

    return {
        "ch1_your_mission": ch1,
        "ch2_startup_sequence": ch2,
        "ch3_agent_spawning_rules": ch3,
        "ch4_error_handling": ch4,
        "ch5_reference": ch5,
        "navigation_hint": "Reference chapters by name (e.g., 'see CH4 for error handling')",
    }
