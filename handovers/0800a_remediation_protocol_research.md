# Handover 0800a: Research — Remediation Agent Protocol Gap Analysis (#38)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P1
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Chain:** 0800a (Research) -> 0800b (Fix)

---

## Task Summary

Enhancement #38: "Remediation Agent Spawning Protocol." The MCP server already has TWO enforcement gates:

1. **`COMPLETION_BLOCKED`** — agents cannot mark themselves complete unless all messages are read and all todos are done (`complete_job()` in `orchestration_service.py`)
2. **`CLOSEOUT_BLOCKED`** — projects cannot close unless all agents are complete (`close_project_and_update_memory()` in `project_closeout.py`)

Your job is to trace the FULL end-to-end flow from agent completion through project closeout, identify what happens when these gates fire, and determine what remediation guidance is missing.

**Key constraint:** The MCP server is PASSIVE — it cannot spawn agents. It can only return responses with instructions. Any "remediation agent spawning" must happen on the client side (orchestrator deciding to respawn a Task tool subagent in CLI mode, or telling the user to paste a prompt in multi-terminal mode).

---

## The Two Enforcement Gates

### Gate 1: Agent Completion (`COMPLETION_BLOCKED`)

**File:** `src/giljo_mcp/services/orchestration_service.py`
**Symbol:** `OrchestrationService.complete_job` (lines ~1559-1807)

When an agent calls `complete_job()`, the system checks:
- Are there unread messages addressed to this agent? (`Message.status == "pending"` and `Message.to_agents.contains([agent_id])`)
- Are there incomplete todo items? (`AgentTodoItem.status != "completed"`)

If either: raises `ValidationError` with `error_code="COMPLETION_BLOCKED"` and reasons list.

### Gate 2: Project Closeout (`CLOSEOUT_BLOCKED`)

**File:** `src/giljo_mcp/tools/project_closeout.py`
**Symbol:** `close_project_and_update_memory` (lines ~35-230)
**Helper:** `_check_agent_readiness` (lines ~233-274)

When the orchestrator calls `close_project_and_update_memory()`, the system checks:
- Are all agents in "complete" or "decommissioned" status?
- If not: returns blockers list with agent_id, agent_name, status, job_id, messages_waiting

If blockers exist and `force=False`: raises `ProjectStateError` with `status: "CLOSEOUT_BLOCKED"`.

---

## Research Tasks (Execute In Order)

### Task 1: Trace the COMPLETION_BLOCKED Gate

1. Read `OrchestrationService.complete_job()` body (orchestration_service.py, use `find_symbol` with `include_body=True`)
2. Answer: What EXACTLY does the `COMPLETION_BLOCKED` response contain?
3. Answer: Does the response give the agent enough info to self-remediate? (e.g., "call receive_messages() first", "complete todo X first")
4. Answer: What happens if the agent IGNORES the error and just stays in "working" status forever?
5. Answer: Is there a timeout or staleness mechanism for agents that never complete?

### Task 2: Trace the CLOSEOUT_BLOCKED Gate

1. Read `close_project_and_update_memory()` full body (project_closeout.py)
2. Read `_check_agent_readiness()` full body
3. Answer: What EXACTLY does the `CLOSEOUT_BLOCKED` response contain?
4. Answer: Does it tell the orchestrator HOW to fix each blocker?
5. Answer: Does it differentiate between "agent is actively working" vs "agent is stuck/dead"?
6. Answer: Does it include the agent's unread message count or incomplete todo count?

### Task 3: Trace the Orchestrator's Closeout Instructions

1. Read `thin_prompt_generator.py` — `build_retirement_prompt()` (the retirement/context-exhaustion flow)
   - What does it tell orchestrators about handling agents that aren't complete?
   - Does it mention CLOSEOUT_BLOCKED at all?
2. Read `protocol_builder.py` — the COMPLETION section for orchestrators
   - `get_orchestrator_instructions()` or `build_orchestrator_prompt()` — find the closeout instructions
   - Does it tell orchestrators what to do when closeout is blocked?
3. Read `protocol_builder.py` — `build_multi_terminal_prompt()` (if it exists)
   - What does the multi-terminal orchestrator know about handling stuck agents?
   - Does it know it can tell the user to paste a prompt in the stuck agent's terminal?

### Task 4: Trace the Agent Protocol Instructions

1. Read `protocol_builder.py` — the agent completion instructions (Phase 4)
   - What are agents told about COMPLETION_BLOCKED?
   - Do they know they'll be rejected if messages are unread or todos incomplete?
