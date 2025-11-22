# Handover 0232: Bottom Message Composer Bar

**Status**: ✅ DEPRECATED - Already Complete via Handover 0231 Phase 4
**Completion Date**: 2025-11-21
**Actual Effort**: 0 hours (pre-existing implementation)
**Dependencies**: Handover 0226 (backend API extensions)
**Part of**: Visual Refactor Series (0225-0237)

---

## Implementation Summary

**Status**: ✅ **DEPRECATED** - This handover was fully implemented in Handover 0231 Phase 4 (commit c96fa89c).

**Finding**: All sticky positioning functionality already exists in `MessageInput.vue` (lines 396-404). The `.position-sticky` CSS block matches this handover's specification exactly.

**What Already Exists**:
- `position` prop with validator (lines 89-93) supporting `inline`, `modal`, and `sticky` modes
- Complete sticky CSS implementation (lines 396-404):
  - `position: sticky`
  - `bottom: 0`
  - `background: white`
  - `box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1)`
  - `z-index: 100`
  - `padding: 16px`
  - `border-top: 1px solid rgba(0, 0, 0, 0.12)`
- Tests verifying sticky behavior (MessageInput.0231.spec.js)

**Verification**: See `handovers/0232_investigation_report.md` for complete analysis.

**Recommendation**: Proceed directly to Handover 0233.

---

## Original Specification (For Reference)

---

## ⚠️ PRE-IMPLEMENTATION VERIFICATION REQUIRED

**CRITICAL**: Before implementing this handover, verify existing MessageInput sticky CSS.

**Verification Steps**:
1. Open `frontend/src/components/projects/MessageInput.vue`
2. Check for existing sticky CSS (around lines 165-174 based on codebase analysis)
3. Run the application and test sticky behavior

**Possible Outcomes**:
- ✅ **Sticky CSS exists AND works** → Mark handover as "ALREADY COMPLETE" (no work needed)
- ⚠️ **Sticky CSS exists BUT broken** → Debug existing CSS (don't add duplicate CSS)
- ❌ **No sticky CSS** → Proceed with implementation below

**Why This Verification**:
- Codebase analysis suggests MessageInput.vue may already have sticky positioning (lines 165-174)
- Implementing duplicate CSS will create conflicts
- Verify first, implement only if needed

---

## Objective

Enable sticky bottom message composer by **reusing existing MessageInput.vue** component with position mode support. This approach requires only CSS changes to the existing 360-line component rather than creating a new 150-line duplicate.

**CRITICAL**: Per QUICK_LAUNCH.txt line 19 - NO parallel systems. We enhance MessageInput (360 lines exist), not duplicate it.

---

## Current State Analysis

### Existing Message Input Component

**Location**: `frontend/src/components/projects/MessageInput.vue` (360 lines)

**Current Features**:
- Message composition textarea
- Character counter (10K limit)
- Send button with keyboard shortcuts (Ctrl+Enter)
- File attachment support
- Auto-grow textarea
- Validation logic

**Reusable Capabilities**:
- All 360 lines work for sticky positioning
- Only needs `position` prop for CSS styling
- No duplication needed

### Vision Document Requirements

**Bottom Composer Features**:
- Fixed to bottom of viewport
- Shadow/elevation for visual separation
- Same functionality as inline composer
- Keyboard shortcuts preserved

---

## TDD Approach

### 0. Test-Driven Development Order

**Test-Driven Development Order**:

1. Write failing tests for MessageInput sticky mode (applies correct CSS)
2. Add position styling to existing MessageInput
3. Write failing tests for sticky behavior (stays at bottom on scroll)
4. Verify CSS position: sticky works as expected
5. Refactor if needed

**Test Focus**: CSS positioning (component behaves same, just positioned differently).

**Key Principle**: Add CSS classes, don't duplicate logic.

---

## Implementation Plan

### Enhance Existing MessageInput for Position Modes

**File**: `frontend/src/components/projects/MessageInput.vue` (MODIFY EXISTING - add 30 lines)

**NOTE**: This was already prepared in Handover 0231. No additional changes needed.

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
      outlined
      dense
    >
      <template #append>
        <v-btn
          icon
          :disabled="!canSend"
          color="primary"
          @click="handleSend"
        >
          <v-icon>mdi-send</v-icon>
        </v-btn>
      </template>
    </v-textarea>

    <!-- Character counter (existing) -->
    <div class="text-caption text-grey">
      {{ remainingCharacters }} / 10000 characters
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  jobId: String,
  position: {  // ALREADY ADDED in Handover 0231
    type: String,
    default: 'inline',
    validator: (v) => ['inline', 'modal', 'sticky'].includes(v)
  }
})

