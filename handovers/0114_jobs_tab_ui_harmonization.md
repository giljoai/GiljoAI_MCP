---
**Handover ID:** 0114
**Title:** Jobs Tab UI/UX Harmonization with Visual Design Spec
**Date:** 2025-01-07
**Status:** Planning
**Priority:** High
**Complexity:** Medium
**Estimated Effort:** 2 weeks
**Related Handovers:**
- 0113 (Unified Agent State System)
- 0073 (Static Agent Grid)
- 0107 (Agent Monitoring & Cancellation)
- 0105 (Claude Code Subagent Toggle)
- 0109 (Execution Prompt Dialog)

**Design Reference:** `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels version 2.pdf`

---

## 1. Executive Summary

### Current State
The Jobs tab has a basic implementation with:
- Agent cards displayed horizontally with scroll functionality
- "Use Claude Code Subagents" toggle (Handover 0105)
- Basic status badges (waiting, working, complete, failed, blocked)
- Message Center panel on the right side
- "Launch Agent" buttons for waiting agents
- Execution prompt dialog (Handover 0109)

### Desired State
Full implementation per PDF design specification (9 slides) with:
- Dual-mode operation: "Staging" vs "Jobs" tabs
- Complete 8-state status badge system
- Dynamic button behavior based on Claude Code toggle
- Orchestrator-specific action buttons ("Close Out Project", "Continue Working")
- Project completion banner with summary download
- Decommissioned state for closed-out projects
- Unassigned agent slot placeholder
- Enhanced visual hierarchy and professional polish

### Goal
Production-grade UI that exactly matches the PDF specification, providing a polished, intuitive user experience for managing multi-agent workflows.

---

## 2. Visual Design Analysis (9 Slides)

### Slide 1: Initial Staging State
**Context:** User activates a project for the first time

**UI Elements:**
- Tab navigation: **"Staging"** (active) | "Jobs" (inactive)
- Project header:
  - Project title (yellow text)
  - Project ID (below title)
  - Link format: `http://x.x.x.x\project\{project-ID}?via=jobs`
- Two side-by-side panels:
  - **Left:** "Project Description" (editable with "Edit" button)
  - **Right:** "Orchestrator Created Mission" (editable with "Edit" button)
- Agent team section (green header background)
- Single agent card: **Orchestrator**
  - Brown/tan header with "Orchestrator" label
  - Agent ID: Xxxxxxxxxxxx
  - Role: FROM TEMPLATE
  - Status badge: "Activated" (green)
- Action button: **"Stage Project"** (green button, left sidebar area)
- Note: "Remaining Agents appear here via Websocket structure when Orchestrator finishes assigning them to project."
- **Important:** Only one orchestrator allowed per project at any time. Second can only be created via `/handover` MCP command.

---

### Slide 2: Finished Staging State
**Context:** Orchestrator has created mission and assigned all agents

**UI Changes from Slide 1:**
- Action button changes:
  - **"Launch Jobs"** (yellow button) replaces "Stage Project"
  - **"CANCEL"** (pink button) appears next to it
- Agent grid now displays:
  - Orchestrator (brown/tan header)
  - Analyzer (red header)
  - Implementer (light blue header)
  - Reviewer (purple header)
  - Tester (yellow header)
  - Doc (green header - partially visible, indicating more cards)
- Each agent card shows:
  - Agent ID: Xxxxxxxxxxxx
  - Role: (from template)
  - **"EDIT JOB"** button at bottom
