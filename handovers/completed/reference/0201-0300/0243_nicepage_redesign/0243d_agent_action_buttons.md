# Handover 0243d: Agent Action Buttons (5 Actions Per Agent)

**Status**: 🔵 Ready for Implementation
**Priority**: P1 (High - Critical UX feature)
**Estimated Effort**: 8-10 hours
**Tool**: CCW (Cloud) for frontend work
**Subagent**: tdd-implementor (test-driven development)
**Dependencies**: 0243c (dynamic status must work first)
**Part**: 4 of 6 in Nicepage conversion series

---

## Mission

Implement 5 action buttons per agent in JobsTab table actions column: Play/Launch, Folder, Info, Cancel, Hand Over.

**Current State**: Only 3 actions shown (Play, Folder, Info)
**Missing**: Cancel and Hand Over buttons

---

## Visual Reference

**Target**: Each agent row should have 5 icon buttons in actions column:

1. **Play** (yellow) - Copy agent prompt, launch in CLI
2. **Folder** (yellow) - Open agent workspace (future placeholder)
3. **Info** (white) - View agent details
4. **Cancel** (orange/warning) - Cancel running job
5. **Hand Over** (orange/warning) - Trigger orchestrator succession

**Conditional Display**:
- Play: Show only when `status === 'waiting'`
- Folder: Always show (placeholder)
- Info: Always show
- Cancel: Show only when `status === 'working'`
- Hand Over: Show only when `agent_type === 'orchestrator' && status === 'working'`

---

## Current Implementation Gap

**File**: `frontend/src/components/projects/JobsTab.vue` (lines 68-90)

**Current actions column**:
```vue
<td class="actions-cell">
  <v-btn icon="mdi-play" size="small" @click="copyAgentPrompt(agent)" />
  <v-btn icon="mdi-folder" size="small" @click="openWorkspace(agent)" />
  <v-btn icon="mdi-information" size="small" @click="showAgentInfo(agent)" />
</td>
```

**Missing**:
- ❌ Cancel button (`mdi-cancel`)
- ❌ Hand Over button (`mdi-hand-wave`)
- ❌ Conditional display logic (Play only when waiting, Cancel only when working, etc.)

---

## Required Implementation

### 1. Cancel Button

**Template** (add to actions column):
```vue
<v-btn
  v-if="agent.status === 'working'"
  icon="mdi-cancel"
  size="small"
  color="warning"
  class="cancel-btn"
  @click="confirmCancelJob(agent)"
>
  <v-icon>mdi-cancel</v-icon>
  <v-tooltip activator="parent" location="top">Cancel job</v-tooltip>
</v-btn>
```

**Confirmation Dialog**:
```vue
<v-dialog v-model="showCancelDialog" max-width="500">
  <v-card>
    <v-card-title>Cancel Agent Job?</v-card-title>
    <v-card-text>
      The agent will stop work on its next check-in. This action cannot be undone.

      <div class="agent-info">
        <strong>Agent:</strong> {{ selectedAgent?.agent_type }}<br>
        <strong>ID:</strong> {{ selectedAgent?.id }}
      </div>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn text @click="showCancelDialog = false">No, keep running</v-btn>
      <v-btn color="error" @click="cancelJob">Yes, cancel</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**Script methods**:
```javascript
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

const showCancelDialog = ref(false)
const selectedAgent = ref(null)
const { showToast } = useToast()

const confirmCancelJob = (agent) => {
  selectedAgent.value = agent
  showCancelDialog.value = true
}

const cancelJob = async () => {
  try {
    await api.post(`/jobs/${selectedAgent.value.id}/cancel`, {
      reason: 'User requested cancellation'
    })

    showToast('Agent job cancelled successfully', 'success')
    showCancelDialog.value = false

    // Status will update via WebSocket event (agent:status_changed)
  } catch (error) {
    console.error('[JobsTab] Cancel job failed:', error)
    showToast('Failed to cancel agent job', 'error')
  }
}
```

**API Endpoint**: `POST /api/jobs/{job_id}/cancel`

**Backend** (already exists in `api/endpoints/jobs.py`):
```python
@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    request: CancelJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Set job status to 'cancelled'
    # Emit WebSocket event: agent:status_changed
    pass
```

### 2. Hand Over Button

**Template** (add to actions column):
```vue
<v-btn
  v-if="agent.agent_type === 'orchestrator' && agent.status === 'working'"
  icon="mdi-hand-wave"
  size="small"
  color="warning"
  class="handover-btn"
  @click="openHandoverDialog(agent)"
