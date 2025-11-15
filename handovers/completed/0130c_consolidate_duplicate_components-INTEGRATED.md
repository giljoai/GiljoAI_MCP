# Handover 0130c: Consolidate Duplicate Components

---
**⚠️ CRITICAL UPDATE (2025-11-12): MERGED INTO HANDOVER 0515**

This handover has been **merged** into the 0500 series remediation project:

**New Scope**: Handover 0515 - Frontend Consolidation
**Parent Project**: Projectplan_500.md
**Status**: Deferred until after critical remediation (Handovers 0500-0514 complete)

**Reason for Merger**: The refactoring (Handovers 0120-0130) left 23 critical implementation gaps. Component consolidation (0130c) and API centralization (0130d) are now combined into a single cohesive frontend consolidation effort (Handover 0515). See:
- **Investigation Reports**: Products, Projects, Settings, Orchestration breakage
- **Master Plan**: `handovers/Projectplan_500.md`
- **New Handover**: `handovers/0515_frontend_consolidation.md`

**MERGED INTO**: Handover 0515 combines both 0130c (merge duplicate components) and 0130d (centralize API calls) into a single cohesive frontend consolidation effort.

**Original scope below** (preserved for historical reference):

---

**Date**: 2025-11-12
**Priority**: P2 (Medium - Code Quality Improvement)
**Duration**: 1-2 days
**Status**: Merged into Handover 0515
**Type**: Component Consolidation & Refactoring
**Dependencies**: Handover 0130b (Remove Zombie Code) - PENDING
**Parent**: Handover 0130 (Frontend WebSocket Modernization)

---

## Executive Summary

### Why Consolidate Components?

**PROBLEM**: Multiple similar components with overlapping functionality confuse both developers and AI coding tools:
- Which AgentCard to use? (Basic vs Enhanced)
- Which Timeline to use? (Vertical vs Horizontal vs Artifact)
- Are they intentionally different or accidental duplicates?

**FOR AGENTIC AI TOOLS**: When an AI tool needs to display agent status, it might:
- Pick the wrong component (basic instead of enhanced)
- Create a third variant instead of using existing
- Miss features available in the enhanced version
- Generate inconsistent UI across the application

**SOLUTION**: Consolidate to single-purpose components with clear naming and documentation.

### What We're Consolidating

1. **Agent Card Components** (2 variants → 1 unified)
   - `orchestration/AgentCard.vue` (basic, 1 usage)
   - `projects/AgentCardEnhanced.vue` (full-featured, 4 usages)
   - **Target**: Single `AgentCard.vue` with feature flags

2. **Timeline Components** (3 variants → 1 or 2)
   - `SubAgentTimeline.vue` (vertical)
   - `SubAgentTimelineHorizontal.vue` (horizontal)
   - `agent-flow/ArtifactTimeline.vue` (artifact-specific)
   - **Target**: Verify if all are actively used, consolidate if redundant

3. **Potential Other Duplicates** (audit needed)
   - Setup wizard variants
   - Form components with similar purposes
   - Modal dialogs with overlapping features

---

## Objectives

### Primary Objectives

1. **Consolidate AgentCard Components**
   - Merge `AgentCard.vue` and `AgentCardEnhanced.vue`
   - Preserve all features from both
   - Use props to control feature visibility (compact mode vs full mode)
   - Update all 5 usage locations

2. **Audit Timeline Components**
   - Analyze usage of all 3 timeline variants
   - Determine if all are necessary
   - Consolidate if 2+ are redundant
   - Document if all 3 serve different purposes

3. **Document Component Purposes**
   - Add JSDoc comments explaining when to use each
   - Update COMPONENT_GUIDE.md with usage guidance
   - Prevent future duplication

### Secondary Objectives

1. **Create Component Selection Guide**
   - Decision tree: "Which component should I use?"
   - Add to docs for developers and AI tools

2. **Extract Shared Logic to Composables**
   - Agent status formatting
   - Timeline data processing
   - Reusable across consolidated components

3. **Improve Component Discoverability**
   - Better naming conventions
   - Clearer directory structure
   - README in each component folder

---

## Current State Analysis

### AgentCard Variants Analysis

