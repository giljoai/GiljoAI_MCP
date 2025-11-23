# Handover 0243e: Message Center & Tab Activation Fix

**Status**: 🔵 Ready for Implementation
**Priority**: P1 (High - Critical communication + navigation)
**Estimated Effort**: 8-11 hours
**Tool**: CCW (Cloud) for frontend work
**Subagent**: ux-designer (UI/UX specialist)
**Dependencies**: 0243c (dynamic status), 0243d (action buttons)
**Part**: 5 of 6 in Nicepage conversion series

---

## Mission

**Part A**: Implement message center integration with JobsTab (message sending + count display)
**Part B**: Fix tab activation state persistence for Launch/Implement tabs

**Objective**: Enable developer-to-agent communication and fix tab navigation UX to match Nicepage design.

---

## Part A: Message Center Integration

### Visual Reference

**Target** (from Nicepage design):
- Message composer with 3 elements:
  1. Recipient selector buttons ("Orchestrator", "Broadcast")
  2. Message input field (rounded, dark background)
  3. Send button (yellow play icon)

**Message Counts** (in table):
- "Messages Sent" column (messages from developer to agent)
- "Messages Waiting" column (pending messages for agent)
- "Messages Read" column (acknowledged messages by agent)

### Current Implementation

**File**: `frontend/src/components/projects/JobsTab.vue` (lines 96-125)

**Current state**:
- ✅ Message composer UI exists
- ✅ Send button present
- ❌ Message counts NOT displayed (columns empty)
- ❌ WebSocket event handlers missing
- ❌ Styling doesn't match Nicepage design tokens

### Required Implementation

#### 1. Message Composer Styling

**Template** (align to Nicepage tokens):
```vue
<template>
  <div class="message-composer">
    <v-btn
      class="recipient-btn"
      :variant="selectedRecipient === 'orchestrator' ? 'flat' : 'outlined'"
      rounded
      color="yellow-darken-2"
      @click="selectedRecipient = 'orchestrator'"
    >
      Orchestrator
    </v-btn>

    <v-btn
      class="broadcast-btn"
      :variant="selectedRecipient === 'broadcast' ? 'flat' : 'outlined'"
      rounded
      color="yellow-darken-2"
      @click="selectedRecipient = 'broadcast'"
    >
      Broadcast
    </v-btn>

    <v-text-field
      v-model="messageText"
      class="message-input"
      placeholder="Type message..."
      variant="outlined"
      density="compact"
      hide-details
      @keyup.enter="sendMessage"
    />

    <v-btn
      icon="mdi-play"
      class="send-btn"
      color="yellow-darken-2"
      :loading="sending"
      :disabled="!messageText.trim()"
      @click="sendMessage"
    />
  </div>
</template>
```

**Styles** (use design tokens):
```scss
@import '@/styles/design-tokens.scss';

.message-composer {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 16px;
  background: $background-tertiary;
  border-radius: $border-radius-medium;
  margin-bottom: 20px;

  .recipient-btn,
  .broadcast-btn {
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: $button-border-radius-small;  // 6px
    text-transform: none;
    font-size: $font-size-body;
    font-weight: $font-weight-normal;
    padding: 8px 16px;

    &.v-btn--variant-flat {
      background: $text-highlight;
      color: #000;
      font-weight: $font-weight-bold;
    }

    &.v-btn--variant-outlined {
      border-color: rgba(255, 215, 0, 0.4);
      color: rgba(255, 215, 0, 0.7);

      &:hover {
        background: rgba(255, 215, 0, 0.1);
        border-color: rgba(255, 215, 0, 0.6);
      }
    }
  }

  .message-input {
    flex: 1;

    ::v-deep(.v-field) {
      background: rgba(20, 35, 50, 0.8);
      border: 2px solid rgba(255, 255, 255, 0.2);
      border-radius: $border-radius-small;  // 8px

      input {
        color: $text-primary;
        font-size: $font-size-body;
        padding: 8px 12px;

        &::placeholder {
          color: rgba(255, 255, 255, 0.4);
        }
      }

      &:hover {
        border-color: rgba(255, 255, 255, 0.3);
      }

      &.v-field--focused {
        border-color: $text-highlight;
      }
    }
  }

  .send-btn {
    border-radius: 50%;
    width: 40px;
    height: 40px;

    &:disabled {
      opacity: 0.4;
    }
  }
}
```

