# Handover 0819b: Notification Lifecycle Management

**Date:** 2026-03-14
**From Agent:** Research/Planning Session
**To Agent:** Next Session (tdd-implementor)
**Priority:** Medium
**Estimated Complexity:** 1-2 hours
**Status:** Not Started
**Edition Scope:** CE

## Task Summary

When a project reaches a terminal state (`completed`, `terminated`, `cancelled`), all notifications associated with that project should be removed from the notification bell. Currently notifications accumulate indefinitely until page refresh, with no removal mechanism.

Also add a store reset on logout as defense-in-depth for tenant isolation.

## Context and Background

- Notification system is entirely frontend/in-memory (Pinia store, no database table)
- Notifications carry optional `metadata.project_id` linking them to a project
- Health alerts (`agent_health`, `agent_silent`) include project context via `metadata.project_id` (handover 0259)
- Connection notifications (`connection_lost`, `connection_restored`) do NOT have `project_id` -- these are system-level and must NOT be cleared
- The store currently has: `addNotification`, `markAsRead`, `markAllAsRead` -- but NO removal/clearing actions
- Three UI paths transition projects to terminal states -- all three need notification clearing

## Technical Details

### File 1: `frontend/src/stores/notifications.js` (87 lines total)

**Full current store structure:**
```javascript
// State: notifications = ref([])
// Getters: unreadCount, agentHealthNotifications, badgeColor, sortedNotifications
// Actions: addNotification(notification), markAsRead(id), markAllAsRead()
// Return block at line 72-86 exports all of the above
```

**Notification schema (created by `addNotification` at line 44-56):**
```javascript
{
  id: crypto.randomUUID(),
  type: 'agent_health' | 'connection_lost' | 'connection_restored' | ...,
  title: string,
  message: string,
  timestamp: ISO string,
  read: boolean,
  metadata?: {          // <-- Optional, only on health alerts
    project_id?: string,  // <-- Filter key for clearing
    project_name?: string,
    job_id?: string,
    agent_display_name?: string,
  }
}
```

**Changes needed:** Add two new actions before the return block (before line 72), then export them in the return block.

### File 2: `frontend/src/components/projects/ProjectTabs.vue`

**Where:** In `handleCloseoutComplete()` (line 570, modified by 0819a to stay on page).

**Current imports (lines 152-166):** Does NOT import `useNotificationStore`. Must add:
```javascript
import { useNotificationStore } from '@/stores/notifications'
```

**Where to add the store instantiation:** After the existing store instantiations around line 155-160:
```javascript
const notificationStore = useNotificationStore()
```

**Where to call it:** Inside `handleCloseoutComplete()`, after the modal closes and before/after data refresh:
```javascript
notificationStore.clearForProject(projectId.value)
```

### File 3: `frontend/src/views/ProjectsView.vue`

**Two places need notification clearing here:**

**A) Cancel action -- line 1319-1321:**
```javascript
case 'cancel':
  await projectStore.cancelProject(projectId)
  break
```
Change to:
```javascript
case 'cancel':
  await projectStore.cancelProject(projectId)
  notificationStore.clearForProject(projectId)
  break
```

**B) ManualCloseoutModal completion -- line 1341-1346:**
```javascript
async function handleCloseoutComplete() {
  showCloseoutModal.value = false
  closeoutProjectId.value = null
  closeoutProjectName.value = ''
  await projectStore.fetchProjects()
}
```
Change to:
```javascript
async function handleCloseoutComplete() {
  const projectIdToClear = closeoutProjectId.value  // capture before clearing
  showCloseoutModal.value = false
  closeoutProjectId.value = null
  closeoutProjectName.value = ''
  notificationStore.clearForProject(projectIdToClear)
  await projectStore.fetchProjects()
}
```

**Import needed in ProjectsView.vue:** Add to the existing imports (around line 730):
```javascript
import { useNotificationStore } from '@/stores/notifications'
```
And instantiate it near other store usages:
```javascript
const notificationStore = useNotificationStore()
```

### File 4: `frontend/src/stores/user.js`

**The `logout` function at lines 79-96:**
```javascript
async function logout() {
  try {
    await api.auth.logout()
  } catch (error) {
    console.error('[UserStore] Logout endpoint failed:', error)
  } finally {
    currentUser.value = null
    clearOrgFields()
    setTenantKey(null)
    localStorage.removeItem('remembered_username')
  }
}
```