**Component 1: `orchestration/AgentCard.vue`**
```vue
Purpose: Basic agent status card for grid display
Usage: AgentCardGrid.vue (1 usage)
Features:
  - Agent name and type
  - Status badge (idle/working/complete)
  - Simple click handler
  - Minimal styling

Lines: ~150 (estimated)
Complexity: Low
```

**Component 2: `projects/AgentCardEnhanced.vue`**
```vue
Purpose: Full-featured agent job card with succession support
Usage: JobsTab.vue, LaunchTab.vue, etc. (4 usages)
Features:
  - All features from basic AgentCard
  - Instance number tracking
  - Context usage progress bar
  - Handover button (orchestrators only)
  - Real-time status updates via WebSocket
  - Succession timeline integration
  - Expanded details panel

Lines: ~400 (estimated)
Complexity: Medium-High
```

**Analysis**:
- Enhanced version is superset of basic version
- Basic version used only in grid layout (needs compact display)
- Enhanced version used in detailed views (needs all features)

**Consolidation Strategy**:
```vue
<!-- Unified AgentCard.vue -->
<template>
  <v-card :class="{ compact: variant === 'compact' }">
    <!-- Always show: name, type, status -->
    <v-card-title>{{ agent.name }}</v-card-title>

    <!-- Compact mode: minimal display -->
    <template v-if="variant === 'compact'">
      <v-chip :color="statusColor">{{ status }}</v-chip>
    </template>

    <!-- Full mode: all enhanced features -->
    <template v-else>
      <v-card-subtitle>Instance {{ instance }}</v-card-subtitle>
      <ContextUsageBar v-if="showContext" :usage="contextUsage" />
      <HandoverButton v-if="showHandover && isOrchestrator" />
      <v-expand-transition>
        <AgentDetails v-if="expanded" :agent="agent" />
      </v-expand-transition>
    </template>
  </v-card>
</template>

<script setup>
const props = defineProps({
  agent: { type: Object, required: true },
  variant: { type: String, default: 'full' }, // 'compact' | 'full'
  showContext: { type: Boolean, default: true },
  showHandover: { type: Boolean, default: true },
})
</script>
```

**Migration Plan**:
1. Copy all features from Enhanced to basic AgentCard
2. Add `variant` prop ('compact' | 'full')
3. Update AgentCardGrid to use `variant="compact"`
4. Update project views to use `variant="full"` (or default)
5. Delete AgentCardEnhanced.vue
6. Update imports

### Timeline Variants Analysis

**Component 1: `SubAgentTimeline.vue`**
```vue
Purpose: Vertical timeline of agent activities
Usage: Unknown (needs grep audit)
Features:
  - Vertical layout
  - Chronological events
  - Agent status changes

Lines: ~200 (estimated)
```

**Component 2: `SubAgentTimelineHorizontal.vue`**
```vue
Purpose: Horizontal timeline of agent activities
Usage: Unknown (needs grep audit)
Features:
  - Horizontal layout (space-constrained views)
  - Same event types as vertical
  - Responsive to container width

Lines: ~180 (estimated)
```

**Component 3: `agent-flow/ArtifactTimeline.vue`**
```vue
Purpose: Timeline of artifact creation/updates
Usage: Agent flow visualization
Features:
  - Artifact-specific events
  - File change tracking
  - Different data structure

Lines: ~220 (estimated)
```

**Analysis**:
- Vertical vs Horizontal: Same data, different layout → consolidate?
- Artifact timeline: Different purpose (artifacts, not agents) → keep separate

**Consolidation Strategy**:
```vue
<!-- Option 1: Unified SubAgentTimeline with orientation prop -->
<SubAgentTimeline :orientation="'vertical'" />
<SubAgentTimeline :orientation="'horizontal'" />

<!-- Option 2: Keep both, extract shared logic to composable -->
// composables/useTimelineData.js
export function useTimelineData(events) {
  // Shared data processing, formatting, filtering
}
```

**Decision Needed**: Audit usage first, then decide consolidation approach

---

## Implementation Plan

### Phase 1: Audit Component Usage (1 hour)

**Steps**:
1. Audit AgentCard usages
2. Audit Timeline usages
3. Identify any other duplicate components
4. Document findings