#### 2. Message Sending Logic

**Script**:
```javascript
import { ref, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

const messageText = ref('')
const selectedRecipient = ref('orchestrator')
const sending = ref(false)
const { showToast } = useToast()

const sendMessage = async () => {
  if (!messageText.value.trim()) {
    showToast('Message cannot be empty', 'warning')
    return
  }

  sending.value = true

  try {
    const payload = {
      to_agent: selectedRecipient.value === 'broadcast' ? 'all' : 'orchestrator',
      message: messageText.value.trim(),
      priority: 'medium'
    }

    await api.post('/api/messages/send', payload)

    showToast('Message sent successfully', 'success')
    messageText.value = ''  // Clear input after successful send

    // Message counts will update via WebSocket event
  } catch (error) {
    console.error('[JobsTab] Send message failed:', error)
    showToast(`Failed to send message: ${error.response?.data?.detail || error.message}`, 'error')
  } finally {
    sending.value = false
  }
}
```

#### 3. Message Count Display

**Template** (update table columns):
```vue
<!-- Messages Sent column -->
<td class="messages-sent-cell text-center">
  <span class="message-count">{{ getMessagesSent(agent) }}</span>
</td>

<!-- Messages Waiting column -->
<td class="messages-waiting-cell text-center">
  <span class="message-count message-waiting">{{ getMessagesWaiting(agent) }}</span>
</td>

<!-- Messages Read column -->
<td class="messages-read-cell text-center">
  <span class="message-count message-read">{{ getMessagesRead(agent) }}</span>
</td>
```

**Script methods**:
```javascript
/**
 * Get count of messages sent from developer to this agent
 */
const getMessagesSent = (agent) => {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(m => m.from === 'developer' || m.direction === 'outbound').length
}

/**
 * Get count of messages waiting to be read by agent
 */
const getMessagesWaiting = (agent) => {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(m => m.status === 'pending' || m.status === 'sent').length
}

/**
 * Get count of messages acknowledged/read by agent
 */
const getMessagesRead = (agent) => {
  if (!agent.messages || !Array.isArray(agent.messages)) return 0
  return agent.messages.filter(m => m.status === 'acknowledged' || m.status === 'read').length
}
```

**Styles for counts**:
```scss
.message-count {
  display: inline-block;
  min-width: 24px;
  padding: 4px 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  color: $text-primary;
  font-size: $font-size-small;
  font-weight: $font-weight-bold;

  &.message-waiting {
    background: rgba(255, 152, 0, 0.2);
    color: #ff9800;
  }

  &.message-read {
    background: rgba(76, 175, 80, 0.2);
    color: #4caf50;
  }
}
```

#### 4. WebSocket Event Handlers

