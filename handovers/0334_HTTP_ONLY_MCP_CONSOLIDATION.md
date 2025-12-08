# Handover 0334: HTTP-Only MCP Consolidation

## Status: READY FOR IMPLEMENTATION
## Priority: HIGH
## Type: Architecture Cleanup + Feature Completion
## Consolidates: 0261 (partial), 0262 (partial), 0297 (partial), 0333 (complete)

---

## Executive Summary

This handover consolidates incomplete work from handovers 0261, 0262, 0297, and 0333 into a single focused cleanup. The core decision: **GiljoAI is HTTP-only MCP** - no localhost stdio users exist, so all stdio-specific code paths should be removed.

### Handover Status Assessment

| Handover | Status | What's Done | What's Left |
|----------|--------|-------------|-------------|
| **0333** | COMPLETE | Staging prompt simplified (~50 lines), broadcast step restored | Nothing |
| **0262** | PARTIAL | HTTP path implements atomic job start | Stdio path incomplete (REMOVE instead of fix) |
| **0297** | PARTIAL | Backend TODO mode complete, WebSocket events working | Steps column UI data format mismatch |
| **0261** | SUPERSEDED | Staging prompt via 0333 | `get_agent_mission()` protocol enhancement (Task 3) |

### Architecture Decision

**HTTP-only MCP Transport**:
- All clients connect via HTTP MCP (`/mcp` JSON-RPC endpoint)
- `X-API-Key` authentication on every request
- `OrchestrationService` handles all business logic with WebSocket events
- Stdio/FastMCP path is dead code - remove it

---

## Tasks

### Task 1: Remove Stdio MCP Code Paths

**Files to modify**:

#### `src/giljo_mcp/tools/orchestration.py`

The stdio path at lines 491-589 (`register_orchestration_tools/get_agent_mission`) has incomplete atomic job start:
- Sets `mission_acknowledged_at` timestamp
- MISSING: Status transition `waiting` → `working`
- MISSING: WebSocket events

**Action**: Remove the entire stdio tool registration block since HTTP path (`OrchestrationService.get_agent_mission()`) handles everything correctly.

Search for all `@mcp.tool()` decorators and remove the stdio-specific implementations that duplicate HTTP service layer functionality.

#### `src/giljo_mcp/__main__.py`

Remove stdio server startup code if it exists.

#### `src/giljo_mcp/mcp_adapter.py`

Review and remove stdio transport adapter code.

#### Other files with `stdio` references:
- `src/giljo_mcp/tools/agent_messaging.py`
- `src/giljo_mcp/tools/__init__.py`
- `src/giljo_mcp/agent_message_queue.py`
- `src/giljo_mcp/auth_manager.py`

**Verification**: After removal, `grep -r "stdio" src/giljo_mcp/` should return no results.

---

### Task 2: Fix Steps Column Data Format (0297 Gap)

**Problem**: API returns flat fields, UI expects nested object.

**API Response** (current):
```json
{
  "job_id": "...",
  "steps_total": 5,
  "steps_completed": 3,
  "current_step": "Writing tests"
}
```

**UI Expectation** (JobsTab.vue):
```javascript
agent.steps.completed  // undefined - no nested object
agent.steps.total      // undefined
```

**Files to modify**:
- `frontend/src/stores/projectTabs.js` - Add transformation when processing job data
- OR `api/endpoints/projects/jobs.py` - Return nested `steps` object

**Recommended fix** (frontend transformation):
```javascript
// In projectTabs.js or websocketIntegrations.js
function transformJobData(job) {
  return {
    ...job,
    steps: {
      total: job.steps_total || 0,
      completed: job.steps_completed || 0,
      current: job.current_step || null
    }
  };
}
```

**Acceptance Criteria**:
- Steps column shows `3/5` format when TODO-style progress reported
- Shows `—` when no progress reported
- Updates in real-time via WebSocket

---

### Task 3: Enhance `get_agent_mission()` Response (0261 Task 3)

**File**: `src/giljo_mcp/services/orchestration_service.py`

**Current**: Returns raw mission text + minimal metadata.

**Enhanced**: Return full agent protocol embedded in response.

**Current response** (lines 520-558):
```python
return {
    "success": True,
    "agent_job_id": agent_job_id,
    "agent_name": agent_job.agent_type,
    "agent_type": agent_job.agent_type,
    "mission": agent_job.mission or "",
    "project_id": str(agent_job.project_id),
    "estimated_tokens": estimated_tokens,
    "thin_client": True,
}
```

