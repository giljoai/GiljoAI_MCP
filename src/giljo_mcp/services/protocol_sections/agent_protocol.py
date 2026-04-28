# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Agent 5-phase lifecycle protocol generation."""

from __future__ import annotations

from giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol


def _build_conditional_blocks(
    git_integration_enabled: bool,
    execution_mode: str,
    tool: str,
) -> tuple[str, str]:
    """
    Build optional Phase 4 blocks that depend on runtime configuration.

    Returns:
        (git_commit_block, gil_add_block) — either string may be empty.
    """
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
        # Handover 0841: Platform-aware command syntax in closeout signoff
        gil_add_cmd = "$gil-add" if tool == "codex" else "/gil_add"
        gil_add_block = f"""
### User Guidance (Multi-Terminal)
After completing your work, tell the user:
"My work is complete. If you discovered technical debt or follow-up work,
tell me and I'll use {gil_add_cmd} to save it to your dashboard."
"""

    return git_commit_block, gil_add_block


def _build_worker_protocol_body(
    job_id: str,
    tenant_key: str,
    executor_id: str,
    job_type: str,
    phase1_step4: str,
    git_commit_block: str,
    gil_add_block: str,
    protocol_framing: str,
) -> str:
    """
    Render the complete 5-phase worker protocol string.

    All parameters are injected via f-string; no side effects.
    """

    # ruff's S608 detector matches the `from_agent=` token in example send_message calls
    # within the f-string body. Suppressed at function level rather than per-line.
    body = rf"""## Agent Lifecycle Protocol (5 Phases)

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

1. Call `mcp__giljo_mcp__get_agent_mission(job_id="{job_id}", tenant_key="{tenant_key}")` - Get mission (auto-transitions to WORKING)
2. Call `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")` - Check for instructions
3. Review any messages and incorporate feedback BEFORE starting work

{phase1_step4}

### Phase 2: EXECUTION
Execute your assigned tasks (TodoWrite created in Phase 1):
- Maintain focus on mission objectives
- Update todos as you progress
- **MESSAGE CHECK**: Call `receive_messages()` after completing each TodoWrite task
  - Full call: `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
  - If queue not empty: Process messages BEFORE continuing
  - If queue empty: Safe to proceed

### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `receive_messages()` - MANDATORY before reporting
   - Full call: `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
2. Process ALL pending messages
3. Call `report_progress()` with your todo_items:

   mcp__giljo_mcp__report_progress(
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

**WARNING: todo_items is a FULL REPLACEMENT.** Always include ALL prior items with their
current statuses. Omitting completed items will be REJECTED by the server (regression guard).
Use todo_append to add genuinely new items discovered mid-work.

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
- ALWAYS use `receive_messages()` to check messages (NOT `inspect_messages()`)
- `receive_messages()` auto-acknowledges and removes messages from queue
- `inspect_messages()` is read-only - messages stay pending (use for debugging only)

### Phase 4: COMPLETION
Before calling `complete_job()`, you MUST verify:
1. All TODO items completed (your TodoWrite list is fully marked completed)
2. All messages read (queue empty after `receive_messages()`)

**Resolve action tags:** Before completing, check if any `action_required` tagged items from
360 memory were addressed by your work (visible in fetch_context memory_360 under `action_required_items`).
If so, include `resolved_action_items: ["<description>"]` in your result dict to clear them.

Final steps:
1. Call `receive_messages()` - Final message check
   - Full call: `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`
2. Process any pending messages - ensure queue is empty
3. Call `complete_job()` - ONLY after TODOs are complete and queue is empty
   - Full call: `mcp__giljo_mcp__complete_job(job_id="{job_id}", result={{"summary": "...", "artifacts": [...]}})`

If you call `complete_job()` without meeting these requirements:
- System will REJECT your completion
- Response will list specific blockers (unread messages, incomplete TODOs)

#### Phase 4 — ORCHESTRATOR ADDENDUM: Closeout sequence

Orchestrators MUST NOT place `write_360_memory(...)` or `close_project_and_update_memory(...)`
on their TodoWrite list. Those calls execute AFTER `complete_job()` returns success — a
TodoWrite entry for them would be unmarkable until after `complete_job` runs, and the
COMPLETION_BLOCKED gate would then trap you with an unfinished TODO.

Your final pre-completion TODO should read something like
"Verify all agents complete and prepare closeout summary." Mark it complete IMMEDIATELY
BEFORE calling `complete_job()` — the act of calling `complete_job()` IS the start of the
closeout sequence, not a step that follows it.

Canonical post-completion sequence (mirrors `project_closeout.py` required_sequence):

1. `complete_job(job_id=...)` — orchestrator completes itself FIRST
2. `write_360_memory(...)` — write the project memory entry
3. `close_project_and_update_memory(project_id=..., force=False)` — final close after all agents complete

Example ordered calls:

```
# All agent work verified, all messages read, all pre-closeout TODOs marked complete
complete_job(job_id="...", result={{"summary": "...", "artifacts": [...]}})  # closeout step 1
write_360_memory(project_id="...", ...)                                      # closeout step 2 (post-complete_job)
close_project_and_update_memory(project_id="...", force=False)               # closeout step 3
```
{git_commit_block}{gil_add_block}
### Phase 5: ERROR HANDLING & BLOCKED STATUS

**To mark yourself BLOCKED** (unclear requirements, waiting for clarification):
1. Call `mcp__giljo_mcp__set_agent_status(job_id="{job_id}", status="blocked", reason="BLOCKED: <reason>")`
   - Sets status to "blocked" and stores block_reason
2. Send message to orchestrator explaining what you need (use orchestrator's agent_id UUID from YOUR TEAM table):
   - `mcp__giljo_mcp__send_message(to_agents=["<orchestrator-agent-id-uuid>"], content="BLOCKER: <details>", from_agent="{executor_id}", project_id="...", message_type="direct", requires_action=true)`
   - ALWAYS use the orchestrator's agent_id UUID, NEVER the display name "orchestrator"
3. STOP work and poll for response (use longer intervals while blocked — 15-20 seconds between polls, up to 5 attempts):
   - `mcp__giljo_mcp__receive_messages(agent_id="{executor_id}", tenant_key="{tenant_key}")`

**To resume from BLOCKED**:
1. After receiving guidance, call `report_progress()` with your updated TODO list:
   - `mcp__giljo_mcp__report_progress(job_id="{job_id}", tenant_key="{tenant_key}", todo_items=[...])`
   - This automatically transitions your status from "blocked" back to "working"
2. Continue execution with Phase 2

**Use BLOCKED for**: Unclear requirements, missing context, waiting for decisions, unrecoverable errors (all errors use blocked status)

## If You Are Reactivated (Handover 0435c)

If you receive context indicating you are resuming a previously completed job:
1. Call `get_agent_mission(job_id="...")` to load your full prior context
2. Read any new messages via `receive_messages()` — these contain the reason for reactivation
3. Continue work from your prior state — do not restart from scratch
4. When done, call `complete_job()` again with updated results

## Handover on Context Exhaustion

If you run out of context before completing, **DO NOT write 360 memory**.
Memory writes are orchestrator-only — both for normal completion and for handovers.
Your job is to send the orchestrator everything it needs to decide what happens next.

1. Send a HANDOVER message to the orchestrator (use the orchestrator's agent_id UUID
   listed in YOUR TEAM table at the top of your mission):
   - `mcp__giljo_mcp__send_message(to_agents=["<orchestrator-agent-id-uuid>"],`
     `content="HANDOVER: Context exhausted. COMPLETED: <what you finished>.`
     `IN-PROGRESS: <what was active and the stopping point>. NEXT-STEPS:`
     `<what a successor needs to do>. BLOCKERS: <any known blockers>.",`
     `from_agent="{executor_id}", project_id="...", message_type="direct",`
     `requires_action=true)`
2. Set yourself BLOCKED so the orchestrator knows you're waiting:
   - `mcp__giljo_mcp__set_agent_status(job_id="{job_id}", status="blocked",`
     `reason="BLOCKED: context exhausted, handover sent to orchestrator")`
3. STOP. Do NOT call `complete_job()` and do NOT call `write_360_memory()`.
   The orchestrator will decide whether to spawn a successor (preserving your
   job_id) or write a handover memory entry itself.

Workers may write `baseline`, `decision`, `architecture`, and `discovery` entries
when their mission explicitly assigns them. Workers MUST NOT write `project_completion`,
`session_handover`, or `action_required` entries — the tool will reject those with
`ORCHESTRATOR_ONLY_ENTRY_TYPE`. To record those, send a HANDOVER or progress message
to your orchestrator with the content.

Concrete examples (one per category):
- Worker `baseline`: `write_360_memory(entry_type="baseline", ...)` after seeding
  the architecture snapshot from a frozen reference doc.
- Worker `decision`: `write_360_memory(entry_type="decision", ...)` to record
  "chose Postgres JSONB over a separate audit table — rationale: tenant scoping".
- Worker `architecture`: `write_360_memory(entry_type="architecture", ...)` to
  capture a new layered boundary (e.g. EventBus introduced between CE and SaaS).
- Worker `discovery`: `write_360_memory(entry_type="discovery", ...)` for a
  surprising finding (e.g. "Alembic skips offline migrations on PG18 boot").
- Orchestrator `action_required`: `write_360_memory(entry_type="action_required", ...)`
  to flag a deferred follow-up that future agents must pick up.

Use `discovery` for one-off findings worth remembering; use `action_required`
only when the entry MUST trigger future work (orchestrator-only).
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
1. Send: `send_message(to_agents=["<orchestrator-uuid>"], content="REQUEST_CONTEXT: <specific need>", from_agent="{executor_id}", project_id="...", message_type="direct", requires_action=true)`
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
"""  # noqa: S608 — prose protocol template, not SQL
    return protocol_framing + body


def _generate_agent_protocol(
    job_id: str,
    tenant_key: str,
    agent_name: str,
    agent_id: str | None = None,
    execution_mode: str = "multi_terminal",
    git_integration_enabled: bool = False,
    job_type: str = "agent",
    tool: str = "multi_terminal",
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

    # Handover 0830/0851: Orchestrator protocol fork — 3-phase coordination lifecycle
    if job_type == "orchestrator":
        return _generate_orchestrator_protocol(job_id, tenant_key, executor_id, execution_mode)

    git_commit_block, gil_add_block = _build_conditional_blocks(git_integration_enabled, execution_mode, tool)

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

    return _build_worker_protocol_body(
        job_id=job_id,
        tenant_key=tenant_key,
        executor_id=executor_id,
        job_type=job_type,
        phase1_step4=phase1_step4,
        git_commit_block=git_commit_block,
        gil_add_block=gil_add_block,
        protocol_framing=protocol_framing,
    )
