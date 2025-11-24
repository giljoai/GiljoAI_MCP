# Professional Agent Flow Visualization System

## Overview

The Agent Flow Visualization system is a state-of-the-art, production-grade component suite for visualizing AI agent orchestration in real-time. Built with Vue 3, Vue Flow, GSAP animations, and Vuetify, it provides a professional interface for monitoring and managing complex agent workflows.

## Architecture

### Core Components

#### 1. **FlowCanvas.vue** - Main Visualization Container
The central orchestration component that manages the entire flow visualization.

**Features:**
- Pan and zoom controls (0.1x - 4x zoom)
- Drag-and-drop node repositioning
- Auto-layout and reset view functionality
- Real-time WebSocket integration
- Status bar with live metrics
- Detail panels for nodes and edges
- Dark-themed, professional UI

**Props:**
```javascript
{
  projectId: String,           // Project to visualize
  autoInitialize: Boolean,     // Auto-fetch agents on mount
  showDetails: Boolean         // Show detail panels
}
```

**Emitted Events:**
```javascript
@node-selected="(node) => {}"   // Node clicked
@edge-selected="(edge) => {}"   // Edge clicked
@flow-ready="() => {}"          // Flow initialized
```

#### 2. **AgentNode.vue** - Individual Agent Visualization
Represents a single agent in the flow with status, metrics, and messages.

**Features:**
- Status indicator ring with animations
- Health and context usage progress bars
- Active job count badge
- Message counter badge
- Hover panel with detailed information
- Status-based styling (active=green, error=red, etc.)
- Handles for connections

**Data Structure:**
```javascript
{
  label: String,              // Agent name
  agentId: String,           // Unique identifier
  status: 'active' | 'pending' | 'completed' | 'error',
  role: String,              // Agent role/type
  health: Number,            // Health percentage (0-100)
  activeJobs: Number,        // Number of active jobs
  contextUsed: Number,       // Context usage percentage
  tokens: Number,            // Total tokens used
  duration: Number,          // Execution time in ms
  messages: Array,           // Message objects
  icon: String              // MDI icon name
}
```

#### 3. **ThreadView.vue** - Message Conversation Panel
Displays all messages exchanged with an agent in a threaded format.

**Features:**
- Real-time message updates
- Search and filter capabilities
- Status-based message styling
- Message expansion with detailed information
- Auto-scroll to latest messages
- Message actions (copy, delete, view details)
- Priority indicators
- Acknowledgment tracking

**Props:**
```javascript
{
  nodeId: String,            // Agent node ID
  agentName: String,         // Agent name
  limit: Number              // Messages per load
}
```

#### 4. **MissionDashboard.vue** - Mission Overview
High-level dashboard showing mission progress and status.

**Features:**
- Mission title and description
- Progress bar with percentage
- Assigned agents list with status
- Goals tracking
- Timeline with start/completion times
- Error messages display
- Mission control actions (pause/resume/stop)
- Quick statistics

#### 5. **ArtifactTimeline.vue** - Created Files/Artifacts
Timeline and gallery of artifacts created during execution.

**Features:**
- List and grid view modes
- Search and filter by type
- Sorting (newest/oldest first)
- File size display
- Path and description preview
- Tag system
- Download and copy path actions
- File type icons
- Agent association tracking

### State Management

#### **agentFlowStore.js** - Pinia Store
Centralized state management for the flow visualization.

**State:**
```javascript
{
  nodes: Array,                 // Flow nodes
  edges: Array,                 // Connections
  selectedNode: Object|null,    // Currently selected node
  selectedEdge: Object|null,    // Currently selected edge
  flowZoom: Number,            // Current zoom level
  flowPan: Object,             // Pan position {x, y}
  flowLoading: Boolean,        // Loading state
  flowError: String|null,      // Error message
  animationSpeed: String,      // 'fast', 'normal', 'slow'
  showMinimap: Boolean,        // Minimap visibility
  showControls: Boolean,       // Controls visibility
  missionData: Object|null,    // Active mission data
  artifacts: Array,            // Created artifacts
  threadMessages: Object,      // Node -> messages mapping
  nodeMetrics: Object          // Historical metrics
}
```

**Key Actions:**
```javascript
// Initialization
initializeFromAgents()           // Load agents into flow
generateEdgesFromMessages()      // Create connections

// Node Management
updateNodeStatus(nodeId, status)
updateNodeMetrics(nodeId, metrics)
selectNode(nodeId)
clearSelection()

// Message Management
addMessageToNode(nodeId, message)
getThreadMessages(nodeId)
handleMessageFlow(data)

// Mission Management
setMissionData(mission)
addArtifact(artifact)

// View Management
updateZoom(zoom)
updatePan(pan)
resetFlow()
```