>
  <v-icon>mdi-hand-wave</v-icon>
  <v-tooltip activator="parent" location="top">Hand over to successor</v-tooltip>
</v-btn>
```

**Handover Dialog** (reuse existing component from AgentCard):
```vue
<LaunchSuccessorDialog
  v-model="showHandoverDialog"
  :agent="selectedAgent"
  @successor-created="handleSuccessorCreated"
/>
```

**Import**:
```javascript
import LaunchSuccessorDialog from '@/components/orchestration/LaunchSuccessorDialog.vue'
```

**Script methods**:
```javascript
const showHandoverDialog = ref(false)

const openHandoverDialog = (agent) => {
  selectedAgent.value = agent
  showHandoverDialog.value = true
}

const handleSuccessorCreated = (successorData) => {
  console.log('[JobsTab] Successor created:', successorData)
  showToast('Orchestrator handover initiated', 'success')
  showHandoverDialog.value = false
}
```

**LaunchSuccessorDialog component** (already exists at `frontend/src/components/orchestration/LaunchSuccessorDialog.vue`):
- Shows succession reason options (manual, context_limit, phase_transition)
- Calls API: `POST /api/orchestrator/succession`
- Emits `successor-created` event on success

### 3. Conditional Display Logic

**Updated actions column template**:
```vue
<td class="actions-cell">
  <!-- Play/Launch (only when waiting) -->
  <v-btn
    v-if="agent.status === 'waiting'"
    icon="mdi-play"
    size="small"
    color="yellow-darken-2"
    @click="copyAgentPrompt(agent)"
  >
    <v-icon>mdi-play</v-icon>
    <v-tooltip activator="parent" location="top">Launch agent</v-tooltip>
  </v-btn>

  <!-- Folder (always show - placeholder) -->
  <v-btn
    icon="mdi-folder"
    size="small"
    color="yellow-darken-2"
    @click="openWorkspace(agent)"
  >
    <v-icon>mdi-folder</v-icon>
    <v-tooltip activator="parent" location="top">Open workspace</v-tooltip>
  </v-btn>

  <!-- Info (always show) -->
  <v-btn
    icon="mdi-information"
    size="small"
    color="white"
    @click="showAgentInfo(agent)"
  >
    <v-icon>mdi-information</v-icon>
    <v-tooltip activator="parent" location="top">Agent details</v-tooltip>
  </v-btn>

  <!-- Cancel (only when working) -->
  <v-btn
    v-if="agent.status === 'working'"
    icon="mdi-cancel"
    size="small"
    color="warning"
    @click="confirmCancelJob(agent)"
  >
    <v-icon>mdi-cancel</v-icon>
    <v-tooltip activator="parent" location="top">Cancel job</v-tooltip>
  </v-btn>

  <!-- Hand Over (only for working orchestrators) -->
  <v-btn
    v-if="agent.agent_type === 'orchestrator' && agent.status === 'working'"
    icon="mdi-hand-wave"
    size="small"
    color="warning"
    @click="openHandoverDialog(agent)"
  >
    <v-icon>mdi-hand-wave</v-icon>
    <v-tooltip activator="parent" location="top">Hand over</v-tooltip>
  </v-btn>