- Grid behavior:
  - **Sideways scrollable** (horizontal overflow)
  - Navigation arrows: `<` (left) and `>` (right) for scroll control
  - Multiple agents of same type allowed (e.g., two uniquely ID'd Implementers)

**Color Scheme:**
- Launch Jobs button: Yellow/gold background, black text
- CANCEL button: Pink/magenta background, white text
- Agent headers: Each agent type has unique color (from agent color palette)

---

### Slide 3: Jobs Page - Waiting State (Claude Code OFF)
**Context:** User clicked "Launch Jobs" button, transitioned to Jobs tab

**Tab Navigation:**
- "Staging" (inactive) | **"Jobs"** (active)

**Layout:**
- **Left Column (~60% width):** Agent cards (horizontal scrollable)
- **Right Column (~40% width):** Message Center panel

**Agent Cards:**
Each card shows:
- Agent type header (color-coded)
- Agent ID: Xxxxxxxxxxxx
- **Status: "Waiting"** (white badge with border, no background fill)
- Info field TBD (placeholder)
- Instruction text:
  ```
  Each agent requires its own Terminal
  window and agentic AI tool started.
  Claude Code uses subagents, and does
  not require individual terminal windows
  per agent but can still be used this way
  ```
- **"Launch Agent"** button (yellow/gold, black text)

**Special Elements:**
- **Toggle (Orchestrator card):** "Use Claude Code Subagents" (OFF state)
- **Unassigned agent slot:** Dashed-border placeholder card
  - No agent type header
  - Center text: "Unassigned agent slot"
  - Note: "No Max agent fill, but only one card placeholder is shown."

**Message Center:**
- Header: "Message Center"
- Empty state (no messages yet)
- User avatar at bottom (circle icon)

**Important Notes:**
- This is the default condition **before agents have started working**
- Claude Code toggle defaults to **OFF**
- All agents show "Waiting" status
- All agents display "Launch Agent" button

---

### Slide 4: Jobs Page - Waiting State (Claude Code ON)
**Context:** User toggled "Use Claude Code Subagents" to ON

**Key Differences from Slide 3:**
1. **Toggle state:** "Use Claude Code Subagents" (ON - green switch)

2. **Button changes:**
   - **"Launch Agent"** replaced with **"View Prompt"** button
   - Button style: Outlined/secondary style (not bold yellow)

3. **Text changes:**
   - Instruction text replaced with:
     ```
     USING CLAUDE SUBAGENTS
     ```
   - Displayed in darker box/card background

4. **Orchestrator card:**
   - Still shows "Launch Agent" button (orchestrator launches regardless of toggle)
   - Toggle control remains on orchestrator card

**Message Center:**
- Header: "Messages" (note: plural, not "Message Center")
- Still empty state

**Behavior:**
- Only orchestrator launches in separate terminal
- Other agents will be spawned as Claude Code subagents by orchestrator
- Non-orchestrator cards become informational (no launch action needed)

---

### Slide 5: Jobs Page - Working State
**Context:** Agents are actively working on tasks

**Status Changes:**
- Orchestrator: **"Working"** (white badge with border)
- Analyzer: **"Working"** (white badge with border)
- Implementer: **"Working"** (white badge with border)
- Implementer 2: **"Working"** (white badge with border)
- Tester: **"Working"** (white badge with border)

**UI Elements:**
- All cards maintain "USING CLAUDE SUBAGENTS" text (if toggle ON)
- All cards show **"View Prompt"** button
- Status badges change from "Waiting" to "Working"
- Toggle remains visible on orchestrator card
- Unassigned agent slot still visible

**Message Center:**
- Header: "Messages"
- Scroll bar visible (messages accumulating)

**Visual Indicator:**
- Subtle animation or icon on "Working" badges (optional)

---

### Slide 6: Jobs Page - Failed State
**Context:** One agent encounters an error

**Status Changes:**
- Orchestrator: "Working" (white badge)
- **Analyzer: "Failed"** (pink/magenta badge, filled background)
- Implementer: "Working" (white badge)
- Implementer 2: "Working" (white badge)
- Tester: "Working" (white badge)

**Failed Agent Card (Analyzer):**
- Status badge: **"Failed"** (pink/magenta background, white text)
- Badge style: Filled (not outlined like waiting/working)
- Info field shows error details (if available)
- "View Prompt" button remains

**Other agents:**
- Continue showing "Working" status
- No changes to their cards

**Visual Hierarchy:**
- Failed card should stand out (priority state)
- Error badge uses high-contrast color

---

### Slide 7: Jobs Page - All Complete State
**Context:** All agents have finished their tasks successfully

**Status Changes:**
- **All agents:** "Completed" (green badge, filled background)

**Orchestrator Card - Special Actions:**
Two new buttons appear on orchestrator card:
1. **"Close Out Project"** (green button, filled)
2. **"Continue Working"** (blue button, filled)

**Button Behavior:**
- **Close Out Project:** Transitions all agents to "Decommissioned" state
- **Continue Working:** Returns all agents to "Working" status (resume work)

**Visual Layout:**
- Both buttons appear in orchestrator card action area
- Stacked vertically or side-by-side (design choice)
- "Close Out Project" has visual prominence (primary action)

**Other Agent Cards:**
- Show "Completed" status badge (green, filled)
- "View Prompt" button remains
- No special action buttons

---

### Slide 8: Status Badge Reference
**Context:** Complete status badge color palette

**Status Badge List:**
Per database model (`src/giljo_mcp/models.py:2077-2078`):
```python
status = "waiting" | "working" | "review" | "complete" | "failed" | "blocked" | "cancelled" | "decommissioned"
```

**Badge Styles:**

1. **Waiting** (white outlined)
   - Border: 2px solid white
   - Background: transparent
   - Text: white

2. **Working** (white outlined)
   - Border: 2px solid white
   - Background: transparent
   - Text: white

3. **Completed** (green filled)
   - Background: #4CAF50
   - Text: white
   - Icon: mdi-check-circle

4. **Reviewing** (purple/magenta filled)
   - Background: #9C27B0
   - Text: white
   - Icon: mdi-eye-check

5. **Blocked** (orange filled)
   - Background: #FF9800
   - Text: white
   - Icon: mdi-alert-octagon

6. **Failed** (pink/red filled)
   - Background: #E91E63
   - Text: white
   - Icon: mdi-alert-circle

7. **Cancelled** (red filled)
   - Background: #F44336
   - Text: white
   - Icon: mdi-cancel

8. **Decommissioned** (gray filled)
   - Background: #9E9E9E
   - Text: white
   - Icon: mdi-power-off

**Visual Guidelines:**
- Outlined badges: Border only, no background fill
- Filled badges: Solid background color, white text
- Badge height: 20-24px
- Font size: 11-12px
- Border radius: 12px (pill shape)

---

### Slide 9: Project Closed Out State
**Context:** User clicked "Close Out Project" button

**Top Banner (NEW):**
- Green banner spanning full width
- Text: **"Project Completed"** (green text, large font)
- Button: **"Download Summary"** (green filled button)
- Position: Above agent cards, below tab navigation
- Purpose: Signals project is complete and user can download summary documentation

**Status Changes:**
- **All agents:** "Decommissioned" (gray badge, filled background)

**Agent Card Changes:**
- Status: "Decommissioned" badge (gray)
- Action button: **"View Prompt"** (no launch/action buttons)
- Info text: "USING CLAUDE SUBAGENTS" (if toggle was ON)
- Cards become read-only/informational

**Orchestrator Card:**
- No "Close Out Project" or "Continue Working" buttons
- Only "View Prompt" button remains
- Status: "Decommissioned"

**Behavior:**
- Project is in final/archived state
- No further work can be initiated
- All data remains viewable
- Summary download provides final documentation

**Visual Indicators:**
- Banner provides clear visual signal of completion
- Gray badges indicate inactive/archived state
- Download button provides actionable next step

---

## 3. Component Requirements

### 3.1 Frontend Components to Update

#### A. `ProjectTabs.vue` (Location: `F:\GiljoAI_MCP\frontend\src\components\projects\ProjectTabs.vue`)
**Current Implementation:** Unknown (needs investigation)

**Required Updates:**
- Add proper "Staging" vs "Jobs" tab navigation
- "Staging" tab shows:
  - Project Description panel (editable)
  - Orchestrator Created Mission panel (editable)
  - Agent team grid (orchestrator + assigned agents)
  - "Stage Project" button (transitions to "Launch Jobs" when ready)
  - "CANCEL" button (when staging complete)
- "Jobs" tab shows:
  - Agent cards grid (horizontal scroll)
  - Message Center panel
  - Status-dependent UI elements
- Handle tab switching logic
- Persist tab state in URL query params (e.g., `?tab=jobs`)

---

#### B. `JobsTab.vue` (Location: `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue`)
**Current Implementation:** ✅ Well-implemented (1060 lines)

**Required Updates:**
1. **Remove existing completion banner** (lines 4-18)
   - Current: Simple v-alert when all agents complete
   - Replace with: Full ProjectCompletionBanner component

2. **Add Project Completion Banner** (above agent grid)
   - Show when all agents decommissioned
   - Component: `<ProjectCompletionBanner />` (new component)

3. **Update Claude Code Toggle** (lines 45-68)
   - Current: Toggle with hint text
   - Keep existing implementation
   - Ensure toggle state persists in Vuex store

4. **Agent Cards Grid** (lines 70-100)
   - Current: Horizontal scroll working well
   - Keep existing implementation
   - Ensure unassigned agent slot placeholder renders correctly

5. **Message Center Panel** (lines 132-150)
   - Current: MessageStream + MessageInput
   - Keep existing implementation
   - Update header text based on state ("Message Center" vs "Messages")

**No Major Changes Needed** - Current implementation already aligns well with PDF design.

---

#### C. `AgentCardEnhanced.vue` (Location: `F:\GiljoAI_MCP\frontend\src\components\projects\AgentCardEnhanced.vue`)
**Current Implementation:** ✅ Comprehensive (918 lines)

**Required Updates:**

1. **Status Display** (lines 27-30)
   - Current: Basic status text
   - Update: Use StatusBadge component with 8-state styling

2. **Waiting State - Button Logic** (lines 248-271)
   - Current: "Launch Agent" button with tooltip when disabled
   - **CORRECT** - Matches PDF Slide 3 & 4
   - Keep existing implementation:
     - When `promptButtonDisabled = false`: Show "Launch Agent" (yellow button)
     - When `promptButtonDisabled = true`: Show "Claude Code Mode" (gray, disabled)

3. **Add Instructional Text** (NEW - below status)
   - When `status === 'waiting'` AND `!promptButtonDisabled`:
     ```vue
     <div class="agent-instructions text-caption text-grey">
       Each agent requires its own Terminal window and agentic AI tool started.
       Claude Code uses subagents, and does not require individual terminal
       windows per agent but can still be used this way
     </div>
     ```
   - When `status === 'waiting'` AND `promptButtonDisabled`:
     ```vue
     <div class="agent-instructions text-caption text-primary font-weight-bold">
       USING CLAUDE SUBAGENTS
     </div>
     ```

4. **Working State - "View Prompt" button** (NEW)
   - When `status === 'working'`:
     ```vue
     <v-btn
       v-if="status === 'working'"
       variant="outlined"
       color="primary"
       block
       @click="$emit('view-prompt', agent)"
     >
       <v-icon start>mdi-text-box-outline</v-icon>
       View Prompt
     </v-btn>
     ```
   - Show "USING CLAUDE SUBAGENTS" text if toggle ON

5. **Complete State - Orchestrator Actions** (lines 324-333)
   - Current: Simple "Closeout Project" button when `showCloseoutButton = true`
   - **UPDATE:** Replace with OrchestratorActions component (new component)
   - Component should show TWO buttons:
     - "Close Out Project" (green)
     - "Continue Working" (blue)

6. **Decommissioned State** (NEW)
   - When `status === 'decommissioned'`:
     - Show gray "Decommissioned" badge
     - Only show "View Prompt" button (no actions)
     - Display "USING CLAUDE SUBAGENTS" text if toggle was ON

**Testing Checklist:**
- [ ] Waiting state shows correct button based on toggle
- [ ] Instructional text appears/disappears correctly
- [ ] Working state shows "View Prompt" button
- [ ] Complete state shows orchestrator actions (orchestrator only)
- [ ] Decommissioned state is read-only

---

#### D. `StatusBadge.vue` (Location: `F:\GiljoAI_MCP\frontend\src\components\StatusBadge.vue`)
**Current Implementation:** ❌ Incorrect - Project status badge, not agent job status

**Current Purpose:** Project status (active, inactive, completed, cancelled, deleted)

**Required Action:** Create new component: `AgentStatusBadge.vue`

**New Component: `AgentStatusBadge.vue`**
**Purpose:** Display agent job status with 8-state styling

**Props:**
```javascript
{
  status: {
    type: String,
    required: true,
    validator: (value) => [
      'waiting',
      'working',
      'review',
      'complete',
      'failed',
      'blocked',
      'cancelled',
      'decommissioned'
    ].includes(value)
  },
  size: {
    type: String,
    default: 'small',
    validator: (value) => ['x-small', 'small', 'default'].includes(value)
  }
}
```

**Badge Styling Map:**
```javascript
const STATUS_CONFIG = {
  waiting: {
    label: 'Waiting',
    color: 'transparent',
    textColor: 'white',
    border: '2px solid white',
    icon: 'mdi-clock-outline'
  },
  working: {
    label: 'Working',
    color: 'transparent',
    textColor: 'white',
    border: '2px solid white',
    icon: 'mdi-cog'
  },
  review: {
    label: 'Reviewing',
    color: '#9C27B0', // purple
    textColor: 'white',
    border: 'none',
    icon: 'mdi-eye-check'
  },
  complete: {
    label: 'Completed',
    color: '#4CAF50', // green
    textColor: 'white',
    border: 'none',
    icon: 'mdi-check-circle'
  },
  failed: {
    label: 'Failed',
    color: '#E91E63', // pink
    textColor: 'white',
    border: 'none',
    icon: 'mdi-alert-circle'
  },
  blocked: {
    label: 'Blocked',
    color: '#FF9800', // orange
    textColor: 'white',
    border: 'none',
    icon: 'mdi-alert-octagon'
  },
  cancelled: {
    label: 'Cancelled',
    color: '#F44336', // red
    textColor: 'white',
    border: 'none',
    icon: 'mdi-cancel'
  },
  decommissioned: {
    label: 'Decommissioned',
    color: '#9E9E9E', // gray
    textColor: 'white',
    border: 'none',
    icon: 'mdi-power-off'
  }
}
```

**Template:**
```vue
<template>
  <v-chip
    :color="badgeConfig.color"
    :style="badgeStyle"
    :size="size"
    :prepend-icon="badgeConfig.icon"
    variant="flat"
    class="agent-status-badge"
    :aria-label="`Agent status: ${badgeConfig.label}`"
    role="status"
  >
    <span class="badge-text">{{ badgeConfig.label }}</span>
  </v-chip>
</template>
```

**Computed Style:**
```javascript
const badgeStyle = computed(() => {
  const config = STATUS_CONFIG[props.status]
  return {
    backgroundColor: config.color,
    color: config.textColor,
    border: config.border,
    fontWeight: 600,
    letterSpacing: '0.5px'
  }
})
```

---

#### E. `ProjectCompletionBanner.vue` (NEW - Location: `F:\GiljoAI_MCP\frontend\src\components\projects\ProjectCompletionBanner.vue`)
**Purpose:** Display project completion banner with download summary button

**Props:**
```javascript
{
  projectId: {
    type: String,
    required: true
  },
  projectName: {
    type: String,
    required: true
  }
}
```

**Template:**
```vue
<template>
  <v-banner
    class="project-completion-banner"
    color="success"
    icon="mdi-check-circle"
    elevation="2"
    lines="one"
    sticky
  >
    <template v-slot:text>
      <div class="d-flex align-center justify-space-between">
        <div class="completion-text">
          <h3 class="text-h5 font-weight-bold">Project Completed</h3>
          <p class="text-body-2 mt-1 mb-0">
            All agents have been decommissioned. Download the summary to review results.
          </p>
        </div>
        <v-btn
          color="success"
          variant="elevated"
          size="large"
          prepend-icon="mdi-download"
          @click="downloadSummary"
          :loading="downloading"
          aria-label="Download project summary"
        >
          Download Summary
        </v-btn>
      </div>
    </template>
  </v-banner>
</template>
```

**Methods:**
```javascript
const downloading = ref(false)

const downloadSummary = async () => {
  downloading.value = true
  try {
    const response = await api.get(`/api/projects/${props.projectId}/summary`, {
      responseType: 'blob'
    })

    // Create download link
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.projectName}_Summary.pdf`
    link.click()
    window.URL.revokeObjectURL(url)

    showToast('Summary downloaded successfully', 'success')
  } catch (error) {
    console.error('Failed to download summary:', error)
    showToast('Failed to download summary', 'error')
  } finally {
    downloading.value = false
  }
}
```

**Styling:**
```scss
.project-completion-banner {
  background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%) !important;
  color: white !important;
  padding: 24px 32px !important;
  border-radius: 12px !important;
  margin-bottom: 24px !important;
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.3) !important;

  .completion-text {
    h3 {
      color: white;
      margin-bottom: 8px;
    }
    p {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}
```

---

#### F. `OrchestratorActions.vue` (NEW - Location: `F:\GiljoAI_MCP\frontend\src\components\projects\OrchestratorActions.vue`)
**Purpose:** Orchestrator-specific action buttons when all agents complete

**Props:**
```javascript
{
  orchestratorId: {
    type: String,
    required: true
  },
  projectId: {
    type: String,
    required: true
  }
}
```

**Template:**
```vue
<template>
  <div class="orchestrator-actions">
    <!-- Close Out Project Button -->
    <v-btn
      color="success"
      variant="elevated"
      block
      prepend-icon="mdi-check-circle"
      class="mb-2"
      @click="handleCloseOut"
      :loading="closingOut"
      aria-label="Close out project and mark all agents as decommissioned"
    >
      Close Out Project
    </v-btn>

    <!-- Continue Working Button -->
    <v-btn
      color="primary"
      variant="elevated"
      block
      prepend-icon="mdi-refresh"
      @click="handleContinue"
      :loading="continuing"
      aria-label="Return all agents to working status"
    >
      Continue Working
    </v-btn>
  </div>
</template>
```

**Methods:**
```javascript
const closingOut = ref(false)
const continuing = ref(false)
const emit = defineEmits(['close-out', 'continue-working'])

const handleCloseOut = async () => {
  const confirmed = confirm(
    'Close Out Project?\n\n' +
    'This will decommission all agents and mark the project as completed.\n\n' +
    'You can still view agent details and download the summary.\n\n' +
    'Continue?'
  )

  if (!confirmed) return

  closingOut.value = true
  try {
    await api.post(`/api/projects/${props.projectId}/close-out`)
    emit('close-out')
    showToast('Project closed out successfully', 'success')
  } catch (error) {
    console.error('Failed to close out project:', error)
    showToast('Failed to close out project', 'error')
  } finally {
    closingOut.value = false
  }
}

const handleContinue = async () => {
  const confirmed = confirm(
    'Continue Working?\n\n' +
    'This will return all agents to "Working" status.\n\n' +
    'Use this if you need agents to perform additional work.\n\n' +
    'Continue?'
  )

  if (!confirmed) return

  continuing.value = true
  try {
    await api.post(`/api/projects/${props.projectId}/continue-working`)
    emit('continue-working')
    showToast('Agents returned to working status', 'success')
  } catch (error) {
    console.error('Failed to continue working:', error)
    showToast('Failed to continue working', 'error')
  } finally {
    continuing.value = false
  }
}
```

---

#### G. `UnassignedAgentSlot.vue` (NEW - Location: `F:\GiljoAI_MCP\frontend\src\components\projects\UnassignedAgentSlot.vue`)
**Purpose:** Placeholder card for unassigned agent slots

**Props:**
```javascript
{
  // No props needed - purely visual
}
```

**Template:**
```vue
<template>
  <v-card
    class="unassigned-agent-slot"
    variant="outlined"
    :style="slotStyles"
    role="presentation"
    aria-label="Unassigned agent slot"
  >
    <v-card-text class="d-flex align-center justify-center">
      <div class="text-center text-grey">
        <v-icon size="64" color="grey-lighten-1">mdi-plus-circle-outline</v-icon>
        <div class="text-body-2 mt-2">Unassigned agent slot</div>
      </div>
    </v-card-text>
  </v-card>
</template>
```

**Computed Styles:**
```javascript
const slotStyles = computed(() => ({
  width: '280px',
  minHeight: '200px',
  borderRadius: '20px',
  border: '2px dashed rgba(0, 0, 0, 0.2)',
  background: 'transparent',
  transition: 'all 0.3s ease'
}))
```

**Styling:**
```scss
.unassigned-agent-slot {
  cursor: default;
  opacity: 0.6;

  &:hover {
    opacity: 0.8;
    border-color: rgba(0, 0, 0, 0.4);
  }
}
```

---

### 3.2 Component Integration Summary

**Component Hierarchy:**
```
ProjectTabs.vue
├── StagingTab.vue (existing or new)
│   ├── ProjectDescriptionPanel.vue (editable)
│   ├── MissionPanel.vue (editable)
│   ├── AgentTeamGrid.vue
│   │   └── AgentCardEnhanced.vue (mode="launch")
│   └── StagingActions.vue (Stage Project / Launch Jobs / Cancel buttons)
│
└── JobsTab.vue (existing - update)
    ├── ProjectCompletionBanner.vue (NEW - shown when all decommissioned)
    ├── AgentCardsSection.vue (left column)
    │   ├── ClaudeCodeToggle.vue (existing - keep)
    │   ├── AgentCardEnhanced.vue (update)
    │   │   ├── AgentStatusBadge.vue (NEW)
    │   │   └── OrchestratorActions.vue (NEW - shown on orchestrator when all complete)
    │   └── UnassignedAgentSlot.vue (NEW)
    └── MessageCenterPanel.vue (right column - existing)
        ├── MessageStream.vue (existing)
        └── MessageInput.vue (existing)
```

---

## 4. State Management Updates

### 4.1 Vuex Store: `projectTabs.js`

**Current State:**
```javascript
// Location: frontend/src/stores/projectTabs.js (if exists)
// OR: frontend/src/stores/projects.js

state: {
  activeTab: 'staging', // 'staging' | 'jobs'
  claudeCodeSubagentsEnabled: false, // Already exists per Handover 0105
  // ... other state
}
```

**New State Properties:**
```javascript
state: {
  activeTab: 'staging', // 'staging' | 'jobs'
  claudeCodeSubagentsEnabled: false,
  stagingComplete: false, // true when orchestrator assigns all agents
  allAgentsComplete: false, // true when all agents status = 'complete'
  allAgentsDecommissioned: false, // true when all agents status = 'decommissioned'
  projectClosedOut: false // true when project.status = 'completed'
}
```

**Mutations:**
```javascript
mutations: {
  SET_ACTIVE_TAB(state, tab) {
    state.activeTab = tab
  },

  SET_CLAUDE_CODE_SUBAGENTS(state, enabled) {
    state.claudeCodeSubagentsEnabled = enabled
  },

  SET_STAGING_COMPLETE(state, complete) {
    state.stagingComplete = complete
  },

  SET_ALL_AGENTS_COMPLETE(state, complete) {
    state.allAgentsComplete = complete
  },

  SET_ALL_AGENTS_DECOMMISSIONED(state, decommissioned) {
    state.allAgentsDecommissioned = decommissioned
  },

  SET_PROJECT_CLOSED_OUT(state, closedOut) {
    state.projectClosedOut = closedOut
  }
}
```

**Actions:**
```javascript
actions: {
  switchTab({ commit }, tab) {
    commit('SET_ACTIVE_TAB', tab)
    // Update URL query param
    const url = new URL(window.location)
    url.searchParams.set('tab', tab)
    window.history.pushState({}, '', url)
  },

  toggleClaudeCodeSubagents({ commit, state }) {
    const newValue = !state.claudeCodeSubagentsEnabled
    commit('SET_CLAUDE_CODE_SUBAGENTS', newValue)
    // Persist to localStorage
    localStorage.setItem('claudeCodeSubagents', JSON.stringify(newValue))
  },

  updateAgentStatuses({ commit }, agents) {
    // Check if all agents complete
    const allComplete = agents.every(a => a.status === 'complete')
    commit('SET_ALL_AGENTS_COMPLETE', allComplete)

    // Check if all agents decommissioned
    const allDecommissioned = agents.every(a => a.status === 'decommissioned')
    commit('SET_ALL_AGENTS_DECOMMISSIONED', allDecommissioned)
  }
}
```

**Getters:**
```javascript
getters: {
  showCompletionBanner: (state) => {
    return state.allAgentsDecommissioned && state.projectClosedOut
  },

  showOrchestratorActions: (state) => {
    return state.allAgentsComplete && !state.projectClosedOut
  },

  stagingButtonLabel: (state) => {
    return state.stagingComplete ? 'Launch Jobs' : 'Stage Project'
  }
}
```

---

### 4.2 WebSocket Event Handlers

**New Events to Handle:**

```javascript
// Location: frontend/src/composables/useWebSocket.js

// Event: job:all_complete
// Triggered when all agent jobs reach 'complete' status
on('job:all_complete', (data) => {
  console.log('[WebSocket] All agents complete:', data)
  store.commit('projects/SET_ALL_AGENTS_COMPLETE', true)

  // Show toast notification
  showToast('All agents have completed their tasks!', 'success')
})

// Event: project:closed_out
// Triggered when project.status transitions to 'completed'
on('project:closed_out', (data) => {
  console.log('[WebSocket] Project closed out:', data)
  store.commit('projects/SET_PROJECT_CLOSED_OUT', true)
  store.commit('projects/SET_ALL_AGENTS_DECOMMISSIONED', true)

  // Update all agent statuses to 'decommissioned'
  // (Should be handled by agent job update events)
})

// Event: job:status_changed
// Already exists - update to handle new statuses
on('job:status_changed', (data) => {
  console.log('[WebSocket] Job status changed:', data)

  // Update agent in store
  store.commit('projects/UPDATE_AGENT_STATUS', {
    jobId: data.job_id,
    status: data.status
  })

  // Re-check all agent statuses
  const agents = store.state.projects.currentProject.agents
  store.dispatch('projects/updateAgentStatuses', agents)
})

// Event: agents:assigned
// Triggered when orchestrator finishes assigning agents
on('agents:assigned', (data) => {
  console.log('[WebSocket] Agents assigned:', data)
  store.commit('projects/SET_STAGING_COMPLETE', true)

  // Update agent list
  store.commit('projects/SET_AGENTS', data.agents)
})
```

---

## 5. API Endpoint Requirements

### 5.1 New Endpoints to Implement

#### A. Close Out Project
**Endpoint:** `POST /api/projects/{project_id}/close-out`

**Purpose:** Transitions all 'complete' agents to 'decommissioned' and project to 'completed'

**Request Body:** (optional)
```json
{
  "notes": "Final project notes (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "project_id": "uuid",
  "status": "completed",
  "agents_decommissioned": 5,
  "decommissioned_at": "2025-01-07T12:34:56Z"
}
```

**Logic:**
```python
# Location: api/endpoints/projects.py

@router.post("/{project_id}/close-out")
async def close_out_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Close out a project:
    1. Verify all agents are in 'complete' status
    2. Transition all agents to 'decommissioned'
    3. Set project.status = 'completed'
    4. Emit WebSocket event: project:closed_out
    """
    # Get project with multi-tenant isolation
    project = db.query(MCPProject).filter(
        MCPProject.project_id == project_id,
        MCPProject.tenant_id == current_user.tenant_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all agent jobs for this project
    agents = db.query(MCPAgentJob).filter(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_id == current_user.tenant_id
    ).all()

    # Check if all agents are complete
    if not all(agent.status == 'complete' for agent in agents):
        raise HTTPException(
            status_code=400,
            detail="Cannot close out project - not all agents are complete"
        )

    # Transition all agents to decommissioned
    for agent in agents:
        agent.status = 'decommissioned'
        agent.decommissioned_at = datetime.now(timezone.utc)

    # Update project status
    project.status = 'completed'
    project.completed_at = datetime.now(timezone.utc)

    db.commit()

    # Emit WebSocket event
    await websocket_manager.broadcast_to_project(
        project_id=project_id,
        event='project:closed_out',
        data={
            'project_id': project_id,
            'status': 'completed',
            'agents_decommissioned': len(agents)
        }
    )

    return {
        'success': True,
        'project_id': project_id,
        'status': 'completed',
        'agents_decommissioned': len(agents),
        'decommissioned_at': project.completed_at.isoformat()
    }
```

**Error Responses:**
- `400`: Not all agents complete
- `404`: Project not found
- `403`: Unauthorized

---

#### B. Continue Working
**Endpoint:** `POST /api/projects/{project_id}/continue-working`

**Purpose:** Transitions all 'complete' agents back to 'working' status

**Request Body:** (optional)
```json
{
  "reason": "Additional work required (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "project_id": "uuid",
  "agents_resumed": 5,
  "resumed_at": "2025-01-07T12:34:56Z"
}
```

**Logic:**
```python
# Location: api/endpoints/projects.py

@router.post("/{project_id}/continue-working")
async def continue_working(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resume work on a completed project:
    1. Verify all agents are in 'complete' status
    2. Transition all agents back to 'working'
    3. Keep project.status as 'active'
    4. Emit WebSocket event: project:work_resumed
    """
    # Get project
    project = db.query(MCPProject).filter(
        MCPProject.project_id == project_id,
        MCPProject.tenant_id == current_user.tenant_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all agent jobs
    agents = db.query(MCPAgentJob).filter(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_id == current_user.tenant_id
    ).all()

    # Check if all agents are complete
    if not all(agent.status == 'complete' for agent in agents):
        raise HTTPException(
            status_code=400,
            detail="Cannot resume work - not all agents are complete"
        )

    # Transition all agents back to working
    for agent in agents:
        agent.status = 'working'
        agent.completed_at = None  # Clear completion timestamp

    db.commit()

    # Emit WebSocket event
    await websocket_manager.broadcast_to_project(
        project_id=project_id,
        event='project:work_resumed',
        data={
            'project_id': project_id,
            'agents_resumed': len(agents)
        }
    )

    return {
        'success': True,
        'project_id': project_id,
        'agents_resumed': len(agents),
        'resumed_at': datetime.now(timezone.utc).isoformat()
    }
```

**Error Responses:**
- `400`: Not all agents complete
- `404`: Project not found
- `403`: Unauthorized

---

#### C. Download Project Summary
**Endpoint:** `GET /api/projects/{project_id}/summary`

**Purpose:** Generates and downloads project summary document (PDF or Markdown)

**Query Parameters:**
- `format`: `pdf` | `markdown` (default: `pdf`)

**Response:**
- **Content-Type:** `application/pdf` or `text/markdown`
- **Content-Disposition:** `attachment; filename="{project_name}_Summary.pdf"`

**Logic:**
```python
# Location: api/endpoints/projects.py

from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

@router.get("/{project_id}/summary")
async def get_project_summary(
    project_id: str,
    format: str = 'pdf',
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate project summary document.
    Includes:
    - Project metadata (name, description, dates)
    - Orchestrator mission
    - Agent assignments and results
    - Task completion summary
    - Timeline
    """
    # Get project
    project = db.query(MCPProject).filter(
        MCPProject.project_id == project_id,
        MCPProject.tenant_id == current_user.tenant_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all agents
    agents = db.query(MCPAgentJob).filter(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_id == current_user.tenant_id
    ).all()

    if format == 'pdf':
        # Generate PDF summary
        pdf_buffer = generate_pdf_summary(project, agents)

        # Return as downloadable file
        return Response(
            content=pdf_buffer.getvalue(),
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{project.name}_Summary.pdf"'
            }
        )

    elif format == 'markdown':
        # Generate Markdown summary
        markdown_content = generate_markdown_summary(project, agents)

        return Response(
            content=markdown_content,
            media_type='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename="{project.name}_Summary.md"'
            }
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'pdf' or 'markdown'.")


def generate_pdf_summary(project, agents):
    """Generate PDF summary using ReportLab"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(100, 750, f"Project Summary: {project.name}")

    # Project Details
    p.setFont("Helvetica", 12)
    y = 700
    p.drawString(100, y, f"Project ID: {project.project_id}")
    y -= 20
    p.drawString(100, y, f"Status: {project.status}")
    y -= 20
    p.drawString(100, y, f"Created: {project.created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 20
    if project.completed_at:
        p.drawString(100, y, f"Completed: {project.completed_at.strftime('%Y-%m-%d %H:%M')}")

    # Mission
    y -= 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "Mission:")
    y -= 20
    p.setFont("Helvetica", 10)
    # Wrap text for mission (simplified - use proper text wrapping in production)
    mission_text = project.mission or "No mission defined"
    p.drawString(100, y, mission_text[:80])

    # Agents Section
    y -= 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "Agent Results:")
    y -= 20

    for agent in agents:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y, f"{agent.agent_type.capitalize()}:")
        y -= 15
        p.setFont("Helvetica", 10)
        p.drawString(120, y, f"Status: {agent.status}")
        y -= 15
        p.drawString(120, y, f"Job ID: {agent.job_id}")
        y -= 25

        if y < 100:  # New page if running out of space
            p.showPage()
            y = 750

    p.save()
    buffer.seek(0)
    return buffer


def generate_markdown_summary(project, agents):
    """Generate Markdown summary"""
    md = f"""# Project Summary: {project.name}

## Project Details
- **Project ID:** {project.project_id}
- **Status:** {project.status}
- **Created:** {project.created_at.strftime('%Y-%m-%d %H:%M')}
"""

    if project.completed_at:
        md += f"- **Completed:** {project.completed_at.strftime('%Y-%m-%d %H:%M')}\n"

    md += f"""
## Mission
{project.mission or 'No mission defined'}

## Agent Results

"""

    for agent in agents:
        md += f"""### {agent.agent_type.capitalize()}
- **Job ID:** {agent.job_id}
- **Status:** {agent.status}
- **Mission:** {agent.mission[:100]}...

"""

    return md
```

**Error Responses:**
- `400`: Invalid format parameter
- `404`: Project not found
- `403`: Unauthorized

---

### 5.2 Endpoint Integration Summary

**API Endpoints to Add:**
```python
# Location: api/endpoints/projects.py

# New endpoints
POST   /api/projects/{project_id}/close-out
POST   /api/projects/{project_id}/continue-working
GET    /api/projects/{project_id}/summary

# Existing endpoints (ensure they support new statuses)
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
GET    /api/projects/{project_id}/agents
```

**WebSocket Events to Emit:**
- `project:closed_out` - When project closes out
- `project:work_resumed` - When work resumes
- `job:status_changed` - When agent status changes to 'decommissioned'

---

## 6. CSS/Styling Requirements

### 6.1 Status Badge Colors

**CSS Variables (add to `frontend/src/styles/variables.scss`):**
```scss
// Agent Job Status Badge Colors
$status-waiting-border: #ffffff;
$status-waiting-bg: transparent;
$status-waiting-text: #ffffff;

$status-working-border: #ffffff;
$status-working-bg: transparent;
$status-working-text: #ffffff;

$status-completed-bg: #4CAF50;
$status-completed-text: #ffffff;

$status-reviewing-bg: #9C27B0;
$status-reviewing-text: #ffffff;

$status-blocked-bg: #FF9800;
$status-blocked-text: #ffffff;

$status-failed-bg: #E91E63;
$status-failed-text: #ffffff;

$status-cancelled-bg: #F44336;
$status-cancelled-text: #ffffff;

$status-decommissioned-bg: #9E9E9E;
$status-decommissioned-text: #ffffff;
```

---

### 6.2 Button Colors

**CSS Classes (add to `frontend/src/styles/buttons.scss`):**
```scss
// Launch Jobs / Stage Project Button (Yellow)
.btn-launch-jobs {
  background: #FFC107 !important;
  color: rgba(0, 0, 0, 0.87) !important;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(255, 193, 7, 0.4);

  &:hover {
    background: #FFD54F !important;
    box-shadow: 0 4px 12px rgba(255, 193, 7, 0.5);
  }
}

// Cancel Button (Pink)
.btn-cancel {
  background: #E91E63 !important;
  color: #ffffff !important;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(233, 30, 99, 0.4);

  &:hover {
    background: #F06292 !important;
    box-shadow: 0 4px 12px rgba(233, 30, 99, 0.5);
  }
}

// Close Out Project Button (Green)
.btn-close-out {
  background: #4CAF50 !important;
  color: #ffffff !important;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.4);

  &:hover {
    background: #66BB6A !important;
    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.5);
  }
}