### Services

#### **flowWebSocket.js** - Real-time Communication
Manages WebSocket subscriptions for real-time flow updates.

**Subscribed Events:**
```javascript
// Agent Events
'agent_communication:status_update'    // Agent status changed
'agent_communication:agent_spawned'    // New agent spawned
'agent_communication:agent_complete'   // Agent completed
'agent_communication:error'            // Agent error

// Message Events
'agent_communication:message_sent'           // Message sent
'agent_communication:message_acknowledged'  // Message acknowledged
'agent_communication:message_completed'     // Message completed

// Artifact Events
'agent_communication:artifact_created'      // File created
'agent_communication:directory_structure'   // Directory created
'agent_communication:code_artifact'         // Code file created

// Mission Events
'mission:started'                     // Mission started
'mission:progress'                    // Progress update
'mission:completed'                   // Mission completed
'mission:failed'                      // Mission failed
```

**Methods:**
```javascript
initialize()                         // Setup subscriptions
subscribeToAgent(agentId)           // Subscribe to agent
unsubscribeFromAgent(agentId)       // Unsubscribe from agent
subscribeToProject(projectId)       // Subscribe to project
unsubscribeFromProject(projectId)   // Unsubscribe from project
on(event, handler)                  // Register custom handler
clearSubscriptions()                // Cleanup
```

## Color Scheme

Professional dark theme with semantic colors:

```javascript
colorPalette = {
  active: '#67bd6d',     // Green - Active/Running
  waiting: '#ffc300',    // Amber - Waiting
  complete: '#8b5cf6',   // Purple - Completed
  error: '#c6298c',      // Red/Pink - Error
  pending: '#315074'     // Blue - Pending
}
```

## Animation Durations

```javascript
animationDurations = {
  fast: 200,    // Quick UI feedback
  normal: 400,  // Standard transitions
  slow: 800     // Smooth emphasis animations
}
```

## Integration Guide

### 1. Basic Setup

```vue
<template>
  <div class="app">
    <FlowCanvas
      :project-id="currentProject.id"
      :auto-initialize="true"
      :show-details="true"
      @flow-ready="onFlowReady"
      @node-selected="onNodeSelected"
    />
  </div>
</template>

<script setup>
import { FlowCanvas } from '@/components/agent-flow'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentProject = { id: route.params.projectId }

function onFlowReady() {
  console.log('Flow initialized')
}

function onNodeSelected(node) {
  console.log('Selected node:', node.data.label)
}
</script>
```

### 2. Full Dashboard Layout

```vue
<template>
  <v-container fluid class="dashboard-container">
    <v-row>
      <!-- Main Flow Canvas -->
      <v-col cols="12" md="8">
        <FlowCanvas :project-id="projectId" />
      </v-col>

      <!-- Sidebar Panels -->
      <v-col cols="12" md="4">
        <!-- Mission Overview -->
        <MissionDashboard class="mb-4" />

        <!-- Artifacts Timeline -->
        <ArtifactTimeline class="mb-4" />
      </v-col>
    </v-row>

    <!-- Full-width Message Thread -->
    <v-row>
      <v-col cols="12">
        <ThreadView
          v-if="selectedAgent"
          :node-id="`agent-${selectedAgent.id}`"
          :agent-name="selectedAgent.name"
          @message-details="showMessageDetails"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import {
  FlowCanvas,
  MissionDashboard,
  ArtifactTimeline,
  ThreadView,
} from '@/components/agent-flow'
import { useAgentFlowStore } from '@/stores/agentFlow'

const flowStore = useAgentFlowStore()
const projectId = 'project-123'
const selectedAgent = ref(null)

// Watch for node selections
watch(
  () => flowStore.selectedNode,
  (node) => {
    if (node?.data?.agentId) {
      selectedAgent.value = { id: node.data.agentId, name: node.data.label }
    }
  },
)

function showMessageDetails(message) {
  // Handle message details
}
</script>
```

### 3. Real-time Updates

The system automatically handles real-time updates through WebSocket events:

```javascript
// In your agent store or orchestrator:

// When agent status changes
broadcastMessage('agent_communication:status_update', {
  agent_name: 'designer',
  agent_id: 'agent-123',
  status: 'active',
  health: 95,
  context_used: 45,
  active_jobs: 2
})

// When message is sent
broadcastMessage('agent_communication:message_sent', {
  message_id: 'msg-456',
  from_agent: 'orchestrator',
  to_agents: ['designer', 'developer'],
  content: 'Design the UI component',
  created_at: new Date().toISOString()
})

// When artifact is created
broadcastMessage('agent_communication:artifact_created', {
  filename: 'component.vue',
  filepath: '/src/components/component.vue',
  agent_name: 'designer',
  agent_id: 'agent-123',
  content_type: 'text/vue',
  filesize: 2048
})
```

