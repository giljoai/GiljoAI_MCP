# Handover 0800b: Implement — Remediation Protocol Enhancements (#38)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Implementation agent (tdd-implementor)
**Priority:** P1
**Estimated Complexity:** 1.5 hours
**Status:** Not Started
**Chain:** 0800a (Research COMPLETE) -> 0800b (Implementation)

---

## Task Summary

The research in 0800a confirmed: both COMPLETION_BLOCKED (agent can't complete) and CLOSEOUT_BLOCKED (project can't close) enforcement gates work correctly. But there is a **CRITICAL orchestrator instruction gap**: neither CLI nor multi-terminal orchestrator prompts include ANY handling for when closeout is blocked. The system blocks correctly, then leaves the orchestrator with no recovery path.

Four fixes needed across 3 files. All backward-compatible, no DB migrations. ~155 LOC total.

---

## Read Before Starting

1. Read the 0800a findings: `F:\GiljoAI_MCP\prompts\0800_chain\chain_log.json` (session 0800a findings)
2. Read coding protocols: `F:\GiljoAI_MCP\handovers\handover_instructions.md`

---

## Fix 1: CLI Orchestrator CLOSEOUT_BLOCKED Handling (~40 LOC)

### File: `src/giljo_mcp/thin_prompt_generator.py`
### Symbol: `_build_claude_code_execution_prompt` (lines ~1275-1546)

**Context:** This prompt is given to orchestrators running in Claude Code CLI subagent mode. Section 7 ("When You're Done") currently only covers the happy path: "Ensure all have status='complete'" — but has NO fallback for when they don't.

**What to add:** After the existing Section 7 completion instructions, add a new section for handling agents that are NOT complete. The retirement prompt (`build_retirement_prompt`, lines ~159-291) already demonstrates the full pattern — adapt it for normal closeout.

**The section should instruct the orchestrator to:**

1. Check `get_workflow_status()` — identify agents not in "complete" or "decommissioned" status
2. For each non-complete agent:
   - a. Drain their messages: `receive_messages(agent_id="<their_agent_id>", tenant_key="<tenant_key>")`
   - b. Process any actionable messages (respond, acknowledge)
   - c. If they have incomplete todos, update via `report_progress(job_id="<their_job_id>", todo_items=[...])` marking remaining items as "completed" or "skipped"
   - d. Force-complete: `complete_job(job_id="<their_job_id>", result={"summary": "Force-completed by orchestrator during closeout.", "status": "force_completed"})`
   - e. Do NOT call `complete_job()` on agents already in "complete" status
3. Skip agents in status "decommissioned"
4. After all agents are complete, proceed with normal closeout (write_360_memory, close_project_and_update_memory)

**Important:** Look at the existing `build_retirement_prompt()` STEP 2 (lines ~225-252) for the exact pattern. It already does drain-messages → update-todos → force-complete. Mirror that pattern but integrate it into the CLI orchestrator's closeout flow.

**Where to insert:** Find the Section 7 / "When You're Done" block in `_build_claude_code_execution_prompt()`. Add the new handling AFTER the happy-path instructions and BEFORE the "Handover" section.

---

## Fix 2: Multi-Terminal Orchestrator CLOSEOUT_BLOCKED Handling (~35 LOC)

### File: `src/giljo_mcp/thin_prompt_generator.py`
### Symbol: `_build_multi_terminal_orchestrator_prompt` (lines ~1548-1676)

**Context:** This prompt is given to orchestrators in multi-terminal mode. Section 5 ("Project Closeout") currently only covers the happy path: "When all agents show status 'complete'". No fallback.

