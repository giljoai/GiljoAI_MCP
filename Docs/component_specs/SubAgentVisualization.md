# Sub-Agent Visualization Component Specifications

## Project: 5.1.c Dashboard Sub-Agent Visualization

**Designer**: designer agent
**Date**: 2025-01-15
**Version**: 1.0

---

## 1. SubAgentTimeline.vue

### Overview

A horizontal timeline visualization showing the lifecycle of orchestrator and sub-agents with real-time WebSocket updates.

### Visual Design

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Timeline Header                                               │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ 🤖 Agent Timeline              [Filter] [Export] [Refresh] ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Timeline Tracks                                              │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Orchestrator ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━││
│ │   └─ Designer    ━━━━━━━━━━                               ││
│ │   └─ Frontend    ━━━━━━━━━━━━━━                           ││
│ │   └─ Implementer      ━━━━━━━━━━━━━━━━━━                  ││
│ │   └─ Tester                       ━━━━━━━━                ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Timeline Axis                                                │
│ ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤   │
│ 0s   10s  20s  30s  40s  50s  60s  70s  80s  90s  100s      │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```vue
<template>
  <v-card class="sub-agent-timeline" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center">
      <v-icon left color="primary">
        <!-- Use frontend/public/icons/users.svg -->
      </v-icon>
      <span>Agent Timeline</span>
      <v-spacer />
      <v-btn-toggle v-model="viewMode" density="compact">
        <v-btn value="live" size="small">Live</v-btn>
        <v-btn value="history" size="small">History</v-btn>
      </v-btn-toggle>
      <v-btn
        icon="mdi-filter"
        size="small"
        @click="showFilters = !showFilters"
      />
      <v-btn icon="mdi-download" size="small" @click="exportTimeline" />
      <v-btn icon="mdi-refresh" size="small" @click="refreshTimeline" />
    </v-card-title>

    <!-- Filters (collapsible) -->
    <v-expand-transition>
      <v-card-text v-show="showFilters" class="filters-section">
        <v-row dense>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedProject"
              :items="projects"
              label="Project"
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedAgentTypes"
              :items="agentTypes"
              label="Agent Types"
              multiple
              chips
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="timeRange.start"
              label="Start Time"
              type="datetime-local"
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="timeRange.end"
              label="End Time"
              type="datetime-local"
              density="compact"
              hide-details
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-expand-transition>

    <!-- Timeline Container -->
    <v-card-text class="timeline-container">
      <div class="timeline-wrapper" ref="timelineWrapper">
        <!-- SVG Timeline rendered here -->
      </div>
    </v-card-text>

    <!-- Agent Details Panel (expandable) -->
    <v-expand-transition>
      <v-card-text v-if="selectedAgent" class="agent-details">
        <v-row>
          <v-col cols="12" md="6">
            <div class="detail-item">
              <strong>Agent:</strong> {{ selectedAgent.name }}
            </div>
            <div class="detail-item">
              <strong>Status:</strong>
              <v-chip
                :color="getStatusColor(selectedAgent.status)"
                size="small"
              >
                {{ selectedAgent.status }}
              </v-chip>
            </div>
            <div class="detail-item">
              <strong>Duration:</strong>
              {{ formatDuration(selectedAgent.duration) }}
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="detail-item">
              <strong>Context Usage:</strong>
              <v-progress-linear
                :model-value="selectedAgent.contextUsage"
                :color="getContextColor(selectedAgent.contextUsage)"
                height="20"
                rounded
              >
                {{ selectedAgent.contextUsage }}%
              </v-progress-linear>
            </div>
            <div class="detail-item">
              <strong>Mission:</strong>
              <v-tooltip :text="selectedAgent.mission">
                <template v-slot:activator="{ props }">
                  <span v-bind="props" class="mission-text">
                    {{ truncate(selectedAgent.mission, 100) }}
                  </span>
                </template>
              </v-tooltip>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-expand-transition>
  </v-card>
</template>
```

### Color Scheme (from docs/color_themes.md)

- **Background**: `#1e3147` (Medium Dark Blue - card background)
- **Timeline Track Background**: `#182739` (Dark Blue)
- **Active Agent Bar**: `#67bd6d` (Success Green)
- **Pending Agent Bar**: `#ffc300` (Primary Yellow)
- **Completed Agent Bar**: `#8f97b7` (Light Blue)
- **Failed Agent Bar**: `#c6298c` (Alert Pink/Red)
- **Grid Lines**: `#315074` (Medium Blue)
- **Text**: `#e1e1e1` (Light Gray)

