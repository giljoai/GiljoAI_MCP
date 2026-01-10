# Agent Type Refactoring Guide (If Needed)

**Purpose**: Step-by-step reference for anyone attempting to refactor `agent_type` naming or consolidate agent type logic.

---

## Phase 1: Create Centralized Configuration

### Step 1.1: Create `frontend/src/utils/agentTypeConfig.js`

```javascript
/**
 * Centralized Agent Type Configuration
 * Single source of truth for agent types, colors, and abbreviations
 *
 * CRITICAL: Update all imports in components when this changes
 */

// Agent type constants (prevent typos)
export const AGENT_TYPES = {
  ORCHESTRATOR: 'orchestrator',
  ANALYZER: 'analyzer',
  IMPLEMENTER: 'implementer',
  IMPLEMENTOR: 'implementor', // Alias
  TESTER: 'tester',
  REVIEWER: 'reviewer',
  DOCUMENTER: 'documenter',
  RESEARCHER: 'researcher',
}

// Color palette for avatars and displays
// HEX colors matching current JobsTab.vue/LaunchTab.vue
export const AGENT_TYPE_COLORS_HEX = {
  orchestrator: '#D4A574', // Tan/Beige - Project coordination
  analyzer: '#E74C3C',     // Red - Analysis & research
  implementer: '#3498DB',  // Blue - Code implementation
  implementor: '#3498DB',  // Blue - Code implementation (alias)
  tester: '#FFC300',       // Yellow - Testing & QA
  reviewer: '#9B59B6',     // Purple - Code review
  documenter: '#27AE60',   // Green - Documentation
  researcher: '#27AE60',   // Green - Research (alias)
}

// Vuetify color names (for useAgentData composable)
export const AGENT_TYPE_COLORS_VUETIFY = {
  orchestrator: 'orange',
  analyzer: 'red',
  implementer: 'blue',
  tester: 'yellow',
  reviewer: 'purple',
  documenter: 'green',
  researcher: 'green',
}

// Two-letter abbreviations for avatars
export const AGENT_TYPE_ABBRS = {
  orchestrator: 'OR',
  analyzer: 'AN',
  implementer: 'IM',
  implementor: 'IM',
  tester: 'TE',
  reviewer: 'RV',
  documenter: 'DO',
  researcher: 'RE',
}

// Helper function: Get HEX color
export const getAgentColorHex = (agentType) => {
  return AGENT_TYPE_COLORS_HEX[agentType] || '#999'
}

// Helper function: Get Vuetify color
export const getAgentColorVuetify = (agentType) => {
  return AGENT_TYPE_COLORS_VUETIFY[agentType] || 'grey'
}

// Helper function: Get abbreviation
export const getAgentAbbreviation = (agentType) => {
  return AGENT_TYPE_ABBRS[agentType] || (agentType || '').substring(0, 2).toUpperCase()
}

// Check if agent is orchestrator (useful for CLI mode logic)
export const isOrchestrator = (agentType) => {
  return agentType === AGENT_TYPES.ORCHESTRATOR
}
```

---

## Phase 2: Update Components to Use Centralized Config

### Step 2.1: Update `frontend/src/components/projects/JobsTab.vue`

**Current** (Lines 571-599):
```javascript
function getAgentColor(agentType) {
  const colors = {
    orchestrator: '#D4A574',
    analyzer: '#E74C3C',
    // ... (duplicated code)
  }
}
```

**Replace with**:
```javascript
import { getAgentColorHex, getAgentAbbreviation } from '@/utils/agentTypeConfig'

// Remove the entire getAgentColor and getAgentAbbr functions
// Use imported functions instead

// In template:
// :color="getAgentColorHex(agent.agent_type)"
// {{ getAgentAbbreviation(agent.agent_type) }}
```

**Also update**: Lines 749 (CLI mode check)
```javascript
// Current
if (agent.agent_type === 'orchestrator') {

// New
import { isOrchestrator } from '@/utils/agentTypeConfig'
if (isOrchestrator(agent.agent_type)) {
```

**Also update**: Line 211 (Hand Over button condition)
```javascript
// Current
v-if="agent.agent_type === 'orchestrator' && ['working', 'complete', 'completed'].includes(agent.status)"

// New
v-if="isOrchestrator(agent.agent_type) && ['working', 'complete', 'completed'].includes(agent.status)"
```

### Step 2.2: Update `frontend/src/components/projects/LaunchTab.vue`

