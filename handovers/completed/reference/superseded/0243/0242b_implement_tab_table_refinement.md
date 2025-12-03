# Handover 0242b: Implement Tab Table Refinement

**Status**: 🟡 Pending
**Priority**: P1 (High)
**Estimated Effort**: 4-6 hours
**Tool**: CCW (Cloud) - Pure Vue/CSS refinements
**Subagent**: tdd-implementor (test-driven development)
**Dependencies**: ✅ 0242a must be complete first

---

## Executive Summary

Refine `JobsTab.vue` (Implement Tab) to pixel-perfect match the Nicepage design specification (`IMplement tab.jpg` screenshot). This is an **incremental refinement**, NOT a rewrite.

**Critical Change**: Replace hardcoded "Waiting." text with dynamic `{{ agent.status }}` binding.

**Focus Areas**:
1. Dynamic status rendering (replace hardcoded "Waiting.")
2. Table column width proportions (match screenshot exactly)
3. Action icon colors (Play/Folder yellow, Info white)
4. Table borders and spacing
5. Claude toggle indicator styling

**What NOT to Touch**:
- `<script>` section logic (WebSocket handlers, message queue logic)
- Agent tracking and monitoring
- Message composer functionality

---

## Reference Materials

**Primary Screenshot**: `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\IMplement tab.jpg`
**Nicepage HTML**: `F:\Nicepage\MCP Server\index.html`
**Current Implementation**: `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue`
**Archived Handover**: `F:\GiljoAI_MCP\handovers\completed\0241_emergency_gui_fix_match_screenshots-C.md`

---

## Detailed Tasks

### Task 1: Dynamic Status Rendering (1.5 hours) ⚠️ CRITICAL

**Current State**: Status column shows hardcoded "Waiting." text.

**Problem**: Agent status never updates because it's hardcoded, not bound to reactive data.

**Required Change**:

```vue
<!-- ❌ BEFORE (0241 - hardcoded): -->
<td class="status-cell">Waiting.</td>

<!-- ✅ AFTER (0242b - dynamic): -->
<td class="status-cell">{{ agent.status || 'Waiting...' }}</td>
```

**Full Template Example**:
```vue
<template>
  <table class="agents-table">
    <thead>
      <tr>
        <th>Agent Type</th>
        <th>Agent ID</th>
        <th>Agent Status</th>
        <th>Job Read</th>
        <th>Job Acknowledged</th>
        <th>Messages Sent</th>
        <th>Messages Waiting</th>
        <th>Messages Read</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="agent in agents" :key="agent.id">
        <!-- Agent Type Column -->
        <td class="agent-type-cell">
          <v-avatar size="32" :color="getAgentColor(agent.type)">
            {{ getAgentInitials(agent.type) }}
          </v-avatar>
          <span class="agent-name">{{ agent.type }}</span>
        </td>

        <!-- Agent ID Column -->
        <td class="agent-id-cell">{{ agent.id }}</td>

        <!-- ⚠️ CRITICAL: Dynamic Status Column -->
        <td class="status-cell">
          {{ agent.status || 'Waiting...' }}
        </td>

        <!-- Job Read Column -->
        <td class="job-read-cell">
          <v-icon v-if="agent.job_read" size="16" color="green">
            mdi-check
          </v-icon>
        </td>

        <!-- Job Acknowledged Column -->
        <td class="job-ack-cell">
          <v-icon v-if="agent.job_acknowledged" size="16" color="green">
            mdi-check
          </v-icon>
        </td>

        <!-- Messages Sent Column -->
        <td class="messages-sent-cell">{{ agent.messages_sent || 0 }}</td>

        <!-- Messages Waiting Column -->
        <td class="messages-waiting-cell">{{ agent.messages_waiting || 0 }}</td>

        <!-- Messages Read Column -->
        <td class="messages-read-cell">{{ agent.messages_read || 0 }}</td>

        <!-- Actions Column -->
        <td class="actions-cell">
          <v-icon size="20" color="yellow-darken-2">mdi-play</v-icon>
          <v-icon size="20" color="yellow-darken-2">mdi-folder</v-icon>
          <v-icon size="20" color="white">mdi-information</v-icon>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.status-cell {
  color: #ffd700;      /* Yellow text */
  font-style: italic;  /* Italic style */
  font-size: 14px;
}
</style>
```