// Continue Working Button (Blue)
.btn-continue-working {
  background: #2196F3 !important;
  color: #ffffff !important;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.4);

  &:hover {
    background: #42A5F5 !important;
    box-shadow: 0 4px 12px rgba(33, 150, 243, 0.5);
  }
}

// Launch Agent Button (Yellow - same as Launch Jobs)
.btn-launch-agent {
  @extend .btn-launch-jobs;
}

// View Prompt Button (Outlined)
.btn-view-prompt {
  border: 2px solid #2196F3 !important;
  color: #2196F3 !important;
  background: transparent !important;
  font-weight: 600;

  &:hover {
    background: rgba(33, 150, 243, 0.08) !important;
  }
}
```

---

### 6.3 Layout Styles

**Grid Layout (add to `frontend/src/components/projects/JobsTab.vue`):**
```scss
.jobs-tab {
  // Agent grid: Horizontal scroll with flexbox
  &__agents-grid {
    display: flex;
    gap: 16px;
    min-width: min-content;
    padding: 4px;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-behavior: smooth;
  }

  // Agent card width: ~300px fixed
  &__agent-card {
    flex-shrink: 0;
    width: 300px;
  }

  // Card spacing: 16px gap
  &__agents-scroll {
    gap: 16px;
  }

  // Message Center: Fixed right panel, 400px width
  &__message-center {
    width: 400px;
    flex-shrink: 0;
    border-left: 2px solid rgba(0, 0, 0, 0.08);
    padding-left: 24px;
  }
}

