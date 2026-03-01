# Handover 0497e: Fresh Agent Recovery Flow (Successor Spawning)

**Date:** 2026-02-25
**From Agent:** Research/Architecture Session
**To Agent:** system-architect + tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 4-6 hours
**Status:** COMPLETE (2026-02-25)
**Chain:** 0497a → 0497b → 0497c → 0497d → **0497e** (Multi-Terminal Production Parity)
**Depends On:** 0497b (result storage) + 0497c (orchestrator prompt knows about spawning)

## Task Summary

When a tester or any agent finds problems with a completed agent's work, the orchestrator needs to spawn a fresh successor agent with a new job that says "read the predecessor's work and fix the issues." This handover defines the recovery flow: fresh context window, new AgentJob + AgentExecution, mission that references predecessor's completion result + git commits.

## Context and Background

### Why Fresh Session, Not Continue
- Context fog (200K token budget exhaustion, multiple compactions) makes continued sessions unreliable
- A fresh agent with a clear mission starts clean
- Git history IS the source of truth for what was done
- The predecessor's stored completion result (0497b) provides structured summary
- Fresh context = no accumulated hallucinations or drift

### The Flow
```
1. Tester finds problem → messages orchestrator
2. Orchestrator receives message via receive_messages()
3. Orchestrator spawns new agent via spawn_agent_job():
   - agent_name = same template as predecessor (e.g., "tdd-implementor")
   - agent_display_name = unique name (e.g., "Implementer 2")
   - mission = "Fix issues found by tester. Read predecessor's work first."
   - References predecessor's job_id for result lookup
4. New AgentJob + AgentExecution appear on dashboard (WebSocket event)
5. New play button appears in Jobs tab
6. Orchestrator tells user: "Implementer 2 has been spawned. Copy its prompt from the Jobs tab and paste into a new terminal."
7. User copies prompt → pastes into new terminal
8. New agent calls get_agent_mission() → receives mission with predecessor reference
9. New agent calls get_agent_result(predecessor_job_id) → reads what predecessor did
10. New agent reads git log if git enabled → sees predecessor's commits
11. New agent fixes the issues
```

### What Already Exists
- `spawn_agent_job()` already works for runtime spawning (not just staging)
- WebSocket broadcasts `agent:created` event — UI updates automatically
- `shouldShowLaunchAction()` (via `shouldShowCopyButton()` in JobsTab.vue) shows play buttons for **ALL agents in multi-terminal mode** regardless of status — successor agents get a play button immediately
- The orchestrator prompt (0497c) already instructs about spawning new agents

### What's Missing
- No `get_agent_result()` MCP tool to read predecessor's completion data (0497b adds this)
- No standardized mission template for "successor" agents
- No guidance in the successor's mission about WHERE to find predecessor data
- The orchestrator needs to craft the right mission when spawning

### Design Constraints
- **Token budget:** Predecessor context injection (summary + commits + boilerplate) should be capped. Impose a **2000 character limit** on `result.get("summary")` with truncation + `[TRUNCATED]` marker. Cap commits list to last 10 entries. Estimated overhead: 300-800 tokens per successor spawn, well within 200K context budget.
- **Single-depth predecessor only:** This is single-depth by design — successor C references predecessor B only, not B's predecessor A. This is correct because B's completion result should summarize B's work including awareness of A. Deep recursive chains are unnecessary and would add complexity.
- **`tool_accessor.py` pattern note:** The existing `tool_accessor.spawn_agent_job()` already omits `context_chunks` from its MCP-facing interface (selective parameter filtering). Adding `predecessor_job_id` follows this established pattern.

## Technical Details

### Files to Modify

**`src/giljo_mcp/services/orchestration_service.py`** — Enhance `spawn_agent_job()`:

Add an optional `predecessor_job_id` parameter:
```python
async def spawn_agent_job(
    self,
    agent_display_name: str,
    agent_name: str,
    mission: str,
    project_id: str,
    tenant_key: str,
    parent_job_id: Optional[str] = None,
    context_chunks: Optional[list[str]] = None,
    phase: Optional[int] = None,
    predecessor_job_id: Optional[str] = None,  # NEW: for recovery spawns
) -> SpawnResult:
```

When `predecessor_job_id` is provided:
1. Validate the predecessor job exists and belongs to the same project + tenant
2. Fetch predecessor's completion result from `AgentExecution.result` (added by 0497b)
3. **Truncate** the summary to 2000 characters and commits list to 10 entries
4. Prepend a "PREDECESSOR CONTEXT" section to the mission:
```
## PREDECESSOR CONTEXT
You are replacing a previous agent who completed their work but issues were found.

Previous Agent: {predecessor.agent_display_name} (job_id: {predecessor.job_id})
Completion Summary: {predecessor_result.get("summary", "No summary available")}
Commits: {predecessor_result.get("commits", ["No commits recorded"])}

Your task: Read the predecessor's work, understand what was done, then fix the issues described in your mission below.

If git integration is enabled, run `git log --oneline -10` to see recent commits.
If you need more detail, call `mcp__giljo-mcp__get_agent_result(job_id="{predecessor.job_id}", tenant_key="{tenant_key}")`.

---
{original_mission}
```