**Key difference from CLI mode:** In multi-terminal mode, the orchestrator CANNOT act on behalf of agents (they're in separate terminals). The remediation must be USER-DIRECTED.

**The section should instruct the orchestrator to:**

1. Check `get_workflow_status()` — identify agents not in "complete" status
2. For each non-complete agent:
   - a. First try: Send them a message via `send_message(to_agents=["<agent_id>"], content="Please read all pending messages via receive_messages(), complete remaining TODO items, then call complete_job()")`
   - b. Wait ~30 seconds and re-check status
   - c. If agent is still not complete (terminal may be closed/dead): Tell the user:
     ```
     "Agent [name] (job_id: [id]) did not complete. Their terminal may be closed.
     To reactivate: Open a new terminal and run:
     claude --dangerously-skip-permissions "You are resuming agent work. Call mcp__giljo-mcp__get_agent_mission(job_id='[job_id]') to get your mission, then call receive_messages() to read pending messages, complete your TODO items, and call complete_job() when done."
     ```
3. After all agents respond or user intervenes, proceed with closeout

**Where to insert:** Find the Section 5 / "Project Closeout" block in `_build_multi_terminal_orchestrator_prompt()`. Add the non-complete handling AFTER the happy-path list and BEFORE any final sections.

---

## Fix 3: Enrich project_closeout.py CLOSEOUT_BLOCKED Response (~50 LOC)

### File: `src/giljo_mcp/tools/project_closeout.py`
### Symbol: `_check_agent_readiness` (lines ~233-274)

**Context:** The current blocker format is basic: `{agent_id, agent_name, status, job_id, messages_waiting}`. The `write_360_memory.py` implementation has a RICHER format with `issue_type` differentiation, todo counts, and item names. Make them consistent.

**Current code pattern (approximately):**
```python
blockers.append({
    "agent_id": execution.agent_id,
    "agent_name": execution.agent_name or execution.agent_display_name,
    "status": execution.status,
    "job_id": execution.job_id,
    "messages_waiting": execution.messages_waiting_count or 0,
})
```

**Change to include:**
1. Query incomplete todos for each blocking agent (same pattern used in `complete_job()`)
2. Add `issue_type` field: determine the PRIMARY reason this agent is blocking
   - `"still_working"` if status not in ("complete", "decommissioned")
   - `"unread_messages"` if messages_waiting > 0 (even if status is something else)
   - `"incomplete_todos"` if there are incomplete todos
3. Add `incomplete_todo_count` and `incomplete_todo_names` (up to 5 names)
4. Add `suggested_action` field per blocker (see Fix 4)

**You'll need to import and query AgentTodoItem** — look at how `complete_job()` does it (orchestration_service.py ~lines 1659-1672) for the exact query pattern.

**Also add a summary dict** to the ProjectStateError context:
```python
"summary": {
    "agents_checked": len(executions),
    "still_working": count_of_still_working,
    "with_unread_messages": count_with_unread,
    "with_incomplete_todos": count_with_incomplete,
}
```

---

## Fix 4: Per-Blocker Suggested Actions (~30 LOC)

### Files: `src/giljo_mcp/tools/project_closeout.py` AND `src/giljo_mcp/tools/write_360_memory.py`

**For project_closeout.py** (integrate into Fix 3's enriched blockers):

Add a `suggested_action` string field to each blocker entry based on `issue_type`:
- `"still_working"` → `"Send message to agent asking for status, or drain messages via receive_messages(agent_id='X') and force-complete via complete_job(job_id='Y')"`
- `"unread_messages"` → `"Agent has N unread messages. Drain via receive_messages(agent_id='X'), process, then complete_job(job_id='Y')"`
- `"incomplete_todos"` → `"Agent has N incomplete TODO items: [names]. Update via report_progress(job_id='Y', todo_items=[...]) marking as completed, then complete_job(job_id='Y')"`

**For write_360_memory.py** (add to existing blockers — currently they have `issue_type` but no `suggested_action`):

Search for where blockers are constructed in `_check_closeout_readiness()` and add the same `suggested_action` field using the same logic.

---

## Implementation Steps

1. Read `F:\GiljoAI_MCP\prompts\0800_chain\chain_log.json` — understand the findings
2. Read `src/giljo_mcp/thin_prompt_generator.py` — find `_build_claude_code_execution_prompt` and `_build_multi_terminal_orchestrator_prompt`
3. Read `build_retirement_prompt()` in the same file — this is your reference pattern for drain-and-complete
4. Apply Fix 1 (CLI CLOSEOUT_BLOCKED handling) — add section to `_build_claude_code_execution_prompt`
5. Apply Fix 2 (Multi-terminal CLOSEOUT_BLOCKED handling) — add section to `_build_multi_terminal_orchestrator_prompt`
6. Read `src/giljo_mcp/tools/project_closeout.py` — find `_check_agent_readiness`
7. Apply Fix 3 (enrich CLOSEOUT_BLOCKED response) — add issue_type, todo details, summary
8. Read `src/giljo_mcp/tools/write_360_memory.py` — find `_check_closeout_readiness` blocker construction
9. Apply Fix 4 (per-blocker suggested_action) — add to both files
10. Run test suite: `python -m pytest tests/ -x -q --timeout=30`
11. If tests pass, commit with message: `feat(0800b): Add orchestrator CLOSEOUT_BLOCKED remediation + enriched blocker responses`
12. Update chain_log.json with results

---

## Testing

### For Fixes 1-2 (prompt changes):
No new tests needed — these are prompt text additions. Verify by reading the generated prompts.

### For Fixes 3-4 (response enrichment):
Run `python -m pytest tests/ -x -q --timeout=30`. The existing closeout tests should still pass. The enriched response is a superset of the old format — backward compatible.

If there are specific closeout tests, look for them:
```
python -m pytest tests/ -k "closeout" -x -q --timeout=30
python -m pytest tests/ -k "close_project" -x -q --timeout=30
python -m pytest tests/ -k "agent_readiness" -x -q --timeout=30
```

---

## Success Criteria

- [ ] CLI orchestrator prompt includes CLOSEOUT_BLOCKED handling with drain-and-complete pattern
- [ ] Multi-terminal orchestrator prompt includes CLOSEOUT_BLOCKED handling with user-directed remediation
- [ ] `_check_agent_readiness()` returns enriched blockers with issue_type, todo details, summary
- [ ] Both CLOSEOUT_BLOCKED paths include per-blocker suggested_action
- [ ] All tests pass
- [ ] Chain_log.json updated
- [ ] Changes committed

## DO NOT
- Do NOT add staleness tracking or DB migrations — that's deferred
- Do NOT modify complete_job() COMPLETION_BLOCKED logic — it already works
- Do NOT change the actual CLOSEOUT_BLOCKED enforcement behavior — only enrich the response
- Do NOT create new files or modules
- Do NOT modify agent (non-orchestrator) prompts

## Reference Files
- 0800 Chain Log: `F:\GiljoAI_MCP\prompts\0800_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
- Coding Protocols: `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
