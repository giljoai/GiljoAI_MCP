# Handover 0378: Agent ID / Job ID Confusion and Message Tool Fixes

**Status**: Ready for Execution
**Priority**: High
**Estimated Effort**: 1-2 hours
**Risk Level**: Medium (affects agent communication)
**Complexity**: Low (parameter fixes and template correction)

---

## Executive Summary

### What
Fix three related bugs discovered during Claude Code CLI agent simulation testing:
1. `receive_messages()` rejects `tenant_key` parameter despite schema requiring it
2. `full_protocol` template incorrectly tells agents to use `job_id` as `agent_id` for messages
3. Inconsistent ID usage guidance causing agent communication failures

### Why
During alpha testing (2025-12-25), a simulated analyzer agent followed the `full_protocol` instructions exactly and encountered:
- `receive_messages(tenant_key=...)` threw "unexpected keyword argument" error
- Using the protocol-specified ID for messages returned "Agent execution not found"
- Only by ignoring the protocol and using the actual `agent_id` did messages work

This breaks the thin-client architecture where agents are supposed to follow `full_protocol` as the "single behavioral authority."

### Discovery Context
- Test project: TinyContacts
- Mode: Claude Code CLI
- Agent: analyzer (job_id: `448a9d6b-4f86-4b19-92fb-1c3bf597f176`)
- Actual agent_id: `3adca815-b453-40e9-8f17-31c66f7eae95`

---

## Bug Details

### Bug 1: `receive_messages()` AND `list_messages()` Reject `tenant_key`

**Reproduction (receive_messages):**
```python
mcp__giljo-mcp__receive_messages(
    agent_id="448a9d6b-4f86-4b19-92fb-1c3bf597f176",
    tenant_key="***REMOVED***"
)
```

**Error:**
```
Error executing receive_messages: ToolAccessor.receive_messages() got an unexpected keyword argument 'tenant_key'
```

**Reproduction (list_messages):**
```python
mcp__giljo-mcp__list_messages(
    tenant_key="***REMOVED***",
    limit=10
)
```

**Error:**
```
Error executing list_messages: ToolAccessor.list_messages() got an unexpected keyword argument 'tenant_key'
```

**Analysis:**
- MCP tool schema defines `tenant_key` as a parameter for BOTH tools
- Implementation does not accept `tenant_key` for EITHER tool
- Schema/implementation mismatch affects multiple messaging tools

**Location:** `src/giljo_mcp/tools/messaging.py` (likely)

---

### Bug 2: `full_protocol` Uses Wrong ID for Messages

**What `get_agent_mission()` returns:**
```json
{
  "agent_id": "3adca815-b453-40e9-8f17-31c66f7eae95",
  "job_id": "448a9d6b-4f86-4b19-92fb-1c3bf597f176"
}
```

**What `full_protocol` says:**
```markdown
**Your Identifiers:**
- job_id (work order): `448a9d6b-4f86-4b19-92fb-1c3bf597f176` - Use for mission, progress, completion
- agent_id (executor): `448a9d6b-4f86-4b19-92fb-1c3bf597f176` - Use for messages
```

**Problem:** Both identifiers show the same value (`job_id`). The `agent_id` line should show `3adca815-b453-40e9-8f17-31c66f7eae95`.

**Root Cause:** Template generation uses `{job_id}` placeholder for both lines instead of `{agent_id}` for the second line.

**Location:** `src/giljo_mcp/services/orchestration_service.py` - `_generate_agent_protocol()` function

---

### Bug 3: Message Function Fails with Protocol-Specified ID

**Using protocol-specified ID (job_id):**
```python
receive_messages(agent_id="448a9d6b-4f86-4b19-92fb-1c3bf597f176")
# Result: {"success": false, "error": "Agent execution 448a9d6b... not found"}
```

**Using actual agent_id:**
```python
receive_messages(agent_id="3adca815-b453-40e9-8f17-31c66f7eae95")
# Result: {"success": true, "messages": [...], "count": 1}
```

**Analysis:** The message system looks up agents by `agent_id`, not `job_id`. But the protocol tells agents to use `job_id` for everything.

---

## Fix Plan

### Fix 1: Update `receive_messages` Implementation

**Option A: Add tenant_key parameter (Recommended)**
```python
# In messaging.py
async def receive_messages(
    agent_id: str,
    tenant_key: str,  # ADD THIS
    exclude_progress: bool = True,
    exclude_self: bool = True,
    limit: int = 10,
    message_types: list[str] | None = None
) -> dict:
    # Add tenant validation
    # ... rest of implementation
```

**Option B: Remove tenant_key from schema**
If tenant isolation isn't needed for message retrieval, remove from MCP tool definition.

**Recommendation:** Option A - maintain consistency with other tools that require tenant_key.

---

### Fix 2: Correct `full_protocol` Template

**File:** `src/giljo_mcp/services/orchestration_service.py`

**Find in `_generate_agent_protocol()`:**
```python
**Your Identifiers:**
- job_id (work order): `{job_id}` - Use for mission, progress, completion
- agent_id (executor): `{job_id}` - Use for messages
```

