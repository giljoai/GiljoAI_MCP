# Handover 0111: WebSocket Real-Time Updates & Orchestrator ID Bug

**Date**: 2025-01-06
**Status**: 📋 INVESTIGATION NEEDED
**Priority**: High
**From**: Handover 0109 testing
**Estimated Effort**: 3-4 hours

---

## Executive Summary

Two critical bugs discovered during Handover 0109 testing:

1. **WebSocket broadcasts don't work from MCP tool context** - Mission and agent cards don't appear in UI without page refresh
2. **Orchestrator ID changes on every "Stage Project" click** - ID should be stable, created once at project activation

Both issues prevent a smooth user experience and need architectural investigation.

---

## Issue 1: WebSocket Broadcasts from MCP Context

### Problem

**What's Broken:**
- Orchestrator calls `update_project_mission()` via MCP ✅
- Mission saves to database ✅
- WebSocket broadcast FAILS ❌
- UI doesn't update (mission panel stays blank) ❌
- Same issue for `spawn_agent_job()` - agent cards don't appear ❌

**Expected Behavior:**
- Mission appears in "Orchestrator Created Mission" panel
- Loading spinner shows during staging
- Agent cards appear in real-time as they're spawned
- "Just Added" badges on new agent cards

**Actual Behavior:**
- Data saves to database correctly
- No WebSocket events fire
- User must refresh page to see changes

### Root Cause Analysis

**Code Location**: `src/giljo_mcp/tools/project.py:380-436`

```python
# WebSocket broadcast code EXISTS
from api.app import state
ws_manager = getattr(state, "websocket_manager", None)
if ws_manager:
    # This code runs...
    sent_count = await ws_dep.broadcast_to_tenant(...)
    logger.info(f"Mission update broadcasted to {sent_count} clients")
else:
    logger.debug("WebSocket manager not available")  # THIS fires
```

**The Problem:**
- MCP tools run in `tool_accessor.py` context
- `state.websocket_manager` is NOT available in that context
- HTTP request context (where WebSocket manager lives) is separate
- Silent failure - no errors, just no broadcast

### Evidence

**Test Log Analysis** (from Handover 0109):
- Searched for "websocket\|broadcast\|Mission update" in `logs/api_stdout.log`
- NO broadcast logs found
- Means `ws_manager` was None

**Why It Works in HTTP Endpoints:**
- `api/endpoints/projects.py` has access to `state.websocket_manager`
- MCP tools (`src/giljo_mcp/tools/`) do NOT

### Files Affected

**Backend:**
- `src/giljo_mcp/tools/project.py` - update_project_mission (line 380-436)
- `src/giljo_mcp/tools/orchestration.py` - spawn_agent_job (similar issue)
- Any other MCP tool that tries to broadcast WebSocket events

**Frontend:**
- `frontend/src/components/projects/LaunchTab.vue` (line 831) - Listening for events that never fire
- `frontend/src/components/projects/JobsTab.vue` - Agent card updates

### Impact

**User Experience:**
- Medium severity - data saves correctly but UI feels broken
- Confusing - users think staging failed
- Workaround exists (page refresh) but not obvious

**Workaround:**
1. Orchestrator completes staging successfully
2. User refreshes browser page
3. Mission and agent cards appear

---

## Issue 2: Orchestrator ID Changes on "Stage Project" Click

### Problem

**What's Broken:**
- User activates project → orchestrator job created with ID `abc-123` ✅
- LaunchTab shows "Orchestrator ID: abc-123" on agent card ✅
- User clicks "Stage Project" button
- Orchestrator ID changes to `def-456` ❌
- Each click generates a NEW ID ❌

**Expected Behavior:**
- Orchestrator job created ONCE at project activation
- ID remains stable throughout project lifecycle
- "Stage Project" button just copies the prompt (no new job)

**Actual Behavior:**
- Each "Stage Project" click creates new orchestrator job
- ID increments: `#1`, `#2`, `#3`, etc.
- Old orchestrator jobs left behind in database

### Investigation Needed

**Questions:**
1. Where does "Stage Project" button call backend?
   - File: `frontend/src/components/projects/LaunchTab.vue`
   - Method: Look for `@click="stageProject"` or similar

2. What endpoint does it hit?
   - Possibly `POST /api/v1/projects/{id}/orchestrator`?
   - Or prompts endpoint creates orchestrator as side effect?