</td>
```

**Styles**:
```scss
.actions-cell {
  display: flex;
  gap: 4px;
  align-items: center;

  .v-btn {
    min-width: 32px;

    &:hover {
      opacity: 0.8;
    }
  }
}
```

---

## TDD Workflow

### RED: Write Failing Tests

**File**: `tests/unit/JobsTab-actions.spec.js`

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import JobsTab from '@/components/projects/JobsTab.vue'

describe('JobsTab agent action buttons (Phase 4)', () => {
  let wrapper

  const mockAgents = [
    { id: 'agent-1', agent_type: 'orchestrator', status: 'working' },
    { id: 'agent-2', agent_type: 'implementor', status: 'waiting' },
    { id: 'agent-3', agent_type: 'tester', status: 'complete' }
  ]

  beforeEach(() => {
    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Test' },
        agents: mockAgents
      }
    })
  })

  // RED: Conditional display tests
  it('shows play button only for waiting agents', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')

    // Row 0 (working orchestrator): NO play button
    expect(rows[0].find('.actions-cell [icon="mdi-play"]').exists()).toBe(false)

    // Row 1 (waiting implementor): YES play button
    expect(rows[1].find('.actions-cell [icon="mdi-play"]').exists()).toBe(true)

    // Row 2 (complete tester): NO play button
    expect(rows[2].find('.actions-cell [icon="mdi-play"]').exists()).toBe(false)
  })

  it('shows cancel button only for working agents', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')

    // Row 0 (working orchestrator): YES cancel button
    expect(rows[0].find('.cancel-btn').exists()).toBe(true)

    // Row 1 (waiting implementor): NO cancel button
    expect(rows[1].find('.cancel-btn').exists()).toBe(false)

    // Row 2 (complete tester): NO cancel button
    expect(rows[2].find('.cancel-btn').exists()).toBe(false)
  })

  it('shows hand over button only for working orchestrators', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')

    // Row 0 (working orchestrator): YES hand over button
    expect(rows[0].find('.handover-btn').exists()).toBe(true)

    // Row 1 (waiting implementor): NO hand over button (not orchestrator)
    expect(rows[1].find('.handover-btn').exists()).toBe(false)

    // Row 2 (complete tester): NO hand over button (not working)
    expect(rows[2].find('.handover-btn').exists()).toBe(false)
  })

  it('always shows folder and info buttons', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')

    rows.forEach(row => {
      expect(row.find('[icon="mdi-folder"]').exists()).toBe(true)
      expect(row.find('[icon="mdi-information"]').exists()).toBe(true)
    })
  })

  // RED: Cancel job workflow tests
  it('opens confirmation dialog when cancel button clicked', async () => {
    const cancelBtn = wrapper.find('.cancel-btn')
    await cancelBtn.trigger('click')

    expect(wrapper.vm.showCancelDialog).toBe(true)
    expect(wrapper.vm.selectedAgent.id).toBe('agent-1')
  })

  it('calls cancel API when confirmed', async () => {
    const mockApi = vi.spyOn(api, 'post').mockResolvedValue({ data: { success: true } })

    // Open dialog
    await wrapper.find('.cancel-btn').trigger('click')

    // Confirm cancellation
    wrapper.vm.showCancelDialog = true
    await wrapper.vm.cancelJob()

    expect(mockApi).toHaveBeenCalledWith('/jobs/agent-1/cancel', {
      reason: 'User requested cancellation'
    })
  })

  it('shows success toast after cancellation', async () => {
    const mockToast = vi.spyOn(wrapper.vm, 'showToast')
    vi.spyOn(api, 'post').mockResolvedValue({ data: { success: true } })

    await wrapper.find('.cancel-btn').trigger('click')
    await wrapper.vm.cancelJob()

    expect(mockToast).toHaveBeenCalledWith('Agent job cancelled successfully', 'success')
  })

  // RED: Hand over workflow tests
  it('opens handover dialog when hand over button clicked', async () => {
    const handoverBtn = wrapper.find('.handover-btn')
    await handoverBtn.trigger('click')

    expect(wrapper.vm.showHandoverDialog).toBe(true)
    expect(wrapper.vm.selectedAgent.id).toBe('agent-1')
  })

  it('emits successor-created event after handover', async () => {
    const successorData = { id: 'successor-uuid', spawned_by: 'agent-1' }

    await wrapper.find('.handover-btn').trigger('click')

    // Simulate LaunchSuccessorDialog emission
    wrapper.vm.handleSuccessorCreated(successorData)

    expect(wrapper.vm.showHandoverDialog).toBe(false)
  })
})
```

### GREEN: Implement Minimum Code

**Tasks**:
1. Add Cancel button template + confirmation dialog
2. Add Hand Over button template + LaunchSuccessorDialog
3. Update conditional display logic (v-if directives)
4. Add cancel job method (API call + toast)
5. Add hand over methods (open dialog, handle succession)
6. Run tests: `npm run test:unit -- JobsTab-actions.spec.js`

### REFACTOR: Polish Code

**Tasks**:
1. Extract action button logic to composable (`useAgentActions.js`)
2. Add loading states for Cancel/Hand Over buttons
3. Add error handling with user-friendly messages
4. Clean up unused code
5. Run coverage: `npm run test:unit -- --coverage`

---

## Deliverables

**Files to Modify**:
- ✅ `frontend/src/components/projects/JobsTab.vue` (template + script)

**Files to Import** (already exist):
- ✅ `frontend/src/components/orchestration/LaunchSuccessorDialog.vue`

**Success Criteria**:
- [ ] 5 action buttons per agent row
- [ ] Play button: Only when `status === 'waiting'`
- [ ] Folder button: Always shown
- [ ] Info button: Always shown
- [ ] Cancel button: Only when `status === 'working'`
- [ ] Hand Over button: Only when `agent_type === 'orchestrator' && status === 'working'`
- [ ] Cancel confirmation dialog works
- [ ] Cancel API call succeeds
- [ ] Hand Over dialog opens
- [ ] Successor creation succeeds
- [ ] Test coverage: >80%