**Commands**:
```bash
# AgentCard usages
echo "=== AgentCard.vue usages ==="
grep -r "import.*AgentCard'" frontend/src --include="*.vue" | grep -v "AgentCardEnhanced"

echo "=== AgentCardEnhanced.vue usages ==="
grep -r "import.*AgentCardEnhanced" frontend/src --include="*.vue"

# Timeline usages
echo "=== SubAgentTimeline.vue usages ==="
grep -r "import.*SubAgentTimeline'" frontend/src --include="*.vue" | grep -v "Horizontal"

echo "=== SubAgentTimelineHorizontal.vue usages ==="
grep -r "import.*SubAgentTimelineHorizontal" frontend/src --include="*.vue"

echo "=== ArtifactTimeline.vue usages ==="
grep -r "import.*ArtifactTimeline" frontend/src --include="*.vue"

# Other potential duplicates
echo "=== Potential duplicates (similar names) ==="
find frontend/src/components -name "*.vue" | sort | uniq -d
```

**Document Results in**: `handovers/0130c_AUDIT_RESULTS.md`

**Success Criteria**:
- ✅ All AgentCard usages documented (file + line number)
- ✅ All Timeline usages documented
- ✅ Other duplicates identified
- ✅ Consolidation priority determined

### Phase 2: Consolidate AgentCard Components (4-6 hours)

**Steps**:
1. Read both AgentCard files completely
2. Create unified component with feature flags
3. Test in isolation (Storybook or test route)
4. Update all usage locations (5 files)
5. Run build and test
6. Delete old components
7. Commit

**Implementation**:

**Step 2.1: Create Unified Component**
```bash
# Backup current files
cp frontend/src/components/orchestration/AgentCard.vue frontend/src/components/orchestration/AgentCard.backup
cp frontend/src/components/projects/AgentCardEnhanced.vue frontend/src/components/projects/AgentCardEnhanced.backup

# Read both files to understand all features
```

