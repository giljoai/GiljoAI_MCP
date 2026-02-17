# Handover: Staging Messaging Unlock

**Date:** 2026-02-16
**From Agent:** Orchestrator Session (Alpha Trial Debrief)
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 1-2 Hours
**Status:** Ready

## Task Summary

Narrow the staging directive trigger so orchestrators can send individual messages during staging. Currently ANY `send_message()` call from a staging orchestrator triggers the STOP directive. Only broadcast messages should trigger it.

## Context and Background

Alpha trial feedback (2026-02-16) revealed the staging STOP directive is too aggressive. An orchestrator wanted to send individual test messages to spawned agents before broadcasting STAGING_COMPLETE, but the server blocked the first `send_message()` call regardless of message type.

**Key discussion points that led to this decision:**
- Messaging should be open from the moment agents are spawned, not locked until implementation
- Orchestrators MUST still use `spawn_agent_job()` for job creation (messaging cannot bypass this -- you can't message agents that don't exist)
- Agent missions come from `get_agent_mission()` (database), not from messages -- so messaging can't be abused as a job assignment channel
- The `acknowledge_job()` implementation gate (checks `implementation_launched_at`) already prevents agents from transitioning to `working` during staging
- The STOP directive should only fire on broadcasts, which are the natural "I'm done" signal

**Related handovers:**
- 0488: Staging Broadcast Response Enforcement (original STOP directive -- this handover narrows that behavior)
- 0709: Implementation phase gate on `acknowledge_job()`

## Technical Details

**File to Modify:**
- `src/giljo_mcp/services/message_service.py` (lines 474-498)

**Current code (line 480):**
```python
if is_orchestrator and is_staging:
    # STOP directive fires on ANY message
```

**Required change:**
```python
if is_orchestrator and is_staging and message_type == "broadcast":
    # STOP directive fires ONLY on broadcast messages
```

**Key consideration:** Verify what variable holds the message type at that point in the code. The `send_message()` method receives `message_type` as a parameter -- confirm it's accessible at the check point (line 480). If message type is determined differently (e.g., by checking `to_agents == ['all']`), adapt accordingly.

## Implementation Plan

1. **Phase 1: Modify condition** (~15 min)
   - Update the staging directive condition in `message_service.py` line 480
   - Add `message_type == "broadcast"` (or equivalent check) to the condition
   - Keep all existing STOP directive content unchanged

2. **Phase 2: Test** (~1 hour)
   - Write test: staging orchestrator sends individual message -- no STOP directive in response
   - Write test: staging orchestrator sends broadcast -- STOP directive IS in response
   - Write test: non-orchestrator agent sends broadcast during staging -- no STOP directive
   - Verify existing staging completion tests still pass

3. **Phase 3: Protocol update** (~15 min)
   - No protocol changes needed. CH2 Step 7 Finale still says broadcast is the final action
   - The protocol already doesn't prohibit individual messaging during staging -- the server was just over-enforcing

## Testing Requirements

**Unit Tests:**
- `test_staging_orchestrator_individual_message_no_directive` -- individual message returns normal response
- `test_staging_orchestrator_broadcast_triggers_directive` -- broadcast returns STOP directive
- `test_staging_orchestrator_multiple_messages_then_broadcast` -- multiple individual messages allowed, broadcast still triggers STOP

**Integration Tests:**
- Full staging flow: spawn agents, send individual messages, broadcast STAGING_COMPLETE, verify STOP

## Dependencies and Blockers

- None. This is a one-line condition change with no schema, API, or frontend impact.

## Success Criteria

- Staging orchestrator can send individual messages to spawned agents without receiving STOP directive
- Staging orchestrator broadcast still triggers STOP directive (no regression)
- All existing staging tests pass
- No changes to MCP tool schemas (zero token impact on tool discovery)

## Rollback Plan

Revert the single condition change in `message_service.py` line 480.