**Subscribe to message events**:
```javascript
import { onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAuth } from '@/composables/useAuth'

const { on, off } = useWebSocket()
const { currentUser } = useAuth()

const currentTenantKey = computed(() => currentUser.value?.tenant_key)

onMounted(() => {
  on('message:sent', handleMessageSent)
  on('message:acknowledged', handleMessageAcknowledged)
  on('message:new', handleNewMessage)
})

onUnmounted(() => {
  off('message:sent', handleMessageSent)
  off('message:acknowledged', handleMessageAcknowledged)
  off('message:new', handleNewMessage)
})

/**
 * Handle message sent event (developer -> agent)
 */
const handleMessageSent = (data) => {
  if (data.tenant_key !== currentTenantKey.value) return

  console.log('[JobsTab] Message sent event:', data)

  // Add message to agent's messages array
  const agent = agents.value.find(a => a.id === data.to_agent || a.agent_id === data.to_agent)
  if (agent) {
    if (!agent.messages) agent.messages = []
    agent.messages.push({
      id: data.message_id,
      from: 'developer',
      direction: 'outbound',
      status: 'sent',
      text: data.message,
      priority: data.priority || 'medium',
      timestamp: data.timestamp || new Date().toISOString()
    })
  }
}

/**
 * Handle message acknowledged event (agent read message)
 */
const handleMessageAcknowledged = (data) => {
  if (data.tenant_key !== currentTenantKey.value) return

  console.log('[JobsTab] Message acknowledged event:', data)

  // Update message status
  const agent = agents.value.find(a => a.id === data.agent_id || a.agent_id === data.agent_id)
  if (agent && agent.messages) {
    const message = agent.messages.find(m => m.id === data.message_id)
    if (message) {
      message.status = 'acknowledged'
    }
  }
}

/**
 * Handle new message event (agent -> developer)
 */
const handleNewMessage = (data) => {
  if (data.tenant_key !== currentTenantKey.value) return

  console.log('[JobsTab] New message event:', data)

  // Add message to agent's messages array
  const agent = agents.value.find(a => a.id === data.from_agent || a.agent_id === data.from_agent)
  if (agent) {
    if (!agent.messages) agent.messages = []
    agent.messages.push({
      id: data.message_id,
      from: 'agent',
      direction: 'inbound',
      status: 'pending',
      text: data.message,
      priority: data.priority || 'medium',
      timestamp: data.timestamp || new Date().toISOString()
    })
  }
}
```

---

## Part B: Tab Activation Fix

### Problem Statement

**Issue**: Clicking "Implement" tab does not activate it - "Launch" tab stays highlighted.

**Root Cause**: Tab activation state not managed reactively with Vuetify's v-tabs component.

### Required Implementation

**File**: `frontend/src/components/projects/ProjectTabs.vue` (or equivalent parent component)

#### Vuetify v-tabs Integration

**Template**:
```vue
<template>
  <div class="project-tabs-container">
    <v-tabs v-model="activeTab" class="project-tabs" bg-color="transparent">
      <v-tab value="launch" class="tab-link">
        <v-icon start>mdi-rocket-launch</v-icon>
        Launch
      </v-tab>

      <v-tab value="implement" class="tab-link">
        <v-icon start>mdi-code-braces</v-icon>
        Implement
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab" class="tab-content">
      <v-window-item value="launch">
        <LaunchTab :project="currentProject" />
      </v-window-item>

      <v-window-item value="implement">
        <JobsTab :project="currentProject" :agents="agents" />
      </v-window-item>
    </v-window>
  </div>
</template>
```

#### Script

```javascript
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LaunchTab from '@/components/projects/LaunchTab.vue'
import JobsTab from '@/components/projects/JobsTab.vue'

const activeTab = ref('launch')
const route = useRoute()
const router = useRouter()

// Initialize from URL query param (optional - enables deep linking)
if (route.query.tab && ['launch', 'implement'].includes(route.query.tab)) {
  activeTab.value = route.query.tab
}

// Update URL when tab changes (optional - enables browser back/forward)
watch(activeTab, (newTab) => {
  if (route.query.tab !== newTab) {
    router.replace({
      query: { ...route.query, tab: newTab },
      hash: route.hash
    })
  }
})
```

#### Styles

