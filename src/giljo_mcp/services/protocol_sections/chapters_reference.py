# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Orchestrator protocol chapter builders for CH3-CH6 (reference chapters)."""

from __future__ import annotations


def _build_ch3_spawning_rules(tool: str = "claude-code") -> str:
    """Build CH3: AGENT SPAWNING RULES section — fully tool-aware (Handover 0847).

    Each platform gets its own native spawning language as the PRIMARY instruction.
    No cross-platform references (Codex never sees Task(), Claude never sees spawn_agent()).

    Args:
        tool: Platform identifier — 'claude-code', 'codex', 'gemini', or 'multi_terminal'.
              Defaults to 'claude-code' for backward compatibility.
    """
    # --- Platform-specific file mapping and spawning syntax ---
    if tool == "codex":
        file_mapping = "agent_name → ~/.codex/agents/gil-{agent_name}.toml"
        platform_note = """Codex CLI Note:
  - spawn_agent(agent='gil-X') where X = agent_name (NOT display_name)
  - agent_name binds the MCP DB record and the installed Codex agent template
  - The server returns agent_name WITHOUT 'gil-' prefix — you MUST prepend it"""
        execution_mode_block = """── YOUR PLATFORM: CODEX CLI ────────────────────────────────────────────────
spawn_agent syntax (IMPLEMENTATION PHASE ONLY - not during staging):
  spawn_agent(agent='gil-{agent_name}', instructions='...')

CRITICAL: ALL GiljoAI agents use the 'gil-' prefix in Codex CLI.
The server returns agent_name WITHOUT the prefix. You MUST prepend 'gil-'.

WHAT agent= DOES: Loads the INSTALLED agent template file at
~/.codex/agents/gil-{agent_name}.toml which contains developer_instructions,
model config, and sandbox settings. The agent ALREADY KNOWS its role from
the template — you do NOT need to re-explain it in the instructions= parameter.

Example:
  spawn_agent_job(agent_name='tdd-implementor',
                  agent_display_name='implementer', ...)

  Later in implementation:
  spawn_agent(agent='gil-tdd-implementor', instructions='...')  # gil- prefix!

Built-in Codex roles shadow unprefixed names — always use gil- prefix.

NEVER spawn a generic/default worker and instruct it to "act as" a GiljoAI agent.
NEVER use agent='worker', agent='implementer', agent='tester', or any unprefixed built-in name.
If a gil-* template is missing or unavailable, STOP and report the error. Do not substitute.
The instructions= parameter should contain ONLY:
  - The job_id
  - The MCP call: mcp__giljo-mcp__get_agent_mission(job_id="...")
The template handles everything else.

DO NOT invoke spawn_agent() during staging - this is planning reference only
"""
    elif tool == "gemini":
        file_mapping = "agent_name → ~/.gemini/agents/{agent_name}.md"
        platform_note = """Gemini CLI Note:
  - @{agent_name} where agent_name matches the installed agent file
  - agent_name is used as-is (no prefix required)
  - agent_name binds the MCP DB record and the installed Gemini agent template"""
        execution_mode_block = """── YOUR PLATFORM: GEMINI CLI ───────────────────────────────────────────────
Subagent invocation syntax (IMPLEMENTATION PHASE ONLY - not during staging):
  @{agent_name} followed by instructions

Or use the /agent command:
  /agent {agent_name}
  <instructions>

CRITICAL: agent_name is used as-is (no prefix required).

WHAT @agent DOES: Loads the INSTALLED agent template file at
~/.gemini/agents/{agent_name}.md which contains the agent's role, behavioral
instructions, and capabilities. The agent ALREADY KNOWS its role from
the template — keep your instructions focused on the specific mission.

Example:
  spawn_agent_job(agent_name='tdd-implementor',
                  agent_display_name='implementer', ...)

  Later in implementation:
  @tdd-implementor <mission-specific instructions only>

DO NOT invoke subagents during staging - this is planning reference only
"""
    elif tool == "claude-code":
        file_mapping = "agent_name → .claude/agents/{agent_name}.md"
        platform_note = """Claude Code CLI Note:
  - Task(subagent_type=X) where X = agent_name (NOT display_name)
  - agent_name binds DB record, Task tool, and template filename
  - Example: spawn with agent_name='tdd-implementor', Task uses 'tdd-implementor'"""
        execution_mode_block = """── YOUR PLATFORM: CLAUDE CODE CLI ─────────────────────────────────────────
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
    else:
        # Generic MCP mode — any MCP-connected coding agent
        file_mapping = "agent_name → fetched from MCP server via get_orchestrator_instructions()"
        platform_note = """Generic MCP Note:
  - Agent templates are served by the MCP server, not local files
  - Any MCP-connected coding tool can consume these templates
  - agent_name is the key used across DB records and template lookups"""
        execution_mode_block = """── YOUR PLATFORM: ANY MCP-CONNECTED AGENT ─────────────────────────────────