3. Does it call `/activate` again?
   - Line 765 in `api/endpoints/projects.py` creates orchestrator
   - Line 777: `if not existing_orchestrator:` should prevent duplicates
   - Why isn't this check working?

4. Is there a race condition?
   - Multiple clicks in quick succession?
   - Async session not flushing before check?

### Code to Investigate

**Backend:**
```python
# api/endpoints/projects.py:765-804
# This SHOULD create orchestrator only once
existing_orch_stmt = select(MCPAgentJob).where(
    MCPAgentJob.project_id == project_id,
    MCPAgentJob.agent_type == "orchestrator",
    MCPAgentJob.tenant_key == current_user.tenant_key,
)
existing_orchestrator = existing_orch_result.scalar_one_or_none()

if not existing_orchestrator:  # Why does this fail?
    # Create orchestrator job
    orchestrator_job = MCPAgentJob(...)
```

**Frontend:**
- Find "Stage Project" button click handler
- Check if it's calling `/activate` or `/orchestrator` endpoint
- See if it's creating orchestrator as side effect

### Impact

**User Experience:**
- High severity - creates database clutter
- Confusing - orchestrator ID keeps changing
- Potential bugs - which orchestrator is "real"?

**Database:**
- Orphaned orchestrator jobs accumulate
- Clutters mcp_agent_jobs table
- May cause issues with mission persistence

---

## Implementation Plan

### Phase 1: Investigation (Fresh Agent)

**Tasks:**
1. Trace "Stage Project" button flow (frontend → backend)
2. Identify exact endpoint that creates duplicate orchestrators
3. Check if `/activate` is called multiple times
4. Analyze orchestrator creation logic for race conditions
5. Document findings with code snippets

**Deliverables:**
- Investigation report with code locations
- Root cause explanation
- Reproduction steps

### Phase 2: Fix Orchestrator ID Bug

**Tasks:**
1. Fix duplicate orchestrator creation
2. Ensure `existing_orchestrator` check works correctly
3. Add unique constraint if missing (DB level)
4. Add frontend debounce if needed (prevent double-clicks)

**Testing:**
- Click "Stage Project" 10 times rapidly
- Verify only ONE orchestrator job exists
- Verify ID remains stable

### Phase 3: Fix WebSocket Broadcasts

**Tasks:**
1. Refactor WebSocket access for MCP context
2. Options:
   - A) Pass WebSocket manager to tool_accessor
   - B) Use event bus pattern (publish/subscribe)
   - C) Create separate WebSocket broadcast service
3. Update all affected MCP tools
4. Test real-time UI updates

**Testing:**
- Orchestrator saves mission → mission appears without refresh
- Orchestrator spawns agents → cards appear in real-time
- Loading spinner works correctly

---

## Success Criteria

**Must Have:**
- ✅ Orchestrator ID stable across multiple "Stage Project" clicks
- ✅ No duplicate orchestrator jobs in database
- ✅ Mission appears in UI without page refresh
- ✅ Agent cards appear in real-time
- ✅ WebSocket broadcasts work from MCP tools

**Nice to Have:**
- ✅ Loading spinner during staging
- ✅ "Just Added" badges on new agent cards
- ✅ Smooth animations for card appearance

---

## Related Handovers

- **0109**: Agent Lifecycle Implementation (where bugs were discovered)
- **0080**: Orchestrator Succession (orchestrator job creation)
- **0086**: WebSocket Integration (original WebSocket implementation)

---

## Notes for Fresh Agent

**Database Reset Performed:**
- Project `ce9015f5-d521-449c-9a89-66a9055436c8` cleaned
- All agent jobs deleted (20 removed)
- Mission cleared
- Ready for clean test

**Testing Environment:**
- Dev mode active
- Can create/delete test data freely
- Test with actual orchestrator on remote laptop

**Key Files to Read:**
1. `api/endpoints/projects.py` (lines 703-824) - Project activation
2. `api/endpoints/prompts.py` - Staging prompt generation
3. `frontend/src/components/projects/LaunchTab.vue` - "Stage Project" button
4. `src/giljo_mcp/tools/project.py` - update_project_mission WebSocket code

---

**Status**: Ready for fresh agent investigation
**Assigned**: Not yet
**Created By**: Orchestrator (patrik-test)
**Date**: 2025-01-06 22:30