---

## Integration Testing

**File**: `tests/integration/jobstab-actions.spec.js`

```javascript
describe('JobsTab action buttons integration', () => {
  it('completes cancel job workflow', async () => {
    const { wrapper, mockApi } = setupIntegrationTest()

    // Click cancel button
    await wrapper.find('.cancel-btn').trigger('click')

    // Verify dialog opened
    expect(wrapper.find('.v-dialog').isVisible()).toBe(true)

    // Confirm cancellation
    await wrapper.find('.v-dialog .v-btn[color="error"]').trigger('click')

    // Verify API called
    expect(mockApi).toHaveBeenCalledWith('/jobs/agent-uuid/cancel', {
      reason: 'User requested cancellation'
    })

    // Simulate WebSocket event (status update)
    emit('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'cancelled'
    })

    await wrapper.vm.$nextTick()

    // Verify status updated in UI
    expect(wrapper.find('.status-cell').text()).toBe('Cancelled')
  })

  it('completes hand over workflow', async () => {
    const { wrapper, mockApi } = setupIntegrationTest()

    // Click hand over button
    await wrapper.find('.handover-btn').trigger('click')

    // Verify LaunchSuccessorDialog opened
    expect(wrapper.findComponent(LaunchSuccessorDialog).isVisible()).toBe(true)

    // Select reason and confirm
    const dialog = wrapper.findComponent(LaunchSuccessorDialog)
    await dialog.vm.$emit('successor-created', {
      id: 'successor-uuid',
      spawned_by: 'orchestrator-uuid'
    })

    // Verify toast shown
    expect(wrapper.vm.showToast).toHaveBeenCalledWith('Orchestrator handover initiated', 'success')
  })
})
```

---

## Next Steps

**Parallel with 0243e**:
- This handover (0243d): Agent action buttons
- 0243e: Message center + tab activation (independent work)

**Blocks**:
- 0243f: Integration testing (needs all components complete)

---

## Estimated Timeline

**Total**: 8-10 hours

**Breakdown**:
- Cancel button + dialog: 3 hours
- Hand Over button + integration: 3 hours
- Conditional display logic: 2 hours
- Test writing + validation: 2-3 hours

---

## Agent Instructions

**You are a tdd-implementor agent**:

1. **RED**: Write failing tests FIRST
   - Test conditional display for all 5 buttons
   - Test cancel workflow (dialog → API → toast)
   - Test hand over workflow (dialog → succession)

2. **GREEN**: Implement minimum code
   - Add Cancel button + confirmation dialog
   - Add Hand Over button + LaunchSuccessorDialog
   - Update conditional display (v-if directives)
   - Wire up API calls and event handlers

3. **REFACTOR**: Polish code
   - Extract to composable if needed
   - Add loading states
   - Error handling

4. **Integration test**: E2E workflows
   - Cancel job workflow (click → confirm → API → WebSocket update)
   - Hand over workflow (click → dialog → succession)

5. **Report back**: Test coverage %, integration test results, blockers

---

## API Reference

### Cancel Job Endpoint

**Endpoint**: `POST /api/jobs/{job_id}/cancel`

**Request Body**:
```json
{
  "reason": "User requested cancellation"
}
```

**Response**:
```json
{
  "success": true,
  "job_id": "agent-uuid",
  "status": "cancelled",
  "cancelled_at": "2025-11-23T10:30:00Z"
}
```

**WebSocket Event** (emitted after cancellation):
```json
{
  "event": "agent:status_changed",
  "data": {
    "job_id": "agent-uuid",
    "tenant_key": "test-tenant",
    "status": "cancelled",
    "timestamp": "2025-11-23T10:30:00Z"
  }
}
```

### Orchestrator Succession Endpoint

**Endpoint**: `POST /api/orchestrator/succession`

**Request Body**:
```json
{
  "current_job_id": "orchestrator-uuid",
  "reason": "manual",
  "tenant_key": "test-tenant"
}
```

**Response**:
```json
{
  "success": true,
  "successor_id": "successor-uuid",
  "spawned_by": "orchestrator-uuid",
  "context_summary": "Handover summary (condensed mission)",
  "created_at": "2025-11-23T10:35:00Z"
}
```

---

## Component Architecture

### JobsTab Component Structure