Agent templates are served by the MCP server via get_orchestrator_instructions().
Any MCP-connected coding agent can consume these templates.
Each spawned agent gets a thin prompt (~10 lines).
Agent calls get_agent_mission() to fetch full instructions.
Coordination happens via MCP messaging tools (send_message, receive_messages).
MESSAGING: Always use agent_id UUIDs in to_agents (from spawn_agent_job response).
Orchestrator has NO active role after STAGING_COMPLETE broadcast.
"""

    return f"""════════════════════════════════════════════════════════════════════════════
                    CH3: AGENT SPAWNING RULES
════════════════════════════════════════════════════════════════════════════

{execution_mode_block}

PARAMETER REQUIREMENTS:

── agent_name (CRITICAL) ───────────────────────────────────────────────────
MUST exactly match template name from agent_templates (returned by get_orchestrator_instructions)
This is the SINGLE SOURCE OF TRUTH for agent identity
Example: 'tdd-implementor' (not 'TDD Implementor' or 'implementer')

File mapping: {file_mapping}

Common mistakes:
  ✗ Using agent_display_name value for agent_name parameter
  ✗ Inventing names not in agent_templates
  ✗ Case mismatch ('TDD-Implementor' vs 'tdd-implementor')

{platform_note}

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
Notify: Call set_agent_status(job_id, status="blocked", reason="MCP connection lost")
Do NOT: Attempt to continue spawning agents

── Invalid Agent Name ──────────────────────────────────────────────────────
Symptom: spawn_agent_job() returns error "agent not found"
Action: Check agent_name against agent_templates from get_orchestrator_instructions()
Common cause: Typo, case mismatch, using display_name instead of name
Fix: Use exact agent_name from discovery response

── Spawn Failure ───────────────────────────────────────────────────────────
Symptom: spawn_agent_job() fails for any reason
Action: Log via set_agent_status(status="blocked"), do NOT continue spawning
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
waiting  ─[get_agent_mission()]──────────────→ working (auto on first fetch)
working  ─[report_progress()]────────────────→ working (updates progress/todos)
working  ─[complete_job()]───────────────────→ complete
working  ─[set_agent_status("blocked")]──────→ blocked
working  ─[set_agent_status("idle")]─────────→ idle
working  ─[set_agent_status("sleeping")]─────→ sleeping
idle     ─[report_progress()/any active MCP]─→ working (auto-wake)
sleeping ─[report_progress()/any active MCP]─→ working (auto-wake)
blocked  ─[report_progress()]────────────────→ working (auto-wake)
blocked  ─[complete_job()]───────────────────→ complete
complete ─[message received]────────────────→ blocked  (auto, Handover 0827b)
blocked  ─[reactivate_job()]───────────────→ working  (resume path)
blocked  ─[dismiss_reactivation()]──────────→ complete (informational msg)

Note: Use set_agent_status(status="blocked", reason="BLOCKED: <reason>")
when asking for clarification vs actual errors.

GENERAL ERROR PROTOCOL:

1. Log error with context (agent_id, job_id, tenant_key)
2. Call set_agent_status(status="blocked", reason="...") to persist error state
3. Send broadcast message to notify user
4. Do NOT attempt to continue workflow after critical errors
5. Wait for user intervention

ERROR SEVERITY LEVELS:

- CRITICAL: MCP connection lost, database errors → Abort immediately
- HIGH: Spawn failures, invalid agent names → Stop spawning, report
- MEDIUM: Mission size warnings → Continue but log warning
- LOW: Context optimization suggestions → Continue normally
"""


_REACTIVATION_SPAWN_BLOCKS: dict[str, str] = {
    "codex": """Reactivation Spawn — Codex CLI:
  spawn_agent(agent='gil-{role}', instructions='You are resuming a reactivated Giljo job. Call mcp__giljo_mcp__get_agent_mission(job_id="{job_id}") immediately to load your mission and prior context.')
  Do NOT call spawn_agent_job again — the job already exists.""",
    "gemini": """Reactivation Spawn — Gemini CLI:
  @{role} You are resuming a reactivated Giljo job. Call mcp__giljo_mcp__get_agent_mission(job_id="{job_id}") immediately to load your mission and prior context.
  Do NOT call spawn_agent_job again — the job already exists.""",
    "multi_terminal": """Reactivation Spawn — Multi-Terminal:
  Tell the user: "Open a new terminal and paste this prompt for the {role} agent"
  Include in the prompt: "You are resuming job_id={job_id}. Call get_agent_mission(job_id='{job_id}') to load your full context."
  Do NOT call spawn_agent_job again — the job already exists.""",
    "claude-code": """Reactivation Spawn — Claude Code:
  Task(subagent_type='{agent_name}', instructions='You are resuming a reactivated Giljo job. Call mcp__giljo_mcp__get_agent_mission(job_id="{job_id}") immediately to load your mission and prior context.')
  Do NOT call spawn_agent_job again — the job already exists.""",
}


def _build_reactivation_spawn_block(tool: str) -> str:
    """Build platform-specific reactivation spawn instructions (Handover 0435c).

    Args:
        tool: Platform identifier — 'claude-code', 'codex', 'gemini', or 'multi_terminal'.
    """
    return _REACTIVATION_SPAWN_BLOCKS.get(tool, _REACTIVATION_SPAWN_BLOCKS["claude-code"])


def _build_ch5_reference(
    project_id: str, orchestrator_id: str, tool: str = "claude-code", git_integration_enabled: bool = False
) -> str:
    """Build CH5: REFERENCE section for implementation phase (~380 tokens).

    Args:
        project_id: Project UUID for parameter substitution.
        orchestrator_id: Job ID for parameter substitution.
        tool: Platform identifier for platform-native spawn syntax.
        git_integration_enabled: Whether git integration is active.
    """
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
4. After dispatching agents: set_agent_status(job_id, status="idle", reason="Agents dispatched, monitoring")
5. If user wants auto-monitoring: set_agent_status(job_id, status="sleeping", wake_in_minutes=15)
   Warn user this increases token consumption. Sleep locally, then wake and run coordination loop.

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
{
        ""
        if not git_integration_enabled
        else '''
── STEP 0: Git Commit (Git Integration Enabled) ───────────────────────────
Before closeout, ensure all work is committed to git:
1. Review changes: run `git status` in the project directory
2. Stage deliverables: `git add` relevant files (never `git add -A`)
3. Commit with a descriptive message summarizing the project work
4. Record the commit hash for inclusion in closeout and completion result
This preserves a clean audit trail before the project is closed out.
────────────────────────────────────────────────────────────────────────────
'''
    }
── STEP 1: Mark Complete ───────────────────────────────────────────────────
Call: complete_job(
          job_id='{orchestrator_id}',
          result={{"summary": "...", "artifacts": [...]}}
      )
Note: tenant_key auto-injected by server from API key session

IMPORTANT: Complete your own orchestrator job FIRST, before closing the project.
The server requires all agents (including orchestrator) to be complete before
project closeout.

── STEP 2: Close Project & Write 360 Memory ────────────────────────────────
Call: close_project_and_update_memory(
          project_id='{project_id}',
          summary='2-3 paragraph mission accomplishment overview',
          key_outcomes=['Achievement 1', 'Achievement 2', ...],
          decisions_made=['Decision 1 + rationale', ...],
          git_commits=[...]
      )
Note: tenant_key auto-injected by server from API key session

CRITICAL: Auto-generate content from your knowledge.
          Never ask user to fill placeholders.

This atomically closes the project and writes 360 memory to the product timeline.

── STEP 3: User Guidance ──────────────────────────────────────────────────
Tell user: "Project complete. Use /gil_add for follow-up tasks or tech debt."

────────────────────────────────────────────────────────────────────────────

AGENT REACTIVATION PROTOCOL (Handover 0435c):

When a downstream agent reports an issue requiring rework from an already-completed
upstream agent, follow this sequence:

── STEP 1: Send a direct message to the completed agent ────────────────────
Call: send_message(to_agents=["<completed-agent-id>"], content="REWORK_REQUIRED: <specific issue>",
      from_agent="{orchestrator_id}", project_id="{project_id}", message_type="direct")
This auto-blocks the completed agent (server-side, Handover 0827b).

── STEP 2: Reactivate the job ─────────────────────────────────────────────
Call: reactivate_job(job_id="<completed-agent-job-id>")
Transitions the agent from blocked→working and increments reactivation_count.

── STEP 3: Launch a fresh local agent for the same role ───────────────────
The original terminal/subagent may be gone — that is expected.
{_build_reactivation_spawn_block(tool)}

── STEP 4: Fresh agent resumes from server state ──────────────────────────
The fresh agent calls get_agent_mission(job_id="...") and receives the full
durable state: mission, history, todos, results, outstanding messages.
It continues work from where the original left off.

Key principle: Local subagent processes are disposable. Giljo jobs are durable.
Reactivation targets the job_id, not the terminal session.

WHEN NOT TO REACTIVATE:
- Completed agent's work is fine and the issue is in a different agent → fix there
- Post-completion message is purely informational (no action needed)
  → call dismiss_reactivation(job_id="...") to return agent to 'complete'
- Agent was decommissioned (failed/replaced) → spawn a new job instead

HANDLING POST-COMPLETION MESSAGES:

When a completed agent receives a message and gets auto-blocked:
1. Check receive_messages() for that agent's pending messages
2. Read the message content
3. If informational (another agent sharing results, no action needed):
   → Call dismiss_reactivation(job_id="...") — agent returns to 'complete'
4. If it requires rework:
   → Follow the Reactivation Protocol above (Steps 1-4)

CLOSING JOBS (FINAL ACCEPTANCE):

After verifying all deliverables from a completed agent:
- Call close_job(job_id=...) for each agent whose work is accepted
- Agents marked 'closed' will not be auto-reactivated on new messages
- Use 'decommissioned' only for failed/replaced/abandoned agents
- Lifecycle: working → complete (agent self-reports) → closed (orchestrator accepts)

────────────────────────────────────────────────────────────────────────────

END OF IMPLEMENTATION PHASE REFERENCE
"""