**Current** (Lines 285-315): Duplicate getAgentColor and getAgentInitials
**Replace with**: Import from agentTypeConfig

**Update filtering logic** (Lines 240-251):
```javascript
// Current
const nonOrchestratorAgents = computed(() => {
  return sortedJobs.value.filter((agent) => agent.agent_type !== 'orchestrator')
})

const orchestrators = sortedJobs.value
  .filter((agent) => agent.agent_type === 'orchestrator')

// New
import { AGENT_TYPES } from '@/utils/agentTypeConfig'

const nonOrchestratorAgents = computed(() => {
  return sortedJobs.value.filter((agent) => agent.agent_type !== AGENT_TYPES.ORCHESTRATOR)
})

const orchestrators = sortedJobs.value
  .filter((agent) => agent.agent_type === AGENT_TYPES.ORCHESTRATOR)
```

**Update orchestrator check** (Line 448):
```javascript
// Current
if (agent.agent_type === 'orchestrator') {

// New
import { isOrchestrator } from '@/utils/agentTypeConfig'
if (isOrchestrator(agent.agent_type)) {
```

### Step 2.3: Update `frontend/src/utils/actionConfig.js`

**Update all agent_type checks** (Lines 114, 139, 188, 205):
```javascript
// Current (multiple places)
if (claudeCodeCliMode && job.agent_type !== 'orchestrator') {

if (job.agent_type !== 'orchestrator') return false

// New
import { isOrchestrator } from '@/utils/agentTypeConfig'

if (claudeCodeCliMode && !isOrchestrator(job.agent_type)) {

if (!isOrchestrator(job.agent_type)) return false
```

### Step 2.4: Update `frontend/src/composables/useAgentData.js`

**Update sorting logic** (Lines 46-47):
```javascript
// Current
if (a.agent_type === 'orchestrator') return -1
if (b.agent_type === 'orchestrator') return 1

// New
import { isOrchestrator } from '@/utils/agentTypeConfig'

if (isOrchestrator(a.agent_type)) return -1
if (isOrchestrator(b.agent_type)) return 1
```

**Update color function** (Lines 97-106):
```javascript
// Current
const getAgentTypeColor = (agentType) => {
  const colors = {
    orchestrator: 'orange',
    // ... (needs updating to match JobsTab colors)
  }
}

// New
import { getAgentColorVuetify } from '@/utils/agentTypeConfig'

const getAgentTypeColor = (agentType) => {
  return getAgentColorVuetify(agentType)
}
```

**Update abbreviation function** (Lines 115-124):
```javascript
// Current
const getAgentAbbreviation = (agentType) => {
  const abbr = {
    orchestrator: 'Or',
    // ...
  }
}

// New
import { getAgentAbbreviation } from '@/utils/agentTypeConfig'

// Remove this function - use imported version instead
```

### Step 2.5: Update `frontend/src/stores/agentJobsStore.js`

**Update orchestrator check** (Lines 107-111):
```javascript
// Current
const aIsOrchestrator = a.agent_type === 'orchestrator' ? 0 : 1
const bIsOrchestrator = b.agent_type === 'orchestrator' ? 0 : 1

// New
import { isOrchestrator } from '@/utils/agentTypeConfig'

const aIsOrchestrator = isOrchestrator(a.agent_type) ? 0 : 1
const bIsOrchestrator = isOrchestrator(b.agent_type) ? 0 : 1
```

### Step 2.6: Update `frontend/src/stores/agentJobs.js`

**Filter setup** (Line 30):
```javascript
// Add agent_type to table filters (already there - no change needed)
agent_type: [],
```

**Filter logic** (Lines 55-58):
```javascript
// Current code should work as-is, but consider using constant:
if (tableFilters.value.agent_type.length) {
  filtered = filtered.filter((a) =>
    tableFilters.value.agent_type.includes(a.agent_type),
  )
}
```

### Step 2.7: Update Remaining Components

**`frontend/src/components/orchestration/AgentCardGrid.vue`** (Lines 173, 193):
```javascript
// Current
if (props.usingClaudeCodeSubagents) {
  return agent.is_orchestrator || agent.agent_type === 'orchestrator'
}

// New
import { isOrchestrator } from '@/utils/agentTypeConfig'

if (props.usingClaudeCodeSubagents) {
  return agent.is_orchestrator || isOrchestrator(agent.agent_type)
}
```

