"""
Orchestration MCP Tools (HTTP-only)

Production architecture:
- HTTP MCP endpoint (/mcp) → ToolAccessor → OrchestrationService (service layer)
- FastMCP tool registrations below are for unit testing only

Helper functions (get_project_by_alias, etc.) are used by both paths.
See: api/endpoints/mcp_http.py for HTTP routing.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import yaml
from sqlalchemy import and_, select

from src.giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as _DEFAULT_DEPTH_CONFIG
from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY as _DEFAULT_FIELD_PRIORITY
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.logging import ErrorCode, get_logger
from src.giljo_mcp.models import Product, Project


# Handover 0450: Removed dead import of ProjectOrchestrator


logger = get_logger(__name__)

# Extract inner structure for backward compatibility with existing code
# defaults.py uses versioned structure: {"version": "2.1", "priorities": {...}}
# This code expects flat structure: {"field": {"toggle": True, "priority": X}}
DEFAULT_FIELD_PRIORITIES = _DEFAULT_FIELD_PRIORITY["priorities"]
DEFAULT_DEPTH_CONFIG = _DEFAULT_DEPTH_CONFIG["depths"]


# ============================================================================
# STANDALONE HELPER FUNCTIONS (For Testing and Tenant Isolation)
# ============================================================================


async def get_project_by_alias(alias: str, tenant_key: str, session) -> dict[str, Any]:
    """
    Fetch project details using its 6-character alias with tenant isolation.

    This is a testable helper function that enforces tenant boundaries.
    The MCP tool wrapper calls this function.

    Args:
        alias: 6-character project alias (case insensitive)
        tenant_key: Tenant isolation key
        session: Database session

    Returns:
        Dictionary containing project details or error
    """
    try:
        if not alias or len(alias) != 6:
            return {"error": "Alias must be exactly 6 characters"}

        if not tenant_key or not tenant_key.strip():
            return {"error": "tenant_key is required"}

        alias_upper = alias.upper()

        # TENANT ISOLATION: Filter by both alias pattern AND tenant_key
        result = await session.execute(
            select(Project).where(and_(Project.name.ilike(f"%{alias_upper}%"), Project.tenant_key == tenant_key))
        )
        project = result.scalar_one_or_none()

        if not project:
            return {"error": f"Project with alias '{alias_upper}' not found"}

        # Get product details if available with TENANT VALIDATION
        product_name = None
        product_tenant = None
        if project.product_id:
            # TENANT ISOLATION: Filter product by tenant_key
            product_result = await session.execute(
                select(Product).where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
            )
            product = product_result.scalar_one_or_none()
            if product:
                product_name = product.name
                product_tenant = product.tenant_key

        return {
            "success": True,
            "project": {
                "id": str(project.id),
                "name": project.name,
                "alias": alias_upper,
                "tenant_key": project.tenant_key,
                "mission": project.mission,
                "status": project.status,
                "created_at": project.created_at.isoformat() if project.created_at else None,
            },
            "product": (
                {
                    "id": str(project.product_id) if project.product_id else None,
                    "name": product_name,
                    "tenant_key": product_tenant,
                }
                if project.product_id and product_name
                else None
            ),
        }

    except Exception as e:
        logger.error(
            "project_fetch_by_alias_failed",
            error_code=ErrorCode.MCP_ORCHESTRATOR_ERROR.value,
            alias=alias,
            error_message=str(e),
            exc_info=True,
        )
        return {"error": f"Failed to fetch project: {e!s}"}


# Handover 0281 Phase 1: Default configurations imported from config/defaults.py
# (DEFAULT_FIELD_PRIORITIES and DEFAULT_DEPTH_CONFIG are now unified across the codebase)


def _normalize_field_priorities(field_priorities: Dict[str, Any]) -> Dict[str, int]:
    """
    Normalize field_priorities from nested format to integer format.

    Handover 0357: DEFAULT_FIELD_PRIORITIES uses {"field": {"toggle": True, "priority": X}} format
    but mission_planner expects {"field": X} (just integers).

    Args:
        field_priorities: Dict with either nested or integer priority values

    Returns:
        Dict with integer priority values (1-4)
    """
    normalized = {}
    for field_key, value in field_priorities.items():
        if isinstance(value, dict) and "priority" in value:
            # Extract priority from nested format, respecting toggle
            if value.get("toggle", True):
                normalized[field_key] = value["priority"]
            else:
                normalized[field_key] = 4  # EXCLUDED if toggle is off
        elif isinstance(value, int):
            # Already in integer format
            normalized[field_key] = value
        else:
            # Unknown format, default to IMPORTANT
            normalized[field_key] = 2
    return normalized


async def _get_user_config(
    user_id: str,
    tenant_key: str,
    session: Any,  # AsyncSession type hint would create circular import
) -> Dict[str, Any]:
    """
    Fetch user's field_priority_config and depth_config from database.

    Args:
        user_id: User UUID
        tenant_key: Tenant isolation key
        session: SQLAlchemy AsyncSession

    Returns:
        dict with 'field_priorities' and 'depth_config' keys

    Behavior:
        - Returns user's custom config if exists
        - Falls back to DEFAULT_FIELD_PRIORITIES and DEFAULT_DEPTH_CONFIG if None
        - Ensures multi-tenant isolation (user must belong to tenant_key)
        - Normalizes depth_config keys from UI format to internal format
    """
    from src.giljo_mcp.models.auth import User

    try:
        # Query user with tenant isolation
        result = await session.execute(
            select(User).where(and_(User.id == user_id, User.tenant_key == tenant_key, User.is_active == True))
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "user_not_found_using_defaults",
                user_id=user_id,
                tenant_key=tenant_key,
            )
            # Handover 0357: Normalize default priorities to integer format
            normalized_defaults = _normalize_field_priorities(DEFAULT_FIELD_PRIORITIES.copy())
            return {"field_priorities": normalized_defaults, "depth_config": DEFAULT_DEPTH_CONFIG.copy()}

        # Get user's custom configs or fall back to defaults
        # Handover 0346: Handle nested v2.0 format {"version": "2.0", "priorities": {...}}
        raw_field_priorities = user.field_priority_config
        if raw_field_priorities is not None:
            # Extract priorities from v2.0 nested structure if present
            if isinstance(raw_field_priorities, dict) and "priorities" in raw_field_priorities:
                field_priorities = raw_field_priorities["priorities"]
            else:
                field_priorities = raw_field_priorities
        else:
            field_priorities = DEFAULT_FIELD_PRIORITIES.copy()

        # Handover 0357: Normalize field_priorities to integer format for mission_planner
        field_priorities = _normalize_field_priorities(field_priorities)

        # Get depth config and normalize keys from UI format to internal format
        raw_depth_config = user.depth_config
        if raw_depth_config is not None:
            # Key mapping: UI/database keys → internal code keys
            key_mapping = {
                "memory_last_n_projects": "memory_360",
                "git_commits": "git_history",
                # These keys match, but include for completeness
                "agent_templates": "agent_templates",
                "vision_documents": "vision_documents",
            }

            depth_config = {}
            for db_key, value in raw_depth_config.items():
                # Map to internal key if mapping exists, otherwise keep original
                internal_key = key_mapping.get(db_key, db_key)
                depth_config[internal_key] = value

            # Handover 0352: Normalize deprecated 'optional' value to 'light'
            if depth_config.get("vision_documents") == "optional":
                depth_config["vision_documents"] = "light"
                logger.debug(
                    "[USER_CONFIG] Normalized vision_documents 'optional' → 'light'", extra={"user_id": user_id}
                )

            logger.debug(
                "[USER_CONFIG] Normalized depth_config keys",
                extra={"raw_keys": list(raw_depth_config.keys()), "normalized_keys": list(depth_config.keys())},
            )
        else:
            depth_config = DEFAULT_DEPTH_CONFIG.copy()

        logger.info(
            "[USER_CONFIG] Fetched user configuration",
            extra={
                "user_id": user_id,
                "tenant_key": tenant_key,
                "has_custom_field_priorities": user.field_priority_config is not None,
                "has_custom_depth_config": user.depth_config is not None,
                "depth_config": depth_config,
            },
        )

        return {"field_priorities": field_priorities, "depth_config": depth_config}

    except Exception as e:
        logger.error(
            "user_config_fetch_failed",
            error_code=ErrorCode.MCP_CONTEXT_FETCH_FAILED.value,
            user_id=user_id,
            tenant_key=tenant_key,
            error_message=str(e),
            exc_info=True,
        )
        # Fall back to defaults on error (Handover 0357: normalize to integer format)
        normalized_defaults = _normalize_field_priorities(DEFAULT_FIELD_PRIORITIES.copy())
        return {"field_priorities": normalized_defaults, "depth_config": DEFAULT_DEPTH_CONFIG.copy()}


def _infer_execution_mode_from_tool(tool_type: str | None) -> str:
    """
    Infer execution_mode from tool_type when not explicitly specified.

    Args:
        tool_type: Tool type from orchestrator job (claude-code, codex, gemini, universal, None)

    Returns:
        Inferred execution mode ('claude-code' or 'legacy')

    Examples:
        >>> _infer_execution_mode_from_tool('claude-code')
        'claude-code'
        >>> _infer_execution_mode_from_tool('universal')
        'legacy'
        >>> _infer_execution_mode_from_tool(None)
        'legacy'
    """
    if tool_type == "claude-code":
        return "claude-code"
    # Default to legacy for all other cases (codex, gemini, universal, None)
    return "legacy"


def _build_mode_instructions(execution_mode: str, agent_templates: list[dict]) -> str:
    """
    Build mode-specific instructions for orchestrator.

    Args:
        execution_mode: Execution mode ('claude-code' or 'legacy')
        agent_templates: List of agent template dictionaries

    Returns:
        Mode-specific instruction text

    Examples:
        Claude Code mode returns instructions for spawning sub-agents via Task tool.
        Legacy mode returns instructions for manual terminal launches.
    """
    if execution_mode == "claude-code":
        # Claude Code mode - orchestrator spawns sub-agents
        instructions = """**CLAUDE CODE MODE - Sub-Agent Spawning**

