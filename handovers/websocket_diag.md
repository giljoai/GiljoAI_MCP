# WebSocket Real-Time Updates Diagnostic

**Created**: 2025-11-07  
**Status**: 🔧 In Progress - Debugging Phase  
**Issue**: Mission and agents don't appear in real-time during orchestrator staging (require manual page refresh)

---

## Problem Statement

When clicking "Stage Project" button in LaunchTab:
1. ✅ Orchestrator executes successfully
2. ✅ Mission and agents created in database
3. ❌ **UI doesn't update in real-time** - requires manual browser refresh
4. ❌ WebSocket events (`project:mission_updated`, `agent:created`) not being broadcast

**Expected Behavior**: Mission and agent cards should appear in real-time as orchestrator creates them

**Actual Behavior**: Data written to database but frontend WebSocket listeners never fire

---

## Architecture Overview

### Cross-Process Communication Challenge

**The Problem**:
- MCP tools run in **separate Python process** from FastAPI server
- Cannot directly access `api.app.state.websocket_manager` from MCP tools
- Need bridge mechanism for MCP → WebSocket communication

**The Solution**: HTTP Bridge Pattern
```
MCP Tool (tool_accessor.py)
    ↓ HTTP POST
HTTP Bridge Endpoint (/api/v1/ws-bridge/emit)
    ↓ Direct access to WebSocketManager
WebSocket Broadcast to Frontend
    ↓ Event listeners
Vue Component Updates
```

### HTTP Bridge Endpoint

**Location**: `api/endpoints/websocket_bridge.py`

**Endpoint**: `POST /api/v1/ws-bridge/emit`

**Request Model**:
```python
{
    "event_type": "project:mission_updated" | "agent:created",
    "tenant_key": "tk_...",
    "data": {
        # Event-specific payload
    }
}
```

**Response Model**:
```python
{
    "success": true,
    "event_type": "project:mission_updated",
    "clients_notified": 2,
    "message": "Event broadcasted to 2 client(s)"
}
```

---

## Current Implementation

### 1. MCP Tool: `update_project_mission()`

**File**: `src/giljo_mcp/tools/tool_accessor.py` (lines ~412-437)

**Code**:
```python
# Broadcast mission update via WebSocket HTTP bridge
logger.info(f"[WEBSOCKET DEBUG] About to broadcast mission_updated for project {project_id}")
if project:
    try:
        import httpx
        
        logger.info(f"[WEBSOCKET DEBUG] httpx imported, creating client for HTTP bridge")

        # Use HTTP bridge to emit WebSocket event (MCP runs in separate process)
        async with httpx.AsyncClient() as client:
            bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
            logger.info(f"[WEBSOCKET DEBUG] Sending POST to {bridge_url}")
            
            response = await client.post(
                bridge_url,
                json={
                    "event_type": "project:mission_updated",
                    "tenant_key": project.tenant_key,
                    "data": {
                        "project_id": project_id,
                        "mission": mission,
                        "token_estimate": len(mission) // 4,
                        "user_config_applied": False,
                        "generated_by": "orchestrator",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
                timeout=5.0,
            )
            logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response: {response.status_code}")
            logger.info(f"[WEBSOCKET] Broadcasted mission_updated for project {project_id} via HTTP bridge")
    except Exception as ws_error:
        logger.error(f"[WEBSOCKET ERROR] Failed to broadcast mission_updated via HTTP bridge: {ws_error}", exc_info=True)
```

### 2. MCP Tool: `spawn_agent_job()`

**File**: `src/giljo_mcp/tools/tool_accessor.py` (lines ~1675-1705)

**Code**:
```python
# Broadcast agent creation via WebSocket HTTP bridge
logger.info(f"[WEBSOCKET DEBUG] About to broadcast agent:created for {agent_name} ({agent_type})")
try:
    import httpx
    
    logger.info(f"[WEBSOCKET DEBUG] httpx imported for agent creation broadcast")

    # Use HTTP bridge to emit WebSocket event (MCP runs in separate process)
    async with httpx.AsyncClient() as client:
        bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
        logger.info(f"[WEBSOCKET DEBUG] Sending POST to {bridge_url} for agent:created")
        
        response = await client.post(
            bridge_url,
            json={
                "event_type": "agent:created",
                "tenant_key": tenant_key,
                "data": {
                    "project_id": project_id,
                    "agent_id": agent_job_id,
                    "agent_job_id": agent_job_id,
                    "agent_type": agent_type,
                    "agent_name": agent_name,
                    "status": "waiting",
                    "thin_client": True,
                    "prompt_tokens": prompt_tokens,
                    "mission_tokens": mission_tokens,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
            timeout=5.0,
        )
        logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response for agent:created: {response.status_code}")
        logger.info(f"[WEBSOCKET] Broadcasted agent:created for {agent_name} ({agent_type}) via HTTP bridge")
except Exception as ws_error:
    logger.error(f"[WEBSOCKET ERROR] Failed to broadcast agent:created via HTTP bridge: {ws_error}", exc_info=True)
```

