# Handover 0243c: JobsTab Dynamic Status Fix (CRITICAL 0242b)

**Status**: 🔴 CRITICAL - Blocking Real-Time Updates
**Priority**: P0 (Critical - User cannot see job progress)
**Estimated Effort**: 6-8 hours
**Tool**: CCW (Cloud) for frontend work
**Subagent**: tdd-implementor (test-driven development)
**Dependencies**: 0243a (design-tokens.scss)
**Part**: 3 of 6 in Nicepage conversion series

---

## Mission

Fix hardcoded "Waiting." status in JobsTab table to display dynamic status from backend `agent.status` field. Enable real-time status updates via WebSocket events.

**CRITICAL**: This is the 0242b fix - users currently cannot see when agents start working, complete, or fail.

---

## Problem Statement

**Current Implementation** (`JobsTab.vue` line 46):
```vue
<td class="status-cell">Waiting.</td>
```

**Issue**: Status is HARDCODED as "Waiting." - does NOT update when backend changes agent status.

**Impact**:
- ❌ Users cannot see when agents start working
- ❌ Users cannot see when agents complete
- ❌ Users cannot see when agents fail
- ❌ Real-time progress tracking broken

**Root Cause**: Line 46 has literal string "Waiting." instead of dynamic binding to `agent.status`.

---

## Required Implementation

### Backend Data Model

**MCPAgentJob entity** (`src/giljo_mcp/models.py`):
```python
class MCPAgentJob(Base):
    __tablename__ = "mcp_agent_jobs"

    status = Column(String, default='waiting')  # Values: waiting, working, complete, failed, cancelled
```

**WebSocket Event** (backend emits when status changes):
```python
# src/giljo_mcp/services/agent_job_manager.py
await websocket_manager.emit_to_tenant(
    event="agent:status_changed",
    data={
        "job_id": job.id,
        "tenant_key": job.tenant_key,
        "status": new_status,  # waiting, working, complete, failed, cancelled
        "timestamp": datetime.utcnow().isoformat()
    },
    tenant_key=job.tenant_key
)
```

### Status Configuration

**Create**: `frontend/src/utils/statusConfig.js`

```javascript
/**
 * Status configuration for agent job status display
 * Provides consistent status labels, colors, and styles across JobsTab and other components
 */

export const statusConfig = {
  waiting: {
    label: 'Waiting.',
    color: '#ffd700',      // Yellow
    italic: true,
    chipColor: 'warning'
  },
  working: {
    label: 'Working...',
    color: '#ffd700',      // Yellow
    italic: true,
    chipColor: 'warning'
  },
  complete: {
    label: 'Complete',
    color: '#67bd6d',      // Green
    italic: false,
    chipColor: 'success'
  },
  failed: {
    label: 'Failed',
    color: '#e53935',      // Red
    italic: false,
    chipColor: 'error'
  },
  cancelled: {
    label: 'Cancelled',
    color: '#ff9800',      // Orange
    italic: false,
    chipColor: 'warning'
  }
}

/**
 * Get human-readable label for status
 * @param {string} status - Agent status value
 * @returns {string} Display label
 */
export const getStatusLabel = (status) => {
  return statusConfig[status]?.label || 'Unknown'
}

/**
 * Get color for status display
 * @param {string} status - Agent status value
 * @returns {string} Hex color code
 */
export const getStatusColor = (status) => {
  return statusConfig[status]?.color || '#666'
}

/**
 * Check if status should be displayed in italic
 * @param {string} status - Agent status value
 * @returns {boolean} True if italic
 */
export const isStatusItalic = (status) => {
  return statusConfig[status]?.italic || false
}

/**
 * Get Vuetify chip color for status
 * @param {string} status - Agent status value
 * @returns {string} Vuetify color name
 */
export const getStatusChipColor = (status) => {
  return statusConfig[status]?.chipColor || 'default'
}
```

### JobsTab Template Update

**Replace line 46** in `frontend/src/components/projects/JobsTab.vue`:

```vue
<!-- BEFORE (WRONG - hardcoded) -->
<td class="status-cell">Waiting.</td>

<!-- AFTER (CORRECT - dynamic) -->
<td
  class="status-cell"
  :style="{
    color: getStatusColor(agent.status),
    fontStyle: isStatusItalic(agent.status) ? 'italic' : 'normal'
  }"
>
  {{ getStatusLabel(agent.status) }}
</td>
```

