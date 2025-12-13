# Handover 0287: Launch Button Staging Complete Signal

## Status: PENDING
## Priority: HIGH
## Type: Feature Implementation
## Depends On: Handover 0286 (WebSocket wiring)

---

## Problem Statement

After clicking "Stage Project", the button correctly changes to "Orchestrator Active", but the "Launch Jobs" button does **not enable dynamically** - it requires a page refresh.

**Current Behavior:**
1. User clicks "Stage Project"
2. Button changes to "Orchestrator Active" (works)
3. Orchestrator runs in terminal, creates mission and spawns agents
4. "Launch Jobs" button stays disabled
5. User must refresh page to enable "Launch Jobs"

**Expected Behavior:**
- "Launch Jobs" enables automatically when staging completes

---

## Root Cause Analysis

The `readyToLaunch` computed property requires:
```javascript
readyToLaunch(state) {
  return state.orchestratorMission && state.agents.length > 0 && !state.isStaging
}
```

**The Gap:** There is no explicit signal from the orchestrator that staging is complete. The frontend relies on:
- `project:mission_updated` WebSocket event (to set `orchestratorMission`)
- `agent:created` WebSocket events (to populate `agents` array)

But there's no guarantee these events are received or that they indicate staging is truly complete.

---

## Solution: Orchestrator Self-Message Signal

**Approach:** Orchestrator sends an MCP message to itself when staging completes. This:
1. Uses existing messaging infrastructure
2. Creates an auditable record
3. Triggers WebSocket event
4. Frontend detects message and enables Launch button

### Message Content
```
"Staging complete. Mission created and {N} agents spawned. Ready to launch."
```

---

## Implementation Plan

### Phase 1: Backend - Ensure Message Events Work (Handover 0286)

This handover depends on 0286 fixing the WebSocket event name mismatches first.

### Phase 2: Update Orchestrator Staging Prompt

Modify the orchestrator's staging instructions to include a final step:

**File:** `src/giljo_mcp/thin_prompt_generator.py` or staging prompt template

Add to orchestrator's 7-task workflow:
```
TASK 8: Signal staging complete
- Call send_message() MCP tool
- To: self (orchestrator job_id)
- Content: "Staging complete. Mission created and {N} agents spawned. Ready to launch."
- This triggers WebSocket event for UI update
```

### Phase 3: Frontend - Listen for Staging Complete Signal

**File:** `frontend/src/components/projects/ProjectTabs.vue`

Add handler for orchestrator receiving a message:

```javascript
const handleStagingComplete = (data) => {
  // Check if message is to orchestrator and contains "Staging complete"
  const orchestrator = store.agents.find(a => a.agent_type === 'orchestrator')
  if (!orchestrator) return

  if (data.to_agent === orchestrator.id &&
      data.content?.includes('Staging complete')) {
    // Force readyToLaunch re-evaluation
    // The message itself confirms mission + agents exist
    store.setStagingComplete(true)
  }
}

// In onMounted:
on('message:new', handleStagingComplete)
```

### Phase 4: Update Store

**File:** `frontend/src/stores/projectTabs.js`

Add state and getter:

```javascript
// State
stagingComplete: false,

// Getter - modify readyToLaunch
readyToLaunch(state) {
  // Original condition OR explicit staging complete signal
  return (state.orchestratorMission && state.agents.length > 0 && !state.isStaging)
         || state.stagingComplete
}

// Action
setStagingComplete(value) {
  this.stagingComplete = value
}
```

---

## Alternative Approach: Simpler Detection

Instead of adding a new message, detect staging complete from existing events:

**Trigger:** When orchestrator has:
1. Mission set (from `project:mission_updated`)
2. At least one non-orchestrator agent (from `agent:created`)
3. Orchestrator status is 'working' (from `agent:status_changed`)

```javascript
// In ProjectTabs.vue
watch(
  () => [store.orchestratorMission, store.agents],
  ([mission, agents]) => {
    const hasOrchestrator = agents.some(a => a.agent_type === 'orchestrator')
    const hasSpecialists = agents.some(a => a.agent_type !== 'orchestrator')

    if (mission && hasOrchestrator && hasSpecialists) {
      // Staging is implicitly complete
      store.setStagingComplete(true)
    }
  },
  { deep: true }
)
```

This approach requires no backend changes but is less explicit.

---

## Recommended Approach

**Use the message-based signal** because:
1. Explicit > implicit
2. Creates audit trail
3. Consistent with MCP messaging architecture
4. Orchestrator knows definitively when it's done

---

## Acceptance Criteria

- [ ] Orchestrator sends "Staging complete" message to itself after spawning agents
- [ ] WebSocket event fires when message is sent
- [ ] Frontend receives event and enables "Launch Jobs" button
- [ ] No page refresh required
- [ ] Works in both Claude Code mode and multi-terminal mode

---

## Files to Modify

1. `src/giljo_mcp/thin_prompt_generator.py` - Add Task 8 to staging workflow
2. `frontend/src/components/projects/ProjectTabs.vue` - Add message handler
3. `frontend/src/stores/projectTabs.js` - Add stagingComplete state

---

## Testing Plan

1. Open project page, go to Launch tab
2. Click "Stage Project"
3. Paste prompt into terminal
4. Watch orchestrator create mission and spawn agents
5. Verify "Launch Jobs" enables automatically (no refresh)
6. Check browser console for WebSocket events
7. Check backend logs for message creation

---

## Dependencies

- **Handover 0286**: WebSocket event names must be fixed first
  - `message:new` event must be emitted when messages are created
  - Without this, the staging complete signal won't reach frontend

---

## Estimated Effort

- Backend (prompt update): 30 minutes
- Frontend (handler + store): 1 hour
- Testing: 30 minutes
- Total: 2 hours

---

## Notes

This is the final piece to complete the staging-to-launch flow. Once implemented:
1. User clicks "Stage Project"
2. Orchestrator runs, creates mission, spawns agents
3. Orchestrator sends "Staging complete" message
4. Frontend receives message via WebSocket
5. "Launch Jobs" button enables automatically
6. User clicks "Launch Jobs" to begin execution

The user experience will be seamless with no manual page refreshes required.