**`src/giljo_mcp/tools/tool_accessor.py`** — Expose new tools:
1. `get_agent_result(job_id, tenant_key)` — reads completion result from 0497b
2. Ensure `spawn_agent_job` accepts `predecessor_job_id` parameter pass-through

**`src/giljo_mcp/schemas/service_responses.py`** — Update `SpawnResult`:
- Add `predecessor_job_id: Optional[str] = None` field

**`api/endpoints/agent_jobs/models.py`** — Update `JobResponse`:
- Add `result: Optional[dict] = None` field so the frontend can display completion results

### Optional: `predecessor_job_id` Column on AgentJob
The current design stores predecessor reference only in the mission text (prepended context), not as a database column. If future queries like "find all successor jobs for job X" are needed, consider adding a nullable `predecessor_job_id` column to `AgentJob`. This is out of scope for this handover but worth tracking.

### Frontend Considerations (Future — Not in This Handover)
The frontend Jobs tab could show a "predecessor" link or badge on successor agents. This is a UI enhancement and should be a separate handover if desired. The backend support from this handover enables it.

## Implementation Plan

### Phase 1: Research (Read-Only)
1. Read `spawn_agent_job()` full signature and body
2. Read `tool_accessor.py` to understand how spawn parameters are exposed to MCP
3. Verify WebSocket `agent:created` event triggers UI update in Jobs tab
4. Confirm `shouldShowCopyButton()` shows play button for new waiting agents

### Phase 2: Write Tests (TDD)
1. Test `spawn_agent_job()` with `predecessor_job_id` — mission includes predecessor context
2. Test predecessor context includes completion summary and commits
3. Test `predecessor_job_id` validated (must exist, same project, same tenant)
4. Test invalid `predecessor_job_id` raises ValidationError
5. Test `get_agent_result()` MCP tool returns stored result with tenant isolation
6. Test spawn without `predecessor_job_id` — existing behavior unchanged (regression)

### Phase 3: Implement Successor Spawning
1. Add `predecessor_job_id` parameter to `spawn_agent_job()`
2. Implement predecessor lookup and context injection
3. Pass through to MCP tool in `tool_accessor.py`
4. Add `get_agent_result` to tool_accessor.py and MCP registry

### Phase 4: End-to-End Validation
1. Stage project → complete an agent → spawn successor via orchestrator
2. Verify successor's mission contains predecessor context
3. Verify successor can call `get_agent_result()` to read predecessor data
4. Verify new agent appears on dashboard with play button

**Recommended Sub-Agents:** system-architect (design), tdd-implementor (implementation)

## Testing Requirements

### Unit Tests
- Spawn with predecessor: mission injection correctness
- Spawn without predecessor: regression (unchanged behavior)
- Predecessor validation: tenant isolation, existence checks
- get_agent_result: tenant isolation, missing data handling

### Integration Tests
- Full recovery flow: complete → spawn successor → verify context chain
- Orchestrator spawns successor via MCP tool → appears on dashboard

### Manual Testing
1. Stage project, launch agents
2. Complete one agent
3. Have orchestrator spawn successor with predecessor reference
4. Verify new play button appears
5. Copy and paste into new terminal
6. Verify successor can read predecessor's work

## Dependencies and Blockers
- **Hard dependency on 0497b**: `get_agent_result()` reads from the `result` column added in 0497b
- **Soft dependency on 0497c**: Orchestrator prompt tells the orchestrator it can spawn successors, but the MCP tool works regardless
- **Soft dependency on 0497d**: Git commit instructions make predecessor commits available, but flow works without git

## Success Criteria
- `spawn_agent_job()` accepts `predecessor_job_id` and injects predecessor context into mission
- `get_agent_result()` MCP tool allows any agent to read a completed agent's result
- Successor agents appear on dashboard with working play buttons
- Predecessor validation enforces tenant isolation and existence
- All existing spawn tests pass (no regression)

## Rollback Plan
- `predecessor_job_id` is optional — all existing callers unaffected
- `get_agent_result` is additive — removing it doesn't break existing tools
- `git revert` cleanly removes all additions

## Cascading Analysis
- **Downstream**: New optional parameter on spawn — backwards compatible
- **Upstream**: Reads from AgentExecution.result (added in 0497b) — read-only
- **Sibling**: Existing spawn callers unaffected (parameter is optional with default None)
- **Installation**: No `install.py` changes (0497b handles the migration)

---

## Completion Summary

### 2026-02-25 - Reconciliation Closeout
**Status:** COMPLETE

**Implementation commit:** `c6592915` feat(0497e): Successor spawning with predecessor context injection

**What was built:**
- `spawn_agent_job()` accepts `predecessor_job_id` parameter
- Predecessor context (completion result + git commits) injected into successor mission
- `get_agent_result()` MCP tool allows any agent to read a completed agent's result
- Successor agents appear on dashboard with working play buttons via WebSocket broadcast
- Predecessor validation enforces tenant isolation and existence