**Change:** Add notification store clearing in the `finally` block:
```javascript
finally {
  currentUser.value = null
  clearOrgFields()
  setTenantKey(null)
  localStorage.removeItem('remembered_username')
  // Clear notifications on logout (tenant isolation defense-in-depth, Handover 0819b)
  const { useNotificationStore } = await import('@/stores/notifications')
  useNotificationStore().clearAll()
}
```

Note: Use dynamic import to avoid circular dependency risk (user store is loaded very early). Alternatively, import at the top of the file if no circular dependency exists -- check the existing imports first.

## Implementation Plan

### Phase 1: Add Actions to Notification Store

In `frontend/src/stores/notifications.js`, add before the return block (before line 72):

```javascript
function clearForProject(projectId) {
  if (!projectId) return
  notifications.value = notifications.value.filter(
    (n) => n.metadata?.project_id !== projectId
  )
}

function clearAll() {
  notifications.value = []
}
```

Update the return block (lines 72-86) to include both:
```javascript
return {
  notifications,
  unreadCount,
  agentHealthNotifications,
  sortedNotifications,
  badgeColor,
  addNotification,
  markAsRead,
  markAllAsRead,
  clearForProject,
  clearAll,
}
```

### Phase 2: Hook into ProjectTabs.vue (CloseoutModal Path)

1. Add import: `import { useNotificationStore } from '@/stores/notifications'`
2. Add instantiation: `const notificationStore = useNotificationStore()`
3. In `handleCloseoutComplete()`: add `notificationStore.clearForProject(projectId.value)`

### Phase 3: Hook into ProjectsView.vue (Cancel + ManualCloseout Paths)

1. Add import and instantiation (see File 3 above)
2. In cancel case (line 1319): add `notificationStore.clearForProject(projectId)` after the cancel call
3. In `handleCloseoutComplete` (line 1341): capture `closeoutProjectId.value` before clearing, then call `notificationStore.clearForProject()`

### Phase 4: Logout Reset in user.js

Add `clearAll()` call in the logout function's `finally` block (line 85-95).

## Testing Requirements

### Unit Tests (Vitest)

Write tests in `frontend/tests/stores/notifications.clearing.test.js`:

1. `test_clearForProject_removes_matching_notifications` - add 3 notifications (2 with project_id='AAA', 1 with project_id='BBB'), call `clearForProject('AAA')`, verify only BBB remains
2. `test_clearForProject_preserves_system_notifications` - add a `connection_lost` notification (no metadata.project_id), call `clearForProject('AAA')`, verify connection notification survives
3. `test_clearForProject_noop_on_null` - call `clearForProject(null)`, verify no crash, notifications unchanged
4. `test_clearForProject_noop_on_undefined` - call `clearForProject(undefined)`, verify same
5. `test_clearAll_empties_store` - add 5 notifications, call `clearAll()`, verify `notifications.value` is empty
6. `test_unreadCount_updates_after_clearForProject` - add 2 unread notifications for project A, clear, verify `unreadCount` drops to 0
7. `test_badgeColor_recalculates_after_clear` - add an `agent_health` warning notification, clear it, verify `badgeColor` changes

### Manual Testing

1. Trigger health alerts on a project (wait for agent staleness or simulate via WebSocket)
2. Verify bell shows unread notifications with project chip
3. Close out the project via CloseoutModal -> verify notifications for that project disappear from bell
4. Repeat via ManualCloseoutModal (from projects list "Complete" action) -> verify same
5. Repeat via Cancel (from projects list "Cancel" action) -> verify same
6. Connection lost/restored notifications must survive all clearing operations

## Success Criteria

- `clearForProject(id)` removes all notifications with matching `metadata.project_id`
- System-level notifications (no project_id in metadata) are never affected
- Clearing triggers on all 3 terminal paths: CloseoutModal, ManualCloseoutModal, Cancel
- `clearAll()` empties the store completely (for logout)
- `unreadCount` and `badgeColor` computeds update correctly after clearing

## Dependencies

- **0819a** modifies `handleCloseoutComplete` in ProjectTabs.vue. If 0819a is done first, the function will look different but the notification clearing call is additive. If 0819b is done first, 0819a just needs to preserve the `clearForProject` call.
- No blocking dependency in either direction.

## Rollback Plan

Revert changes to `notifications.js`, `ProjectTabs.vue`, `ProjectsView.vue`, `user.js`. No backend or database changes.
