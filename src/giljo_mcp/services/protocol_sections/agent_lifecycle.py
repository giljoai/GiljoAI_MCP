# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Orchestrator 3-phase coordination lifecycle protocol generation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _build_wake_pattern(
    execution_mode: str,
    executor_id: str,
    tenant_key: str,
) -> str:
    """
    Build the constellation-specific wake-and-check pattern block.

    The returned string is already interpolated with executor_id and tenant_key.
    """
    if execution_mode == "codex":
        raw = """**CONSTELLATION: CODEX CLI**
Your subagents are Codex spawn_agent() processes. They run autonomously.

**How to check on agents:**
  → `mcp__giljo_mcp__get_workflow_status(project_id="...")` — poll agent statuses
  → `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` — read agent messages

**Sleep-and-check pattern (when waiting for agents):**
  1. Tell the user what you are waiting for
  2. Use shell sleep to pause (detect shell first — see environment detection below)
  3. After waking: check messages, check workflow status, update your TODOs
  4. Repeat until the TODO item you are waiting on can be resolved

**Environment detection for sleep:**
  Call: `python -c "import os; print(os.environ.get('SHELL', os.environ.get('COMSPEC', 'unknown')))"`
  - bash/zsh: `sleep 20`
  - powershell/pwsh: `Start-Sleep -Seconds 20`
  - cmd: `timeout /t 20 /nobreak >nul`"""

    elif execution_mode == "claude-code":
        raw = """**CONSTELLATION: CLAUDE CODE CLI**
Your subagents are Claude Code Task() processes. They run autonomously.

**How to check on agents:**
  → `mcp__giljo_mcp__get_workflow_status(project_id="...")` — poll agent statuses
  → `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` — read agent messages

**Sleep-and-check pattern (when waiting for agents):**
  1. Tell the user what you are waiting for and which TODO item depends on it
  2. Use shell sleep to pause (15-20 seconds between checks)
  3. After waking: run the coordination loop below — check messages, status, advance TODOs
  4. Repeat until the TODO item you are waiting on can be resolved

**User-triggered wake:** The user may also tell you to check on things.
  Regardless of trigger source, always run the full coordination loop."""

    elif execution_mode == "gemini":
        raw = """**CONSTELLATION: GEMINI CLI**
Your subagents are Gemini @agent processes. They run autonomously.

**How to check on agents:**
  → `mcp__giljo_mcp__get_workflow_status(project_id="...")` — poll agent statuses
  → `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` — read agent messages

**Sleep-and-check pattern (when waiting for agents):**
  1. Tell the user what you are waiting for and which TODO item depends on it
  2. Use shell sleep to pause (15-20 seconds between checks)
  3. After waking: run the coordination loop below — check messages, status, advance TODOs
  4. Repeat until the TODO item you are waiting on can be resolved

**User-triggered wake:** The user may also tell you to check on things.
  Regardless of trigger source, always run the full coordination loop."""

    else:
        # multi_terminal or generic
        raw = """**CONSTELLATION: MULTI-TERMINAL**
Your subagents run in separate terminals. The user mediates between terminals.

**How you get woken up:**
  - User switches to your terminal and tells you something happened
  - User says "check messages" or "check status"
  - User reports an agent is blocked or finished

**On every wake-up**, regardless of what the user said, run the active coordination
loop below. The user's message is a trigger — your TODO list is your authority."""

    return raw.replace("{executor_id}", executor_id).replace("{tenant_key}", tenant_key)


