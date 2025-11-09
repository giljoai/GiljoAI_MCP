# ACTIVE DEBUGGING SESSION: WebSocket Real-Time Mission Updates

**Status**: IN PROGRESS - Needs Fresh Agent
**Date**: 2025-11-08 03:30 AM
**Priority**: HIGH - Core feature broken

---

## PROBLEM STATEMENT

**Initial Issue**: When an MCP tool calls `update_project_mission()` to update a project's mission text, the frontend UI does NOT automatically refresh to show the new mission. Users must manually refresh the browser page to see changes.

**Expected Behavior**: Mission field should update in real-time via WebSocket broadcast when MCP tool writes to database.

**Actual Behavior**: Database updates successfully, but WebSocket broadcast reaches **0 clients** instead of the connected frontend client.

---

## HOW TO TEST

### Test Command (Use MCP Tool)
```javascript
// In Claude Code or Codex CLI with GiljoAI MCP configured:
mcp__giljo-mcp__update_project_mission({
  project_id: "ce9015f5-d521-449c-9a89-66a9055436c8",
  mission: "Hello World #14 - Testing real-time updates"
})
```

### Expected Result
- Mission text appears in UI **immediately** without page refresh
- Backend logs show: `WebSocket event emitted: project:mission_updated to 1 client(s)`

### Current Result (BROKEN)
- Mission text only appears after manual page refresh
- Backend logs show: `WebSocket event emitted: project:mission_updated to 0 client(s)`
- Reason: **Tenant key mismatch** - Client has `tenant=default`, broadcast targets `tenant=tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0`

---

## ROOT CAUSE ANALYSIS

### The Problem Chain

1. **WebSocket connects in "setup mode"** instead of authenticated mode
2. Setup mode assigns `tenant_key="default"`
3. Actual broadcast uses correct `tenant_key="tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0"`
4. Tenant keys don't match → broadcast filtered out → 0 clients reached

### Why Setup Mode is Triggered

**File**: `api/auth_utils.py:76-84`

```python
# Check setup state
setup_state = await get_setup_state(db)
database_initialized = setup_state.get("database_initialized", True)

if not database_initialized:
    logger.info("WebSocket connection allowed: initial setup mode (database not initialized)")
    return {"authenticated": True, "context": "setup"}
```

**Issue**: `get_setup_state(db)` is being called with `db=None`, which makes it return `database_initialized=False`, even though the database IS initialized (all HTTP API calls work fine with JWT auth).

### Latest Log Evidence (03:30:11)

```
03:30:11 - INFO - WebSocket connection allowed: initial setup mode (database not initialized)
03:30:11 - INFO - [WS AUTH DEBUG] auth_result keys: ['authenticated', 'context'], user_info keys: [], tenant_key=default
03:30:11 - INFO - WebSocket connected: client_1762590611869_hyz1vxbht (auth_type: setup)
```

**Meanwhile, HTTP requests work perfectly**:
```
03:30:11 - INFO - [AUTH] JWT SUCCESS - User: patrik, Tenant: tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0
```

---

## INVESTIGATION HISTORY

### Fix Attempt #1: EventBus (FAILED)
**Location**: `src/giljo_mcp/tools/project.py:379-425`
**Attempted**: Use EventBus to broadcast WebSocket events
**Why Failed**: MCP tools run in separate process from FastAPI, can't access EventBus directly

**Solution**: Replaced with HTTP bridge pattern using `httpx.AsyncClient()` to POST to `/api/v1/ws-bridge/emit`
**Result**: HTTP bridge works (200 OK), but still broadcasts to 0 clients

---

### Fix Attempt #2: WebSocket Manager Exposure (FIXED)
**Location**: `api/app.py:500`
**Error**: `AttributeError: 'WebSocketDependency' object has no attribute 'ws_manager'`
**Fix**:
```python
# Expose websocket_manager on app.state for dependency injection
app.state.websocket_manager = state.websocket_manager
```
**Result**: HTTP bridge endpoint now has access to WebSocket manager

---

### Fix Attempt #3: JWT Cookie Extraction (FAILED - Wrong Approach)
**Location**: `frontend/src/layouts/DefaultLayout.vue:100-107`
**Attempted**: Extract JWT from `access_token` cookie and pass as query parameter
**Why Failed**:
1. `access_token` is an **httpOnly cookie** - JavaScript cannot read it via `document.cookie`
2. Cross-origin issue - frontend at `localhost:7274`, backend at `10.1.0.164:7272`
3. Browser security prevents JavaScript from accessing httpOnly cookies

**Evidence**:
```javascript
console.log('[DefaultLayout] All cookies:', cookies)  // Array(1)
console.log('[DefaultLayout] JWT cookie found:', jwtCookie)  // undefined
```

---

### Fix Attempt #4: Automatic Cookie Authentication (CURRENT)
**Location**: `frontend/src/layouts/DefaultLayout.vue:100-102`
**Approach**: Remove manual cookie extraction, let browser send httpOnly cookie automatically
**Code**:
```javascript
// Connect WebSocket - browser will automatically send httpOnly access_token cookie
await wsStore.connect()
console.log('[DefaultLayout] WebSocket connected with automatic cookie authentication')
```

**Backend Support**: `api/auth_utils.py:91-110` already reads `access_token` from WebSocket Cookie header automatically

**Current Status**: Browser sends cookie automatically, but backend still treats connection as "setup mode" due to `get_setup_state()` returning `database_initialized=False`

---

## DIAGNOSTIC LOGS ADDED

### Backend (`api/auth_utils.py:78`)
```python
logger.info(f"[WS SETUP DEBUG] db={db}, setup_state={setup_state}, database_initialized={database_initialized}")
```

