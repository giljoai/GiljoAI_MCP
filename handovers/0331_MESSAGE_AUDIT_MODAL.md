# Handover 0331: Message Audit Modal for Agent Communication Review

**Date:** 2025-12-06
**From Agent:** Research/Planning Session
**To Agent:** ux-designer, frontend-tester
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation

---

## Task Summary

Build a two-layer message audit modal triggered by the folder icon on agent cards in JobsTab. This enables developers to review agent communication history as an auditable "story" of coordination between agents.

**Why:** Agents communicate via MCP messaging for coordination and decisions. Currently, only counters are visible (Sent/Waiting/Read). Developers need to audit the full conversation flow to understand what happened and diagnose agent behavior issues.

**Expected Outcome:** Clicking the folder icon opens a modal showing all messages for that agent, with tabs for filtering and a detail view for expanded message content including broadcast recipient read status.

---

## Context and Background

### Research Findings (0331 Pre-Work)

**Existing Infrastructure (No Changes Needed):**
- `Message` table with `to_agents`, `acknowledged_by`, `content`, `status`, `priority`, `created_at`
- `MCPAgentJob.messages` JSONB array used for counters
- `MessageModal.vue`, `MessageList.vue`, `MessageItem.vue` exist but NOT wired to folder icon
- WebSocket events: `message:sent`, `message:received`, `message:acknowledged`
- Counters in JobsTab use `status` field, NOT `acknowledged_by`

**Key Insight:** No schema changes required. Counters use `status` field in JSONB, so enhancing `acknowledged_by` display is purely additive.

### Related Handovers
- 0295: Messaging Contract (Reference)
- 0296: Agent Messaging Behavior (Reference)
- 0297: UI Message Status & Job Signaling (Reference)
- 0299: Unified UI Messaging Endpoint (Complete)

---

## Technical Details

### Files to Create/Modify

**New Files:**
1. `frontend/src/components/messages/MessageAuditModal.vue` - Main two-layer modal
2. `frontend/src/components/messages/MessageDetailView.vue` - Expanded message detail (layer 2)

**Files to Modify:**
1. `frontend/src/components/projects/JobsTab.vue` - Wire folder icon to modal
2. `frontend/src/components/StatusBoard/ActionIcons.vue` - Verify `view-messages` event emission

### Data Flow

```
User clicks folder icon (ActionIcons.vue)
  ↓ emits 'view-messages' with job data
JobsTab.vue catches event
  ↓ opens MessageAuditModal with agent.messages
MessageAuditModal.vue
  ↓ Layer 1: Tabbed list (Sent/Waiting/Read)
  ↓ Click message row
MessageDetailView.vue
  ↓ Layer 2: Full message + recipient status
```

### Message Data Structure (from JSONB)

```javascript
// agent.messages array item
{
  id: "uuid",
  from: "developer" | "orchestrator" | "agent_id",
  direction: "inbound" | "outbound",
  status: "pending" | "waiting" | "acknowledged" | "read",
  text: "truncated content (max 200 chars)",
  content: "full message body",
  priority: "normal" | "high" | "urgent",
  timestamp: "ISO datetime",
  to_agents: ["recipient_job_ids"],  // for broadcast
  message_type: "direct" | "broadcast" | "system"
}
```

### Recipient Read Status (for broadcasts)

Compare arrays to determine read status:
- `to_agents`: All intended recipients
- `acknowledged_by`: Recipients who read the message
- **Unread** = in `to_agents` but NOT in `acknowledged_by` (show RED)
- **Read** = in `acknowledged_by` (show GREEN with timestamp if available)

---

## Implementation Plan

### Phase 1: Wire Folder Icon to Modal (30 min)

**File:** `JobsTab.vue`

1. Import existing `MessageModal.vue` or create new `MessageAuditModal.vue`
2. Add reactive state: `showMessageModal`, `selectedAgent`
3. Handle `view-messages` event from ActionIcons
4. Pass `agent.messages` and `agent.agent_name` to modal

