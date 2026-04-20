# Manual Test: Handover 0111 - Agent Card Real-Time Updates

**Issue Fixed**: Agent cards not appearing in real-time (required page refresh)

**Root Cause**: MCP tools tried to use EventBus pattern which doesn't exist in MCP process

**Fix**: HTTP bridge pattern - MCP tools call HTTP endpoint to trigger WebSocket broadcasts

## Prerequisites

- API server running on port 7272 (`python startup.py`)
- Frontend running (`cd frontend && npm run dev`)
- Active product and project created
- At least one orchestrator agent in the project

## Test 1: Agent Cards Appear Without Refresh

**Objective**: Verify agent cards appear in real-time when orchestrator spawns agents

### Steps:

1. **Open Dashboard**
   - Navigate to `http://localhost:5173` (or your frontend URL)
   - Log in if required
   - Navigate to Projects → Select active project → Jobs tab

2. **Open Browser DevTools**
   - Press F12 to open DevTools
   - Go to **Network** tab
   - Filter by **WS** (WebSocket)
   - Verify WebSocket connection is established (look for green "101 Switching Protocols")

3. **Open Console Tab**
   - Switch to **Console** tab in DevTools
   - Clear any existing logs (click trash icon)

4. **Trigger Agent Spawning**
   - Click "Stage Project" button in the UI
   - Orchestrator will begin spawning agents

5. **Verify Real-Time Updates** (CRITICAL)
   - Watch the Jobs tab WITHOUT refreshing the page
   - Agent cards should appear immediately as they are spawned
   - Each new agent should appear within 1-2 seconds of creation

### Expected Results:

✅ **Agent cards appear WITHOUT page refresh**
✅ **Agent cards appear within 1-2 seconds of spawning**
✅ **No console errors**
✅ **WebSocket events visible in Network → WS tab**
✅ **Backend logs show**: `[HTTP BRIDGE] Agent spawned broadcast sent: {agent_name} ({agent_type})`

### Failure Indicators:

❌ Agent cards don't appear until page refresh
❌ Console shows errors like "Cannot read property 'emit' of undefined"
❌ Backend logs show "Failed to broadcast agent:created"
❌ WebSocket connection disconnected or not established

## Test 2: WebSocket Event Inspection

**Objective**: Verify agent:created events are broadcast via WebSocket

### Steps:

1. **Setup WebSocket Monitoring**
   - Open DevTools → Network → WS
   - Click on the WebSocket connection (usually `/ws`)
   - View **Messages** tab

2. **Trigger Agent Spawning**
   - Click "Stage Project" or trigger orchestrator to spawn agents

3. **Inspect WebSocket Messages**
   - Watch for messages with `type: "agent:created"`
   - Verify message structure

### Expected WebSocket Message Structure:

```json
{
  "type": "agent:created",
  "timestamp": "2025-11-12T10:30:00.000Z",
  "schema_version": "1.0",
  "tenant_key": "tk_...",
  "project_id": "proj_...",
  "agent_id": "agent_...",
  "job_id": "agent_...",
  "agent_type": "implementer",
  "agent_name": "Backend Implementer",
  "status": "pending",
  "thin_client": true,
  "prompt_tokens": 50,
  "mission_tokens": 2000
}
```

### Expected Results:

✅ **agent:created messages visible in WebSocket**
✅ **Message contains all required fields**
✅ **tenant_key matches your tenant**
✅ **project_id matches current project**

## Test 3: Backend Logging Verification

**Objective**: Verify HTTP bridge is called successfully

### Steps:

1. **Monitor Backend Logs**
   - Open terminal where API server is running
   - Watch for log output as agents are spawned

2. **Trigger Agent Spawning**
   - Click "Stage Project"

3. **Verify Log Entries**
   - Look for `[HTTP BRIDGE]` log entries

### Expected Log Output:

```
INFO: [HTTP BRIDGE] Agent spawned broadcast sent: System Architect (architect)
INFO: [HTTP BRIDGE] Agent spawned broadcast sent: Backend Implementer (implementer)
INFO: [HTTP BRIDGE] Agent spawned broadcast sent: QA Tester (tester)
INFO: WebSocket event emitted: agent:created to 1 client(s)
```

### Expected Results:

✅ **[HTTP BRIDGE] log entries appear for each agent**
✅ **No warning messages about broadcast failures**
✅ **WebSocket event emitted log shows correct client count**

### Failure Indicators:

❌ `[HTTP BRIDGE] Broadcast failed with status {status_code}`
❌ `[HTTP BRIDGE] Failed to broadcast agent:created: {error}`
❌ No HTTP bridge logs appearing

## Test 4: Multi-Tenant Isolation

**Objective**: Verify agent:created events don't leak across tenants

### Prerequisites:

- Two user accounts in different tenants
- Two separate browser sessions (or incognito + regular)

### Steps:

1. **Setup Two Sessions**
   - Browser 1: Log in as User A (Tenant A)
   - Browser 2: Log in as User B (Tenant B)
   - Both: Open DevTools → Network → WS

2. **Spawn Agents in Tenant A**
   - In Browser 1, trigger agent spawning

3. **Verify Isolation**
   - Browser 1 should receive agent:created events
   - Browser 2 should NOT receive any events

### Expected Results:

✅ **Tenant A receives agent:created events**
✅ **Tenant B receives NO events from Tenant A**
✅ **Zero cross-tenant leakage**

## Test 5: Error Handling

**Objective**: Verify errors don't crash the system

### Test 5A: WebSocket Disconnected

1. **Setup**
   - Open project Jobs tab
   - Open DevTools → Network → WS
   - Right-click WebSocket connection → Close

2. **Trigger Agent Spawning**
   - Click "Stage Project"

3. **Verify**
   - Backend should log warning (not error)
   - Agent spawning should complete successfully
   - Database should contain new agent jobs

### Expected Results:

✅ **Agents created in database**
✅ **Backend logs warning about WebSocket unavailable**
✅ **No crashes or exceptions**

### Test 5B: HTTP Bridge Timeout

1. **Simulate Slow Network**
   - This requires code change to test (mock httpx client)
   - See integration test `test_http_bridge_timeout_enforced`

2. **Verify**
   - Agent spawning completes within ~6 seconds
   - Doesn't hang waiting for bridge response

## Test 6: Concurrent Agent Spawning

**Objective**: Verify multiple agents spawning simultaneously

### Steps:

1. **Setup**
   - Open project Jobs tab
   - Open DevTools → Console

2. **Trigger Multiple Agent Spawns**
   - Click "Stage Project" (orchestrator spawns 3-5 agents)

3. **Verify**
   - All agent cards appear
   - All agents have correct types and names
   - No duplicate agents

### Expected Results:

✅ **All agents appear in Jobs tab**
✅ **Correct number of agents (no duplicates)**
✅ **All agent cards show correct information**

## Regression Tests

These tests verify existing functionality still works:

### Regression 1: Mission Updates

**Objective**: Verify mission updates still broadcast

1. Navigate to project Overview tab
2. Trigger orchestrator to generate mission
3. Mission should appear without refresh

✅ **Mission appears in real-time**

### Regression 2: Orchestrator ID Stability (Fixed Nov 6)

**Objective**: Verify orchestrator doesn't duplicate on multiple clicks

1. Click "Stage Project" 5 times rapidly
2. Wait for orchestrators to spawn
3. Query database:

```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM mcp_agent_jobs WHERE agent_type='orchestrator' AND project_id='{project_id}'"
```

✅ **Should return 1 (not 5+)**

### Regression 3: Agent Status Updates

**Objective**: Verify agent status changes broadcast

1. Open project Jobs tab
2. Acknowledge an agent job (if testing workflow)
3. Status should update without refresh

✅ **Status updates in real-time**

## Performance Benchmarks

- **Agent card appearance**: < 2 seconds after spawn
- **WebSocket message latency**: < 100ms
- **HTTP bridge response time**: < 50ms
- **No memory leaks after 50+ agent spawns**

## Troubleshooting

### Issue: Agent cards don't appear

**Checks**:
1. Verify WebSocket connected (DevTools → Network → WS)
2. Check backend logs for HTTP bridge errors
3. Verify tenant_key matches between frontend and backend
4. Check browser console for JavaScript errors

### Issue: WebSocket connection fails

**Checks**:
1. Verify API server running on port 7272
2. Check firewall settings
3. Verify CORS configuration
4. Check network connectivity

### Issue: Backend logs show broadcast failures

**Checks**:
1. Verify WebSocketManager is initialized
2. Check for errors in API startup
3. Verify database connection
4. Check tenant_key in auth context

## Success Criteria

**Handover 0111 is FULLY RESOLVED when**:

✅ All 6 manual tests pass
✅ Integration tests pass (`pytest tests/integration/test_agent_card_realtime.py`)
✅ No console errors during normal operation
✅ Backend logs show successful HTTP bridge calls
✅ WebSocket events visible in DevTools
✅ Zero cross-tenant leakage confirmed

## Database Verification

Verify agents are created correctly in database:

```bash
# List all agent jobs for project
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT job_id, agent_type, agent_name, status, created_at FROM mcp_agent_jobs WHERE project_id='{project_id}' ORDER BY created_at DESC;"

# Count agents by type
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT agent_type, COUNT(*) as count FROM mcp_agent_jobs WHERE project_id='{project_id}' GROUP BY agent_type;"

# Verify no duplicate orchestrators
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM mcp_agent_jobs WHERE agent_type='orchestrator' AND project_id='{project_id}';"
```

Expected: Should be 1 orchestrator per project (not multiple)

---

**Tester**: _______________
**Date**: _______________
**Test Result**: [ ] PASS [ ] FAIL
**Notes**: _______________________________________________