2. Search for any "COMPLETION_BLOCKED" handling in protocol or prompt text
3. Answer: If an agent gets COMPLETION_BLOCKED, does it know what to do next?

### Task 5: Analyze the Two Execution Modes

**CLI Subagent Mode (Claude Code):**
1. Can the orchestrator call `complete_job()` on behalf of a stuck subagent? Or does tenant/auth block this?
2. Can the orchestrator call `receive_messages()` for another agent and then process those messages?
3. Can the orchestrator read another agent's todos and complete them?
4. If none of the above: what CAN the orchestrator do? Just `force=true`?

**Multi-Terminal Mode:**
1. Read `protocol_builder.py` multi-terminal prompt — what does the orchestrator know about reactivating agents?
2. Can the orchestrator generate a "paste this in agent X's terminal" instruction?
3. Does the system track which terminal an agent is running in? (Probably not)
4. What info would the user need to reactivate a stuck agent? (agent_id, job_id, what's pending)

### Task 6: Identify the Gaps

Based on Tasks 1-5, categorize what's missing:

**Category A — Agent self-remediation gaps:**
- Does the agent know about COMPLETION_BLOCKED before it tries?
- Does the error response give clear enough instructions?

**Category B — Orchestrator remediation gaps:**
- Does the orchestrator know what to do when CLOSEOUT_BLOCKED fires?
- Can it generate actionable instructions for the user (multi-terminal) or itself (CLI)?

**Category C — Response richness gaps:**
- Does CLOSEOUT_BLOCKED give enough detail? (agent names, what's pending, suggested actions)
- Should it include per-agent remediation steps?

**Category D — Missing features:**
- Is there a staleness/timeout mechanism for agents that never complete?
- Should the orchestrator prompt include explicit CLOSEOUT_BLOCKED handling instructions?
- Should CLOSEOUT_BLOCKED include a copy-paste reactivation prompt for multi-terminal mode?

---

## Chain Log Instructions

### Step 1: Mark Session Started
Read and update `F:\GiljoAI_MCP\prompts\0800_chain\chain_log.json`:
- Set `0800a.status` to `"in_progress"`
- Set `0800a.started_at` to current ISO timestamp

### Step 2: Execute Research Tasks (above)

### Step 3: Write Findings to Chain Log
Update `0800a` in chain_log.json with:
```json
{
  "findings": {
    "completion_blocked_gate": {
      "works": true/false,
      "response_quality": "sufficient/insufficient",
      "agent_knows_about_it": true/false,
      "self_remediation_possible": true/false,
      "gaps": ["..."]
    },
    "closeout_blocked_gate": {
      "works": true/false,
      "response_quality": "sufficient/insufficient",
      "orchestrator_knows_what_to_do": true/false,
      "differentiates_stuck_vs_working": true/false,
      "includes_remediation_steps": true/false,
      "gaps": ["..."]
    },
    "cli_mode_remediation": {
      "orchestrator_can_act_for_agent": true/false,
      "how": "description of what orchestrator can do",
      "gaps": ["..."]
    },
    "multi_terminal_remediation": {
      "orchestrator_can_guide_user": true/false,
      "reactivation_prompt_possible": true/false,
      "gaps": ["..."]
    },
    "overall_assessment": "by-design / partially-implemented / real-gap",
    "proposed_fixes": [
      {
        "name": "Fix name",
        "type": "protocol/response/instruction",
        "description": "...",
        "files_to_change": ["..."],
        "backward_compatible": true/false,
        "estimated_loc": 0,
        "recommended": true/false,
        "rationale": "..."
      }
    ]
  }
}
```

Also update: `tasks_completed`, `files_investigated`, `deviations`, `notes_for_next`, `summary`, `status: "complete"`, `completed_at`

---

## Success Criteria

- [ ] Traced COMPLETION_BLOCKED gate end-to-end (what agent sees, what it can do)
- [ ] Traced CLOSEOUT_BLOCKED gate end-to-end (what orchestrator sees, what it can do)
- [ ] Analyzed CLI subagent mode remediation capabilities
- [ ] Analyzed multi-terminal mode remediation capabilities
- [ ] Categorized gaps (A/B/C/D categories above)
- [ ] At least 2 fix approaches proposed (or documented as already-sufficient)
- [ ] Findings written to chain_log.json

## DO NOT
- Do NOT implement any fixes — research only
- Do NOT modify any source code files
- Do NOT create commits

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0800_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
- Coding Protocols: `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
- Feb Report: `F:\GiljoAI_MCP\handovers\Handover_report_feb.md` (Section 6, Enhancement #38)