**Enhanced response**:
```python
# Build complete agent protocol
protocol = f"""# Agent Mission: {agent_job.agent_name or agent_job.agent_type}

**Agent Type**: {agent_job.agent_type}
**Job ID**: {agent_job_id}
**Project ID**: {agent_job.project_id}

---

## Your Mission

{agent_job.mission}

---

## 6-Phase Protocol

### Phase 1: ACKNOWLEDGE (Automatic)
This call has already acknowledged your job. Your status is now "working".

### Phase 2: ANALYZE
- Understand mission requirements
- Identify dependencies on other agents
- Check `get_workflow_status(project_id, tenant_key)` if blocked

### Phase 3: PLAN
- Break mission into concrete TODO steps
- Report plan via: `report_progress(job_id, {{"mode": "todo", "total_steps": N, "completed_steps": 0, "current_step": "Planning"}})`

### Phase 4: EXECUTE
- Implement your mission
- Update progress: `report_progress(job_id, {{"mode": "todo", "total_steps": N, "completed_steps": k, "current_step": "description"}})`

### Phase 5: VERIFY
- Test your work
- Ensure quality standards met

### Phase 6: COMPLETE
- Call: `complete_job(job_id, {{"summary": "...", "files_modified": [...]}})`

---

## Communication

**Message Orchestrator**:
```python
send_message(to_agents=["orchestrator"], content="...", project_id="{agent_job.project_id}")
```

**Check Messages**:
```python
get_next_instruction(job_id="{agent_job_id}", agent_type="{agent_job.agent_type}", tenant_key="{tenant_key}")
```

**Report Error**:
```python
report_error(job_id="{agent_job_id}", error="Description of blocker")
```

---

## Available MCP Tools

- `complete_job(job_id, result)` - Mark job complete
- `report_progress(job_id, progress)` - Update TODO progress
- `report_error(job_id, error)` - Pause job and escalate
- `send_message(to_agents, content, project_id)` - Send messages
- `get_next_instruction(job_id, agent_type, tenant_key)` - Check inbox
- `get_workflow_status(project_id, tenant_key)` - Monitor overall progress
"""

return {
    "success": True,
    "agent_job_id": agent_job_id,
    "agent_name": agent_job.agent_name or agent_job.agent_type,
    "agent_type": agent_job.agent_type,
    "mission": agent_job.mission or "",
    "full_protocol": protocol,  # NEW: Complete ready-to-execute instructions
    "project_id": str(agent_job.project_id),
    "estimated_tokens": len(protocol) // 4,
    "thin_client": True,
}
```

**Why**: CLI subagents spawned via Task tool receive thin prompts. They call `get_agent_mission()` to fetch instructions. The current response only has raw mission - agent doesn't know the 6-phase protocol, communication patterns, or available tools.

**Note**: The atomic job start semantics (setting `mission_acknowledged_at`, transitioning status, emitting WebSocket events) are already implemented in the HTTP path. This enhancement adds protocol documentation to the response.

---

### Task 4: Update Documentation

**Files**:
- `CLAUDE.md` - Update "HTTP-only MCP" section to clarify stdio is removed
- `docs/ORCHESTRATOR.md` - Add protocol enhancement details

---

## Files Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/giljo_mcp/tools/orchestration.py` | Remove stdio tool implementations | ~100 lines removed |
| `src/giljo_mcp/__main__.py` | Remove stdio startup | TBD |
| `src/giljo_mcp/mcp_adapter.py` | Remove stdio adapter | TBD |
| `src/giljo_mcp/services/orchestration_service.py` | Enhance `get_agent_mission()` response | ~50 lines added |
| `frontend/src/stores/projectTabs.js` | Add steps data transformation | ~10 lines |
| `CLAUDE.md` | Update architecture note | ~5 lines |

---

## Testing

### Unit Tests
- [ ] `test_get_agent_mission_returns_full_protocol()`
- [ ] `test_steps_column_receives_nested_object()`

### Integration Tests
- [ ] `test_http_mcp_get_agent_mission()` - Verify WebSocket events emitted
- [ ] `test_steps_column_updates_realtime()` - WebSocket → UI

### Manual Verification
1. Stage a project with multiple agents
2. Spawn subagents
3. Call `get_agent_mission()` via HTTP MCP
4. Verify response includes `full_protocol` field
5. Verify Steps column displays `0/N` initially
6. Call `report_progress(mode="todo", ...)`
7. Verify Steps column updates to `k/N`

---

## Acceptance Criteria

1. **Stdio Removed**: `grep -r "stdio" src/giljo_mcp/` returns no results
2. **Steps Column Working**: Shows `completed/total` format, updates in real-time
3. **Protocol Enhanced**: `get_agent_mission()` response includes 6-phase protocol
4. **All Tests Pass**: Existing tests + new tests
5. **HTTP MCP Unchanged**: All existing HTTP MCP functionality works

---

## Related Handovers

- **0261**: CLI Implementation Prompt (Task 3 protocol enhancement - now here)
- **0262**: Agent Mission Protocol Merge (HTTP path complete, stdio removed instead of fixed)
- **0297**: UI Message Status & Job Signaling (Steps column gap - now here)
- **0333**: Staging Prompt Architecture Correction (complete, broadcast step restored)
- **0260**: Claude Code CLI Toggle Enhancement (toggle working, implementation prompt TBD)

---

## Notes for Implementer

### Why Remove Stdio Instead of Fixing?

The stdio MCP path was designed for localhost CLI users running `python -m giljo_mcp` directly. In practice:
- All production users connect via HTTP MCP
- HTTP path has full WebSocket support for real-time UI
- Maintaining two code paths creates duplication and bugs
- The incomplete stdio atomic job start is a symptom of this split

By removing stdio, we:
- Eliminate duplicate code
- Have single source of truth (OrchestrationService)
- Reduce maintenance burden
- Simplify testing

### Protocol Enhancement Trade-offs

**Pros**:
- CLI subagents get complete instructions in one call
- No need for agents to "know" the protocol beforehand
- Self-documenting - mission includes how to execute

**Cons**:
- Larger response (~1,000 tokens vs ~200 tokens)
- Protocol text repeated per agent

**Decision**: The pros outweigh the cons. Subagents need this information anyway.

---

## Estimated Effort

- Task 1 (Remove stdio): 2-3 hours
- Task 2 (Steps column): 1 hour
- Task 3 (Protocol enhancement): 2 hours
- Task 4 (Documentation): 30 minutes
- Testing: 1-2 hours

**Total**: 6-8 hours

---

**End of Handover 0334**