### Icons Used (from frontend/public/icons/)

- `users.svg` - Timeline header icon
- `rocket.svg` - Agent spawn indicator
- `checkmark.svg` - Agent completion indicator
- `close.svg` - Agent failure indicator
- `refresh.svg` - Refresh button
- `download.svg` - Export button

### Responsive Breakpoints

- **Mobile (320px - 600px)**:
  - Vertical stacking of timeline tracks
  - Simplified time axis (fewer labels)
  - Touch-enabled pan/zoom
- **Tablet (600px - 960px)**:
  - Horizontal timeline with scroll
  - Collapsible filters
- **Desktop (960px - 1280px+)**:
  - Full horizontal timeline
  - All controls visible
  - Side-by-side agent details

### WebSocket Events

```javascript
// Listen for real-time updates
websocketService.onMessage("agent:spawn", (data) => {
  // Add new agent to timeline
});

websocketService.onMessage("agent:complete", (data) => {
  // Update agent status and duration
});

websocketService.onMessage("agent:update", (data) => {
  // Update context usage and status
});
```

### Animation Specifications

- **Agent Bar Entry**: Slide in from left, 300ms ease-out
- **Status Changes**: Color transition 200ms ease
- **Hover Effects**: Scale 1.02, elevation increase
- **Timeline Pan**: Smooth scroll with momentum
- **Progress Updates**: Animated width changes

---

## 2. SubAgentTree.vue

### Overview

Interactive tree visualization showing parent-child relationships between orchestrator and sub-agents with collapsible nodes.

### Visual Design

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Tree Header                                                  │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ 🌳 Agent Hierarchy         [Expand All] [Collapse] [Reset] ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Tree Visualization                                           │
│ ┌───────────────────────────────────────────────────────────┐│
│ │     [Orchestrator]                                         ││
│ │          │                                                 ││
│ │    ┌─────┼─────┬─────────┐                               ││
│ │    │     │     │         │                               ││
│ │ [Designer] [Frontend] [Implementer]                       ││
│ │             │                                              ││
│ │         ┌───┴───┐                                         ││
│ │         │       │                                         ││
│ │    [Component1] [Component2]                              ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Legend & Controls                                            │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ 🟢 Active  🟡 Pending  🔵 Complete  🔴 Failed             ││
│ │ Zoom: [－][slider][＋]  Pan: Click & Drag                 ││
│ └───────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```vue
<template>
  <v-card class="sub-agent-tree" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center">
      <v-icon left color="primary">
        <!-- Use frontend/public/icons/chart.svg -->
      </v-icon>
      <span>Agent Hierarchy</span>
      <v-spacer />
      <v-btn size="small" @click="expandAll">
        <v-icon left>mdi-unfold-more-horizontal</v-icon>
        Expand All
      </v-btn>
      <v-btn size="small" @click="collapseAll">
        <v-icon left>mdi-unfold-less-horizontal</v-icon>
        Collapse
      </v-btn>
      <v-btn size="small" @click="resetView">
        <v-icon left>mdi-restore</v-icon>
        Reset
      </v-btn>
    </v-card-title>

    <!-- Tree Container -->
    <v-card-text class="tree-container">
      <div class="tree-wrapper" ref="treeWrapper">
        <!-- D3.js or Vue-flow tree rendered here -->
        <svg :width="treeWidth" :height="treeHeight" class="tree-svg">
          <!-- Tree nodes and links -->
        </svg>
      </div>

      <!-- Zoom Controls -->
      <div class="zoom-controls">
        <v-btn icon="mdi-minus" size="x-small" @click="zoomOut" />
        <v-slider
          v-model="zoomLevel"
          :min="0.5"
          :max="2"
          :step="0.1"
          density="compact"
          hide-details
          class="zoom-slider"
        />
        <v-btn icon="mdi-plus" size="x-small" @click="zoomIn" />
      </div>
    </v-card-text>

    <!-- Node Details Tooltip -->
    <v-tooltip
      v-model="showTooltip"
      :location="tooltipLocation"
      :open-on-hover="false"
      contained
    >
      <template v-slot:activator>
        <!-- Invisible activator -->
      </template>
      <div class="node-tooltip">
        <div class="tooltip-header">
          <v-icon :color="getNodeColor(hoveredNode?.status)" size="small">
            {{ getNodeIcon(hoveredNode?.type) }}
          </v-icon>
          <strong>{{ hoveredNode?.name }}</strong>
        </div>
        <v-divider class="my-1" />
        <div class="tooltip-content">
          <div><strong>Type:</strong> {{ hoveredNode?.type }}</div>
          <div><strong>Status:</strong> {{ hoveredNode?.status }}</div>
          <div>
            <strong>Children:</strong> {{ hoveredNode?.children?.length || 0 }}
          </div>
          <div><strong>Context:</strong> {{ hoveredNode?.contextUsage }}%</div>
          <div>
            <strong>Duration:</strong>
            {{ formatDuration(hoveredNode?.duration) }}
          </div>
        </div>
      </div>
    </v-tooltip>

    <!-- Legend -->
    <v-card-actions class="legend-section">
      <v-chip
        v-for="status in statusTypes"
        :key="status.value"
        :color="status.color"
        size="small"
        class="mr-2"
      >
        <v-icon left size="x-small">{{ status.icon }}</v-icon>
        {{ status.label }}
      </v-chip>
    </v-card-actions>
  </v-card>
</template>
```

