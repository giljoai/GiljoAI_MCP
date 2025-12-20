# Handover 0366d-2: Frontend Messaging - Agent ID Display

**Status**: Ready for execution
**Estimated Duration**: 2-3 hours
**Dependencies**: 0366b (backend messaging service updated)
**Executor**: TDD-Implementor Agent

---

## Mission

Update 4 frontend messaging components to display `agent_id` (executor UUID) instead of `agent_type` names. This aligns frontend display with the backend dual-model architecture where AgentExecution uses UUIDs for identity.

## Context

- **Backend Changes (0366b)**: MessageService now stores `from_agent_id` and `to_agent_id` (executor UUIDs)
- **Frontend Gap**: Components still reference `from_agent`, `to_agent` (agent_type strings)
- **Goal**: Display executor UUIDs in messaging UI for accurate agent identification

---

## EXPLICIT Scope (4 Files ONLY)

### 1. MessageStream.vue
**Path**: `frontend/src/components/projects/MessageStream.vue`

**Current Behavior**:
- Line 72-73: Displays `{{ formatAgentName(message.to_agent) }}` (agent_type)
- Line 215: Gets agent type from `message.from_agent` or `message.agent_type`

**Required Changes**:
- Display `from_agent_id` instead of `from_agent` in message sender
- Display `to_agent_id` instead of `to_agent` in recipient line (line 72-73)
- Format: Show truncated UUID (first 8 chars) with tooltip for full UUID
- Example: `→ To abc12345...` with tooltip `abc12345-6789-0123-4567-890abcdef123`
- Add `data-testid="message-list"` to `.message-stream__list` (line 35)
- Add `data-testid="message-item"` to `.message-stream__message` (line 36)

**Functions to Update**:
- `formatAgentName()` → `formatAgentId(agentId)` - truncate UUID to 8 chars
- `getAgentType()` → Keep for ChatHeadBadge (still needs agent_type), but add `getAgentId()` for sender display

---

### 2. MessageInput.vue
**Path**: `frontend/src/components/projects/MessageInput.vue`

**Current Behavior**:
- Line 121-124: `recipientOptions` hardcoded to `[{ label: 'Orchestrator', value: 'orchestrator' }, { label: 'Broadcast', value: 'broadcast' }]`
- Dropdown shows agent type names

**Required Changes**:
- **Prop Addition**: Accept `agents` prop (array of agent objects with `agent_id`, `agent_type`, `instance_number`)
- **Dropdown Update**: Show active agents dynamically
  - Format: `"{agent_type} (Instance {n}) - {agent_id:8}..."`
  - Example: `"Orchestrator (Instance 1) - abc12345..."`
  - Keep "Broadcast" option at top
- **Payload Update**: Emit `to_agent_id` instead of `to_agent` in submit event
- Add `data-testid="recipient-select"` to `v-select` (line 30)
- Add `data-testid="message-input"` to `.message-input__textarea` (line 13)

**New Props**:
```vue
agents: {
  type: Array,
  default: () => [],
  // Each agent: { agent_id, agent_type, instance_number }
}
```

**Computed Property**:
```javascript
const recipientOptions = computed(() => {
  const options = [{ label: 'Broadcast', value: 'broadcast' }]

  props.agents.forEach(agent => {
    const label = `${agent.agent_type} (Instance ${agent.instance_number || 1}) - ${agent.agent_id.slice(0, 8)}...`
    options.push({ label, value: agent.agent_id })
  })

  return options
})
```

---

### 3. MessageDetailView.vue
**Path**: `frontend/src/components/projects/MessageDetailView.vue`

**Current Behavior**:
- Line 12: Shows `{{ message.from || 'unknown' }}` (agent_type or user)

**Required Changes**:
- Show `from_agent_id` (full UUID) for agent messages
- Show `to_agent_id` (full UUID) for targeted messages
- Format: Full UUID in monospace font
- Add rows:
  - **From Agent ID**: `{{ message.from_agent_id || 'N/A' }}`
  - **To Agent ID**: `{{ message.to_agent_id || 'Broadcast' }}`
- Add `data-testid="message-detail"` to `.message-detail` (line 1)