```scss
@import '@/styles/design-tokens.scss';

.project-tabs-container {
  display: flex;
  flex-direction: column;
  height: 100%;

  .project-tabs {
    border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;

    ::v-deep(.v-tab) {
      border: 2px solid rgba(255, 255, 255, 0.2);
      border-bottom: none;
      border-radius: 10px 10px 0 0;
      color: rgba(255, 255, 255, 0.5);
      text-transform: none;
      font-weight: $font-weight-bold;
      font-size: $font-size-body;
      padding: 12px 24px;
      margin-right: 4px;
      background: rgba(20, 35, 50, 0.3);
      transition: all 0.3s ease;

      &.v-tab--selected {
        border-color: $text-highlight;
        color: $text-highlight;
        background: rgba(255, 215, 0, 0.1);

        .v-icon {
          color: $text-highlight;
        }
      }

      &:hover:not(.v-tab--selected) {
        color: rgba(255, 215, 0, 0.7);
        border-color: rgba(255, 215, 0, 0.3);
        background: rgba(255, 215, 0, 0.05);
      }

      .v-icon {
        color: rgba(255, 255, 255, 0.5);
        margin-right: 8px;
        font-size: 20px;
      }
    }
  }

  .tab-content {
    flex: 1;
    overflow-y: auto;

    ::v-deep(.v-window-item) {
      height: 100%;
    }
  }
}
```

---

## TDD Workflow

### RED: Write Failing Tests

**File**: `tests/unit/JobsTab-messages.spec.js`

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import JobsTab from '@/components/projects/JobsTab.vue'
import api from '@/services/api'
import { useWebSocket } from '@/composables/useWebSocket'

vi.mock('@/services/api')
vi.mock('@/composables/useWebSocket')
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

const mockProject = {
  id: 'project-uuid',
  name: 'Test Project',
  tenant_key: 'test-tenant'
}

const mockAgent = {
  id: 'agent-uuid',
  agent_name: 'Test Agent',
  agent_type: 'implementer',
  status: 'active',
  messages: []
}