### Backend (`api/app.py:865`)
```python
logger.info(f"[WS AUTH DEBUG] auth_result keys: {list(auth_result.keys())}, user_info keys: {list(user_info.keys())}, tenant_key={tenant_key_from_user}")
```

### Backend (`api/endpoints/websocket_bridge.py:116-126`)
```python
logger.info(f"[BRIDGE DEBUG] Total active connections: {len(ws_dep.manager.active_connections)}, Target tenant: {request.tenant_key}")
for client_id, ws in ws_dep.manager.active_connections.items():
    auth_context = ws_dep.manager.auth_contexts.get(client_id, {})
    client_tenant = auth_context.get("tenant_key")
    logger.info(f"[BRIDGE DEBUG] Client {client_id[:8]}: tenant={client_tenant}, target={request.tenant_key}, match={client_tenant == request.tenant_key}")
```

---

## KEY FILES MODIFIED

1. **`api/app.py:500`** - Expose websocket_manager for dependency injection
2. **`api/app.py:865`** - Add WS AUTH DEBUG logging
3. **`api/auth_utils.py:78`** - Add WS SETUP DEBUG logging
4. **`api/endpoints/websocket_bridge.py:103-104`** - Fix attribute name `ws_manager` → `manager`
5. **`api/endpoints/websocket_bridge.py:116-126`** - Add BRIDGE DEBUG logging
6. **`src/giljo_mcp/tools/project.py:379-425`** - Replace EventBus with HTTP bridge
7. **`frontend/src/layouts/DefaultLayout.vue:100-102`** - Rely on automatic cookie authentication

---

## NEXT STEPS FOR FRESH AGENT

### Immediate Investigation Needed

**Question**: Why is `get_setup_state(db)` returning `database_initialized=False` when `db` session is passed?

**Check**:
1. Read `api/app.py` lines 848-855 - Is database session being created correctly for WebSocket endpoint?
2. Read `api/dependencies/setup.py` - What does `get_setup_state()` do when `db=None` vs `db=session`?
3. Add debug logging to see if `db` is actually `None` when `authenticate_websocket()` is called

### Hypothesis

The WebSocket endpoint (`api/app.py:839-898`) creates a database session:
```python
session = None
session_cm = None
if state.db_manager:
    session_cm = state.db_manager.get_session_async()
    session = await session_cm.__aenter__()
```

But `get_setup_state(db=session)` might be returning wrong value, OR the session isn't being passed correctly to `authenticate_websocket()`.

### Test After Fix

1. Restart backend (to pick up new logging)
2. Hard refresh browser (Ctrl+Shift+R)
3. Check backend logs for `[WS SETUP DEBUG]` line - what is `db` value?
4. Run MCP test: `update_project_mission()` with "Hello World #14"
5. Check if broadcast reaches **1 client** instead of 0
6. Verify mission text updates in UI without manual refresh

---

## PROJECT CONTEXT

**User**: patrik
**Tenant**: tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0
**Project**: Project Start (ID: ce9015f5-d521-449c-9a89-66a9055436c8)
**Backend**: Running at http://10.1.0.164:7272
**Frontend**: Running at http://10.1.0.164:7274 (Vite dev server)

**MCP Configuration**: Working - successfully writes to database
**HTTP API Auth**: Working - JWT cookies authenticate correctly
**WebSocket Auth**: BROKEN - Connects in setup mode with wrong tenant_key

---

## ADDITIONAL CONTEXT

### How WebSocket Flow Works

1. **Frontend connects**: `await wsStore.connect()` in `DefaultLayout.vue`
2. **Browser sends**: Automatic Cookie header with `access_token=<JWT>`
3. **Backend authenticates**: `authenticate_websocket()` in `auth_utils.py` extracts token from Cookie header
4. **Backend validates**: `validate_jwt_token()` returns user info with `tenant_key`
5. **Connection stored**: WebSocket manager stores `auth_context` with `tenant_key`
6. **MCP writes mission**: Calls `update_project_mission()`
7. **HTTP bridge called**: POSTs to `/api/v1/ws-bridge/emit` with event and `tenant_key`
8. **Broadcast filtered**: Only clients with matching `tenant_key` receive event

**Current Failure Point**: Step 3 - `authenticate_websocket()` returns early with setup mode before extracting JWT token

---

## MONITORING COMMANDS

```powershell
# Watch backend logs for WebSocket activity
powershell -Command "Get-Content 'F:\GiljoAI_MCP\logs\api_stdout.log' -Tail 0 -Wait | Select-String -Pattern 'WS SETUP DEBUG|WS AUTH DEBUG|BRIDGE DEBUG|mission_updated'"

# Check recent WebSocket connections
powershell -Command "Get-Content 'F:\GiljoAI_MCP\logs\api_stdout.log' | Select-String -Pattern 'WebSocket connected' | Select-Object -Last 5"

# Check broadcast results
powershell -Command "Get-Content 'F:\GiljoAI_MCP\logs\api_stdout.log' | Select-String -Pattern 'WebSocket event emitted' | Select-Object -Last 5"
```

---

## SUCCESS CRITERIA

✅ Backend logs show: `WebSocket authenticated via JWT: <user_id>`
✅ Backend logs show: `[WS AUTH DEBUG] ... tenant_key=tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0`
✅ Backend logs show: `WebSocket event emitted: project:mission_updated to 1 client(s)`
✅ Frontend UI updates mission text **automatically** without manual refresh

---

**Handover to**: Next debugging agent
**Resume from**: Investigate why `database_initialized=False` when it should be `True`
**Priority**: Critical - Blocking real-time updates feature