**Layout Update**:
```vue
<div class="meta-row">
  <strong>From Agent ID:</strong>
  <code class="text-mono">{{ message.from_agent_id || 'User' }}</code>
</div>
<div class="meta-row">
  <strong>To Agent ID:</strong>
  <code class="text-mono">{{ message.to_agent_id || 'Broadcast' }}</code>
</div>
```

**Style Addition**:
```css
.text-mono {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}
```

---

### 4. MessageAuditModal.vue
**Path**: `frontend/src/components/projects/MessageAuditModal.vue`

**Current Behavior**:
- Line 112: Shows `formatMessageMeta(message)` (timestamp + status)

**Required Changes**:
- Update `formatMessageMeta()` to include truncated `from_agent_id` / `to_agent_id`
- Format: `"[timestamp] from abc12345... → to def67890... (status)"`
- Add tooltip with full UUIDs to each message row

**Function Update**:
```javascript
function formatMessageMeta(message) {
  const fromId = message.from_agent_id
    ? message.from_agent_id.slice(0, 8) + '...'
    : 'user'
  const toId = message.to_agent_id
    ? message.to_agent_id.slice(0, 8) + '...'
    : 'broadcast'
  const status = message.status || 'unknown'
  const timestamp = message.timestamp || message.created_at
  const date = timestamp ? new Date(timestamp) : null
  const timePart = date ? date.toLocaleTimeString() : 'Unknown time'

  return `${timePart} | ${fromId} → ${toId} (${status})`
}
```

---

## NOT In Scope (EXPLICIT)

These files are EXCLUDED from this handover:

- ❌ `JobsTab.vue` - Agent table display (covered in 0366d-1)
- ❌ `AgentTableView.vue` - Status board (covered in 0366d-1)
- ❌ `LaunchTab.vue` - Launch interface (covered in 0366d-3)
- ❌ `OrchestratorLaunchButton.vue` - Launch button (covered in 0366d-3)
- ❌ Backend message service - Already updated in 0366b
- ❌ New messaging features - Only display updates
- ❌ Message threading or grouping - Future enhancement
- ❌ Comprehensive test suites - 1 simple E2E test only

**Do NOT**:
- Add new messaging functionality
- Refactor message state management
- Change WebSocket message handling
- Update message queue logic
- Modify message persistence
- Add message search or filtering
- Implement message reactions or read receipts

---

## Acceptance Criteria

### Functional Requirements
- [ ] MessageStream displays sender `from_agent_id` (truncated with tooltip)
- [ ] MessageStream displays recipient `to_agent_id` (truncated with tooltip)
- [ ] MessageInput dropdown shows agents by `agent_id` with format: `"{type} (Instance {n}) - {id:8}..."`
- [ ] MessageInput emits `to_agent_id` in submit payload
- [ ] MessageDetailView shows full `from_agent_id` and `to_agent_id` UUIDs
- [ ] MessageAuditModal meta includes truncated agent IDs

### Testing Requirements
- [ ] 1 simple E2E test: Send message to specific agent by UUID
  - Test file: `frontend/src/components/projects/__tests__/MessageInput.agent-id.spec.js`
  - Test: Click recipient dropdown → Select agent by UUID → Send message → Verify payload contains `to_agent_id`

### Code Quality
- [ ] All testid attributes added as specified
- [ ] UUID truncation helper function created (if needed)
- [ ] Tooltips show full UUIDs on hover
- [ ] Monospace font for UUIDs in detail views

---

## Implementation Notes

### UUID Truncation Helper
Consider adding to MessageStream.vue:

```javascript
/**
 * Truncate UUID to first 8 characters for display
 * @param {string} uuid - Full UUID
 * @returns {string} Truncated UUID (e.g., "abc12345...")
 */
function truncateUuid(uuid) {
  if (!uuid || typeof uuid !== 'string') return 'unknown'
  return uuid.slice(0, 8) + '...'
}
```

### Tooltip Pattern
Use Vuetify `v-tooltip` for full UUID display:

```vue
<v-tooltip location="bottom">
  <template #activator="{ props }">
    <span v-bind="props">{{ truncateUuid(message.from_agent_id) }}</span>
  </template>
  <span>{{ message.from_agent_id }}</span>
</v-tooltip>
```

### MessageInput Agents Prop
Parent component (JobsTab or MessagePanel) must pass active agents:

```vue
<MessageInput
  :job-id="activeJobId"
  :agents="activeAgents"
  @submit="handleMessageSubmit"
/>
```

Where `activeAgents` is computed from job status:
```javascript
const activeAgents = computed(() => {
  return jobs.value
    .filter(job => job.status !== 'completed')
    .map(job => ({
      agent_id: job.agent_id,
      agent_type: job.agent_type,
      instance_number: job.instance_number
    }))
})
```

---

## Files Modified (Summary)

1. **frontend/src/components/projects/MessageStream.vue** - Display agent IDs in message routing
2. **frontend/src/components/projects/MessageInput.vue** - Target messages by agent ID
3. **frontend/src/components/projects/MessageDetailView.vue** - Show full agent IDs
4. **frontend/src/components/projects/MessageAuditModal.vue** - Include agent IDs in metadata

---

## Rollout Strategy

### Phase 1: Component Updates (1.5 hours)
1. Update MessageStream.vue (30 min)
2. Update MessageInput.vue (40 min)
3. Update MessageDetailView.vue (20 min)

### Phase 2: Modal Updates (30 min)
4. Update MessageAuditModal.vue (30 min)

### Phase 3: Testing (30 min)
5. Write 1 E2E test for MessageInput
6. Manual smoke test: Send message to specific agent

### Phase 4: Verification (30 min)
7. Verify all testid attributes present
8. Verify tooltips show full UUIDs
9. Verify message send payload includes `to_agent_id`

---

## Success Metrics

- **User Experience**: Developers can see exact agent UUIDs in messaging UI
- **Accuracy**: Messages target specific agent instances (not just agent types)
- **Clarity**: Truncated UUIDs with tooltips balance readability and precision
- **Testability**: All interactive elements have data-testid attributes

---

## Related Handovers

- **0366b**: Backend messaging service updated to use agent_id fields
- **0366c**: Backend tools refactored to use agent_id parameters
- **0366d-1**: Frontend agent table updated to display agent_id
- **0366d-3**: Frontend launch interface updated to show agent_id

---

## TDD Approach: LITE Variant

**For frontend/UI work, use TDD-Lite** (not full RED-GREEN-REFACTOR):

1. **Verify current state** - Check component renders without errors
2. **Make changes** - Update component per spec
3. **Test manually** - Verify in browser
4. **Add data-testid** - For future E2E testing
5. **One simple E2E test** - Verify basic functionality

**Why TDD-Lite for frontend?**
- Full TDD is overkill for display-only changes
- Vue components are declarative (less logic to test)
- Manual verification catches visual issues tests miss
- data-testid enables future test expansion

**NOT required:**
- ❌ Writing tests FIRST
- ❌ Comprehensive test suites
- ❌ Unit tests for every component
- ❌ Mocking complex dependencies

---

## Kickoff Prompt

Copy this prompt to start execution:

---

**Mission**: Execute Handover 0366d-2 - Frontend Messaging Agent ID Display

**Context**: Read `handovers/0366d-2_frontend_messaging.md` for complete specification.

**Approach**: TDD-Lite (verify → change → test manually → add data-testid → 1 E2E test)

**Scope**: 4 files only:
1. `frontend/src/components/projects/MessageStream.vue` - Display agent IDs in message sender/recipient
2. `frontend/src/components/projects/MessageInput.vue` - Target messages by agent ID in dropdown
3. `frontend/src/components/projects/MessageDetailView.vue` - Show full agent IDs in detail view
4. `frontend/src/components/projects/MessageAuditModal.vue` - Include agent IDs in message metadata

**NOT in scope**:
- ❌ JobsTab.vue (covered in 0366d-1)
- ❌ AgentTableView.vue (covered in 0366d-1)
- ❌ Launch components (covered in 0366d-3)
- ❌ Backend message service (already done in 0366b)
- ❌ New messaging features
- ❌ Comprehensive test suites

**Acceptance Criteria**: See handover document section "Acceptance Criteria"

**References**:
- Models: `src/giljo_mcp/models/agent_identity.py`
- Memory: `handovers/0366c_context_tools_agent_id_red_phase.md` (Serena)
- Prior work: 0366a (models), 0366b (services), 0366c (backend)

**First Step**: Read the handover file completely, then verify current state of MessageStream.vue component.

---

**End of Handover 0366d-2**
