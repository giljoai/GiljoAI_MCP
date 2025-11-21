# Handover 0231: Message Transcript Modal

**Status**: Ready for Implementation
**Priority**: Medium
**Estimated Effort**: 2 hours (reduced from 4 via component reuse)
**Dependencies**: Handover 0228 (StatusBoardTable component)
**Part of**: Visual Refactor Series (0225-0237)

---

## Objective

Create MessageModal component by **reusing existing MessagePanel.vue** component with modal mode support. Trigger on table row click in AgentTableView. This approach enhances existing components rather than creating duplicates.

**CRITICAL**: Per QUICK_LAUNCH.txt line 19 - NO parallel systems. We reuse MessagePanel (347 lines exist), not duplicate it.

---

## Current State Analysis

### Existing Message Panel

**Location**: `frontend/src/components/messages/MessagePanel.vue` (347 lines)

**Current Features**:
- Display messages in chronological order
- Filter by message type (sent, received, broadcast)
- Filter by message status (pending, acknowledged)
- Search functionality
- Virtual scroll for performance

**Reusable Capabilities**:
- All 347 lines can be reused for modal display
- Only needs `mode` prop to distinguish inline vs modal styling
- No duplication needed

### Vision Document Requirements (Slide 18)

**Modal Layout**:
- Centered overlay (800px width, max 600px height)
- MessagePanel component inside modal
- MessageInput component in modal footer
- Close on X button, ESC key, click outside

---

## TDD Approach

### 0. Test-Driven Development Order

**Test-Driven Development Order**:

1. Write failing tests for MessagePanel modal mode (renders correctly with mode="modal")
2. Add modal mode styling to existing MessagePanel
3. Write failing tests for MessageModal wrapper (opens/closes, passes props correctly)
4. Implement thin MessageModal wrapper component
5. Write failing tests for MessageInput modal position (renders in modal footer)
6. Add position prop to existing MessageInput
7. Refactor if needed

**Test Focus**: Component reuse (same MessagePanel works in both inline and modal contexts).

**Key Principle**: Add props to existing components, don't duplicate logic.

---

## Implementation Plan

### 1. Enhance Existing MessagePanel for Modal Mode

**File**: `frontend/src/components/messages/MessagePanel.vue` (MODIFY EXISTING - add 10 lines)

Add modal mode support to EXISTING component:

```vue
<template>
  <div :class="['message-panel', `mode-${mode}`]">
    <!-- EXISTING CONTENT (lines 1-347) remains unchanged -->
    <!-- Virtual scroll, filtering, search - all existing functionality -->
  </div>
</template>

<script setup>
const props = defineProps({
  messages: Array,
  jobId: String,
  mode: {  // NEW PROP (1 line)
    type: String,
    default: 'inline',
    validator: (v) => ['inline', 'modal'].includes(v)
  }
})
</script>

<style scoped>
/* EXISTING STYLES (lines 1-50) remain unchanged */

/* NEW: Modal-specific styling (5 lines) */
.mode-modal {
  max-height: 600px;
  overflow-y: auto;
  padding: 0;
}
</style>
```

**Impact**: 10 lines added to existing 347-line component (not 200+ new component)

---

### 2. Create Thin Modal Wrapper

**File**: `frontend/src/components/messages/MessageModal.vue` (NEW - 80 lines)

```vue
<template>
  <v-dialog
    v-model="isOpen"
    max-width="800px"
    @click:outside="close"
    @keydown.esc="close"
  >
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <v-icon class="mr-2">mdi-message-text</v-icon>
          <span>Messages: {{ agentName }}</span>
        </div>
        <v-btn icon size="small" @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-0">
        <!-- REUSE EXISTING MessagePanel -->
        <MessagePanel
          :messages="messages"
          :job-id="jobId"
          :mode="'modal'"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <!-- REUSE EXISTING MessageInput -->
        <MessageInput
          :job-id="jobId"
          :position="'modal'"
          @message-sent="handleMessageSent"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'
import MessagePanel from '@/components/messages/MessagePanel.vue'  // REUSE
import MessageInput from '@/components/projects/MessageInput.vue'  // REUSE

const props = defineProps({
  isOpen: Boolean,
  jobId: String,
  agentName: String,
  messages: Array
})

const emit = defineEmits(['close', 'message-sent'])

const isOpen = computed({
  get: () => props.isOpen,
  set: (value) => emit('update:isOpen', value)
})

function close() {
  emit('close')
}

function handleMessageSent(messageData) {
  emit('message-sent', messageData)
}
</script>

<style scoped>
/* Minimal modal-specific styles */
.v-card-text {
  max-height: 600px;
  overflow-y: auto;
}
</style>
```