You can spawn specialist agents as sub-agents using the Task tool.

**Workflow**:
1. Review agent templates below for available specialists
2. Use spawn_agent_job() MCP tool to create agent job in database
3. Spawn sub-agent via Task tool with agent's launch_instructions
4. Monitor progress via get_workflow_status()

**Example**:
```python
# Step 1: Create agent job via MCP
result = await spawn_agent_job(
    agent_display_name="implementer",
    agent_name="Backend Implementer",
    mission="Implement user authentication",
    project_id=project_id,
    tenant_key=tenant_key
)

# Step 2: Spawn sub-agent using Task tool with launch_instructions
# Use the launch_instructions from agent template below
```

**Agent Launch Instructions**:
Each agent template below includes launch_instructions showing how to start the agent.
"""
        return instructions
    # Legacy mode - manual terminal launches
    instructions = """**LEGACY MODE - Manual Agent Launches**

Specialist agents must be launched manually in separate terminals.

**Workflow**:
1. Use spawn_agent_job() MCP tool to create agent jobs
2. Copy each agent's launch_instructions from templates below
3. User manually pastes commands into separate terminal windows
4. Monitor progress via get_workflow_status()

**Agent Launch Instructions**:
Each agent template below includes launch_instructions for manual copying.
"""
    return instructions


def _format_agent_templates(templates: list, execution_mode: str) -> list[dict]:
    """
    Format agent templates with launch_instructions for the given execution mode.

    Args:
        templates: SQLAlchemy AgentTemplate model instances
        execution_mode: Execution mode ('claude-code' or 'legacy')

    Returns:
        List of formatted agent template dictionaries with launch_instructions

    Examples:
        >>> templates = [AgentTemplate(name='implementer', ...)]
        >>> formatted = _format_agent_templates(templates, 'claude-code')
        >>> formatted[0]['launch_instructions']
        'cd $PROJECT_PATH && claude-code --agent implementer'
    """
    formatted_templates = []

    for template in templates:
        template_dict = {
            "name": template.name,
            "role": template.role,
            "description": template.description[:200] if template.description else "",
        }

        # Extract launch_instructions from meta_data
        if template.meta_data and "launch_instructions" in template.meta_data:
            template_dict["launch_instructions"] = template.meta_data["launch_instructions"]
        else:
            # Provide default launch instruction if not specified
            template_dict["launch_instructions"] = f"cd $PROJECT_PATH && {execution_mode} --agent {template.name}"

        formatted_templates.append(template_dict)

    return formatted_templates


# ========================================================================
# Depth Config Helper Functions (Handover 0281 Phase 3) - REMOVED
# Individual fetch_* functions replaced with monolithic context architecture
# All context fetched via get_orchestrator_instructions() MCP tool
# ========================================================================


# ========================================================================
# Standalone Functions for Testing
# These are test-friendly wrappers that can be imported directly
# ========================================================================


async def health_check() -> dict[str, Any]:
    """
    MCP server health check (standalone for testing).

    Returns:
        Health status dict with server info
    """
    from datetime import datetime, timezone

    return {
        "status": "healthy",
        "server": "giljo-mcp",
        "version": "3.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected",
        "message": "GiljoAI MCP server is operational",
    }


# ============================================================================
# ORCHESTRATOR RESPONSE HELPER FUNCTIONS (Handover 0347c)
# ============================================================================


def _get_post_staging_behavior(cli_mode: bool) -> dict:
    """
    Generate post_staging_behavior field (mode-aware).

    Args:
        cli_mode: True if execution_mode is "claude_code_cli", False for "multi_terminal"

    Returns:
        Dict with mode-specific behavior guidance

    Handover 0709b: Mention staging_directive in broadcast response
    """
    return {
        "cli_mode": "Staging orchestrator SESSION ENDS after STAGING_COMPLETE broadcast. Server returns staging_directive with STOP action. DO NOT call complete_job(). Implementation happens in separate execution.",
        "multi_terminal_mode": "Staging orchestrator SESSION ENDS after STAGING_COMPLETE broadcast. Server returns staging_directive with STOP action. DO NOT call complete_job(). User manually launches agents via [Copy Prompt] buttons.",
    }


def _get_required_final_action() -> dict:
    """
    Generate required_final_action field.

    Returns:
        Dict with required broadcast action for enabling Implement button

    Handover 0709b: Broadcast response enriched with staging_directive
    """
    return {
        "action": "send_message",
        "params": {
            "to_agents": ["all"],
            "message_type": "broadcast",
            "content_template": "STAGING_COMPLETE: Mission created, {N} agents spawned",
        },
        "why": "Enables Implement button in UI - REQUIRED",
        "response_note": "Server returns staging_directive field with STOP action when this broadcast succeeds",
    }


def _get_multi_terminal_rules() -> dict:
    """
    Generate multi_terminal_mode_rules field.

    Returns:
        Dict with multi-terminal execution rules
    """
    return {
        "agent_launching": "User clicks [Copy Prompt] button in Implementation tab",
        "coordination": "Agents communicate via MCP messaging tools",
        "orchestrator_role": "Staging only - no active coordination after broadcast",
    }


def _get_error_handling() -> dict:
    """
    Generate error_handling field.

    Returns:
        Dict with error handling guidance
    """
    return {
        "invalid_agent_name": "Verify against allowed_agent_names list before calling spawn_agent_job",
        "spawn_failure": "Log via report_error(), do not proceed with remaining agents",
        "mcp_connection_lost": "Abort staging, notify user",
    }


def _get_spawning_limits() -> dict:
    """
    Generate agent_spawning_limits field.

    Returns:
        Dict with agent spawning limits
    """
    return {
        "max_agent_display_names": 8,
        "max_instances_per_type": "unlimited",
        "recommended_total": "2-5 agents for typical projects",
    }


def _get_context_management(context_budget: int) -> dict:
    """
    Generate context_management field.

    Args:
        context_budget: Context budget in tokens (default 150000)

    Returns:
        Dict with context management guidance
    """
    return {
        "context_budget": context_budget,
        "warning_threshold": 0.8,
        "action_at_threshold": "Consider triggering succession via create_successor_orchestrator",
    }


def _build_orchestrator_protocol(
    cli_mode: bool,
    context_budget: int,
    project_id: str,
    orchestrator_id: str,
    tenant_key: str,
    include_implementation_reference: bool = True,
) -> dict:
    """
    Build chapter-based orchestrator protocol.

    Creates 5 navigable chapters with clear visual boundaries.
    Solves the "rotation problem" where content gets buried.

    Args:
        cli_mode: True if execution_mode is "claude_code_cli"
        context_budget: Token budget (default 150000)
        project_id: Project UUID for parameter substitution
        orchestrator_id: Job ID for parameter substitution
        tenant_key: Tenant key for parameter substitution
        include_implementation_reference: Include CH5 (default True)

    Returns:
        Dict with chapter keys and navigation_hint
    """
    # CH1: YOUR MISSION (~180 tokens)
    ch1 = """════════════════════════════════════════════════════════════════════════════
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
- Project.description = USER INPUT (what needs to be done)
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

    # CH2: STARTUP SEQUENCE (~350 tokens - reduced via deduplication)
    ch2 = f"""════════════════════════════════════════════════════════════════════════════
                       CH2: STARTUP SEQUENCE
════════════════════════════════════════════════════════════════════════════

Follow these steps IN ORDER (Steps 1-7 for staging):


── STEP 0: Detect Environment ──────────────────────────────────────────────
Before planning, detect your development environment:
Call: python -c "import platform; print(platform.system())"
Store result (Windows/Linux/Darwin) - use platform-appropriate commands in agent missions

Platform command reference:
- Sleep: Windows 'timeout /t N /nobreak' | Unix 'sleep N'
- Clear: Windows 'cls' | Unix 'clear'
- Path separator: Windows '\' | Unix '/'

── STEP 1: Verify MCP ──────────────────────────────────────────────────────
Call: health_check()
Expected: {{"status": "healthy", "database": "connected"}}
If failed: Abort and notify user

── STEP 2: Fetch Context ───────────────────────────────────────────────────
Call: get_orchestrator_instructions(job_id='{orchestrator_id}')
Note: tenant_key auto-injected by server from API key session
Returns:
  - project_description: User requirements (INPUT for your analysis)
  - mission: Product context with priority fields applied
  - field_priorities: User's context configuration
  - agent_discovery_tool: Reference to get_available_agents()

Read this protocol via orchestrator_protocol field.

⚠️  CONTEXT VARIABLES (CRITICAL):
Your fetch_context() responses contain AUTHORITATIVE values:
  - project_path: The project directory - USE THIS in missions
  - product_name: The product name
  - tenant_key: Your tenant isolation key
When writing missions or referencing directories, ALWAYS use values from context.
NEVER hardcode paths you observe in your terminal session.

── STEP 3: Discover Agents ─────────────────────────────────────────────────
Call: get_available_agents(active_only=true)
Note: tenant_key auto-injected by server from API key session
Returns: List of available agent templates
Use agent_name from response when spawning (see CH3 for rules)

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

⚠️  STATUS NOTE: Do NOT call acknowledge_job() during staging.
   Your job remains in 'waiting' status - this enables the Implement
   button in UI. acknowledge_job() is for implementation phase only.
"""

    # CH3: AGENT SPAWNING RULES (~200 tokens - reduced via deduplication)
    # Build mode-specific blocks
    if cli_mode:
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
Coordination happens via MCP messaging tools (send_message, receive)
Orchestrator has NO active role after STAGING_COMPLETE broadcast
"""

    ch3 = f"""════════════════════════════════════════════════════════════════════════════
                    CH3: AGENT SPAWNING RULES
