# Handover 0105d: MCP Tool Registration Fix

**Date**: 2025-11-06
**Status**: ✅ COMPLETE
**Priority**: CRITICAL
**Blocks**: Orchestrator mission persistence workflow

---

## Problem

Orchestrator #10 failed at Step 3 of startup sequence with error:
```
The update_project_mission tool doesn't exist
```

**Root Cause**: `update_project_mission` MCP tool was defined in codebase but **not registered** in HTTP API endpoint.

---

## Investigation

### Tool Exists in Multiple Places

1. **Tool Definition**: `src/giljo_mcp/tools/project.py:316`
   - Decorated with `@mcp.tool()`
   - Full implementation with WebSocket broadcast

2. **ToolAccessor Method**: `src/giljo_mcp/tools/tool_accessor.py:391`
   - Method exists: `async def update_project_mission(...)`

3. **HTTP API Mapping**: `api/endpoints/mcp_tools.py:61-108`
   - **MISSING** from `tool_map` dictionary
   - This dictionary routes HTTP requests to tool functions

### Why This Matters

**Architecture**: GiljoAI uses HTTP-based MCP adapter for multi-user support.

**Flow**:
1. Claude Code calls MCP tool via stdio
2. MCP adapter translates to HTTP request → `POST /mcp/tools/execute`
3. API server looks up tool in `tool_map` dictionary
4. Tool not found → 404 error → Orchestrator fails

---

## Fix Applied

**File**: `api/endpoints/mcp_tools.py`
**Line**: 68
**Change**: Added missing tool registration

```python
tool_map = {
    # Project tools
    "create_project": state.tool_accessor.create_project,
    "list_projects": state.tool_accessor.list_projects,
    "get_project": state.tool_accessor.get_project,
    "switch_project": state.tool_accessor.switch_project,
    "close_project": state.tool_accessor.close_project,
    "update_project_mission": state.tool_accessor.update_project_mission,  # ← ADDED
    # ... rest of tool_map
}
```

---

## Testing

### Verification Steps

1. ✅ Server restarted successfully
2. ✅ MCP health check returns `"tool_accessor": "ready"`
3. ✅ No startup errors in logs
4. ⏳ End-to-end orchestrator test (user to perform)

### Test Orchestrator Workflow

1. Activate project → Stage orchestrator
2. Copy thin prompt → Paste in Claude Code
3. Verify Steps 1-5 execute:
   - Step 1: Health check ✅
   - Step 2: Fetch mission ✅
   - Step 3: Persist mission ← **Should work now**
   - Step 4: Execute mission
   - Step 5: Coordinate agents

---

## Impact

**Before Fix**:
- Orchestrator failed at Step 3 (100% failure rate)
- Mission never appeared in LaunchTab UI
- Workflow blocked

**After Fix**:
- Orchestrator can persist mission to database
- LaunchTab displays mission via WebSocket
- Workflow unblocked

---

## Related Files

**Modified**:
- `api/endpoints/mcp_tools.py` (1 line added)

**Not Modified** (already correct):
- `src/giljo_mcp/tools/project.py` (tool definition exists)
- `src/giljo_mcp/tools/tool_accessor.py` (method exists)
- `src/giljo_mcp/thin_prompt_generator.py` (Step 3 instruction correct)

---

## Architectural Questions Answered

### Q1: Does prompt distinguish "STAGING" vs "EXECUTING"?

**Answer**: NO - Current architecture uses single prompt for both.

**Current Behavior**:
- User clicks "Stage Project" → Gets thin prompt
- Orchestrator executes Steps 1-5 in single session
- Step 3 persists mission (staging output)
- Steps 4-5 execute mission immediately

**Future Option**: Two-phase workflow would require:
- Prompt #1: "Stage Project" (Steps 1-3 only)
- Prompt #2: "Execute Project" (Steps 4-5 only)

### Q2: Do we have multiple things called "mission"?

**Answer**: YES - Terminology needs clarification.

**Current Usage**:
- `Project.mission` - User's high-level project vision (database field)
- `MCPAgentJob.mission` - Agent-specific condensed instructions (database field)
- "Mission" in workflow - Condensed plan fetched from MCP tool

**Suggested Definitions**:
- **Vision** = User's project description (Project.mission field)
- **Mission** = Orchestrator's condensed plan (context prioritization and orchestration applied)
- **Job** = Individual agent work assignment (MCPAgentJob record)
- **Task** = Sub-units of work within a job

### Q3: Was it just a broken tool or wrong prompt architecture?

**Answer**: Just a broken tool registration ✅

**Prompt Architecture is Correct**:
- 5-step sequence makes sense
- Thin client pattern properly implemented
- Only issue: Tool not registered in HTTP API

---

## Prevention

**Code Review Checklist**:
- [ ] When adding new MCP tool, verify:
  1. Tool defined with `@mcp.tool()` decorator
  2. Method exists in ToolAccessor class
  3. **Tool registered in `mcp_tools.py` tool_map**
  4. Tool listed in `/mcp/tools/list` endpoint (optional)

**Future Improvement**: Auto-generate tool_map from ToolAccessor methods to prevent manual registration gaps.

---

## Deployment

**Steps**:
1. ✅ Code change applied
2. ✅ Server restarted
3. ⏳ User testing required

**Rollback**: Revert line 68 in `api/endpoints/mcp_tools.py` (safe, no database changes)

---

**Fix Complete**: 2025-11-06
**Fixed By**: Orchestrator (patrik-test)
**Server Status**: Running on http://localhost:7272
**Ready for Testing**: YES ✅