describe('JobsTab message center (Phase 5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Message Composer', () => {
    it('renders message composer with all elements', () => {
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      expect(wrapper.find('.message-composer').exists()).toBe(true)
      expect(wrapper.find('.recipient-btn').exists()).toBe(true)
      expect(wrapper.find('.broadcast-btn').exists()).toBe(true)
      expect(wrapper.find('.message-input').exists()).toBe(true)
      expect(wrapper.find('.send-btn').exists()).toBe(true)
    })

    it('send button is disabled when message is empty', () => {
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      expect(wrapper.find('.send-btn').attributes('disabled')).toBeDefined()
    })

    it('send button is enabled when message has text', async () => {
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      await wrapper.find('.message-input input').setValue('Test message')
      expect(wrapper.find('.send-btn').attributes('disabled')).toBeUndefined()
    })
  })

  describe('Message Sending', () => {
    it('sends message when send button clicked', async () => {
      const mockApi = vi.spyOn(api, 'post').mockResolvedValue({ data: { success: true } })
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      await wrapper.find('.message-input input').setValue('Test message')
      await wrapper.find('.send-btn').trigger('click')

      expect(mockApi).toHaveBeenCalledWith('/api/messages/send', {
        to_agent: 'orchestrator',
        message: 'Test message',
        priority: 'medium'
      })
    })

    it('sends message to broadcast when broadcast selected', async () => {
      const mockApi = vi.spyOn(api, 'post').mockResolvedValue({ data: { success: true } })
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      await wrapper.find('.broadcast-btn').trigger('click')
      await wrapper.find('.message-input input').setValue('Broadcast message')
      await wrapper.find('.send-btn').trigger('click')

      expect(mockApi).toHaveBeenCalledWith('/api/messages/send', {
        to_agent: 'all',
        message: 'Broadcast message',
        priority: 'medium'
      })
    })

    it('clears input after successful send', async () => {
      vi.spyOn(api, 'post').mockResolvedValue({ data: { success: true } })
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      await wrapper.find('.message-input input').setValue('Test message')
      await wrapper.find('.send-btn').trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('.message-input input').element.value).toBe('')
    })

    it('shows error toast on API failure', async () => {
      vi.spyOn(api, 'post').mockRejectedValue(new Error('Network error'))
      const { showToast } = useToast()
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      await wrapper.find('.message-input input').setValue('Test message')
      await wrapper.find('.send-btn').trigger('click')
      await wrapper.vm.$nextTick()

      expect(showToast).toHaveBeenCalledWith(
        expect.stringContaining('Failed to send message'),
        'error'
      )
    })
  })

  describe('Message Counts', () => {
    it('displays message counts from agent data', () => {
      const agentWithMessages = {
        ...mockAgent,
        messages: [
          { from: 'developer', status: 'sent' },
          { from: 'developer', status: 'acknowledged' },
          { from: 'agent', status: 'pending' },
          { from: 'agent', status: 'read' }
        ]
      }
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [agentWithMessages] }
      })

      expect(wrapper.find('.messages-sent-cell').text()).toBe('2')
      expect(wrapper.find('.messages-waiting-cell').text()).toBe('1')
      expect(wrapper.find('.messages-read-cell').text()).toBe('1')
    })

    it('displays 0 when agent has no messages', () => {
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })

      expect(wrapper.find('.messages-sent-cell').text()).toBe('0')
      expect(wrapper.find('.messages-waiting-cell').text()).toBe('0')
      expect(wrapper.find('.messages-read-cell').text()).toBe('0')
    })
  })

  describe('WebSocket Events', () => {
    it('updates message counts when message:sent event received', async () => {
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })
      const { emit } = useWebSocket()

      emit('message:sent', {
        tenant_key: 'test-tenant',
        to_agent: 'agent-uuid',
        message: 'Test message',
        message_id: 'msg-uuid',
        timestamp: new Date().toISOString()
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.messages-sent-cell').text()).toBe('1')
    })

    it('updates message status when message:acknowledged event received', async () => {
      const agentWithMessage = {
        ...mockAgent,
        messages: [
          { id: 'msg-uuid', from: 'developer', status: 'sent' }
        ]
      }
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [agentWithMessage] }
      })
      const { emit } = useWebSocket()

      emit('message:acknowledged', {
        tenant_key: 'test-tenant',
        agent_id: 'agent-uuid',
        message_id: 'msg-uuid'
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.messages-read-cell').text()).toBe('1')
    })

    it('ignores events from different tenant', async () => {
      const wrapper = mount(JobsTab, {
        props: { project: mockProject, agents: [mockAgent] }
      })
      const { emit } = useWebSocket()

      emit('message:sent', {
        tenant_key: 'other-tenant',
        to_agent: 'agent-uuid',
        message: 'Test message'
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.messages-sent-cell').text()).toBe('0')
    })
  })
})
```

**File**: `tests/unit/ProjectTabs.spec.js`

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

const mockProject = {
  id: 'project-uuid',
  name: 'Test Project',
  tenant_key: 'test-tenant'
}

const mockAgents = []

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } }
  ]
})

describe('ProjectTabs tab activation (Phase 6)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('activates Launch tab by default', () => {
    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    expect(wrapper.vm.activeTab).toBe('launch')
    expect(wrapper.find('.v-tab--selected').text()).toContain('Launch')
  })

  it('activates Implement tab when clicked', async () => {
    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    const implementTab = wrapper.findAll('.v-tab')[1]
    await implementTab.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.activeTab).toBe('implement')
    expect(wrapper.find('.v-tab--selected').text()).toContain('Implement')
  })

  it('persists tab state across rerenders', async () => {
    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    await wrapper.findAll('.v-tab')[1].trigger('click')
    await wrapper.vm.$forceUpdate()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.activeTab).toBe('implement')
    expect(wrapper.find('.v-tab--selected').text()).toContain('Implement')
  })

  it('initializes from URL query param', async () => {
    await router.push('/?tab=implement')

    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    expect(wrapper.vm.activeTab).toBe('implement')
  })

  it('updates URL when tab changes', async () => {
    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    await wrapper.findAll('.v-tab')[1].trigger('click')
    await wrapper.vm.$nextTick()

    expect(router.currentRoute.value.query.tab).toBe('implement')
  })

  it('shows LaunchTab content when Launch tab active', () => {
    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    expect(wrapper.findComponent({ name: 'LaunchTab' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'JobsTab' }).exists()).toBe(false)
  })

  it('shows JobsTab content when Implement tab active', async () => {
    const wrapper = mount(ProjectTabs, {
      props: { project: mockProject, agents: mockAgents },
      global: { plugins: [router] }
    })

    await wrapper.findAll('.v-tab')[1].trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent({ name: 'LaunchTab' }).exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'JobsTab' }).exists()).toBe(true)
  })
})
```