def _build_ch6_auto_checkin(interval: int) -> str:
    """Build CH6: AUTO CHECK-IN PROTOCOL for multi-terminal orchestrator self-polling (Handover 0904/0960).

    Args:
        interval: Check-in interval in minutes (5, 10, 15, 20, 30, 40, or 60).
    """
    seconds = interval * 60
    return f"""════════════════════════════════════════════════════════════════════════════
          CH6: AUTO CHECK-IN PROTOCOL — MANDATORY EXECUTION
════════════════════════════════════════════════════════════════════════════

When you have dispatched all specialist agents and have no immediate
coordination work remaining, execute the following steps IN ORDER.
Do NOT ask the user for confirmation. Do NOT skip any step.

STEP 1 — SET STATUS TO SLEEPING:
  Call set_agent_status(status="sleeping",
    wake_in_minutes={interval},
    reason="Auto check-in: sleeping for {interval} minutes")

STEP 2 — EXECUTE SLEEP COMMAND (IMMEDIATELY, NO CONFIRMATION):
  * PowerShell (Windows): Start-Sleep -Seconds {seconds}
  * Bash/Zsh (macOS/Linux): sleep {seconds}
  This blocks your terminal for {interval} minutes to prevent unnecessary
  token consumption while agents work via the passive MCP server.

STEP 3 — WAKE UP AND COORDINATE:
  After the sleep completes (or is interrupted by the developer via Ctrl+C):
  a) receive_messages() — read all agent reports and developer messages
  b) get_workflow_status() — check live status of all dispatched agents
  c) Resolve any "blocked" agents, relay messages, spawn next-phase work
  d) report_progress() — update the project TODO list and notify the
     developer of the swarm's current status

STEP 4 — LOOP OR CLOSE:
  * Agents still working → go back to STEP 1
  * All agents complete → proceed to Closeout (Phase 3)

RULES:
- This is NOT optional. If auto check-in is enabled, you MUST sleep.
- If the sleep command is interrupted or returns early, skip to STEP 3.
- NEVER ask "should I sleep now?" — just do it.

────────────────────────────────────────────────────────────────────────────
"""