### 3. Frontend WebSocket Listeners

**File**: `frontend/src/components/projects/LaunchTab.vue`

**Mission Update Listener** (lines ~257-275):
```javascript
const handleMissionUpdated = (event) => {
  console.log('[LaunchTab] Received project:mission_updated event:', event);
  
  if (event.data?.project_id === projectId.value) {
    // Update mission text
    mission.value = event.data.mission || '';
    
    // Update staging status
    if (event.data.generated_by === 'orchestrator') {
      isStaging.value = true;
      stagingProgress.value = 30; // Mission generated
    }
    
    // Show success snackbar
    showSnackbar('Mission updated successfully', 'success');
  }
};
```

**Agent Created Listener** (lines ~277-301):
```javascript
const handleAgentCreated = (event) => {
  console.log('[LaunchTab] Received agent:created event:', event);
  
  if (event.data?.project_id === projectId.value) {
    // Refresh agents list
    fetchAgentJobs();
    
    // Update staging progress
    stagingProgress.value += 10; // Increment per agent
    
    // Check if all agents spawned (6 agents expected)
    if (agentJobs.value.filter(a => a.agent_type !== 'orchestrator').length >= 6) {
      isStaging.value = false;
      readyToLaunch.value = true;
      stagingProgress.value = 100;
      showSnackbar('All agents spawned! Ready to launch.', 'success');
    }
  }
};
```

**Event Subscription** (lines ~463-465):
```javascript
onMounted(async () => {
  // Subscribe to WebSocket events
  webSocketService.on('project:mission_updated', handleMissionUpdated);
  webSocketService.on('agent:created', handleAgentCreated);
  webSocketService.on('project:staging_cancelled', handleStagingCancelled);
  
  // ... rest of onMounted
});
```

---

## WebSocket Usage Throughout Application

**Not just for staging** - WebSocket is critical infrastructure used for:

1. **Staging Phase**:
   - `project:mission_updated` - Mission appears in real-time
   - `agent:created` - Agents appear as spawned

2. **Execution Phase** (already working):
   - `agent:status_changed` - Agent card status updates
   - `message:received` - Agent-to-agent messaging
   - `job:progress` - Progress bar updates
   - Status transitions (waiting → active → completed)

3. **Control Operations**:
   - `project:staging_cancelled` - Cancellation propagation
   - `orchestrator:instructions_fetched` - Thin client updates

**Conclusion**: WebSocket is NOT optional - it's used extensively for job execution phase. We need to fix the bug, not replace the architecture.

---

## Diagnostic Logging Added

### Log Statements in `tool_accessor.py`

**Mission Update** (5 debug points):
1. `[WEBSOCKET DEBUG] About to broadcast mission_updated for project {project_id}`
2. `[WEBSOCKET DEBUG] httpx imported, creating client for HTTP bridge`
3. `[WEBSOCKET DEBUG] Sending POST to {bridge_url}`
4. `[WEBSOCKET DEBUG] HTTP bridge response: {response.status_code}`
5. `[WEBSOCKET] Broadcasted mission_updated for project {project_id} via HTTP bridge`

**Agent Creation** (5 debug points):
1. `[WEBSOCKET DEBUG] About to broadcast agent:created for {agent_name} ({agent_type})`
2. `[WEBSOCKET DEBUG] httpx imported for agent creation broadcast`
3. `[WEBSOCKET DEBUG] Sending POST to {bridge_url} for agent:created`
4. `[WEBSOCKET DEBUG] HTTP bridge response for agent:created: {response.status_code}`
5. `[WEBSOCKET] Broadcasted agent:created for {agent_name} ({agent_type}) via HTTP bridge`

**Error Logging**: All exceptions now use `exc_info=True` for full traceback

### Log Files to Monitor

- `logs/giljo_mcp.log` - MCP tool execution logs (where HTTP bridge calls appear)
- `logs/api_stdout.log` - FastAPI server logs (where HTTP bridge endpoint logs appear)
- `logs/api_stderr.log` - API errors

### Log Search Commands

**Check if HTTP bridge being called**:
```powershell
Select-String -Path "F:\GiljoAI_MCP\logs\giljo_mcp.log" -Pattern "WEBSOCKET DEBUG" | Select-Object -Last 20
```

**Check HTTP bridge endpoint responses**:
```powershell
Select-String -Path "F:\GiljoAI_MCP\logs\api_stdout.log" -Pattern "ws-bridge" | Select-Object -Last 20
```