```
JobsTab.vue
├── Template
│   ├── v-card (container)
│   ├── v-table (agents table)
│   │   ├── thead (headers: Agent, Type, Status, Health, Actions)
│   │   └── tbody (agent rows)
│   │       ├── td.agent-name-cell
│   │       ├── td.type-cell
│   │       ├── td.status-cell
│   │       ├── td.health-cell
│   │       └── td.actions-cell (5 buttons)
│   │           ├── v-btn (Play) [v-if="status === 'waiting'"]
│   │           ├── v-btn (Folder) [always]
│   │           ├── v-btn (Info) [always]
│   │           ├── v-btn (Cancel) [v-if="status === 'working'"]
│   │           └── v-btn (Hand Over) [v-if="orchestrator && working"]
│   ├── v-dialog (cancel confirmation)
│   └── LaunchSuccessorDialog (hand over)
└── Script
    ├── Props: project, agents
    ├── State: showCancelDialog, showHandoverDialog, selectedAgent
    ├── Methods:
    │   ├── copyAgentPrompt(agent)
    │   ├── openWorkspace(agent)
    │   ├── showAgentInfo(agent)
    │   ├── confirmCancelJob(agent)
    │   ├── cancelJob()
    │   ├── openHandoverDialog(agent)
    │   └── handleSuccessorCreated(data)
    └── Imports:
        ├── LaunchSuccessorDialog
        ├── useToast
        └── api
```

---

## Error Handling

### Cancel Job Error Cases

**Case 1: Job not found**
```javascript
catch (error) {
  if (error.response?.status === 404) {
    showToast('Agent job not found', 'error')
  }
}
```

**Case 2: Job already cancelled**
```javascript
catch (error) {
  if (error.response?.status === 409) {
    showToast('Job already cancelled or completed', 'warning')
  }
}
```

**Case 3: Network error**
```javascript
catch (error) {
  if (!error.response) {
    showToast('Network error - please check connection', 'error')
  }
}
```

### Hand Over Error Cases

**Case 1: Not an orchestrator**
```javascript
// Prevented by v-if check in template
v-if="agent.agent_type === 'orchestrator' && agent.status === 'working'"
```

**Case 2: Succession failed**
```javascript
// Handled in LaunchSuccessorDialog component
@successor-created="handleSuccessorCreated"
@error="handleSuccessionError"
```

---

## Testing Checklist

**Unit Tests** (`tests/unit/JobsTab-actions.spec.js`):
- [ ] Play button: visible only when `status === 'waiting'`
- [ ] Cancel button: visible only when `status === 'working'`
- [ ] Hand Over button: visible only when `orchestrator + working`
- [ ] Folder/Info buttons: always visible
- [ ] Cancel dialog opens on button click
- [ ] Cancel API called with correct params
- [ ] Success toast shown after cancellation
- [ ] Hand Over dialog opens on button click
- [ ] Successor created event handled correctly

**Integration Tests** (`tests/integration/jobstab-actions.spec.js`):
- [ ] Complete cancel workflow (button → dialog → API → WebSocket → UI update)
- [ ] Complete hand over workflow (button → dialog → succession → toast)
- [ ] Error handling for failed cancellation
- [ ] Error handling for failed succession

**Manual Testing**:
- [ ] Visual: 5 buttons per agent row
- [ ] Visual: Correct icons and colors (yellow, white, orange)
- [ ] Interaction: Cancel confirmation dialog shows agent details
- [ ] Interaction: Hand Over dialog shows succession reasons
- [ ] Real-time: Status updates via WebSocket after cancellation
- [ ] Real-time: New successor appears in table after handover

---

## Acceptance Criteria

**Functional Requirements**:
1. ✅ 5 action buttons per agent row in JobsTab
2. ✅ Conditional display logic (Play when waiting, Cancel when working, etc.)
3. ✅ Cancel button opens confirmation dialog with agent details
4. ✅ Cancel API call succeeds and emits WebSocket event
5. ✅ Hand Over button opens LaunchSuccessorDialog
6. ✅ Successor creation succeeds and shows toast
7. ✅ UI updates in real-time via WebSocket events

**Non-Functional Requirements**:
1. ✅ Test coverage >80%
2. ✅ No console errors or warnings
3. ✅ Accessible keyboard navigation
4. ✅ Responsive design (buttons don't overflow on small screens)
5. ✅ Loading states during API calls
6. ✅ User-friendly error messages

---

## Definition of Done

- [ ] All 5 action buttons implemented and visible
- [ ] Conditional display logic working correctly
- [ ] Cancel workflow complete (dialog → API → WebSocket → UI)
- [ ] Hand Over workflow complete (dialog → succession → toast)
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] No regressions in existing functionality
- [ ] Code reviewed and approved
- [ ] Documentation updated (if needed)

---

**END OF HANDOVER 0243d**
