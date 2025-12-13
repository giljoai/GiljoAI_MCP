# Handover 0291: Staging Complete Broadcast Signal

## Status: READY FOR IMPLEMENTATION
## Priority: HIGH
## Type: Feature Implementation
## Supersedes: Handover 0287 (watcher approach unreliable)

---

## Problem Statement

After staging completes, the "Launch Jobs" button does NOT enable dynamically - it requires page refresh.

**Current Behavior:**
1. User clicks "Stage Project"
2. Button changes to "Orchestrator Active" (works via 0290 payload normalization)
3. Orchestrator runs in terminal, creates mission and spawns agents
4. "Launch Jobs" button stays disabled
5. User must refresh page to enable "Launch Jobs"

**Expected Behavior:**
- "Launch Jobs" enables automatically when orchestrator finishes staging

---

## Root Cause

Handover 0287's implicit detection approach (watching `orchestratorMission` + `agents` changes) is unreliable because:
1. WebSocket events may arrive before store state is fully updated
2. Vue reactivity timing issues with deep watchers
3. No explicit signal that staging is COMPLETE (vs still in progress)

---

## Solution: Explicit Broadcast Message Signal

**Approach:** Orchestrator sends a broadcast message to ALL agents when staging completes.

### Why This Works

1. **Explicit > Implicit**: Message in system = definitive proof staging is done
2. **Auditable**: Message appears in MCP message center
3. **UI Visible**: Shows in JobsTab as:
   - "Messages Sent: 1" for orchestrator
   - "Messages Waiting: 1" for all other agents
4. **WebSocket Wired**: `message:sent` event already emitted (MessageService line 143-160)
5. **Simple Detection**: Frontend listens for FIRST `message:sent` from orchestrator

---

## Implementation Plan

### Phase 1: Modify Staging Prompt

**File:** `src/giljo_mcp/thin_prompt_generator.py`

**Location:** `_build_thin_prompt()` method (line 477-520)

**Change:** Add Step 6 to STARTUP SEQUENCE:

```
STARTUP SEQUENCE:
1. Verify MCP: mcp__giljo-mcp__health_check()
2. Fetch context: mcp__giljo-mcp__get_orchestrator_instructions(...)
3. CREATE MISSION: Analyze requirements → Generate execution plan
4. PERSIST MISSION: mcp__giljo-mcp__update_project_mission(...)
5. SPAWN AGENTS: mcp__giljo-mcp__spawn_agent_job() for each specialist
6. SIGNAL COMPLETE: Send broadcast message to all agents:
   - Use: mcp__giljo-mcp__send_message()
   - To: "all" (broadcasts to all agents in project)
   - Content: "STAGING_COMPLETE: Mission created, {N} agents spawned: {list}"
   - This triggers UI to enable Launch Jobs button
```

### Phase 2: Verify MCP Tool Support

**File:** `src/giljo_mcp/services/message_service.py`

**Status:** Already implemented (lines 173-250)

The `broadcast()` method:
- Sends message to all agents in project
- Sets `message_type="broadcast"`
- Emits WebSocket event via `broadcast_message_sent()` (line 146)

**WebSocket Event:** `message:sent` (api/websocket.py line 980)

### Phase 3: Frontend - Listen for Staging Complete

**File:** `frontend/src/components/projects/ProjectTabs.vue`

**Add handler in `onMounted()`:**

```javascript
// Listen for orchestrator's first broadcast (staging complete signal)
const handleStagingCompleteMessage = (data) => {
  // Only process if this is for our project
  if (data.project_id !== projectId.value) return

  // Check if message is from orchestrator and contains staging complete marker
  const fromOrchestrator = data.from_agent === 'orchestrator' ||
                           data.message_type === 'broadcast'
  const isStagingComplete = data.content_preview?.includes('STAGING_COMPLETE') ||
                            data.content?.includes('STAGING_COMPLETE')

  if (fromOrchestrator && isStagingComplete) {
    console.log('[ProjectTabs] Staging complete signal received via broadcast')
    store.setStagingComplete(true)
  }
}

on('message:sent', handleStagingCompleteMessage)
```

### Phase 4: Update Store (if not done in 0287)

**File:** `frontend/src/stores/projectTabs.js`

Ensure these exist:
```javascript
// State
stagingComplete: false,

// Getter
readyToLaunch(state) {
  return (state.orchestratorMission && state.agents.length > 0 && !state.isStaging)
         || state.stagingComplete
}

// Action
setStagingComplete(complete) {
  this.stagingComplete = complete
  if (complete) {
    this.isStaging = false  // Also clear staging flag
  }
}
```