**Test:** Click folder icon → modal opens with agent's messages

### Phase 2: Create MessageAuditModal.vue (2-3 hours)

**Structure:**
```vue
<template>
  <v-dialog v-model="isOpen" max-width="800" scrollable>
    <v-card>
      <!-- Header -->
      <v-card-title>Messages: {{ agentName }}</v-card-title>

      <!-- Tabs: Sent | Waiting | Read -->
      <v-tabs v-model="activeTab">
        <v-tab value="sent">Sent ({{ sentCount }})</v-tab>
        <v-tab value="waiting">Waiting ({{ waitingCount }})</v-tab>
        <v-tab value="read">Read ({{ readCount }})</v-tab>
      </v-tabs>

      <!-- Message List -->
      <v-card-text>
        <v-list>
          <v-list-item
            v-for="msg in filteredMessages"
            :key="msg.id"
            @click="selectMessage(msg)"
          >
            <!-- Timestamp | From/To | Preview (30 chars) -->
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Detail View (Layer 2) -->
    <MessageDetailView
      v-if="selectedMessage"
      :message="selectedMessage"
      @close="selectedMessage = null"
    />
  </v-dialog>
</template>
```

**Filtering Logic:**
```javascript
const filteredMessages = computed(() => {
  const msgs = props.messages || []
  switch (activeTab.value) {
    case 'sent':
      return msgs.filter(m => m.from === 'developer' || m.direction === 'outbound')
    case 'waiting':
      return msgs.filter(m => m.status === 'pending' || m.status === 'waiting')
    case 'read':
      return msgs.filter(m => m.status === 'acknowledged' || m.status === 'read')
    default:
      return msgs
  }
})
```

**Test:** Tabs filter correctly, counts match JobsTab counters

### Phase 3: Create MessageDetailView.vue (1-2 hours)

**Structure:**
```vue
<template>
  <v-dialog v-model="isOpen" max-width="600">
    <v-card>
      <!-- Header -->
      <v-card-title>Message Details</v-card-title>

      <!-- Metadata -->
      <v-card-text>
        <div><strong>Message ID:</strong> {{ message.id }}</div>
        <div><strong>From:</strong> {{ message.from }}</div>
        <div><strong>Sent:</strong> {{ formatDate(message.timestamp) }}</div>
        <div><strong>Priority:</strong> {{ message.priority }}</div>
        <div><strong>Type:</strong> {{ displayType }}</div>

        <!-- Full Message Body -->
        <v-divider class="my-3" />
        <div class="message-body">{{ message.content || message.text }}</div>

        <!-- Recipients Section (for broadcasts) -->
        <v-divider class="my-3" v-if="isBroadcast" />
        <div v-if="isBroadcast">
          <strong>Recipients:</strong>
          <v-list dense>
            <v-list-item
              v-for="recipient in recipients"
              :key="recipient.id"
              :class="recipient.read ? 'text-success' : 'text-error'"
            >
              <v-icon :color="recipient.read ? 'success' : 'error'" size="small">
                {{ recipient.read ? 'mdi-check-circle' : 'mdi-alert-circle' }}
              </v-icon>
              {{ recipient.name }}
              <span v-if="recipient.readAt" class="text-caption ml-2">
                read {{ formatDate(recipient.readAt) }}
              </span>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn @click="$emit('close')">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
```

**Recipient Status Logic:**
```javascript
const recipients = computed(() => {
  const toAgents = props.message.to_agents || []
  const acknowledgedBy = props.message.acknowledged_by || []

  return toAgents.map(agentId => ({
    id: agentId,
    name: agentId,  // Could resolve to friendly name if available
    read: acknowledgedBy.includes(agentId),
    readAt: null  // Future: extract from enhanced acknowledged_by structure
  }))
})

const displayType = computed(() => {
  if (props.message.message_type === 'broadcast' ||
      props.message.to_agents?.includes('all')) {
    return 'Broadcast'
  }
  return 'Direct'
})
```

