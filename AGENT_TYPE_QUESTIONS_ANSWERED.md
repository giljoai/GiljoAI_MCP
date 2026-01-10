# Agent Type Frontend Usage - Questions Answered

**Research Date**: 2026-01-10
**Codebase**: GiljoAI MCP Frontend (Vue 3)
**Scope**: Comprehensive search across components, stores, services, and utilities

---

## Question 1: Is agent_type used to determine badge colors?

### Answer: YES - EXTENSIVELY

`agent_type` directly determines avatar colors in multiple components. There are **THREE SEPARATE COLOR MAPPING IMPLEMENTATIONS** (inconsistency alert!):

### Implementation 1: JobsTab.vue (Hex Colors)
**File**: `frontend/src/components/projects/JobsTab.vue`
**Lines**: 571-587
**Function**: `getAgentColor(agentType)`

```javascript
function getAgentColor(agentType) {
  const colors = {
    orchestrator: '#D4A574',  // Tan/Beige
    analyzer: '#E74C3C',      // Red
    implementer: '#3498DB',   // Blue
    tester: '#FFC300',        // Yellow
    reviewer: '#9B59B6',      // Purple
    documenter: '#27AE60',    // Green
    researcher: '#27AE60',    // Green
  }
  return colors[agentType] || '#999'
}
```

**Used in**:
- Line 26: `<v-avatar :color="getAgentColor(agent.agent_type)">`
- Line 27: `{{ getAgentAbbr(agent.agent_type) }}` (avatar initials)

### Implementation 2: LaunchTab.vue (Hex Colors - DUPLICATE)
**File**: `frontend/src/components/projects/LaunchTab.vue`
**Lines**: 285-296
**Function**: `getAgentColor(agentType)`

```javascript
const getAgentColor = (agentType) => {
  const colors = {
    orchestrator: '#D4A574',  // IDENTICAL to JobsTab
    analyzer: '#E74C3C',
    implementer: '#3498DB',
    // ... (same mapping)
  }
  return colors[agentType] || '#999'
}
```

**Problem**: Code duplication - if colors change, must update in 2 places!

**Used in**:
- Line 122: `<div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">`

### Implementation 3: useAgentData.js (Vuetify Colors - INCONSISTENT)
**File**: `frontend/src/composables/useAgentData.js`
**Lines**: 97-106
**Function**: `getAgentTypeColor(agentType)`

```javascript
const getAgentTypeColor = (agentType) => {
  const colors = {
    orchestrator: 'orange',     // DIFFERENT from hex
    analyzer: 'red',            // Vuetify color names
    implementer: 'blue',
    tester: 'yellow',
    reviewer: 'purple',
  }
  return colors[agentType] || 'grey'
}
```

**Problem**: Different color scheme than JobsTab/LaunchTab!

**Used in**:
- `AgentTableView.vue` Line 14: `<v-avatar :color="getAgentTypeColor(item.agent_type)">`
- `AgentCardGrid.vue` (imported from composable)

### Summary: Color Badge Usage