**Impact**: 80 lines (thin wrapper) vs 200+ duplicate = **60% reduction**

---

### 3. Enhance Existing MessageInput for Position Modes

**File**: `frontend/src/components/projects/MessageInput.vue` (MODIFY EXISTING - add 30 lines)

Add position prop to EXISTING component:

```vue
<template>
  <div :class="['message-input', `position-${position}`]">
    <!-- EXISTING CONTENT (lines 1-360) remains unchanged -->
    <v-textarea
      v-model="message"
      placeholder="Type your message..."
      :max-length="10000"
      rows="3"
      auto-grow
    />
    <!-- ... existing send button, character counter, etc ... -->
  </div>
</template>

<script setup>
const props = defineProps({
  jobId: String,
  position: {  // NEW PROP (1 line)
    type: String,
    default: 'inline',
    validator: (v) => ['inline', 'modal', 'sticky'].includes(v)
  }
})

// EXISTING LOGIC (lines 1-360) remains unchanged
</script>

<style scoped>
/* EXISTING STYLES remain unchanged */

/* NEW: Position-specific styling (15 lines) */
.position-sticky {
  position: sticky;
  bottom: 0;
  background: white;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
  z-index: 10;
}

.position-modal {
  border-top: 1px solid #e0e0e0;
  padding-top: 16px;
  width: 100%;
}
</style>
```

**Impact**: 30 lines added to existing 360-line component (not 150+ new component) = **80% reduction**

---

## Code Reduction Summary

| Component | Original Approach | Redesigned Approach | Reduction |
|-----------|-------------------|---------------------|-----------|
| **MessageTranscriptModal.vue** | 200 lines (duplicate) | **Not created** | 200 lines saved |
| **MessagePanel.vue** | Unchanged | +10 lines (mode prop) | 10 lines added |
| **MessageModal.vue** | N/A | +80 lines (wrapper) | 60% vs original |
| **MessageInput.vue** | Unchanged | +30 lines (position) | 30 lines added |
| **Net Code** | +200 lines | +120 lines | **40% reduction** |

---

## Integration with AgentTableView

**File**: `frontend/src/components/orchestration/AgentTableView.vue` (from Handover 0228)

Update row click handler:

```vue
<script setup>
const emit = defineEmits(['row-click', 'launch-agent'])

function handleRowClick(event, { item }) {
  // Emit event to parent (JobsTab) to open MessageModal
  emit('row-click', {
    jobId: item.job_id,
    agentName: item.agent_name,
    messages: item.messages || []
  })
}
</script>
```

**File**: `frontend/src/views/JobsTab.vue`

Handle modal open:

```vue
<template>
  <v-container>
    <!-- Agent display (card/table views) -->
    <AgentCardGrid
      :agents="agents"
      @view-details="handleOpenMessageModal"
    />

    <!-- Message Modal (NEW - 5 lines) -->
    <MessageModal
      v-model:is-open="messageModalOpen"
      :job-id="selectedJobId"
      :agent-name="selectedAgentName"
      :messages="selectedMessages"
      @message-sent="handleMessageSent"
    />
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import MessageModal from '@/components/messages/MessageModal.vue'

const messageModalOpen = ref(false)
const selectedJobId = ref(null)
const selectedAgentName = ref('')
const selectedMessages = ref([])

function handleOpenMessageModal({ jobId, agentName, messages }) {
  selectedJobId.value = jobId
  selectedAgentName.value = agentName
  selectedMessages.value = messages
  messageModalOpen.value = true
}

function handleMessageSent(messageData) {
  // Handle new message (e.g., refresh messages list)
  console.log('Message sent:', messageData)
}
</script>
```

**Impact**: 15 lines added to JobsTab (not 50+ for separate modal handling)

---

## Testing Criteria

### 1. MessagePanel Modal Mode

**Test**: Verify modal mode styling applied correctly

```javascript
// tests/components/test_message_panel.spec.js

describe('MessagePanel', () => {
  it('renders in inline mode by default', () => {
    const wrapper = mount(MessagePanel, {
      props: { jobId: 'test-uuid', messages: [] }
    })

    expect(wrapper.find('.mode-inline').exists()).toBe(true)
    expect(wrapper.find('.mode-modal').exists()).toBe(false)
  })

  it('renders in modal mode when specified', () => {
    const wrapper = mount(MessagePanel, {
      props: {
        jobId: 'test-uuid',
        messages: [],
        mode: 'modal'
      }
    })

    expect(wrapper.find('.mode-modal').exists()).toBe(true)
    expect(wrapper.find('.mode-inline').exists()).toBe(false)
  })

  it('applies max-height in modal mode', () => {
    const wrapper = mount(MessagePanel, {
      props: { jobId: 'test-uuid', messages: [], mode: 'modal' }
    })

    const panel = wrapper.find('.mode-modal')
    expect(panel.element.style.maxHeight).toBe('600px')
  })
})
```

