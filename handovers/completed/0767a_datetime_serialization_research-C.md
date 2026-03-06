# Handover 0767a: Research — get_agent_mission() Datetime Serialization Bug

**Date:** 2026-03-04
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P1 (Critical)
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Chain:** 0767a (Research) -> 0767b (Fix)

---

## Task Summary

`get_agent_mission()` has an intermittent datetime serialization error. The first MCP call fails, but an immediate retry succeeds. This affects every agent's startup flow — it's the first tool call agents make after spawning. Your job is to find the root cause, trace the full runtime flow, and propose a fix.

---

## The Bug (from MCP Enhancement List #39)

- **What**: `get_agent_mission()` throws a datetime serialization error
- **When**: Intermittent — first call after agent spawn fails, retry succeeds
- **Impact**: Every spawned agent hits this. Wastes a tool call and causes a confusing error on startup
- **Suspected cause**: Likely a datetime/timestamp field in the response that isn't being serialized to ISO string before JSON encoding

---

## CRITICAL: Trace the Full Runtime Flow

**Lesson from 0766a**: Surface-level code reading is insufficient. You MUST trace the complete execution path from MCP tool call through to response serialization:

```
Agent calls MCP tool "get_agent_mission"
  -> mcp_http.py receives HTTP POST
  -> tool_map dispatches to tool_accessor.get_agent_mission()
  -> tool_accessor calls orchestration_service.get_agent_mission()
  -> service queries DB via SQLAlchemy ORM
  -> service builds response dict/model
  -> response serialized to JSON for MCP protocol
  -> WHERE DOES THE DATETIME FAIL TO SERIALIZE?
```

Pay special attention to:
1. **ORM model datetime fields** — SQLAlchemy returns `datetime` objects, not strings
2. **Response dict construction** — does the service put raw datetime objects into the response dict?
3. **JSON serialization** — Python's `json.dumps()` can't handle `datetime` objects by default
4. **Pydantic model serialization** — if using typed returns, Pydantic handles datetime automatically
5. **Why does retry work?** — is there session caching, lazy loading, or a race condition?

---

## Files to Investigate

### Primary (READ THESE BODIES)

| File | Symbol | Lines | What to Look For |
|------|--------|-------|------------------|
| `src/giljo_mcp/services/orchestration_service.py` | `OrchestrationService.get_agent_mission` | 952-1194 | The full method — find ALL datetime fields in the return value |
| `src/giljo_mcp/tools/tool_accessor.py` | `ToolAccessor.get_agent_mission` | 462-464 | Pass-through — does it transform the response? |
| `api/endpoints/mcp_http.py` | MCP tool dispatch handler | ~854-895 | How is the tool response serialized to JSON? Is there a `default=str` handler? |
| `src/giljo_mcp/models/agent_identity.py` | `AgentJob` model | Check all datetime columns | `created_at`, `updated_at`, `started_at`, etc. |
| `src/giljo_mcp/models/agent_identity.py` | `AgentExecution` model | Check all datetime columns | `started_at`, `completed_at`, `last_progress_at`, etc. |

### Secondary (CHECK FOR SERIALIZATION PATTERNS)

| File | What to Look For |
|------|------------------|
| `src/giljo_mcp/services/orchestration_service.py` | Search for `isoformat()`, `str()`, `json_serializable`, or datetime conversion patterns near `get_agent_mission` |
| `api/endpoints/mcp_http.py` | Search for `json.dumps`, `JSONResponse`, `default=str`, or custom JSON encoders |
| Any Pydantic response model used by `get_agent_mission` | Check if there's a typed return model (post-0731 typed returns series) |

---

## Research Tasks (Execute in Order)

### Task 1: Read get_agent_mission() Implementation
1. Read `OrchestrationService.get_agent_mission()` full body (lines 952-1194)
2. Identify EVERY field in the response dict/model
3. Flag which fields contain datetime objects vs strings
4. Check if there's any explicit datetime-to-string conversion

### Task 2: Read the Model Definitions
1. Read `AgentJob` model — list ALL datetime columns with their SQLAlchemy types
2. Read `AgentExecution` model — list ALL datetime columns
3. Check if any columns use `DateTime(timezone=True)` vs `DateTime` vs `TIMESTAMP`

### Task 3: Trace the Serialization Path
1. Read `ToolAccessor.get_agent_mission()` — does it transform the response?
2. Read the MCP HTTP handler in `mcp_http.py` — how does it serialize the tool response to JSON?
3. Look for `json.dumps()` calls — is there a `default=str` or custom encoder?
4. Check if the response goes through `JSONResponse()` (FastAPI auto-serializes datetime)
5. Check if there's a manual `json.dumps()` without datetime handling

### Task 4: Understand Why Retry Works
1. Could this be an ORM lazy-loading issue? (first access loads, second has cached data)
2. Could this be a session state issue? (first call hits an edge case in session management)
3. Could this be a race condition? (agent spawned but DB row not yet committed)
4. Search for any `await session.refresh()` or `session.expire_all()` patterns

### Task 5: Search for Similar Patterns
1. Search for other MCP tools that return datetime fields — do they have the same bug?
2. Search for `isoformat` across the services directory — is there a standard pattern?
3. Check if `get_orchestrator_instructions()` has the same issue (it returns similar data)

### Task 6: Propose Fix
Propose at least 2 approaches:
- **Where to fix** (model level? service level? serialization level?)
- **What to change** (specific code changes)
- **Backward compatibility** assessment
- **Estimated lines of code**
- **Recommended approach** and why

---

## Chain Log Instructions

### Step 1: Mark Session Started
Read and update `F:\GiljoAI_MCP\prompts\0767_chain\chain_log.json`:
- Set `0767a.status` to `"in_progress"`
- Set `0767a.started_at` to current ISO timestamp

### Step 2: Execute Research Tasks (above)

### Step 3: Write Findings to Chain Log
Update `0767a` in chain_log.json with:
```json
{
  "findings": {
    "bug_confirmed": true/false,
    "root_cause": "description of the exact cause",
    "failing_field": "which datetime field fails",
    "serialization_path": "description of how response gets serialized",
    "why_retry_works": "explanation",
    "affected_datetime_fields": ["field1", "field2"],
    "other_tools_affected": ["tool1", "tool2"],
    "proposed_fixes": [
      {
        "name": "Approach A",
        "where": "file:line",
        "what": "description",
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

- [ ] Root cause of the datetime serialization error identified with code evidence
- [ ] Full serialization path traced (MCP call -> response)
- [ ] Explanation of why retry succeeds
- [ ] All datetime fields in get_agent_mission response catalogued
- [ ] Check if other MCP tools have the same issue
- [ ] At least 2 fix approaches proposed
- [ ] Findings written to chain_log.json

## DO NOT
- Do NOT implement any fixes — research only
- Do NOT modify any source code files
- Do NOT create commits
- Do NOT spawn the next terminal

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0767_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
- Feb Report Section 6: `F:\GiljoAI_MCP\handovers\Handover_report_feb.md`