**Status Values from Backend**:
- `"Waiting..."` - Agent created, waiting for orchestrator
- `"Working..."` - Agent actively processing
- `"Complete"` - Agent finished successfully
- `"Error"` - Agent encountered error

**WebSocket Event** (already implemented in `<script>`, do not modify):
```javascript
// Preserved from 0241 - DO NOT MODIFY
socket.on('agent:updated', (agentData) => {
  const index = agents.value.findIndex(a => a.id === agentData.id)
  if (index !== -1) {
    agents.value[index] = { ...agents.value[index], ...agentData }
  }
})
```

**Verification**:
- Status text updates when `agent:updated` WebSocket event fires
- Yellow italic styling applied
- Fallback to "Waiting..." if status undefined

---

### Task 2: Table Column Width Adjustments (1.5 hours)

**Current State**: Column widths may not match screenshot proportions.

**Required Column Proportions** (59 total units):
| Column | Width Units | Purpose |
|--------|-------------|---------|
| Agent Type | 11 | Avatar + name |
| Agent ID | 12 | Full UUID (grey monospace) |
| Agent Status | 9 | Yellow italic text |
| Job Read | 3 | Checkmark or empty |
| Job Acknowledged | 3 | Checkmark or empty |
| Messages Sent | 4 | Numeric count |
| Messages Waiting | 4 | Numeric count |
| Messages Read | 4 | Numeric count |
| Actions | 9 | 3 icons (play, folder, info) |

**CSS Grid Implementation**:
```vue
<style scoped>
.agents-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

/* Column widths using CSS Grid approach */
.agents-table thead tr,
.agents-table tbody tr {
  display: grid;
  grid-template-columns:
    11fr   /* Agent Type */
    12fr   /* Agent ID */
    9fr    /* Agent Status */
    3fr    /* Job Read */
    3fr    /* Job Acknowledged */
    4fr    /* Messages Sent */
    4fr    /* Messages Waiting */
    4fr    /* Messages Read */
    9fr;   /* Actions */
  gap: 8px;
  padding: 16px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.agents-table thead tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 500;
  color: #ccc;
}

/* Individual column styling */
.agent-type-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-id-cell {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-cell {
  color: #ffd700;
  font-style: italic;
}

.job-read-cell,
.job-ack-cell {
  text-align: center;
}

.messages-sent-cell,
.messages-waiting-cell,
.messages-read-cell {
  text-align: center;
  font-variant-numeric: tabular-nums;  /* Mono-width numbers */
}

.actions-cell {
  display: flex;
  gap: 8px;
  justify-content: center;
}
</style>
```

**Alternative: Table Layout Implementation** (if CSS Grid causes issues):
```vue
<style scoped>
.agents-table {
  width: 100%;
  table-layout: fixed;  /* Fixed layout for precise widths */
}

.agents-table thead th:nth-child(1) { width: 18.64%; }  /* 11/59 */
.agents-table thead th:nth-child(2) { width: 20.34%; }  /* 12/59 */
.agents-table thead th:nth-child(3) { width: 15.25%; }  /* 9/59 */
.agents-table thead th:nth-child(4) { width: 5.08%; }   /* 3/59 */
.agents-table thead th:nth-child(5) { width: 5.08%; }   /* 3/59 */
.agents-table thead th:nth-child(6) { width: 6.78%; }   /* 4/59 */
.agents-table thead th:nth-child(7) { width: 6.78%; }   /* 4/59 */
.agents-table thead th:nth-child(8) { width: 6.78%; }   /* 4/59 */
.agents-table thead th:nth-child(9) { width: 15.25%; }  /* 9/59 */
</style>
```

**Verification**:
- Measure column widths in DevTools
- Agent Type: ~19% of table width
- Agent ID: ~20% of table width
- Agent Status: ~15% of table width
- Job columns: ~5% each
- Message columns: ~7% each
- Actions: ~15% of table width

---