**Check for errors**:
```powershell
Select-String -Path "F:\GiljoAI_MCP\logs\giljo_mcp.log" -Pattern "WEBSOCKET ERROR" | Select-Object -Last 10
```

---

## Testing Procedure

### 1. Restart Claude Code MCP Connection

**Why**: MCP server doesn't hot-reload Python files - must restart to load new `tool_accessor.py` code

**How**:
- Close Claude Code
- Reopen Claude Code
- Reconnect to GiljoAI MCP server

### 2. Clear Previous Test Data

Use control panel to clear project to initial state:
```powershell
python F:\GiljoAI_MCP\dev_tools\control_panel.py
```
- Paste project UUID
- Click "Clear Project Initial State"
- This clears: mission, agent jobs, staging status (keeps project + orchestrator)

### 3. Monitor Logs in Real-Time

**Terminal 1** (Watch MCP logs):
```powershell
Get-Content F:\GiljoAI_MCP\logs\giljo_mcp.log -Wait -Tail 50
```

**Terminal 2** (Watch API logs):
```powershell
Get-Content F:\GiljoAI_MCP\logs\api_stdout.log -Wait -Tail 50
```

### 4. Execute Staging

1. Navigate to project Launch tab
2. Click "Stage Project" button
3. **Watch logs in real-time** for `[WEBSOCKET DEBUG]` messages
4. **Watch browser console** for WebSocket event logs

### 5. Analyze Results

**Scenario A**: No `[WEBSOCKET DEBUG]` logs appear
- ❌ MCP server not reloaded OR
- ❌ Code path not being executed (logic bug)

**Scenario B**: `[WEBSOCKET DEBUG]` logs appear but stop at specific point
- ❌ httpx import failure (stops after "About to broadcast")
- ❌ Network/timeout issue (stops after "Sending POST")
- ❌ HTTP bridge endpoint error (shows response status != 200)

**Scenario C**: All `[WEBSOCKET DEBUG]` logs appear with 200 status
- ✅ HTTP bridge working
- ❌ Frontend WebSocket listener issue OR
- ❌ Multi-tenant isolation issue (wrong tenant_key)

**Scenario D**: `[WEBSOCKET ERROR]` logs appear
- 🔥 Exception details will show exact failure point

---

## Known Issues

### Issue 1: MCP Server Module Reloading

**Problem**: Even after restarting Claude Code, MCP server may cache old `tool_accessor.py` module

**Workaround**: 
- Fully close Claude Code (not just restart)
- Wait 5-10 seconds
- Reopen Claude Code

**Verification**: Check log file timestamps - logs should show "httpx imported" immediately after restart

### Issue 2: Port Mismatch

**Problem**: HTTP bridge hardcoded to `localhost:7272` but server may be on different port

**Check**: Verify server port in `config.yaml`:
```yaml
api:
  host: 0.0.0.0
  port: 7272  # <-- Verify this matches HTTP bridge URL
```

**Fix if needed**: Update `bridge_url` in both methods to match actual port

### Issue 3: httpx Not Installed in MCP Environment

**Problem**: MCP server may have separate Python environment without httpx

**Check**: 
```powershell
python -c "import httpx; print(httpx.__version__)"
```

**Fix if needed**:
```powershell
pip install httpx
```

---

## Alternative Approaches Considered

### Option 1: Simple Polling
- ✅ Simpler to implement
- ❌ Inefficient (constant HTTP requests)
- ❌ 1-5 second lag
- ❌ Doesn't scale with multiple agents
- **Verdict**: ❌ Not viable - WebSocket already required for job execution

### Option 2: Server-Sent Events (SSE)
- ✅ Simpler than WebSocket (one-way)
- ✅ Built-in reconnection
- ❌ Still requires similar infrastructure
- ❌ Less flexible than WebSocket
- **Verdict**: ❌ No benefit over fixing WebSocket

### Option 3: Queue + Page Refresh
- ✅ Very simple
- ❌ **Terrible UX** - loses scroll, form state, workflow
- ❌ Breaks active job monitoring
- **Verdict**: ❌ Unacceptable UX degradation

### Option 4: Hybrid (Polling for staging, WebSocket for jobs)
- ❌ Maintains complexity with no real benefit
- ❌ Two systems to maintain
- **Verdict**: ❌ Over-engineered

### **Recommendation: Fix WebSocket Bug**

**Rationale**:
1. WebSocket infrastructure already exists and works for execution phase
2. 90% of WebSocket usage is for job execution (not staging)
3. Real-time agent status updates are critical for UX
4. HTTP bridge approach is architecturally sound
5. Likely simple bug (module not reloaded or httpx issue)

---