**Step 2.2: Write Unified AgentCard.vue**
```vue
<!-- frontend/src/components/AgentCard.vue (new unified location) -->
<template>
  <v-card
    :class="[
      'agent-card',
      `agent-card--${variant}`,
      { 'agent-card--clickable': clickable }
    ]"
    :elevation="variant === 'compact' ? 1 : 2"
    @click="handleClick"
  >
    <!-- Header: Always visible -->
    <v-card-title class="d-flex align-center">
      <v-icon :color="agentTypeColor" start>{{ agentTypeIcon }}</v-icon>
      <span>{{ agent.name }}</span>
      <v-spacer></v-spacer>
      <v-chip
        :color="statusColor"
        size="small"
        variant="flat"
      >
        {{ statusText }}
      </v-chip>
    </v-card-title>

    <!-- Compact mode: Minimal display -->
    <template v-if="variant === 'compact'">
      <v-card-subtitle v-if="showSubtitle">
        {{ agent.agent_type }} • {{ formattedDate }}
      </v-card-subtitle>
    </template>

    <!-- Full mode: Enhanced features -->
    <template v-else-if="variant === 'full'">
      <!-- Instance tracking (orchestrators) -->
      <v-card-subtitle v-if="agent.instance_number" class="d-flex align-center">
        <v-chip size="x-small" variant="outlined">
          Instance {{ agent.instance_number }}
        </v-chip>
        <span class="ml-2">{{ agent.agent_type }}</span>
      </v-card-subtitle>

      <v-card-text>
        <!-- Context usage (if available) -->
        <ContextUsageBar
          v-if="showContext && agent.context_used"
          :context-used="agent.context_used"
          :context-budget="agent.context_budget"
        />

        <!-- Progress indicator (working jobs) -->
        <v-progress-linear
          v-if="agent.status === 'working' && agent.progress"
          :model-value="agent.progress"
          color="primary"
          height="6"
          class="mt-2"
        />

        <!-- Metadata -->
        <div class="text-caption text-grey mt-2">
          <div>Created: {{ formattedDate }}</div>
          <div v-if="agent.completed_at">Completed: {{ formattedCompletedDate }}</div>
          <div v-if="agent.result">{{ truncatedResult }}</div>
        </div>
      </v-card-text>

      <v-card-actions v-if="showActions">
        <!-- Handover button (orchestrators only) -->
        <v-btn
          v-if="showHandover && isOrchestrator"
          variant="tonal"
          size="small"
          prepend-icon="mdi-hand-wave"
          @click.stop="$emit('trigger-handover')"
        >
          Hand Over
        </v-btn>

        <!-- View details -->
        <v-btn
          v-if="showDetails"
          variant="text"
          size="small"
          @click.stop="$emit('view-details')"
        >
          Details
        </v-btn>

        <v-spacer></v-spacer>

        <!-- Expand/collapse -->
        <v-btn
          v-if="expandable"
          :icon="expanded ? 'mdi-chevron-up' : 'mdi-chevron-down'"
          variant="text"
          size="small"
          @click.stop="toggleExpanded"
        />
      </v-card-actions>

      <!-- Expanded content -->
      <v-expand-transition>
        <div v-if="expanded && expandable">
          <v-divider></v-divider>
          <v-card-text>
            <!-- Detailed agent info -->
            <slot name="expanded-content">
              <pre class="text-caption">{{ agent }}</pre>
            </slot>
          </v-card-text>
        </div>
      </v-expand-transition>
    </template>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import ContextUsageBar from './ContextUsageBar.vue'

const props = defineProps({
  agent: {
    type: Object,
    required: true,
  },
  variant: {
    type: String,
    default: 'full',
    validator: (value) => ['compact', 'full'].includes(value),
  },
  clickable: {
    type: Boolean,
    default: false,
  },
  showContext: {
    type: Boolean,
    default: true,
  },
  showHandover: {
    type: Boolean,
    default: true,
  },
  showActions: {
    type: Boolean,
    default: true,
  },
  showDetails: {
    type: Boolean,
    default: false,
  },
  showSubtitle: {
    type: Boolean,
    default: true,
  },
  expandable: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['click', 'trigger-handover', 'view-details'])

const expanded = ref(false)

const isOrchestrator = computed(() => props.agent.agent_type === 'orchestrator')

const statusColor = computed(() => {
  switch (props.agent.status) {
    case 'pending': return 'grey'
    case 'active': return 'primary'
    case 'working': return 'info'
    case 'complete': return 'success'
    case 'failed': return 'error'
    case 'paused': return 'warning'
    default: return 'grey'
  }
})

const statusText = computed(() => {
  return props.agent.status?.charAt(0).toUpperCase() + props.agent.status?.slice(1) || 'Unknown'
})

const agentTypeIcon = computed(() => {
  const icons = {
    orchestrator: 'mdi-brain',
    implementer: 'mdi-code-braces',
    tester: 'mdi-test-tube',
    reviewer: 'mdi-eye',
    documenter: 'mdi-file-document',
  }
  return icons[props.agent.agent_type] || 'mdi-robot'
})

const agentTypeColor = computed(() => {
  const colors = {
    orchestrator: 'purple',
    implementer: 'blue',
    tester: 'green',
    reviewer: 'orange',
    documenter: 'cyan',
  }
  return colors[props.agent.agent_type] || 'grey'
})

const formattedDate = computed(() => {
  return props.agent.created_at
    ? formatDistanceToNow(new Date(props.agent.created_at), { addSuffix: true })
    : 'Unknown'
})

const formattedCompletedDate = computed(() => {
  return props.agent.completed_at
    ? formatDistanceToNow(new Date(props.agent.completed_at), { addSuffix: true })
    : null
})

const truncatedResult = computed(() => {
  const result = props.agent.result || ''
  return result.length > 100 ? result.substring(0, 100) + '...' : result
})

function handleClick() {
  if (props.clickable) {
    emit('click', props.agent)
  }
}

function toggleExpanded() {
  expanded.value = !expanded.value
}
</script>

<style scoped>
.agent-card--compact {
  cursor: pointer;
  transition: all 0.2s;
}

.agent-card--compact:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.agent-card--clickable {
  cursor: pointer;
}
</style>
```

**Step 2.3: Update Usage Locations**

**File 1: `orchestration/AgentCardGrid.vue`**
```vue
<script setup>
import AgentCard from '@/components/AgentCard.vue' // New unified location

// Update usage
</script>

<template>
  <div class="agent-card-grid">
    <AgentCard
      v-for="agent in agents"
      :key="agent.id"
      :agent="agent"
      variant="compact"
      clickable
      @click="handleAgentClick"
    />
  </div>
</template>
```