### Phase 5: Verify JobsTab Message Columns

**File:** `frontend/src/components/projects/JobsTab.vue`

The message columns already exist (lines 73-85):
- "Messages Sent" - `getMessagesSent(agent)`
- "Messages Waiting" - `getMessagesWaiting(agent)`
- "Messages Read" - `getMessagesRead(agent)`

Verify these functions:
1. Increment when `message:sent` event received
2. Decrement waiting / increment read when `message:acknowledged` received

---

## Message Format

Orchestrator sends:
```
STAGING_COMPLETE: Mission created, 3 agents spawned: [implementer-1, tester-1, analyzer-1]
```

This message:
1. Appears in MCP message center
2. Shows "Messages Sent: 1" for orchestrator row in JobsTab
3. Shows "Messages Waiting: 1" for all other agent rows
4. Triggers `message:sent` WebSocket event
5. Frontend detects "STAGING_COMPLETE" marker → enables Launch Jobs button

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `src/giljo_mcp/thin_prompt_generator.py` | Add Step 6 to STARTUP SEQUENCE | ~507-520 |
| `frontend/src/components/projects/ProjectTabs.vue` | Add `message:sent` handler | onMounted |
| `frontend/src/stores/projectTabs.js` | Verify stagingComplete state (from 0287) | state/getters |

---

## WebSocket Events Flow

```
1. Orchestrator calls send_message() MCP tool
   └─► MessageService.send_message() (message_service.py:75-171)
       └─► broadcast_message_sent() (message_service.py:143-160)
           └─► websocket.broadcast_message_sent() (websocket.py:952-1001)
               └─► Event: "message:sent" with payload:
                   {
                     type: "message:sent",
                     data: {
                       message_id: "uuid",
                       job_id: "project_id",
                       from_agent: "orchestrator",
                       to_agent: null,  // broadcast
                       message_type: "broadcast",
                       content_preview: "STAGING_COMPLETE: ..."
                     }
                   }

2. Frontend receives "message:sent" event
   └─► ProjectTabs handleStagingCompleteMessage()
       └─► Detects "STAGING_COMPLETE" in content
           └─► store.setStagingComplete(true)
               └─► readyToLaunch getter returns true
                   └─► Launch Jobs button enables
```

---

## Testing Plan

### Manual Test
1. Open project page, go to Launch tab
2. Click "Stage Project"
3. Paste prompt into Claude Code terminal
4. Watch orchestrator:
   - Create mission
   - Spawn agents
   - Send "STAGING_COMPLETE" broadcast
5. Verify in UI:
   - Orchestrator row shows "Messages Sent: 1"
   - Other agent rows show "Messages Waiting: 1"
   - "Launch Jobs" button enables (NO REFRESH)

### Unit Tests
```javascript
describe('Staging Complete Signal (0291)', () => {
  it('enables Launch Jobs when message:sent received with STAGING_COMPLETE', async () => {
    // Setup store with orchestrator + agents but stagingComplete=false
    // Simulate message:sent event
    // Assert store.stagingComplete === true
    // Assert readyToLaunch === true
  })

  it('ignores non-orchestrator messages', async () => {
    // Simulate message:sent from implementer
    // Assert stagingComplete unchanged
  })

  it('ignores messages without STAGING_COMPLETE marker', async () => {
    // Simulate regular orchestrator message
    // Assert stagingComplete unchanged
  })
})
```

---

## Acceptance Criteria

- [ ] Staging prompt includes Step 6: send broadcast message
- [ ] Orchestrator sends "STAGING_COMPLETE" broadcast after spawning agents
- [ ] JobsTab shows message counts correctly
- [ ] `message:sent` WebSocket event triggers frontend handler
- [ ] Frontend detects marker and enables Launch Jobs button
- [ ] No page refresh required
- [ ] Works in both Claude Code mode and multi-terminal mode

---

## Estimated Effort

- Backend (prompt update): 15 minutes
- Frontend (WebSocket handler): 30 minutes
- Testing: 30 minutes
- Total: ~1.5 hours

---

## Dependencies

- Handover 0290 (payload normalization): COMPLETE
- MessageService.send_message(): EXISTS
- WebSocket `message:sent` event: EXISTS
- JobsTab message columns: EXISTS

---

## Notes

This approach is superior to 0287 because:
1. **Explicit signal** - message in system proves staging done
2. **Visible feedback** - user sees message counts change
3. **Auditable** - message stored in database
4. **Simple detection** - just check for marker string
5. **No timing issues** - message event is atomic

The orchestrator effectively "announces" completion rather than the frontend "guessing" based on state changes.