## UI Changes Made

### LaunchTab Redesign

**Removed**: Static orchestrator card fixture

**Added**: Clean action button panel

**File**: `frontend/src/components/projects/LaunchTab.vue` (lines 5-71)

**New Layout**:
```vue
<!-- Left Column: Action Buttons Panel -->
<v-col cols="12" md="3" class="mb-4 mb-md-0">
  <v-card elevation="2" class="action-panel pa-4">
    <!-- Stage Project Button (Initial State) -->
    <v-btn v-if="!isStaging && !readyToLaunch" ...>
      Stage Project
    </v-btn>

    <!-- Launch Jobs Button (Ready State) -->
    <v-btn v-if="readyToLaunch" ...>
      Launch Jobs
    </v-btn>

    <!-- Cancel Button -->
    <v-btn v-if="isStaging || readyToLaunch" ...>
      Cancel Staging
    </v-btn>
  </v-card>
</v-col>
```

**Removed Code**: `orchestratorAgent` computed property (lines 421-444) - no longer needed

---

## Orchestrator Auto-Creation Discovery

**File**: `api/endpoints/projects.py` (lines 797-830)

**Behavior**: When project is activated, orchestrator job is automatically created if one doesn't exist

**Code**:
```python
# Check if orchestrator already exists
existing_orch_stmt = select(MCPAgentJob).where(
    MCPAgentJob.project_id == project_id,
    MCPAgentJob.agent_type == "orchestrator",
    MCPAgentJob.tenant_key == current_user.tenant_key,
)
existing_orch_result = await db.execute(existing_orch_stmt)
existing_orchestrator = existing_orch_result.scalar_one_or_none()

if not existing_orchestrator:
    # Create orchestrator job automatically
    orchestrator_job = MCPAgentJob(
        tenant_key=current_user.tenant_key,
        project_id=project_id,
        agent_type="orchestrator",
        agent_name="Orchestrator",
        mission="...",
        status="waiting",
        tool_type="universal",
    )
    # ... create and commit
```

**Impact**: This is why orchestrator appears in Agent Team section even after clearing database - it's intentional persistence behavior.

**Decision**: Keep this behavior - orchestrator should persist in Agent Team tab.

---

## Next Agent Instructions

### Immediate Steps

1. **Verify MCP Server Restart**:
   - User must restart Claude Code MCP connection
   - Check log timestamps to confirm new code loaded

2. **Run Staging Test**:
   - Monitor logs in real-time (both MCP and API logs)
   - Watch browser console for WebSocket events
   - Document which log statements appear

3. **Analyze Log Output**:
   - If no logs: MCP not reloaded → investigate module caching
   - If partial logs: Identify exact failure point
   - If complete logs with 200: Check frontend listener or tenant_key mismatch
   - If error logs: Debug specific exception

4. **Debug Based on Findings**:
   - **httpx import failure**: Install httpx in MCP environment
   - **Network timeout**: Check if API server accessible from MCP process
   - **Port mismatch**: Update `bridge_url` to match `config.yaml`
   - **Frontend listener issue**: Check browser console for event reception
   - **Tenant isolation**: Verify `tenant_key` matches between API and WebSocket client

### If Still Failing After Debug

5. **Test HTTP Bridge Directly**:
```powershell
# Test endpoint directly (replace tenant_key and project_id)
Invoke-RestMethod -Method POST -Uri "http://localhost:7272/api/v1/ws-bridge/emit" `
  -ContentType "application/json" `
  -Body '{"event_type":"test:event","tenant_key":"tk_...","data":{"test":"value"}}'
```

6. **Add Frontend Console Logging**:
   - Verify WebSocket connection state
   - Verify event subscription registration
   - Check if events received but not handled

7. **Consider Process Communication Alternatives**:
   - Unix socket instead of HTTP
   - Redis pub/sub
   - Shared memory queue

### Documentation to Update After Fix

- Add WebSocket troubleshooting guide
- Document HTTP bridge pattern for future MCP tools
- Add MCP module reloading notes to developer guide

---

## References

**Related Handovers**:
- Handover 0111 - MCP-to-WebSocket HTTP Bridge (original implementation)

**Key Files**:
- `src/giljo_mcp/tools/tool_accessor.py` - MCP tools with HTTP bridge calls
- `api/endpoints/websocket_bridge.py` - HTTP bridge endpoint
- `frontend/src/components/projects/LaunchTab.vue` - WebSocket event listeners
- `api/dependencies/websocket.py` - WebSocketManager implementation

**Architecture Docs**:
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - WebSocket architecture overview
- `docs/guides/thin_client_migration_guide.md` - Thin client pattern

---

**Status**: 🔧 Debug logging added, awaiting test results with MCP server restart
