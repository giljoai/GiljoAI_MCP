# Handover 0411: JobsTab Duration Column and UX Improvements

**Status**: ✅ ARCHIVED
**Priority**: MEDIUM
**Commit**: `910a20db`
**Created**: 2026-01-09
**Archived**: 2026-01-17

---

## Completion Summary

**What Was Built**:
- Duration column with live elapsed time tracking (updates every second)
- Pulsing "Working" animation for active agents
- Improved sort order prioritizing active work (working → failed → blocked → waiting → complete)

**Key Files Modified**:
- `frontend/src/components/projects/JobsTab.vue` (duration column, pulse animation, timer lifecycle)
- `frontend/src/stores/agentJobsStore.js` (new sort order with timestamp-based secondary sorting)

**No Backend Changes Required** - Uses existing `started_at` and `completed_at` fields.

**Final Status**: Production ready. All changes committed.

---

## Summary

Added Duration column to JobsTab agent table with live elapsed time tracking, pulsing animation for working agents, and improved sort order prioritizing active work.

---

## Changes Implemented

### 1. Duration Column

**Purpose**: Show time elapsed from when agent started working to completion.

| Agent State | Display |
|-------------|---------|
| Not started (`started_at` null) | `---` |
| Working (active) | Live elapsed time, updates every second |
| Completed | Final duration |

**Format Examples**:
- `< 1 minute`: `45s`
- `1-60 minutes`: `3m 22s`
- `> 1 hour`: `1h 23m`

**Implementation**:
```javascript
// Live timer - updates every second
const now = ref(Date.now())
let durationTimer = null

onMounted(() => {
  durationTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
})

// Format function
function formatDuration(agent) {
  if (!agent.started_at) return '---'

  const start = new Date(agent.started_at).getTime()
  const end = agent.completed_at
    ? new Date(agent.completed_at).getTime()
    : now.value
  const durationMs = end - start

  // Format based on duration length
  if (durationMs < 60000) return `${Math.round(durationMs / 1000)}s`
  if (durationMs < 3600000) {
    const mins = Math.floor(durationMs / 60000)
    const secs = Math.round((durationMs % 60000) / 1000)
    return `${mins}m ${secs}s`
  }
  const hours = Math.floor(durationMs / 3600000)
  const mins = Math.floor((durationMs % 3600000) / 60000)
  return `${hours}h ${mins}m`
}
```

### 2. Pulsing "Working" Animation

**Purpose**: Visual indicator that agent is actively working.

**CSS Animation**:
```scss
&.status-working-pulse {
  animation: pulse-glow 1.5s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% {
    opacity: 1;
    text-shadow: 0 0 4px rgba(255, 215, 0, 0.4);
  }
  50% {
    opacity: 0.6;
    text-shadow: 0 0 12px rgba(255, 215, 0, 0.8);
  }
}
```

**Binding**:
```html
<td class="status-cell"
    :class="{ 'status-working-pulse': agent.status === 'working' }">
```

### 3. Improved Sort Order

**Previous Order**:
1. Failed
2. Blocked
3. Waiting
4. Working
5. Complete

**New Order** (active work prioritized):
1. **Working** (most recently started first)
2. Failed
3. Blocked
4. Waiting
5. **Complete** (most recently completed first)
6. Cancelled
7. Decommissioned

**Implementation** (`agentJobsStore.js`):
```javascript
const sortedJobs = computed(() => {
  const priority = {
    working: 1,
    failed: 2,
    blocked: 3,
    waiting: 4,
    complete: 5,
    completed: 5,  // alias
    cancelled: 6,
    decommissioned: 7,
  }

  const list = Array.from(jobsById.value.values())
  list.sort((a, b) => {
    const aPriority = priority[a.status] || 999
    const bPriority = priority[b.status] || 999

    if (aPriority !== bPriority) return aPriority - bPriority

    // Working: most recently started on top
    if (a.status === 'working' && b.status === 'working') {
      const aStarted = a.started_at ? new Date(a.started_at).getTime() : 0
      const bStarted = b.started_at ? new Date(b.started_at).getTime() : 0
      if (aStarted !== bStarted) return bStarted - aStarted
    }

    // Completed: most recently completed on top
    if ((a.status === 'complete' || a.status === 'completed') &&
        (b.status === 'complete' || b.status === 'completed')) {
      const aCompleted = a.completed_at ? new Date(a.completed_at).getTime() : 0
      const bCompleted = b.completed_at ? new Date(b.completed_at).getTime() : 0
      if (aCompleted !== bCompleted) return bCompleted - aCompleted
    }

    // Orchestrators first within same status
    const aIsOrch = a.agent_type === 'orchestrator' ? 0 : 1
    const bIsOrch = b.agent_type === 'orchestrator' ? 0 : 1
    if (aIsOrch !== bIsOrch) return aIsOrch - bIsOrch

    return (a.agent_type || '').localeCompare(b.agent_type || '')
  })

  return list
})
```

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/components/projects/JobsTab.vue` | Duration column, pulse animation, timer lifecycle |
| `frontend/src/stores/agentJobsStore.js` | New sort order with timestamp-based secondary sorting |

---

## Data Dependencies

Uses existing fields from backend (no backend changes required):

| Field | Source | Used For |
|-------|--------|----------|
| `started_at` | `AgentExecution.started_at` | Duration start time |
| `completed_at` | `AgentExecution.completed_at` | Duration end time |
| `status` | `AgentExecution.status` | Sort priority, pulse trigger |

These fields are already:
- Set by `OrchestrationService.update_agent_status()`
- Emitted via WebSocket `agent:status_changed` events
- Returned in job list API response

---

## Testing Notes

- Duration updates every second for working agents
- Timer is cleaned up on component unmount (no memory leaks)
- Sort order persists across WebSocket updates
- Pulse animation only applies to `working` status

---

## Related

- **0410**: Message optimization (message_check tool) - companion handover
- **0243c**: JobsTab dynamic status fix - foundation for status tracking
- **0379b**: Agent/Job domain migration - established agentJobsStore pattern