**Replace with:**
```python
**Your Identifiers:**
- job_id (work order): `{job_id}` - Use for mission, progress, completion
- agent_id (executor): `{agent_id}` - Use for messages
```

**Also update all `receive_messages` examples in the protocol:**

**Before:**
```python
receive_messages(agent_id="{job_id}")
```

**After:**
```python
receive_messages(agent_id="{agent_id}", tenant_key="{tenant_key}")
```

---

### Fix 3: Update Protocol Message Check Instructions

**Current (incorrect):**
```markdown
- **MESSAGE CHECK**: Call `receive_messages()` after completing each TodoWrite task
  - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{job_id}")`
```

**Fixed:**
```markdown
- **MESSAGE CHECK**: Call `receive_messages()` after completing each TodoWrite task
  - Full call: `mcp__giljo-mcp__receive_messages(agent_id="{agent_id}", tenant_key="{tenant_key}")`
```

Apply this pattern to ALL `receive_messages` examples in the protocol (there are approximately 4 occurrences).

---

## Verification Checklist

### After Fix 1 (receive_messages tenant_key)
```python
# Should work without error
mcp__giljo-mcp__receive_messages(
    agent_id="3adca815-b453-40e9-8f17-31c66f7eae95",
    tenant_key="***REMOVED***"
)
```

### After Fix 2 & 3 (protocol template)
```python
# Get agent mission and verify identifiers section
response = mcp__giljo-mcp__get_agent_mission(agent_job_id="...", tenant_key="...")

# Verify in full_protocol:
# - agent_id line shows DIFFERENT value than job_id line
# - All receive_messages examples use agent_id, not job_id
# - All receive_messages examples include tenant_key parameter
```

### Integration Test
1. Spawn a test agent via `spawn_agent_job()`
2. Agent calls `get_agent_mission()`
3. Agent follows `full_protocol` EXACTLY as written
4. Agent successfully calls `receive_messages()` with protocol-specified parameters
5. No errors, messages retrieved successfully

---

## Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/messaging.py` | Add `tenant_key` parameter to `receive_messages()` |
| `src/giljo_mcp/services/orchestration_service.py` | Fix `_generate_agent_protocol()` to use `{agent_id}` for message instructions |

---

## Rollback Plan

### If receive_messages breaks
```bash
git checkout HEAD -- src/giljo_mcp/tools/messaging.py
```

### If protocol generation breaks
```bash
git checkout HEAD -- src/giljo_mcp/services/orchestration_service.py
```

---

## Success Criteria

- [ ] `receive_messages(agent_id=X, tenant_key=Y)` works without "unexpected argument" error
- [ ] `full_protocol` shows different values for `job_id` and `agent_id` identifiers
- [ ] All `receive_messages` examples in protocol use `{agent_id}` (not `{job_id}`)
- [ ] All `receive_messages` examples in protocol include `tenant_key` parameter
- [ ] Agent following protocol exactly can successfully retrieve messages
- [ ] Existing tests pass

---

## ID Usage Clarification (For Documentation)

After this fix, the correct ID usage is:

| Function | Use This ID | Why |
|----------|-------------|-----|
| `get_agent_mission()` | `job_id` (as `agent_job_id`) | Job is the work order |
| `acknowledge_job()` | `job_id` | Acknowledging the work order |
| `report_progress()` | `job_id` | Progress is on the work order |
| `complete_job()` | `job_id` | Completing the work order |
| `report_error()` | `job_id` | Error is on the work order |
| `receive_messages()` | `agent_id` | Messages are to/from the executor |
| `send_message()` | `agent_id` (as `from_agent`) | Messages are from the executor |

---

## Origin

Discovered during alpha testing of Claude Code CLI orchestration mode (2025-12-25).

Test sequence:
1. Orchestrator staged project with 3 agents
2. Simulated analyzer agent startup
3. Agent followed `full_protocol` exactly
4. `receive_messages()` failed with tenant_key error
5. Removed tenant_key, tried again
6. Failed with "agent execution not found" using protocol-specified ID
7. Used actual agent_id from mission response - success

The fix ensures agents can follow `full_protocol` as the "single behavioral authority" without encountering these errors.

---

---

## Bug 4: TodoWrite and report_progress() Not Linked in Protocol

### Observed Behavior
During alpha testing, the analyzer agent:
1. Created TodoWrite with 5 items (Claude Code native)
2. Called `report_progress()` once with `0/5`
3. Never called `report_progress()` again as tasks progressed
4. Called `complete_job()` - jumped from 0/5 to done

The dashboard showed `0/5` the entire time until completion, never showing incremental progress.

### Root Cause
The `full_protocol` has **two disconnected systems**:
- **TodoWrite** - Claude Code native tool for agent's internal task tracking
- **report_progress()** - MCP tool that updates backend/dashboard

The protocol mentions both but **doesn't explicitly link them**:

```markdown
### Phase 2: EXECUTION
- Update todos as you progress  # <-- TodoWrite
- **MESSAGE CHECK**: Call `receive_messages()` after completing each TodoWrite task

### Phase 3: PROGRESS REPORTING (After each milestone)
3. Call `report_progress()` with current status  # <-- MCP
```