### Task 3: Action Icon Color Updates (1 hour)

**Current State**: All action icons may be same color.

**Required Changes**:
```vue
<template>
  <td class="actions-cell">
    <!-- Play icon: Yellow -->
    <v-icon
      size="20"
      color="yellow-darken-2"
      :class="{ 'faded-icon': usingClaudeCodeSubagents }"
      @click="handlePlayAgent(agent.id)"
    >
      mdi-play
    </v-icon>

    <!-- Folder/Copy icon: Yellow -->
    <v-icon
      size="20"
      color="yellow-darken-2"
      @click="handleCopyAgentPrompt(agent.id)"
    >
      mdi-folder
    </v-icon>

    <!-- Info icon: White (NOT yellow) -->
    <v-icon
      size="20"
      color="white"
      @click="handleShowAgentInfo(agent.id)"
    >
      mdi-information
    </v-icon>
  </td>
</template>

<style scoped>
.actions-cell {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

/* Faded when Claude Code CLI mode active */
.faded-icon {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
```

**Icon Behavior**:
- **Play icon**: Clickable, triggers agent execution (faded in Claude CLI mode)
- **Folder icon**: Clickable, copies agent prompt to clipboard
- **Info icon**: Clickable, shows agent details modal

**Verification**:
- Play icon: `color="yellow-darken-2"` (Vuetify color)
- Folder icon: `color="yellow-darken-2"`
- Info icon: `color="white"` (NOT yellow)
- Play icon faded (`opacity: 0.4`) when `usingClaudeCodeSubagents` is true

---

### Task 4: Table Border and Spacing (0.5 hour)

**Current State**: Table borders may not match screenshot.

**Required Changes**:
```vue
<template>
  <div class="table-container">
    <table class="agents-table">
      <!-- Table content -->
    </table>
  </div>
</template>

<style scoped>
.table-container {
  border: 2px solid rgba(255, 255, 255, 0.2);  /* Outer border */
  border-radius: 16px;                         /* Rounded corners */
  overflow: hidden;                            /* Clips content to radius */
  background: rgba(14, 28, 45, 0.3);          /* Subtle background */
}

.agents-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

/* Header row border */
.agents-table thead tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);  /* Stronger header border */
}

/* Body row borders */
.agents-table tbody tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);  /* Subtle row borders */
}

.agents-table tbody tr:last-child {
  border-bottom: none;  /* No border on last row */
}

/* Cell padding */
.agents-table th,
.agents-table td {
  padding: 16px 12px;  /* Vertical 16px, Horizontal 12px */
}
</style>
```

**Verification**:
- Table container: 2px solid rgba border, 16px radius
- Header border: 1px solid rgba (stronger than body)
- Row borders: 1px solid rgba (subtle)
- Cell padding: 16px vertical, 12px horizontal

---

### Task 5: Claude Toggle Styling (0.5 hour)

**Current State**: Toggle indicator may not match screenshot.

**Required Changes**:
```vue
<template>
  <div class="claude-toggle-section">
    <!-- Toggle label -->
    <div class="toggle-label">Claude Subagents</div>

    <!-- Toggle indicator (visual only, not interactive) -->
    <div class="toggle-indicator">
      <div
        class="toggle-dot"
        :class="{ 'toggle-on': usingClaudeCodeSubagents }"
      ></div>
    </div>

    <!-- Status text -->
    <div class="toggle-status">
      {{ usingClaudeCodeSubagents ? 'ON' : 'OFF' }}
    </div>
  </div>
</template>

<style scoped>
.claude-toggle-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.toggle-label {
  font-size: 14px;
  color: #ccc;
}

.toggle-indicator {
  width: 40px;
  height: 24px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  position: relative;
  transition: background 0.3s ease;
}

.toggle-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #666;  /* Grey when OFF */
  position: absolute;
  top: 4px;
  left: 4px;
  transition: all 0.3s ease;
}

.toggle-dot.toggle-on {
  background: #00ff00;  /* Green when ON */
  left: 20px;           /* Moves to right */
}

.toggle-status {
  font-size: 12px;
  color: #999;
  font-weight: 500;
}
</style>
```