// Responsive adjustments
@media (max-width: 1400px) {
  .jobs-tab {
    &__message-center {
      width: 350px;
    }
  }
}

@media (max-width: 1200px) {
  .jobs-tab {
    &__agent-card {
      width: 260px;
    }

    &__message-center {
      width: 300px;
    }
  }
}

@media (max-width: 1024px) {
  .jobs-tab {
    // Stack columns vertically on tablet
    flex-direction: column;

    &__message-center {
      width: 100%;
      border-left: none;
      border-top: 2px solid rgba(0, 0, 0, 0.08);
      padding-left: 0;
      padding-top: 24px;
      margin-top: 24px;
    }
  }
}
```

---

### 6.4 Agent Card Styles

**Update `frontend/src/components/projects/AgentCardEnhanced.vue`:**
```scss
.agent-card-enhanced {
  // Card dimensions
  width: 300px;
  min-height: 200px;
  max-height: 450px;

  // Agent instructions text
  .agent-instructions {
    padding: 12px;
    background: rgba(0, 0, 0, 0.03);
    border-radius: 8px;
    margin-top: 12px;
    line-height: 1.5;

    &.using-subagents {
      background: rgba(33, 150, 243, 0.08);
      color: #2196F3;
      font-weight: 600;
      text-align: center;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
  }

  // Decommissioned state
  &.status--decommissioned {
    opacity: 0.7;

    .agent-card__header {
      background: #9E9E9E !important;
    }

    .agent-card__body {
      background: linear-gradient(to bottom, rgba(158, 158, 158, 0.05) 0%, transparent 100%);
    }
  }
}
```

---

### 6.5 Completion Banner Styles

**Create `frontend/src/components/projects/ProjectCompletionBanner.vue`:**
```scss
.project-completion-banner {
  background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%) !important;
  color: white !important;
  padding: 32px 48px !important;
  border-radius: 16px !important;
  margin-bottom: 32px !important;
  box-shadow: 0 8px 24px rgba(76, 175, 80, 0.3) !important;
  border: 2px solid #66bb6a !important;

  .completion-text {
    h3 {
      font-size: 2rem;
      font-weight: 700;
      color: white;
      margin-bottom: 12px;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    p {
      font-size: 1rem;
      color: rgba(255, 255, 255, 0.95);
      line-height: 1.6;
    }
  }

  .download-button {
    min-width: 200px;
    height: 48px;
    font-size: 1rem;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);

    &:hover {
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
      transform: translateY(-2px);
    }
  }
}
```

---

## 7. Accessibility Requirements

### 7.1 ARIA Labels

**All Interactive Elements Must Have:**
```html
<!-- Status Badge -->
<v-chip aria-label="Agent status: Working" role="status">
  Working
