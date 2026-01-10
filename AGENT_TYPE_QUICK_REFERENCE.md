# Agent Type Frontend Usage - Quick Reference

**TL;DR**: `agent_type` is **NOT** just display. It's deeply woven into logic, sorting, filtering, and critical features. Renaming would break 20+ files.

---

## Quick Answers

| Question | Answer | Evidence |
|----------|--------|----------|
| **Badge colors?** | YES | JobsTab.vue lines 26-27; 3 separate color mappings |
| **Avatar generation?** | YES | Every avatar uses agent_type for color & initials |
| **Filtering/sorting?** | YES | agentJobsStore.js, agentJobs.js, LaunchTab.vue |
| **Display in components?** | YES | 8+ components including JobsTab, LaunchTab, AgentCard |
| **Would break if renamed?** | CATASTROPHIC | Sorting, filtering, CLI mode, Hand Over, avatars all fail |

---

## Critical Files

### Functional Logic (Must Change)
```
✗ frontend/src/utils/actionConfig.js (Lines 114, 139, 188, 205)
✗ frontend/src/stores/agentJobsStore.js (Lines 107-111)
✗ frontend/src/stores/agentJobs.js (Lines 55-58)
✗ frontend/src/composables/useAgentData.js (Lines 46-47)
✗ frontend/src/components/projects/LaunchTab.vue (Lines 240-251, 448)
✗ frontend/src/components/projects/JobsTab.vue (Lines 211, 749)
✗ frontend/src/components/projects/AgentDetailsModal.vue (Line 313)
```

### Display Logic (Must Change)
```
✗ frontend/src/components/projects/JobsTab.vue (Lines 26-27, 571-599)
✗ frontend/src/components/projects/LaunchTab.vue (Lines 122-123, 285-315)
✗ frontend/src/composables/useAgentData.js (Lines 97-124)
✗ frontend/src/components/orchestration/AgentTableView.vue (Lines 14, 16)
✗ frontend/src/components/AgentCard.vue (Line 5, 15, 447)
✗ frontend/src/components/projects/AgentDetailsModal.vue (Lines 22-24)
```

### WebSocket/Service (Should Review)
```
~ frontend/src/stores/websocketEventRouter.js (Lines 122, 127, 138, 142)
~ frontend/src/composables/useStalenessMonitor.js (Lines 43, 46)
~ frontend/src/components/projects/MessageStream.vue (Line 223)
```

---

## Color Mappings (Code Duplication Alert!)

### JobsTab.vue & LaunchTab.vue (HEX Colors - IDENTICAL)
```javascript
orchestrator: '#D4A574',  // Tan/Beige
analyzer: '#E74C3C',      // Red
implementer: '#3498DB',   // Blue
tester: '#FFC300',        // Yellow
reviewer: '#9B59B6',      // Purple
documenter: '#27AE60',    // Green
```

### useAgentData.js (Vuetify Colors - DIFFERENT!)
```javascript
orchestrator: 'orange',   // ← NOT #D4A574!
analyzer: 'red',
implementer: 'blue',
tester: 'yellow',
reviewer: 'purple',
```

**Problem**: Same agent type shows different colors in different views!

---

## Abbreviations (Also Duplicated)

### JobsTab.vue
```
orchestrator: 'OR'
analyzer: 'AN'
implementer: 'IM'
tester: 'TE'
reviewer: 'RV'
documenter: 'DO'
researcher: 'RE'
```

### LaunchTab.vue
```
orchestrator: 'OR'
analyzer: 'AN'
implementer: 'IM'
tester: 'TE'
reviewer: 'RV'
documenter: 'DO'
researcher: 'RE'
```

### useAgentData.js
```
orchestrator: 'Or'  ← Different case!
analyzer: 'An'
implementer: 'Im'
tester: 'Te'
reviewer: 'Re'
```

---

## Critical Sorting Logic

### Orchestrators MUST sort first:
```javascript
// agentJobsStore.js Line 107-111
const aIsOrchestrator = a.agent_type === 'orchestrator' ? 0 : 1
const bIsOrchestrator = b.agent_type === 'orchestrator' ? 0 : 1
if (aIsOrchestrator !== bIsOrchestrator) return aIsOrchestrator - bIsOrchestrator
```

**If agent_type missing**: Sort breaks, orchestrator appears randomly.

---

## Critical Filtering Logic

### Users filter by agent_type:
```javascript
// agentJobs.js Line 55-58
if (tableFilters.value.agent_type.length) {
  filtered = filtered.filter((a) =>
    tableFilters.value.agent_type.includes(a.agent_type),
  )
}
```