**Verification**:
- Toggle dot: 16px circle
- Grey (`#666`) when OFF, green (`#00ff00`) when ON
- Dot moves left/right with smooth transition
- Label: "Claude Subagents", grey text

---

### Task 6: Testing (1 hour)

Create comprehensive test suite: `frontend/tests/unit/components/projects/JobsTab.0242b.spec.js`

**Test Structure** (49 tests total):

```javascript
import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import JobsTab from '@/components/projects/JobsTab.vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({ components, directives })

describe('JobsTab.vue - 0242b Table Refinement', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(JobsTab, {
      global: {
        plugins: [vuetify],
      },
      props: {
        projectId: 'test-project-123',
      },
    })
  })

  describe('Dynamic Status Rendering', () => {
    it('should render dynamic status from agent data', async () => {
      await wrapper.setData({
        agents: [
          { id: 'agent-1', type: 'Orchestrator', status: 'Working...' },
        ],
      })
      const statusCell = wrapper.find('.status-cell')
      expect(statusCell.text()).toBe('Working...')
    })

    it('should show "Waiting..." when status undefined', async () => {
      await wrapper.setData({
        agents: [{ id: 'agent-1', type: 'Orchestrator', status: undefined }],
      })
      const statusCell = wrapper.find('.status-cell')
      expect(statusCell.text()).toBe('Waiting...')
    })

    it('should render "Complete" status', async () => {
      await wrapper.setData({
        agents: [{ id: 'agent-1', type: 'Implementor', status: 'Complete' }],
      })
      const statusCell = wrapper.find('.status-cell')
      expect(statusCell.text()).toBe('Complete')
    })

    it('should render "Error" status', async () => {
      await wrapper.setData({
        agents: [{ id: 'agent-1', type: 'Tester', status: 'Error' }],
      })
      const statusCell = wrapper.find('.status-cell')
      expect(statusCell.text()).toBe('Error')
    })

    it('should have yellow italic styling', () => {
      const statusCell = wrapper.find('.status-cell')
      const styles = window.getComputedStyle(statusCell.element)
      expect(styles.color).toContain('255, 215, 0') // #ffd700 in rgb
      expect(styles.fontStyle).toBe('italic')
    })

    it('should update status on agent:updated event', async () => {
      const socket = wrapper.vm.$socket
      await wrapper.setData({
        agents: [{ id: 'agent-1', type: 'Orchestrator', status: 'Waiting...' }],
      })

      socket.emit('agent:updated', { id: 'agent-1', status: 'Working...' })
      await wrapper.vm.$nextTick()

      const statusCell = wrapper.find('.status-cell')
      expect(statusCell.text()).toBe('Working...')
    })
  })

  describe('Table Column Width Adjustments', () => {
    it('should render 9 column headers', () => {
      const headers = wrapper.findAll('.agents-table thead th')
      expect(headers).toHaveLength(9)
    })

    it('should have correct header labels', () => {
      const headers = wrapper.findAll('.agents-table thead th')
      expect(headers[0].text()).toBe('Agent Type')
      expect(headers[1].text()).toBe('Agent ID')
      expect(headers[2].text()).toBe('Agent Status')
      expect(headers[3].text()).toBe('Job Read')
      expect(headers[4].text()).toBe('Job Acknowledged')
      expect(headers[5].text()).toBe('Messages Sent')
      expect(headers[6].text()).toBe('Messages Waiting')
      expect(headers[7].text()).toBe('Messages Read')
      expect(headers[8].text()).toBe('Actions')
    })

    it('should use CSS Grid for column layout', () => {
      const row = wrapper.find('.agents-table thead tr')
      const styles = window.getComputedStyle(row.element)
      expect(styles.display).toBe('grid')
    })

    it('should have correct grid template columns', () => {
      const row = wrapper.find('.agents-table thead tr')
      const styles = window.getComputedStyle(row.element)
      expect(styles.gridTemplateColumns).toContain('11fr 12fr 9fr 3fr 3fr 4fr 4fr 4fr 9fr')
    })

    it('should have 8px gap between columns', () => {
      const row = wrapper.find('.agents-table thead tr')
      const styles = window.getComputedStyle(row.element)
      expect(styles.gap).toBe('8px')
    })

    it('should show full UUID in Agent ID column', async () => {
      const testUuid = '123e4567-e89b-12d3-a456-426614174000'
      await wrapper.setData({
        agents: [{ id: testUuid, type: 'Orchestrator' }],
      })
      const idCell = wrapper.find('.agent-id-cell')
      expect(idCell.text()).toBe(testUuid)
    })

    it('should use monospace font for Agent ID', () => {
      const idCell = wrapper.find('.agent-id-cell')
      const styles = window.getComputedStyle(idCell.element)
      expect(styles.fontFamily).toContain('Courier New')
    })

    it('should center-align Job Read column', () => {
      const cell = wrapper.find('.job-read-cell')
      const styles = window.getComputedStyle(cell.element)
      expect(styles.textAlign).toBe('center')
    })

    it('should center-align Job Acknowledged column', () => {
      const cell = wrapper.find('.job-ack-cell')
      const styles = window.getComputedStyle(cell.element)
      expect(styles.textAlign).toBe('center')
    })

    it('should center-align message count columns', () => {
      const sentCell = wrapper.find('.messages-sent-cell')
      const waitingCell = wrapper.find('.messages-waiting-cell')
      const readCell = wrapper.find('.messages-read-cell')

      const sentStyles = window.getComputedStyle(sentCell.element)
      const waitingStyles = window.getComputedStyle(waitingCell.element)
      const readStyles = window.getComputedStyle(readCell.element)

      expect(sentStyles.textAlign).toBe('center')
      expect(waitingStyles.textAlign).toBe('center')
      expect(readStyles.textAlign).toBe('center')
    })
  })

  describe('Action Icon Color Updates', () => {
    it('should render three action icons', () => {
      const icons = wrapper.find('.actions-cell').findAll('v-icon')
      expect(icons).toHaveLength(3)
    })

    it('should render Play icon with yellow color', () => {
      const playIcon = wrapper.find('v-icon[icon="mdi-play"]')
      expect(playIcon.exists()).toBe(true)
      expect(playIcon.attributes('color')).toBe('yellow-darken-2')
    })

    it('should render Folder icon with yellow color', () => {
      const folderIcon = wrapper.find('v-icon[icon="mdi-folder"]')
      expect(folderIcon.exists()).toBe(true)
      expect(folderIcon.attributes('color')).toBe('yellow-darken-2')
    })

    it('should render Info icon with white color', () => {
      const infoIcon = wrapper.find('v-icon[icon="mdi-information"]')
      expect(infoIcon.exists()).toBe(true)
      expect(infoIcon.attributes('color')).toBe('white')
    })

    it('should fade Play icon when Claude CLI mode active', async () => {
      await wrapper.setData({ usingClaudeCodeSubagents: true })
      const playIcon = wrapper.find('v-icon[icon="mdi-play"]')
      expect(playIcon.classes()).toContain('faded-icon')
    })

    it('should NOT fade Play icon when Claude CLI mode inactive', async () => {
      await wrapper.setData({ usingClaudeCodeSubagents: false })
      const playIcon = wrapper.find('v-icon[icon="mdi-play"]')
      expect(playIcon.classes()).not.toContain('faded-icon')
    })

    it('should trigger handlePlayAgent on Play icon click', async () => {
      const handlePlayAgent = vi.fn()
      wrapper.vm.handlePlayAgent = handlePlayAgent

      const playIcon = wrapper.find('v-icon[icon="mdi-play"]')
      await playIcon.trigger('click')

      expect(handlePlayAgent).toHaveBeenCalled()
    })

    it('should trigger handleCopyAgentPrompt on Folder icon click', async () => {
      const handleCopyAgentPrompt = vi.fn()
      wrapper.vm.handleCopyAgentPrompt = handleCopyAgentPrompt

      const folderIcon = wrapper.find('v-icon[icon="mdi-folder"]')
      await folderIcon.trigger('click')

      expect(handleCopyAgentPrompt).toHaveBeenCalled()
    })

    it('should trigger handleShowAgentInfo on Info icon click', async () => {
      const handleShowAgentInfo = vi.fn()
      wrapper.vm.handleShowAgentInfo = handleShowAgentInfo

      const infoIcon = wrapper.find('v-icon[icon="mdi-information"]')
      await infoIcon.trigger('click')

      expect(handleShowAgentInfo).toHaveBeenCalled()
    })
  })

  describe('Table Border and Spacing', () => {
    it('should have table container with border', () => {
      const container = wrapper.find('.table-container')
      const styles = window.getComputedStyle(container.element)
      expect(styles.border).toContain('2px solid')
      expect(styles.borderRadius).toBe('16px')
    })

    it('should have header border-bottom', () => {
      const headerRow = wrapper.find('.agents-table thead tr')
      const styles = window.getComputedStyle(headerRow.element)
      expect(styles.borderBottom).toContain('1px solid')
    })

    it('should have body row borders', () => {
      const bodyRow = wrapper.find('.agents-table tbody tr')
      const styles = window.getComputedStyle(bodyRow.element)
      expect(styles.borderBottom).toContain('1px solid')
    })

    it('should have correct cell padding', () => {
      const cell = wrapper.find('.agents-table td')
      const styles = window.getComputedStyle(cell.element)
      expect(styles.padding).toContain('16px 12px')
    })
  })

  describe('Claude Toggle Styling', () => {
    it('should render Claude toggle section', () => {
      const toggleSection = wrapper.find('.claude-toggle-section')
      expect(toggleSection.exists()).toBe(true)
    })

    it('should show correct label', () => {
      const label = wrapper.find('.toggle-label')
      expect(label.text()).toBe('Claude Subagents')
    })

    it('should render toggle indicator', () => {
      const indicator = wrapper.find('.toggle-indicator')
      expect(indicator.exists()).toBe(true)
    })

    it('should render toggle dot', () => {
      const dot = wrapper.find('.toggle-dot')
      expect(dot.exists()).toBe(true)
    })

    it('should show grey dot when OFF', async () => {
      await wrapper.setData({ usingClaudeCodeSubagents: false })
      const dot = wrapper.find('.toggle-dot')
      const styles = window.getComputedStyle(dot.element)
      expect(styles.background).toContain('102, 102, 102') // #666 in rgb
    })

    it('should show green dot when ON', async () => {
      await wrapper.setData({ usingClaudeCodeSubagents: true })
      const dot = wrapper.find('.toggle-dot.toggle-on')
      const styles = window.getComputedStyle(dot.element)
      expect(styles.background).toContain('0, 255, 0') // #00ff00 in rgb
    })

    it('should show "OFF" status text when disabled', async () => {
      await wrapper.setData({ usingClaudeCodeSubagents: false })
      const status = wrapper.find('.toggle-status')
      expect(status.text()).toBe('OFF')
    })

    it('should show "ON" status text when enabled', async () => {
      await wrapper.setData({ usingClaudeCodeSubagents: true })
      const status = wrapper.find('.toggle-status')
      expect(status.text()).toBe('ON')
    })

    it('should have 16px dot size', () => {
      const dot = wrapper.find('.toggle-dot')
      const styles = window.getComputedStyle(dot.element)
      expect(styles.width).toBe('16px')
      expect(styles.height).toBe('16px')
      expect(styles.borderRadius).toBe('50%')
    })
  })

  describe('Message Composer (Preserved)', () => {
    it('should render message composer', () => {
      const composer = wrapper.find('.message-composer')
      expect(composer.exists()).toBe(true)
    })

    it('should have Orchestrator button', () => {
      const btn = wrapper.find('.orchestrator-button')
      expect(btn.exists()).toBe(true)
    })

    it('should have Broadcast button', () => {
      const btn = wrapper.find('.broadcast-button')
      expect(btn.exists()).toBe(true)
    })

    it('should trigger sendMessage on button click', async () => {
      const sendMessage = vi.fn()
      wrapper.vm.sendMessage = sendMessage

      const btn = wrapper.find('.orchestrator-button')
      await btn.trigger('click')

      expect(sendMessage).toHaveBeenCalled()
    })
  })

  describe('WebSocket Event Handling (Preserved)', () => {
    it('should add agent on agent:created event', async () => {
      const socket = wrapper.vm.$socket
      const initialCount = wrapper.vm.agents.length

      socket.emit('agent:created', {
        id: 'new-agent',
        type: 'Implementor',
        status: 'Waiting...',
      })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.agents).toHaveLength(initialCount + 1)
    })

    it('should update agent on agent:updated event', async () => {
      const socket = wrapper.vm.$socket
      await wrapper.setData({
        agents: [{ id: 'agent-1', status: 'Waiting...' }],
      })

      socket.emit('agent:updated', { id: 'agent-1', status: 'Working...' })
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.agents[0].status).toBe('Working...')
    })
  })
})
```