| Component | Color Type | Colors Consistent? |
|-----------|-----------|-------------------|
| JobsTab | Hex (#D4A574) | Yes, internal |
| LaunchTab | Hex (#D4A574) | Yes, but DUPLICATES JobsTab |
| AgentTableView | Vuetify (orange) | No, different from JobsTab/LaunchTab |
| AgentCardGrid | Vuetify (orange) | No, different from JobsTab/LaunchTab |

**Critical Finding**: Different components display **different colors** for the same agent type!
- Orchestrator in JobsTab: `#D4A574` (tan)
- Orchestrator in AgentTableView: `orange` (Vuetify)

---

## Question 2: Is it used for avatar generation?

### Answer: YES - EVERY AGENT DISPLAY

Avatar generation uses both **color** AND **initials/abbreviations** derived from `agent_type`.

### Component 1: JobsTab.vue
**File**: `frontend/src/components/projects/JobsTab.vue`
**Lines**: 23-37

```vue
<td class="agent-type-cell">
  <!-- Color from agent_type -->
  <v-avatar :color="getAgentColor(agent.agent_type)" size="32">
    <!-- Initials from agent_type -->
    <span class="avatar-text">{{ getAgentAbbr(agent.agent_type) }}</span>
  </v-avatar>

  <!-- Display agent_type in secondary label -->
  <div class="agent-info">
    <span>{{ agent.agent_name || agent.agent_type }}</span>
    <span v-if="agent.agent_name && agent.agent_name !== agent.agent_type">
      {{ agent.agent_type }}
    </span>
  </div>
</td>
```

**Abbreviations mapping** (Lines 588-599):
```javascript
function getAgentAbbr(agentType) {
  const abbrs = {
    orchestrator: 'OR',
    analyzer: 'AN',
    implementer: 'IM',
    tester: 'TE',
    reviewer: 'RV',
    documenter: 'DO',
    researcher: 'RE',
  }
  return abbrs[agentType] || agentType.substring(0, 2).toUpperCase()
}
```

### Component 2: LaunchTab.vue
**File**: `frontend/src/components/projects/LaunchTab.vue`
**Lines**: 118-127

```vue
<div class="agent-slim-card" :data-agent-type="agent.agent_type">
  <!-- Color from agent_type -->
  <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
    <!-- Initials from agent_type -->
    {{ getAgentInitials(agent.agent_type) }}
  </div>

  <!-- Display agent_type as name -->
  <span class="agent-name">{{ agent.agent_type?.toUpperCase() || '' }}</span>
</div>
```

**Initials mapping** (Lines 302-315):
```javascript
const getAgentInitials = (agentType) => {
  if (!agentType) return '??'
  if (agentType === 'orchestrator') return 'OR'
  if (agentType === 'analyzer') return 'AN'
  if (agentType === 'implementer') return 'IM'
  if (agentType === 'implementor') return 'IM'
  if (agentType === 'tester') return 'TE'
  if (agentType === 'reviewer') return 'RV'
  if (agentType === 'documenter') return 'DO'
  if (agentType === 'researcher') return 'RE'
  return agentType.substring(0, 2).toUpperCase()
}
```

### Component 3: AgentTableView.vue
**File**: `frontend/src/components/orchestration/AgentTableView.vue`
**Lines**: 12-26

```vue
<template #item.agent_type="{ item }">
  <div class="d-flex align-center">
    <!-- Color from getAgentTypeColor() which uses agent_type -->
    <v-avatar :color="getAgentTypeColor(item.agent_type)" size="32" class="mr-2">
      <!-- Abbreviation from agent_type -->
      <span>{{ getAgentAbbreviation(item.agent_type) }}</span>
    </v-avatar>

    <!-- Agent display name or type -->
    <span>{{ item.agent_name || item.agent_type }}</span>

    <!-- Secondary agent type label -->
    <span v-if="item.agent_name && item.agent_name !== item.agent_type">
      {{ item.agent_type }}
    </span>
  </div>
</template>
```

**Abbreviation mapping** (from `useAgentData.js` Lines 115-124):
```javascript
const getAgentAbbreviation = (agentType) => {
  const abbr = {
    orchestrator: 'Or',
    analyzer: 'An',
    implementer: 'Im',
    tester: 'Te',
    reviewer: 'Re',
  }
  return abbr[agentType] || agentType.substring(0, 2).toUpperCase()
}
```

### Component 4: AgentCard.vue
**File**: `frontend/src/components/AgentCard.vue`
**Lines**: 5, 15, 447

```vue
<v-card :class="`agent-card--${agent.agent_type}`" :style="cardStyles">
  <div class="agent-card__header" :style="headerStyles">
    <!-- Agent type label in header -->
    <span>{{ agentTypeLabel }}</span>
  </div>
</v-card>
```

**Computed color property**:
```javascript
const agentColor = computed(() => getAgentColor(props.agent.agent_type))
const agentTypeLabel = computed(() => agentColor.value.name)
```

### Avatar Generation Summary

**Every agent display requires**:
1. Color lookup from agent_type
2. Abbreviation lookup from agent_type
3. CSS class or style binding using agent_type

**Impact**: If agent_type is missing/wrong, avatars are incomplete or broken.

---

## Question 3: Is it used in any filtering/sorting logic?

### Answer: YES - CRITICAL TO DATA FLOW

### Sorting Logic

#### Sorting 1: Priority Sorting (agentJobsStore.js)
**File**: `frontend/src/stores/agentJobsStore.js`
**Lines**: 107-111

```javascript
// Orchestrators must appear FIRST in list
const aIsOrchestrator = a.agent_type === 'orchestrator' ? 0 : 1
const bIsOrchestrator = b.agent_type === 'orchestrator' ? 0 : 1
if (aIsOrchestrator !== bIsOrchestrator) return aIsOrchestrator - bIsOrchestrator

// Then sort by agent_type alphabetically
return (a.agent_type || '').localeCompare(b.agent_type || '')
```

**Effect**: Orchestrators ALWAYS appear first, regardless of other factors.

**Used in**: Agent list display, ensuring orchestrators are immediately visible.

#### Sorting 2: Composable Sorting (useAgentData.js)
**File**: `frontend/src/composables/useAgentData.js`
**Lines**: 45-47

```javascript
// Secondary sort: orchestrator first within same status/timestamp
if (a.agent_type === 'orchestrator') return -1
if (b.agent_type === 'orchestrator') return 1

// Tertiary sort: alphabetical by name
return (a.agent_name || '').localeCompare(b.agent_name || '')
```

**Effect**: Same as above - orchestrators prioritized.

**Used in**: Shared logic for AgentCardGrid and AgentTableView.

### Filtering Logic

#### Filtering 1: Type-Based Filtering (agentJobs.js)
**File**: `frontend/src/stores/agentJobs.js`
**Lines**: 30, 55-58

```javascript
// Filter configuration
tableFilters.value = {
  status: [],
  health_status: [],
  agent_type: [],  // User can select which agent types to show
  has_unread: null,
}

// Apply filtering
if (tableFilters.value.agent_type.length) {
  filtered = filtered.filter((a) =>
    tableFilters.value.agent_type.includes(a.agent_type),
  )
}
```

**Effect**: Users can hide/show specific agent types from table.

#### Filtering 2: Orchestrator vs Non-Orchestrator (LaunchTab.vue)
**File**: `frontend/src/components/projects/LaunchTab.vue`
**Lines**: 239-252

```javascript
// Separate orchestrators from other agents
const nonOrchestratorAgents = computed(() => {
  return sortedJobs.value.filter((agent) => agent.agent_type !== 'orchestrator')
})

// Find orchestrator jobs separately
const orchestrators = sortedJobs.value
  .filter((agent) => agent.agent_type === 'orchestrator')
  .sort((a, b) => (b.instance_number || 0) - (a.instance_number || 0))
```

**Effect**: UI displays orchestrators and non-orchestrators in different sections.

**Consequence if broken**: UI layout breaks, orchestrators disappear, agents mixed up.

### Sorting/Filtering Impact Summary

| Logic | File | Purpose | Consequence if Broken |
|-------|------|---------|----------------------|
| Orchestrator priority sort | agentJobsStore.js | Orchestrators always first | Wrong agent order displayed |
| Type-based filter | agentJobs.js | Users can filter by type | Filter dropdown broken |
| Orchestrator separation | LaunchTab.vue | Show orchestrators separately | UI layout breaks |
| Type alphabet sort | agentJobsStore.js | Secondary sort by agent_type | Agents not in order |

---

## Question 4: What components display agent_type?

### Answer: 8+ Components (Direct Display)

#### 1. JobsTab.vue (MAIN)
**File**: `frontend/src/components/projects/JobsTab.vue`
- **Lines**: 23, 26-27, 30, 35
- **Display**: Agent avatar, initials, agent type label
- **Purpose**: Main status table for job monitoring
- **Critical**: Yes - users see this daily

#### 2. LaunchTab.vue (MAIN)
**File**: `frontend/src/components/projects/LaunchTab.vue`
- **Lines**: 120-126
- **Display**: Agent slim card with avatar and name
- **Purpose**: Orchestrator/agent launch interface
- **Critical**: Yes - users interact with this

#### 3. AgentTableView.vue
**File**: `frontend/src/components/orchestration/AgentTableView.vue`
- **Lines**: 12-26
- **Display**: Table column with avatar and agent type
- **Purpose**: Alternative table view
- **Critical**: Medium - reusable component

#### 4. AgentCard.vue
**File**: `frontend/src/components/AgentCard.vue`
- **Lines**: 5, 15, 447
- **Display**: Card styling and header label
- **Purpose**: Individual agent status card
- **Critical**: Yes - displays agent info

#### 5. AgentDetailsModal.vue
**File**: `frontend/src/components/projects/AgentDetailsModal.vue`
- **Lines**: 22-24, 281, 313
- **Display**: Agent type chip and details
- **Purpose**: Detailed agent information popup
- **Critical**: Yes - users view agent details

#### 6. SuccessionTimeline.vue
**File**: `frontend/src/components/projects/SuccessionTimeline.vue`
- **Lines**: 33
- **Display**: Agent type label in succession timeline
- **Purpose**: Show orchestrator succession history
- **Critical**: Medium - shows handover chain

#### 7. MessageAuditModal.vue
**File**: `frontend/src/components/projects/MessageAuditModal.vue`
- **Lines**: 245
- **Display**: Agent label in message audit
- **Purpose**: Show which agent sent each message
- **Critical**: Medium - for message audit trail

#### 8. AgentCardGrid.vue
**File**: `frontend/src/components/orchestration/AgentCardGrid.vue`
- **Used indirectly**: Via useAgentData composable (color/abbreviation)
- **Purpose**: Card grid display of agents
- **Critical**: Medium - grid layout

#### Additional: Message-Related Components

**MessageStream.vue** (Line 223)
- **Display**: Extract agent_type from message metadata
- **Function**: `getAgentType()` - determines chat head color

**MessageInput.vue** (Lines 108, 136)
- **Display**: Agent type in agent dropdown
- **Function**: Build agent selector labels

---

## Question 5: What would break if we renamed to `role`?

### Answer: CRITICAL SYSTEMS WOULD FAIL

### Breaking Changes by Category

#### A. Color/Avatar System (VISUAL BREAKDOWN)
**What would happen**: Avatars lose their colors and initials.

**Affected**:
- `getAgentColor()` function in JobsTab.vue (Line 571)
  - Referenced by: Line 26
  - Result: `<v-avatar :color="undefined">` - broken avatar

- `getAgentInitials()` function in LaunchTab.vue (Line 302)
  - Referenced by: Line 123
  - Result: No initials displayed

- `getAgentTypeColor()` in useAgentData.js (Line 97)
  - Referenced by: AgentTableView.vue, AgentCardGrid.vue
  - Result: All colors broken in table view

**Impact**: Users can't distinguish agent types visually.

#### B. Sorting Logic (DATA STRUCTURE BREAKDOWN)
**What would happen**: Orchestrators no longer appear first.

**Affected**:
1. agentJobsStore.js (Lines 107-111)
   ```javascript
   const aIsOrchestrator = a.agent_type === 'orchestrator' ? 0 : 1
   // ↑ This check breaks - 'role' field doesn't exist
   ```

2. useAgentData.js (Lines 46-47)
   ```javascript
   if (a.agent_type === 'orchestrator') return -1
   // ↑ Same issue
   ```

**Result**: Orchestrators appear randomly in list, breaking UX priority.

#### C. Filtering Logic (TABLE INTERACTION BREAKDOWN)
**What would happen**: Agent type filter doesn't work.

**Affected**:
- agentJobs.js (Lines 55-58)
  ```javascript
  if (tableFilters.value.agent_type.length) {
    filtered = filtered.filter((a) =>
      tableFilters.value.agent_type.includes(a.agent_type),  // ← BROKEN
    )
  }
  ```

**Result**: Users click "Filter by Type" button, nothing happens.

#### D. Conditional Rendering (FEATURE BREAKDOWN)
**What would happen**: Critical buttons/UI disappear or appear incorrectly.

**Affected Components**:

1. **JobsTab.vue** (Line 211) - Hand Over button
   ```javascript
   v-if="agent.agent_type === 'orchestrator' && ['working', 'complete', 'completed'].includes(agent.status)"
   // ↑ agent_type doesn't exist → button never shows
   ```
   **Impact**: Orchestrator handover feature broken.

2. **LaunchTab.vue** (Lines 240-241)
   ```javascript
   const nonOrchestratorAgents = computed(() => {
     return sortedJobs.value.filter((agent) => agent.agent_type !== 'orchestrator')
     // ↑ Filters wrong data
   })
   ```
   **Impact**: Orchestrators and non-orchestrators mixed in UI.

3. **LaunchTab.vue** (Line 448)
   ```javascript
   if (agent.agent_type === 'orchestrator') {
     // Orchestrators don't have editable missions
   }
   // ↑ This logic breaks - orchestrators get mission editor
   ```
   **Impact**: Users can edit orchestrator missions (corrupts workflow).

4. **AgentDetailsModal.vue** (Line 313)
   ```javascript
   const isOrchestrator = computed(() => {
     return props.agent?.agent_type === 'orchestrator'
   })
   // ↑ Always false → wrong UI shown
   ```
   **Impact**: Wrong details panel displayed.

#### E. Claude Code CLI Mode (CRITICAL FEATURE BREAKDOWN)
**What would happen**: CLI mode action restrictions fail completely.

**Affected**: actionConfig.js (Lines 114, 139, 188, 205)

```javascript
export function shouldShowLaunchAction(job, claudeCodeCliMode) {
  if (claudeCodeCliMode && job.agent_type !== 'orchestrator') {
    return false  // ← agent_type doesn't exist → always true
  }
  // ...
}
```

**Cascade failure**:
1. User in Claude Code CLI mode clicks "Launch" on non-orchestrator
2. System allows it (when it shouldn't)
3. Non-orchestrator launches in CLI mode (breaks orchestration workflow)
4. Project fails

**Impact**: Claude Code CLI mode completely broken.

#### F. API/Backend Integration (SILENT DATA CORRUPTION)
**What would happen**: Backend receives wrong field name.

**Affected**: API requests that include agent_type:
- WebSocket handlers expect `agent_type` in payload
- Backend filtering expects `agent_type` in requests
- Data mismatch causes:
  - Health alerts show undefined
  - Staleness notifications fail
  - Message routing broken

**Example** (websocketEventRouter.js, Line 122):
```javascript
const { health_state, agent_type, issue_description } = payload
// ↑ agent_type will be undefined
message: `${agent_type} - ${issue_description}`  // → "undefined - Alert"
```

#### G. Test Files (TESTING BREAKDOWN)
**What would happen**: E2E tests fail silently.

**Affected**: 10+ test files with data attributes:
```javascript
:data-agent-type="agent.agent_type"
// Tests check: expect(wrapper.attributes('data-agent-type')).toBe('orchestrator')
```

**Impact**: Tests fail, preventing regression detection.

---

## Summary: What Breaks

### Severity Tiers

#### 🔴 CRITICAL (System Breaking)
1. ✗ Avatar colors (visibility completely lost)
2. ✗ Avatar initials (avatars show nothing)
3. ✗ Sorting logic (wrong order)
4. ✗ Filtering logic (doesn't work)
5. ✗ Hand Over button (hidden)
6. ✗ Orchestrator/Non-Orchestrator separation (UI breaks)
7. ✗ Claude Code CLI mode (actions allowed when shouldn't be)
8. ✗ Mission editability (wrong UI shown)

#### 🟠 HIGH (Feature Breaking)
1. ✗ Conditional rendering in 5+ components
2. ✗ API request building
3. ✗ WebSocket payload extraction

#### 🟡 MEDIUM (UX Degradation)
1. ✗ Console logging/debugging
2. ✗ Component CSS class binding
3. ✗ Test data attributes

---

## Conclusion

**Renaming `agent_type` → `role` would be CATASTROPHIC.**

It would break:
- Visual display (colors, initials)
- Core functionality (sorting, filtering)
- Critical features (CLI mode, hand over)
- UI layout (orchestrator separation)
- Backend integration (WebSocket, API)

**Estimated Impact**: 20+ files, 30+ breaking changes, 2-3 days to fix, HIGH RISK of missing issues.

**Recommendation**: **DO NOT RENAME** unless absolutely necessary. If necessary, centralize configuration first (see `AGENT_TYPE_REFACTORING_GUIDE.md`).