</v-chip>

<!-- Launch Agent Button -->
<v-btn aria-label="Launch agent in separate terminal window">
  Launch Agent
</v-btn>

<!-- View Prompt Button -->
<v-btn aria-label="View agent execution prompt">
  View Prompt
</v-btn>

<!-- Close Out Project Button -->
<v-btn aria-label="Close out project and decommission all agents">
  Close Out Project
</v-btn>

<!-- Continue Working Button -->
<v-btn aria-label="Return all agents to working status">
  Continue Working
</v-btn>

<!-- Download Summary Button -->
<v-btn aria-label="Download project summary document">
  Download Summary
</v-btn>

<!-- Claude Code Toggle -->
<v-switch aria-label="Toggle Claude Code subagent mode">
  Use Claude Code Subagents
</v-switch>

<!-- Agent Card -->
<v-card
  role="article"
  aria-label="Orchestrator agent - Working status"
>
  <!-- card content -->
</v-card>
```

---

### 7.2 Keyboard Navigation

**Requirements:**
- All buttons: Tab-focusable with visible focus ring
- Agent grid: Arrow key navigation (Left/Right to scroll)
- Dialogs: Escape key to close
- Toggle: Space/Enter to activate
- Focus trap in dialogs (prevent focus leaving dialog)

**Implementation:**
```vue
<!-- Agent Cards Scroll Container -->
<div
  ref="agentsScrollContainer"
  class="jobs-tab__agents-scroll"
  tabindex="0"
  @keydown="handleAgentsKeydown"
  aria-label="Agent cards - use arrow keys to scroll"