**Alternative with v-chip** (optional enhancement for better visual consistency):
```vue
<td class="status-cell">
  <v-chip
    size="x-small"
    :color="getStatusChipColor(agent.status)"
    variant="flat"
  >
    {{ getStatusLabel(agent.status) }}
  </v-chip>
</td>
```

### JobsTab Script Update

**Add imports** (top of `<script setup>` section):
```javascript
import { statusConfig, getStatusLabel, getStatusColor, isStatusItalic } from '@/utils/statusConfig'
import { useWebSocket } from '@/composables/useWebSocket'
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const { on, off } = useWebSocket()
```

**Add WebSocket event handler**:
```javascript
// Get current tenant key for multi-tenant isolation
const currentTenantKey = computed(() => store.state.user?.tenant_key)

/**
 * Handle agent status updates from WebSocket
 * CRITICAL: Multi-tenant isolation - reject events from other tenants
 */
const handleStatusUpdate = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[JobsTab] Status update rejected: tenant mismatch', {
      expected: currentTenantKey.value,
      received: data.tenant_key
    })
    return
  }

  // Find agent and update status
  const agent = props.agents.find(a => a.id === data.job_id)
  if (agent) {
    agent.status = data.status
    console.log(`[JobsTab] Agent ${data.job_id} status updated: ${data.status}`)
  } else {
    console.warn(`[JobsTab] Agent not found for status update: ${data.job_id}`)
  }
}

onMounted(() => {
  on('agent:status_changed', handleStatusUpdate)
  console.log('[JobsTab] WebSocket listener registered: agent:status_changed')
})

onUnmounted(() => {
  off('agent:status_changed', handleStatusUpdate)
  console.log('[JobsTab] WebSocket listener removed')
})
```

---

## TDD Workflow

### RED: Write Failing Tests

**File**: `tests/unit/JobsTab-status.spec.js`

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useWebSocket } from '@/composables/useWebSocket'

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn()
  }))
}))