// EXISTING LOGIC (lines 1-360) remains unchanged
</script>

<style scoped>
/* EXISTING STYLES remain unchanged */

/* Position-specific styling (ALREADY ADDED in Handover 0231) */
.position-inline {
  /* Default inline styles */
  padding: 16px;
}

.position-modal {
  /* Modal footer styles */
  border-top: 1px solid #e0e0e0;
  padding-top: 16px;
  width: 100%;
}

.position-sticky {
  /* Sticky bottom bar styles (NEW for this handover) */
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
  z-index: 100;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
}
</style>
```

**Impact**: 15 lines CSS added (sticky positioning) to existing 360-line component

**Total Changes from Handover 0231**: 30 lines (all position modes)

**NEW for Handover 0232**: 15 lines (sticky mode only)

---

## Integration with Main View

**File**: `frontend/src/views/JobsTab.vue` or `ProjectsView.vue`

Add sticky message composer to bottom of view:

```vue
<template>
  <v-container fluid class="jobs-view">
    <!-- Agent display (card/table views) -->
    <AgentCardGrid
      :agents="agents"
      @view-details="handleOpenMessageModal"
    />

    <!-- Message history panel (existing) -->
    <MessagePanel
      :job-id="activeJobId"
      :messages="messages"
      mode="inline"
    />

    <!-- Sticky Bottom Message Composer (NEW - 5 lines) -->
    <MessageInput
      v-if="activeJobId"
      :job-id="activeJobId"
      :position="'sticky'"
      @message-sent="handleMessageSent"
    />
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import MessageInput from '@/components/projects/MessageInput.vue'  // REUSE

const activeJobId = ref(null)

function handleMessageSent(messageData) {
  // Handle new message
  console.log('Message sent:', messageData)
}
</script>

<style scoped>
.jobs-view {
  /* Ensure enough bottom padding for sticky composer */
  padding-bottom: 150px;  /* Approximate height of sticky composer */
}
</style>
```

**Impact**: 5 lines added to view (not 150+ for new component)

---

## Code Reduction Summary

| Component | Original Approach | Redesigned Approach | Reduction |
|-----------|-------------------|---------------------|-----------|
| **MessageComposer.vue** | 150 lines (new component) | **Not created** | 150 lines saved |
| **MessageInput.vue** | Unchanged | +15 lines (sticky CSS) | 15 lines added |
| **Net Code** | +150 lines | +15 lines | **90% reduction** |

**NOTE**: If counting from Handover 0231, total MessageInput changes = 30 lines (all 3 position modes)

---

## Testing Criteria

### 1. Sticky Positioning Test

**Test**: Verify sticky positioning works correctly

```javascript
// tests/components/test_message_input.spec.js