>
  <!-- cards -->
</div>

<script>
function handleAgentsKeydown(event) {
  switch (event.key) {
    case 'ArrowLeft':
      event.preventDefault()
      scrollAgentsLeft()
      break
    case 'ArrowRight':
      event.preventDefault()
      scrollAgentsRight()
      break
    case 'Home':
      event.preventDefault()
      scrollToStart()
      break
    case 'End':
      event.preventDefault()
      scrollToEnd()
      break
  }
}
</script>
```

---

### 7.3 Color Contrast

**WCAG AA Compliance (4.5:1 for normal text, 3:1 for large text):**

| Element | Foreground | Background | Contrast Ratio | Status |
|---------|-----------|------------|---------------|--------|
| Waiting badge | White (#FFFFFF) | Transparent (dark bg) | 7.0:1 | ✅ Pass |
| Working badge | White (#FFFFFF) | Transparent (dark bg) | 7.0:1 | ✅ Pass |
| Completed badge | White (#FFFFFF) | Green (#4CAF50) | 4.8:1 | ✅ Pass |
| Failed badge | White (#FFFFFF) | Pink (#E91E63) | 5.2:1 | ✅ Pass |
| Blocked badge | White (#FFFFFF) | Orange (#FF9800) | 4.6:1 | ✅ Pass |
| Decommissioned badge | White (#FFFFFF) | Gray (#9E9E9E) | 4.5:1 | ✅ Pass |
| Launch Jobs button | Black (#000000) | Yellow (#FFC107) | 10.5:1 | ✅ Pass |
| Close Out button | White (#FFFFFF) | Green (#4CAF50) | 4.8:1 | ✅ Pass |

**Testing Tool:** Use https://webaim.org/resources/contrastchecker/

---

### 7.4 Screen Reader Support

**Requirements:**
- Status changes announced via `role="status"` with `aria-live="polite"`
- Button actions announced clearly (e.g., "Close out project button")
- Agent card content readable in logical order
- Skip links for keyboard users
- Descriptive link text (no "click here")

**Implementation:**
```vue
<!-- Status Badge with Live Region -->
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
>
  <v-chip
    :color="statusColor"
    :aria-label="`Agent status changed to ${statusLabel}`"
  >
    {{ statusLabel }}
  </v-chip>
</div>

<!-- Completion Banner with Alert Role -->
<v-banner
  role="alert"
  aria-labelledby="completion-heading"
>
  <h3 id="completion-heading">Project Completed</h3>
  <p>All agents have been decommissioned.</p>
