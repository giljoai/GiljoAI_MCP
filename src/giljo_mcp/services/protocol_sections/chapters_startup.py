"""Orchestrator protocol chapter builders for CH1 and CH2 (startup sequence)."""

from __future__ import annotations

from typing import Any


def _build_ch1_mission(tool: str = "claude-code") -> str:
    """Build CH1: YOUR MISSION section (~180 tokens).

    Args:
        tool: Platform identifier — 'claude-code', 'codex', 'gemini', or 'multi_terminal'.
    """
    # Platform-specific "do not spawn" warning
    spawn_warning_map = {
        "codex": "You do NOT call spawn_agent() (that's for implementation phase)",
        "gemini": "You do NOT invoke @agent commands (that's for implementation phase)",
        "claude-code": "You do NOT call Task() tool (that's for implementation phase)",
    }
    spawn_warning = spawn_warning_map.get(tool, "You do NOT execute implementation work directly")

    return f"""════════════════════════════════════════════════════════════════════════════
                           CH1: YOUR MISSION
════════════════════════════════════════════════════════════════════════════

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)

You are STAGING the project. Your job:
1. Analyze requirements from project_description
2. Create condensed mission plan
3. Assign work to specialist agents via spawn_agent_job()

WHAT YOU ARE NOT:
- You do NOT execute implementation work
- {spawn_warning}
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
DO NOT report progress yet. Steps 0-3 are internal startup — do not track them.

After Step 4 (Create Mission), you will have a real plan with work items.
THAT is when you initialize progress tracking.

IMPLEMENTATION TODO LIST
During staging, write yourself a todo list for the implementation phase.
This is your execution plan — the deliverables you will hold yourself
accountable to when implementation begins (which may be a different
session with fresh context).

Each item should describe a PROJECT OUTCOME, not an orchestrator action.
You already know how to spawn agents, fetch context, and broadcast signals.
Don't write down your operating procedures. Write down what the project
needs to deliver.

Good: "Build authentication API", "Validate inter-agent messaging", "Generate test summary report"
Bad:  "Spawn api-implementer agent", "Fetch context", "Broadcast STAGING_COMPLETE"

Aim for 3-7 items. Too few = no visibility. Too many = you're tracking mechanics again.

Test: If you lost all memory of staging and only had this list, could you
understand what the project needs to accomplish?

Call: report_progress(
          job_id='{orchestrator_id}',
          todo_items=[{{"content": "<project outcome>", "status": "pending"}}]
      )
Note: tenant_key auto-injected by server from API key session

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