describe('JobsTab dynamic status (Phase 3 - CRITICAL)', () => {
  let wrapper
  let mockOn, mockOff
  let store

  const mockAgents = [
    { id: 'agent-1', agent_type: 'orchestrator', agent_name: 'Orchestrator', status: 'working' },
    { id: 'agent-2', agent_type: 'implementor', agent_name: 'Implementor', status: 'waiting' },
    { id: 'agent-3', agent_type: 'tester', agent_name: 'Tester', status: 'complete' },
    { id: 'agent-4', agent_type: 'analyzer', agent_name: 'Analyzer', status: 'failed' },
    { id: 'agent-5', agent_type: 'reviewer', agent_name: 'Reviewer', status: 'cancelled' }
  ]

  beforeEach(() => {
    mockOn = vi.fn()
    mockOff = vi.fn()

    vi.mocked(useWebSocket).mockReturnValue({
      on: mockOn,
      off: mockOff,
      emit: vi.fn()
    })

    // Create Vuex store with user state
    store = createStore({
      state: {
        user: {
          tenant_key: 'test-tenant'
        }
      }
    })

    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Test Project' },
        agents: mockAgents
      },
      global: {
        plugins: [store]
      }
    })
  })

  // RED: These tests will FAIL with hardcoded "Waiting."
  it('displays "Working..." for working agents (yellow italic)', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[0].find('.status-cell')

    expect(statusCell.text()).toBe('Working...')
    expect(statusCell.element.style.color).toBe('rgb(255, 215, 0)')  // #ffd700
    expect(statusCell.element.style.fontStyle).toBe('italic')
  })

  it('displays "Waiting." for waiting agents (yellow italic)', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[1].find('.status-cell')

    expect(statusCell.text()).toBe('Waiting.')
    expect(statusCell.element.style.color).toBe('rgb(255, 215, 0)')
    expect(statusCell.element.style.fontStyle).toBe('italic')
  })

  it('displays "Complete" for completed agents (green, NOT italic)', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[2].find('.status-cell')

    expect(statusCell.text()).toBe('Complete')
    expect(statusCell.element.style.color).toBe('rgb(103, 189, 109)')  // #67bd6d
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('displays "Failed" for failed agents (red, NOT italic)', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[3].find('.status-cell')

    expect(statusCell.text()).toBe('Failed')
    expect(statusCell.element.style.color).toBe('rgb(229, 57, 53)')  // #e53935
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('displays "Cancelled" for cancelled agents (orange, NOT italic)', () => {
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[4].find('.status-cell')

    expect(statusCell.text()).toBe('Cancelled')
    expect(statusCell.element.style.color).toBe('rgb(255, 152, 0)')  // #ff9800
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('displays "Unknown" for invalid status values (graceful degradation)', () => {
    const invalidAgent = {
      id: 'agent-6',
      agent_type: 'invalid',
      agent_name: 'Invalid',
      status: 'invalid-status'
    }

    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Test' },
        agents: [invalidAgent]
      },
      global: {
        plugins: [store]
      }
    })

    const statusCell = wrapper.find('.status-cell')
    expect(statusCell.text()).toBe('Unknown')
    expect(statusCell.element.style.color).toBe('rgb(102, 102, 102)')  // #666
  })

  it('registers WebSocket listener on mount', () => {
    expect(mockOn).toHaveBeenCalledWith('agent:status_changed', expect.any(Function))
  })

  it('removes WebSocket listener on unmount', () => {
    wrapper.unmount()
    expect(mockOff).toHaveBeenCalledWith('agent:status_changed', expect.any(Function))
  })

  it('updates status when WebSocket event received', async () => {
    // Get the handler function passed to 'on'
    const handler = mockOn.mock.calls.find(call => call[0] === 'agent:status_changed')[1]

    // Simulate WebSocket event - agent-1 changes from "working" to "complete"
    handler({
      job_id: 'agent-1',
      tenant_key: 'test-tenant',
      status: 'complete'
    })

    await wrapper.vm.$nextTick()

    // Verify UI updated
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[0].find('.status-cell')
    expect(statusCell.text()).toBe('Complete')
    expect(statusCell.element.style.color).toBe('rgb(103, 189, 109)')
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('rejects status updates from different tenant (multi-tenant isolation)', async () => {
    const handler = mockOn.mock.calls.find(call => call[0] === 'agent:status_changed')[1]

    // Simulate WebSocket event from DIFFERENT tenant
    const consoleWarnSpy = vi.spyOn(console, 'warn')
    handler({
      job_id: 'agent-1',
      tenant_key: 'other-tenant',  // Different tenant!
      status: 'complete'
    })

    await wrapper.vm.$nextTick()

    // Verify warning logged
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('tenant mismatch'),
      expect.objectContaining({
        expected: 'test-tenant',
        received: 'other-tenant'
      })
    )

    // Verify UI NOT updated (status still "working")
    const rows = wrapper.findAll('.agents-table tbody tr')
    const statusCell = rows[0].find('.status-cell')
    expect(statusCell.text()).toBe('Working...')  // NOT "Complete"
  })

  it('handles status update for non-existent agent gracefully', async () => {
    const handler = mockOn.mock.calls.find(call => call[0] === 'agent:status_changed')[1]

    const consoleWarnSpy = vi.spyOn(console, 'warn')
    handler({
      job_id: 'non-existent-agent',
      tenant_key: 'test-tenant',
      status: 'complete'
    })

    await wrapper.vm.$nextTick()

    // Verify warning logged
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Agent not found for status update')
    )

    // Verify no errors thrown
    expect(wrapper.html()).toBeTruthy()
  })

  it('updates multiple agents sequentially via WebSocket', async () => {
    const handler = mockOn.mock.calls.find(call => call[0] === 'agent:status_changed')[1]

    // Update agent-2: waiting → working
    handler({
      job_id: 'agent-2',
      tenant_key: 'test-tenant',
      status: 'working'
    })
    await wrapper.vm.$nextTick()

    let rows = wrapper.findAll('.agents-table tbody tr')
    expect(rows[1].find('.status-cell').text()).toBe('Working...')

    // Update agent-2: working → complete
    handler({
      job_id: 'agent-2',
      tenant_key: 'test-tenant',
      status: 'complete'
    })
    await wrapper.vm.$nextTick()

    rows = wrapper.findAll('.agents-table tbody tr')
    expect(rows[1].find('.status-cell').text()).toBe('Complete')

    // Update agent-4: failed → working (retry scenario)
    handler({
      job_id: 'agent-4',
      tenant_key: 'test-tenant',
      status: 'working'
    })
    await wrapper.vm.$nextTick()

    rows = wrapper.findAll('.agents-table tbody tr')
    expect(rows[3].find('.status-cell').text()).toBe('Working...')
  })
})
```

### GREEN: Implement Minimum Code

**Tasks**:
1. ✅ Create `frontend/src/utils/statusConfig.js` with status mapping
2. ✅ Update `JobsTab.vue` template (line 46) with dynamic status binding
3. ✅ Update `JobsTab.vue` script (add imports and WebSocket handler)
4. ✅ Run tests: `npm run test:unit -- JobsTab-status.spec.js`
5. ✅ Verify all tests pass (should show 11/11 passing)

### REFACTOR: Polish Code

**Tasks**:
1. Extract WebSocket handler to composable if reused elsewhere (check LaunchTab, AgentTableView)
2. Add JSDoc comments to status utility functions
3. Clean up console.log statements (keep console.warn for security events)
4. Verify no unused imports
5. Run linter: `npm run lint`
6. Run coverage: `npm run test:unit -- --coverage`

**Code Quality Checks**:
- [ ] All functions have JSDoc comments
- [ ] Multi-tenant isolation verified in tests
- [ ] Error handling for invalid status values
- [ ] No memory leaks (WebSocket listeners cleaned up)
- [ ] Test coverage >80%

---

## Integration Testing

**File**: `tests/integration/jobstab-status-updates.spec.js`

```javascript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useWebSocket } from '@/composables/useWebSocket'