**If agent_type missing**: Filter doesn't work.

---

## Critical Conditional Rendering

### Hand Over button (JobsTab.vue Line 211)
```javascript
v-if="agent.agent_type === 'orchestrator' && ['working', 'complete', 'completed'].includes(agent.status)"
```

**If agent_type missing**: Button never shows.

### Orchestrator/Non-Orchestrator separation (LaunchTab.vue Lines 240-251)
```javascript
const nonOrchestratorAgents = computed(() => {
  return sortedJobs.value.filter((agent) => agent.agent_type !== 'orchestrator')
})
```

**If agent_type missing**: UI layout breaks, agents mixed up.

### Mission editability (LaunchTab.vue Line 448)
```javascript
if (agent.agent_type === 'orchestrator') {
  // Orchestrators don't have editable missions
}
```

**If agent_type missing**: Users can edit orchestrator missions (corrupts workflow).

---

## Claude Code CLI Mode (CRITICAL)

### actionConfig.js - Launch permission (Line 114)
```javascript
if (claudeCodeCliMode && job.agent_type !== 'orchestrator') {
  return false  // Only orchestrator can launch in CLI mode
}
```

**If agent_type missing**: Non-orchestrators can launch in CLI mode (breaks workflow).

### actionConfig.js - Hand Over permission (Line 205)
```javascript
if (job.agent_type !== 'orchestrator') {
  return 'Only orchestrator can initiate handover'
}
```

**If agent_type missing**: Non-orchestrators can hand over (corrupts orchestration).

---

## What Breaks (Severity Tiers)

### 🔴 CRITICAL (System Fails)
- [ ] Avatar colors (visibility lost)
- [ ] Avatar initials (avatars empty)
- [ ] Sorting (orchestrators not first)
- [ ] Filtering (doesn't work)
- [ ] Hand Over button (hidden)
- [ ] CLI mode (wrong agents allowed)

### 🟠 HIGH (Features Broken)
- [ ] Orchestrator/non-orchestrator separation UI
- [ ] Mission editability logic
- [ ] Agent details modal display
- [ ] WebSocket health alerts
- [ ] Staleness notifications

### 🟡 MEDIUM (UX Degraded)
- [ ] Console logging
- [ ] CSS class binding
- [ ] Test data attributes

---

## Refactoring Effort

| Task | Files | Effort | Risk |
|------|-------|--------|------|
| Create centralized config | 1 | 1-2h | Low |
| Update components | 8-10 | 3-4h | Med |
| Update stores/services | 4-5 | 1-2h | Low |
| Update tests | 10+ | 2-3h | Med |
| Testing & verification | N/A | 2-3h | High |
| **TOTAL** | **23+** | **9-14h** | **HIGH** |

---

## Recommendation

**DO NOT RENAME** `agent_type` → `role` without:

1. ✓ Creating centralized config (agentTypeConfig.js)
2. ✓ Consolidating 3 color mappings into 1
3. ✓ Updating 20+ files
4. ✓ Comprehensive testing (sorting, filtering, CLI mode)
5. ✓ Visual regression testing (avatar colors)

**Risk**: High probability of breaking critical workflows if not done perfectly.

**Better Alternative**: Leave `agent_type` as-is, create centralized constants/functions instead:
```javascript
export const AGENT_TYPES = { ORCHESTRATOR: 'orchestrator', ... }
export const isOrchestrator = (agentType) => agentType === AGENT_TYPES.ORCHESTRATOR
```

This reduces refactoring to 4-5 hours with much lower risk.

---

## Files By Impact

### Must Review (Functional Impact)
1. agentJobsStore.js
2. agentJobs.js
3. actionConfig.js
4. useAgentData.js
5. LaunchTab.vue
6. JobsTab.vue
7. AgentDetailsModal.vue
8. AgentCardGrid.vue

### Should Review (Display Impact)
1. AgentTableView.vue
2. AgentCard.vue
3. SuccessionTimeline.vue
4. MessageAuditModal.vue

### Check for Integration (API/WebSocket)
1. websocketEventRouter.js
2. useStalenessMonitor.js
3. MessageStream.vue
4. MessageInput.vue

### Update Tests
All `*.spec.js` files checking `data-agent-type` attributes

---

## See Also

- `AGENT_TYPE_USAGE_ANALYSIS.md` - Comprehensive analysis with line numbers
- `AGENT_TYPE_REFACTORING_GUIDE.md` - Step-by-step refactoring instructions
- `AGENT_TYPE_QUESTIONS_ANSWERED.md` - Detailed Q&A with code examples