**Running Tests**:
```bash
cd frontend
npm test -- JobsTab.0242b.spec.js
```

**Expected Output**:
```
✓ JobsTab.vue - 0242b Table Refinement (49 tests)
  ✓ Dynamic Status Rendering (6 tests)
  ✓ Table Column Width Adjustments (11 tests)
  ✓ Action Icon Color Updates (9 tests)
  ✓ Table Border and Spacing (4 tests)
  ✓ Claude Toggle Styling (9 tests)
  ✓ Message Composer (Preserved) (4 tests)
  ✓ WebSocket Event Handling (Preserved) (2 tests)

Test Files  1 passed (1)
     Tests  49 passed (49)
```

---

## Files to Modify

### Primary File
- **`frontend/src/components/projects/JobsTab.vue`**
  - Modify: `<template>` section (dynamic status binding, table structure)
  - Modify: `<style scoped>` section (column widths, colors, borders)
  - **DO NOT MODIFY**: `<script>` section (preserve all logic)

### New Test File
- **`frontend/tests/unit/components/projects/JobsTab.0242b.spec.js`** (CREATE)
  - 49 comprehensive tests
  - Covers dynamic status, table layout, icons, toggle, preserved logic

---

## Files NOT to Modify

**Critical**: DO NOT modify these sections of `JobsTab.vue`:

```vue
<script>
// ❌ DO NOT TOUCH THIS SCRIPT SECTION ❌

// Preserve reactive refs
const agents = ref([])
const usingClaudeCodeSubagents = ref(false)

// Preserve WebSocket handlers
socket.on('agent:created', (agentData) => {
  agents.value.push(agentData)
})

socket.on('agent:updated', (agentData) => {
  const index = agents.value.findIndex(a => a.id === agentData.id)
  if (index !== -1) {
    agents.value[index] = { ...agents.value[index], ...agentData }
  }
})

// Preserve message composer logic
const sendMessage = async (recipientId, messageContent) => {
  // Message queue logic
}

// ❌ END DO NOT TOUCH ❌
</script>
```

---

## Success Criteria

### Visual Validation
- ✅ Side-by-side comparison with `IMplement tab.jpg` shows pixel-perfect match
- ✅ Agent status is dynamic (NOT hardcoded "Waiting.")
- ✅ Table column widths match screenshot proportions
- ✅ Action icons: Play/Folder yellow, Info white
- ✅ Claude toggle: Green dot when ON, grey when OFF

### Functional Validation
- ✅ All 49 tests passing
- ✅ WebSocket `agent:updated` event updates status column
- ✅ Status values render correctly: Waiting.../Working.../Complete/Error
- ✅ Play icon fades in Claude CLI mode
- ✅ Message composer functional