### GREEN: Implement Minimum Code

**Tasks**:
1. Update message composer styling with design tokens
2. Implement sendMessage method with API call
3. Add message count display methods
4. Add WebSocket event handlers (message:sent, message:acknowledged, message:new)
5. Replace custom tabs with Vuetify v-tabs and v-window
6. Add reactive activeTab state with URL sync
7. Run tests and verify all pass

### REFACTOR: Polish Code

**Tasks**:
1. Extract message logic to composable (`useMessages.js`) for reusability
2. Add comprehensive error handling for API failures
3. Add loading states and visual feedback
4. Clean up unused code and console logs
5. Add JSDoc comments for all public methods
6. Optimize WebSocket event handlers (debounce if needed)

---

## API Endpoints Reference

**Message Sending**:
```
POST /api/messages/send
Content-Type: application/json
Authorization: Bearer <token>

{
  "to_agent": "orchestrator" | "all",
  "message": "string",
  "priority": "low" | "medium" | "high" | "critical"
}

Response:
{
  "success": true,
  "message_id": "uuid",
  "timestamp": "2025-11-23T10:00:00Z"
}
```

**WebSocket Events**:
```javascript
// Sent when developer sends message
{
  event: 'message:sent',
  data: {
    tenant_key: 'uuid',
    to_agent: 'uuid',
    message: 'string',
    message_id: 'uuid',
    priority: 'medium',
    timestamp: '2025-11-23T10:00:00Z'
  }
}

// Sent when agent acknowledges message
{
  event: 'message:acknowledged',
  data: {
    tenant_key: 'uuid',
    agent_id: 'uuid',
    message_id: 'uuid',
    timestamp: '2025-11-23T10:00:00Z'
  }
}

// Sent when agent sends message to developer
{
  event: 'message:new',
  data: {
    tenant_key: 'uuid',
    from_agent: 'uuid',
    message: 'string',
    message_id: 'uuid',
    priority: 'medium',
    timestamp: '2025-11-23T10:00:00Z'
  }
}
```

---

## Design Tokens Reference

**Colors**:
- `$text-highlight`: #ffd700 (yellow for active states)
- `$text-primary`: rgba(255, 255, 255, 0.9)
- `$background-tertiary`: rgba(20, 35, 50, 0.6)

**Border Radius**:
- `$border-radius-small`: 8px (inputs)
- `$border-radius-medium`: 12px (containers)
- `$button-border-radius-small`: 6px (buttons)

**Typography**:
- `$font-size-body`: 14px
- `$font-size-small`: 12px
- `$font-weight-normal`: 400
- `$font-weight-bold`: 600

**Spacing**:
- Gap between elements: 12px
- Padding for containers: 16px
- Icon margin: 8px

---

## Deliverables

**Files to Modify**:
- ✅ `frontend/src/components/projects/JobsTab.vue` (message center integration)
- ✅ `frontend/src/components/projects/ProjectTabs.vue` (tab activation fix)

**Files to Create**:
- ✅ `tests/unit/JobsTab-messages.spec.js` (message center tests)
- ✅ `tests/unit/ProjectTabs.spec.js` (tab activation tests)

**Optional**:
- `frontend/src/composables/useMessages.js` (if refactoring message logic)

**Success Criteria**:
- [ ] Message composer styled to match Nicepage design tokens
- [ ] Send button works (API call + success/error toast)
- [ ] Message counts display correctly (Sent, Waiting, Read)
- [ ] WebSocket events update counts in real-time
- [ ] Implement tab activates when clicked
- [ ] Tab state persists across rerenders and page refreshes (URL sync)
- [ ] Test coverage: >80% for both components
- [ ] No console errors or warnings
- [ ] Visual QA matches Nicepage screenshot