### 2. MessageModal Wrapper

**Test**: Verify modal opens/closes correctly

```javascript
// tests/components/test_message_modal.spec.js

describe('MessageModal', () => {
  it('renders MessagePanel in modal mode', () => {
    const wrapper = mount(MessageModal, {
      props: {
        isOpen: true,
        jobId: 'test-uuid',
        agentName: 'Test Agent',
        messages: []
      }
    })

    const messagePanel = wrapper.findComponent(MessagePanel)
    expect(messagePanel.exists()).toBe(true)
    expect(messagePanel.props('mode')).toBe('modal')
  })

  it('renders MessageInput in modal position', () => {
    const wrapper = mount(MessageModal, {
      props: {
        isOpen: true,
        jobId: 'test-uuid',
        agentName: 'Test Agent',
        messages: []
      }
    })

    const messageInput = wrapper.findComponent(MessageInput)
    expect(messageInput.exists()).toBe(true)
    expect(messageInput.props('position')).toBe('modal')
  })

  it('closes on X button click', async () => {
    const wrapper = mount(MessageModal, {
      props: {
        isOpen: true,
        jobId: 'test-uuid',
        agentName: 'Test Agent',
        messages: []
      }
    })

    const closeButton = wrapper.find('[data-test="close-button"]')
    await closeButton.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('closes on ESC key press', async () => {
    const wrapper = mount(MessageModal, {
      props: {
        isOpen: true,
        jobId: 'test-uuid',
        agentName: 'Test Agent',
        messages: []
      }
    })

    const dialog = wrapper.findComponent({ name: 'VDialog' })
    await dialog.trigger('keydown.esc')

    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
```

### 3. Component Reuse Verification

**Test**: Verify no logic duplication

```javascript
it('MessagePanel behaves identically in inline and modal modes', async () => {
  const messages = [
    { id: 1, content: 'Test message', status: 'pending' }
  ]

  // Inline mode
  const inlineWrapper = mount(MessagePanel, {
    props: { jobId: 'test-uuid', messages, mode: 'inline' }
  })

  // Modal mode
  const modalWrapper = mount(MessagePanel, {
    props: { jobId: 'test-uuid', messages, mode: 'modal' }
  })

  // Verify same message rendering logic
  expect(inlineWrapper.html()).toContain('Test message')
  expect(modalWrapper.html()).toContain('Test message')

  // Verify same filtering/search logic (existing functionality)
  expect(inlineWrapper.vm.filteredMessages).toEqual(modalWrapper.vm.filteredMessages)
})
```

---

## Success Criteria

- ✅ MessagePanel.vue enhanced with `mode` prop (+10 lines)
- ✅ MessageModal.vue created as thin wrapper (+80 lines)
- ✅ MessageInput.vue enhanced with `position` prop (+30 lines)
- ✅ Zero logic duplication between inline and modal message display
- ✅ Modal opens on table row click
- ✅ Modal closes on X button, ESC key, click outside
- ✅ MessageInput renders in modal footer with correct styling
- ✅ Total code reduction: 40% vs creating duplicate MessageTranscriptModal

---

## Architecture Compliance

**QUICK_LAUNCH.txt line 19**: "NO parallel systems"
- ✅ MessagePanel reused, not duplicated
- ✅ MessageInput reused, not duplicated
- ✅ Single source of truth for message display logic

**QUICK_LAUNCH.txt line 28**: "No zombie code"
- ✅ All existing MessagePanel/MessageInput logic preserved
- ✅ Only added mode/position props (no commented blocks)
- ✅ No orphaned duplicate components

---

## Next Steps

→ **Handover 0232**: Bottom Message Composer Bar
- Enhance MessageInput for sticky position mode
- Add bottom message bar to main view (already prepared via `position` prop)

→ **Handover 0233**: UI Polish & Accessibility
- Keyboard navigation for modal
- ARIA labels for screen readers
- Responsive layout improvements

---

## References

- **Vision Document**: Slide 18 (Message transcript modal view)
- **Existing Components**:
  - `frontend/src/components/messages/MessagePanel.vue` (347 lines - REUSED)
  - `frontend/src/components/projects/MessageInput.vue` (360 lines - REUSED)
- **AgentTableView**: Handover 0228 (row click trigger)
- **Vuetify v-dialog**: [Documentation](https://vuetifyjs.com/en/components/dialogs/)