### Code Quality
- ✅ No console errors in browser DevTools
- ✅ No linting errors (`npm run lint`)
- ✅ `<script>` section unchanged from 0241 implementation
- ✅ All reactive logic preserved

---

## Testing Commands

```bash
# Frontend directory
cd frontend

# Install dependencies (if needed)
npm install

# Run specific test file
npm test -- JobsTab.0242b.spec.js

# Run with coverage
npm test -- JobsTab.0242b.spec.js --coverage

# Run all tests (0242a + 0242b)
npm test

# Lint check
npm run lint

# Build verification
npm run build
```

---

## Manual Verification Steps

1. **Start Backend Server**:
   ```bash
   python startup.py
   ```

2. **Start Frontend Dev Server**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Navigate to Implement Tab**:
   - Open: `http://10.1.0.164:7274/projects/{project-id}?via=jobs`

4. **Visual Inspection**:
   - Open `IMplement tab.jpg` screenshot side-by-side
   - Compare:
     - Table column widths (Agent Type 19%, Agent ID 20%, etc.)
     - Agent Status column (yellow italic text)
     - Action icons (Play/Folder yellow, Info white)
     - Claude toggle (green dot when ON)

5. **Functional Testing**:
   - Stage project → Launch jobs (navigate to Implement Tab)
   - Verify Orchestrator row appears
   - Verify Agent Status shows "Waiting..." initially
   - Wait for agent:created events
   - Verify new agent rows appear
   - Wait for agent:updated events
   - **CRITICAL**: Verify Agent Status column updates dynamically
   - Toggle Claude Subagents → Verify Play icon fades
   - Click Folder icon → Verify clipboard copy works
   - Click Info icon → Verify agent details modal appears