describe('JobsTab status updates integration', () => {
  let wrapper
  let store
  let emitFn

  beforeEach(() => {
    // Create mock WebSocket with working emit function
    const mockWebSocket = {
      on: vi.fn((event, handler) => {
        // Store handler for later invocation
        mockWebSocket._handlers = mockWebSocket._handlers || {}
        mockWebSocket._handlers[event] = handler
      }),
      off: vi.fn(),
      emit: vi.fn()
    }

    // Create emit function that triggers handlers
    emitFn = (event, data) => {
      if (mockWebSocket._handlers[event]) {
        mockWebSocket._handlers[event](data)
      }
    }

    vi.mocked(useWebSocket).mockReturnValue(mockWebSocket)

    store = createStore({
      state: {
        user: {
          tenant_key: 'test-tenant'
        }
      }
    })

    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Integration Test' },
        agents: [
          { id: 'agent-uuid', agent_type: 'orchestrator', agent_name: 'Orchestrator', status: 'waiting' }
        ]
      },
      global: {
        plugins: [store]
      }
    })
  })

  it('updates status in real-time when backend changes it', async () => {
    // Initial state: agent is "waiting"
    const statusCell = wrapper.find('.status-cell')
    expect(statusCell.text()).toBe('Waiting.')
    expect(statusCell.element.style.color).toBe('rgb(255, 215, 0)')
    expect(statusCell.element.style.fontStyle).toBe('italic')

    // Simulate backend status change via WebSocket: waiting → working
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'working'
    })

    await wrapper.vm.$nextTick()

    // Verify UI updated in real-time
    expect(statusCell.text()).toBe('Working...')
    expect(statusCell.element.style.color).toBe('rgb(255, 215, 0)')
    expect(statusCell.element.style.fontStyle).toBe('italic')

    // Simulate completion: working → complete
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'complete'
    })

    await wrapper.vm.$nextTick()

    // Verify completion status
    expect(statusCell.text()).toBe('Complete')
    expect(statusCell.element.style.color).toBe('rgb(103, 189, 109)')
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('handles failure scenario correctly', async () => {
    // Start with working agent
    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Test' },
        agents: [
          { id: 'agent-uuid', agent_type: 'implementor', agent_name: 'Implementor', status: 'working' }
        ]
      },
      global: {
        plugins: [store]
      }
    })

    // Simulate failure
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'failed'
    })

    await wrapper.vm.$nextTick()

    const statusCell = wrapper.find('.status-cell')
    expect(statusCell.text()).toBe('Failed')
    expect(statusCell.element.style.color).toBe('rgb(229, 57, 53)')
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('handles cancellation scenario correctly', async () => {
    // Start with working agent
    wrapper = mount(JobsTab, {
      props: {
        project: { id: 'project-uuid', name: 'Test' },
        agents: [
          { id: 'agent-uuid', agent_type: 'tester', agent_name: 'Tester', status: 'working' }
        ]
      },
      global: {
        plugins: [store]
      }
    })

    // Simulate cancellation
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'cancelled'
    })

    await wrapper.vm.$nextTick()

    const statusCell = wrapper.find('.status-cell')
    expect(statusCell.text()).toBe('Cancelled')
    expect(statusCell.element.style.color).toBe('rgb(255, 152, 0)')
    expect(statusCell.element.style.fontStyle).not.toBe('italic')
  })

  it('maintains multi-tenant isolation during rapid updates', async () => {
    const statusCell = wrapper.find('.status-cell')

    // Event from correct tenant (should update)
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'working'
    })
    await wrapper.vm.$nextTick()
    expect(statusCell.text()).toBe('Working...')

    // Event from wrong tenant (should NOT update)
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'other-tenant',
      status: 'complete'
    })
    await wrapper.vm.$nextTick()
    expect(statusCell.text()).toBe('Working...')  // Still "Working...", not "Complete"

    // Event from correct tenant (should update)
    emitFn('agent:status_changed', {
      job_id: 'agent-uuid',
      tenant_key: 'test-tenant',
      status: 'complete'
    })
    await wrapper.vm.$nextTick()
    expect(statusCell.text()).toBe('Complete')
  })
})
```

---

## Deliverables

**Files to Create**:
- ✅ `frontend/src/utils/statusConfig.js` (status mapping utility - 80 lines)
- ✅ `tests/unit/JobsTab-status.spec.js` (unit tests - 250 lines)
- ✅ `tests/integration/jobstab-status-updates.spec.js` (integration tests - 150 lines)

**Files to Modify**:
- ✅ `frontend/src/components/projects/JobsTab.vue` (line 46 + WebSocket handler - ~30 line change)

**Success Criteria**:
- [ ] Status displays dynamically from `agent.status` field (NOT hardcoded)
- [ ] "Waiting." → Yellow (#ffd700), italic
- [ ] "Working..." → Yellow (#ffd700), italic
- [ ] "Complete" → Green (#67bd6d), NOT italic
- [ ] "Failed" → Red (#e53935), NOT italic
- [ ] "Cancelled" → Orange (#ff9800), NOT italic
- [ ] "Unknown" → Gray (#666), NOT italic (graceful degradation)
- [ ] WebSocket listener registered on mount
- [ ] WebSocket listener removed on unmount
- [ ] Multi-tenant isolation verified (cross-tenant events rejected)
- [ ] Test coverage: >80% (11/11 unit tests + 4/4 integration tests passing)
- [ ] No console errors in DevTools
- [ ] No memory leaks (verify in DevTools Memory Profiler)

---

## Multi-Tenant Isolation (CRITICAL)

**Security Check**:
```javascript
const handleStatusUpdate = (data) => {
  // CRITICAL: Always verify tenant_key matches current user's tenant
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[JobsTab] Status update rejected: tenant mismatch', {
      expected: currentTenantKey.value,
      received: data.tenant_key
    })
    return  // REJECT cross-tenant events
  }

  // Safe to update UI - event is from same tenant
  const agent = props.agents.find(a => a.id === data.job_id)
  if (agent) {
    agent.status = data.status
    console.log(`[JobsTab] Agent ${data.job_id} status updated: ${data.status}`)
  }
}
```

**Why This Matters**:
- **Security**: Prevents Tenant A from seeing Tenant B's agent status updates
- **Data Integrity**: Ensures UI only shows data user is authorized to see
- **Compliance**: Required for multi-tenant SaaS architecture

**Test Verification**:
```javascript
it('rejects cross-tenant events', async () => {
  handler({
    job_id: 'agent-1',
    tenant_key: 'other-tenant',  // DIFFERENT tenant
    status: 'complete'
  })

  // Verify UI NOT updated
  expect(wrapper.find('.status-cell').text()).toBe('Working...')  // Still original status

  // Verify warning logged
  expect(consoleWarnSpy).toHaveBeenCalledWith(
    expect.stringContaining('tenant mismatch')
  )
})
```

---

## Performance Considerations

### Reactive Updates
- **Vue 3 Reactivity**: Use `ref`/`reactive` for agents array
- **Minimal Re-renders**: Status updates trigger only affected row (not entire table)
- **Debouncing**: If multiple rapid updates occur, consider debouncing (100ms)

```javascript
import { debounce } from 'lodash-es'

