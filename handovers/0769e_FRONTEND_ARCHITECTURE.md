# 0769e: Frontend Architecture Hardening

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 5 of 7
**Branch:** `feature/0769-quality-sprint`
**Priority:** MEDIUM — fragility reduction
**Estimated Time:** 2 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (sections F5, F6, F8, F10)
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

The fragility analysis identified several architectural risks in the frontend: a WebSocket reconnection race condition, a mega-hub event router (575 lines routing 30 event types through 13 stores), duplicated payload normalization, and a CORS scoping bug. This phase hardens these areas.

---

## Scope

### Task 1: Split websocketEventRouter.js (575 lines -> domain files)

**File:** `frontend/src/stores/websocketEventRouter.js`

**Problem:** Single file imports 13 stores and maps ~30 event types. Changed 18 times in 2 months. Any handler bug can crash all event routing.

**Split plan:** Create domain-specific route files that the main router composes:

```
frontend/src/stores/
  websocketEventRouter.js          (keep as thin composer, ~100 lines)
  eventRoutes/
    agentEventRoutes.js            (agent job events)
    messageEventRoutes.js          (message events)
    projectEventRoutes.js          (project events)
    systemEventRoutes.js           (setup, config, notifications)
```

Each route file exports a function `registerRoutes(router)` or an event-to-handler map. The main router composes them.

**CRITICAL:** Run `npx vitest run -- tests/stores/websocketEventRouter.spec.js` before and after to ensure no regression.

### Task 2: Fix WebSocket Reconnection Race Condition

**File:** `frontend/src/stores/websocket.js`, lines 319-353

**Problem:** The reconnect logic uses `setTimeout` + `await connect()`. If `handleDisconnect` fires again during the reconnect delay, a second reconnect timer starts. No mutex prevents overlapping reconnection attempts.

**Fix:** Add a `reconnectTimer` ref and clear it on each new attempt:

```javascript
const reconnectTimer = ref(null)

function handleDisconnect() {
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value)
  }
  reconnectTimer.value = setTimeout(async () => {
    reconnectTimer.value = null
    await connect()
  }, delay)
}
```

Also consider adding a `reconnectInFlight` flag that `connect()` checks to prevent overlapping connection attempts.

### Task 3: Fix Payload Normalization Duplication

**Files:**
- `frontend/src/stores/websocket.js`, lines 427-438
- `frontend/src/stores/websocketEventRouter.js`, lines 466-480

**Problem:** Both files normalize WebSocket payloads (merging nested `data` to top level). If one changes and the other doesn't, events get double-normalized or inconsistently shaped.

**Fix:** Create a shared utility:
```
frontend/src/utils/normalizeWebsocketPayload.js
```

Import and use in both locations. Remove the duplicate logic.

### Task 4: Fix CORS Origin Resolution Scoping Bug

**File:** `api/app.py`, around line 288

**Problem:** The `config` variable is used outside its `try` block. If the config read on line 252 failed, `config` would be undefined, causing a `NameError` on line 288 when checking `network_mode`.

**Fix:** Move the `network_mode` resolution inside the successful config-read block, or set a default `network_mode = "localhost"` before the try block.

---

## What NOT To Do

- Do NOT change the WebSocket message protocol or event types
- Do NOT rename event type strings
- Do NOT modify backend WebSocket code (except the CORS fix in app.py)
- Do NOT change the store APIs (actions, getters) — only internal routing

---

## Acceptance Criteria

- [ ] `websocketEventRouter.js` <= 150 lines (down from 575)
- [ ] Domain route files created and functional
- [ ] WebSocket reconnect has mutex preventing duplicate connections
- [ ] Payload normalization happens in exactly one place (shared utility)
- [ ] CORS scoping bug fixed
- [ ] `npx vitest run` passes with 0 failures
- [ ] `npm run build` succeeds
- [ ] WebSocket event routing tests still pass

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0769d's `notes_for_next`

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Tasks 1-4. Run tests after each task.

### Step 4: Update Chain Log
In `notes_for_next`, include:
- New file paths for event route modules
- normalizeWebsocketPayload utility path
- Any event handler changes

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