════════════════════════════════════════════════════════════════════════════

PARAMETER REQUIREMENTS:

── agent_name (CRITICAL) ───────────────────────────────────────────────────
MUST exactly match template name from get_available_agents() response
This is the SINGLE SOURCE OF TRUTH for agent identity
Example: 'tdd-implementor' (not 'TDD Implementor' or 'implementer')

File mapping: agent_name → .claude/agents/{{agent_name}}.md

Common mistakes:
  ✗ Using agent_display_name value for agent_name parameter
  ✗ Inventing names not in get_available_agents() response
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

1. Verify agent_name exists in get_available_agents() response
2. Check you haven't exceeded recommended limits
3. Ensure mission is specific to this agent's role
4. Confirm project_id and tenant_key are correct
"""

    # CH4: ERROR HANDLING (~400 tokens with status machine)
    ch4 = """════════════════════════════════════════════════════════════════════════════
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
Action: Check agent_name against get_available_agents() response
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

── Context Budget Warning ──────────────────────────────────────────────────
Symptom: Approaching 80% of context_budget (120K/150K tokens)
Action: Review field_priorities, reduce depth_config if needed
Tools: fetch_context() for on-demand loading instead of upfront
Note: Only applies during implementation phase (see CH5)

── Agent Discovery Empty ───────────────────────────────────────────────────
Symptom: get_available_agents() returns empty list
Cause: No active agent templates in database
Action: Report to user - template configuration required
Fix: User must activate templates in My Settings → Agent Templates

