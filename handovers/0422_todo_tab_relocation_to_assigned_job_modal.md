# Handover: TODO Tab Relocation to Assigned Job Modal

**Date:** 2026-01-19
**From Agent:** Observer Session
**To Agent:** ux-designer or tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 5-8 hours
**Status:** Ready for Implementation

---

## Task Summary

Move the TODO/Plan visualization from MessageAuditModal to the agent "Assigned Job" modal as a new tab. The reasoning is that TODO items are job-related (task tracking), not messaging-related.

---

## Context and Background

### Current State
- TODO items are displayed in the "Plan / TODOs" tab inside `MessageAuditModal.vue`
- The "Assigned Job" modal in `JobsTab.vue` (briefcase icon) shows only the mission text
- Clicking the "Steps" column opens MessageAuditModal with Plan tab active
- Data flows via WebSocket `job:progress_update` events containing `todo_items` array

### Why This Change
- TODOs represent agent task execution progress, not inter-agent communication
- Semantic mismatch: Message Audit = communication audit, TODOs = job execution tracking
- Users expect job-related information (mission + tasks) grouped together

---

## Technical Details

### Files to Modify

| File | Change Description |
|------|-------------------|
| `frontend/src/components/projects/JobsTab.vue` | Convert inline "Assigned Job" modal (lines 274-312) to use new tabbed component |
| `frontend/src/components/projects/MessageAuditModal.vue` | Remove "Plan / TODOs" tab (lines 85-93, 100-132, 263-274, 345-368, 431-474) |

### New File to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/projects/AgentJobModal.vue` | New modal with tabs: "Mission" and "Plan" |

### Key Code Sections

**MessageAuditModal.vue - TODO Implementation to Extract:**
```vue
<!-- Lines 100-132: Template for TODO items -->
<div v-if="activeTab === 'plan'" class="todo-items-column">
  <div v-for="(item, index) in todoItems" :key="`todo-${index}`" class="todo-item-row">
    <v-icon :icon="getStatusIcon(item.status)" :color="getStatusColor(item.status)" />
    <span class="todo-item-content">{{ item.content }}</span>
  </div>
</div>

<!-- Lines 263-274: Computed property -->
const todoItems = computed(() =>
  props.agent?.todo_items && Array.isArray(props.agent.todo_items)
    ? props.agent.todo_items
    : []
)

<!-- Lines 345-368: Helper functions -->
function getStatusIcon(status) { /* pending/in_progress/completed icons */ }
function getStatusColor(status) { /* grey/warning/success colors */ }
```

**JobsTab.vue - Current Assigned Job Modal (lines 274-312):**
```vue
<v-dialog v-model="showAssignedJobModal" max-width="700">
  <v-card>
    <v-card-title>{{ selectedAgent?.agent_name || 'Agent' }} - Assigned Job</v-card-title>
    <v-card-text>
      <div><strong>Agent ID:</strong> {{ selectedAgent?.agent_id }}</div>
      <div><strong>Job ID:</strong> {{ selectedAgent?.job_id }}</div>
      <div class="mt-4"><strong>Mission:</strong></div>
      <pre>{{ selectedAgent?.mission || 'No mission assigned' }}</pre>
    </v-card-text>
  </v-card>
</v-dialog>
```

### Data Flow (No Backend Changes Needed)

1. **Source**: `AgentJob.todo_items` array (via WebSocket `job:progress_update`)
2. **Store**: `agentJobsStore.handleProgressUpdate()` stores `todo_items` on job object
3. **Access**: `selectedAgent.todo_items` already available in JobsTab.vue
4. **Real-time**: WebSocket updates reflect immediately when modal is open

---

## Implementation Plan

### Phase 1: Create AgentJobModal Component (2-3 hours)
1. Create `frontend/src/components/projects/AgentJobModal.vue`
2. Implement two tabs using Vuetify `v-tabs`:
   - **Tab 1: Mission** - Current mission display (from JobsTab lines 296-301)
   - **Tab 2: Plan** - TODO items list (from MessageAuditModal lines 100-132)
3. Props: `show`, `agent`, `initialTab`
4. Emits: `close`
5. Extract helper functions: `getStatusIcon()`, `getStatusColor()`

### Phase 2: Update JobsTab.vue (1 hour)
1. Import and register `AgentJobModal` component
2. Replace inline `v-dialog` (lines 274-312) with `<AgentJobModal>`
3. Update `handleStepsClick()` to open modal with Plan tab active
4. Update briefcase click to open modal with Mission tab active

### Phase 3: Clean Up MessageAuditModal.vue (30 min)
1. Remove "Plan / TODOs" tab button (lines 85-93)
2. Remove Plan tab content (lines 100-132)
3. Remove `todoItems` computed property (lines 263-274)
4. Remove `planCount` computed (line 273)
5. Remove helper functions if not used elsewhere (lines 345-368)
6. Remove CSS for todo items (lines 431-474)

### Phase 4: Testing (1-2 hours)
1. Unit tests for AgentJobModal component
2. Verify Steps column click opens Plan tab
3. Verify briefcase click opens Mission tab
4. Verify real-time WebSocket updates while modal open
5. Verify no regressions in MessageAuditModal

**Recommended Sub-Agent:** `ux-designer` or `tdd-implementor`

---

## Testing Requirements

### Unit Tests
- [ ] AgentJobModal renders with Mission tab by default
- [ ] AgentJobModal shows Plan tab when initialTab='plan'
- [ ] TODO items display with correct icons/colors per status
- [ ] Empty state shown when no todo_items

### Integration Tests
- [ ] Steps column click opens AgentJobModal with Plan tab
- [ ] Briefcase click opens AgentJobModal with Mission tab
- [ ] WebSocket progress updates reflect in open modal

### Manual Testing
1. Open project with active agents
2. Click briefcase icon on agent row → Should show Mission tab
3. Click Steps column → Should show Plan tab with TODO items
4. Trigger progress update → Should see TODO items update in real-time
5. Verify MessageAuditModal no longer has Plan tab

---

## Dependencies and Blockers

**Dependencies:** None - all data flow already exists

**Potential Blockers:**
- None identified - straightforward UI refactor

---

## Success Criteria

- [ ] AgentJobModal component created with Mission and Plan tabs
- [ ] TODO items moved from MessageAuditModal to AgentJobModal
- [ ] Steps column click opens Plan tab
- [ ] Briefcase click opens Mission tab
- [ ] MessageAuditModal simplified (no Plan tab)
- [ ] All unit and integration tests pass
- [ ] No regressions in existing functionality

---

## Rollback Plan

If issues arise:
1. Revert AgentJobModal.vue creation
2. Restore MessageAuditModal.vue Plan tab code
3. Restore JobsTab.vue inline modal

Git-based rollback: `git checkout HEAD~1 -- frontend/src/components/projects/`

---

## Additional Resources

- **Related Handover:** 0402 (Agent TODO Items Table) - original TODO implementation
- **WebSocket Events:** `job:progress_update` sends `todo_items` array
- **Store Location:** `frontend/src/stores/agentJobsStore.js` lines 154-196