6. **DevTools WebSocket Monitoring**:
   - Open DevTools → Network → WS tab
   - Monitor WebSocket connection
   - Watch for `agent:updated` events
   - Verify status column updates when events received

7. **DevTools Console Check**:
   - Open DevTools → Console
   - Verify no errors logged
   - Check for warnings (should be none)

---

## Rollback Plan

If issues arise during implementation:

1. **Git Stash Changes**:
   ```bash
   git stash save "0242b in-progress work"
   ```

2. **Return to 0242a State**:
   ```bash
   git checkout frontend/src/components/projects/JobsTab.vue
   ```

3. **Document Issues**:
   - Create GitHub issue: `GUI 0242b Rollback - [describe problem]`
   - Tag with `gui-redesign`, `0242-series`, `needs-investigation`

---

## Next Steps

**Upon Completion of 0242b**:
1. ✅ All 49 tests passing
2. ✅ Visual validation complete (pixel-perfect match)
3. ✅ Manual testing complete (dynamic status verified)
4. ✅ Git commit created:
   ```bash
   git add frontend/src/components/projects/JobsTab.vue
   git add frontend/tests/unit/components/projects/JobsTab.0242b.spec.js
   git commit -m "feat: Implement Tab table refinement (0242b)

   - Dynamic status rendering (replaced hardcoded 'Waiting.')
   - Table column width adjustments (match Nicepage proportions)
   - Action icon colors (Play/Folder yellow, Info white)
   - Claude toggle styling (green/grey dot indicator)
   - 49 comprehensive tests
   - Preserved WebSocket reactivity and message composer

   Handover: 0242b
   Tests: 49 passing (78 total with 0242a)
   Status: Ready for 0242c ✅"
   ```

5. **Proceed to Handover 0242c**: Integration testing and polish

---

## Notes for TDD-Implementor Subagent

**Your Mission**:
- **CRITICAL**: Replace hardcoded "Waiting." with `{{ agent.status || 'Waiting...' }}`
- Focus on table structure and column proportions
- Match screenshot pixel-perfect (use DevTools to measure)
- Run tests frequently (TDD approach: write test → implement → verify)
- DO NOT refactor `<script>` logic (that's out of scope)
- Preserve all WebSocket handlers and message composer

**Communication**:
- Report progress after each task (1-6)
- Share screenshots of before/after comparisons
- Run `npm test` after every change to catch regressions early
- Verify dynamic status updates via WebSocket events
- Ask questions if screenshot is ambiguous

**Quality Checklist Before Marking Complete**:
- [ ] All 49 tests passing
- [ ] Agent Status column shows dynamic values (NOT hardcoded)
- [ ] Table column widths match screenshot proportions
- [ ] Action icons have correct colors (Play/Folder yellow, Info white)
- [ ] Claude toggle works correctly (green/grey dot)
- [ ] No console errors in DevTools
- [ ] No linting errors
- [ ] Side-by-side screenshot comparison shows pixel-perfect match
- [ ] Manual WebSocket event test confirms status updates