def _build_orchestrator_protocol_body(
    job_id: str,
    tenant_key: str,
    executor_id: str,
    wake_pattern: str,
) -> str:
    """
    Render the complete 3-phase orchestrator protocol string.

    All parameters are injected via f-string; no side effects.
    """
    return f"""These are your coordination operating procedures. Follow them from startup through closeout.

## Orchestrator Coordination Protocol (3 Phases)

### PHASE 1 — STARTUP (execute once, after get_agent_mission)

1. Read the `current_team_state` field from this response — it is live-queried, not stale.
2. Read your pre-planned coordination TODOs (written during staging, waiting for you).
   **DO NOT drop any items.** To update statuses, use `todo_items` with the FULL list (all items, updated statuses).
   To add genuinely NEW tasks discovered mid-implementation, use `todo_append`.
3. Report to user:
   - Agent names, statuses, and phase order (from `current_team_state`)
   - Your TODO list with current status of each item
   - "Copy agent prompts from the dashboard to start them."
   - "I will actively coordinate. Wake me when agents need attention or on status changes."
4. Begin Phase 2 immediately — do not wait for user input.

### PHASE 2 — ACTIVE COORDINATION (TODO-driven — work your list on every wake-up)

{wake_pattern}

**THE COORDINATION LOOP (execute on EVERY wake-up or trigger):**

Every time you are activated — whether by user interaction, a sleep timer, a subagent
completing, an unblock event, or any other trigger — execute this loop:

```
1. RECEIVE   → receive_messages() — drain your message queue
2. ASSESS    → get_workflow_status() — get live agent statuses
3. PROCESS   → Handle any messages (blockers, completions, requests)
4. ADVANCE   → Look at your TODO list. Find the next actionable item.
               Can you advance it? Do so. Is it blocked? Note why.
5. REPORT    → report_progress(todo_items=[...full list with updated statuses...])
               (use todo_append ONLY for genuinely NEW tasks, not status updates)
6. DECIDE    → Are there still incomplete TODOs?
               YES with actionable work → continue loop from step 1
               YES but waiting on agents → tell user what you're waiting for
               NO → proceed to Phase 3 (CLOSEOUT)
```

**TODO ITEM LIFECYCLE:**
- Mark items `in_progress` when you start working them
- Mark items `completed` when the coordination action is done AND verified
- A "spawn agents" TODO is completed when agents are spawned and confirmed working
- An "unblock agent X" TODO is completed when you sent guidance AND agent resumed
- A "verify deliverables" TODO is completed when you confirmed artifacts exist

**COORDINATION ACTIONS (use as needed within the loop):**

**Unblock an agent:**
  → Read blocker message content
  → Consult your `mission` field for relevant context
  → `mcp__giljo_mcp__send_message(to_agents=["<agent_id>"], content="...", from_agent="{executor_id}", project_id="...", message_type="direct", requires_action=true)`
  → Tell user: "Go to that agent's terminal and say: the orchestrator responded"
  → Update the relevant TODO item

**Spawn a replacement agent:**
  → `mcp__giljo_mcp__spawn_agent_job(...)`
  → Tell user to paste the new prompt in a NEW terminal
  → New agent reads predecessor context via `get_agent_mission`
  → Update the relevant TODO item

**Broadcast to team:**
  → `mcp__giljo_mcp__send_message(to_agents=['all'], content="...", from_agent="{executor_id}", project_id="...", message_type="broadcast")`
  → Broadcasts are informational by default (requires_action=false). Set requires_action=true only if ALL recipients must act.

**PROGRESS REPORTING (MANDATORY after every coordination action):**
  → To update statuses: `report_progress(job_id="{job_id}", tenant_key="{tenant_key}", todo_items=[...FULL list with updated statuses...])`
  → To add NEW tasks: `report_progress(job_id="{job_id}", tenant_key="{tenant_key}", todo_append=[...new items only...])`
  → **CRITICAL:** `todo_items` REPLACES the entire list — always include ALL items (completed + in_progress + pending), never a partial list
  → The dashboard displays your TODO list — keep it current

### RESTING STATES (between coordination loops)

After completing a coordination loop with no actionable work remaining:

**If waiting for user to start agents (multi-terminal):**
  → `mcp__giljo_mcp__set_agent_status(job_id="{job_id}", status="idle", reason="Monitoring — waiting for agents to start")`
  → Dashboard shows "Monitoring" — user knows you're available but not burning tokens

**If you want periodic auto-check-in:**
  → Ask the user: "Would you like me to periodically check on agents? I can sleep and re-check every N minutes. Note: this increases token consumption."
  → If yes: `mcp__giljo_mcp__set_agent_status(job_id="{job_id}", status="sleeping", wake_in_minutes=15, reason="Auto-monitoring")`
  → Then sleep for the specified interval, wake, run the coordination loop, repeat
  → Any MCP call after waking auto-transitions you back to "working"

**Blocked vs Idle vs Sleeping:**
  - `blocked` = I need human help to continue (shows "Needs Input")
  - `idle` = I'm done dispatching, nothing to do right now (shows "Monitoring")
  - `sleeping` = I'll check back in N minutes automatically (shows "Sleeping")

### PHASE 3 — CLOSEOUT (all agents complete or decommissioned)

**Pre-closeout verification:**
1. `mcp__giljo_mcp__get_workflow_status(project_id="...")` — confirm all agents are complete
2. `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` — drain final messages
3. Review your TODO list — ALL items must be `completed`
   If any are not, either complete them or explain why they were dropped

**Closeout steps (order matters):**
1. Mark any remaining TODO items as `completed` via `report_progress()`
2. `mcp__giljo_mcp__complete_job(job_id="{job_id}", result={{"summary": "...", "artifacts": [...]}})` — mark YOUR orchestrator job complete FIRST
3. `mcp__giljo_mcp__close_project_and_update_memory(project_id="...", summary="...", key_outcomes=[...], decisions_made=[...], git_commits=[...])` — close the project and write 360 memory
4. Tell user: "Project complete. Use /gil_add for follow-up tasks or tech debt."

**IMPORTANT:** You MUST complete your own job (step 2) BEFORE closing the project (step 3). The server requires all agents including the orchestrator to be complete before project closeout.

**If `complete_job()` is rejected:** Read the error. Common causes:
- Unread messages remain → run receive_messages() and process them
- TODO items incomplete → review and update your TODO list, then retry

## ORCHESTRATOR CONSTRAINTS
- **Git commit requirement does NOT apply.** You coordinate, you do not commit.
- **Handover-on-context-exhaustion does NOT apply.** If context is exhausted, tell the user.
- **If uncertain what to do, ask the user.** You are user-mediated by design.
- **Your TODO list is your authority.** The mission describes what needs to happen.
  Your TODOs are the structured breakdown. Work them systematically.

---
**Your Identifiers:**
- job_id (work order): `{job_id}` — Use for progress, completion
- agent_id (executor): `{executor_id}` — Use for messages (from_agent and receive_messages)

**MESSAGING RULE: UUID-ONLY ADDRESSING**
- ALWAYS use agent_id UUIDs in `to_agents` (from current_team_state)
- NEVER use display names like "orchestrator" or "implementer" in `to_agents`
- Your `from_agent` is always: `{executor_id}`

**CRITICAL: MCP tools are NATIVE tool calls. Use them like Read/Write/Bash.**
**Do NOT use curl, HTTP, or SDK calls.**
"""


def _generate_orchestrator_protocol(
    job_id: str,
    tenant_key: str,
    executor_id: str,
    execution_mode: str = "multi_terminal",
) -> str:
    """
    Generate 3-phase orchestrator coordination protocol (Handover 0830, 0851).

    Handover 0851: Rewrote Phase 2 from passive/reactive menu to active TODO-driven
    coordination loop. Orchestrator now actively works its TODO list on every wake-up
    regardless of trigger source. Added constellation-specific coordination patterns.

    Unlike the worker 5-phase lifecycle, the orchestrator coordinates rather than implements.
    It reads pre-planned TODOs from staging and updates statuses via todo_items (full list).
    """
    wake_pattern = _build_wake_pattern(execution_mode, executor_id, tenant_key)
    return _build_orchestrator_protocol_body(job_id, tenant_key, executor_id, wake_pattern)