const debouncedStatusUpdate = debounce((data) => {
  const agent = props.agents.find(a => a.id === data.job_id)
  if (agent) {
    agent.status = data.status
  }
}, 100)
```

### Memory Management
- **WebSocket Listeners**: MUST be cleaned up on unmount (verified in tests)
- **No Memory Leaks**: Event handlers properly removed
- **Verification**: Use DevTools Memory Profiler to verify no leaks

**DevTools Check**:
1. Open Chrome DevTools → Memory tab
2. Take heap snapshot before mounting JobsTab
3. Mount JobsTab
4. Take heap snapshot after mounting
5. Unmount JobsTab
6. Force garbage collection (DevTools → Collect garbage icon)
7. Take heap snapshot after unmount
8. Verify no JobsTab objects retained

---

## Testing Checklist

### Unit Tests (11 tests)
- [ ] Status "working" displays correctly (yellow italic)
- [ ] Status "waiting" displays correctly (yellow italic)
- [ ] Status "complete" displays correctly (green, NOT italic)
- [ ] Status "failed" displays correctly (red, NOT italic)
- [ ] Status "cancelled" displays correctly (orange, NOT italic)
- [ ] Invalid status displays "Unknown" (gray, NOT italic)
- [ ] WebSocket listener registered on mount
- [ ] WebSocket listener removed on unmount
- [ ] WebSocket event updates UI correctly
- [ ] Cross-tenant events rejected (multi-tenant isolation)
- [ ] Non-existent agent handled gracefully
- [ ] Multiple sequential updates work correctly

### Integration Tests (4 tests)
- [ ] Real-time status updates (waiting → working → complete)
- [ ] Failure scenario (working → failed)
- [ ] Cancellation scenario (working → cancelled)
- [ ] Multi-tenant isolation during rapid updates

### Manual Testing
- [ ] Open JobsTab in browser
- [ ] Verify status displays correctly for each status value
- [ ] Simulate backend status change (via API or WebSocket)
- [ ] Verify UI updates in real-time without page refresh
- [ ] Check console for errors (should be none)
- [ ] Verify colors match design tokens
- [ ] Verify italic vs non-italic rendering

---

## Next Steps

**Parallel with 0243b**:
- This handover (0243c): JobsTab dynamic status
- 0243b: LaunchTab layout polish (independent work)

**Blocks**:
- 0243d: Agent action buttons (needs dynamic status working)
- 0243e: Real-time agent monitoring (needs dynamic status + actions)
- 0243f: Integration testing (needs all components complete)

**Deployment**:
- After all tests pass, deploy to staging environment
- Verify real backend WebSocket events trigger UI updates
- Load test with multiple concurrent agents updating status
- Monitor for memory leaks over 30-minute session

---

## Estimated Timeline

**Total**: 6-8 hours

**Breakdown**:
- Status config utility (statusConfig.js): 1 hour
- JobsTab template update (line 46): 1 hour
- JobsTab script update (WebSocket handler): 2 hours
- Unit test writing (11 tests): 2 hours
- Integration test writing (4 tests): 1 hour
- Manual testing + bug fixes: 1-2 hours

**Milestones**:
- Hour 2: Status config complete, template updated
- Hour 4: WebSocket handler working, unit tests passing
- Hour 6: Integration tests passing, manual testing complete
- Hour 8: All bugs fixed, code reviewed, ready for merge

---

## Agent Instructions

**You are a tdd-implementor agent**. This is CRITICAL 0242b fix:

### Phase 1: RED (2 hours)
1. **Write failing tests FIRST** in `tests/unit/JobsTab-status.spec.js`
   - Test all 5 status values (waiting, working, complete, failed, cancelled)
   - Test "Unknown" for invalid status (graceful degradation)
   - Test WebSocket event handling (mount, unmount, status update)
   - Test multi-tenant isolation (CRITICAL security check)
   - Test error scenarios (non-existent agent, invalid data)

2. **Run tests and verify they FAIL**
   - Expected: All 11 tests should fail with "Waiting." hardcoded
   - Command: `npm run test:unit -- JobsTab-status.spec.js`

### Phase 2: GREEN (3 hours)
1. **Create statusConfig.js utility**
   - Define 5 status configurations (waiting, working, complete, failed, cancelled)
   - Implement 4 helper functions (getStatusLabel, getStatusColor, isStatusItalic, getStatusChipColor)
   - Add JSDoc comments

2. **Update JobsTab.vue template (line 46)**
   - Replace hardcoded "Waiting." with dynamic binding
   - Use `:style` binding for color and fontStyle
   - Use `{{ getStatusLabel(agent.status) }}` for text

3. **Update JobsTab.vue script**
   - Add imports (statusConfig, useWebSocket, useStore)
   - Add `currentTenantKey` computed property
   - Implement `handleStatusUpdate` function with multi-tenant check
   - Register WebSocket listener in `onMounted`
   - Cleanup WebSocket listener in `onUnmounted`

4. **Run tests and verify they PASS**
   - Expected: All 11 tests should pass
   - Command: `npm run test:unit -- JobsTab-status.spec.js`

### Phase 3: REFACTOR (1 hour)
1. **Clean up code**
   - Add JSDoc comments to all functions
   - Remove unused imports
   - Improve error messages
   - Run linter: `npm run lint`

2. **Verify code quality**
   - Run coverage: `npm run test:unit -- --coverage`
   - Target: >80% coverage
   - Check for memory leaks (DevTools Memory Profiler)

### Phase 4: Integration Test (1-2 hours)
1. **Write integration tests** in `tests/integration/jobstab-status-updates.spec.js`
   - Test real-time updates (waiting → working → complete)
   - Test failure scenario
   - Test cancellation scenario
   - Test multi-tenant isolation during rapid updates

2. **Run integration tests**
   - Expected: All 4 tests should pass
   - Command: `npm run test:integration -- jobstab-status-updates.spec.js`

### Phase 5: Report (15 minutes)
1. **Summary for Orchestrator**
   - Test coverage % (unit + integration)
   - Any blockers encountered
   - Screenshots of UI (before/after)
   - Performance notes (memory usage, re-render count)

2. **Deliverables**
   - All files created/modified
   - Test results (11/11 unit + 4/4 integration passing)
   - Code review checklist completed

**CRITICAL**: Do NOT proceed to 0243d until this fix is verified working in staging. This is the foundation for all agent action buttons and real-time monitoring features.

---

## Troubleshooting

### Issue: Tests Fail with "WebSocket listener not registered"
**Solution**: Verify `onMounted` is called correctly in component lifecycle.

### Issue: Status not updating in UI
**Solution**: Check Vue reactivity - use `ref` or `reactive` for agents array.

### Issue: Cross-tenant events NOT rejected
**Solution**: Verify `currentTenantKey` computed property is correct and matches Vuex store state.

### Issue: Memory leak detected
**Solution**: Verify `onUnmounted` cleanup is called. Use `wrapper.unmount()` in tests.

### Issue: Colors don't match design
**Solution**: Use hex values from statusConfig.js, NOT CSS variables (until 0243a merged).

---

## References

**Backend Code**:
- `src/giljo_mcp/models.py` (MCPAgentJob.status field)
- `src/giljo_mcp/services/agent_job_manager.py` (WebSocket emission)

**Frontend Code**:
- `frontend/src/components/projects/JobsTab.vue` (current implementation)
- `frontend/src/composables/useWebSocket.js` (WebSocket composable)
- `frontend/src/store/index.js` (Vuex store with user.tenant_key)

**Design Tokens** (0243a):
- `frontend/src/styles/design-tokens.scss` (color variables)

**Related Handovers**:
- 0242a: LaunchTab visual polish (completed)
- 0242b: THIS handover (JobsTab dynamic status)
- 0243a: Design tokens standardization (dependency)
- 0243d: Agent action buttons (blocked by this)

---

**End of Handover 0243c**