**Files 2-5: Project views (JobsTab, LaunchTab, etc.)**
```vue
<script setup>
import AgentCard from '@/components/AgentCard.vue' // New unified location

// Update usage
</script>

<template>
  <AgentCard
    :agent="job"
    variant="full"
    show-context
    show-handover
    expandable
    @trigger-handover="handleHandover"
  />
</template>
```

**Step 2.4: Test and Commit**
```bash
# Test build
cd frontend && npm run build

# Test in browser
npm run dev
# Navigate to: orchestration grid, jobs tab, launch tab

# If all tests pass, delete old components
rm frontend/src/components/orchestration/AgentCard.vue
rm frontend/src/components/projects/AgentCardEnhanced.vue

# Commit
git add -A
git commit -m "refactor(0130c): Consolidate AgentCard components

Merged AgentCard.vue and AgentCardEnhanced.vue into unified component.

Changes:
- Created new AgentCard.vue with variant prop (compact | full)
- Migrated all features from both old components
- Updated 5 usage locations:
  - AgentCardGrid.vue (variant='compact')
  - JobsTab.vue (variant='full')
  - LaunchTab.vue (variant='full')
  - [other files]

Features preserved:
- Compact mode: Grid display, minimal info
- Full mode: Instance tracking, context bars, handover button

Benefits:
- Single source of truth for agent display
- No confusion about which component to use
- AI coding tools guided to correct component

Deleted:
- orchestration/AgentCard.vue (merged)
- projects/AgentCardEnhanced.vue (merged)

Handover: 0130c - Consolidate Duplicate Components"
```

**Success Criteria**:
- ✅ Unified AgentCard.vue created
- ✅ All 5 usage locations updated
- ✅ Frontend build succeeds
- ✅ Manual testing confirms both variants work
- ✅ Old components deleted
- ✅ Changes committed

### Phase 3: Audit and Consolidate Timeline Components (4-6 hours)

**Steps**:
1. Audit timeline usage (from Phase 1 results)
2. Read all 3 timeline components
3. Decide consolidation strategy
4. Implement (if consolidating)
5. Test and commit

**Decision Matrix**:

| Scenario | Action |
|----------|--------|
| Vertical & Horizontal used, different layouts of same data | Extract shared logic to composable, keep both |
| Only one timeline actively used | Delete unused, keep active |
| Both used but nearly identical code | Consolidate with `orientation` prop |
| Artifact timeline different data structure | Keep separate (different purpose) |

**If Consolidating Vertical + Horizontal**:

**Create: `composables/useTimelineData.js`**
```javascript
import { ref, computed } from 'vue'

export function useTimelineData(events) {
  const sortedEvents = computed(() => {
    return [...events].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
  })

  const formattedEvents = computed(() => {
    return sortedEvents.value.map(event => ({
      ...event,
      formattedTime: formatDistanceToNow(new Date(event.timestamp), { addSuffix: true }),
      icon: getEventIcon(event.type),
      color: getEventColor(event.type),
    }))
  })

  function getEventIcon(type) {
    const icons = {
      started: 'mdi-play',
      completed: 'mdi-check',
      failed: 'mdi-alert',
      message: 'mdi-message',
    }
    return icons[type] || 'mdi-circle'
  }

  function getEventColor(type) {
    const colors = {
      started: 'info',
      completed: 'success',
      failed: 'error',
      message: 'grey',
    }
    return colors[type] || 'grey'
  }

  return {
    sortedEvents,
    formattedEvents,
  }
}
```

**Update: `SubAgentTimeline.vue`**
```vue
<template>
  <v-timeline :direction="orientation">
    <v-timeline-item
      v-for="event in formattedEvents"
      :key="event.id"
      :icon="event.icon"
      :dot-color="event.color"
    >
      <template v-slot:opposite>
        <span class="text-caption">{{ event.formattedTime }}</span>
      </template>
      <v-card>
        <v-card-title>{{ event.title }}</v-card-title>
        <v-card-text>{{ event.description }}</v-card-text>
      </v-card>
    </v-timeline-item>
  </v-timeline>
</template>

<script setup>
import { useTimelineData } from '@/composables/useTimelineData'

const props = defineProps({
  events: { type: Array, required: true },
  orientation: { type: String, default: 'vertical' }, // 'vertical' | 'horizontal'
})

const { formattedEvents } = useTimelineData(props.events)
</script>
```