describe('MessageInput', () => {
  it('renders in inline position by default', () => {
    const wrapper = mount(MessageInput, {
      props: { jobId: 'test-uuid' }
    })

    expect(wrapper.find('.position-inline').exists()).toBe(true)
    expect(wrapper.find('.position-sticky').exists()).toBe(false)
  })

  it('renders in sticky position when specified', () => {
    const wrapper = mount(MessageInput, {
      props: {
        jobId: 'test-uuid',
        position: 'sticky'
      }
    })

    expect(wrapper.find('.position-sticky').exists()).toBe(true)
    expect(wrapper.find('.position-inline').exists()).toBe(false)
  })

  it('applies sticky CSS in sticky mode', () => {
    const wrapper = mount(MessageInput, {
      props: { jobId: 'test-uuid', position: 'sticky' }
    })

    const input = wrapper.find('.position-sticky')
    const styles = window.getComputedStyle(input.element)

    expect(styles.position).toBe('sticky')
    expect(styles.bottom).toBe('0px')
    expect(styles.zIndex).toBe('100')
  })
})
```

### 2. Functionality Preservation Test

**Test**: Verify same functionality across all positions

```javascript
it('sends messages correctly in all position modes', async () => {
  const positions = ['inline', 'modal', 'sticky']

  for (const position of positions) {
    const wrapper = mount(MessageInput, {
      props: { jobId: 'test-uuid', position }
    })

    // Type message
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Test message')

    // Click send button
    const sendButton = wrapper.find('[data-test="send-button"]')
    await sendButton.trigger('click')

    // Verify message sent
    expect(wrapper.emitted('message-sent')).toBeTruthy()
    expect(wrapper.emitted('message-sent')[0][0].content).toBe('Test message')
  }
})
```

### 3. Keyboard Shortcuts Test

**Test**: Verify Ctrl+Enter works in sticky mode

```javascript
it('sends message on Ctrl+Enter in sticky mode', async () => {
  const wrapper = mount(MessageInput, {
    props: { jobId: 'test-uuid', position: 'sticky' }
  })

  const textarea = wrapper.find('textarea')
  await textarea.setValue('Test message')

  // Simulate Ctrl+Enter
  await textarea.trigger('keydown', { key: 'Enter', ctrlKey: true })

  expect(wrapper.emitted('message-sent')).toBeTruthy()
})
```

---

## Success Criteria

- ✅ MessageInput.vue enhanced with `position="sticky"` support (+15 lines CSS)
- ✅ Sticky composer stays at bottom of viewport on scroll
- ✅ Same functionality as inline/modal modes (character counter, validation, send)
- ✅ Keyboard shortcuts preserved (Ctrl+Enter)
- ✅ Zero logic duplication (all positions use same component)
- ✅ Total code reduction: 90% vs creating new MessageComposer component

---

## Architecture Compliance

**QUICK_LAUNCH.txt line 19**: "NO parallel systems"
- ✅ MessageInput enhanced, not duplicated
- ✅ Single component supports 3 position modes (inline, modal, sticky)
- ✅ Single source of truth for message composition logic

**QUICK_LAUNCH.txt line 28**: "No zombie code"
- ✅ All existing MessageInput logic preserved
- ✅ Only added CSS classes (no commented blocks)
- ✅ No orphaned duplicate components

---

## Visual Design

**Sticky Composer Appearance**:
- **Shadow**: `box-shadow: 0 -2px 8px rgba(0,0,0,0.1)` (subtle elevation)
- **Border**: `border-top: 1px solid #e0e0e0` (visual separation)
- **Background**: `background: white` (opaque, not transparent)
- **Z-index**: `z-index: 100` (above other content)
- **Padding**: `padding: 16px` (consistent with inline mode)

---

## Next Steps

→ **Handover 0233**: Job Read/Acknowledged Indicators
- Add visual badges for message counts in status board table
- Integrate with table view endpoint's unread_count/acknowledged_count fields
- WebSocket real-time updates for badge changes

→ **Handover 0234**: UI Polish & Accessibility
- Keyboard navigation for sticky composer
- ARIA labels for screen readers
- Responsive layout improvements

---

## References

- **Vision Document**: Slides 10, 17 (message field and send button)
- **Existing Component**: `frontend/src/components/projects/MessageInput.vue` (360 lines - REUSED)
- **Backend API**: `/api/agent-jobs/{job_id}/messages` (message send endpoint)
- **Character Limit**: `MAX_MESSAGE_LENGTH = 10000` (from `src/giljo_mcp/tools/agent_messaging.py`)
- **CSS position:sticky**: [MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/CSS/position)
