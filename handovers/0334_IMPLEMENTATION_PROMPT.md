# Handover 0334 Implementation Prompt

## For: Fresh Agent Starting Implementation

---

## Your Mission

Implement Handover 0334: HTTP-Only MCP Consolidation. This handover consolidates incomplete work from handovers 0261, 0262, 0297, and 0333.

**Read the full handover first**: `handovers/0334_HTTP_ONLY_MCP_CONSOLIDATION.md`

---

## Context Summary

GiljoAI is **HTTP-only MCP** - no localhost stdio users exist. The stdio code paths are already disabled via stubs in `src/giljo_mcp/tools/__init__.py` (line 76: `register_orchestration_tools = _removed`). The remaining stdio tool implementations in `orchestration.py` are dead code.

### What's Already Done
- **0333**: Staging prompt is working (~50 lines, includes broadcast step)
- **0262 HTTP path**: `OrchestrationService.get_agent_mission()` implements full atomic job start with WebSocket events
- **0297 backend**: `report_progress(mode="todo")` works, persists to `job_metadata.todo_steps`
- **Stdio stubs**: Already raise `NotImplementedError` - no active users

### What Needs Implementation

| Task | File | Description |
|------|------|-------------|
| **Task 2** | `frontend/src/stores/projectTabs.js` | Fix Steps column data format mismatch |
| **Task 3** | `src/giljo_mcp/services/orchestration_service.py` | Enhance `get_agent_mission()` to return full protocol |

---

## Task 2: Fix Steps Column Data Format

**Problem**: API returns flat fields, UI expects nested object.

**Current API response**:
```json
{
  "steps_total": 5,
  "steps_completed": 3,
  "current_step": "Writing tests"
}
```

**UI expects** (in `JobsTab.vue`):
```javascript
agent.steps.completed  // undefined
agent.steps.total      // undefined
```

**Fix**: Add transformation in `frontend/src/stores/projectTabs.js` or `websocketIntegrations.js`:

```javascript
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

**Acceptance**:
- Steps column shows `3/5` format when TODO-style progress reported
- Shows `—` when no progress
- Updates in real-time via WebSocket

---

## Task 3: Enhance get_agent_mission() Response

**File**: `src/giljo_mcp/services/orchestration_service.py` (around line 410)

**Current**: Returns raw mission text + minimal metadata.

**Enhancement**: Add `full_protocol` field with 6-phase protocol embedded.

**Why**: CLI subagents spawned via Task tool receive thin prompts. They call `get_agent_mission()` but currently only get raw mission - no protocol, no lifecycle, no communication patterns.

**Add to the return dict** (after line ~558):

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
- Report plan: `report_progress(job_id, {{"mode": "todo", "total_steps": N, "completed_steps": 0, "current_step": "Planning"}})`

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
send_message(to_agents=["orchestrator"], content="...", project_id="{agent_job.project_id}")

**Check Messages**:
get_next_instruction(job_id="{agent_job_id}", agent_type="{agent_job.agent_type}", tenant_key="{tenant_key}")

**Report Error**:
report_error(job_id="{agent_job_id}", error="Description of blocker")

---

## Available MCP Tools

- complete_job(job_id, result) - Mark job complete
- report_progress(job_id, progress) - Update TODO progress
- report_error(job_id, error) - Pause job and escalate
- send_message(to_agents, content, project_id) - Send messages
- get_next_instruction(job_id, agent_type, tenant_key) - Check inbox
- get_workflow_status(project_id, tenant_key) - Monitor overall progress
"""

return {
    "success": True,
    "agent_job_id": agent_job_id,
    "agent_name": agent_job.agent_name or agent_job.agent_type,
    "agent_type": agent_job.agent_type,
    "mission": agent_job.mission or "",
    "full_protocol": protocol,  # NEW
    "project_id": str(agent_job.project_id),
    "estimated_tokens": len(protocol) // 4,
    "thin_client": True,
}
```

**Note**: The atomic job start semantics (setting `mission_acknowledged_at`, transitioning status `waiting` → `working`, emitting WebSocket events) are already implemented in the HTTP path. This enhancement just adds protocol documentation to the response.

---

## DO NOT Implement

- **Task 1 (Delete stdio code)**: Already disabled via stubs. The dead code in `orchestration.py` can be cleaned up later but is not blocking.
- **Task 4 (Documentation)**: Skip unless you have time after Tasks 2 & 3.

---

## Testing

### Unit Tests to Add
- `test_get_agent_mission_returns_full_protocol()` - Verify `full_protocol` field exists
- `test_steps_column_receives_nested_object()` - Verify transformation works

### Manual Verification
1. Stage a project with multiple agents
2. Call `get_agent_mission()` via HTTP MCP (`/mcp` endpoint)
3. Verify response includes `full_protocol` field
4. In Jobs tab, verify Steps column displays `0/N` initially
5. Call `report_progress(mode="todo", total_steps=5, completed_steps=2)`
6. Verify Steps column updates to `2/5`

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `frontend/src/stores/projectTabs.js` | TBD | Add steps data transformation |
| `src/giljo_mcp/services/orchestration_service.py` | ~410-560 | Add `full_protocol` to response |

---

## Acceptance Criteria

1. **Steps Column Working**: Shows `completed/total` format, updates in real-time
2. **Protocol Enhanced**: `get_agent_mission()` response includes `full_protocol` field with 6-phase protocol
3. **All Existing Tests Pass**: Don't break anything
4. **New Tests Added**: Cover the new functionality

---

## Commit Message Template

```
feat: Implement Handover 0334 - HTTP-only MCP consolidation

- Add steps data transformation for UI (0297 gap)
- Enhance get_agent_mission() with full protocol (0261 Task 3)
- Steps column now shows completed/total format
- CLI subagents receive complete 6-phase protocol

Closes: 0334, 0297 (partial), 0261 (Task 3)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

**Start with Task 2 (Steps column)** - it's smaller and gives you quick feedback. Then move to Task 3.