### Tree Node Design

```javascript
// Node structure
const nodeTemplate = {
  id: "agent-uuid",
  name: "Agent Name",
  type: "orchestrator|designer|frontend|implementer|tester",
  status: "active|pending|complete|failed",
  parent: "parent-uuid",
  children: [],
  contextUsage: 75,
  duration: 45000, // ms
  mission: "Agent mission description",
  expanded: true,

  // Visual properties
  x: 0,
  y: 0,
  width: 140,
  height: 60,
  color: "#67bd6d",
  icon: "robot.svg",
};
```

### Node Visual Specifications

```
┌─────────────────────────┐
│  🤖  Orchestrator       │  <- Icon + Name
│  ████████████░░░  75%   │  <- Context usage bar
│  Status: Active         │  <- Status indicator
└─────────────────────────┘
```

- **Node Dimensions**: 140px × 60px
- **Border Radius**: 8px (Vuetify rounded)
- **Border Width**: 2px
- **Shadow**: elevation-2 (Vuetify)

### Color Coding (from docs/color_themes.md)

#### Node Backgrounds

- **Orchestrator**: `#1e3147` (Medium Dark Blue)
- **Active Agents**: `#182739` (Dark Blue)
- **All Nodes Border by Status**:
  - Active: `#67bd6d` (Green) - 2px solid
  - Pending: `#ffc300` (Yellow) - 2px solid
  - Complete: `#8f97b7` (Light Blue) - 2px solid
  - Failed: `#c6298c` (Pink/Red) - 2px solid

#### Connection Lines

- **Active Path**: `#67bd6d` (Green) - 2px solid
- **Inactive Path**: `#315074` (Medium Blue) - 1px dashed
- **Handoff Arrow**: `#ffc300` (Yellow)

### Icons Used (from frontend/public/icons/)

- `chart.svg` - Tree header icon
- `users.svg` - Orchestrator node
- `bubble.svg` - Sub-agent nodes
- `rocket.svg` - Active status
- `checkmark.svg` - Complete status
- `close.svg` - Failed status

### Interaction Specifications

#### Click Actions

- **Single Click**: Select node, show details
- **Double Click**: Expand/collapse children
- **Right Click**: Context menu (view logs, restart, terminate)

#### Drag Actions

- **Node Drag**: Disabled (auto-layout)
- **Canvas Drag**: Pan the tree view
- **Scroll Wheel**: Zoom in/out

#### Hover Effects

- **Node Hover**:
  - Scale to 1.05
  - Elevation increase
  - Show tooltip after 500ms
  - Highlight connected paths

### Animation Specifications

- **Node Appearance**: Fade in + scale from 0.8 to 1.0, 400ms ease-out
- **Node Status Change**: Color transition 300ms ease
- **Tree Expansion**: Spring animation, 500ms
- **Connection Lines**: Draw animation from parent to child, 300ms
- **Zoom**: Smooth transition, 200ms ease-in-out

### Responsive Behavior

#### Mobile (320px - 600px)

- Simplified node design (name only)
- Touch gestures for pan/zoom
- Tap to show details in modal

#### Tablet (600px - 960px)

- Full node design
- Touch + mouse support
- Side panel for details

#### Desktop (960px+)

- Full interactive tree
- Hover tooltips
- Keyboard shortcuts

### WebSocket Integration