── STATUS TRANSITIONS ──────────────────────────────────────────────────────
waiting ─[acknowledge_job()]─→ working
working ─[report_progress()]─→ working (updates progress/todos)
working ─[complete_job()]─→ complete
working ─[report_error()]─→ blocked
blocked ─[acknowledge_job()]─→ working (resume from blocked)

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

    # CH5: REFERENCE (~380 tokens or minimal if not included)
    if include_implementation_reference:
        ch5 = f"""════════════════════════════════════════════════════════════════════════════
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
3. Monitor agent progress via receive_messages() every 2-3 minutes
4. Coordinate handoffs between dependent agents

COORDINATION PATTERNS:

Sequential Pattern:
  Spawn agent A → Poll receive_messages() → Wait for completion →
  Send handoff message → Spawn agent B → Repeat

Parallel Pattern:
  Spawn all agents → Poll receive_messages() every 2-3 min →
  Coordinate as agents finish → Track completion states

Hybrid Pattern:
  Spawn parallel batch 1 → Monitor → Wait for batch 1 complete →
  Send handoff messages → Spawn batch 2 → Repeat

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

CONTEXT MANAGEMENT (Implementation Phase):

Budget: {context_budget} tokens (default 150,000)
Warning Threshold: 80% ({int(context_budget * 0.8)} tokens)
Simple Handover: Available via /gil_handover command or UI "Hand Over" button

When context is high:
  - User can manually trigger handover
  - Session context written to 360 Memory
  - Context counter reset to 0
  - Continuation prompt returned for same session

────────────────────────────────────────────────────────────────────────────

END OF IMPLEMENTATION PHASE REFERENCE
"""
    else:
        ch5 = ""

    return {
        "ch1_your_mission": ch1,
        "ch2_startup_sequence": ch2,
        "ch3_agent_spawning_rules": ch3,
        "ch4_error_handling": ch4,
        "ch5_reference": ch5,
        "navigation_hint": "Reference chapters by name (e.g., 'see CH4 for error handling')",
    }


