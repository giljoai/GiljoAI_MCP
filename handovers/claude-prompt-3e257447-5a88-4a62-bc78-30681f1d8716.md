# Plan: Fix Alpha Test Failures + UUID Normalization

## Executive Summary

Alpha test revealed 4 issues + architecture inconsistency. Research confirms:
- **Uncommitted git changes are SAFE** - Only legacy MCP command cleanup
- **2 issues are code bugs** - Need fixes
- **2 issues are prompt adherence problems** - Need template strengthening
- **1 architecture issue** - Agent identification uses mixed names/UUIDs

---

## Issues Identified

| # | Issue | Root Cause | Fix Type |
|---|-------|------------|----------|
| 1 | Steps column shows "—" | Agent didn't follow `full_protocol` TodoWrite requirements | Prompt/Template |
| 2 | Messages Read = 0 | Frontend can't match message IDs (sync gap) | Code Bug |
| 3 | Messages Waiting not decrementing | Same as #2 - `acknowledgedNow === 0` early exit | Code Bug |
| 4 | from_agent = "orchestrator" | Hardcoded in agent_coordination.py:1277 | Code Bug |
| 5 | Mixed agent identification | `to_agents` uses UUIDs, `from_agent` uses names/UUIDs | Architecture |

---

## Detailed Analysis

### Issue 1: Steps Column "—" (Prompt Adherence)

**Evidence**: Analyzer called `report_progress()` but didn't include `todo_items` array

**Root Cause**: The `full_protocol` clearly states:
```
### CRITICAL: Sync TodoWrite with MCP Progress (Handover 0402)
Every time you update TodoWrite status:
1. Count completed vs total items
2. IMMEDIATELY call report_progress() with updated counts AND todo_items
```

But the analyzer subagent ignored this. Claude subagents sometimes skip complex multi-step instructions.

**Fix**: Strengthen prompt with MANDATORY enforcement and examples directly in Task tool prompt.

---

### Issues 2 & 3: Message Counters Not Updating (Code Bug)

**Flow Trace**:
```
Backend: receive_messages() → broadcast_message_acknowledged() ✓
WebSocket: message:acknowledged event emitted ✓
Router: websocketEventRouter.js routes to handler ✓
Handler: handleMessageAcknowledged() → EARLY EXIT at acknowledgedNow === 0
```

**Root Cause**: `handleMessageAcknowledged()` iterates over `previous.messages` looking for matching IDs. If the messages aren't in the local array (never received `message:received` event), `acknowledgedNow = 0` and counters don't update.

**Fix**: Add fallback counter update when messages aren't found locally but payload has valid `message_ids`.

---

### Issue 4: from_agent Hardcoded (Code Bug)

**Location**: `src/giljo_mcp/tools/agent_coordination.py` line ~1277

```python
result = await comm_queue.send_message(
    ...
    from_agent="orchestrator",  # HARDCODED BUG!
    ...
)
```

**Fix**: Accept `from_agent` as parameter and pass it through.

---

## Implementation Plan

### Phase 1: Fix Message Counter Bug (Priority 1)

**File**: `frontend/src/stores/agentJobsStore.js`

**Change**: Add fallback in `handleMessageAcknowledged()` when `acknowledgedNow === 0`:

```javascript
// After line 351 (before final return)
if (acknowledgedNow === 0 && messageIds.length > 0) {
  // Fallback: Backend acknowledged messages we don't have locally
  // Update counters based on payload count
  const nextJob = normalizeJob({
    ...previous,
    messages_waiting_count: Math.max(0, (previous.messages_waiting_count || 0) - messageIds.length),
    messages_read_count: (previous.messages_read_count || 0) + messageIds.length,
  })
  jobsById.value = createNextMapWith(jobsById.value, recipientId, nextJob)
  return
}
```

---

### Phase 2: UUID Normalization for Agent Messaging (Priority 2)

**Goal**: All agent identification uses `agent_id` (UUID), with `agent_name` for display only.

#### 2a. Rename Parameters for Clarity

**File**: `src/giljo_mcp/tools/agent_coordination.py`

**Change function signature** (lines 1198-1204):
```python
async def send_message(
    job_id: str,
    to_agent_id: str,        # RENAMED: was to_agent
    message: str,
    tenant_key: str,
    from_agent_id: str,      # NEW: required UUID, no default
    priority: int = 1,
) -> Dict[str, Any]:
```