```javascript
// Real-time tree updates
websocketService.onMessage("agent:spawn", (data) => {
  addNodeToTree(data);
  animateNodeEntry(data.id);
});

websocketService.onMessage("agent:handoff", (data) => {
  animateHandoff(data.from, data.to);
});

websocketService.onMessage("agent:complete", (data) => {
  updateNodeStatus(data.id, "complete");
});
```

---

## 3. Integration Guidelines

### State Management (Pinia)

```javascript
// stores/agentVisualization.js
export const useAgentVisualizationStore = defineStore("agentVisualization", {
  state: () => ({
    agents: [],
    timeline: {
      start: null,
      end: null,
      events: [],
    },
    tree: {
      root: null,
      nodes: {},
      links: [],
    },
    filters: {
      project: null,
      agentTypes: [],
      status: [],
      timeRange: {},
    },
  }),

  actions: {
    async fetchAgentTree(projectId) {
      // GET /api/agents/tree
    },

    async fetchAgentMetrics(filters) {
      // GET /api/agents/metrics
    },

    handleAgentSpawn(data) {
      // Update both timeline and tree
    },

    handleAgentComplete(data) {
      // Update status and duration
    },
  },
});
```

### API Endpoints Required

1. **GET /api/agents/tree**

   - Returns hierarchical agent structure
   - Response time: <100ms

2. **GET /api/agents/metrics**

   - Returns performance statistics
   - Supports filtering by project, time range
   - Response time: <100ms

3. **WebSocket Events**
   - `agent:spawn` - New agent created
   - `agent:complete` - Agent finished
   - `agent:update` - Status/context change
   - `agent:handoff` - Work transferred

### Performance Requirements

- **Initial Load**: <500ms for 100 agents
- **Real-time Updates**: <100ms latency
- **Animations**: 60fps minimum
- **Memory Usage**: <50MB for 1000 agents
- **Tree Rendering**: Virtual scrolling for >500 nodes

### Accessibility (WCAG 2.1 AA)

- **Keyboard Navigation**: Full tree traversal with arrow keys
- **Screen Reader**: ARIA labels for all interactive elements
- **Focus Indicators**: Visible focus rings
- **Color Contrast**: All text meets 4.5:1 ratio
- **Alternative Text**: Icons have descriptive labels

---

## 4. Component Props & Events

### SubAgentTimeline.vue

#### Props

```typescript
interface TimelineProps {
  projectId?: string;
  agents?: Agent[];
  timeRange?: { start: Date; end: Date };
  autoRefresh?: boolean;
  refreshInterval?: number;
}
```

#### Events

```typescript
emit('agent-selected', agent: Agent)
emit('time-range-changed', range: TimeRange)
emit('export-requested', format: 'csv' | 'json')
```

### SubAgentTree.vue

#### Props

```typescript
interface TreeProps {
  projectId?: string;
  rootAgent?: Agent;
  expandLevel?: number;
  interactive?: boolean;
  showLegend?: boolean;
}
```

#### Events

```typescript
emit('node-selected', node: TreeNode)
emit('node-expanded', node: TreeNode)
emit('node-collapsed', node: TreeNode)
emit('context-menu', { node: TreeNode, event: MouseEvent })
```

---

## 5. Implementation Priority

### Phase 1 (Immediate)

1. Basic SubAgentTimeline with static data
2. Basic SubAgentTree with static data
3. WebSocket listeners setup

### Phase 2 (Next Iteration)

1. Real-time updates
2. Interactive features (zoom, pan, filters)
3. API integration

### Phase 3 (Polish)

1. Animations and transitions
2. Export functionality
3. Performance optimizations
4. Mobile responsiveness

---

## 6. Handoff to frontend_developer

### Required Actions

1. Implement components following these specifications exactly
2. Use only the specified colors from docs/color_themes.md
3. Use only icons from frontend/public/icons/
4. Ensure WebSocket integration for real-time updates
5. Follow Vuetify 3 component patterns
6. Test responsive behavior at all breakpoints
7. Implement loading states with MascotLoader.vue
8. Add error handling with ToastManager.vue

### Deliverables Expected

1. SubAgentTimeline.vue component
2. SubAgentTree.vue component
3. Pinia store for state management
4. Integration with DashboardView.vue
5. Unit tests for critical functions
6. Documentation of any deviations

---

**Designer Agent Signature**: Complete specifications delivered
**Next Step**: Handoff to frontend_developer for implementation
**Timeline**: Implementation should begin immediately