### 4. Styling and Customization

All components use CSS custom properties for theming:

```scss
// Override colors
:root {
  --color-bg-elevated: #1e3147;
  --color-bg-secondary: #182739;
  --color-border: #315074;
  --color-accent-primary: #ffc300;
  --color-text-primary: #e1e1e1;
  --color-text-secondary: #8f97b7;
}

// Component-specific customization
.flow-canvas {
  // Customize your flow here
}

.agent-node {
  --node-color: #67bd6d; // Per-node color
}
```

## Performance Optimization

### 1. Virtual Scrolling
ThreadView uses virtual scrolling for messages:
- Max 50 messages in DOM at once
- Automatic load-more pagination
- Smooth scrolling with 60fps

### 2. State Management
- Efficient Pinia store with computed properties
- Limited artifact history (max 100 items)
- Message deduplication
- Metric data limiting (max 100 per node)

### 3. Animation Performance
- GSAP for smooth 60fps animations
- Hardware-accelerated transforms
- Optimized CSS transitions
- Configurable animation speed

### 4. Rendering Efficiency
- Vue Flow handles large node counts efficiently
- Lazy loading of detail panels
- Conditional rendering for heavy components
- Smart recomputation of expensive computations

## Testing

### Run Tests
```bash
npm run test                    # Run all tests
npm run test:coverage          # Generate coverage report
npm run test:ui               # Interactive UI test runner
```

### Test Coverage
- **Store tests:** 89%+ coverage of agentFlowStore
- **Component tests:** Visual rendering and interactions
- **Integration tests:** WebSocket and real-time updates
- **E2E tests:** Complete user workflows (optional)

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern mobile browsers

## Dependencies

```json
{
  "@vue-flow/core": "^1.0.0",
  "@vue-flow/background": "^1.0.0",
  "@vue-flow/controls": "^1.0.0",
  "@vue-flow/minimap": "^1.0.0",
  "gsap": "^3.12.0",
  "vue": "^3.4.0",
  "vuetify": "^3.4.0",
  "pinia": "^3.0.0"
}
```

## Troubleshooting

### Flow Not Rendering
1. Check WebSocket connection status
2. Verify agents exist in store
3. Check browser console for errors
4. Ensure projectId prop is set

### Nodes Not Updating
1. Verify WebSocket events are being broadcast
2. Check event names match subscription patterns
3. Ensure data format matches expected structure
4. Check store actions are being called

### Performance Issues
1. Reduce animation speed in settings
2. Limit number of nodes (group/collapse)
3. Disable minimap if not needed
4. Clear artifact history periodically

### Styling Issues
1. Check Vuetify theme is properly configured
2. Verify dark theme colors in theme.js
3. Check CSS custom properties are defined
4. Clear browser cache and rebuild

## API Reference

### FlowCanvas Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| projectId | String | null | Project identifier |
| autoInitialize | Boolean | true | Auto-fetch agents |
| showDetails | Boolean | true | Show detail panels |

### AgentNode Data
| Field | Type | Description |
|-------|------|-------------|
| label | String | Agent display name |
| agentId | String | Unique identifier |
| status | String | Current status |
| role | String | Agent role/type |
| health | Number | Health percentage |
| activeJobs | Number | Active job count |
| contextUsed | Number | Context usage % |
| tokens | Number | Total tokens used |
| messages | Array | Message objects |

### Store Actions
See agentFlowStore documentation above for complete API reference.

## Contributing

When adding new features:
1. Follow Vue 3 Composition API patterns
2. Use Pinia for state management
3. Implement comprehensive tests
4. Add TypeScript types (optional but recommended)
5. Update this documentation
6. Ensure accessibility (a11y)
7. Test responsive design

## License

Part of GiljoAI MCP project. All rights reserved.

## Support

For issues, questions, or suggestions:
- Check the integration guide above
- Review test files for usage examples
- Check browser console for detailed errors
- Review WebSocket event logs in debug mode

## Changelog

### v1.0.0 (Initial Release)
- Full flow visualization system
- Real-time WebSocket integration
- Message threading and artifact tracking
- Mission overview dashboard
- Professional dark theme
- Comprehensive test coverage
- Production-ready performance

---

**Last Updated:** 2024-10-22  
**Version:** 1.0.0  
**Status:** Production Ready