async def get_orchestrator_instructions(
    agent_id: str,
    tenant_key: str,
    user_id: Optional[str] = None,  # Handover 0281 Phase 1: User-specific config
    db_manager: "DatabaseManager" = None,
) -> dict[str, Any]:
    """
    Fetch orchestrator instructions (standalone for testing - Phase C).

    This is a test-friendly wrapper around the MCP tool.
    For production use, the HTTP MCP endpoint calls ToolAccessor.get_orchestrator_instructions().

    Updated in Handover 0366c to use agent_id parameter.
    Handover 0422: Updated comment - stdio MCP removed, HTTP MCP is authoritative.

    Args:
        agent_id: Agent execution UUID (WHO is executing)
        tenant_key: Tenant isolation key
        user_id: Optional user UUID for fetching user-specific field_priority_config and depth_config (Handover 0281)
        db_manager: Optional DatabaseManager instance (for testing)

    Returns:
        Orchestrator instructions dict with both agent_id and job_id
    """
    from src.giljo_mcp.config_manager import get_config
    from src.giljo_mcp.database import DatabaseManager

    if db_manager is None:
        # Get database URL from config for test environments
        config = get_config()
        db_url = config.database.database_url
        db_manager = DatabaseManager(database_url=db_url, is_async=True)
    async with db_manager.get_session_async() as session:
        from sqlalchemy import and_, select
        from sqlalchemy.orm import joinedload

        from src.giljo_mcp.mission_planner import MissionPlanner
        from src.giljo_mcp.models import AgentTemplate, Product, Project
        from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

        try:
            # Validate inputs
            if not agent_id or not agent_id.strip():
                return {"error": "VALIDATION_ERROR", "message": "Agent ID is required"}

            if not tenant_key or not tenant_key.strip():
                return {"error": "VALIDATION_ERROR", "message": "Tenant key is required"}

            # Phase C: Resolve agent_id → job_id via AgentExecution
            result = await session.execute(
                select(AgentExecution).where(
                    and_(
                        AgentExecution.agent_id == agent_id,
                        AgentExecution.tenant_key == tenant_key,
                    )
                )
            )
            agent_execution = result.scalar_one_or_none()

            if not agent_execution:
                return {
                    "error": "NOT_FOUND",
                    "message": f"Agent execution {agent_id} not found for tenant",
                    "troubleshooting": [
                        "Verify agent_id is correct",
                        "Check tenant_key matches project",
                        "Ensure agent execution was created successfully",
                    ],
                    "severity": "ERROR",
                }

            # Phase C: Get job_id from execution
            job_id = agent_execution.job_id

            # Phase C: Get AgentJob with tenant isolation
            result = await session.execute(
                select(AgentJob).where(
                    and_(
                        AgentJob.job_id == job_id,
                        AgentJob.tenant_key == tenant_key,
                    )
                )
            )
            agent_job = result.scalar_one_or_none()

            if not agent_job:
                return {
                    "error": "NOT_FOUND",
                    "message": f"Agent job {job_id} not found",
                    "troubleshooting": [
                        "Database integrity issue - execution exists but job missing",
                        "Contact support",
                    ],
                    "severity": "ERROR",
                }

            # Handover 0233: Track mission_acknowledged_at timestamp (idempotent)
            # Set timestamp on FIRST read only (doesn't overwrite existing)
            if agent_execution.mission_acknowledged_at is None:
                agent_execution.mission_acknowledged_at = datetime.now(timezone.utc)
                await session.commit()
                logger.info(
                    f"[MISSION_TRACKING] Set mission_acknowledged_at for agent {agent_id}",
                    extra={"agent_id": agent_id, "job_id": job_id, "tenant_key": tenant_key},
                )

                # Handover 0233 Phase 5: Emit WebSocket event for mission_acknowledged
                try:
                    # Import websocket manager
                    from api.app import state

                    ws_manager = getattr(state, "websocket_manager", None)

                    if ws_manager:
                        await ws_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="job:mission_acknowledged",
                            data={
                                "agent_id": agent_id,
                                "job_id": job_id,
                                "project_id": str(agent_job.project_id) if agent_job.project_id else None,
                                "agent_display_name": agent_execution.agent_display_name,
                                "agent_name": agent_execution.agent_name,
                                "mission_acknowledged_at": agent_execution.mission_acknowledged_at.isoformat(),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        logger.info(
                            "[WEBSOCKET] Broadcasted job:mission_acknowledged event",
                            extra={
                                "agent_id": agent_id,
                                "job_id": job_id,
                                "tenant_key": tenant_key,
                                "mission_acknowledged_at": agent_execution.mission_acknowledged_at.isoformat(),
                            },
                        )
                except Exception as ws_error:
                    # Non-blocking - WebSocket failures shouldn't break MCP tool
                    logger.warning(
                        f"[WEBSOCKET] Failed to broadcast job:mission_acknowledged event: {ws_error}",
                        extra={"agent_id": agent_id, "job_id": job_id},
                    )

            # Get project
            result = await session.execute(
                select(Project).where(
                    and_(
                        Project.id == agent_job.project_id,
                        Project.tenant_key == tenant_key,
                    )
                )
            )
            project = result.scalar_one_or_none()
            if not project:
                return {"error": "NOT_FOUND", "message": "Project not found for agent job"}

            # Get product with eager loading of relationships (Handover 0281: Fix lazy loading issue)
            if not project.product_id:
                return {"error": "NOT_FOUND", "message": "No product linked to project"}

            result = await session.execute(
                select(Product)
                .options(
                    joinedload(Product.vision_documents),  # Eager load vision documents
                    joinedload(Product.projects),  # Eager load projects
                )
                .where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
            )
            product = result.unique().scalar_one_or_none()

            if not product:
                return {"error": "NOT_FOUND", "message": "Product not found"}

            # Generate condensed mission
            planner = MissionPlanner(db_manager)
            metadata = agent_job.job_metadata or {}

            # Handover 0281 Phase 1 + 0283: Fetch user-specific config if user_id provided
            if user_id:
                user_config = await _get_user_config(user_id, tenant_key, session)
                field_priorities = user_config["field_priorities"]
                depth_config = user_config["depth_config"]
                logger.info(
                    "[USER_CONFIG] Applied user-specific configuration to orchestrator instructions",
                    extra={"agent_id": agent_id, "job_id": job_id, "user_id": user_id, "tenant_key": tenant_key},
                )
            else:
                # Fall back to job_metadata or empty dict (existing behavior)
                field_priorities = metadata.get("field_priorities", {})
                depth_config = metadata.get("depth_config", {})
                logger.debug(
                    "[USER_CONFIG] No user_id provided, using job_metadata config",
                    extra={"agent_id": agent_id, "job_id": job_id},
                )

            # Handover 0283: Pass depth_config to mission planner
            condensed_mission = await planner._build_context_with_priorities(
                product=product,
                project=project,
                field_priorities=field_priorities,
                depth_config=depth_config,
                user_id=user_id,
            )

            # Handover 0246c: Agent templates no longer embedded
            # Use get_available_agents() MCP tool instead

            # Phase C: Include original AgentJob.mission in the response
            # Prepend the job mission to the condensed context
            import json

            full_mission = f"{agent_job.mission}\n\n---\n\n{json.dumps(condensed_mission, indent=2)}"

            # Handover 0408: Serena MCP injection for orchestrators
            include_serena = False
            try:
                config_path = Path.cwd() / "config.yaml"
                if config_path.exists():
                    with open(config_path, encoding="utf-8") as f:
                        config_data = yaml.safe_load(f) or {}
                    include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
            except Exception as e:
                logger.warning(f"[SERENA] Failed to read config in get_orchestrator_instructions: {e}")

            if include_serena:
                from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions

                serena_notice = generate_serena_instructions(enabled=True)
                full_mission = serena_notice + "\n\n---\n\n" + full_mission
                logger.info("[SERENA] Injected into orchestrator instructions", extra={"agent_id": agent_id})

            # Calculate token estimate
            estimated_tokens = len(full_mission) // 4

            # Handover 0346: Read execution mode from Project table for live switching (not frozen metadata)
            execution_mode = getattr(project, "execution_mode", None) or metadata.get(
                "execution_mode", "multi_terminal"
            )
            cli_mode = execution_mode == "claude_code_cli"

            # Build base response
            response = {
                "agent_id": agent_id,  # Phase C: WHO is executing
                "job_id": job_id,  # Phase C: WHAT work order
                "project_id": str(project.id),
                "project_name": project.name,
                "project_description": project.description or "",
                "mission": full_mission,  # Job mission + condensed context
                "mission_format": "json",  # Handover 0347b: JSON format indicator
                "context_budget": agent_execution.context_budget or 150000,
                "context_used": agent_execution.context_used or 0,
                "agent_discovery_tool": "get_available_agents()",  # Handover 0246c: Reference to discovery tool
                "field_priorities": field_priorities,
                "token_reduction_applied": bool(field_priorities),
                "thin_client": True,
                # Handover 0347c: Add 6 new guidance fields
                "post_staging_behavior": _get_post_staging_behavior(cli_mode),
                "required_final_action": _get_required_final_action(),
                "multi_terminal_mode_rules": _get_multi_terminal_rules() if not cli_mode else None,
                "error_handling": _get_error_handling(),
                "agent_spawning_limits": _get_spawning_limits(),
                "context_management": _get_context_management(agent_execution.context_budget or 150000),
                # Handover 0408: Serena MCP integration status
                "integrations": {
                    "serena_mcp_enabled": include_serena,
                },
            }

            # Handover 0260 Phase 5a + 0351: Add agent_spawning_constraint for Claude Code CLI mode
            if execution_mode == "claude_code_cli":
                # Fetch allowed agent names from active templates
                result = await session.execute(
                    select(AgentTemplate.name).where(
                        and_(
                            AgentTemplate.tenant_key == tenant_key,
                            AgentTemplate.is_active == True,  # noqa: E712
                        )
                    )
                )
                allowed_agent_names = [row[0] for row in result.fetchall()]

                response["agent_spawning_constraint"] = {
                    "mode": "strict_task_tool",
                    "allowed_agent_names": allowed_agent_names,
                    "instruction": (
                        "CRITICAL: You MUST use Claude Code's native Task tool for agent spawning. "
                        "The agent_name parameter must EXACTLY match one of the allowed template names. "
                        "Use agent_display_name for display category labels. "
                        f"Allowed agent names: {allowed_agent_names}"
                    ),
                }

                logger.info(
                    f"[AGENT_CONSTRAINT] Added spawning constraint for CLI mode: {len(allowed_agent_names)} allowed names",
                    extra={
                        "agent_id": agent_id,
                        "job_id": job_id,
                        "execution_mode": execution_mode,
                        "allowed_names": allowed_agent_names,
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Error in get_orchestrator_instructions: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}


async def get_agent_mission(
    agent_id: str, tenant_key: str, db_manager: Optional["DatabaseManager"] = None
) -> dict[str, Any]:
    """
    Fetch agent mission (standalone for testing - Phase C).

    Updated in Handover 0366c to use agent_id parameter.

    Args:
        agent_id: Agent execution UUID (WHO is executing)
        tenant_key: Tenant isolation key
        db_manager: Optional DatabaseManager instance (for testing)

    Returns:
        Agent mission dict with both agent_id and job_id
    """
    from giljo_mcp.config_manager import get_config
    from giljo_mcp.database import DatabaseManager

    if db_manager is None:
        config = get_config()
        db_url = config.database.database_url
        db_manager = DatabaseManager(database_url=db_url, is_async=True)

    async with db_manager.get_session_async() as session:
        from sqlalchemy import and_, select

        from giljo_mcp.models.agent_identity import AgentExecution, AgentJob

        try:
            # Phase C: Resolve agent_id → job_id via AgentExecution
            result = await session.execute(
                select(AgentExecution).where(
                    and_(
                        AgentExecution.agent_id == agent_id,
                        AgentExecution.tenant_key == tenant_key,
                    )
                )
            )
            agent_execution = result.scalar_one_or_none()

            if not agent_execution:
                return {"error": "NOT_FOUND", "message": f"Agent execution {agent_id} not found"}

            # Phase C: Get job_id from execution
            job_id = agent_execution.job_id

            # Phase C: Get AgentJob with tenant isolation
            result = await session.execute(
                select(AgentJob).where(
                    and_(
                        AgentJob.job_id == job_id,
                        AgentJob.tenant_key == tenant_key,
                    )
                )
            )
            agent_job = result.scalar_one_or_none()

            if not agent_job:
                return {"error": "NOT_FOUND", "message": f"Agent job {job_id} not found"}

            estimated_tokens = len(agent_job.mission or "") // 4

            return {
                "agent_id": agent_id,  # Phase C: WHO is executing
                "job_id": job_id,  # Phase C: WHAT work order
                "agent_name": agent_execution.agent_name or agent_execution.agent_display_name,
                "agent_display_name": agent_execution.agent_display_name,
                "mission": agent_job.mission or "",
                "thin_client": True,
            }

        except Exception as e:
            logger.error(f"Error in get_agent_mission: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}


async def get_generic_agent_template(
    session: "AsyncSession",
    agent_id: str,
    job_id: str,
    product_id: str,
    project_id: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Get generic agent template with injected variables.

    Used by Orchestrator to spawn agents in Generic/Legacy mode.
    Template provides unified protocol for all agent types.

    Handover 0246b: Generic Agent Template Implementation

    Args:
        session: AsyncSession for database operations
        agent_id: UUID of agent instance
        job_id: UUID of job in MCP_AGENT_JOBS
        product_id: UUID of product context
        project_id: UUID of project context
        tenant_key: Tenant isolation key

    Returns:
        {
            "success": true,
            "template": "<rendered prompt>",
            "variables_injected": {
                "agent_id": "...",
                "job_id": "...",
                "product_id": "...",
                "project_id": "...",
                "tenant_key": "..."
            },
            "protocol_version": "1.0"
        }
    """
    try:
        from src.giljo_mcp.templates.generic_agent_template import GenericAgentTemplate

        template = GenericAgentTemplate()
        rendered = template.render(
            agent_id=agent_id,
            job_id=job_id,
            product_id=product_id,
            project_id=project_id,
            tenant_key=tenant_key,
        )

        logger.info(
            "Generic agent template rendered",
            extra={
                "agent_id": agent_id,
                "job_id": job_id,
                "template_version": template.version,
                "tenant_key": tenant_key,
            },
        )

        return {
            "success": True,
            "template": rendered,
            "variables_injected": {
                "agent_id": agent_id,
                "job_id": job_id,
                "product_id": product_id,
                "project_id": project_id,
                "tenant_key": tenant_key,
            },
            "protocol_version": template.version,
        }

    except Exception as e:
        logger.error(
            f"Failed to render generic agent template: {e}",
            extra={"agent_id": agent_id, "job_id": job_id, "tenant_key": tenant_key},
        )
        return {
            "success": False,
            "error": str(e),
            "agent_id": agent_id,
            "job_id": job_id,
        }


async def spawn_agent_job(
    agent_display_name: str,
    agent_name: str,
    mission: str,
    project_id: str,
    tenant_key: str,
    parent_job_id: Optional[str] = None,
    parent_agent_id: Optional[str] = None,
    db_manager: Optional["DatabaseManager"] = None,
    session: Optional["AsyncSession"] = None,
) -> dict[str, Any]:
    """
    Spawn agent job (standalone for testing).

    Args:
        agent_display_name: Type of agent
        agent_name: Name of agent
        mission: Agent mission
        project_id: Project UUID
        tenant_key: Tenant isolation key
        parent_job_id: Optional parent job UUID
        parent_agent_id: Handover 0506 - Retiring orchestrator's agent_id to authorize successor spawn
        db_manager: Optional DatabaseManager instance (for testing)
        session: Optional AsyncSession (for testing with transaction isolation)

    Returns:
        Spawn result dict
    """

    from giljo_mcp.config_manager import get_config
    from giljo_mcp.database import DatabaseManager

    # If session is provided, use it directly (for testing with transaction isolation)
    if session is not None:
        return await _spawn_agent_job_impl(
            session, agent_display_name, agent_name, mission, project_id, tenant_key, parent_job_id, parent_agent_id
        )

    # Otherwise, create session from db_manager
    if db_manager is None:
        config = get_config()
        db_url = config.database.database_url
        db_manager = DatabaseManager(database_url=db_url, is_async=True)

    async with db_manager.get_session_async() as session:
        return await _spawn_agent_job_impl(
            session, agent_display_name, agent_name, mission, project_id, tenant_key, parent_job_id, parent_agent_id
        )


async def _spawn_agent_job_impl(
    session,
    agent_display_name: str,
    agent_name: str,
    mission: str,
    project_id: str,
    tenant_key: str,
    parent_job_id: Optional[str] = None,
    parent_agent_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Internal implementation of spawn_agent_job.

    Args:
        parent_agent_id: Handover 0506 - If provided, bypasses orchestrator duplication check
                        when spawning successor during handover. The retiring orchestrator
                        provides its own agent_id to authorize successor creation.
    """

    from sqlalchemy import and_, select

    from giljo_mcp.models import AgentTemplate
    from giljo_mcp.models.agent_identity import AgentExecution, AgentJob

    try:
        # Handover 0351: Validate agent_name against active templates (NOT agent_display_name)
        # agent_name is the SINGLE SOURCE OF TRUTH for template matching
        # Skip validation for orchestrator (special case handled separately)
        if agent_display_name != "orchestrator":
            # Fetch active agent template names
            template_result = await session.execute(
                select(AgentTemplate.name).where(
                    and_(
                        AgentTemplate.tenant_key == tenant_key,
                        AgentTemplate.is_active == True,  # noqa: E712
                    )
                )
            )
            valid_agent_names = [row[0] for row in template_result.fetchall()]

            if agent_name not in valid_agent_names:
                # Invalid agent_name - provide helpful error message
                logger.warning(
                    f"Invalid agent_name '{agent_name}' - not in valid templates",
                    extra={
                        "agent_name": agent_name,
                        "agent_display_name": agent_display_name,
                        "valid_names": valid_agent_names,
                        "project_id": project_id,
                        "tenant_key": tenant_key,
                    },
                )
                return {
                    "success": False,
                    "error": f"Invalid agent_name '{agent_name}'. Must be one of: {valid_agent_names}",
                    "hint": (
                        "Handover 0351: The agent_name parameter must EXACTLY match a template name (e.g., 'implementer', 'tester'). "
                        "agent_name is the SINGLE SOURCE OF TRUTH for template matching. "
                        "Use agent_display_name for categorization (e.g., 'worker', 'reviewer')."
                    ),
                    "valid_agent_names": valid_agent_names,
                }

        # ORCHESTRATOR DUPLICATION PREVENTION
        # Check if we're trying to create an orchestrator
        if agent_display_name == "orchestrator":
            # Query for existing orchestrator EXECUTIONS in this project with active statuses
            result = await session.execute(
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentJob.tenant_key == tenant_key,
                        AgentExecution.agent_display_name == "orchestrator",
                        AgentExecution.status.in_(["waiting", "working"]),
                    )
                )
            )
            existing_orchestrator = result.scalar_one_or_none()

            if existing_orchestrator:
                # Handover 0506: Allow spawning successor if parent_agent_id matches existing orchestrator
                # This enables retiring orchestrator to spawn its own replacement during handover
                if parent_agent_id and parent_agent_id == existing_orchestrator.agent_id:
                    logger.info(
                        f"Handover: Allowing successor spawn from orchestrator {parent_agent_id}",
                        extra={
                            "project_id": project_id,
                            "tenant_key": tenant_key,
                            "parent_agent_id": parent_agent_id,
                            "existing_agent_id": existing_orchestrator.agent_id,
                        },
                    )
                    # Continue with spawn - this is an authorized handover
                else:
                    # Active orchestrator already exists - prevent duplicate
                    logger.warning(
                        f"Orchestrator already exists for project {project_id} with status {existing_orchestrator.status}",
                        extra={
                            "project_id": project_id,
                            "tenant_key": tenant_key,
                            "existing_agent_id": existing_orchestrator.agent_id,
                            "existing_job_id": existing_orchestrator.job_id,
                            "existing_status": existing_orchestrator.status,
                        },
                    )
                    return {
                        "success": False,
                        "error": f"Orchestrator already exists for this project with status '{existing_orchestrator.status}'. "
                        f"Only one active orchestrator is allowed during staging. Use succession for runtime handover.",
                        "existing_agent_id": existing_orchestrator.agent_id,
                        "existing_job_id": existing_orchestrator.job_id,
                        "existing_status": existing_orchestrator.status,
                    }

        # No duplicate found (or not an orchestrator) - proceed with creation
        # HIGH #3 FIX: Create BOTH AgentJob (work order) AND AgentExecution (executor)

        # Create work order (the WHAT)
        job_id = str(uuid4())
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project_id,
            mission=mission,
            job_type=agent_display_name,  # AgentJob uses job_type
            status="active",  # AgentJob uses 'active'
            job_metadata={},
        )
        session.add(agent_job)
        await session.flush()  # Flush to ensure job_id is available

        # Create executor (the WHO)
        agent_id = str(uuid4())
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name=agent_display_name,
            agent_name=agent_name,
            status="waiting",  # AgentExecution uses 'waiting'
            spawned_by=parent_job_id,  # Link to parent agent_id (not job_id)
            context_budget=10000,
            context_used=0,
        )
        session.add(agent_execution)

        # Update project staging_status when orchestrator is spawned
        if agent_display_name == "orchestrator":
            from giljo_mcp.models import Project

            result = await session.execute(
                select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
            )
            project = result.scalar_one_or_none()
            if project:
                project.staging_status = "staged"
                project.updated_at = datetime.now(timezone.utc)

        await session.commit()

        # HIGH #4 FIX: Generate thin prompt using agent_id (not agent_job_id)
        thin_prompt = f"""I am {agent_name} for Project.

## CRITICAL: MCP TOOL USAGE

MCP tools are **NATIVE tool calls** - identical to Read, Write, Bash, Glob.
- CORRECT: Call `mcp__giljo-mcp__get_agent_mission` directly as a tool
- WRONG: curl, HTTP, fetch, requests, SDK calls

## MANDATORY STARTUP SEQUENCE

Execute these IN ORDER before starting your mission:

1. **Get Mission:**
   Tool: mcp__giljo-mcp__get_agent_mission
   Parameters: {{"agent_id": "{agent_id}", "tenant_key": "{tenant_key}"}}

2. **Acknowledge Job (marks you as WORKING):**
   Tool: mcp__giljo-mcp__acknowledge_job
   Parameters: {{"job_id": "{job_id}", "agent_id": "{agent_id}"}}

3. **Check Messages (BEFORE starting work):**
   Tool: mcp__giljo-mcp__receive_messages
   Parameters: {{"agent_id": "{agent_id}"}}

## WORKFLOW REQUIREMENTS (MANDATORY)

BEFORE implementing ANY code, you MUST:
1. Create TodoWrite task list with 3-7 specific tasks
2. Count and announce: "X steps to complete: [list items]"
3. Mark tasks in_progress when starting, completed when finishing
4. Report progress: "Completed step X of Y: [description]"
5. NEVER skip planning - poor planning leads to poor execution

4. **Execute your mission** (details in get_agent_mission response)

5. **Report Progress** (after each milestone):
   Tool: mcp__giljo-mcp__report_progress
   Parameters: {{"job_id": "{job_id}", "tenant_key": "{tenant_key}", "todo_items": [
     {{"content": "Task description", "status": "completed|in_progress|pending"}}
   ]}}
   Backend calculates percent/steps automatically from your todo_items array.

6. **Complete Job** (when done):
   Tool: mcp__giljo-mcp__complete_job
   Parameters: {{"job_id": "{job_id}", "result": {{"summary": "...", "artifacts": [...]}}}}

Your full mission is in the database. Call get_agent_mission to retrieve it."""

        mission_tokens = len(mission) // 4
        prompt_tokens = len(thin_prompt) // 4

        # Broadcast agent creation via in-process WebSocketManager (0379e)
        try:
            from api.app import state

            websocket_manager = getattr(state, "websocket_manager", None)
            if websocket_manager:
                await websocket_manager.broadcast_to_tenant(
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
                        "mission": mission,  # Handover 0464: Include mission for UI display
                    },
                )
        except Exception as ws_error:
            logger.warning(f"[WEBSOCKET] Failed to broadcast agent:created: {ws_error}")

        # Build base response
        response = {
            "success": True,
            "job_id": job_id,  # Work order UUID
            "agent_id": agent_id,  # Executor UUID
            "execution_id": agent_execution.id,  # Handover 0457: Unique row ID for frontend Map key
            "agent_prompt": thin_prompt,
            "prompt_tokens": prompt_tokens,
            "mission_tokens": mission_tokens,
            # Handover 0383 Option B: Explicit Task tool usage
            "task_tool_usage": f"Task(subagent_type='{agent_name}', ...)",
        }

        # Handover 0383 Option C: Warning when agent_name != agent_display_name
        if agent_name != agent_display_name:
            response["warning"] = (
                f"agent_name '{agent_name}' differs from agent_display_name '{agent_display_name}'. "
                "Task tool MUST use agent_name (template filename), NOT agent_display_name."
            )

        return response

    except Exception as e:
        logger.error(f"Error in spawn_agent_job: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to spawn agent: {e!s}"}