---

## Estimated Timeline

**Total**: 8-11 hours

**Breakdown**:
- Message composer styling: 2 hours
- Message sending logic + API integration: 2 hours
- Message count display + methods: 2 hours
- WebSocket event handlers: 2 hours
- Tab activation fix (v-tabs + v-window): 1 hour
- Test writing + validation: 2-3 hours
- Visual QA + polish: 1 hour

---

## Agent Instructions

**You are a ux-designer agent working on critical communication and navigation features.**

### Part A - Message Center Implementation (6-8 hours)

**TDD Approach**:
1. Write failing tests for message sending (API calls, toast notifications)
2. Write failing tests for message counts (Sent, Waiting, Read)
3. Write failing tests for WebSocket events (message:sent, message:acknowledged)

**Implementation**:
1. Update message composer template with design tokens
2. Implement sendMessage method with API integration
3. Add message count display methods
4. Add WebSocket event handlers for real-time updates
5. Run tests until all pass

**Visual QA**:
- [ ] Message composer matches Nicepage (rounded buttons, dark input, yellow play icon)
- [ ] Recipient selector works (Orchestrator/Broadcast toggle)
- [ ] Send button disabled when input empty
- [ ] Success/error toasts display correctly
- [ ] Message counts update in real-time via WebSocket

### Part B - Tab Activation Fix (2-3 hours)

**TDD Approach**:
1. Write failing tests for tab activation (default Launch, click Implement)
2. Write failing tests for tab state persistence
3. Write failing tests for URL sync (optional)

**Implementation**:
1. Replace custom tabs with Vuetify v-tabs and v-window
2. Add reactive activeTab state
3. Add URL query param sync (optional but recommended)
4. Run tests until all pass

**Visual QA**:
- [ ] Launch tab active by default
- [ ] Implement tab activates when clicked
- [ ] Tab state persists across rerenders
- [ ] Tab styling matches Nicepage (yellow highlight, rounded top corners)
- [ ] URL updates when tab changes (optional)

### Reporting Back

**Required**:
1. Test coverage % for both components
2. Visual QA checklist completion status
3. Any blockers or questions
4. Screenshots showing before/after (optional)

**Example Report**:
```
✅ Part A (Message Center) - Complete
- Test coverage: 85% (JobsTab-messages.spec.js)
- API integration working
- WebSocket events updating counts in real-time
- Visual QA: Matches Nicepage design

✅ Part B (Tab Activation) - Complete
- Test coverage: 90% (ProjectTabs.spec.js)
- v-tabs integration working
- URL sync enabled
- Visual QA: Tab activation working correctly

⚠️ Minor Issue: WebSocket reconnection after page refresh
- Workaround: Manual refresh updates counts
- Suggest adding reconnection logic in useWebSocket composable
```

---

## Related Documentation

**Design Tokens**: `frontend/src/styles/design-tokens.scss`
**WebSocket Composable**: `frontend/src/composables/useWebSocket.js`
**API Service**: `frontend/src/services/api.js`
**Toast Composable**: `frontend/src/composables/useToast.js`

**Previous Handovers**:
- 0243c (Dynamic Status) - Status chip implementation
- 0243d (Action Buttons) - Action icons implementation

**Next Handover**:
- 0243f (Final Polish) - Overall visual QA and cleanup

---

## Notes

**Testing**: Use Vitest for unit tests, Vue Test Utils for component testing.
**Mocking**: Mock API calls, WebSocket events, and composables for isolated testing.
**Visual QA**: Compare with Nicepage screenshot in `handovers/Nicepagezip/` folder.
**Cross-Platform**: All code must work on Windows, macOS, and Linux.
**Documentation**: Update component API docs if creating reusable composables.

**End of Handover 0243e**