**`frontend/src/components/projects/AgentDetailsModal.vue`** (Line 313):
```javascript
// Current
const isOrchestrator = computed(() => {
  return props.agent?.agent_type === 'orchestrator'
})

// New
import { isOrchestrator as isAgentOrchestrator } from '@/utils/agentTypeConfig'

const isOrchestrator = computed(() => {
  return isAgentOrchestrator(props.agent?.agent_type)
})
```

**`frontend/src/components/projects/LaunchTab.vue`** (Lines 345-348):
```javascript
// Current
function getInstanceNumber(agent) {
  const agentType = agent.agent_type?.toLowerCase()
  if (!agentType) return 1
  const sameTypeAgents = sortedJobs.value.filter((a) => a.agent_type?.toLowerCase() === agentType)

// New - keep same logic but consider using constant if needed
// This is case-sensitive check, so be careful with refactoring
```

---

## Phase 3: Update Stores and Services

### Step 3.1: Update WebSocket Event Router

**`frontend/src/stores/websocketEventRouter.js`** (Lines 122, 127, 138, 142):
```javascript
// Current
const { health_state, agent_type, issue_description } = payload
message: `${agent_type} - ${issue_description}`,

// Keep as-is - these are display messages from backend
// No refactoring needed here
```

### Step 3.2: Update Composables

**`frontend/src/composables/useStalenessMonitor.js`** (Lines 43, 46):
```javascript
// Current
message: `${job.agent_name || job.agent_type} has been inactive for over 10 minutes`,
agent_type: job.agent_type

// Keep as-is - displaying agent info from database
// No refactoring needed here
```

---

## Phase 4: Test Updates

### Step 4.1: Update Component Tests

All test files need to update data attributes:

**Current**:
```javascript
data-testid="agent-row"
:data-agent-type="agent.agent_type"
```

**Tests check**:
```javascript
expect(wrapper.attributes('data-agent-type')).toBe('orchestrator')
```

**No code change needed** - `agent_type` is still the property name, just using constant comparison:
```javascript
import { isOrchestrator } from '@/utils/agentTypeConfig'

if (isOrchestrator(agentData.agent_type)) {
  // Test orchestrator-specific behavior
}
```

### Step 4.2: Mock Data Updates

**`frontend/src/components/StatusBoard/ActionIcons.vue`** (Line 161):
```javascript
// Current mock data
agent_type: 'implementer',

// New (import constants if needed for tests)
import { AGENT_TYPES } from '@/utils/agentTypeConfig'
agent_type: AGENT_TYPES.IMPLEMENTER,
```

---

## Phase 5: Verification Checklist

### Before Merging

- [ ] All imports of agentTypeConfig present and working
- [ ] No hard-coded 'orchestrator' strings remain (except in comments)
- [ ] Color consistency verified visually
  - [ ] JobsTab avatars display correct colors
  - [ ] LaunchTab avatars match JobsTab
  - [ ] Vuetify colors used in AgentTableView match
- [ ] Filtering works
  - [ ] Can filter by agent_type in table
  - [ ] Orchestrators separate from non-orchestrators
- [ ] Sorting works
  - [ ] Orchestrators always appear first
  - [ ] Other agents sorted alphabetically
- [ ] CLI mode logic intact
  - [ ] Only orchestrators can launch in Claude Code mode
  - [ ] Hand Over button only shows for orchestrators
- [ ] Tests pass
  - [ ] All unit tests pass
  - [ ] All integration tests pass
  - [ ] E2E tests verify sorting/filtering
- [ ] Visual regression testing
  - [ ] Agent avatars display correctly
  - [ ] Colors match across components
  - [ ] No UI breaks visible

---

## Estimated Effort

| Phase | Files | Effort | Risk |
|-------|-------|--------|------|
| 1: Create config | 1 new file | 1-2 hours | Low |
| 2: Update components | 8-10 files | 3-4 hours | Medium |
| 3: Update stores/services | 4-5 files | 1-2 hours | Low |
| 4: Update tests | 10+ files | 2-3 hours | Medium |
| 5: Verification | Testing | 2-3 hours | High |
| **TOTAL** | **23+ files** | **9-14 hours** | **High** |

---

## Alternative: Minimal Refactoring

If full refactoring is too much work, consider:

1. **Just centralize colors**: Keep function names, move to single file
2. **Add constants**: Define AGENT_TYPES constant, update orchestrator checks
3. **Don't rename**: Keep `agent_type` field name (zero breaking changes)

This would reduce effort to 4-5 hours with much lower risk.