**Test:**
- Direct message shows single recipient
- Broadcast shows all recipients with read (green) / unread (red) status

### Phase 4: Polish & Edge Cases (30 min)

1. Empty state: "No messages" when list is empty
2. Loading state during initial fetch
3. Message preview truncation (30 chars, exclude code blocks)
4. Keyboard navigation (Esc to close)
5. Responsive design for smaller screens

---

## Testing Requirements

### Unit Tests

**File:** `frontend/tests/unit/MessageAuditModal.spec.js`

```javascript
describe('MessageAuditModal', () => {
  test('filters_messages_by_sent_tab')
  test('filters_messages_by_waiting_tab')
  test('filters_messages_by_read_tab')
  test('counts_match_jobstab_counter_logic')
  test('opens_detail_view_on_message_click')
  test('closes_on_escape_key')
})
```

**File:** `frontend/tests/unit/MessageDetailView.spec.js`

```javascript
describe('MessageDetailView', () => {
  test('displays_message_metadata')
  test('displays_full_message_body')
  test('shows_broadcast_label_for_broadcast_messages')
  test('shows_recipient_list_for_broadcasts')
  test('marks_read_recipients_green')
  test('marks_unread_recipients_red')
})
```

### Manual Testing Checklist

1. [ ] Navigate to JobsTab with agents that have messages
2. [ ] Click folder icon → modal opens
3. [ ] Verify tab counts match dashboard counters
4. [ ] Click each tab → messages filter correctly
5. [ ] Click message row → detail view opens
6. [ ] Verify broadcast shows all recipients
7. [ ] Verify unread recipients shown in RED
8. [ ] Press Escape → modals close
9. [ ] Test with 0 messages → empty state shown

---

## Dependencies and Blockers

**Dependencies:**
- None - all required infrastructure exists

**Blockers:**
- None identified

**User Decisions Required:**
- None - all requirements confirmed in research phase

---

## Success Criteria

**Definition of Done:**
- [ ] Folder icon click opens MessageAuditModal
- [ ] Three tabs (Sent/Waiting/Read) filter messages correctly
- [ ] Tab counts match JobsTab counter logic exactly
- [ ] Message list shows: timestamp, from/to, 30-char preview
- [ ] Clicking message opens MessageDetailView
- [ ] Detail view shows: ID, from, sent date, priority, type, full body
- [ ] Broadcast messages show recipient list with read status
- [ ] Unread recipients displayed in RED
- [ ] Read recipients displayed in GREEN
- [ ] Unit tests pass
- [ ] Manual testing checklist complete
- [ ] No regression in existing message counters

---

## Rollback Plan

**If Things Go Wrong:**
- Revert `JobsTab.vue` changes to disconnect modal
- Delete new component files
- No database or API changes to revert

---

## Additional Resources

**Existing Components to Reference:**
- `frontend/src/components/messages/MessageModal.vue`
- `frontend/src/components/messages/MessageItem.vue`
- `frontend/src/components/projects/JobsTab.vue` (counter logic lines 476-501)

**Message Contract:**
- `handovers/0295_MESSAGING_CONTRACT_AND_CATEGORIES.md`

**Workflow Diagrams:**
- `handovers/Reference_docs/giljoai workflow.pdf` (pages 36-38)

---

## Recommended Sub-Agent

**Primary:** `ux-designer` - UI component creation, Vuetify patterns
**Secondary:** `frontend-tester` - Unit test creation, manual testing

---

## Notes for Implementing Agent

1. **DO NOT** modify counter logic in JobsTab - it works correctly
2. **DO NOT** modify database schema - not needed
3. **DO** reuse existing message type definitions from `frontend/src/types/message.ts`
4. **DO** follow Vuetify 3 patterns used elsewhere in codebase
5. **DO** emit WebSocket-compatible events if adding real-time features later