**Update internal call** (line 1277):
```python
result = await comm_queue.send_message(
    ...
    from_agent=from_agent_id,  # Use the UUID parameter
    to_agent=to_agent_id,
    ...
)
```

#### 2b. Update MCP Tool Schema

**File**: `api/endpoints/mcp_http.py`

Update `send_message` tool definition:
```python
{
    "name": "send_message",
    "parameters": {
        "to_agent_id": {"type": "string", "description": "Target agent UUID (agent_id)"},
        "from_agent_id": {"type": "string", "description": "Sender agent UUID (your agent_id)"},
        ...
    }
}
```

#### 2c. Update full_protocol Template

**File**: `src/giljo_mcp/services/orchestration_service.py` (or wherever full_protocol is generated)

Change example from:
```python
send_message(to_agent="implementer", ...)
```
To:
```python
send_message(to_agent_id="<agent_id from spawn_agent_job>", from_agent_id="{agent_id}", ...)
```

#### 2d. Include agent_name in Responses for UI

When returning message data, include both:
```python
{
    "from_agent_id": "uuid-here",
    "from_agent_name": "analyzer",  # For UI display
    "to_agent_id": "uuid-here",
    "to_agent_name": "implementer"  # For UI display
}
```

---

### Phase 3: Strengthen TodoWrite Prompt (Priority 3)

**File**: `.claude/agents/analyzer.md` (and other agent templates)

**Add explicit enforcement block**:
```markdown
## MANDATORY: TodoWrite Sync (DO NOT SKIP)

Before EVERY report_progress() call:
1. Create TodoWrite items for your tasks (if not done)
2. Count completed vs total
3. ALWAYS include todo_items array:

```python
mcp__giljo-mcp__report_progress(
    job_id="YOUR_JOB_ID",
    tenant_key="YOUR_TENANT",
    progress={
        "mode": "todo",
        "completed_steps": <count>,
        "total_steps": <count>,
        "current_step": "<current task>",
        "percent": <(completed/total)*100>,
        "todo_items": [
            {"content": "Task 1", "status": "completed"},
            {"content": "Task 2", "status": "in_progress"},
            ...
        ]
    }
)
```

FAILURE TO INCLUDE todo_items = Dashboard shows "--" = TEST FAILURE
```

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/stores/agentJobsStore.js` | Add fallback counter update (lines 348-360) |
| `src/giljo_mcp/tools/agent_coordination.py` | Rename to_agent→to_agent_id, add from_agent_id (lines 1198-1280) |
| `api/endpoints/mcp_http.py` | Update send_message schema with new param names |
| `src/giljo_mcp/services/orchestration_service.py` | Update full_protocol template to use agent_id |
| `src/giljo_mcp/services/message_service.py` | Include agent_name in message responses |
| `.claude/agents/analyzer.md` | Strengthen TodoWrite requirement |
| `.claude/agents/implementer.md` | Strengthen TodoWrite requirement |
| `.claude/agents/documenter.md` | Strengthen TodoWrite requirement |

---

## Testing Plan

After fixes:
1. Send message to Tester agent using `to_agent_id` (UUID) → Verify Messages Waiting +1
2. Tester reads via receive_messages() → Verify Messages Waiting -1, Messages Read +1
3. Analyzer calls report_progress with todo_items → Verify Steps shows "2/5"
4. Analyzer sends message using `from_agent_id` → Verify from_agent shows UUID and from_agent_name shows "analyzer"
5. Verify message list response includes both `from_agent_id` and `from_agent_name`
6. Re-run alpha test with TinyContacts project to verify end-to-end

---

## Notes

- Uncommitted git changes are UNRELATED to these issues (legacy cleanup only)
- The subagent working on MCP command removals did NOT touch messaging or progress code
- Issues 1-4 exist in committed code, not the uncommitted changes

## Architecture Decision: UUID Normalization

**Rationale**: Using agent_id (UUID) everywhere provides:
- **Precision**: No ambiguity between "implementer" vs "implementer-frontend"
- **Succession support**: Same job, different executor UUID per succession
- **Query safety**: Exact match, not LIKE patterns
- **Future-proof**: Ready for multi-instance agents

**Display mapping**: UI maps `agent_id` → `agent_name` via `agent_executions` table join.

---

## Phase 4: Reactive Feedback System (Architecture-Correct)

**Architecture Constraint**: MCP Server is PASSIVE. Agents PULL via HTTP - no push channel exists.

**What Server CAN Do**:
1. Store messages in DB → Agent sees on next `receive_messages()` call
2. Return warnings in MCP tool responses → IMMEDIATE feedback

### 4a. Two-Channel Feedback Strategy

| Channel | Mechanism | Latency | Use Case |
|---------|-----------|---------|----------|
| **Response Warning** | Return `warnings[]` in `report_progress()` response | IMMEDIATE | Agent sees right away |
| **Message Queue** | Store in DB, agent polls via `receive_messages()` | Next poll | Persistent reminder |

### 4b. Implementation: Immediate Warning in Response

**File**: `src/giljo_mcp/services/orchestration_service.py` (`report_progress()` method)

**Change**: Return warning in response when `todo_items` missing:

```python
# After processing, before return statement (~line 1240)
warnings = []
todo_items = progress.get("todo_items")
if not isinstance(todo_items, list) or len(todo_items) == 0:
    warnings.append(
        "WARNING: todo_items missing! Dashboard Steps shows '--'. "
        "Include todo_items=[{content, status}] in every report_progress() call."
    )

