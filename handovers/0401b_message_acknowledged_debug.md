# Handover 0401b: Message Acknowledged WebSocket Debug

**Status**: COMPLETE ✅
**Parent**: 0401 (Unified WebSocket Platform Refactor)
**Created**: 2026-01-02
**Context Compacts**: 3 (fresh agent needed)

## Problem Statement

The `message:acknowledged` WebSocket event is NOT updating frontend counters:
- **Messages Waiting** should decrement (-1) when agent reads message
- **Messages Read** should increment (+1) when agent reads message
- **Neither happens** - counters stay frozen

## What Works (Verified)

1. **Steps Column** - Real-time updates working (2/5 → 4/5 → 5/5)
2. **Messages Waiting on Receive** - Increments correctly when message sent to agent
3. **Message IDs** - Now stored as proper UUIDs (fixed "None" string issue)
4. **WebSocket connection** - Events are being received (message:received works)

## What's Broken

When an agent calls `receive_messages` (which acknowledges messages):
1. Backend calls `broadcast_message_acknowledged()` (line 730 in message_service.py)
2. Event should route to `handleMessageAcknowledged()` in agentJobsStore.js
3. **Counters don't update** - Waiting stays same, Read stays at 0

## Technical Flow (Trace This)

```
Backend: message_service.py:730 → broadcast_message_acknowledged()
    ↓
WebSocket: api/websocket.py:1064 → broadcast_message_acknowledged()
    ↓
EventFactory: api/events/schemas.py:681 → message_acknowledged()
    ↓
Frontend: websocketEventRouter.js:185 → 'message:acknowledged' handler
    ↓
Store: agentJobsStore.js:309 → handleMessageAcknowledged(payload)
    ↓
EXPECTED: messages_waiting_count--, messages_read_count++
ACTUAL: No change
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/giljo_mcp/services/message_service.py` | Backend broadcast trigger | 726-739 |
| `api/websocket.py` | WebSocket manager | 1064-1085 |
| `api/events/schemas.py` | Event factory | 681-701 |
| `frontend/src/stores/websocketEventRouter.js` | Event routing | 185-193 |
| `frontend/src/stores/agentJobsStore.js` | Counter update logic | 309-354 |

## handleMessageAcknowledged Logic (agentJobsStore.js:309-354)

```javascript
function handleMessageAcknowledged(payload) {
  const recipientId = resolveJobId(payload?.agent_id || payload?.job_id)
  if (!recipientId) return  // <-- Could be failing here

  const previous = jobsById.value.get(recipientId)
  if (!previous) return  // <-- Or here

  const messageIds = ensureArray(payload?.message_ids).length
    ? ensureArray(payload?.message_ids)
    : payload?.message_id
      ? [payload.message_id]
      : []

  if (!messageIds.length) return  // <-- Or here (no message IDs?)

  // ... matching and counter update logic
}
```

## Environment

```
tenant_key: ***REMOVED***
project_id: 08afad1b-c8ee-4659-b207-c909e677c376
```

## Active Test Agents (All Waiting Status)

| Agent | job_id (work order) | agent_id (executor UUID) |
|-------|---------------------|--------------------------|
| **Tester** | `d2a384c2-9eed-4178-887e-2eda7a90799d` | `bb2d78a8-d929-4ab5-a218-b3e7c1a83c20` |
| **Documenter** | `8d0ae552-14df-41d5-8739-5e06e54993ef` | `69918eab-2187-40b8-934a-97179a31de39` |
| **Orchestrator** | `fc8e501c-03eb-419c-9e81-c9a8183d0bfe` | `32add4b5-7d5d-44fa-9aad-70eef5437ab9` |
| **Implementer** | `aabc219f-202e-43f2-86c5-fac625ee41a1` | `6efa0f62-7b50-4ef7-bda7-cebeaa276af0` |
| **Analyzer** | `a003c645-a724-41ea-864e-bd3188fab9bf` | `b5e88b4d-65a1-4e6a-b995-57ab363045cc` |
| **Reviewer** | `055e8047-6823-4ed2-a6f4-4cfa66b4fba9` | `d8784d92-a16c-4c4f-8c56-e758851022db` |

**Lookup Query**:
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT ae.agent_id, ae.agent_type, ae.agent_name, ae.status, ae.job_id
FROM agent_executions ae
JOIN agent_jobs aj ON aj.job_id = ae.job_id
WHERE ae.status NOT IN ('cancelled', 'complete', 'failed', 'decommissioned')
ORDER BY ae.agent_type;"
```

## Test Commands

### 1. Check Current Message Counts
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT ae.agent_type, ae.agent_name,
       COUNT(CASE WHEN m.status = 'pending' THEN 1 END) as waiting,
       COUNT(CASE WHEN m.status = 'acknowledged' THEN 1 END) as read
FROM agent_executions ae
LEFT JOIN messages m ON ae.agent_id::text = ANY(m.to_agent_ids)
WHERE ae.tenant_key = '***REMOVED***'
AND ae.status = 'waiting'
GROUP BY ae.agent_type, ae.agent_name;"
```