An agent following this literally might:
- Update TodoWrite frequently (visible only to itself)
- Call report_progress() only "after milestones" (vague)
- Never sync the two systems

### Impact
- Dashboard shows stale progress (e.g., stuck at 0/5)
- User has no visibility into actual agent progress
- Defeats the purpose of progress tracking

### Recommended Fix

Add explicit sync instruction to `full_protocol`:

```markdown
### CRITICAL: Sync TodoWrite with MCP Progress

Every time you update TodoWrite status (mark item complete or in_progress):
1. Count completed vs total items
2. IMMEDIATELY call report_progress() with updated counts:

   mcp__giljo-mcp__report_progress(
       job_id="{job_id}",
       tenant_key="{tenant_key}",
       progress={
           "mode": "todo",
           "completed_steps": <completed_count>,
           "total_steps": <total_count>,
           "current_step": "<current task activeForm>",
           "percent": <(completed/total)*100>
       }
   )

This keeps the dashboard in sync with your actual progress.
Do NOT skip this step - the backend cannot see your TodoWrite updates.
```

### Files to Modify
- `src/giljo_mcp/services/orchestration_service.py` - `_generate_agent_protocol()` function

---

## Additional Investigation Required: Ghost Messages from `report_progress()`

### Observed Behavior
During analyzer agent simulation, the dashboard showed:
```
Message Audit: analyzer
448a9d6b-4f86-4b19-92fb-1c3bf597f176
Steps: 0 / 0
Sent (1)
Waiting (2)
Read (0)
Plan / TODOs (0)
(empty message)
2:33:03 AM | user → broadcast (sent)
```

### What the agent actually did
1. `get_agent_mission()` - fetch mission
2. `acknowledge_job()` - mark as working
3. `receive_messages()` - check for messages
4. `TodoWrite` - create task list
5. `report_progress()` - report 0/5 steps complete

**The agent did NOT call `send_message()`** - yet the dashboard shows a sent message.

### Questions to investigate

1. **Does `report_progress()` internally create a message?**
   - If so, is this intentional for dashboard visualization?
   - Should it be excluded from the "Sent" count?

2. **Why does it show `from: user` instead of `from: analyzer`?**
   - The sender should be the agent_id or agent_name, not "user"
   - Possible bug in message attribution

3. **Why is the message content "(empty message)"?**
   - The progress payload has data: `{"mode": "todo", "completed_steps": 0, "total_steps": 5, ...}`
   - Is the dashboard not rendering progress payloads as message content?

4. **Is this a dashboard display bug or backend behavior?**
   - Check if a message record is actually created in the database
   - Check if `report_progress()` calls `send_message()` internally

### Files to check
- `src/giljo_mcp/tools/orchestration.py` - `report_progress()` implementation
- `src/giljo_mcp/services/message_service.py` - message creation logic
- Frontend message audit component - display logic

---

**Handover 0378**: Agent ID / Job ID Confusion and Message Tool Fixes

---

## Implementation Summary (2025-12-25)

**Status:** COMPLETE

### What Was Fixed

| Bug | Fix | Commit |
|-----|-----|--------|
| Bug 1a | Added `tenant_key` to `ToolAccessor.receive_messages()` | `94ece0b2` |
| Bug 1b | Added `tenant_key` to `ToolAccessor.list_messages()` | `94ece0b2` |
| Bug 2 | Pass `execution.agent_id` to `_generate_agent_protocol()` (line 906-911) | `377ee1c6` |
| Bug 3 | Added `tenant_key` to all 4 `receive_messages()` examples in protocol | `377ee1c6` |
| Bug 4 | Added "CRITICAL: Sync TodoWrite with MCP Progress" section | `377ee1c6` |
| Investigation | Ghost messages documented as expected behavior (not a bug) | N/A |

### Files Modified

- `src/giljo_mcp/tools/tool_accessor.py` - Added tenant_key pass-through for message methods
- `src/giljo_mcp/services/orchestration_service.py` - Fixed protocol generator call + template

### Tests Added

- `tests/tools/test_tool_accessor_messaging.py` (2 tests)
- `tests/services/test_orchestration_service_protocol.py` (3 tests added to existing)

**All 9 tests passing.**

### TDD Workflow

Used two parallel TDD implementor agents:
1. Agent 1: ToolAccessor tenant_key fixes
2. Agent 2: Protocol generator fixes (agent_id, tenant_key examples, TodoWrite sync)

### Verification

Protocol now correctly shows:
```
**Your Identifiers:**
- job_id (work order): `448a9d6b-...` - Use for mission, progress, completion
- agent_id (executor): `3adca815-...` - Use for messages  ← DIFFERENT VALUE
```

All `receive_messages()` examples include `tenant_key="{tenant_key}"`.

### Ghost Messages Investigation Result

**Expected behavior** - `report_progress()` calls `comm_queue.send_message()` with `message_type="progress"` to provide orchestrator visibility. The `exclude_progress=True` filter in `receive_messages()` already hides these from agents.