return {
    "status": "success",
    "message": "Progress reported successfully",
    "warnings": warnings,  # NEW: Agent sees immediately
}
```

### 4c. Implementation: Queue Corrective Message (Optional)

**Same location** - also queue a message for next `receive_messages()`:

```python
if not isinstance(todo_items, list) or len(todo_items) == 0:
    # Queue message for next receive_messages() call
    await self._message_service.send_message(
        to_agents=[execution.agent_id],
        content="CORRECTIVE: Include todo_items in report_progress(). Dashboard cannot update without it.",
        project_id=job.project_id,
        message_type="system",
        priority="high",
        from_agent="system",
        tenant_key=tenant_key,
    )
```

### 4d. Acknowledge Job: Queue Initial Reminder

**File**: `src/giljo_mcp/services/orchestration_service.py` (`acknowledge_job()` method)

After setting status to active, queue reminder message:

```python
# After status update, queue protocol reminder
await self._message_service.send_message(
    to_agents=[execution.agent_id],
    content="""PROTOCOL REMINDER:
1. Create TodoWrite task list BEFORE implementation
2. Include todo_items=[] in EVERY report_progress() call
3. Dashboard shows "--" without todo_items = TEST FAILURE""",
    project_id=job.project_id,
    message_type="system",
    priority="high",
    from_agent="system",
    tenant_key=tenant_key,
)
```

### 4e. Agent Flow (How Agent Experiences This)

```
Agent calls acknowledge_job()
  ← Server queues reminder message
  ← Response: {"status": "success", ...}

Agent calls receive_messages() (Phase 1 Step 3)
  ← Gets: "PROTOCOL REMINDER: Create TodoWrite..."

Agent calls report_progress() WITHOUT todo_items
  ← IMMEDIATE Response: {"status": "success", "warnings": ["WARNING: todo_items missing..."]}
  ← Server queues corrective message

Agent calls receive_messages() again
  ← Gets: "CORRECTIVE: Include todo_items..."
  ← Agent corrects behavior
```

### 4f. Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/services/orchestration_service.py` | Add `warnings` to `report_progress()` response |
| `src/giljo_mcp/services/orchestration_service.py` | Queue message when `todo_items` missing |
| `src/giljo_mcp/services/orchestration_service.py` | Queue reminder in `acknowledge_job()` |

### 4g. Why This Works

1. **Immediate feedback**: `warnings` in response - agent sees RIGHT AWAY
2. **Persistent reminder**: Message queue - agent sees on next poll
3. **Self-correcting**: Fires on EVERY forgetful `report_progress()` call
4. **Architecture-compliant**: Server only responds to requests, never pushes
5. **Scales to long missions**: Every call without `todo_items` triggers warning

---

## Status Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Message Counter Fallback | ✅ COMPLETE (Handover 0405) |
| 2 | UUID Normalization | ⏸️ DEFERRED |
| 3 | TodoWrite Prompt Strengthening | ✅ COMPLETE (Handover 0405) |
| 4 | Backend Push-Reminder System | 🆕 NEW - Ready for implementation |

---

## Handover Reference

This plan addresses:
- Handover 0401b (message acknowledgment debug) - Phase 1 ✅
- Handover 0405 (message counter + prompt enforcement) - Phase 1, 3 ✅
- NEW: Handover 0406 (reactive feedback for longer missions) - Phase 4