### 2. Send Direct Message to Tester
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
INSERT INTO messages (id, tenant_key, project_id, from_agent, to_agent_ids, content, message_type, status, priority, created_at)
VALUES (
  gen_random_uuid(),
  '***REMOVED***',
  '08afad1b-c8ee-4659-b207-c909e677c376',
  'orchestrator',
  ARRAY['bb2d78a8-d929-4ab5-a218-b3e7c1a83c20'],
  'Test message for ack debug',
  'direct',
  'pending',
  'normal',
  NOW()
);"
```

### 3. Broadcast to All Agents
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
INSERT INTO messages (id, tenant_key, project_id, from_agent, to_agent_ids, content, message_type, status, priority, created_at)
VALUES (
  gen_random_uuid(),
  '***REMOVED***',
  '08afad1b-c8ee-4659-b207-c909e677c376',
  'orchestrator',
  ARRAY['all'],
  'Broadcast test for ack debug',
  'broadcast',
  'pending',
  'normal',
  NOW()
);"
```

### 4. Tester Reads Messages (MCP Tool)
```python
# Via MCP tool - this triggers the acknowledge flow
receive_messages(
    tenant_key="***REMOVED***",
    agent_id="bb2d78a8-d929-4ab5-a218-b3e7c1a83c20",
    limit=10
)
```

### 5. Check Pending Messages for Tester
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT id, from_agent, content, status, created_at
FROM messages
WHERE 'bb2d78a8-d929-4ab5-a218-b3e7c1a83c20' = ANY(to_agent_ids)
AND tenant_key = '***REMOVED***'
ORDER BY created_at DESC
LIMIT 10;"
```

### 6. Report Progress (for Steps column testing)
```python
# Via MCP tool
report_progress(
    job_id="d2a384c2-9eed-4178-887e-2eda7a90799d",
    tenant_key="***REMOVED***",
    progress={
        "mode": "todo",
        "completed_steps": 3,
        "total_steps": 5,
        "current_step": "Testing step 3",
        "percent": 60
    }
)
```

### 7. Via API (Alternative to MCP)
```bash
# Get auth token first
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "giljo", "password": "YOUR_PASSWORD"}'

# Send message via API
curl -X POST http://localhost:7272/api/messages/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_agents": ["bb2d78a8-d929-4ab5-a218-b3e7c1a83c20"],
    "content": "Test via API",
    "message_type": "direct",
    "project_id": "08afad1b-c8ee-4659-b207-c909e677c376"
  }'

# Receive messages via API (triggers acknowledge)
curl -X GET "http://localhost:7272/api/messages/receive?agent_id=bb2d78a8-d929-4ab5-a218-b3e7c1a83c20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Debug Steps for Fresh Agent

1. **Add console.log to websocketEventRouter.js:186**
   ```javascript
   console.log('[DEBUG] message:acknowledged payload:', payload)
   ```

2. **Add console.log to agentJobsStore.js:310**
   ```javascript
   console.log('[DEBUG] handleMessageAcknowledged - recipientId:', recipientId, 'payload:', payload)
   ```

3. **Check backend logs** for:
   ```
   [WEBSOCKET] Broadcast message:acknowledged for X messages
   ```

4. **Test with receive_messages MCP tool** and watch console

## Likely Root Causes

1. **Event not being broadcast** - Backend not calling broadcast_message_acknowledged
2. **Event not reaching frontend** - WebSocket routing issue
3. **resolveJobId mismatch** - agent_id in payload doesn't match any job
4. **message_ids empty** - Payload has no message_ids to match
5. **Message ID mismatch** - Stored message IDs don't match acknowledged ones

## Recent Commits (This Session)

- `c6e00c5f` - Fixed handleProgressUpdate for todo_steps object format
- `1fb879af` - Updated 0401 handover to Complete (premature - message ack broken)
- `3c384d78` - Added agent_id to JobResponse model (previous session)

## Session History

1. Verified Steps column works with report_progress
2. Tested message counters with Documenter - appeared to work
3. Tested with Tester agent - Messages Waiting increments, but Read never updates
4. Found message IDs were stored as "None" string - fixed by restart
5. After full restart, message IDs correct but ack still broken
6. Context compacted 3 times during debugging

## ROOT CAUSE FOUND (2026-01-02)

**Issue:** `TableRowData` in `table_view.py` was missing `agent_id` field.

**Why this broke things:**
1. WebSocket `message:acknowledged` events include `agent_id` (executor UUID)
2. Frontend `resolveJobId(agent_id)` tries to find job where `job.agent_id === agent_id`
3. Jobs loaded via `/api/agent-jobs/table-view` didn't include `agent_id`
4. `resolveJobId()` returned `null` → no counter update

**Fix Applied:**
```diff
# api/endpoints/agent_jobs/table_view.py

class TableRowData(BaseModel):
    job_id: str
+   agent_id: Optional[str] = None  # Handover 0401b: WebSocket event matching

# In row construction:
    rows.append(
        TableRowData(
            job_id=execution.job_id,
+           agent_id=execution.agent_id,  # Handover 0401b
```

## Verification Results (2026-01-03)

All tests passed! Real-time counter updates working:

| Test | Action | Expected | Actual | Result |
|------|--------|----------|--------|--------|
| Send Message | Orchestrator → Tester | Tester Waiting +1 | 11 → 12 | ✅ |
| Read Message | Tester reads 1 msg | Waiting -1, Read +1 | 12→11, 1→2 | ✅ |

## Resolution Summary

1. ✅ Added `agent_id` to `TableRowData` model
2. ✅ Added `agent_id=execution.agent_id` to row construction
3. ✅ Backend server reloaded with changes
4. ✅ Verified Messages Waiting decrements when agent reads
5. ✅ Verified Messages Read increments when agent reads

**Root cause**: `TableRowData` was missing `agent_id` field, preventing `resolveJobId()` from matching WebSocket events to jobs.