**Delete: `SubAgentTimelineHorizontal.vue`** (if identical to vertical except orientation)

**Commit**:
```bash
git add -A
git commit -m "refactor(0130c): Consolidate timeline components

Changes:
- Extracted shared logic to composables/useTimelineData.js
- Added orientation prop to SubAgentTimeline.vue
- Deleted SubAgentTimelineHorizontal.vue (redundant)
- Updated usages to use orientation prop

Benefits:
- Single timeline component with flexible layout
- Shared data processing logic (DRY)
- Easier to maintain and extend

Handover: 0130c - Consolidate Duplicate Components"
```

**Success Criteria**:
- ✅ Timeline usage audited
- ✅ Consolidation decision documented
- ✅ Implementation complete (if consolidating)
- ✅ All usages updated
- ✅ Tests passing

### Phase 4: Update Documentation (1 hour)

**Steps**:
1. Update COMPONENT_GUIDE.md with consolidated components
2. Add JSDoc comments to new components
3. Create decision tree for component selection
4. Commit documentation

**Update: `frontend/COMPONENT_GUIDE.md`**
```markdown
# Component Usage Guide (Updated 2025-11-12)

## Agent Display

### AgentCard.vue ✅ (Unified Component)
**Location**: `components/AgentCard.vue`

**Purpose**: Display agent job status and information

**Variants**:
- `variant="compact"` - Grid display, minimal info
- `variant="full"` - Detailed display with context, handover, expansion

**When to use**:
- Compact: Grid layouts, overview pages, dashboards
- Full: Detailed views, job monitoring, project pages

**Props**:
```vue
<AgentCard
  :agent="agentObject"
  variant="compact|full"
  :clickable="true"
  :show-context="true"
  :show-handover="true"
  :expandable="false"
  @click="handleClick"
  @trigger-handover="handleHandover"
/>
```

**Example (Compact)**:
```vue
<AgentCard
  v-for="agent in agents"
  :agent="agent"
  variant="compact"
  clickable
  @click="viewAgentDetails"
/>
```

**Example (Full)**:
```vue
<AgentCard
  :agent="currentJob"
  variant="full"
  show-context
  show-handover
  expandable
  @trigger-handover="initiateHandover"
/>
```

## Timeline Display

### SubAgentTimeline.vue ✅ (Unified Component)
**Location**: `components/SubAgentTimeline.vue`

**Purpose**: Display chronological events in timeline format

**Orientations**:
- `orientation="vertical"` - Traditional top-to-bottom timeline
- `orientation="horizontal"` - Space-constrained horizontal layout

**When to use**:
- Vertical: Detail pages, full-screen views
- Horizontal: Compact displays, embedded in cards

**Props**:
```vue
<SubAgentTimeline
  :events="eventArray"
  orientation="vertical|horizontal"
/>
```

### ArtifactTimeline.vue ✅ (Specialized)
**Location**: `components/agent-flow/ArtifactTimeline.vue`

**Purpose**: Display artifact creation/modification timeline

**When to use**: Agent flow visualization, artifact tracking

**Note**: Different data structure from SubAgentTimeline (artifact-specific)

## Decision Tree: Which Component?

### Need to display agent status?
- **Grid/compact layout** → `<AgentCard variant="compact" />`
- **Detailed view** → `<AgentCard variant="full" />`

### Need to display events timeline?
- **Agent events** → `<SubAgentTimeline orientation="vertical|horizontal" />`
- **Artifact changes** → `<ArtifactTimeline />`

## Deprecated/Removed (Do Not Use)

### Consolidated Components (Removed in 0130c)
- ❌ `orchestration/AgentCard.vue` - Use unified `AgentCard.vue` instead
- ❌ `projects/AgentCardEnhanced.vue` - Use unified `AgentCard.vue` instead
- ❌ `SubAgentTimelineHorizontal.vue` - Use `SubAgentTimeline orientation="horizontal"` instead

## For Agentic AI Tools

When writing code that displays agents:
1. Always use `<AgentCard>` from `@/components/AgentCard.vue`
2. Choose variant based on layout: compact for grids, full for details
3. Do NOT create new agent card variants

When writing code that displays timelines:
1. Use `<SubAgentTimeline>` for agent events
2. Use `<ArtifactTimeline>` for artifact changes only
3. Control layout with `orientation` prop, not separate components
```