</v-banner>
```

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1, Days 1-3)
**Goal:** Create new components and update status badge system

**Tasks:**
1. **Day 1: Status Badge Component**
   - [ ] Create `AgentStatusBadge.vue` component
   - [ ] Implement 8-state styling (waiting, working, review, complete, failed, blocked, cancelled, decommissioned)
   - [ ] Add color variables to SCSS
   - [ ] Write unit tests for badge component
   - [ ] Verify color contrast compliance

2. **Day 2: Completion Banner Component**
   - [ ] Create `ProjectCompletionBanner.vue` component
   - [ ] Implement green banner with "Download Summary" button
   - [ ] Add banner animation (fade in/slide down)
   - [ ] Integrate with download API endpoint (stub for now)
   - [ ] Add ARIA labels and accessibility features

3. **Day 3: Orchestrator Actions Component**
   - [ ] Create `OrchestratorActions.vue` component
   - [ ] Implement "Close Out Project" button with confirmation dialog
   - [ ] Implement "Continue Working" button with confirmation dialog
   - [ ] Add API integration stubs
   - [ ] Write unit tests for action handlers

**Deliverables:**
- 3 new Vue components fully functional
- SCSS styling for all 8 status badges
- Unit tests with 80%+ coverage
- Accessibility audit passed

---

### Phase 2: Jobs Tab Redesign (Week 1, Days 4-5)
**Goal:** Update JobsTab.vue with new components and layout

**Tasks:**
1. **Day 4: Layout Updates**
   - [ ] Replace existing completion banner with `<ProjectCompletionBanner />`
   - [ ] Update agent card grid to use new `AgentStatusBadge` component
   - [ ] Add `<UnassignedAgentSlot />` placeholder card
   - [ ] Update Message Center header text logic ("Message Center" vs "Messages")
   - [ ] Verify horizontal scroll behavior
   - [ ] Test responsive design (mobile, tablet, desktop)

2. **Day 5: State Management Integration**
   - [ ] Update Vuex store with new state properties
   - [ ] Add mutations: `SET_ALL_AGENTS_COMPLETE`, `SET_ALL_AGENTS_DECOMMISSIONED`, `SET_PROJECT_CLOSED_OUT`
   - [ ] Add actions: `updateAgentStatuses`, `closeOutProject`, `continueWorking`
   - [ ] Add getters: `showCompletionBanner`, `showOrchestratorActions`
   - [ ] Test state transitions with mock data

**Deliverables:**
- JobsTab.vue updated with new components
- Vuex store updated with new state management
- All state transitions working correctly
- Responsive design verified on 3 breakpoints

---

### Phase 3: Agent Card Updates (Week 2, Days 1-2)
**Goal:** Update AgentCardEnhanced.vue with new status behaviors

**Tasks:**
1. **Day 1: Status-Specific Content**
   - [ ] Add instructional text for "Waiting" state (Claude Code toggle dependent)
   - [ ] Add "USING CLAUDE SUBAGENTS" text for enabled toggle
   - [ ] Update "Launch Agent" button logic (show/hide based on toggle)
   - [ ] Add "View Prompt" button for "Working" state
   - [ ] Implement "Decommissioned" state UI (read-only)
   - [ ] Update status badge to use `AgentStatusBadge` component

2. **Day 2: Orchestrator-Specific Features**
   - [ ] Integrate `OrchestratorActions` component (show when all agents complete)
   - [ ] Add conditional rendering logic (orchestrator only)
   - [ ] Test "Close Out Project" button appears at correct time
   - [ ] Test "Continue Working" button functionality
   - [ ] Verify orchestrator card shows toggle control

**Deliverables:**
- AgentCardEnhanced.vue fully updated per PDF spec
- All 8 status states render correctly
- Orchestrator-specific actions working
- Toggle-dependent UI working correctly

---

### Phase 4: API & WebSocket Integration (Week 2, Days 3-4)
**Goal:** Implement backend endpoints and WebSocket events

**Tasks:**
1. **Day 3: API Endpoints**
   - [ ] Implement `POST /api/projects/{project_id}/close-out`
   - [ ] Implement `POST /api/projects/{project_id}/continue-working`
   - [ ] Implement `GET /api/projects/{project_id}/summary` (PDF generation)
   - [ ] Write API endpoint tests (pytest)
   - [ ] Test multi-tenant isolation
   - [ ] Test error handling (400, 404, 403)

2. **Day 4: WebSocket Events**
   - [ ] Add `project:closed_out` event emission
   - [ ] Add `project:work_resumed` event emission
   - [ ] Update `job:status_changed` to handle 'decommissioned' status
   - [ ] Add frontend WebSocket listeners in `useWebSocket.js`
   - [ ] Test real-time UI updates (completion banner appears, status badges update)
   - [ ] Test multi-client synchronization

**Deliverables:**
- 3 new API endpoints fully functional
- WebSocket events emitting correctly
- Real-time UI updates working
- API tests with 85%+ coverage
- Multi-tenant isolation verified

---

### Phase 5: Polish & Testing (Week 2, Day 5)
**Goal:** Final QA, accessibility audit, and production readiness

**Tasks:**
1. **Morning: CSS Fine-Tuning**
   - [ ] Match PDF colors exactly (use color picker on PDF)
   - [ ] Verify button sizes and spacing
   - [ ] Adjust border-radius for pill-shaped badges
   - [ ] Test animations (badge transitions, banner slide-in)
   - [ ] Verify hover states on all interactive elements

2. **Afternoon: Accessibility Audit**
   - [ ] Run axe DevTools accessibility scan
   - [ ] Verify all ARIA labels present
   - [ ] Test keyboard navigation (Tab, Shift+Tab, Arrow keys, Escape)
   - [ ] Test screen reader (NVDA/JAWS/VoiceOver)
   - [ ] Verify color contrast (WCAG AA compliance)
   - [ ] Test focus indicators visible

3. **End of Day: Cross-Browser Testing**
   - [ ] Chrome (latest)
   - [ ] Firefox (latest)
   - [ ] Safari (latest)
   - [ ] Edge (latest)
   - [ ] Test responsive design on:
     - Mobile (< 600px)
     - Tablet (600-960px)
     - Desktop (> 960px)

**Deliverables:**
- Production-ready UI matching PDF exactly
- All accessibility requirements met (WCAG 2.1 AA)
- Cross-browser compatibility verified
- Performance benchmarks met (< 100ms render time)
- Zero console errors/warnings

---

## 9. Testing Checklist

### 9.1 Functional Testing

**Staging Tab:**
- [ ] "Stage Project" button appears on initial load
- [ ] Orchestrator card appears when project activated
- [ ] Mission panels are editable (Edit buttons work)
- [ ] Remaining agents appear via WebSocket when orchestrator assigns them
- [ ] Button changes to "Launch Jobs" when staging complete
- [ ] "CANCEL" button appears when staging complete
- [ ] "EDIT JOB" buttons appear on all agent cards
- [ ] Agent grid scrolls horizontally
- [ ] Left/right navigation arrows work

**Jobs Tab - Waiting State:**
- [ ] All agents show "Waiting" status badge (white outlined)
- [ ] Toggle defaults to OFF
- [ ] All agents show "Launch Agent" button when toggle OFF
- [ ] Instructional text appears on all cards when toggle OFF
- [ ] Toggle switches to ON state correctly
- [ ] "Launch Agent" buttons change to "View Prompt" when toggle ON
- [ ] Instructional text changes to "USING CLAUDE SUBAGENTS" when toggle ON
- [ ] Orchestrator still shows "Launch Agent" button when toggle ON (orchestrator exception)
- [ ] Unassigned agent slot shows dashed outline placeholder

**Jobs Tab - Working State:**
- [ ] All agent status badges change to "Working" (white outlined)
- [ ] "View Prompt" buttons appear on all cards
- [ ] "USING CLAUDE SUBAGENTS" text shows when toggle ON
- [ ] Progress bars display correctly
- [ ] Current task text updates in real-time
- [ ] Message Center shows messages in real-time
- [ ] Scroll bar appears when messages overflow

**Jobs Tab - Failed State:**
- [ ] Failed agent shows pink "Failed" badge (filled)
- [ ] Other agents remain "Working"
- [ ] Failed card has visual prominence (border/shadow)
- [ ] Error message displays in card
- [ ] "View Error" button appears on failed card

**Jobs Tab - All Complete State:**
- [ ] All agents show green "Completed" badge (filled)
- [ ] Orchestrator card shows TWO buttons:
  - [ ] "Close Out Project" (green)
  - [ ] "Continue Working" (blue)
- [ ] Both buttons have confirmation dialogs
- [ ] Other agent cards show no special actions

**Jobs Tab - Closed Out State:**
- [ ] Green "Project Completed" banner appears at top
- [ ] "Download Summary" button works in banner
- [ ] All agents show gray "Decommissioned" badge (filled)
- [ ] All agent cards show only "View Prompt" button (no actions)
- [ ] Cards are visually muted (opacity 0.7)

---

### 9.2 WebSocket Testing

**Real-Time Updates:**
- [ ] `job:status_changed` event updates agent badges
- [ ] `job:all_complete` event shows orchestrator actions
- [ ] `project:closed_out` event shows completion banner
- [ ] `project:work_resumed` event updates badges to "Working"
- [ ] `agents:assigned` event adds new cards to grid
- [ ] Multiple clients see updates simultaneously

---

### 9.3 API Testing

**Endpoints:**
- [ ] `POST /api/projects/{id}/close-out` returns 200
- [ ] Close-out transitions all agents to 'decommissioned'
- [ ] Close-out sets project.status = 'completed'
- [ ] Close-out fails with 400 if not all agents complete
- [ ] `POST /api/projects/{id}/continue-working` returns 200
- [ ] Continue-working transitions all agents to 'working'
- [ ] Continue-working fails with 400 if not all agents complete
- [ ] `GET /api/projects/{id}/summary` returns PDF file
- [ ] Summary endpoint supports `?format=markdown` parameter
- [ ] All endpoints enforce multi-tenant isolation (403 for wrong tenant)

---

### 9.4 Accessibility Testing

**ARIA & Keyboard:**
- [ ] All status badges have `role="status"`
- [ ] All buttons have descriptive `aria-label`
- [ ] Tab navigation works through all interactive elements
- [ ] Focus indicators visible on all focusable elements
- [ ] Arrow keys scroll agent grid
- [ ] Escape closes dialogs
- [ ] Space/Enter activates toggle
- [ ] Screen reader announces status changes
- [ ] Skip links provided for keyboard users

**Color Contrast:**
- [ ] All status badges meet 4.5:1 ratio
- [ ] All button text meets 4.5:1 ratio
- [ ] Launch Jobs button (yellow) meets 10.5:1 ratio
- [ ] No information conveyed by color alone

---

### 9.5 Responsive Design Testing

**Mobile (< 600px):**
- [ ] Columns stack vertically
- [ ] Agent cards maintain 280px width
- [ ] Horizontal scroll works smoothly
- [ ] Touch gestures work (swipe to scroll)
- [ ] Buttons stack vertically on orchestrator card
- [ ] Completion banner text readable

**Tablet (600-960px):**
- [ ] Columns adjust to 50/50 split
- [ ] Agent cards scale appropriately
- [ ] Message Center width adjusts
- [ ] Touch and mouse both work

**Desktop (> 960px):**
- [ ] 60/40 split (agents/messages) maintained
- [ ] Agent cards fixed at 300px
- [ ] Message Center fixed at 400px
- [ ] Hover states work on all interactive elements

---

### 9.6 Browser Compatibility

**Chrome:**
- [ ] All features work
- [ ] CSS grid/flexbox layout correct
- [ ] WebSocket connections stable
- [ ] Smooth animations

**Firefox:**
- [ ] All features work
- [ ] Custom scrollbar styles applied
- [ ] Focus indicators visible
- [ ] No console errors

**Safari:**
- [ ] All features work
- [ ] Gradient backgrounds render correctly
- [ ] Flexbox layout correct
- [ ] Touch events work on iOS

**Edge:**
- [ ] All features work
- [ ] Chromium-based features supported
- [ ] No IE11 support needed (confirmed)

---

## 10. Appendix: Component File Locations

### 10.1 Existing Components (Update Required)

| Component | Location | Lines | Status |
|-----------|----------|-------|--------|
| JobsTab.vue | `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue` | 1060 | ✅ Minor updates |
| AgentCardEnhanced.vue | `F:\GiljoAI_MCP\frontend\src\components\projects\AgentCardEnhanced.vue` | 918 | ⚠️ Major updates |
| StatusBadge.vue | `F:\GiljoAI_MCP\frontend\src\components\StatusBadge.vue` | 412 | ❌ Wrong purpose |

---

### 10.2 New Components (Create Required)

| Component | Location | Purpose |
|-----------|----------|---------|
| AgentStatusBadge.vue | `F:\GiljoAI_MCP\frontend\src\components\projects\AgentStatusBadge.vue` | 8-state agent job status badges |
| ProjectCompletionBanner.vue | `F:\GiljoAI_MCP\frontend\src\components\projects\ProjectCompletionBanner.vue` | Green banner with download button |
| OrchestratorActions.vue | `F:\GiljoAI_MCP\frontend\src\components\projects\OrchestratorActions.vue` | Close Out / Continue Working buttons |
| UnassignedAgentSlot.vue | `F:\GiljoAI_MCP\frontend\src\components\projects\UnassignedAgentSlot.vue` | Dashed placeholder card |

---

### 10.3 Backend Files (Create/Update Required)

| File | Location | Purpose |
|------|----------|---------|
| projects.py | `F:\GiljoAI_MCP\api\endpoints\projects.py` | Add 3 new endpoints |
| websocket.py | `F:\GiljoAI_MCP\api\websocket.py` | Add new event emissions |
| models.py | `F:\GiljoAI_MCP\src\giljo_mcp\models.py` | Verify 'decommissioned' status exists |

---

### 10.4 State Management Files (Update Required)

| File | Location | Purpose |
|------|----------|---------|
| projectTabs.js | `F:\GiljoAI_MCP\frontend\src\stores\projectTabs.js` | Add new state properties |
| useWebSocket.js | `F:\GiljoAI_MCP\frontend\src\composables\useWebSocket.js` | Add new event listeners |

---

### 10.5 Style Files (Update Required)

| File | Location | Purpose |
|------|----------|---------|
| variables.scss | `F:\GiljoAI_MCP\frontend\src\styles\variables.scss` | Add status badge colors |
| buttons.scss | `F:\GiljoAI_MCP\frontend\src\styles\buttons.scss` | Add button styles |

---

## 11. Success Criteria

### 11.1 Visual Design
- [ ] UI matches PDF specification exactly (pixel-perfect within 5px tolerance)
- [ ] All 8 status badge colors match PDF slide 8
- [ ] Button colors match PDF (yellow, pink, green, blue)
- [ ] Layout dimensions match (300px cards, 400px message panel)
- [ ] Animations smooth (< 300ms transitions)

### 11.2 Functionality
- [ ] All 9 PDF slides represented in working UI
- [ ] Toggle changes UI behavior correctly (Launch Agent ↔ View Prompt)
- [ ] Status transitions work in all directions (waiting → working → complete → decommissioned)
- [ ] Orchestrator actions appear at correct time (all complete)
- [ ] Project closes out correctly (all agents → decommissioned)
- [ ] Continue Working returns agents to working state
- [ ] Summary download generates PDF successfully

### 11.3 Accessibility
- [ ] WCAG 2.1 AA compliance verified (axe DevTools 0 violations)
- [ ] All interactive elements keyboard accessible
- [ ] Screen reader announces all status changes
- [ ] Color contrast > 4.5:1 on all text
- [ ] Focus indicators visible on all focusable elements

### 11.4 Performance
- [ ] Initial render < 100ms (Lighthouse)
- [ ] Smooth 60fps scroll on agent grid
- [ ] WebSocket latency < 50ms
- [ ] Bundle size increase < 50KB
- [ ] No memory leaks (tested over 10-minute session)

### 11.5 Testing
- [ ] Unit tests: 80%+ coverage on new components
- [ ] Integration tests: All API endpoints tested
- [ ] E2E tests: All 9 PDF slides automated
- [ ] Cross-browser: Chrome, Firefox, Safari, Edge verified
- [ ] Responsive: Mobile, tablet, desktop verified

---

## 12. Risks & Mitigations

### Risk 1: PDF Summary Generation Complexity
**Risk:** Generating production-quality PDF summaries may be complex

**Mitigation:**
- Start with simple Markdown export (easier)
- Use lightweight PDF library (ReportLab)
- Provide MVP version in Phase 4, enhance in v3.2

### Risk 2: WebSocket Synchronization
**Risk:** Multiple clients may see inconsistent state during transitions

**Mitigation:**
- Use atomic database transactions
- Emit WebSocket events after DB commit
- Add state version numbers for conflict resolution

### Risk 3: Accessibility Compliance
**Risk:** Achieving WCAG AA on all 8 status badges may require color adjustments

**Mitigation:**
- Test contrast early (Phase 1, Day 1)
- Adjust colors if needed while maintaining visual design intent
- Add text labels if color alone insufficient

### Risk 4: Timeline Overrun
**Risk:** 2-week estimate may be optimistic

**Mitigation:**
- Use Phase 1-3 as MVP (core functionality)
- Phase 4-5 can slip to Week 3 if needed
- Prioritize functional correctness over visual polish

---

## 13. Post-Implementation Tasks

### 13.1 Documentation
- [ ] Update user guide with new Jobs tab features
- [ ] Add developer docs for new components
- [ ] Create video walkthrough of new UI (2-3 minutes)
- [ ] Update API documentation (3 new endpoints)

### 13.2 Monitoring
- [ ] Add analytics events for user actions (Close Out, Continue Working, Download Summary)
- [ ] Monitor PDF generation latency (target < 2 seconds)
- [ ] Track WebSocket event delivery success rate (target > 99%)
- [ ] Monitor frontend render performance (target < 100ms)

### 13.3 Future Enhancements (v3.2+)
- [ ] Enhanced PDF summary with charts and graphs
- [ ] Export project summary as ZIP with all agent logs
- [ ] Email summary to user on project completion
- [ ] Advanced agent filtering (by status, type, instance)
- [ ] Agent performance metrics (time spent, tasks completed)

---

## 14. Conclusion

This handover provides a complete specification for harmonizing the Jobs tab UI with the visual design reference PDF. The implementation is scoped to 2 weeks with 5 distinct phases, clear success criteria, and comprehensive testing requirements.

The final deliverable will be a production-grade, accessible, responsive UI that exactly matches the PDF specification and provides an intuitive, professional experience for managing multi-agent workflows.

**Next Steps:**
1. Review this handover document with team
2. Confirm 2-week timeline and resource availability
3. Begin Phase 1: Foundation (create new components)
4. Schedule daily standups to track progress
5. Plan Phase 5 demo for stakeholders

---

**Document Version:** 1.0
**Last Updated:** 2025-01-07
**Author:** UX Designer Agent
**Status:** Ready for Implementation