**Commit**:
```bash
git add -A
git commit -m "docs(0130c): Update component guide after consolidation

Updated COMPONENT_GUIDE.md with:
- Unified AgentCard.vue usage (compact vs full variants)
- Unified SubAgentTimeline.vue usage (vertical vs horizontal)
- Decision tree for component selection
- Deprecated component list (removed in 0130c)
- AI tool guidance for correct component usage

Handover: 0130c - Consolidate Duplicate Components"
```

---

## Testing and Validation

### Validation Checklist

**Build Validation**:
- [ ] Frontend builds successfully: `npm run build`
- [ ] No import errors in browser console
- [ ] All TypeScript types resolve correctly

**Component Testing**:
- [ ] AgentCard compact mode displays correctly
- [ ] AgentCard full mode displays correctly
- [ ] AgentCard variant switching works
- [ ] Timeline vertical orientation works
- [ ] Timeline horizontal orientation works
- [ ] All props function as expected

**Integration Testing**:
- [ ] AgentCardGrid displays agents (compact mode)
- [ ] JobsTab displays jobs (full mode)
- [ ] LaunchTab displays orchestrators (full mode)
- [ ] Timeline components render events
- [ ] No visual regressions

**Regression Testing**:
- [ ] Agent status updates work
- [ ] Handover button triggers correctly (orchestrators)
- [ ] Context usage bars display
- [ ] Click handlers fire
- [ ] WebSocket updates reflected in UI

---

## Success Criteria

### Code Consolidation Metrics

**Before 0130c**:
- AgentCard components: 2 files (~550 lines total)
- Timeline components: 3 files (~600 lines total)
- Component variants: Unclear which to use
- AI tool confusion: High risk

**After 0130c**:
- AgentCard components: 1 file (~450 lines) ✅
- Timeline components: 2 files (1 unified + 1 specialized) ✅
- Component variants: Clear variant prop guidance ✅
- AI tool confusion: Low risk ✅

### Quality Metrics

- [ ] Code reduction: 20-30% in consolidated components
- [ ] Feature parity: 100% (all features preserved)
- [ ] Documentation: Complete usage guide
- [ ] Developer experience: Clear component selection

---

## Rollback Plan

### If Consolidation Breaks Features

**Option 1: Revert Consolidation Commit**:
```bash
git log --oneline | grep "Consolidate.*components"
git revert <commit-hash>
```

**Option 2: Restore from Backup Files**:
```bash
# Restore old AgentCard files (if backed up)
git checkout HEAD~1 -- frontend/src/components/orchestration/AgentCard.vue
git checkout HEAD~1 -- frontend/src/components/projects/AgentCardEnhanced.vue
```

---

## Completion Checklist

- [ ] Phase 1: Component usage audit complete
- [ ] Phase 2: AgentCard consolidated and tested
- [ ] Phase 3: Timeline components audited and consolidated (if needed)
- [ ] Phase 4: Documentation updated
- [ ] All tests passing
- [ ] No visual regressions
- [ ] COMPONENT_GUIDE.md updated
- [ ] Handover completion summary created
- [ ] Handover archived: `handovers/completed/0130c_consolidate_duplicate_components-C.md`

---

## Next Steps

After 0130c completion:

**DECISION POINT**: Should we proceed with 0130d (Centralize API Calls)?

**Options**:
- **Option A**: Execute 0130d (centralize API patterns)
- **Option B**: Skip to 0131 Production Readiness (recommended)

**Recommendation**: **Option B** - Frontend cleanup complete, move to production readiness

---

**Created**: 2025-11-12
**Status**: READY TO EXECUTE (after 0130b)
**Duration**: 1-2 days
**Success Factor**: Single-purpose components with clear documentation


---
# INTEGRATION NOTE
**Date**: 2025-11-15
**Status**: INTEGRATED INTO 0515

This work has been integrated into:
- **Handover 0515**: Frontend Consolidation & WebSocket V2 Completion
- **Specifically**: 0515a - Merge Duplicate Components

See: /handovers/0515_frontend_consolidation_websocket_v2.md
